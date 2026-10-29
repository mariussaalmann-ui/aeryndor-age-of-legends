# -*- coding: utf-8 -*-
"""
AERYNDOR: LEGACY OF THE MONOLITHS - Transaktionssichere Persistenzschicht (SQLite / PostgreSQL-ready)
Verwaltet Spielerprofile, Inventar, Ausrüstung, Lager, Schmied-Upgrades, Runenweberin-Boni
und persistente Offlineshops mit atomarer Item-Reservierung.
"""

import json
import os
import sqlite3
import threading
import time
import uuid
from typing import Dict, List, Optional, Tuple

from game_data import (
    CHARACTER_CLASSES,
    CLASS_ALLOWED_WEAPONS,
    CLASS_STARTER_ARMOR,
    CLASS_STARTER_WEAPON,
    DEFAULT_DROP_FILTER,
    ITEM_TEMPLATES,
    MAX_PET_LEVEL,
    MAX_PET_STAT_POINTS,
    PASSIVE_SKILL_DEFS,
    PET_SKILL_DEFS,
    QUEST_TEMPLATES,
    calculate_item_effective_stats,
    get_item_slot_size,
    get_required_pet_exp,
)

DB_LOCK = threading.RLock()

INV_COLS = 8
INV_ROWS = 15
INV_PAGE_ROWS = 15
INV_MAX_PAGES = 1
INV_PAGE_SLOTS = INV_COLS * INV_ROWS
INV_TOTAL_SLOTS = INV_COLS * INV_ROWS  # 120 Slots pro Kategorie (8x15 Raster, synchron mit Client-UI)


def get_item_category(template_id: str) -> int:
    """Ordnet ein Item den 4 Kategorien des Legacy-of-the-Monoliths-Inventars zu:
    0 = NORMAL, 1 = UPPITEMS, 2 = FERTIGKEITEN, 3 = KOSTÜME
    """
    tpl = ITEM_TEMPLATES.get(template_id, {})
    itype = tpl.get("type", "equipment")
    slot = str(tpl.get("slot") or "")
    if slot == "costume" or slot.startswith("costume_"):
        return 3
    if template_id in ("book_skill", "mat_soul_stone", "item_soul_fragment") or str(template_id).startswith("fb_") or itype in ("skill_book", "passive_skill_book"):
        return 2
    if itype == "material":
        return 1
    return 0


class GameDatabase:
    def __init__(self, db_path: str):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_db()
        self._seed_demo_offline_shops()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA journal_mode = WAL;")
        return conn

    @staticmethod
    def _can_place_at(occupied: set, slot_idx: int, size_y: int) -> bool:
        if slot_idx < 0 or slot_idx >= INV_TOTAL_SLOTS:
            return False
        row = slot_idx // INV_COLS
        if row + size_y > INV_ROWS:
            return False
        for r in range(size_y):
            if (slot_idx + r * INV_COLS) in occupied:
                return False
        return True

    @staticmethod
    def _mark_occupied(occupied: set, slot_idx: int, size_y: int):
        for r in range(size_y):
            occupied.add(slot_idx + r * INV_COLS)

    @classmethod
    def _first_free_slot(cls, occupied: set, size_y: int) -> int:
        for row in range(INV_ROWS - size_y + 1):
            for col in range(INV_COLS):
                cand = row * INV_COLS + col
                if cls._can_place_at(occupied, cand, size_y):
                    return cand
        return -1

    def _normalize_category_and_find_slot(
        self, conn: sqlite3.Connection, player_id: str, category: int, needed_size_y: int = 0
    ) -> int:
        """Stellt sicher, dass alle Items einer Kategorie ihre vertikale Slot-Größe (1, 2 oder 3 Slots)
        im 5x8-Raster ohne Überlappung einnehmen, und gibt optional den nächsten freien Slot zurück."""
        rows = conn.execute(
            """
            SELECT item_uid, template_id, slot_index
            FROM inventory_items
            WHERE player_id = ? AND category = ? AND equipped_slot IS NULL
            ORDER BY slot_index ASC, created_at ASC
            """,
            (player_id, category),
        ).fetchall()

        occupied = set()
        dirty = False
        for r in rows:
            sz = get_item_slot_size(r["template_id"])
            s_idx = int(r["slot_index"])
            if self._can_place_at(occupied, s_idx, sz):
                self._mark_occupied(occupied, s_idx, sz)
            else:
                new_slot = self._first_free_slot(occupied, sz)
                if new_slot >= 0:
                    self._mark_occupied(occupied, new_slot, sz)
                    conn.execute(
                        "UPDATE inventory_items SET slot_index = ? WHERE item_uid = ?",
                        (new_slot, r["item_uid"]),
                    )
                    dirty = True

        if dirty:
            conn.commit()

        if needed_size_y > 0:
            return self._first_free_slot(occupied, needed_size_y)
        return 0

    def _init_db(self):
        with DB_LOCK:
            conn = self._connect()
            try:
                conn.executescript(
                    """
                    CREATE TABLE IF NOT EXISTS players (
                        player_id TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        class_id TEXT NOT NULL DEFAULT 'warrior',
                        gender TEXT NOT NULL DEFAULT 'male',
                        level INTEGER NOT NULL DEFAULT 1,
                        exp INTEGER NOT NULL DEFAULT 0,
                        hp INTEGER NOT NULL DEFAULT 950,
                        max_hp INTEGER NOT NULL DEFAULT 950,
                        mp INTEGER NOT NULL DEFAULT 260,
                        max_mp INTEGER NOT NULL DEFAULT 260,
                        vit INTEGER NOT NULL DEFAULT 16,
                        int_stat INTEGER NOT NULL DEFAULT 4,
                        str INTEGER NOT NULL DEFAULT 18,
                        dex INTEGER NOT NULL DEFAULT 12,
                        stat_points INTEGER NOT NULL DEFAULT 0,
                        skill_points INTEGER NOT NULL DEFAULT 1,
                        yang INTEGER NOT NULL DEFAULT 3500,
                        shards INTEGER NOT NULL DEFAULT 5,
                        reputation INTEGER NOT NULL DEFAULT 1450,
                        map_id TEXT NOT NULL DEFAULT 'morgenwacht',
                        pos_x REAL NOT NULL DEFAULT 0.0,
                        pos_z REAL NOT NULL DEFAULT 58.0,
                        rot_y REAL NOT NULL DEFAULT 0.0,
                        active_mount TEXT DEFAULT NULL,
                        active_pet TEXT DEFAULT NULL,
                        skills_json TEXT NOT NULL DEFAULT '{}',
                        passives_json TEXT NOT NULL DEFAULT '{}',
                        quests_json TEXT NOT NULL DEFAULT '{}',
                        autofarm_json TEXT NOT NULL DEFAULT '{}',
                        updated_at REAL NOT NULL DEFAULT 0
                    );

                    CREATE TABLE IF NOT EXISTS inventory_items (
                        item_uid TEXT PRIMARY KEY,
                        player_id TEXT NOT NULL,
                        template_id TEXT NOT NULL,
                        category INTEGER NOT NULL DEFAULT 0,
                        slot_index INTEGER NOT NULL DEFAULT 0,
                        equipped_slot TEXT DEFAULT NULL,
                        plus_level INTEGER NOT NULL DEFAULT 0,
                        quantity INTEGER NOT NULL DEFAULT 1,
                        bonuses_json TEXT NOT NULL DEFAULT '[]',
                        locked_bonus_idx INTEGER DEFAULT -1,
                        reserved_shop_id TEXT DEFAULT NULL,
                        created_at REAL NOT NULL DEFAULT 0,
                        FOREIGN KEY (player_id) REFERENCES players(player_id) ON DELETE CASCADE
                    );

                    CREATE TABLE IF NOT EXISTS offline_shops (
                        shop_id TEXT PRIMARY KEY,
                        owner_id TEXT NOT NULL,
                        owner_name TEXT NOT NULL,
                        title TEXT NOT NULL,
                        map_id TEXT NOT NULL DEFAULT 'morgenwacht',
                        pos_x REAL NOT NULL,
                        pos_z REAL NOT NULL,
                        vault_yang INTEGER NOT NULL DEFAULT 0,
                        created_at REAL NOT NULL DEFAULT 0
                    );

                    CREATE TABLE IF NOT EXISTS offline_shop_listings (
                        listing_id TEXT PRIMARY KEY,
                        shop_id TEXT NOT NULL,
                        item_uid TEXT NOT NULL UNIQUE,
                        template_id TEXT NOT NULL,
                        plus_level INTEGER NOT NULL DEFAULT 0,
                        quantity INTEGER NOT NULL DEFAULT 1,
                        bonuses_json TEXT NOT NULL DEFAULT '[]',
                        price_yang INTEGER NOT NULL CHECK (price_yang > 0),
                        listed_at REAL NOT NULL DEFAULT 0,
                        FOREIGN KEY (shop_id) REFERENCES offline_shops(shop_id) ON DELETE CASCADE
                    );

                    CREATE TABLE IF NOT EXISTS market_sales_log (
                        sale_id TEXT PRIMARY KEY,
                        shop_id TEXT NOT NULL,
                        seller_id TEXT NOT NULL,
                        buyer_id TEXT NOT NULL,
                        buyer_name TEXT NOT NULL,
                        template_id TEXT NOT NULL,
                        plus_level INTEGER NOT NULL,
                        quantity INTEGER NOT NULL,
                        price_yang INTEGER NOT NULL,
                        sold_at REAL NOT NULL
                    );

                    CREATE TABLE IF NOT EXISTS accounts (
                        username_key TEXT PRIMARY KEY,
                        username TEXT NOT NULL,
                        password TEXT NOT NULL,
                        email TEXT NOT NULL DEFAULT '',
                        delete_code TEXT NOT NULL DEFAULT '1234',
                        coins INTEGER NOT NULL DEFAULT 250,
                        characters_json TEXT NOT NULL DEFAULT '[null,null,null,null]',
                        updated_at REAL NOT NULL DEFAULT 0
                    );
                    """
                )
                try:
                    conn.execute("ALTER TABLE accounts ADD COLUMN coins INTEGER NOT NULL DEFAULT 250;")
                except Exception:
                    pass
                self._deduplicate_player_names_conn(conn)
                self._migrate_starter_eq_plus0_conn(conn)
                self._migrate_starter_shoes_conn(conn)
                self._ensure_sa_admin_account_conn(conn)
                conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_players_unique_name ON players(LOWER(TRIM(name)));")
                conn.commit()
            finally:
                conn.close()

    @staticmethod
    def _normalize_sa_char_name(raw_name: str) -> str:
        """Stellt sicher, dass jeder Charakter des SA-Accounts ('admin') automatisch das Präfix [SA] trägt."""
        raw = str(raw_name or "").strip()
        if not raw:
            return "[SA]Admin"
        if raw.upper().startswith("[SA]"):
            base = raw[4:].strip()
            return f"[SA]{base}"[:28] if base else "[SA]Admin"
        return f"[SA]{raw}"[:28]

    def _ensure_sa_admin_account_conn(self, conn: sqlite3.Connection):
        """Richtet den offiziellen SA-Account ('admin' / Passwort '123') ein und versieht alle seine Charaktere automatisch mit [SA]."""
        now = time.time()
        row = conn.execute("SELECT * FROM accounts WHERE username_key = 'admin'").fetchone()
        if row is None:
            conn.execute(
                """
                INSERT INTO accounts (username_key, username, password, email, delete_code, coins, characters_json, updated_at)
                VALUES ('admin', 'admin', '123', 'admin@aeryndor.de', '123', 999999, '[null,null,null,null]', ?)
                """,
                (now,),
            )
            return

        try:
            chars = json.loads(row["characters_json"] or "[null,null,null,null]")
            if not isinstance(chars, list):
                chars = [None, None, None, None]
        except Exception:
            chars = [None, None, None, None]
        chars = (chars + [None, None, None, None])[:4]
        for idx, ch in enumerate(chars):
            if not isinstance(ch, dict):
                continue
            cpid = str(ch.get("playerId") or "").strip()
            cname = self._normalize_sa_char_name(ch.get("name") or "Admin")
            ch["name"] = cname
            ch["isSA"] = True
            ch["isGM"] = True
            ch["role"] = "SA"
            if not ch.get("guild") or ch.get("guild") == "Keine Gilde":
                ch["guild"] = "Serverleitung"
            if cpid:
                conn.execute(
                    "UPDATE players SET name = ? WHERE player_id = ?",
                    (cname, cpid),
                )
        conn.execute(
            """
            UPDATE accounts
            SET username = 'admin', password = '123', delete_code = '123', coins = MAX(coins, 999999),
                characters_json = ?, updated_at = ?
            WHERE username_key = 'admin'
            """,
            (json.dumps(chars, ensure_ascii=False), now),
        )

    def _migrate_starter_eq_plus0_conn(self, conn: sqlite3.Connection):
        """Setzt einmalig bei allen bisher erstellten Charakteren und Bots das gesamte Start-EQ (ab Lv. 1) auf +0."""
        starter_lv1_tpls = tuple(
            tpl_id
            for tpl_id, tpl in ITEM_TEMPLATES.items()
            if tpl.get("type") == "equipment" and int(tpl.get("reqLevel", 1) or 1) <= 1
        )
        if not starter_lv1_tpls:
            return
        placeholders = ",".join("?" for _ in starter_lv1_tpls)
        rows = conn.execute("SELECT player_id, quests_json FROM players").fetchall()
        for r in rows:
            pid = r["player_id"]
            try:
                q_dict = json.loads(r["quests_json"] or "{}")
                if not isinstance(q_dict, dict):
                    q_dict = {}
            except Exception:
                q_dict = {}
            if q_dict.get("__starter_eq_plus0_v1__"):
                continue
            q_dict["__starter_eq_plus0_v1__"] = True
            conn.execute(
                f"UPDATE inventory_items SET plus_level = 0 WHERE player_id = ? AND template_id IN ({placeholders}) AND plus_level > 0",
                (pid, *starter_lv1_tpls),
            )
            conn.execute(
                "UPDATE players SET quests_json = ? WHERE player_id = ?",
                (json.dumps(q_dict, ensure_ascii=False), pid),
            )
        conn.execute(
            f"UPDATE offline_shop_listings SET plus_level = 0 WHERE template_id IN ({placeholders}) AND plus_level > 0",
            starter_lv1_tpls,
        )

    def _migrate_starter_shoes_conn(self, conn: sqlite3.Connection):
        """Rüstet bei allen bisherigen Charakteren und Bots einmalig Lv. 1 Schuhe+0 ('shoes_wood') im 'shoes'-Slot aus, falls dieser leer ist."""
        rows = conn.execute("SELECT player_id, quests_json FROM players").fetchall()
        now = time.time()
        for r in rows:
            pid = r["player_id"]
            try:
                q_dict = json.loads(r["quests_json"] or "{}")
                if not isinstance(q_dict, dict):
                    q_dict = {}
            except Exception:
                q_dict = {}
            if q_dict.get("__starter_shoes_v1__"):
                continue
            q_dict["__starter_shoes_v1__"] = True

            has_shoes = conn.execute(
                "SELECT item_uid FROM inventory_items WHERE player_id = ? AND (equipped_slot = 'shoes' OR template_id LIKE 'shoes_%')",
                (pid,),
            ).fetchone()
            if not has_shoes:
                slot_occupied = conn.execute(
                    "SELECT item_uid FROM inventory_items WHERE player_id = ? AND equipped_slot = 'shoes'",
                    (pid,),
                ).fetchone()
                eq_slot = "shoes" if not slot_occupied else None
                conn.execute(
                    """
                    INSERT INTO inventory_items (
                        item_uid, player_id, template_id, category, slot_index,
                        equipped_slot, plus_level, quantity, bonuses_json, created_at
                    ) VALUES (?, ?, 'shoes_wood', 0, 0, ?, 0, 1, '[]', ?)
                    """,
                    (f"itm_{uuid.uuid4().hex[:12]}", pid, eq_slot, now),
                )
            conn.execute(
                "UPDATE players SET quests_json = ? WHERE player_id = ?",
                (json.dumps(q_dict, ensure_ascii=False), pid),
            )

    def _delete_player_cascade_conn(self, conn: sqlite3.Connection, pid: str):
        if not pid:
            return
        conn.execute(
            "DELETE FROM offline_shop_listings WHERE shop_id IN (SELECT shop_id FROM offline_shops WHERE owner_id = ?)",
            (pid,),
        )
        conn.execute("DELETE FROM inventory_items WHERE player_id = ?", (pid,))
        conn.execute("DELETE FROM offline_shops WHERE owner_id = ?", (pid,))
        conn.execute("DELETE FROM players WHERE player_id = ?", (pid,))

    def _deduplicate_player_names_conn(self, conn: sqlite3.Connection):
        """Bereinigt alle doppelten Spielernamen in accounts & players, sodass jeder Name global nur 1x existiert."""
        # 1. Dummy-Fallback 'hero_default' immer löschen
        self._delete_player_cascade_conn(conn, "hero_default")

        # 2. Alle vorhandenen Spieler-Metadaten für Priorisierung laden
        player_meta = {}
        for prow in conn.execute("SELECT player_id, name, level, exp, updated_at FROM players").fetchall():
            player_meta[prow["player_id"]] = (
                int(prow["level"] or 1),
                int(prow["exp"] or 0),
                float(prow["updated_at"] or 0.0),
                str(prow["name"] or "").strip(),
            )

        # 3. Account-Charakterlisten deduplizieren (jeder Name & jede playerId darf global nur 1x vorkommen)
        acc_rows = conn.execute("SELECT username_key, characters_json FROM accounts ORDER BY updated_at DESC").fetchall()
        claimed_names = {}  # lower_name -> player_id
        claimed_pids = set()
        for arow in acc_rows:
            ukey = arow["username_key"]
            try:
                chars = json.loads(arow["characters_json"] or "[null,null,null,null]")
                if not isinstance(chars, list):
                    chars = [None, None, None, None]
            except Exception:
                chars = [None, None, None, None]
            chars = (chars + [None, None, None, None])[:4]
            changed = False
            for idx, ch in enumerate(chars):
                if not isinstance(ch, dict):
                    continue
                pid = str(ch.get("playerId") or "").strip()
                cname = str(ch.get("name") or "").strip()
                if not pid or not cname or pid == "hero_default":
                    chars[idx] = None
                    changed = True
                    continue
                nkey = cname.lower()
                if pid in claimed_pids or (nkey in claimed_names and claimed_names[nkey] != pid):
                    chars[idx] = None
                    changed = True
                    continue
                if ch.get("name") != cname:
                    ch["name"] = cname
                    changed = True
                claimed_pids.add(pid)
                claimed_names[nkey] = pid
            if changed:
                conn.execute(
                    "UPDATE accounts SET characters_json = ? WHERE username_key = ?",
                    (json.dumps(chars, ensure_ascii=False), ukey),
                )

        # 4. players-Tabelle nach LOWER(TRIM(name)) gruppieren und alle Duplikate löschen
        all_players = conn.execute("SELECT player_id, name, level, exp, updated_at FROM players").fetchall()
        by_name = {}
        for prow in all_players:
            pid = prow["player_id"]
            clean_n = str(prow["name"] or "").strip()
            if not clean_n or pid == "hero_default":
                self._delete_player_cascade_conn(conn, pid)
                continue
            if prow["name"] != clean_n:
                conn.execute("UPDATE players SET name = ? WHERE player_id = ?", (clean_n, pid))
            by_name.setdefault(clean_n.lower(), []).append(prow)

        for nkey, group in by_name.items():
            if len(group) <= 1:
                continue
            # Sortiere: 1. In einem Account-Slot verankert, 2. Höchstes Level, 3. Höchste EXP, 4. Zuletzt aktualisiert
            group_sorted = sorted(
                group,
                key=lambda r: (
                    1 if (r["player_id"] in claimed_pids or claimed_names.get(nkey) == r["player_id"]) else 0,
                    int(r["level"] or 1),
                    int(r["exp"] or 0),
                    float(r["updated_at"] or 0.0),
                ),
                reverse=True,
            )
            winner = group_sorted[0]
            for dup_row in group_sorted[1:]:
                self._delete_player_cascade_conn(conn, dup_row["player_id"])

    def _is_character_name_taken_conn(
        self,
        conn: sqlite3.Connection,
        name: str,
        exclude_player_id: Optional[str] = None,
    ) -> bool:
        clean_name = (name or "").strip()
        if not clean_name:
            return True
        nkey = clean_name.lower()
        excl_pid = (exclude_player_id or "").strip()

        if excl_pid:
            prow = conn.execute(
                "SELECT player_id FROM players WHERE LOWER(TRIM(name)) = ? AND player_id != ? LIMIT 1",
                (nkey, excl_pid),
            ).fetchone()
        else:
            prow = conn.execute(
                "SELECT player_id FROM players WHERE LOWER(TRIM(name)) = ? LIMIT 1",
                (nkey,),
            ).fetchone()
        if prow is not None:
            return True

        for arow in conn.execute("SELECT characters_json FROM accounts").fetchall():
            try:
                chars = json.loads(arow["characters_json"] or "[]")
            except Exception:
                chars = []
            if not isinstance(chars, list):
                continue
            for ch in chars:
                if not isinstance(ch, dict):
                    continue
                ch_name = str(ch.get("name") or "").strip().lower()
                ch_pid = str(ch.get("playerId") or "").strip()
                if ch_name == nkey and (not excl_pid or ch_pid != excl_pid):
                    return True
        return False

    def is_character_name_taken(self, name: str, exclude_player_id: Optional[str] = None) -> bool:
        with DB_LOCK:
            conn = self._connect()
            try:
                return self._is_character_name_taken_conn(conn, name, exclude_player_id=exclude_player_id)
            finally:
                conn.close()

    def get_existing_player(self, player_id: str) -> Optional[dict]:
        pid = (player_id or "").strip()
        if not pid or pid == "hero_default":
            return None
        with DB_LOCK:
            conn = self._connect()
            try:
                row = conn.execute("SELECT * FROM players WHERE player_id = ?", (pid,)).fetchone()
                if row is None:
                    return None
                return self._hydrate_player(conn, row)
            finally:
                conn.close()

    def delete_character(self, player_id: str, account_name: Optional[str] = None) -> bool:
        pid = (player_id or "").strip()
        if not pid:
            return False
        with DB_LOCK:
            conn = self._connect()
            try:
                self._delete_player_cascade_conn(conn, pid)
                for arow in conn.execute("SELECT username_key, characters_json FROM accounts").fetchall():
                    if account_name and arow["username_key"] != account_name.strip().lower():
                        continue
                    try:
                        chars = json.loads(arow["characters_json"] or "[null,null,null,null]")
                    except Exception:
                        chars = [None, None, None, None]
                    if not isinstance(chars, list):
                        continue
                    changed = False
                    for idx, ch in enumerate(chars):
                        if isinstance(ch, dict) and str(ch.get("playerId") or "").strip() == pid:
                            chars[idx] = None
                            changed = True
                    if changed:
                        conn.execute(
                            "UPDATE accounts SET characters_json = ?, updated_at = ? WHERE username_key = ?",
                            (json.dumps(chars, ensure_ascii=False), time.time(), arow["username_key"]),
                        )
                conn.commit()
                return True
            finally:
                conn.close()

    def reset_bot_account_fresh_level1(self, player_id: str, preserved_meta: Optional[dict] = None) -> dict:
        """Löscht den Bot-Charakter inkl. sämtlicher Items, Ausrüstung, Offline-Shops & Account-Daten
        komplett aus der Datenbank und erstellt einen fabrikneuen Level-1-Charakter (nur mit +0 Start-EQ),
        während die gesammelten Langzeit-Lerndaten ('__bot_lifetime__') für die weitere Datensammlung erhalten bleiben."""
        pid = str(player_id or "").strip()
        bot_prof = self.BOT_CANONICAL_PROFILES.get(pid, {"name": pid, "class_id": "warrior", "empire": "seiryu"})
        with DB_LOCK:
            conn = self._connect()
            try:
                self._delete_player_cascade_conn(conn, pid)
                # Falls ein Bot-Account in accounts existiert, diesen ebenfalls bereinigen
                acc_key = f"bot_account_{pid.replace('bot_', '').split('_')[0]}"
                conn.execute("DELETE FROM accounts WHERE username_key = ?", (acc_key,))
                conn.commit()
            finally:
                conn.close()

        fresh_p = self.load_or_create_player(
            pid,
            name=bot_prof["name"],
            class_id=bot_prof["class_id"],
            empire=bot_prof["empire"],
            is_sa=False,
        )
        # Für die 2 berittenen Zweihand-Bots ('bot_eisensturm_mounted' / 'bot_donnerkeil_mounted')
        # die +0 Starter-Waffe auf die +0 Kriegsglefe ('glaive_iron') setzen
        if "mounted" in pid and bot_prof["class_id"] == "warrior":
            with DB_LOCK:
                conn = self._connect()
                try:
                    conn.execute(
                        "UPDATE inventory_items SET template_id = 'glaive_iron', plus_level = 0, bonuses_json = '[]' WHERE player_id = ? AND equipped_slot = 'weapon'",
                        (pid,),
                    )
                    conn.commit()
                finally:
                    conn.close()
            fresh_p = self.load_or_create_player(
                pid,
                name=bot_prof["name"],
                class_id=bot_prof["class_id"],
                empire=bot_prof["empire"],
                is_sa=False,
            )

        if isinstance(preserved_meta, dict) and preserved_meta:
            q_map = fresh_p.setdefault("quests", {})
            q_map["__bot_lifetime__"] = preserved_meta
            self.save_player_state(fresh_p)
        return fresh_p

    # Feste Marktplatz-Stellplätze für alle 12 Bots in ihrer jeweiligen Map-1-Hauptstadt
    # - Reich Seiryu (Nordost-Stadt: Zentrum x = +820.0, z = -780.0)
    # - Reich Kaeryu (Nordwest-Stadt: Zentrum x = -820.0, z = -780.0)
    BOT_CITY_SHOP_SPOTS = {
        "bot_veyron_warrior": ("morgenwacht", 806.0, -766.0, "🐉 [Bot]Veyrons Seiryu-Stadtbasar"),
        "bot_nachtklinge_ninja": ("morgenwacht", 814.0, -766.0, "🐉 [Bot]Nachtklinges Seiryu-Stadtbasar"),
        "bot_malakor_sura": ("morgenwacht", 822.0, -766.0, "🐉 [Bot]Malakors Seiryu-Stadtbasar"),
        "bot_aurelia_shaman": ("morgenwacht", 830.0, -766.0, "🐉 [Bot]Aurelias Seiryu-Stadtbasar"),
        "bot_eisensturm_mounted": ("morgenwacht", 838.0, -766.0, "🐉 [Bot]Eisensturms Seiryu-Stadtbasar"),
        "bot_lyra_ninja": ("morgenwacht", 846.0, -766.0, "🐉 [Bot]Lyras Seiryu-Stadtbasar"),
        "bot_kassian_warrior": ("morgenwacht", -838.0, -766.0, "🦁 [Bot]Kassians Kaeryu-Stadtbasar"),
        "bot_schattenfalke_ninja": ("morgenwacht", -830.0, -766.0, "🦁 [Bot]Schattenfalkes Kaeryu-Stadtbasar"),
        "bot_varon_sura": ("morgenwacht", -822.0, -766.0, "🦁 [Bot]Varons Kaeryu-Stadtbasar"),
        "bot_seraphina_shaman": ("morgenwacht", -814.0, -766.0, "🦁 [Bot]Seraphinas Kaeryu-Stadtbasar"),
        "bot_donnerkeil_mounted": ("morgenwacht", -806.0, -766.0, "🦁 [Bot]Donnerkeils Kaeryu-Stadtbasar"),
        "bot_draven_sura": ("morgenwacht", -798.0, -766.0, "🦁 [Bot]Dravens Kaeryu-Stadtbasar"),
    }

    def relocate_or_cleanup_offline_shops(self):
        """Schließt alle verwaisten/wilden Shops außerhalb der Städte und verschiebt alle Bot-Shops
        geordnet auf den Marktplatz ihrer jeweiligen Map-1-Hauptstadt (Seiryu Nordost / Kaeryu Nordwest)."""
        with DB_LOCK:
            conn = self._connect()
            try:
                conn.execute("BEGIN IMMEDIATE")
                rows = conn.execute("SELECT * FROM offline_shops").fetchall()
                for sh in rows:
                    sid = sh["shop_id"]
                    oid = str(sh["owner_id"] or "")
                    sx = float(sh["pos_x"] or 0.0)
                    sz = float(sh["pos_z"] or 0.0)

                    # 1. Bot-Shops immer fest in ihre Map-1-Hauptstadt verschieben
                    if oid in self.BOT_CITY_SHOP_SPOTS:
                        t_map, tx, tz, def_title = self.BOT_CITY_SHOP_SPOTS[oid]
                        conn.execute(
                            "UPDATE offline_shops SET map_id = ?, pos_x = ?, pos_z = ?, title = ? WHERE shop_id = ?",
                            (t_map, tx, tz, def_title, sid),
                        )
                        continue

                    # 2. NPC-Demo-Shops in Seiryu-Stadt (-758) und Kaeryu-Stadt behalten
                    if oid.startswith("npc_trader_"):
                        continue

                    # 3. Prüfe, ob ein sonstiger Shop außerhalb der Map-1-Städte (Seiryu/Kaeryu) in der Wildnis steht -> schließen!
                    in_seiryu_city = ((sx - 820.0) ** 2 + (sz - (-780.0)) ** 2) ** 0.5 <= 145.0
                    in_kaeryu_city = ((sx - (-820.0)) ** 2 + (sz - (-780.0)) ** 2) ** 0.5 <= 145.0
                    if not (in_seiryu_city or in_kaeryu_city):
                        vault = int(sh["vault_yang"] or 0)
                        if vault > 0:
                            conn.execute("UPDATE players SET yang = yang + ? WHERE player_id = ?", (vault, oid))
                        conn.execute("UPDATE inventory_items SET reserved_shop_id = NULL WHERE reserved_shop_id = ?", (sid,))
                        conn.execute("DELETE FROM offline_shop_listings WHERE shop_id = ?", (sid,))
                        conn.execute("DELETE FROM offline_shops WHERE shop_id = ?", (sid,))
                conn.commit()
            except Exception:
                conn.rollback()
            finally:
                conn.close()

    def _seed_demo_offline_shops(self):
        """Erstellt 2 persistente Händler-/Spieler-Offlineshops auf dem Marktplatz von Morgenwacht,
        damit der Spieler sofort das Offlineshop-System und die Marktsuche testen kann."""
        with DB_LOCK:
            conn = self._connect()
            try:
                cur = conn.execute("SELECT COUNT(*) AS cnt FROM offline_shops")
                if cur.fetchone()["cnt"] > 0:
                    conn.close()
                    conn = None
                    self.relocate_or_cleanup_offline_shops()
                    return

                now = time.time()
                shops = [
                    {
                        "shop_id": "shop_npc_octavio",
                        "owner_id": "npc_trader_1",
                        "owner_name": "Klingenmeister Veyron",
                        "title": "⚔️ Veyrons +6 Waffen & Upp-Basar",
                        "map_id": "morgenwacht",
                        "pos_x": 806.0,
                        "pos_z": -758.0,
                        "items": [
                            ("sword_silver", 6, 1, [{"id": "bonus_atk", "name": "Angriffswert", "value": 28, "unit": ""}, {"id": "bonus_crit", "name": "Kritischer Treffer", "value": 7, "unit": "%"}], 2400),
                            ("sword_msk", 4, 1, [{"id": "bonus_vs_metin", "name": "Stark gegen Rissmonolithen", "value": 15, "unit": "%"}], 5800),
                            ("sword_rsb", 5, 1, [{"id": "bonus_vs_monster", "name": "Stark gegen Monster", "value": 15, "unit": "%"}], 7200),
                            ("bow_horn", 5, 1, [{"id": "bonus_crit", "name": "Kritischer Treffer", "value": 10, "unit": "%"}], 3100),
                            ("scroll_blessing", 0, 3, [], 1650),
                            ("mat_wolf_claw", 0, 5, [], 450),
                        ],
                    },
                    {
                        "shop_id": "shop_npc_ariadne",
                        "owner_id": "npc_trader_2",
                        "owner_name": "Runenhändlerin Lyra",
                        "title": "🔮 Lyras Runen, Kostüme & Truhen",
                        "map_id": "morgenwacht",
                        "pos_x": 834.0,
                        "pos_z": -758.0,
                        "items": [
                            ("armor_tiger", 6, 1, [{"id": "bonus_hp", "name": "Max. TP", "value": 800, "unit": ""}], 2900),
                            ("item_bonus_changer", 0, 3, [], 1400),
                            ("item_bonus_adder", 0, 2, [], 1100),
                            ("chest_moonlight", 0, 1, [], 1950),
                        ],
                    },
                ]

                for sh in shops:
                    conn.execute(
                        """
                        INSERT INTO offline_shops (shop_id, owner_id, owner_name, title, map_id, pos_x, pos_z, vault_yang, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?)
                        """,
                        (sh["shop_id"], sh["owner_id"], sh["owner_name"], sh["title"], sh["map_id"], sh["pos_x"], sh["pos_z"], now),
                    )
                    for tpl_id, plus, qty, bonuses, price in sh["items"]:
                        item_uid = f"seed_{uuid.uuid4().hex[:12]}"
                        listing_id = f"lst_{uuid.uuid4().hex[:12]}"
                        conn.execute(
                            """
                            INSERT INTO offline_shop_listings
                            (listing_id, shop_id, item_uid, template_id, plus_level, quantity, bonuses_json, price_yang, listed_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                            (listing_id, sh["shop_id"], item_uid, tpl_id, plus, qty, json.dumps(bonuses, ensure_ascii=False), price, now),
                        )
                conn.commit()
            finally:
                if conn is not None:
                    conn.close()
        self.relocate_or_cleanup_offline_shops()

    @staticmethod
    def _build_starter_items(class_id: str) -> List[tuple]:
        w_tpl = CLASS_STARTER_WEAPON.get(class_id, "sword_broadsword")
        a_tpl = CLASS_STARTER_ARMOR.get(class_id, "armor_leather")
        return [
            # Ausgerüstet (nur das Start-EQ +0, je nach Klasse):
            (w_tpl, 0, 0, "weapon", 0, 1, []),
            (a_tpl, 0, 0, "armor", 0, 1, []),
            ("helm_wood", 0, 0, "helmet", 0, 1, []),
            ("shield_wood", 0, 0, "shield", 0, 1, []),
            ("shoes_wood", 0, 0, "shoes", 0, 1, []),
            ("necklace_wood", 0, 0, "necklace", 0, 1, []),
            ("bracelet_wood", 0, 0, "bracelet", 0, 1, []),
            ("gloves_wood", 0, 0, "gloves", 0, 1, []),
            ("earrings_wood", 0, 0, "earrings", 0, 1, []),
            # Im Inventar (nur 25x Rote Pots, 25x Blaue Pots, Pferd-Start-Siegel, Pet-Start-Siegel — keine Spezial-Items, keine Kostüme):
            ("potion_hp_small", 0, 0, None, 0, 25, []),
            ("potion_mp_medium", 0, 1, None, 0, 25, []),
            ("seal_mount_boar", 0, 2, None, 0, 1, []),
            ("seal_pet_phoenix", 0, 3, None, 0, 1, []),
        ]

    def ensure_class_starter_equipment(self, player_id: str, class_id: str) -> None:
        """Stellt beim Klassenwechsel sicher, dass Start-Waffe und Start-Rüstung zur Klasse passen."""
        w_tpl = CLASS_STARTER_WEAPON.get(class_id, "sword_broadsword")
        a_tpl = CLASS_STARTER_ARMOR.get(class_id, "armor_leather")
        starter_weapons = set(CLASS_STARTER_WEAPON.values())
        starter_armors = set(CLASS_STARTER_ARMOR.values())
        with DB_LOCK:
            conn = self._connect()
            try:
                rows = conn.execute(
                    "SELECT item_uid, template_id FROM inventory_items WHERE player_id = ?",
                    (player_id,),
                ).fetchall()
                for r in rows:
                    if r["template_id"] in starter_weapons and r["template_id"] != w_tpl:
                        conn.execute(
                            "UPDATE inventory_items SET template_id = ? WHERE item_uid = ?",
                            (w_tpl, r["item_uid"]),
                        )
                    elif r["template_id"] in starter_armors and r["template_id"] != a_tpl:
                        conn.execute(
                            "UPDATE inventory_items SET template_id = ? WHERE item_uid = ?",
                            (a_tpl, r["item_uid"]),
                        )
                conn.commit()
            finally:
                conn.close()

    BOT_CANONICAL_PROFILES = {
        "bot_veyron_warrior": {"name": "[Bot]Veyron", "class_id": "warrior", "empire": "seiryu"},
        "bot_nachtklinge_ninja": {"name": "[Bot]Nachtklinge", "class_id": "ninja", "empire": "seiryu"},
        "bot_malakor_sura": {"name": "[Bot]Malakor", "class_id": "sura", "empire": "seiryu"},
        "bot_aurelia_shaman": {"name": "[Bot]Aurelia", "class_id": "shaman", "empire": "seiryu"},
        "bot_eisensturm_mounted": {"name": "[Bot]Eisensturm", "class_id": "warrior", "empire": "seiryu"},
        "bot_lyra_ninja": {"name": "[Bot]Lyra", "class_id": "ninja", "empire": "seiryu"},
        "bot_kassian_warrior": {"name": "[Bot]Kassian", "class_id": "warrior", "empire": "kaeryu"},
        "bot_schattenfalke_ninja": {"name": "[Bot]Schattenfalke", "class_id": "ninja", "empire": "kaeryu"},
        "bot_varon_sura": {"name": "[Bot]Varon", "class_id": "sura", "empire": "kaeryu"},
        "bot_seraphina_shaman": {"name": "[Bot]Seraphina", "class_id": "shaman", "empire": "kaeryu"},
        "bot_donnerkeil_mounted": {"name": "[Bot]Donnerkeil", "class_id": "warrior", "empire": "kaeryu"},
        "bot_draven_sura": {"name": "[Bot]Draven", "class_id": "sura", "empire": "kaeryu"},
    }

    def load_or_create_player(
        self,
        player_id: str,
        name: str = "AeryndorHeld",
        class_id: str = "warrior",
        empire: str = "seiryu",
        is_sa: bool = False,
    ) -> dict:
        bot_prof = self.BOT_CANONICAL_PROFILES.get(str(player_id or ""))
        if bot_prof:
            name = bot_prof["name"]
            class_id = bot_prof["class_id"]
            empire = bot_prof["empire"]
        clean_empire = "kaeryu" if str(empire or "").lower() == "kaeryu" else "seiryu"
        clean_name = (name or "AeryndorHeld").strip()[:28] or "AeryndorHeld"
        is_sa_char = bool(
            is_sa
            or clean_name.upper().startswith("[SA]")
            or str(player_id or "").lower().startswith("hero_admin")
            or str(player_id or "").lower().startswith("char_admin")
        )
        if is_sa_char and not bot_prof:
            clean_name = self._normalize_sa_char_name(clean_name)
        with DB_LOCK:
            conn = self._connect()
            try:
                row = conn.execute("SELECT * FROM players WHERE player_id = ?", (player_id,)).fetchone()
                if row is None:
                    # Prüfe, ob bereits ein anderer Datensatz denselben Namen (case-insensitiv) belegt
                    existing_by_name = conn.execute(
                        "SELECT * FROM players WHERE LOWER(TRIM(name)) = LOWER(?) LIMIT 1",
                        (clean_name,),
                    ).fetchone()
                    if existing_by_name is not None:
                        other_pid = existing_by_name["player_id"]
                        # Prüfen, ob other_pid an einen Account gebunden ist
                        is_bound = False
                        for arow in conn.execute("SELECT characters_json FROM accounts").fetchall():
                            try:
                                achars = json.loads(arow["characters_json"] or "[]")
                            except Exception:
                                achars = []
                            if isinstance(achars, list) and any(
                                isinstance(c, dict) and str(c.get("playerId") or "").strip() == other_pid for c in achars
                            ):
                                is_bound = True
                                break
                        if not is_bound:
                            # Verwaisten Datensatz mit gleichem Namen entfernen, damit kein Duplikat entsteht
                            self._delete_player_cascade_conn(conn, other_pid)
                        else:
                            # Name gehört bereits einem aktiven Account-Charakter -> eindeutigen Namen erzwingen
                            suffix = (player_id or uuid.uuid4().hex)[-4:]
                            clean_name = f"{clean_name[:22]}_{suffix}"
                    name = clean_name
                    cdef = CHARACTER_CLASSES.get(class_id, CHARACTER_CLASSES["warrior"])
                    bstats = cdef["baseStats"]
                    battr = cdef["baseAttributes"]
                    if is_sa_char:
                        default_skills = {sk["id"]: 1 for sk in cdef["skills"]}
                    else:
                        default_skills = {sk["id"]: 1 for sk in cdef["skills"] if not sk.get("special")}
                    default_passives = {ps_id: 0 for ps_id in PASSIVE_SKILL_DEFS}
                    default_quests = {
                        q["id"]: {
                            "progress": 0,
                            "accepted": not bool(q.get("requireAccept", False)),
                            "ready": False,
                            "completed": False,
                            "claimed": False,
                        }
                        for q in QUEST_TEMPLATES
                    }
                    default_quests["__starter_eq_v3__"] = True
                    default_quests["__starter_eq_plus0_v1__"] = True
                    default_quests["__starter_shoes_v1__"] = True
                    default_quests["__passives_reset_fb_only_v2__"] = True
                    default_quests["__empire__"] = clean_empire
                    default_quests["__new_spawn_wall_v1__"] = True
                    if is_sa_char:
                        default_quests["__is_sa__"] = True
                        default_quests["__guild_name__"] = "Serverleitung"
                    # Neu erstellte Spieler starten immer in der Nähe der Stadtmauern Richtung Levelgebiet:
                    # Kaeryu: Am Osttor der Stadtmauer (-708, -772) mit Blick Richtung Westliche Kaeryu-Wiesen (-560, -680)
                    # Seiryu: Am Westtor der Stadtmauer (708, -772) mit Blick Richtung Östliche Seiryu-Wiesen (560, -680)
                    start_x = -708.0 if clean_empire == "kaeryu" else 708.0
                    start_z = -772.0
                    start_rot = 1.35 if clean_empire == "kaeryu" else -1.35
                    default_autofarm = {
                        "enabled": False,
                        "mode": "all",  # 'monsters' | 'metins' | 'all'
                        "radius": 135,
                        "prioritizeElites": True,
                        "attackBosses": True if is_sa_char else False,
                        "autoLoot": True,
                        "autoPotion": True,
                        "autoPotionHpPct": 55,
                        "autoSkills": True,
                        "retreatHpPct": 20,
                        "respectInventoryLimit": True,
                        "dropFilter": {
                            **DEFAULT_DROP_FILTER,
                            "categories": dict(DEFAULT_DROP_FILTER["categories"]),
                        },
                    }
                    now = time.time()
                    start_stat_pts = 90 if is_sa_char else 3
                    start_skill_pts = 35 if is_sa_char else 2
                    start_yang = 50000000 if is_sa_char else 3500
                    start_shards = 5000 if is_sa_char else 5
                    start_rep = 20000 if is_sa_char else 1450
                    conn.execute(
                        """
                        INSERT INTO players (
                            player_id, name, class_id, gender, level, exp, hp, max_hp, mp, max_mp,
                            vit, int_stat, str, dex, stat_points, skill_points, yang, shards, reputation,
                            map_id, pos_x, pos_z, rot_y, active_mount, active_pet,
                            skills_json, passives_json, quests_json, autofarm_json, updated_at
                        ) VALUES (?, ?, ?, 'male', 1, 0, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                                  'morgenwacht', ?, ?, ?, NULL, NULL,
                                  ?, ?, ?, ?, ?)
                        """,
                        (
                            player_id,
                            name,
                            cdef["id"],
                            bstats["hp"],
                            bstats["hp"],
                            bstats["mp"],
                            bstats["mp"],
                            battr["vit"],
                            battr["int"],
                            battr["str"],
                            battr["dex"],
                            start_stat_pts,
                            start_skill_pts,
                            start_yang,
                            start_shards,
                            start_rep,
                            start_x,
                            start_z,
                            start_rot,
                            json.dumps(default_skills),
                            json.dumps(default_passives),
                            json.dumps(default_quests),
                            json.dumps(default_autofarm),
                            now,
                        ),
                    )
                    starter_items = self._build_starter_items(cdef["id"])
                    for tpl_id, cat, s_idx, eq_slot, plus, qty, bonuses in starter_items:
                        conn.execute(
                            """
                            INSERT INTO inventory_items (
                                item_uid, player_id, template_id, category, slot_index,
                                equipped_slot, plus_level, quantity, bonuses_json, created_at
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                            (
                                f"itm_{uuid.uuid4().hex[:12]}",
                                player_id,
                                tpl_id,
                                cat,
                                s_idx,
                                eq_slot,
                                plus,
                                qty,
                                json.dumps(bonuses, ensure_ascii=False),
                                now,
                            ),
                        )
                    conn.commit()
                    row = conn.execute("SELECT * FROM players WHERE player_id = ?", (player_id,)).fetchone()
                elif str(player_id or "").startswith("bot_"):
                    needs_commit = False
                    if clean_name and row["name"] != clean_name:
                        conn.execute(
                            "UPDATE players SET name = ? WHERE player_id = ?",
                            (clean_name, player_id),
                        )
                        conn.execute(
                            "UPDATE offline_shops SET owner_name = ? WHERE owner_id = ?",
                            (clean_name, player_id),
                        )
                        needs_commit = True
                    try:
                        q_obj = json.loads(row["quests_json"] or "{}")
                    except Exception:
                        q_obj = {}
                    if q_obj.get("__empire__") != clean_empire:
                        q_obj["__empire__"] = clean_empire
                        conn.execute(
                            "UPDATE players SET quests_json = ? WHERE player_id = ?",
                            (json.dumps(q_obj), player_id),
                        )
                        needs_commit = True
                    if needs_commit:
                        conn.commit()
                        row = conn.execute("SELECT * FROM players WHERE player_id = ?", (player_id,)).fetchone()

                return self._hydrate_player(conn, row)
            finally:
                conn.close()

    def _hydrate_player(self, conn: sqlite3.Connection, row: sqlite3.Row) -> dict:
        p = dict(row)
        bot_prof = self.BOT_CANONICAL_PROFILES.get(str(p.get("player_id") or ""))
        if bot_prof:
            p["name"] = bot_prof["name"]
            p["class_id"] = bot_prof["class_id"]
        p["skills"] = json.loads(p.pop("skills_json", "{}") or "{}")
        p["passives"] = json.loads(p.pop("passives_json", "{}") or "{}")
        for ps_id in PASSIVE_SKILL_DEFS:
            p["passives"].setdefault(ps_id, 0)
        p["quests"] = json.loads(p.pop("quests_json", "{}") or "{}")
        if not p["quests"].get("__passives_reset_fb_only_v2__"):
            p["quests"]["__passives_reset_fb_only_v2__"] = True
            p["passives"] = {ps_id: 0 for ps_id in PASSIVE_SKILL_DEFS}
            conn.execute(
                "DELETE FROM inventory_items WHERE player_id = ? AND (template_id IN ('book_skill', 'chest_skill_books') OR template_id LIKE 'fb_passive_%') AND reserved_shop_id IS NULL",
                (p["player_id"],),
            )
            conn.execute(
                "UPDATE players SET passives_json = ?, quests_json = ? WHERE player_id = ?",
                (json.dumps(p["passives"]), json.dumps(p["quests"]), p["player_id"]),
            )
        p["autofarm"] = json.loads(p.pop("autofarm_json", "{}") or "{}")
        is_sa_p = bool(
            not bot_prof
            and (
                str(p.get("name") or "").upper().startswith("[SA]")
                or p["quests"].get("__is_sa__")
                or str(p.get("player_id") or "").lower().startswith("hero_admin")
                or str(p.get("player_id") or "").lower().startswith("char_admin")
            )
        )
        if is_sa_p:
            p["name"] = self._normalize_sa_char_name(p.get("name") or "Admin")
            p["isSA"] = True
            p["isGM"] = True
            p["role"] = "sa"
            p["guildName"] = "Serverleitung"
            p["quests"]["__is_sa__"] = True
            cdef_sa = CHARACTER_CLASSES.get(p.get("class_id", "warrior"), CHARACTER_CLASSES["warrior"])
            for sk_sa in cdef_sa.get("skills", []):
                p["skills"].setdefault(sk_sa["id"], 1)
        if p.get("active_pet") and p["active_pet"] != "pet_fire_phoenix":
            p["active_pet"] = "pet_fire_phoenix"
        raw_pet = p["quests"].get("__pet_profile__")
        if not isinstance(raw_pet, dict):
            raw_pet = {}
        pet_lvl = max(1, min(MAX_PET_LEVEL, int(raw_pet.get("level", 1) or 1)))
        raw_pet_skills = raw_pet.get("skills") if isinstance(raw_pet.get("skills"), dict) else {}
        norm_pet_skills = {}
        for sk_def in PET_SKILL_DEFS:
            sk_id = sk_def["id"]
            default_sk_lvl = 1 if sk_id == "auto_pickup" and not raw_pet_skills else 0
            norm_pet_skills[sk_id] = max(0, min(int(sk_def["maxLevel"]), int(raw_pet_skills.get(sk_id, default_sk_lvl) or 0)))
        p["petData"] = {
            "petId": "pet_fire_phoenix",
            "customName": str(raw_pet.get("customName") or "Grüner Smaragddrache"),
            "level": pet_lvl,
            "exp": max(0, int(raw_pet.get("exp", 0) or 0)),
            "maxExp": get_required_pet_exp(pet_lvl),
            "skillPoints": max(0, int(raw_pet.get("skillPoints", 2) if "skillPoints" in raw_pet else 2)),
            "statPoints": max(0, int(raw_pet.get("statPoints", 4) if "statPoints" in raw_pet else 4)),
            "vit": max(0, min(MAX_PET_STAT_POINTS, int(raw_pet.get("vit", 0) or 0))),
            "str": max(0, min(MAX_PET_STAT_POINTS, int(raw_pet.get("str", 0) or 0))),
            "dex": max(0, min(MAX_PET_STAT_POINTS, int(raw_pet.get("dex", 0) or 0))),
            "int": max(0, min(MAX_PET_STAT_POINTS, int(raw_pet.get("int", 0) or 0))),
            "skills": norm_pet_skills,
            "cooldowns": dict(raw_pet.get("cooldowns")) if isinstance(raw_pet.get("cooldowns"), dict) else {},
        }
        p["quests"]["__pet_profile__"] = p["petData"]
        p["completedDungeons"] = list(p["quests"].get("__completed_dungeons__", []))
        if bot_prof:
            p["empire"] = bot_prof["empire"]
            p["quests"]["__empire__"] = bot_prof["empire"]
        else:
            p["empire"] = p["quests"].get("__empire__") or ("kaeryu" if float(p.get("pos_x", 708.0)) < 0.0 else "seiryu")
        p["isDead"] = bool(p["quests"].get("__is_dead__", False)) or int(p.get("hp", 1)) <= 0
        p["deadAt"] = float(p["quests"].get("__dead_at__", 0.0) or 0.0)
        if p["isDead"] and p["deadAt"] <= 0.0:
            p["deadAt"] = time.time()

        # Synchronisiere alle Quests aus QUEST_TEMPLATES für neue und bestehende Charaktere
        bio_bonuses = p["quests"].get("__biologist_bonuses__")
        if not isinstance(bio_bonuses, dict):
            bio_bonuses = {}
        for qtpl in QUEST_TEMPLATES:
            qid = qtpl["id"]
            req_accept = bool(qtpl.get("requireAccept", False))
            if qid not in p["quests"] or not isinstance(p["quests"][qid], dict):
                p["quests"][qid] = {
                    "progress": 0,
                    "accepted": not req_accept,
                    "ready": False,
                    "completed": False,
                    "claimed": False,
                }
            else:
                qst = p["quests"][qid]
                qst.setdefault("progress", 0)
                qst.setdefault("completed", False)
                qst.setdefault("claimed", bool(qst.get("completed", False)))
                if qst.get("completed"):
                    qst["accepted"] = True
                    qst["ready"] = False
                    if qtpl.get("category") == "biologist" and isinstance(qtpl.get("biologistBonus"), dict):
                        bio_bonuses[qid] = dict(qtpl["biologistBonus"])
                else:
                    if req_accept and int(qst.get("progress", 0)) == 0 and not qst.get("userAccepted", False) and qid in ("q_hunt_wolves", "q_slay_bandits"):
                        qst["accepted"] = False
                    else:
                        qst.setdefault("accepted", not req_accept)
                    qst.setdefault("ready", int(qst.get("progress", 0)) >= int(qtpl.get("required", 1)))
        p["quests"]["__biologist_bonuses__"] = bio_bonuses

        # Stelle sicher, dass jedes Spielerprofil ein vollständiges Drop-Filter-Objekt besitzt
        raw_df = p["autofarm"].get("dropFilter")
        if not isinstance(raw_df, dict):
            raw_df = {}
        merged_cats = dict(DEFAULT_DROP_FILTER["categories"])
        if isinstance(raw_df.get("categories"), dict):
            for ck, cv in raw_df["categories"].items():
                if ck in merged_cats:
                    merged_cats[ck] = bool(cv)
        merged_df = dict(DEFAULT_DROP_FILTER)
        for dk, dv in raw_df.items():
            if dk != "categories" and dk in merged_df:
                merged_df[dk] = dv
        merged_df["categories"] = merged_cats
        p["autofarm"]["dropFilter"] = merged_df

        # Migriere veralteten Kostüm-Slot-Namen (costume -> costume_armor)
        conn.execute(
            "UPDATE inventory_items SET equipped_slot = 'costume_armor', category = 3 WHERE player_id = ? AND equipped_slot = 'costume'",
            (p["player_id"],),
        )

        # Einmalige Migration auf das neue saubere Start-Equipment (+0 Holz-Set, 25x Rote/Blaue Pots, Start-Mount/Pet-Siegel, keine Spezial-Items, keine Kostüme)
        if not p["quests"].get("__starter_eq_v3__"):
            p["quests"]["__starter_eq_v3__"] = True
            p["quests"]["__starter_eq_plus0_v1__"] = True
            conn.execute("DELETE FROM inventory_items WHERE player_id = ?", (p["player_id"],))
            now_mig = time.time()
            for tpl_id, cat, s_idx, eq_slot, plus, qty, bonuses in self._build_starter_items(p.get("class_id", "warrior")):
                conn.execute(
                    """
                    INSERT INTO inventory_items (
                        item_uid, player_id, template_id, category, slot_index,
                        equipped_slot, plus_level, quantity, bonuses_json, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        f"itm_{uuid.uuid4().hex[:12]}",
                        p["player_id"],
                        tpl_id,
                        cat,
                        s_idx,
                        eq_slot,
                        plus,
                        qty,
                        json.dumps(bonuses, ensure_ascii=False),
                        now_mig,
                    ),
                )
            conn.execute(
                "UPDATE players SET quests_json = ?, active_mount = NULL, active_pet = NULL WHERE player_id = ?",
                (json.dumps(p["quests"]), p["player_id"]),
            )
            p["active_mount"] = None
            p["active_pet"] = None
        elif not p["quests"].get("__starter_eq_plus0_v1__"):
            p["quests"]["__starter_eq_plus0_v1__"] = True
            starter_lv1_tpls = tuple(
                tpl_id
                for tpl_id, tpl in ITEM_TEMPLATES.items()
                if tpl.get("type") == "equipment" and int(tpl.get("reqLevel", 1) or 1) <= 1
            )
            if starter_lv1_tpls:
                placeholders = ",".join("?" for _ in starter_lv1_tpls)
                conn.execute(
                    f"UPDATE inventory_items SET plus_level = 0 WHERE player_id = ? AND template_id IN ({placeholders}) AND plus_level > 0",
                    (p["player_id"], *starter_lv1_tpls),
                )
            conn.execute(
                "UPDATE players SET quests_json = ? WHERE player_id = ?",
                (json.dumps(p["quests"]), p["player_id"]),
            )

        if not p["quests"].get("__starter_shoes_v1__"):
            p["quests"]["__starter_shoes_v1__"] = True
            has_shoes = conn.execute(
                "SELECT item_uid FROM inventory_items WHERE player_id = ? AND (equipped_slot = 'shoes' OR template_id LIKE 'shoes_%')",
                (p["player_id"],),
            ).fetchone()
            if not has_shoes:
                slot_occupied = conn.execute(
                    "SELECT item_uid FROM inventory_items WHERE player_id = ? AND equipped_slot = 'shoes'",
                    (p["player_id"],),
                ).fetchone()
                eq_slot = "shoes" if not slot_occupied else None
                conn.execute(
                    """
                    INSERT INTO inventory_items (
                        item_uid, player_id, template_id, category, slot_index,
                        equipped_slot, plus_level, quantity, bonuses_json, created_at
                    ) VALUES (?, ?, 'shoes_wood', 0, 0, ?, 0, 1, '[]', ?)
                    """,
                    (f"itm_{uuid.uuid4().hex[:12]}", p["player_id"], eq_slot, time.time()),
                )
            conn.execute(
                "UPDATE players SET quests_json = ? WHERE player_id = ?",
                (json.dumps(p["quests"], ensure_ascii=False), p["player_id"]),
            )

        conn.commit()

        # Alle 4 Inventar-Kategorien auf gültige 2D-Multi-Slot-Positionen (1x1, 1x2, 1x3) normalisieren
        for cat_idx in range(4):
            self._normalize_category_and_find_slot(conn, p["player_id"], cat_idx, 0)

        items_rows = conn.execute(
            "SELECT * FROM inventory_items WHERE player_id = ? ORDER BY category ASC, slot_index ASC, created_at ASC",
            (p["player_id"],),
        ).fetchall()
        inventory = []
        equipment = {}
        for ir in items_rows:
            item_dict = self._format_item_row(ir)
            if item_dict["equippedSlot"]:
                equipment[item_dict["equippedSlot"]] = item_dict
            else:
                inventory.append(item_dict)

        p["inventory"] = inventory
        p["equipment"] = equipment
        return p

    def _format_item_row(self, ir: sqlite3.Row) -> dict:
        d = dict(ir)
        tpl = ITEM_TEMPLATES.get(d["template_id"], {})
        bonuses = json.loads(d.get("bonuses_json", "[]") or "[]")
        for b in bonuses:
            if isinstance(b, dict) and b.get("name") == "Doppel-Yang-Chance":
                b["name"] = "Doppel-Gold-Chance"
        plus = int(d.get("plus_level", 0))
        eff_stats = calculate_item_effective_stats(d["template_id"], plus, bonuses)
        slot_size = get_item_slot_size(d["template_id"])
        return {
            "uid": d["item_uid"],
            "templateId": d["template_id"],
            "name": tpl.get("name", d["template_id"]),
            "type": tpl.get("type", "material"),
            "slot": tpl.get("slot", None),
            "weaponSubType": tpl.get("weaponSubType", None),
            "classes": tpl.get("classes", None),
            "slotSize": slot_size,
            "rarity": tpl.get("rarity", "common"),
            "reqLevel": tpl.get("reqLevel", 1),
            "icon": tpl.get("icon", "rusty_sword"),
            "customIcon": tpl.get("customIcon", None),
            "mountId": tpl.get("mountId", None),
            "petId": tpl.get("petId", None),
            "weaponVisual": tpl.get("weaponVisual", None),
            "category": d["category"],
            "slotIndex": d["slot_index"],
            "equippedSlot": d["equipped_slot"],
            "plusLevel": plus,
            "quantity": d["quantity"],
            "bonuses": bonuses,
            "lockedBonusIdx": d.get("locked_bonus_idx", -1),
            "reservedShopId": d.get("reserved_shop_id", None),
            "effectiveStats": eff_stats,
            "sellPrice": tpl.get("sellPrice", 50) * (1 + plus),
            "stackable": tpl.get("stackable", False),
            "description": tpl.get("description", ""),
        }

    def save_player_state(self, p: dict):
        if not p or p.get("player_id") == "hero_default":
            return
        with DB_LOCK:
            conn = self._connect()
            try:
                pid = str(p["player_id"]).strip()
                desired_name = str(p.get("name") or "").strip()[:28] or "AeryndorHeld"
                collision = conn.execute(
                    "SELECT player_id FROM players WHERE LOWER(TRIM(name)) = LOWER(?) AND player_id != ? LIMIT 1",
                    (desired_name, pid),
                ).fetchone()
                if collision is not None:
                    cur_row = conn.execute("SELECT name FROM players WHERE player_id = ?", (pid,)).fetchone()
                    if cur_row and cur_row["name"]:
                        desired_name = str(cur_row["name"]).strip()
                    else:
                        desired_name = f"{desired_name[:22]}_{pid[-4:]}"
                p["name"] = desired_name
                q_dict = p.setdefault("quests", {})
                if isinstance(p.get("petData"), dict):
                    q_dict["__pet_profile__"] = p["petData"]
                if "completedDungeons" in p:
                    q_dict["__completed_dungeons__"] = list(p["completedDungeons"])
                if "empire" in p and p["empire"]:
                    q_dict["__empire__"] = str(p["empire"])
                q_dict["__is_dead__"] = bool(p.get("isDead", False))
                q_dict["__dead_at__"] = float(p.get("deadAt", 0.0) or 0.0)
                conn.execute(
                    """
                    UPDATE players SET
                        name = ?, class_id = ?, gender = ?, level = ?, exp = ?,
                        hp = ?, max_hp = ?, mp = ?, max_mp = ?,
                        vit = ?, int_stat = ?, str = ?, dex = ?,
                        stat_points = ?, skill_points = ?,
                        yang = ?, shards = ?, reputation = ?,
                        map_id = ?, pos_x = ?, pos_z = ?, rot_y = ?,
                        active_mount = ?, active_pet = ?,
                        skills_json = ?, passives_json = ?, quests_json = ?, autofarm_json = ?,
                        updated_at = ?
                    WHERE player_id = ?
                    """,
                    (
                        p["name"],
                        p["class_id"],
                        p.get("gender", "male"),
                        p["level"],
                        p["exp"],
                        int(p["hp"]),
                        int(p["max_hp"]),
                        int(p["mp"]),
                        int(p["max_mp"]),
                        p["vit"],
                        p["int_stat"],
                        p["str"],
                        p["dex"],
                        p["stat_points"],
                        p["skill_points"],
                        int(p["yang"]),
                        int(p["shards"]),
                        int(p["reputation"]),
                        p["map_id"],
                        float(p["pos_x"]),
                        float(p["pos_z"]),
                        float(p.get("rot_y", 0.0)),
                        p.get("active_mount"),
                        p.get("active_pet"),
                        json.dumps(p.get("skills", {})),
                        json.dumps(p.get("passives", {})),
                        json.dumps(p.get("quests", {})),
                        json.dumps(p.get("autofarm", {})),
                        time.time(),
                        p["player_id"],
                    ),
                )
                conn.commit()
            finally:
                conn.close()

    def add_item_to_inventory(
        self, player_id: str, template_id: str, quantity: int = 1, plus_level: int = 0, bonuses: list = None
    ) -> Tuple[bool, str]:
        tpl = ITEM_TEMPLATES.get(template_id)
        if not tpl:
            return False, "Unbekannter Gegenstand."
        cat = get_item_category(template_id)
        size_y = get_item_slot_size(template_id)
        with DB_LOCK:
            conn = self._connect()
            try:
                if tpl.get("stackable", False):
                    existing = conn.execute(
                        """
                        SELECT item_uid, quantity FROM inventory_items
                        WHERE player_id = ? AND template_id = ? AND equipped_slot IS NULL AND reserved_shop_id IS NULL
                        LIMIT 1
                        """,
                        (player_id, template_id),
                    ).fetchone()
                    if existing:
                        conn.execute(
                            "UPDATE inventory_items SET quantity = quantity + ? WHERE item_uid = ?",
                            (quantity, existing["item_uid"]),
                        )
                        conn.commit()
                        return True, tpl["name"]

                # Finde freien vertikalen Multi-Slot (1x1, 1x2 oder 1x3) im 5x8-Raster
                free_slot = self._normalize_category_and_find_slot(conn, player_id, cat, size_y)
                if free_slot < 0:
                    return False, f"Kein freier {size_y}-Slot-Platz im Inventar!"

                uid = f"itm_{uuid.uuid4().hex[:12]}"
                conn.execute(
                    """
                    INSERT INTO inventory_items (
                        item_uid, player_id, template_id, category, slot_index,
                        equipped_slot, plus_level, quantity, bonuses_json, created_at
                    ) VALUES (?, ?, ?, ?, ?, NULL, ?, ?, ?, ?)
                    """,
                    (
                        uid,
                        player_id,
                        template_id,
                        cat,
                        free_slot,
                        plus_level,
                        quantity,
                        json.dumps(bonuses or [], ensure_ascii=False),
                        time.time(),
                    ),
                )
                conn.commit()
                return True, tpl["name"]
            finally:
                conn.close()

    def consume_item_by_template(self, player_id: str, template_id: str, count: int = 1) -> bool:
        with DB_LOCK:
            conn = self._connect()
            try:
                rows = conn.execute(
                    """
                    SELECT item_uid, quantity FROM inventory_items
                    WHERE player_id = ? AND template_id = ? AND equipped_slot IS NULL AND reserved_shop_id IS NULL
                    ORDER BY quantity ASC
                    """,
                    (player_id, template_id),
                ).fetchall()
                total = sum(r["quantity"] for r in rows)
                if total < count:
                    return False
                rem = count
                for r in rows:
                    if rem <= 0:
                        break
                    take = min(rem, r["quantity"])
                    if take >= r["quantity"]:
                        conn.execute("DELETE FROM inventory_items WHERE item_uid = ?", (r["item_uid"],))
                    else:
                        conn.execute(
                            "UPDATE inventory_items SET quantity = quantity - ? WHERE item_uid = ?",
                            (take, r["item_uid"]),
                        )
                    rem -= take
                conn.commit()
                return True
            finally:
                conn.close()

    def equip_or_unequip_item(
        self,
        player_id: str,
        item_uid: str,
        player_level: int,
        target_slot: Optional[str] = None,
        target_inv_slot: Optional[int] = None,
    ) -> Tuple[bool, str]:
        with DB_LOCK:
            conn = self._connect()
            try:
                item = conn.execute(
                    "SELECT * FROM inventory_items WHERE item_uid = ? AND player_id = ?",
                    (item_uid, player_id),
                ).fetchone()
                if not item:
                    return False, "Gegenstand nicht gefunden."
                if item["reserved_shop_id"]:
                    return False, "Gegenstand ist im Offlineshop reserviert!"

                tpl = ITEM_TEMPLATES.get(item["template_id"], {})
                slot = tpl.get("slot")
                if not slot:
                    return False, "Dieser Gegenstand kann nicht ausgerüstet werden."
                if target_slot and target_slot != slot:
                    return False, f"Dieser Gegenstand passt nicht in diesen Slot!"
                prow_check = conn.execute("SELECT name, quests_json FROM players WHERE player_id = ?", (player_id,)).fetchone()
                is_sa_eq = bool(
                    prow_check
                    and (
                        str(prow_check["name"] or "").upper().startswith("[SA]")
                        or '"__is_sa__": true' in str(prow_check["quests_json"] or "")
                    )
                )
                if not is_sa_eq and player_level < tpl.get("reqLevel", 1):
                    return False, f"Benötigt Charakter-Level {tpl.get('reqLevel', 1)}!"

                if not item["equipped_slot"] and slot == "weapon":
                    prow = conn.execute("SELECT class_id FROM players WHERE player_id = ?", (player_id,)).fetchone()
                    p_class = str(prow["class_id"] if prow else "warrior")
                    w_sub = str(tpl.get("weaponSubType") or "one_hand")
                    allowed_subs = CLASS_ALLOWED_WEAPONS.get(p_class, ["one_hand"])
                    allowed_classes = tpl.get("classes")
                    if (allowed_classes and p_class not in allowed_classes) or (w_sub not in allowed_subs):
                        if w_sub == "two_hand":
                            return False, "⚠️ Nur der Klingenwächter kann Zweihandwaffen tragen!"
                        if w_sub in ("dagger", "bow"):
                            return False, "⚠️ Nur der Schattenjäger kann Dolche und Bögen tragen!"
                        if w_sub in ("staff", "bell", "fan"):
                            return False, "⚠️ Nur der Seelenweber kann Stäbe tragen!"
                        if p_class == "sura":
                            return False, "⚠️ Der Runenmagier kann ausschließlich Einhand-Schwerter tragen!"
                        if p_class == "shaman":
                            return False, "⚠️ Der Seelenweber trägt ausschließlich Stäbe!"
                        return False, "⚠️ Deine Klasse kann diesen Waffentyp nicht tragen!"

                cat = int(item["category"])
                size_y = get_item_slot_size(item["template_id"])

                if item["equipped_slot"]:
                    # Wenn per Drag & Drop auf denselben Ausrüstungs-Slot gezogen wurde, nichts tun
                    if target_slot and target_slot == item["equipped_slot"]:
                        return True, f"{tpl.get('name')} ist bereits in diesem Slot ausgerüstet."

                    # Ablegen in gewünschten oder nächsten freien Multi-Slot
                    dest_slot = -1
                    if target_inv_slot is not None and 0 <= int(target_inv_slot) < INV_TOTAL_SLOTS:
                        rows = conn.execute(
                            "SELECT item_uid, template_id, slot_index FROM inventory_items WHERE player_id = ? AND category = ? AND equipped_slot IS NULL",
                            (player_id, cat),
                        ).fetchall()
                        occupied = set()
                        for r in rows:
                            self._mark_occupied(occupied, int(r["slot_index"]), get_item_slot_size(r["template_id"]))
                        if self._can_place_at(occupied, int(target_inv_slot), size_y):
                            dest_slot = int(target_inv_slot)

                    if dest_slot < 0:
                        dest_slot = self._normalize_category_and_find_slot(conn, player_id, cat, size_y)
                    if dest_slot < 0:
                        return False, f"Kein freier {size_y}-Slot-Platz im Inventar zum Ablegen!"
                    conn.execute(
                        "UPDATE inventory_items SET equipped_slot = NULL, slot_index = ? WHERE item_uid = ?",
                        (dest_slot, item_uid),
                    )
                    conn.commit()
                    return True, f"{tpl.get('name')} abgelegt."
                else:
                    # Neues Item zuerst ausrüsten (damit sein bisheriger Inventarplatz frei wird),
                    # dann das zuvor ausgerüstete Item in einen freien Multi-Slot legen
                    prev_equipped = conn.execute(
                        "SELECT item_uid, template_id, category FROM inventory_items WHERE player_id = ? AND equipped_slot = ?",
                        (player_id, slot),
                    ).fetchall()
                    conn.execute(
                        "UPDATE inventory_items SET equipped_slot = ? WHERE item_uid = ?",
                        (slot, item_uid),
                    )
                    for prev in prev_equipped:
                        if prev["item_uid"] == item_uid:
                            continue
                        prev_cat = int(prev["category"])
                        prev_sz = get_item_slot_size(prev["template_id"])
                        free_slot = self._normalize_category_and_find_slot(conn, player_id, prev_cat, prev_sz)
                        conn.execute(
                            "UPDATE inventory_items SET equipped_slot = NULL, slot_index = ? WHERE item_uid = ?",
                            (max(0, free_slot), prev["item_uid"]),
                        )
                    conn.commit()
                    plus_str = f" +{item['plus_level']}" if int(item["plus_level"] or 0) > 0 else ""
                    return True, f"{tpl.get('name')}{plus_str} ausgerüstet!"
            finally:
                conn.close()

    def move_inventory_item(self, player_id: str, item_uid: str, target_slot_index: int) -> Tuple[bool, str]:
        with DB_LOCK:
            conn = self._connect()
            try:
                item = conn.execute(
                    "SELECT * FROM inventory_items WHERE item_uid = ? AND player_id = ?",
                    (item_uid, player_id),
                ).fetchone()
                if not item:
                    return False, "Gegenstand nicht gefunden."
                if item["reserved_shop_id"]:
                    return False, "Gegenstand ist im Offlineshop reserviert!"

                tpl = ITEM_TEMPLATES.get(item["template_id"], {})
                cat = int(item["category"])
                size_y = get_item_slot_size(item["template_id"])
                target_slot_index = max(0, min(INV_TOTAL_SLOTS - 1, int(target_slot_index)))

                rows = conn.execute(
                    "SELECT item_uid, template_id, slot_index FROM inventory_items WHERE player_id = ? AND category = ? AND equipped_slot IS NULL AND item_uid != ?",
                    (player_id, cat, item_uid),
                ).fetchall()
                occupied = set()
                for r in rows:
                    self._mark_occupied(occupied, int(r["slot_index"]), get_item_slot_size(r["template_id"]))

                if not self._can_place_at(occupied, target_slot_index, size_y):
                    return False, "Ziel-Slot im Inventar ist belegt oder bietet nicht genug Platz!"

                conn.execute(
                    "UPDATE inventory_items SET equipped_slot = NULL, slot_index = ? WHERE item_uid = ?",
                    (target_slot_index, item_uid),
                )
                conn.commit()
                return True, f"{tpl.get('name', 'Gegenstand')} verschoben."
            finally:
                conn.close()

    def update_item_upgrade_and_bonuses(
        self, item_uid: str, plus_level: int, bonuses: list, locked_idx: int = -1
    ):
        with DB_LOCK:
            conn = self._connect()
            try:
                conn.execute(
                    """
                    UPDATE inventory_items
                    SET plus_level = ?, bonuses_json = ?, locked_bonus_idx = ?
                    WHERE item_uid = ?
                    """,
                    (plus_level, json.dumps(bonuses, ensure_ascii=False), locked_idx, item_uid),
                )
                conn.commit()
            finally:
                conn.close()

    update_item_plus_and_bonuses = update_item_upgrade_and_bonuses

    def delete_item(self, player_id: str, item_uid: str, allow_equipped: bool = False) -> Optional[dict]:
        with DB_LOCK:
            conn = self._connect()
            try:
                if allow_equipped:
                    row = conn.execute(
                        "SELECT * FROM inventory_items WHERE item_uid = ? AND player_id = ? AND reserved_shop_id IS NULL",
                        (item_uid, player_id),
                    ).fetchone()
                else:
                    row = conn.execute(
                        "SELECT * FROM inventory_items WHERE item_uid = ? AND player_id = ? AND equipped_slot IS NULL AND reserved_shop_id IS NULL",
                        (item_uid, player_id),
                    ).fetchone()
                if not row:
                    return None
                formatted = self._format_item_row(row)
                conn.execute("DELETE FROM inventory_items WHERE item_uid = ?", (item_uid,))
                conn.commit()
                return formatted
            finally:
                conn.close()

    def sort_inventory(self, player_id: str):
        """Sortiert alle Kategorien nach Slot-Größe (3 Slots -> 2 Slots -> 1 Slot), Plus-Level & Template-ID
        und platziert sie kollisionsfrei im 5x8-Raster."""
        with DB_LOCK:
            conn = self._connect()
            try:
                rows = conn.execute(
                    """
                    SELECT item_uid, category, template_id, plus_level
                    FROM inventory_items
                    WHERE player_id = ? AND equipped_slot IS NULL
                    """,
                    (player_id,),
                ).fetchall()

                by_cat: Dict[int, list] = {0: [], 1: [], 2: [], 3: []}
                for r in rows:
                    c = int(r["category"])
                    by_cat.setdefault(c, []).append(r)

                for c, items in by_cat.items():
                    items.sort(
                        key=lambda x: (
                            -get_item_slot_size(x["template_id"]),
                            -int(x["plus_level"]),
                            str(x["template_id"]),
                        )
                    )
                    occupied = set()
                    for it in items:
                        sz = get_item_slot_size(it["template_id"])
                        slot = self._first_free_slot(occupied, sz)
                        if slot < 0:
                            slot = 0
                        self._mark_occupied(occupied, slot, sz)
                        conn.execute(
                            "UPDATE inventory_items SET slot_index = ? WHERE item_uid = ?",
                            (slot, it["item_uid"]),
                        )
                conn.commit()
            finally:
                conn.close()

    # ========================================================================
    # OFFLINESHOP-SYSTEM (Kap. 11) - Serverseitig, persistent & atomar
    # ========================================================================
    def invalidate_offline_shops_cache(self):
        self._offline_shops_cache = {}

    def list_offline_shops(self, map_id: Optional[str] = None) -> List[dict]:
        now_t = time.time()
        cache = getattr(self, "_offline_shops_cache", None)
        if cache is None:
            cache = {}
            self._offline_shops_cache = cache
        cache_key = str(map_id or "__all__")
        cached_entry = cache.get(cache_key)
        if cached_entry and (now_t - cached_entry[0]) < 1.5:
            return cached_entry[1]

        with DB_LOCK:
            conn = self._connect()
            try:
                if map_id:
                    shops = conn.execute("SELECT * FROM offline_shops WHERE map_id = ?", (map_id,)).fetchall()
                else:
                    shops = conn.execute("SELECT * FROM offline_shops").fetchall()

                result = []
                for sh in shops:
                    sdict = dict(sh)
                    listings = conn.execute(
                        "SELECT * FROM offline_shop_listings WHERE shop_id = ? ORDER BY price_yang ASC",
                        (sh["shop_id"],),
                    ).fetchall()
                    formatted_listings = []
                    for l in listings:
                        tpl = ITEM_TEMPLATES.get(l["template_id"], {})
                        bonuses = json.loads(l["bonuses_json"] or "[]")
                        plus = l["plus_level"]
                        formatted_listings.append(
                            {
                                "listingId": l["listing_id"],
                                "shopId": l["shop_id"],
                                "shopTitle": sh["title"],
                                "sellerName": sh["owner_name"],
                                "itemUid": l["item_uid"],
                                "templateId": l["template_id"],
                                "name": tpl.get("name", l["template_id"]),
                                "type": tpl.get("type", "equipment"),
                                "slot": tpl.get("slot"),
                                "weaponSubType": tpl.get("weaponSubType"),
                                "slotSize": get_item_slot_size(l["template_id"]),
                                "rarity": tpl.get("rarity", "common"),
                                "reqLevel": tpl.get("reqLevel", 1),
                                "icon": tpl.get("icon", "rusty_sword"),
                                "plusLevel": plus,
                                "quantity": l["quantity"],
                                "bonuses": bonuses,
                                "effectiveStats": calculate_item_effective_stats(l["template_id"], plus, bonuses),
                                "priceYang": l["price_yang"],
                            }
                        )
                    sdict["listings"] = formatted_listings
                    result.append(sdict)
                cache[cache_key] = (now_t, result)
                return result
            finally:
                conn.close()

    def get_top_sold_items(self, seller_id: Optional[str] = None, limit: int = 5) -> list:
        """Gibt die meistverkauften Items (nach verkaufter Menge) zurück.
        Wenn seller_id angegeben, nur für diesen Verkäufer."""
        try:
            with DB_LOCK:
                conn = self._connect()
                try:
                    if seller_id:
                        rows = conn.execute(
                            """SELECT template_id, SUM(quantity) AS total_sold, SUM(price_yang) AS total_yang
                               FROM market_sales_log
                               WHERE seller_id = ?
                               GROUP BY template_id
                               ORDER BY total_sold DESC
                               LIMIT ?""",
                            (seller_id, limit),
                        ).fetchall()
                    else:
                        rows = conn.execute(
                            """SELECT template_id, SUM(quantity) AS total_sold, SUM(price_yang) AS total_yang
                               FROM market_sales_log
                               GROUP BY template_id
                               ORDER BY total_sold DESC
                               LIMIT ?""",
                            (limit,),
                        ).fetchall()
                    result = []
                    for r in rows:
                        tid = r["template_id"]
                        tpl = ITEM_TEMPLATES.get(tid, {})
                        result.append({
                            "templateId": tid,
                            "name": tpl.get("name", tid),
                            "icon": tpl.get("icon", ""),
                            "customIcon": tpl.get("customIcon", ""),
                            "totalSold": int(r["total_sold"] or 0),
                            "totalYang": int(r["total_yang"] or 0),
                        })
                    return result
                finally:
                    conn.close()
        except Exception:
            return []

    def create_or_add_to_offline_shop(
        self, player_id: str, player_name: str, shop_title: str, map_id: str, pos_x: float, pos_z: float, item_uid: str, price_yang: int
    ) -> Tuple[bool, str]:
        if price_yang <= 0 or price_yang > 999999999:
            return False, "Ungültiger Gold-Preis (muss größer als 0 sein)."

        with DB_LOCK:
            conn = self._connect()
            try:
                conn.execute("BEGIN IMMEDIATE")
                item = conn.execute(
                    "SELECT * FROM inventory_items WHERE item_uid = ? AND player_id = ?",
                    (item_uid, player_id),
                ).fetchone()
                if not item:
                    conn.rollback()
                    return False, "Gegenstand nicht im Inventar gefunden."
                if item["equipped_slot"]:
                    conn.rollback()
                    return False, "Ausgerüstete Gegenstände müssen zuerst abgelegt werden."
                if item["reserved_shop_id"]:
                    conn.rollback()
                    return False, "Gegenstand ist bereits in einem Shop eingestellt."

                # Bots errichten ihre Offline-Shops IMMER auf dem Marktplatz ihrer eigenen Map-1-Hauptstadt (Seiryu / Kaeryu)!
                if player_id in self.BOT_CITY_SHOP_SPOTS:
                    map_id, pos_x, pos_z, city_shop_title = self.BOT_CITY_SHOP_SPOTS[player_id]
                    shop_title = city_shop_title

                shop = conn.execute("SELECT * FROM offline_shops WHERE owner_id = ?", (player_id,)).fetchone()
                now = time.time()
                if not shop:
                    shop_id = f"shop_{player_id}"
                    conn.execute(
                        """
                        INSERT INTO offline_shops (shop_id, owner_id, owner_name, title, map_id, pos_x, pos_z, vault_yang, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?)
                        """,
                        (shop_id, player_id, player_name, shop_title or f"{player_name}s Basar", map_id, pos_x, pos_z, now),
                    )
                else:
                    shop_id = shop["shop_id"]
                    if player_id in self.BOT_CITY_SHOP_SPOTS:
                        conn.execute(
                            "UPDATE offline_shops SET title = ?, map_id = ?, pos_x = ?, pos_z = ? WHERE shop_id = ?",
                            (shop_title, map_id, pos_x, pos_z, shop_id),
                        )
                    elif shop_title:
                        conn.execute("UPDATE offline_shops SET title = ? WHERE shop_id = ?", (shop_title, shop_id))

                # Reserviere das Item transaktionssicher
                conn.execute(
                    "UPDATE inventory_items SET reserved_shop_id = ? WHERE item_uid = ?",
                    (shop_id, item_uid),
                )
                listing_id = f"lst_{uuid.uuid4().hex[:12]}"
                conn.execute(
                    """
                    INSERT INTO offline_shop_listings
                    (listing_id, shop_id, item_uid, template_id, plus_level, quantity, bonuses_json, price_yang, listed_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        listing_id,
                        shop_id,
                        item_uid,
                        item["template_id"],
                        item["plus_level"],
                        item["quantity"],
                        item["bonuses_json"],
                        int(price_yang),
                        now,
                    ),
                )
                conn.commit()
                tpl = ITEM_TEMPLATES.get(item["template_id"], {})
                return True, f"{tpl.get('name', 'Item')} für {price_yang:,} Gold in deinen Offlineshop eingestellt!"
            except Exception as e:
                conn.rollback()
                return False, f"Transaktionsfehler: {e}"
            finally:
                conn.close()

    def buy_offline_shop_listing(self, buyer_id: str, buyer_name: str, listing_id: str) -> Tuple[bool, str, int]:
        """Atomarer Kauf aus einem Offlineshop: Prüft Gold, verhindert Selbstkauf/Doppelkauf, überträgt Item & schreibt Erlös gut."""
        with DB_LOCK:
            conn = self._connect()
            try:
                conn.execute("BEGIN IMMEDIATE")
                listing = conn.execute(
                    "SELECT * FROM offline_shop_listings WHERE listing_id = ?", (listing_id,)
                ).fetchone()
                if not listing:
                    conn.rollback()
                    return False, "Dieses Angebot wurde bereits verkauft.", 0

                shop = conn.execute(
                    "SELECT * FROM offline_shops WHERE shop_id = ?", (listing["shop_id"],)
                ).fetchone()
                if not shop:
                    conn.rollback()
                    return False, "Shop existiert nicht mehr.", 0

                price = int(listing["price_yang"])
                buyer = conn.execute("SELECT yang FROM players WHERE player_id = ?", (buyer_id,)).fetchone()
                if not buyer or buyer["yang"] < price:
                    conn.rollback()
                    return False, f"Nicht genug Gold! Benötigt: {price:,} Gold.", 0

                cat = get_item_category(listing["template_id"])
                size_y = get_item_slot_size(listing["template_id"])
                free_slot = self._normalize_category_and_find_slot(conn, buyer_id, cat, size_y)
                if free_slot < 0:
                    conn.rollback()
                    return False, f"Kein freier {size_y}-Slot-Platz im Inventar!", 0

                # Ziehe Yang beim Käufer ab
                conn.execute("UPDATE players SET yang = yang - ? WHERE player_id = ?", (price, buyer_id))

                # Schreibe Verkaufserlös im Shop-Tresor gut
                conn.execute(
                    "UPDATE offline_shops SET vault_yang = vault_yang + ? WHERE shop_id = ?",
                    (price, shop["shop_id"]),
                )

                # Entferne Angebot
                conn.execute("DELETE FROM offline_shop_listings WHERE listing_id = ?", (listing_id,))

                # Falls es ein echtes Spieler-Item war, lösche das reservierte Original-Item beim Verkäufer
                conn.execute("DELETE FROM inventory_items WHERE item_uid = ?", (listing["item_uid"],))

                # Erstelle das gekaufte Item beim Käufer im freien Multi-Slot
                new_uid = f"itm_{uuid.uuid4().hex[:12]}"
                conn.execute(
                    """
                    INSERT INTO inventory_items (
                        item_uid, player_id, template_id, category, slot_index,
                        equipped_slot, plus_level, quantity, bonuses_json, created_at
                    ) VALUES (?, ?, ?, ?, ?, NULL, ?, ?, ?, ?)
                    """,
                    (
                        new_uid,
                        buyer_id,
                        listing["template_id"],
                        cat,
                        free_slot,
                        listing["plus_level"],
                        listing["quantity"],
                        listing["bonuses_json"],
                        time.time(),
                    ),
                )

                # Verkaufsprotokoll schreiben
                conn.execute(
                    """
                    INSERT INTO market_sales_log
                    (sale_id, shop_id, seller_id, buyer_id, buyer_name, template_id, plus_level, quantity, price_yang, sold_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        f"sal_{uuid.uuid4().hex[:12]}",
                        shop["shop_id"],
                        shop["owner_id"],
                        buyer_id,
                        buyer_name,
                        listing["template_id"],
                        listing["plus_level"],
                        listing["quantity"],
                        price,
                        time.time(),
                    ),
                )

                conn.commit()
                tpl = ITEM_TEMPLATES.get(listing["template_id"], {})
                return True, f"{tpl.get('name', 'Item')} +{listing['plus_level']} für {price:,} Gold gekauft!", price
            except Exception as e:
                conn.rollback()
                return False, f"Kauf fehlgeschlagen: {e}", 0
            finally:
                conn.close()

    def withdraw_shop_vault(self, player_id: str) -> Tuple[bool, str, int]:
        with DB_LOCK:
            conn = self._connect()
            try:
                conn.execute("BEGIN IMMEDIATE")
                shop = conn.execute("SELECT * FROM offline_shops WHERE owner_id = ?", (player_id,)).fetchone()
                if not shop or shop["vault_yang"] <= 0:
                    conn.rollback()
                    return False, "Keine abholbaren Verkaufserlöse in deinem Offlineshop.", 0
                amount = int(shop["vault_yang"])
                conn.execute("UPDATE offline_shops SET vault_yang = 0 WHERE shop_id = ?", (shop["shop_id"],))
                conn.execute("UPDATE players SET yang = yang + ? WHERE player_id = ?", (amount, player_id))
                conn.commit()
                return True, f"{amount:,} Gold Verkaufserlös aus deinem Offlineshop abgeholt!", amount
            except Exception as e:
                conn.rollback()
                return False, str(e), 0
            finally:
                conn.close()

    def execute_direct_trade(
        self,
        player_a_id: str,
        player_b_id: str,
        uids_a: List[str],
        yang_a: int,
        uids_b: List[str],
        yang_b: int,
    ) -> Tuple[bool, str]:
        """Atomarer Direkt-Handel zwischen zwei Spielern (Items + Gold/Yang)."""
        yang_a = max(0, int(yang_a or 0))
        yang_b = max(0, int(yang_b or 0))
        with DB_LOCK:
            conn = self._connect()
            try:
                conn.execute("BEGIN IMMEDIATE")
                row_a = conn.execute("SELECT yang, name FROM players WHERE player_id = ?", (player_a_id,)).fetchone()
                row_b = conn.execute("SELECT yang, name FROM players WHERE player_id = ?", (player_b_id,)).fetchone()
                if not row_a or not row_b:
                    conn.rollback()
                    return False, "Ein Handelspartner ist nicht mehr verfügbar."
                if int(row_a["yang"]) < yang_a:
                    conn.rollback()
                    return False, f"{row_a['name']} besitzt nicht genug Gold für diesen Handel."
                if int(row_b["yang"]) < yang_b:
                    conn.rollback()
                    return False, f"{row_b['name']} besitzt nicht genug Gold für diesen Handel."

                items_a = []
                for uid in uids_a:
                    it = conn.execute(
                        "SELECT * FROM inventory_items WHERE item_uid = ? AND player_id = ?",
                        (uid, player_a_id),
                    ).fetchone()
                    if not it or it["equipped_slot"] or it["reserved_shop_id"]:
                        conn.rollback()
                        return False, f"Ein angebotener Gegenstand von {row_a['name']} ist nicht mehr handelbar."
                    items_a.append(dict(it))

                items_b = []
                for uid in uids_b:
                    it = conn.execute(
                        "SELECT * FROM inventory_items WHERE item_uid = ? AND player_id = ?",
                        (uid, player_b_id),
                    ).fetchone()
                    if not it or it["equipped_slot"] or it["reserved_shop_id"]:
                        conn.rollback()
                        return False, f"Ein angebotener Gegenstand von {row_b['name']} ist nicht mehr handelbar."
                    items_b.append(dict(it))

                # Entferne zuerst alle angebotenen Items aus den Ursprungs-Inventaren
                for it in items_a:
                    conn.execute("DELETE FROM inventory_items WHERE item_uid = ?", (it["item_uid"],))
                for it in items_b:
                    conn.execute("DELETE FROM inventory_items WHERE item_uid = ?", (it["item_uid"],))

                now_t = time.time()

                # Übertrage Items von A -> B
                for it in items_a:
                    tpl_id = it["template_id"]
                    cat = get_item_category(tpl_id)
                    size_y = get_item_slot_size(tpl_id)
                    free_slot = self._normalize_category_and_find_slot(conn, player_b_id, cat, size_y)
                    if free_slot < 0:
                        conn.rollback()
                        return False, f"Das Inventar von {row_b['name']} hat nicht genug freie Plätze!"
                    conn.execute(
                        """
                        INSERT INTO inventory_items (
                            item_uid, player_id, template_id, category, slot_index,
                            equipped_slot, plus_level, quantity, bonuses_json, locked_bonus_idx, created_at
                        ) VALUES (?, ?, ?, ?, ?, NULL, ?, ?, ?, ?, ?)
                        """,
                        (
                            it["item_uid"],
                            player_b_id,
                            tpl_id,
                            cat,
                            free_slot,
                            it["plus_level"],
                            it["quantity"],
                            it["bonuses_json"],
                            it.get("locked_bonus_idx", -1),
                            now_t,
                        ),
                    )

                # Übertrage Items von B -> A
                for it in items_b:
                    tpl_id = it["template_id"]
                    cat = get_item_category(tpl_id)
                    size_y = get_item_slot_size(tpl_id)
                    free_slot = self._normalize_category_and_find_slot(conn, player_a_id, cat, size_y)
                    if free_slot < 0:
                        conn.rollback()
                        return False, f"Das Inventar von {row_a['name']} hat nicht genug freie Plätze!"
                    conn.execute(
                        """
                        INSERT INTO inventory_items (
                            item_uid, player_id, template_id, category, slot_index,
                            equipped_slot, plus_level, quantity, bonuses_json, locked_bonus_idx, created_at
                        ) VALUES (?, ?, ?, ?, ?, NULL, ?, ?, ?, ?, ?)
                        """,
                        (
                            it["item_uid"],
                            player_a_id,
                            tpl_id,
                            cat,
                            free_slot,
                            it["plus_level"],
                            it["quantity"],
                            it["bonuses_json"],
                            it.get("locked_bonus_idx", -1),
                            now_t,
                        ),
                    )

                # Gold/Yang verrechnen
                if yang_a > 0 or yang_b > 0:
                    conn.execute(
                        "UPDATE players SET yang = yang - ? + ? WHERE player_id = ?",
                        (yang_a, yang_b, player_a_id),
                    )
                    conn.execute(
                        "UPDATE players SET yang = yang - ? + ? WHERE player_id = ?",
                        (yang_b, yang_a, player_b_id),
                    )

                conn.commit()
                return True, "🤝 Handel erfolgreich abgeschlossen!"
            except Exception as e:
                conn.rollback()
                return False, f"Handelsfehler: {e}"
            finally:
                conn.close()

    def authenticate_or_sync_account(
        self,
        username: str,
        password: str,
        client_account_obj: Optional[dict] = None,
        is_register: bool = False,
        email: str = "",
        delete_code: str = "1234",
    ) -> Tuple[bool, str, Optional[dict]]:
        uname = (username or "").strip()
        ukey = uname.lower()
        pw = (password or "").strip()
        if len(uname) < 2 or len(uname) > 24:
            return False, "⚠️ Bitte gültigen Accountnamen (2–24 Zeichen) eingeben.", None
        if any(ch in uname for ch in ("<", ">", '"', "'", "`", ";", "\\", "/", "\x00")):
            return False, "⚠️ Accountname enthält unerlaubte Sonderzeichen.", None
        if ukey == "admin" and pw not in ("123", "9274"):
            return False, "⚠️ Ungültiges Passwort für SA-Account (admin / 123).", None
        clean_email = (email or "").strip()[:80]
        if any(ch in clean_email for ch in ("<", ">", '"', "'", "`", ";", "\x00")):
            clean_email = ""
        clean_code = "".join(ch for ch in str(delete_code or "1234") if ch.isdigit())[:4] or ("123" if ukey == "admin" else "1234")

        with DB_LOCK:
            conn = self._connect()
            try:
                row = conn.execute(
                    "SELECT * FROM accounts WHERE username_key = ?", (ukey,)
                ).fetchone()

                if is_register:
                    if row is not None:
                        return False, "⚠️ Dieser Accountname ist bereits vergeben!", None
                    if len(pw) < 1:
                        return False, "⚠️ Bitte gib ein Passwort ein.", None
                    chars = [None, None, None, None]
                    if isinstance(client_account_obj, dict) and isinstance(client_account_obj.get("characters"), list):
                        raw_chars = (client_account_obj["characters"] + [None, None, None, None])[:4]
                        seen_local = set()
                        for idx, ch in enumerate(raw_chars):
                            if not isinstance(ch, dict):
                                continue
                            cname = str(ch.get("name") or "").strip()
                            if ukey == "admin" and cname:
                                cname = self._normalize_sa_char_name(cname)
                                ch["isSA"] = True
                                ch["isGM"] = True
                                ch["role"] = "SA"
                                ch["guild"] = "Serverleitung"
                            cpid = str(ch.get("playerId") or "").strip()
                            if not cname or not cpid or cname.lower() in seen_local:
                                continue
                            if self._is_character_name_taken_conn(conn, cname, exclude_player_id=cpid):
                                continue
                            seen_local.add(cname.lower())
                            ch["name"] = cname
                            chars[idx] = ch
                    acc_obj = {
                        "username": uname,
                        "email": clean_email or f"{ukey}@aeryndor.de",
                        "deleteCode": clean_code,
                        "characters": chars,
                        "isSA": ukey == "admin",
                    }
                    conn.execute(
                        """
                        INSERT INTO accounts (username_key, username, password, email, delete_code, characters_json, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (ukey, uname, "123" if ukey == "admin" else pw, acc_obj["email"], acc_obj["deleteCode"], json.dumps(chars, ensure_ascii=False), time.time()),
                    )
                    conn.commit()
                    return True, "Account erfolgreich registriert.", acc_obj

                if row is None:
                    # Migration bestehender lokaler Accounts beim ersten Login auf dem Server
                    chars = [None, None, None, None]
                    if isinstance(client_account_obj, dict) and isinstance(client_account_obj.get("characters"), list):
                        raw_chars = (client_account_obj["characters"] + [None, None, None, None])[:4]
                        seen_local = set()
                        for idx, ch in enumerate(raw_chars):
                            if not isinstance(ch, dict):
                                continue
                            cname = str(ch.get("name") or "").strip()
                            if ukey == "admin" and cname:
                                cname = self._normalize_sa_char_name(cname)
                                ch["isSA"] = True
                                ch["isGM"] = True
                                ch["role"] = "SA"
                                ch["guild"] = "Serverleitung"
                            cpid = str(ch.get("playerId") or "").strip()
                            if not cname or not cpid or cname.lower() in seen_local:
                                continue
                            if self._is_character_name_taken_conn(conn, cname, exclude_player_id=cpid):
                                continue
                            seen_local.add(cname.lower())
                            ch["name"] = cname
                            chars[idx] = ch
                    acc_obj = {
                        "username": uname,
                        "email": (client_account_obj or {}).get("email") or f"{ukey}@aeryndor.de",
                        "deleteCode": "123" if ukey == "admin" else ((client_account_obj or {}).get("deleteCode") or "1234"),
                        "characters": chars,
                        "isSA": ukey == "admin",
                    }
                    conn.execute(
                        """
                        INSERT INTO accounts (username_key, username, password, email, delete_code, characters_json, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (ukey, uname, "123" if ukey == "admin" else pw, acc_obj["email"], acc_obj["deleteCode"], json.dumps(chars, ensure_ascii=False), time.time()),
                    )
                    conn.commit()
                    return True, "Erfolgreich eingeloggt.", acc_obj

                stored_pw = str(row["password"] or "")
                if ukey == "admin":
                    if pw not in ("123", "9274"):
                        return False, "⚠️ Falsches Passwort für SA-Account (admin / 123)!", None
                elif stored_pw and pw != stored_pw:
                    return False, "⚠️ Falsches Passwort für diesen Account!", None

                try:
                    srv_chars = json.loads(row["characters_json"] or "[null,null,null,null]")
                    if not isinstance(srv_chars, list):
                        srv_chars = [None, None, None, None]
                except Exception:
                    srv_chars = [None, None, None, None]
                srv_chars = (srv_chars + [None, None, None, None])[:4]

                # Falls der Server-Account noch keine Charaktere hat, aber der Client lokale Charaktere mitbringt, zusammenführen (nur eindeutige Namen!)
                if not any(srv_chars) and isinstance(client_account_obj, dict) and isinstance(client_account_obj.get("characters"), list):
                    cli_chars = (client_account_obj["characters"] + [None, None, None, None])[:4]
                    filtered_cli = [None, None, None, None]
                    seen_local = set()
                    for idx, ch in enumerate(cli_chars):
                        if not isinstance(ch, dict):
                            continue
                        cname = str(ch.get("name") or "").strip()
                        if ukey == "admin" and cname:
                            cname = self._normalize_sa_char_name(cname)
                            ch["isSA"] = True
                            ch["isGM"] = True
                            ch["role"] = "SA"
                            ch["guild"] = "Serverleitung"
                        cpid = str(ch.get("playerId") or "").strip()
                        if not cname or not cpid or cname.lower() in seen_local:
                            continue
                        if self._is_character_name_taken_conn(conn, cname, exclude_player_id=cpid):
                            continue
                        seen_local.add(cname.lower())
                        ch["name"] = cname
                        filtered_cli[idx] = ch
                    if any(filtered_cli):
                        srv_chars = filtered_cli
                        conn.execute(
                            "UPDATE accounts SET characters_json = ?, updated_at = ? WHERE username_key = ?",
                            (json.dumps(srv_chars, ensure_ascii=False), time.time(), ukey),
                        )
                        conn.commit()

                # Level & Standort der Charaktere live aus der players-Tabelle aktualisieren
                dirty_chars = False
                for idx, ch in enumerate(srv_chars):
                    if isinstance(ch, dict) and ch.get("playerId"):
                        if ukey == "admin":
                            norm_n = self._normalize_sa_char_name(ch.get("name") or "Admin")
                            if ch.get("name") != norm_n or not ch.get("isSA"):
                                ch["name"] = norm_n
                                ch["isSA"] = True
                                ch["isGM"] = True
                                ch["role"] = "SA"
                                ch["guild"] = "Serverleitung"
                                dirty_chars = True
                        prow = conn.execute(
                            "SELECT level, map_id, name, class_id FROM players WHERE player_id = ?",
                            (ch["playerId"],),
                        ).fetchone()
                        if prow:
                            new_lvl = int(prow["level"] or 1)
                            if ch.get("level") != new_lvl:
                                ch["level"] = new_lvl
                                dirty_chars = True
                            db_name = str(prow["name"] or "").strip()
                            if ukey == "admin" and db_name:
                                db_name = self._normalize_sa_char_name(db_name)
                                if prow["name"] != db_name:
                                    conn.execute("UPDATE players SET name = ? WHERE player_id = ?", (db_name, ch["playerId"]))
                            if db_name and ch.get("name") != db_name:
                                ch["name"] = db_name
                                dirty_chars = True
                if dirty_chars:
                    conn.execute(
                        "UPDATE accounts SET characters_json = ?, updated_at = ? WHERE username_key = ?",
                        (json.dumps(srv_chars, ensure_ascii=False), time.time(), ukey),
                    )
                    conn.commit()

                acc_obj = {
                    "username": row["username"] or uname,
                    "email": row["email"] or f"{ukey}@aeryndor.de",
                    "deleteCode": "123" if ukey == "admin" else (row["delete_code"] or "1234"),
                    "characters": srv_chars,
                    "isSA": ukey == "admin",
                }
                return True, "Erfolgreich eingeloggt.", acc_obj
            finally:
                conn.close()

    def save_account_characters(
        self, username: str, characters: list, delete_code: Optional[str] = None
    ) -> Tuple[bool, str, list]:
        uname = (username or "").strip()
        ukey = uname.lower()
        if not ukey:
            return False, "Ungültiger Account.", [None, None, None, None]
        raw_chars = (list(characters or []) + [None, None, None, None])[:4]
        with DB_LOCK:
            conn = self._connect()
            try:
                row = conn.execute(
                    "SELECT username_key, characters_json FROM accounts WHERE username_key = ?", (ukey,)
                ).fetchone()
                if not row:
                    return False, "Account nicht gefunden.", raw_chars

                try:
                    old_chars = json.loads(row["characters_json"] or "[null,null,null,null]")
                    if not isinstance(old_chars, list):
                        old_chars = [None, None, None, None]
                except Exception:
                    old_chars = [None, None, None, None]
                old_chars = (old_chars + [None, None, None, None])[:4]
                old_pids = {
                    str(c.get("playerId") or "").strip()
                    for c in old_chars
                    if isinstance(c, dict) and str(c.get("playerId") or "").strip()
                }

                # Validiere Namens-Eindeutigkeit für alle Slots
                clean_chars = [None, None, None, None]
                seen_names = set()
                new_pids = set()
                conflict_msg = None
                for idx, ch in enumerate(raw_chars):
                    if not isinstance(ch, dict):
                        continue
                    cpid = str(ch.get("playerId") or "").strip()
                    cname = str(ch.get("name") or "").strip()[:28]
                    if not cpid or not cname:
                        continue
                    if ukey == "admin":
                        cname = self._normalize_sa_char_name(cname)
                        ch["isSA"] = True
                        ch["isGM"] = True
                        ch["role"] = "SA"
                        if not ch.get("guild") or ch.get("guild") == "Keine Gilde":
                            ch["guild"] = "Serverleitung"
                    nkey = cname.lower()
                    if nkey in seen_names or self._is_character_name_taken_conn(conn, cname, exclude_player_id=cpid):
                        conflict_msg = f"⚠️ Der Spielername „{cname}“ ist auf dem Server bereits vergeben!"
                        # Alten Slot beibehalten, falls er gültig war
                        if isinstance(old_chars[idx], dict):
                            old_pid_slot = str(old_chars[idx].get("playerId") or "").strip()
                            old_name_slot = str(old_chars[idx].get("name") or "").strip().lower()
                            if (
                                old_pid_slot
                                and old_name_slot not in seen_names
                                and not self._is_character_name_taken_conn(conn, old_name_slot, exclude_player_id=old_pid_slot)
                            ):
                                clean_chars[idx] = old_chars[idx]
                                seen_names.add(old_name_slot)
                                new_pids.add(old_pid_slot)
                        continue
                    seen_names.add(nkey)
                    new_pids.add(cpid)
                    ch["name"] = cname
                    clean_chars[idx] = ch
                    if ukey == "admin":
                        conn.execute("UPDATE players SET name = ? WHERE player_id = ?", (cname, cpid))

                # Gelöschte Charaktere dieses Accounts auch aus der players-Tabelle löschen, damit der Name wieder frei wird
                for removed_pid in old_pids - new_pids:
                    self._delete_player_cascade_conn(conn, removed_pid)

                if delete_code:
                    conn.execute(
                        "UPDATE accounts SET characters_json = ?, delete_code = ?, updated_at = ? WHERE username_key = ?",
                        (json.dumps(clean_chars, ensure_ascii=False), delete_code, time.time(), ukey),
                    )
                else:
                    conn.execute(
                        "UPDATE accounts SET characters_json = ?, updated_at = ? WHERE username_key = ?",
                        (json.dumps(clean_chars, ensure_ascii=False), time.time(), ukey),
                    )
                conn.commit()
                if conflict_msg:
                    return False, conflict_msg, clean_chars
                return True, "Charaktere synchronisiert.", clean_chars
            finally:
                conn.close()

    def get_homepage_stats(self, online_players: Optional[dict] = None) -> dict:
        """Liefert Live-Statistiken und die Top-30-Rangliste für die offizielle Aeryndor-Homepage."""
        online_map = online_players or {}
        now = time.time()
        with DB_LOCK:
            conn = self._connect()
            try:
                acc_cnt = conn.execute("SELECT COUNT(*) AS c FROM accounts").fetchone()["c"]
                char_cnt = conn.execute(
                    "SELECT COUNT(*) AS c FROM players WHERE player_id != 'hero_default'"
                ).fetchone()["c"]
                shop_cnt = conn.execute("SELECT COUNT(*) AS c FROM offline_shops").fetchone()["c"]

                rows = conn.execute(
                    """
                    SELECT *
                    FROM players
                    WHERE player_id != 'hero_default'
                    ORDER BY level DESC, exp DESC, reputation DESC
                    LIMIT 30
                    """
                ).fetchall()

                if not rows:
                    rows = conn.execute(
                        """
                        SELECT *
                        FROM players
                        ORDER BY level DESC, exp DESC, reputation DESC
                        LIMIT 15
                        """
                    ).fetchall()

                empire_by_pid = {}
                doctrine_by_pid = {}
                guild_by_pid = {}
                acc_rows = conn.execute("SELECT characters_json FROM accounts").fetchall()
                for ar in acc_rows:
                    try:
                        ch_list = json.loads(ar["characters_json"] or "[]")
                        for ch in ch_list:
                            if isinstance(ch, dict) and ch.get("playerId"):
                                cpid = ch["playerId"]
                                raw_emp = str(ch.get("empire") or "seiryu").strip().lower()
                                empire_by_pid[cpid] = "kaeryu" if raw_emp in ("kaeryu", "dark", "shadow") else "seiryu"
                                raw_doc = ch.get("doctrineIdx", ch.get("doctrine", 0))
                                try:
                                    doctrine_by_pid[cpid] = 1 if str(raw_doc) == "1" else 0
                                except Exception:
                                    doctrine_by_pid[cpid] = 0
                                if ch.get("guild"):
                                    guild_by_pid[cpid] = str(ch.get("guild"))
                    except Exception:
                        pass

                leaderboard = []
                for idx, r in enumerate(rows):
                    pid = r["player_id"]
                    p_live = online_map.get(pid)
                    is_on = bool(
                        p_live
                        and p_live.get("online")
                        and p_live.get("inWorld", False)
                        and (now - float(p_live.get("lastSeen", 0.0) or 0.0)) <= 20.0
                    )
                    cls_id = str(r["class_id"] or "warrior")
                    if cls_id == "ninja":
                        cls_id = "assassin"
                    cls_label_map = {
                        "warrior": "Klingenwächter",
                        "assassin": "Schattenjäger",
                        "ninja": "Schattenjäger",
                        "sura": "Runenmagier",
                        "shaman": "Seelenweber",
                    }
                    emp_key = empire_by_pid.get(pid, "seiryu")
                    city_name = "Kaeryu" if emp_key == "kaeryu" else "Seiryu"

                    try:
                        raw_skills = (
                            dict(p_live["skills"])
                            if (p_live and isinstance(p_live.get("skills"), dict))
                            else json.loads(r["skills_json"] or "{}")
                        )
                    except Exception:
                        raw_skills = {}

                    try:
                        raw_passives = (
                            dict(p_live["passives"])
                            if (p_live and isinstance(p_live.get("passives"), dict))
                            else json.loads(r["passives_json"] or "{}")
                        )
                    except Exception:
                        raw_passives = {}

                    try:
                        raw_quests = (
                            dict(p_live["quests"])
                            if (p_live and isinstance(p_live.get("quests"), dict))
                            else json.loads(r["quests_json"] or "{}")
                        )
                    except Exception:
                        raw_quests = {}

                    raw_mount = (
                        p_live.get("mountData")
                        if (p_live and isinstance(p_live.get("mountData"), dict))
                        else (raw_quests.get("__mount_profile__") if isinstance(raw_quests.get("__mount_profile__"), dict) else {})
                    )
                    horse_lvl = max(1, min(50, int(raw_mount.get("level", 1) or 1)))
                    mount_info = {
                        "level": horse_lvl,
                        "dmgPoints": max(0, int(raw_mount.get("dmgPoints", 0) or 0)),
                        "hpPoints": max(0, int(raw_mount.get("hpPoints", 0) or 0)),
                        "equippedSkin": str(raw_mount.get("equippedSkin") or ""),
                    }

                    raw_pet = (
                        p_live.get("petData")
                        if (p_live and isinstance(p_live.get("petData"), dict))
                        else (raw_quests.get("__pet_profile__") if isinstance(raw_quests.get("__pet_profile__"), dict) else {})
                    )
                    raw_pet_skills = raw_pet.get("skills") if isinstance(raw_pet.get("skills"), dict) else {}
                    norm_pet_skills = {}
                    for sk_def in PET_SKILL_DEFS:
                        sk_id = sk_def["id"]
                        default_sk_lvl = 1 if sk_id == "auto_pickup" and not raw_pet_skills else 0
                        norm_pet_skills[sk_id] = max(0, min(int(sk_def["maxLevel"]), int(raw_pet_skills.get(sk_id, default_sk_lvl) or 0)))
                    pet_info = {
                        "name": str(raw_pet.get("customName") or "Grüner Smaragddrache"),
                        "level": max(1, min(120, int(raw_pet.get("level", 1) or 1))),
                        "vit": max(0, int(raw_pet.get("vit", 0) or 0)),
                        "str": max(0, int(raw_pet.get("str", 0) or 0)),
                        "dex": max(0, int(raw_pet.get("dex", 0) or 0)),
                        "int": max(0, int(raw_pet.get("int", 0) or 0)),
                        "skills": norm_pet_skills,
                    }

                    eq_items = []
                    eq_rows = conn.execute(
                        """
                        SELECT template_id, equipped_slot, plus_level, bonuses_json
                        FROM inventory_items
                        WHERE player_id = ? AND equipped_slot IS NOT NULL
                        """,
                        (pid,),
                    ).fetchall()
                    for er in eq_rows:
                        tpl = ITEM_TEMPLATES.get(er["template_id"], {})
                        try:
                            b_list = json.loads(er["bonuses_json"] or "[]")
                        except Exception:
                            b_list = []
                        eq_items.append(
                            {
                                "templateId": er["template_id"],
                                "name": tpl.get("name", er["template_id"]),
                                "slot": er["equipped_slot"],
                                "plus": int(er["plus_level"] or 0),
                                "rarity": tpl.get("rarity", "common"),
                                "icon": tpl.get("icon", ""),
                                "bonuses": b_list[:7] if isinstance(b_list, list) else [],
                            }
                        )

                    leaderboard.append(
                        {
                            "rank": idx + 1,
                            "playerId": pid,
                            "name": r["name"],
                            "classId": cls_id,
                            "className": cls_label_map.get(cls_id, "Klingenwächter"),
                            "gender": r["gender"] or "male",
                            "doctrineIdx": doctrine_by_pid.get(pid, 0),
                            "guild": guild_by_pid.get(pid, "Keine Gilde"),
                            "level": int((p_live.get("level") if p_live else r["level"]) or 1),
                            "exp": int((p_live.get("exp") if p_live else r["exp"]) or 0),
                            "hp": int((p_live.get("hp") if p_live else r["hp"]) or 950),
                            "maxHp": int((p_live.get("max_hp") if p_live else r["max_hp"]) or 950),
                            "mp": int((p_live.get("mp") if p_live else r["mp"]) or 260),
                            "maxMp": int((p_live.get("max_mp") if p_live else r["max_mp"]) or 260),
                            "vit": int((p_live.get("vit") if p_live else r["vit"]) or 16),
                            "int": int((p_live.get("int_stat") if p_live else r["int_stat"]) or 10),
                            "str": int((p_live.get("str") if p_live else r["str"]) or 16),
                            "dex": int((p_live.get("dex") if p_live else r["dex"]) or 12),
                            "reputation": int((p_live.get("reputation") if p_live else r["reputation"]) or 0),
                            "yang": int((p_live.get("yang") if p_live else r["yang"]) or 0),
                            "shards": int((p_live.get("shards") if p_live else r["shards"]) or 0),
                            "mapId": (p_live.get("map_id") if p_live else r["map_id"]) or "morgenwacht",
                            "empire": emp_key,
                            "cityName": city_name,
                            "online": is_on,
                            "skills": raw_skills if isinstance(raw_skills, dict) else {},
                            "passives": raw_passives if isinstance(raw_passives, dict) else {},
                            "mountInfo": mount_info,
                            "petInfo": pet_info,
                            "equipment": eq_items,
                        }
                    )

                online_count = sum(
                    1
                    for pid, pl in online_map.items()
                    if pid != "hero_default"
                    and pl.get("online")
                    and pl.get("inWorld", False)
                    and (now - float(pl.get("lastSeen", 0.0) or 0.0)) <= 20.0
                )

                return {
                    "serverOnline": True,
                    "onlinePlayers": online_count,
                    "totalAccounts": max(1, int(acc_cnt or 0)),
                    "totalCharacters": max(len(leaderboard), int(char_cnt or 0)),
                    "activeShops": int(shop_cnt or 0),
                    "leaderboard": leaderboard,
                }
            finally:
                conn.close()

    def get_account_dashboard_details(self, username: str, online_players: Optional[dict] = None) -> Optional[dict]:
        """Liefert das vollständige Userpanel-Dossier inklusive Coins, Charakter-Werten und angelegter Ausrüstung."""
        uname = (username or "").strip()
        ukey = uname.lower()
        if not ukey:
            return None
        online_map = online_players or {}
        now = time.time()

        with DB_LOCK:
            conn = self._connect()
            try:
                row = conn.execute("SELECT * FROM accounts WHERE username_key = ?", (ukey,)).fetchone()
                if not row:
                    return None
                try:
                    raw_chars = json.loads(row["characters_json"] or "[null,null,null,null]")
                    if not isinstance(raw_chars, list):
                        raw_chars = [None, None, None, None]
                except Exception:
                    raw_chars = [None, None, None, None]

                detailed_chars = []
                for slot_idx, ch in enumerate((raw_chars + [None, None, None, None])[:4]):
                    if not isinstance(ch, dict):
                        continue
                    pid = ch.get("playerId") or ""
                    prow = None
                    if pid:
                        prow = conn.execute("SELECT * FROM players WHERE player_id = ?", (pid,)).fetchone()
                    if not prow and ch.get("name"):
                        prow = conn.execute(
                            "SELECT * FROM players WHERE lower(name) = lower(?)", (str(ch.get("name")),)
                        ).fetchone()
                        if prow:
                            pid = prow["player_id"]

                    eq_items = []
                    if pid:
                        eq_rows = conn.execute(
                            """
                            SELECT template_id, equipped_slot, plus_level
                            FROM inventory_items
                            WHERE player_id = ? AND equipped_slot IS NOT NULL
                            """,
                            (pid,),
                        ).fetchall()
                        for er in eq_rows:
                            tpl = ITEM_TEMPLATES.get(er["template_id"], {})
                            eq_items.append(
                                {
                                    "templateId": er["template_id"],
                                    "name": tpl.get("name", er["template_id"]),
                                    "slot": er["equipped_slot"],
                                    "plus": int(er["plus_level"] or 0),
                                    "rarity": tpl.get("rarity", "common"),
                                    "icon": tpl.get("icon", ""),
                                }
                            )

                    p_live = online_map.get(pid) if pid else None
                    is_on = bool(
                        p_live
                        and p_live.get("online")
                        and p_live.get("inWorld", False)
                        and (now - float(p_live.get("lastSeen", 0.0) or 0.0)) <= 20.0
                    )

                    lvl = int((prow["level"] if prow else ch.get("level")) or 1)
                    cls_id = str((prow["class_id"] if prow else (ch.get("classId") or ch.get("archetype"))) or "warrior")
                    if cls_id == "ninja":
                        cls_id = "assassin"
                    cls_label_map = {
                        "warrior": "Klingenwächter",
                        "assassin": "Schattenjäger",
                        "ninja": "Schattenjäger",
                        "sura": "Runenmagier",
                        "shaman": "Seelenweber",
                    }
                    gender = str((prow["gender"] if prow else ch.get("gender")) or "male")
                    raw_emp = str(ch.get("empire") or "seiryu").strip().lower()
                    emp_key = "kaeryu" if raw_emp in ("kaeryu", "dark", "shadow") else "seiryu"
                    city_name = "Kaeryu" if emp_key == "kaeryu" else "Seiryu"

                    detailed_chars.append(
                        {
                            "slot": slot_idx,
                            "playerId": pid,
                            "name": (prow["name"] if prow else ch.get("name")) or f"Held #{slot_idx + 1}",
                            "classId": cls_id,
                            "className": cls_label_map.get(cls_id, "Klingenwächter"),
                            "gender": gender,
                            "empire": emp_key,
                            "cityName": city_name,
                            "doctrine": ch.get("doctrineIdx", ch.get("doctrine", 0)),
                            "level": lvl,
                            "exp": int((prow["exp"] if prow else 0) or 0),
                            "hp": int((prow["hp"] if prow else 950) or 950),
                            "maxHp": int((prow["max_hp"] if prow else 950) or 950),
                            "mp": int((prow["mp"] if prow else 260) or 260),
                            "maxMp": int((prow["max_mp"] if prow else 260) or 260),
                            "vit": int((prow["vit"] if prow else 15) or 15),
                            "int": int((prow["int_stat"] if prow else 12) or 12),
                            "str": int((prow["str"] if prow else 16) or 16),
                            "dex": int((prow["dex"] if prow else 14) or 14),
                            "yang": int((prow["yang"] if prow else 3500) or 0),
                            "shards": int((prow["shards"] if prow else 5) or 0),
                            "reputation": int((prow["reputation"] if prow else 1450) or 0),
                            "mapId": (prow["map_id"] if prow else ch.get("mapId")) or "morgenwacht",
                            "online": is_on,
                            "equipment": eq_items,
                        }
                    )

                coins_val = 250
                try:
                    coins_val = int(row["coins"] if row["coins"] is not None else 250)
                except Exception:
                    coins_val = 250

                return {
                    "username": row["username"] or uname,
                    "email": row["email"] or f"{ukey}@aeryndor.de",
                    "deleteCode": row["delete_code"] or "1234",
                    "coins": coins_val,
                    "characters": detailed_chars,
                    "rawCharacters": (raw_chars + [None, None, None, None])[:4],
                }
            finally:
                conn.close()

    def purchase_or_spend_coins(
        self, username: str, sub_action: str, package_id: str, target_player_id: Optional[str] = None
    ) -> Tuple[bool, str, int]:
        """Verarbeitet das Aufladen von Aeryndor-Coins oder den Kauf von Ingame-Paketen im Userpanel."""
        uname = (username or "").strip()
        ukey = uname.lower()
        if not ukey:
            return False, "⚠️ Bitte zuerst im Userpanel einloggen.", 0

        coin_packages = {
            "pack_500": {"coins": 500, "bonus": 50, "label": "550 Aeryndor-Coins (Starter-Paket)"},
            "pack_1500": {"coins": 1500, "bonus": 250, "label": "1.750 Aeryndor-Coins (Krieger-Schatz)"},
            "pack_3500": {"coins": 3500, "bonus": 750, "label": "4.250 Aeryndor-Coins (Monolithen-Truhe)"},
            "pack_8000": {"coins": 8000, "bonus": 2500, "label": "10.500 Aeryndor-Coins (Kaiser-Paket)"},
        }

        shop_rewards = {
            "item_yang_500k": {"cost": 200, "yang": 500_000, "shards": 0, "label": "500.000 Yang Gold-Schatztruhe"},
            "item_yang_2m": {"cost": 650, "yang": 2_000_000, "shards": 0, "label": "2.000.000 Yang Kaiserlicher Goldbarren"},
            "item_shards_50": {"cost": 300, "yang": 0, "shards": 50, "label": "50x Reine Seelensplitter"},
            "item_shards_200": {"cost": 950, "yang": 0, "shards": 200, "label": "200x Astrale Seelensplitter-Truhe"},
        }

        with DB_LOCK:
            conn = self._connect()
            try:
                row = conn.execute("SELECT * FROM accounts WHERE username_key = ?", (ukey,)).fetchone()
                if not row:
                    return False, "⚠️ Account wurde nicht gefunden.", 0
                cur_coins = int(row["coins"] if row["coins"] is not None else 250)

                if sub_action == "topup":
                    pkg = coin_packages.get(package_id)
                    if not pkg:
                        return False, "⚠️ Ungültiges Coin-Paket ausgewählt.", cur_coins
                    added = pkg["coins"] + pkg["bonus"]
                    new_coins = cur_coins + added
                    conn.execute(
                        "UPDATE accounts SET coins = ?, updated_at = ? WHERE username_key = ?",
                        (new_coins, time.time(), ukey),
                    )
                    conn.commit()
                    return True, f"✨ +{added:,} Aeryndor-Coins wurden deinem Account sofort gutgeschrieben!", new_coins

                if sub_action == "redeem":
                    rew = shop_rewards.get(package_id)
                    if not rew:
                        return False, "⚠️ Ungültiges Itemshop-Paket.", cur_coins
                    if cur_coins < rew["cost"]:
                        return (
                            False,
                            f"⚠️ Nicht genügend Aeryndor-Coins ({cur_coins:,} / {rew['cost']:,} benötigt).",
                            cur_coins,
                        )
                    if not target_player_id:
                        return False, "⚠️ Bitte wähle zuerst einen Charakter aus, der das Paket erhalten soll.", cur_coins
                    try:
                        owned_chars = json.loads(row["characters_json"] or "[]")
                        owned_pids = {
                            c.get("playerId") for c in owned_chars if isinstance(c, dict) and c.get("playerId")
                        }
                    except Exception:
                        owned_pids = set()
                    if owned_pids and target_player_id not in owned_pids:
                        return False, "⚠️ Sicherheitsprüfung: Dieser Charakter gehört nicht zu deinem Account.", cur_coins
                    prow = conn.execute("SELECT * FROM players WHERE player_id = ?", (target_player_id,)).fetchone()
                    if not prow:
                        return False, "⚠️ Ausgewählter Charakter existiert noch nicht in der Spielwelt.", cur_coins

                    new_coins = cur_coins - rew["cost"]
                    conn.execute(
                        "UPDATE accounts SET coins = ?, updated_at = ? WHERE username_key = ?",
                        (new_coins, time.time(), ukey),
                    )
                    conn.execute(
                        "UPDATE players SET yang = yang + ?, shards = shards + ?, updated_at = ? WHERE player_id = ?",
                        (rew["yang"], rew["shards"], time.time(), target_player_id),
                    )
                    conn.commit()
                    return (
                        True,
                        f"🎁 {rew['label']} wurde erfolgreich an {prow['name']} ausgeliefert!",
                        new_coins,
                    )

                return False, "⚠️ Unbekannte Transaktion.", cur_coins
            finally:
                conn.close()

    def unstuck_account_character(self, username: str, player_id: str) -> Tuple[bool, str]:
        """Setzt einen festgefahrenen Charakter vom Homepage-Userpanel aus zurück in seine Heimatstadt (Kaeryu oder Seiryu)."""
        ukey = (username or "").strip().lower()
        if not ukey or not player_id:
            return False, "⚠️ Ungültige Anfrage."
        with DB_LOCK:
            conn = self._connect()
            try:
                arow = conn.execute("SELECT characters_json FROM accounts WHERE username_key = ?", (ukey,)).fetchone()
                if not arow:
                    return False, "⚠️ Account nicht gefunden."
                char_emp = "seiryu"
                try:
                    owned_chars = json.loads(arow["characters_json"] or "[]")
                    owned_pids = set()
                    for c in owned_chars:
                        if isinstance(c, dict) and c.get("playerId"):
                            owned_pids.add(c.get("playerId"))
                            if c.get("playerId") == player_id:
                                raw_e = str(c.get("empire") or "seiryu").strip().lower()
                                char_emp = "kaeryu" if raw_e in ("kaeryu", "dark", "shadow") else "seiryu"
                except Exception:
                    owned_pids = set()
                if owned_pids and player_id not in owned_pids:
                    return False, "⚠️ Sicherheitsprüfung: Dieser Charakter gehört nicht zu deinem Account."
                prow = conn.execute("SELECT name FROM players WHERE player_id = ?", (player_id,)).fetchone()
                if not prow:
                    return False, "⚠️ Charakter nicht gefunden."
                spawn_x = -790.0 if char_emp == "kaeryu" else 790.0
                spawn_z = -740.0
                city_label = "Kaeryu" if char_emp == "kaeryu" else "Seiryu"
                conn.execute(
                    "UPDATE players SET map_id = 'morgenwacht', pos_x = ?, pos_z = ?, updated_at = ? WHERE player_id = ?",
                    (spawn_x, spawn_z, time.time(), player_id),
                )
                conn.commit()
                return True, f"🏛️ {prow['name']} wurde sicher in die Stadt {city_label} teleportiert!"
            finally:
                conn.close()

