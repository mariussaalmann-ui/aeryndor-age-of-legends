# -*- coding: utf-8 -*-
"""
AERYNDOR – Serverseitige Bot-Navigation (Hindernis-Karte, A*-Umwege & Navigations-Gedächtnis)

Problem vorher: Der Server bewegte Bots/Autojagd stur in gerader Linie. Häuser, Mauern, Felsen & Bäume
existieren nur im Client -> Bots liefen gegen Gebäude und pendelten davor auf und ab.

Lösung:
  1. Hindernis-Karte: Der Client meldet einmalig pro Map seine Kollisionsdaten (Kreise, Mauersegmente,
     Häuser als gedrehte Rechtecke) an /api/world-obstacles. Gespeichert in data/world_obstacles_<map>.json.
  2. Bewegung: Jeder Server-Schritt wird gegen die Hindernisse geprüft (Gleiten an Wänden statt Durchlaufen).
  3. Umweg-Planung: Ist die direkte Linie blockiert, berechnet A* (2m-Raster, begrenztes Suchfenster)
     einen geglätteten Umweg um das Hindernis.
  4. Gedächtnis: Stellen, an denen ein Bot trotz allem feststeckt, werden als blockiert gemerkt
     (data/bot_nav_memory.json, überlebt Neustarts) und bei künftigen Planungen gemieden.
     Erfolgreiche Umwege werden pro Start-/Zielzelle zwischengespeichert und wiederverwendet.
"""

import heapq
import json
import math
import os
import threading
import time
from typing import Dict, List, Optional, Tuple

NAV_CELL = 2.0          # Raster-Auflösung der A*-Suche (Meter)
BUCKET = 16.0           # Zellgröße des räumlichen Hash-Gitters für Hindernisse
AGENT_PAD = 0.75        # Körperradius des Bots inkl. Sicherheitsabstand
MAX_ASTAR_NODES = 9000  # Obergrenze pro Planung (verhindert Lastspitzen)
LOOKAHEAD = 34.0        # So weit wird die direkte Linie auf Hindernisse geprüft
PLAN_HORIZON = 70.0     # Maximale Entfernung des Zwischenziels einer Planung
MEMORY_TTL_SEC = 14 * 24 * 3600.0
WORLD_LIMIT = 1400.0


def _f(v, default=0.0) -> float:
    try:
        x = float(v)
        if math.isfinite(x):
            return x
    except (TypeError, ValueError):
        pass
    return default


class MapObstacles:
    """Statische Hindernisse einer Map mit räumlichem Hash-Gitter."""

    def __init__(self, map_id: str, data: dict):
        self.map_id = map_id
        self.layout_hash = str(data.get("layoutHash") or "")
        self.circles: List[Tuple[float, float, float]] = []
        self.segments: List[Tuple[float, float, float, float, float]] = []
        self.boxes: List[Tuple[float, float, float, float, float, float]] = []  # x, z, halfW, halfD, cos, sin
        for c in data.get("circles") or []:
            if len(c) >= 3:
                x, z, r = _f(c[0]), _f(c[1]), _f(c[2])
                if 0.25 <= r <= 60.0 and abs(x) <= WORLD_LIMIT and abs(z) <= WORLD_LIMIT:
                    self.circles.append((x, z, r))
        for s in data.get("segments") or []:
            if len(s) >= 5:
                ax, az, bx, bz, ht = (_f(s[0]), _f(s[1]), _f(s[2]), _f(s[3]), _f(s[4], 0.8))
                if math.hypot(bx - ax, bz - az) <= 400.0 and 0.05 <= ht <= 12.0:
                    self.segments.append((ax, az, bx, bz, ht))
        for b in data.get("boxes") or []:
            if len(b) >= 5:
                x, z, w, d, rot = _f(b[0]), _f(b[1]), _f(b[2]), _f(b[3]), _f(b[4])
                if 0.5 <= w <= 80.0 and 0.5 <= d <= 80.0:
                    self.boxes.append((x, z, w * 0.5, d * 0.5, math.cos(rot), math.sin(rot)))
        self._buckets: Dict[Tuple[int, int], List[Tuple[str, int]]] = {}
        self._cell_cache: Dict[Tuple[int, int], bool] = {}
        self._index()

    def _add(self, kind: str, idx: int, minx: float, minz: float, maxx: float, maxz: float):
        for bx in range(int(math.floor(minx / BUCKET)), int(math.floor(maxx / BUCKET)) + 1):
            for bz in range(int(math.floor(minz / BUCKET)), int(math.floor(maxz / BUCKET)) + 1):
                self._buckets.setdefault((bx, bz), []).append((kind, idx))

    def _index(self):
        m = AGENT_PAD + 1.0
        for i, (x, z, r) in enumerate(self.circles):
            self._add("c", i, x - r - m, z - r - m, x + r + m, z + r + m)
        for i, (ax, az, bx, bz, ht) in enumerate(self.segments):
            self._add("s", i, min(ax, bx) - ht - m, min(az, bz) - ht - m, max(ax, bx) + ht + m, max(az, bz) + ht + m)
        for i, (x, z, hw, hd, _c, _s) in enumerate(self.boxes):
            r = math.hypot(hw, hd)
            self._add("b", i, x - r - m, z - r - m, x + r + m, z + r + m)

    @property
    def count(self) -> int:
        return len(self.circles) + len(self.segments) + len(self.boxes)

    def point_blocked(self, x: float, z: float, pad: float = AGENT_PAD) -> bool:
        items = self._buckets.get((int(math.floor(x / BUCKET)), int(math.floor(z / BUCKET))))
        if not items:
            return False
        for kind, idx in items:
            if kind == "c":
                cx, cz, r = self.circles[idx]
                rr = r + pad
                dx = x - cx
                dz = z - cz
                if dx * dx + dz * dz < rr * rr:
                    return True
            elif kind == "s":
                ax, az, bx, bz, ht = self.segments[idx]
                vx, vz = bx - ax, bz - az
                l2 = vx * vx + vz * vz
                t = 0.0 if l2 < 1e-6 else max(0.0, min(1.0, ((x - ax) * vx + (z - az) * vz) / l2))
                px, pz = ax + t * vx, az + t * vz
                rr = ht + pad
                if (x - px) ** 2 + (z - pz) ** 2 < rr * rr:
                    return True
            else:
                bx, bz, hw, hd, c, s = self.boxes[idx]
                dx, dz = x - bx, z - bz
                # In lokales Haus-Koordinatensystem drehen (THREE.js rotation.y)
                lx = dx * c - dz * s
                lz = dx * s + dz * c
                if abs(lx) < hw + pad and abs(lz) < hd + pad:
                    return True
        return False

    def cell_blocked(self, ix: int, iz: int) -> bool:
        key = (ix, iz)
        v = self._cell_cache.get(key)
        if v is None:
            v = self.point_blocked((ix + 0.5) * NAV_CELL, (iz + 0.5) * NAV_CELL, AGENT_PAD * 0.8)
            if len(self._cell_cache) > 400000:
                self._cell_cache.clear()
            self._cell_cache[key] = v
        return v


class BotNavigator:
    """Navigation & Gedächtnis für alle serverseitig bewegten Charaktere (Bots + Autojagd)."""

    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        self.maps: Dict[str, MapObstacles] = {}
        self._lock = threading.Lock()
        self._uploads: Dict[Tuple[str, str], dict] = {}
        self._pending_layout: Dict[str, str] = {}
        self.memory_path = os.path.join(data_dir, "bot_nav_memory.json")
        # map_id -> {"x,z": {"w": weight, "t": lastSeen, "n": hits}}
        self.memory: Dict[str, Dict[str, dict]] = {}
        self.detours: Dict[str, Dict[str, dict]] = {}
        # map_id -> layoutHash, zu dem das gelernte Gedaechtnis gehoert
        self.memory_layout: Dict[str, str] = {}
        self.stats = {"plans": 0, "planFails": 0, "stuckEvents": 0, "learnedBlocks": 0, "detourReuse": 0}
        self.generation: Dict[str, int] = {}
        self._mem_dirty = False
        self._mem_saved_at = time.time()
        self._load_all()

    # ------------------------------------------------------------------ Persistenz
    def _obstacle_path(self, map_id: str) -> str:
        safe = "".join(ch for ch in str(map_id) if ch.isalnum() or ch in "_-") or "map"
        return os.path.join(self.data_dir, f"world_obstacles_{safe}.json")

    def _load_all(self):
        try:
            for fn in os.listdir(self.data_dir):
                if fn.startswith("world_obstacles_") and fn.endswith(".json"):
                    try:
                        with open(os.path.join(self.data_dir, fn), "r", encoding="utf-8") as fh:
                            data = json.load(fh)
                        mid = str(data.get("mapId") or fn[len("world_obstacles_"):-5])
                        self.maps[mid] = MapObstacles(mid, data)
                        print(f"[BotNav] Hindernis-Karte geladen: {mid} ({self.maps[mid].count} Objekte)", flush=True)
                    except Exception as e:
                        print(f"[BotNav] Fehler beim Laden {fn}: {e}", flush=True)
        except FileNotFoundError:
            pass
        try:
            with open(self.memory_path, "r", encoding="utf-8") as fh:
                mem = json.load(fh)
            now = time.time()
            for mid, cells in (mem.get("blocked") or {}).items():
                self.memory[mid] = {k: v for k, v in cells.items() if now - _f(v.get("t")) < MEMORY_TTL_SEC}
            for mid, d in (mem.get("detours") or {}).items():
                self.detours[mid] = {k: v for k, v in d.items() if now - _f(v.get("t")) < MEMORY_TTL_SEC}
            self.stats.update({k: int(v) for k, v in (mem.get("stats") or {}).items() if k in self.stats})
            self.memory_layout = {str(k): str(v) for k, v in (mem.get("layout") or {}).items()}
        except (FileNotFoundError, ValueError):
            pass
        # Wurde eine Map seit dem letzten Lernen veraendert? -> altes Gedaechtnis vergessen
        for mid, mo in self.maps.items():
            if self.memory_layout.get(mid) != mo.layout_hash:
                self.forget_map(mid, mo.layout_hash, reason="Map-Layout beim Start geaendert")

    def save_memory(self, force: bool = False):
        now = time.time()
        if not force and (not self._mem_dirty or now - self._mem_saved_at < 60.0):
            return
        self._mem_saved_at = now
        self._mem_dirty = False
        payload = {
            "version": 2,
            "savedAt": int(now),
            "stats": self.stats,
            "layout": self.memory_layout,
            "blocked": self.memory,
            "detours": self.detours,
        }
        tmp = self.memory_path + ".tmp"
        try:
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump(payload, fh, separators=(",", ":"))
            os.replace(tmp, self.memory_path)
        except OSError as e:
            print(f"[BotNav] Gedächtnis konnte nicht gespeichert werden: {e}", flush=True)

    def summary(self) -> dict:
        return {
            "maps": {mid: {"objects": m.count, "layoutHash": m.layout_hash} for mid, m in self.maps.items()},
            "learnedBlockedCells": sum(len(v) for v in self.memory.values()),
            "rememberedDetours": sum(len(v) for v in self.detours.values()),
            **self.stats,
        }

    # ------------------------------------------------------------------ Upload vom Client
    def known_hash(self, map_id: str) -> str:
        m = self.maps.get(map_id)
        return m.layout_hash if m else ""

    def receive_upload(self, map_id: str, layout_hash: str, part: int, parts: int, body: dict) -> dict:
        map_id = str(map_id or "")[:40]
        layout_hash = str(layout_hash or "")[:64]
        if not map_id or not layout_hash:
            return {"ok": False, "message": "mapId/layoutHash fehlt"}
        if self.known_hash(map_id) == layout_hash:
            return {"ok": True, "known": True}
        parts = max(1, min(200, int(parts)))
        part = max(0, min(parts - 1, int(part)))
        with self._lock:
            key = (map_id, layout_hash)
            up = self._uploads.get(key)
            if up is None or time.time() - up["t"] > 300.0:
                up = {"t": time.time(), "parts": parts, "got": set(), "circles": [], "segments": [], "boxes": []}
                self._uploads[key] = up
            if part not in up["got"]:
                up["got"].add(part)
                for k in ("circles", "segments", "boxes"):
                    arr = body.get(k) or []
                    if isinstance(arr, list):
                        up[k].extend(a for a in arr[:4000] if isinstance(a, list))
            up["t"] = time.time()
            if len(up["got"]) < up["parts"]:
                return {"ok": True, "received": len(up["got"]), "parts": up["parts"]}
            self._uploads.pop(key, None)
            total = len(up["circles"]) + len(up["segments"]) + len(up["boxes"])
            if total < 20 or total > 250000:
                return {"ok": False, "message": f"Unplausible Hindernisanzahl ({total})"}
            known = self.known_hash(map_id)
            if known and known != layout_hash:
                # Map-Aenderung erst uebernehmen, wenn sie ein zweites Mal identisch gemeldet wird
                # (schuetzt vor Fehl-/Zufallsdaten einzelner Clients und vor staendigem Vergessen)
                pend = self._pending_layout.get(map_id)
                if not pend or pend != layout_hash:
                    self._pending_layout[map_id] = layout_hash
                    print(f"[BotNav] Moegliche Map-Aenderung fuer {map_id} gemeldet – warte auf Bestaetigung.", flush=True)
                    return {"ok": True, "pending": True}
                self._pending_layout.pop(map_id, None)
            data = {
                "mapId": map_id,
                "layoutHash": layout_hash,
                "createdAt": int(time.time()),
                "circles": up["circles"],
                "segments": up["segments"],
                "boxes": up["boxes"],
            }
            self.maps[map_id] = MapObstacles(map_id, data)
            # Neue/geaenderte Karte -> komplettes Navigations-Gedaechtnis dieser Map vergessen & neu lernen
            self.forget_map(map_id, layout_hash, reason="Neues Map-Layout empfangen")
            try:
                path = self._obstacle_path(map_id)
                with open(path + ".tmp", "w", encoding="utf-8") as fh:
                    json.dump(data, fh, separators=(",", ":"))
                os.replace(path + ".tmp", path)
            except OSError as e:
                print(f"[BotNav] Hindernis-Karte konnte nicht gespeichert werden: {e}", flush=True)
            print(f"[BotNav] Neue Hindernis-Karte für {map_id}: {self.maps[map_id].count} Objekte", flush=True)
            return {"ok": True, "stored": True, "objects": self.maps[map_id].count}

    # ------------------------------------------------------------------ Gedächtnis
    def forget_map(self, map_id: str, new_layout_hash: str, reason: str = "Map veraendert"):
        """Map wurde umgebaut: gelernte Sperrstellen & Umwege dieser Map vergessen -> Bots lernen neu."""
        old_cells = len(self.memory.get(map_id, {}))
        old_detours = len(self.detours.get(map_id, {}))
        self.memory.pop(map_id, None)
        self.detours.pop(map_id, None)
        self.memory_layout[map_id] = new_layout_hash
        self.generation[map_id] = self.generation.get(map_id, 0) + 1
        self._mem_dirty = True
        print(
            f"[BotNav] {reason}: {map_id} -> Gedaechtnis zurueckgesetzt "
            f"({old_cells} Sperrstellen, {old_detours} Umwege vergessen), Bots lernen neu.",
            flush=True,
        )

    @staticmethod
    def _ckey(ix: int, iz: int) -> str:
        return f"{ix},{iz}"

    def _mem_blocked(self, map_id: str, ix: int, iz: int) -> bool:
        cells = self.memory.get(map_id)
        if not cells:
            return False
        v = cells.get(self._ckey(ix, iz))
        return bool(v) and _f(v.get("w")) >= 1.0

    def remember_blocked(self, map_id: str, x: float, z: float, radius_cells: int = 1):
        if map_id in self.maps:
            self.memory_layout.setdefault(map_id, self.maps[map_id].layout_hash)
        cells = self.memory.setdefault(map_id, {})
        ix0, iz0 = int(math.floor(x / NAV_CELL)), int(math.floor(z / NAV_CELL))
        now = time.time()
        for dx in range(-radius_cells, radius_cells + 1):
            for dz in range(-radius_cells, radius_cells + 1):
                k = self._ckey(ix0 + dx, iz0 + dz)
                v = cells.get(k)
                if v is None:
                    v = {"w": 0.0, "t": now, "n": 0}
                    cells[k] = v
                    self.stats["learnedBlocks"] += 1
                v["w"] = min(3.0, _f(v.get("w")) + (1.0 if dx == 0 and dz == 0 else 0.5))
                v["t"] = now
                v["n"] = int(v.get("n", 0)) + 1
        if len(cells) > 60000:
            for k in sorted(cells, key=lambda kk: _f(cells[kk].get("t")))[:10000]:
                cells.pop(k, None)
        self.stats["stuckEvents"] += 1
        self._mem_dirty = True

    def _blocked_cell(self, mo: Optional[MapObstacles], map_id: str, ix: int, iz: int) -> bool:
        if mo is not None and mo.cell_blocked(ix, iz):
            return True
        return self._mem_blocked(map_id, ix, iz)

    def is_point_blocked(self, map_id: str, x: float, z: float, pad: float = AGENT_PAD) -> bool:
        mo = self.maps.get(map_id)
        if mo is not None and mo.point_blocked(x, z, pad):
            return True
        return self._mem_blocked(map_id, int(math.floor(x / NAV_CELL)), int(math.floor(z / NAV_CELL)))

    def has_data(self, map_id: str) -> bool:
        return map_id in self.maps or bool(self.memory.get(map_id))

    # ------------------------------------------------------------------ Geometrie
    def segment_clear(self, map_id: str, ax: float, az: float, bx: float, bz: float, pad: float = AGENT_PAD) -> bool:
        d = math.hypot(bx - ax, bz - az)
        if d < 0.01:
            return not self.is_point_blocked(map_id, bx, bz, pad)
        n = max(1, int(d / 0.8))
        for i in range(1, n + 1):
            t = i / n
            if self.is_point_blocked(map_id, ax + (bx - ax) * t, az + (bz - az) * t, pad):
                return False
        return True

    def resolve_step(self, map_id: str, cx: float, cz: float, nx: float, nz: float) -> Tuple[float, float, bool]:
        """Verhindert das Durchlaufen von Hindernissen; gleitet an Wänden entlang."""
        if not self.has_data(map_id):
            return nx, nz, False
        if not self.is_point_blocked(map_id, nx, nz, AGENT_PAD * 0.7):
            return nx, nz, False
        # Bot steht bereits (z.B. durch alte Position) im Hindernis -> herauslaufen erlauben
        if self.is_point_blocked(map_id, cx, cz, AGENT_PAD * 0.7):
            return nx, nz, False
        if not self.is_point_blocked(map_id, nx, cz, AGENT_PAD * 0.7):
            return nx, cz, True
        if not self.is_point_blocked(map_id, cx, nz, AGENT_PAD * 0.7):
            return cx, nz, True
        return cx, cz, True

    # ------------------------------------------------------------------ A*-Pfadsuche
    def _nearest_free(self, mo, map_id: str, ix: int, iz: int, max_r: int = 8) -> Optional[Tuple[int, int]]:
        if not self._blocked_cell(mo, map_id, ix, iz):
            return ix, iz
        for r in range(1, max_r + 1):
            best = None
            for dx in range(-r, r + 1):
                for dz in (-r, r) if abs(dx) != r else range(-r, r + 1):
                    if not self._blocked_cell(mo, map_id, ix + dx, iz + dz):
                        dd = dx * dx + dz * dz
                        if best is None or dd < best[0]:
                            best = (dd, ix + dx, iz + dz)
            if best:
                return best[1], best[2]
        return None

    def find_path(self, map_id: str, sx: float, sz: float, gx: float, gz: float) -> Optional[List[Tuple[float, float]]]:
        mo = self.maps.get(map_id)
        s = (int(math.floor(sx / NAV_CELL)), int(math.floor(sz / NAV_CELL)))
        g0 = (int(math.floor(gx / NAV_CELL)), int(math.floor(gz / NAV_CELL)))
        s_free = self._nearest_free(mo, map_id, *s, max_r=3) or s
        g = self._nearest_free(mo, map_id, *g0)
        if g is None:
            return None
        self.stats["plans"] += 1
        margin = 22
        minx, maxx = min(s_free[0], g[0]) - margin, max(s_free[0], g[0]) + margin
        minz, maxz = min(s_free[1], g[1]) - margin, max(s_free[1], g[1]) + margin
        SQ2 = 1.41421356
        open_h = [(0.0, 0.0, s_free)]
        came: Dict[Tuple[int, int], Tuple[int, int]] = {}
        gcost = {s_free: 0.0}
        closed = set()
        expanded = 0
        dirs = ((1, 0, 1.0), (-1, 0, 1.0), (0, 1, 1.0), (0, -1, 1.0), (1, 1, SQ2), (1, -1, SQ2), (-1, 1, SQ2), (-1, -1, SQ2))
        found = False
        while open_h and expanded < MAX_ASTAR_NODES:
            _f_, gc, cur = heapq.heappop(open_h)
            if cur in closed:
                continue
            if cur == g:
                found = True
                break
            closed.add(cur)
            expanded += 1
            for dx, dz, cst in dirs:
                nb = (cur[0] + dx, cur[1] + dz)
                if nb[0] < minx or nb[0] > maxx or nb[1] < minz or nb[1] > maxz or nb in closed:
                    continue
                if self._blocked_cell(mo, map_id, nb[0], nb[1]):
                    continue
                if dx and dz and (
                    self._blocked_cell(mo, map_id, cur[0] + dx, cur[1]) or self._blocked_cell(mo, map_id, cur[0], cur[1] + dz)
                ):
                    continue  # keine Ecken schneiden
                ng = gc + cst
                if ng < gcost.get(nb, 1e18):
                    gcost[nb] = ng
                    came[nb] = cur
                    hx, hz = abs(nb[0] - g[0]), abs(nb[1] - g[1])
                    h = (hx + hz) + (SQ2 - 2.0) * min(hx, hz)
                    heapq.heappush(open_h, (ng + h * 1.05, ng, nb))
        if not found:
            self.stats["planFails"] += 1
            return None
        cells = [g]
        while cells[-1] != s_free:
            cells.append(came[cells[-1]])
        cells.reverse()
        pts = [((c[0] + 0.5) * NAV_CELL, (c[1] + 0.5) * NAV_CELL) for c in cells]
        return self._smooth(map_id, sx, sz, pts)

    def _smooth(self, map_id: str, sx: float, sz: float, pts: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
        if not pts:
            return pts
        out: List[Tuple[float, float]] = []
        ax, az = sx, sz
        i = 0
        n = len(pts)
        while i < n:
            j = n - 1
            while j > i and not self.segment_clear(map_id, ax, az, pts[j][0], pts[j][1], AGENT_PAD * 0.85):
                j -= 1
            out.append(pts[j])
            ax, az = pts[j]
            i = j + 1
        return out

    # ------------------------------------------------------------------ Steuerung pro Charakter
    def next_waypoint(self, p: dict, map_id: str, cx: float, cz: float, tx: float, tz: float, now: float) -> Tuple[float, float]:
        """Liefert den nächsten Zwischenpunkt Richtung (tx, tz) unter Umgehung von Hindernissen."""
        if not self.has_data(map_id):
            return tx, tz
        nav = p.get("_nav")
        gen = self.generation.get(map_id, 0)
        if not isinstance(nav, dict) or nav.get("map") != map_id or nav.get("gen") != gen:
            nav = {"map": map_id, "gen": gen, "goal": None, "path": [], "planAt": 0.0}
            p["_nav"] = nav

        # Aktiver Umweg: Wegpunkte abarbeiten
        goal = nav.get("goal")
        if goal and abs(goal[0] - tx) < 4.0 and abs(goal[1] - tz) < 4.0 and nav.get("path"):
            path = nav["path"]
            while path and math.hypot(path[0][0] - cx, path[0][1] - cz) < 1.3:
                path.pop(0)
            if path:
                # Abkürzung: Ziel wieder direkt frei sichtbar?
                if math.hypot(tx - cx, tz - cz) < LOOKAHEAD and self.segment_clear(map_id, cx, cz, tx, tz):
                    nav["path"] = []
                    return tx, tz
                return path[0]

        d = math.hypot(tx - cx, tz - cz)
        if d < 0.5:
            return tx, tz
        look = min(d, LOOKAHEAD)
        lx = cx + (tx - cx) / d * look
        lz = cz + (tz - cz) / d * look
        if self.segment_clear(map_id, cx, cz, lx, lz):
            nav["path"] = []
            nav["goal"] = None
            return tx, tz

        # Blockiert -> Umweg planen (gedrosselt), Zwischenziel max. PLAN_HORIZON entfernt
        if now - float(nav.get("planAt", 0.0)) < 0.6 and nav.get("goal"):
            return nav["path"][0] if nav.get("path") else (tx, tz)
        nav["planAt"] = now
        hz_d = min(d, PLAN_HORIZON)
        hx = cx + (tx - cx) / d * hz_d
        hz = cz + (tz - cz) / d * hz_d

        dkey = f"{int(cx // 8)},{int(cz // 8)}>{int(hx // 8)},{int(hz // 8)}"
        mem = self.detours.get(map_id, {}).get(dkey)
        path = None
        if mem and mem.get("path"):
            cand = [tuple(pt) for pt in mem["path"]]
            if cand and self.segment_clear(map_id, cx, cz, cand[0][0], cand[0][1]):
                path = cand
                mem["t"] = time.time()
                mem["n"] = int(mem.get("n", 0)) + 1
                self.stats["detourReuse"] += 1
        if path is None:
            path = self.find_path(map_id, cx, cz, hx, hz)
            if path:
                self.detours.setdefault(map_id, {})[dkey] = {
                    "path": [[round(a, 1), round(b, 1)] for a, b in path],
                    "t": time.time(),
                    "n": 1,
                }
                self._mem_dirty = True
        nav["goal"] = (tx, tz)
        nav["path"] = list(path) if path else []
        if nav["path"]:
            p["navDetours"] = int(p.get("navDetours", 0)) + 1
            return nav["path"][0]
        return tx, tz

    def report_progress(self, p: dict, map_id: str, cx: float, cz: float, nx: float, nz: float,
                        step: float, dt: float, blocked: bool) -> bool:
        """Erkennt Feststecken & lernt daraus. Gibt True zurück, wenn neu geplant werden soll."""
        moved = math.hypot(nx - cx, nz - cz)
        nav = p.get("_nav")
        if not isinstance(nav, dict):
            nav = {"map": map_id, "goal": None, "path": [], "planAt": 0.0}
            p["_nav"] = nav
        if step > 0.05 and moved < step * 0.3:
            nav["stuck"] = float(nav.get("stuck", 0.0)) + dt
        else:
            nav["stuck"] = max(0.0, float(nav.get("stuck", 0.0)) - dt * 0.5)
        if nav.get("stuck", 0.0) >= 0.9:
            nav["stuck"] = 0.0
            ang = float(p.get("rot_y", 0.0))
            self.remember_blocked(map_id, cx + math.sin(ang) * 1.6, cz + math.cos(ang) * 1.6, 1)
            nav["path"] = []
            nav["goal"] = None
            nav["planAt"] = 0.0
            p["navStuckLearned"] = int(p.get("navStuckLearned", 0)) + 1
            return True
        return False
