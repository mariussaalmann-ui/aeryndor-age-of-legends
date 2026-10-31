# -*- coding: utf-8 -*-
"""
AERYNDOR: LEGACY OF THE MONOLITHS – Offizieller KI-Panel-, Live-Status- & Support-Bot
Verbindet sich direkt mit dem Discord Gateway v10 (ohne externe Abhängigkeiten) und dem
lokalen Aeryndor-Gameserver (Port 8090 / SQLite-DB), stellt interaktive Button-/Dropdown-Panels,
Popup-Modals, Rollen-Vergabe, Ticket-System, Live-Charakter-Dossiers und den KI-Chronisten bereit.
"""

import base64
import hashlib
import json
import os
import random
import socket
import ssl
import struct
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

TOKEN = os.environ.get("AERYNDOR_DISCORD_TOKEN", "")  # Token in /etc/aeryndor/secrets.env (nicht im Repo!)
GUILD_ID = "1564814262524706957"
BOT_ID = "1564814988810649680"
API_BASE = "https://discord.com/api/v10"
GAME_API_URL = os.environ.get("AERYNDOR_GAME_API", "http://127.0.0.1:8090/api/homepage-stats")
PUBLIC_SITE_URL = "https://aeryndor.ddns.net"

# Bekannte Kanal-IDs auf dem Aeryndor-Discord
CAT_OFFICIAL_ID = "1564816680247365794"
CHAN_WELCOME_ID = "1564816696986960047"
CHAN_STATUS_ID = "1564816721183907862"
CHAN_SUPPORT_ID = "1564816771280539789"
CHAN_BUGS_ID = "1564816766260092970"
CHAN_IDEAS_ID = "1564816762787078267"

# Vollständige Discord-Ranghierarchie von Aeryndor (01 Gründer bis 34 Event-Ping)
DISCORD_ROLES_BY_KEY = {
    # 01–09: Team- und Verwaltungsränge
    "founder": ("1564816165182898358", "👑 Gründer", "#FFD700", "Serverinhaber"),
    "project_lead": ("1564816168487886848", "⚜️ Projektleitung", "#D97706", "Projektverwaltung"),
    "developer": ("1564816171679617054", "💻 Entwickler", "#2563EB", "Entwicklung"),
    "admin": ("1564816174523482242", "🛡️ Administrator", "#DC2626", "Serververwaltung"),
    "gamemaster": ("1564816177765818448", "🔮 Game Master", "#9333EA", "Ingame-Support"),
    "moderator": ("1564816181146161182", "⚔️ Moderator", "#06B6D4", "Discord-Moderation"),
    "supporter": ("1564816184015065099", "🤝 Supporter", "#10B981", "Spielerhilfe"),
    "event_master": ("1564816659435360426", "🎪 Eventmeister", "#F97316", "Events und Turniere"),
    "tester": ("1564816663319416945", "🧪 Tester", "#38BDF8", "Spieltests"),
    # 10–19: Besondere Community-Ränge
    "pioneer": ("1564816666490179737", "🌟 Pionier", "#F59E0B", "Spieler der ersten Stunde"),
    "booster": ("1564816669837365269", "💎 Server-Booster", "#F472B6", "Discord-Serverboost"),
    "pvp_champ": ("1564816672857264129", "🏆 PvP-Champion", "#EF4444", "Aktueller Turniersieger"),
    "rift_slayer": ("1565009870149787769", "⚡ Rissbezwinger", "#A855F7", "Besondere Rissmonolithen-Erfolge"),
    "boss_hunter": ("1565012402414559352", "🐉 Bossjäger", "#E11D48", "Besondere Boss-Erfolge"),
    "trade_lord": ("1565012404771754125", "💰 Handelsfürst", "#EAB308", "Handels- und Markterfolge"),
    "creator": ("1565012409750393033", "🎬 Content Creator", "#EC4899", "Videos und Streams"),
    "comm_hero": ("1565012412074295420", "❤️ Community-Held", "#14B8A6", "Besondere Community-Beiträge"),
    "event_winner": ("1565012414934818926", "🏅 Eventgewinner", "#FB923C", "Gewonnenes Community-Event"),
    "beta_legend": ("1565012417115717653", "🏛️ Beta-Legende", "#60A5FA", "Teilnahme an der Beta"),
    # 20–25: Klassenränge & Heimatstädte
    "cls_warrior": ("1565012422065000578", "⚔️ Klingenwächter", "#F97316", "Klassenrang"),
    "cls_assassin": ("1565012424455758006", "🗡️ Schattenjäger", "#10B981", "Klassenrang"),
    "cls_sura": ("1565012426666156055", "🔮 Runenkrieger", "#C084FC", "Klassenrang"),
    "cls_shaman": ("1565012429279334523", "✨ Seelenweber", "#FACC15", "Klassenrang"),
    "emp_kaeryu": ("1565012432114425971", "🏰 Kaeryu • Stadt der Wächter", "#DC2626", "Heimatstadt"),
    "emp_seiryu": ("1565012434299912396", "🏛️ Seiryu • Stadt des Wissens", "#2563EB", "Heimatstadt"),
    # 26–33: Spielerränge – Aeryndor-Stil (unabhängig von den Charakterklassen)
    "plr_legend": ("1565012436866568234", "👑 Legende von Aeryndor", "#E838C8", "Besondere Erfolge"),
    "plr_mono_guard": ("1565012438770913353", "🌌 Monolithenwächter", "#8B5CF6", "Ab Level 100"),
    "plr_mono_hunt": ("1565012441639686314", "🔮 Monolithenjäger", "#6366F1", "Ab Level 80"),
    "plr_dragon": ("1565012461479006268", "🐉 Drachenbezwinger", "#F43F5E", "Ab Level 60"),
    "plr_veteran": ("1565012464041590915", "🎖️ Veteran", "#F59E0B", "Ab Level 40"),
    "plr_warrior": ("1565012466260385944", "🛡️ Krieger", "#3B82F6", "Ab Level 25"),
    "plr_adventurer": ("1565012468529631314", "📜 Abenteurer", "#22C55E", "Ab Level 10"),
    "plr_wanderer": ("1565012470773325836", "🧭 Wanderer", "#94A3B8", "Neuer Spieler"),
    "boss_ping": ("1565012475294912584", "🔔 Weltboss- & Event-Ping", "#FB7185", "Event-Benachrichtigungen"),
}

# Bekannte Rollen-IDs für das Self-Role-Panel
ROLE_MAP = {
    "role_kaeryu": ("1565012432114425971", "🏰 Kaeryu • Stadt der Wächter"),
    "role_seiryu": ("1565012434299912396", "🏛️ Seiryu • Stadt des Wissens"),
    "role_warrior": ("1565012422065000578", "⚔️ Klingenwächter"),
    "role_assassin": ("1565012424455758006", "🗡️ Schattenjäger"),
    "role_mage": ("1565012426666156055", "🔮 Runenkrieger"),
    "role_shaman": ("1565012429279334523", "✨ Seelenweber"),
    "role_boss_ping": ("1565012475294912584", "🔔 Weltboss- & Event-Ping"),
    "role_adventurer": ("1565012468529631314", "📜 Abenteurer"),
    "role_wanderer": ("1565012470773325836", "🧭 Wanderer"),
}

STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "discord_bot_state.json")

# ============================================================================
# WISSENSDATENBANK DES KI-CHRONISTEN VON AERYNDOR
# ============================================================================
MONOLITH_LORE_TABLE = [
    (5, "Rissmonolith des Erwachens", "Die ersten Anzeichen der zurückkehrenden Dimensionsenergie"),
    (10, "Rissmonolith der Wildnis", "Die fremde Energie beginnt, die Natur zu beeinflussen"),
    (15, "Rissmonolith des Blutmondes", "Aggressive und zerstörerische Energien treten hervor"),
    (20, "Rissmonolith der verlorenen Seelen", "Die Grenze zwischen Leben, Tod und fremden Dimensionen wird schwächer"),
    (25, "Rissmonolith des Zwielichts", "Unterschiedliche Dimensionseinflüsse beginnen sich zu überlagern"),
    (30, "Rissmonolith der Verderbnis", "Die Energie verändert Kreaturen und ihre Umgebung"),
    (35, "Rissmonolith des Chaos", "Das Monolithennetzwerk verliert zunehmend seine Stabilität"),
    (40, "Rissmonolith des Abgrunds", "Ein mächtiger Zugang zu einer gefährlichen fremden Dimension"),
    (45, "Rissmonolith der Verdammnis", "Die zerstörerischen Kräfte der alten Katastrophe kehren zurück"),
    (50, "Rissmonolith der Finsternis", "Schattenenergien beginnen, ganze Regionen zu beeinflussen"),
    (55, "Rissmonolith des Seelensturms", "Mächtige Seelen- und Dimensionsenergien verbinden sich"),
    (60, "Rissmonolith der ewigen Nacht", "Die Energie kann selbst Licht und Atmosphäre verändern"),
    (65, "Rissmonolith der Zerstörung", "Gewaltige Kräfte bedrohen die Stabilität der Landschaft"),
    (70, "Rissmonolith des Dimensionsbruchs", "Die Grenzen zwischen mehreren Dimensionen zerfallen"),
    (75, "Rissmonolith der Leere", "Eine unbekannte Macht entzieht ihrer Umgebung Energie"),
    (80, "Rissmonolith der Urgewalten", "Die ursprünglichen Natur- und Dimensionskräfte treten hervor"),
    (85, "Rissmonolith des Weltenendes", "Die Gefahr eines neuen großen Dimensionsbruchs erreicht ihren Höhepunkt"),
    (90, "Rissmonolith des Ursprungsspalts", "Der mögliche Ursprung des gesamten Monolithennetzwerks"),
]

RANK_TABLE = [
    ("Geächtet", "-20.000", "#7F1D1D", "0% (PvP-Drop-Risiko bei Tod)"),
    ("Verhasst", "-12.000", "#991B1B", "0%"),
    ("Feindselig", "-6.000", "#DC2626", "0%"),
    ("Misstrauisch", "-2.000", "#F97316", "0%"),
    ("Unruhig", "-500", "#FBBF24", "0%"),
    ("Neutral", "0", "#94A3B8", "+0% Schaden"),
    ("Bekannt", "1.000", "#E2E8F0", "+1% Gesamtschaden"),
    ("Freundlich", "3.000", "#86EFAC", "+2% Gesamtschaden"),
    ("Geachtet", "6.000", "#22C55E", "+4% Gesamtschaden"),
    ("Angesehen", "10.000", "#14B8A6", "+6% Gesamtschaden"),
    ("Ehrenhaft", "16.000", "#38BDF8", "+8% Gesamtschaden"),
    ("Ruhmreich", "24.000", "#3B82F6", "+10% Gesamtschaden"),
    ("Erhaben", "35.000", "#818CF8", "+12% Gesamtschaden"),
    ("Heldenhaft", "50.000", "#A855F7", "+15% Gesamtschaden"),
    ("Legendär", "70.000", "#F59E0B", "+18% Gesamtschaden"),
    ("Mythisch", "95.000", "#FB923C", "+21% Gesamtschaden"),
    ("Göttlich", "125.000", "#FDE047", "+25% Gesamtschaden"),
    ("Unsterblich", "160.000+", "#E838C8 (Pink-Violett Verlauf)", "+30% Gesamtschaden (Maximal)"),
]


def load_bot_state() -> dict:
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_bot_state(state: dict):
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[BotState] Fehler beim Speichern: {e}")


def discord_api(method: str, path: str, payload=None, retries: int = 5):
    url = API_BASE + path
    headers = {
        "Authorization": f"Bot {TOKEN}",
        "User-Agent": "AeryndorKIBot/2.0",
        "Content-Type": "application/json",
    }
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    for attempt in range(retries):
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                raw = resp.read().decode("utf-8")
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="ignore")
            if e.code == 429:
                wait_s = 1.5
                try:
                    wait_s = float(json.loads(err_body).get("retry_after", 1.5)) + 0.25
                except Exception:
                    pass
                time.sleep(wait_s)
                continue
            print(f"[DiscordAPI] HTTP {e.code} on {method} {path}: {err_body}")
            if e.code in (400, 401, 403, 404):
                return None
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(1.0)
                continue
            print(f"[DiscordAPI] Fehler bei {method} {path}: {e}")
    return None


def fetch_live_game_stats() -> dict:
    """Liest Live-Daten vom lokalen Aeryndor-Server (oder Fallback von der öffentlichen IP)."""
    for url in (GAME_API_URL, f"{PUBLIC_SITE_URL}/api/homepage-stats"):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "AeryndorKIBot/2.0"})
            with urllib.request.urlopen(req, timeout=4) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception:
            continue
    return {
        "online": True,
        "onlinePlayers": 0,
        "registeredAccounts": 0,
        "registeredCharacters": 0,
        "activeMonoliths": 18,
        "maxLevel": 90,
        "leaderboard": [],
    }


def format_skill_stage(points: int) -> str:
    pts = int(points or 0)
    if pts <= 0:
        return "—"
    if pts < 17:
        return f"Lv. {pts}"
    if pts < 27:
        return f"M{pts - 16}"
    if pts < 37:
        return f"G{pts - 26}"
    return "P (Perfekt)"


def hex_to_int_color(hex_str: str, default: int = 0xD97706) -> int:
    try:
        clean = str(hex_str or "").strip().lstrip("#")
        if len(clean) == 6:
            return int(clean, 16)
    except Exception:
        pass
    return default


# ============================================================================
# KI-ANTWORT-ENGINE FÜR SPIELERFRAGEN & ENZYKLOPÄDIE
# ============================================================================
def generate_ai_chronicle_embed(question: str, user_name: str = "Abenteurer") -> dict:
    q = (question or "").strip()
    ql = q.lower()
    stats = fetch_live_game_stats()
    lb = stats.get("leaderboard") or []

    # 1. Prüfe ob nach einem bestimmten Charakter/Spieler gefragt wird
    for entry in lb:
        cname = str(entry.get("name") or "").strip()
        if cname and len(cname) >= 3 and cname.lower() in ql:
            return build_character_dossier_embed(cname, stats)

    # 2. Prüfe ob nach einem bestimmten Level oder Rissmonolith gefragt wird
    if any(k in ql for k in ("monolith", "riss", "metin", "ursprungsspalt", "blutmond", "erwachen", "weltenende", "leere", "abgrund")):
        matched_monos = []
        for lvl, mname, mdesc in MONOLITH_LORE_TABLE:
            if f" {lvl}" in f" {ql} " or f"lv.{lvl}" in ql or f"level {lvl}" in ql or any(w in ql for w in mname.lower().split() if len(w) > 4 and w != "rissmonolith"):
                matched_monos.append((lvl, mname, mdesc))
        if not matched_monos:
            matched_monos = MONOLITH_LORE_TABLE
        lines_1 = [f"• **Lv. {lv:02d} – {nm}**\n  *{ds}*" for lv, nm, ds in matched_monos[:9]]
        lines_2 = [f"• **Lv. {lv:02d} – {nm}**\n  *{ds}*" for lv, nm, ds in matched_monos[9:18]]
        fields = [
            {
                "name": "🔮 Rissmonolithen (Übersicht I)",
                "value": "\n".join(lines_1) if lines_1 else "Keine Einträge.",
                "inline": False,
            }
        ]
        if lines_2:
            fields.append({
                "name": "🌌 Höhere Rissmonolithen & Ursprungsspalt (Übersicht II)",
                "value": "\n".join(lines_2),
                "inline": False,
            })
        fields.append({
            "name": "⚡ Die 3 Stufen, Level-Elitebosse & Erweckung",
            "value": (
                "• **Stufe 1 (Schlafend):** Spawnt stufenpassende Monsterwellen & dropt **Monolithensplitter**.\n"
                "• **Stufe 2 (Instabil):** Erweckbar mit `1× Monolithensplitter` (Taste **[F]**) – spawnt **1–4 exakt zum Monolith-Level passende Riss-Elitebosse** (*Lv. 5 Roter Zornkeiler, Lv. 10 Grizzlybär, Lv. 15 Schwarzpelz-Bär / Weißer-Eid-Kommandantin, Lv. 20 Weißer Königstiger, Lv. 25 Schwarzwind-To-Su, Lv. 30 Schwarzwind-Gu-Ryung, Lv. 35+ Wilder General*) und dropt **Erwachte Risskerne**.\n"
                "• **Stufe 3 (Erweckt):** Erweckbar mit `1× Erwachter Risskern` – beschwört den **Gebiets-Weltboss** mit **5× Beute-Resonanz** (gemeinsam mit Spielern & nahen KI-Helden bekämpfbar)!\n"
                "• **Ursprungsspalt (Lv. 90):** Das finale Siegel zwischen Schutzmacht der Ersten Hüter und dem Ersten Bruch."
            ),
            "inline": False,
        })
        return {
            "title": "🔮 KI-Chronist • Die 18 Rissmonolithen & 3 Stufen",
            "color": 0xA855F7,
            "description": f"**Deine Frage:** *„{q[:180]}“*\n\nHier ist die offizielle Überlieferung der Gelehrten von Seiryu zu den Rissmonolithen:",
            "fields": fields,
            "footer": {"text": f"Angefragt von {user_name} • Aeryndor KI-Chronist"},
        }

    # 2b. KI-Helden v5.0 (12 Bots), Physische NPC-/Stadt-KI, 3D-Pets, Tapferkeitsumhänge & Koop-Weltboss-Jagd
    if any(k in ql for k in ("bot", "bots", "ki-held", "ki held", "tapferkeitsumhang", "umhang", "umhänge", "pull", "erwecken", "koop", "v4.0", "v5.0", "lyra", "draven", "balancing")):
        return {
            "title": "🧬 KI-Chronist • 12 Autonome KI-Helden (KI v5.0 Omni-Synergy), NPC-/Stadt-KI, 3D-Pets & Koop-Raids",
            "color": 0x38BDF8,
            "description": (
                f"**Deine Frage:** *„{q[:180]}“*\n\n"
                "Die Welt von Aeryndor wird rund um die Uhr von **12 autonomen KI-Helden (6 in Seiryu, 6 in Kaeryu — inkl. [Bot]Lyra & [Bot]Draven)** auf Basis der neuen **KI v5.0 Omni-Synergy** bevölkert:"
            ),
            "fields": [
                {
                    "name": "🏛️ Physische NPC-Quests, Stadtrundgänge & 3D-Pet-Meisterschaft",
                    "value": (
                        "• Die 12 KI-Helden gehen **physisch zu den Quest-NPCs** (*Hauptmann Vaelen, Biologe Aurelius, Heilerin Aldric, Rüstschmied Torvald u.a.*), um Quests anzunehmen und Belohnungen abzuholen.\n"
                        "• Bei ihren **Stadtrundgängen** besuchen sie **Dorfschmied (+1 bis +9)**, **Seelenweberin (1.–7. Bonus)** und **Händlerin** persönlich.\n"
                        "• Jeder Bot führt sein eigenes **3D-Begleiter-Pet** und levelt bis zu **21 passive Pet-Skills**."
                    ),
                    "inline": False,
                },
                {
                    "name": "⚔️ Taktischer Boss-Kampf, Live-Messenger & 600-Kill Auto-Balancing",
                    "value": (
                        "• KI-Helden erwecken **Rissmonolithen auf Stufe 2 & 3**, jagen alle **3 festen 15-Minuten-Kartenbosse** mit taktischem **Schildblock & Ausweich-Kiting** und kehren nach einem Tod per Boss-Return-Memory sofort in den Kampf zurück.\n"
                        "• Im **Messenger & Direkt-Handel** reagieren Bots mit 100% echten Live-Daten (Sektor, Koordinaten, Waffe, passende Items für deine Klasse) und eilen dir auf Zuruf zu Hilfe!"
                    ),
                    "inline": False,
                },
            ],
            "footer": {"text": f"Angefragt von {user_name} • Aeryndor KI-Chronist v5.0"},
        }

    # 2c. Bosse, 3 Gebietsbosse (15 Min. Respawn) & Map-2-Dungeonboss Malakor
    if any(k in ql for k in ("boss", "bosse", "gebietsboss", "weltboss", "dungeon", "katakomben", "malakor", "lykos", "hauptmann", "respawn")):
        return {
            "title": "👑 KI-Chronist • 3 Gebietsbosse (15 Min.), Map-2-Dungeonboss & Weltbosse",
            "color": 0xEF4444,
            "description": (
                f"**Deine Frage:** *„{q[:180]}“*\n\n"
                "In Aeryndor erwarten dich feste Open-World-Gebietsbosse, verstärkte Dungeon-Herrscher und Stufe-3-Riss-Weltbosse:"
            ),
            "fields": [
                {
                    "name": "⚔️ 3 Feste Open-World-Gebietsbosse (15 Minuten Respawn)",
                    "value": (
                        "• **Westlicher Boss-Platz (Kaeryu-West):** *Lykos der Bestienfürst [Gebietsboss]* (`Lv. 20` • `15 Min. Respawn`)\n"
                        "• **Östlicher Boss-Platz (Seiryu-Ost):** *Lykos der Bestienfürst [Gebietsboss]* (`Lv. 20` • `15 Min. Respawn`)\n"
                        "• **Südlicher Boss-Platz (Bakra-Süd):** *Brutaler Hauptmann [Gebietsboss]* (`Lv. 35` • `15 Min. Respawn`)\n"
                        "• Alle 3 Gebietsbosse droppen **Fertigkeitsbücher, Segensrollen, Monolithensplitter, Tapferkeitsumhänge** und **Reine Seelensplitter**."
                    ),
                    "inline": False,
                },
                {
                    "name": "🏰 Map-2-Dungeonboss: Schwarzwind-Kriegsherr Malakor (Lv. 35)",
                    "value": (
                        "• In den **Äther-Katakomben** herrscht jetzt der massiv verstärkte **Schwarzwind-Kriegsherr Malakor [Map-2-Dungeonboss] (Lv. 35)**.\n"
                        "• Er wird von **2 Map-2-Elite-Leibwächtern** (*Schwarzwind-Gu-Ryung & Wilder General*) beschützt und lässt **Ebenholz-Ausrüstung (Lv. 30)** (*Ebenholz-Schwert, Ebenholz-Rüstung*), **Erwachte Risskerne** und **Seelensteine** fallen!"
                    ),
                    "inline": False,
                },
            ],
            "footer": {"text": f"Angefragt von {user_name} • Aeryndor KI-Chronist"},
        }

    # 3. Rangsystem / Rangpunkte / Farben / Unsterblich
    if any(k in ql for k in ("rang", "rangpunkte", "ruhm", "unsterblich", "göttlich", "geächtet", "farbe", "schadensbonus")):
        pos_ranks = "\n".join([f"• **{nm}** (`ab {pts} RP`) – `{col}` → **{bon}**" for nm, pts, col, bon in RANK_TABLE[5:]])
        neg_ranks = "\n".join([f"• **{nm}** (`ab {pts} RP`) – `{col}` → {bon}" for nm, pts, col, bon in RANK_TABLE[:5]])
        return {
            "title": "📊 KI-Chronist • Das 18-stufige Rangpunkte-System",
            "color": 0xE838C8,
            "description": (
                f"**Deine Frage:** *„{q[:180]}“*\n\n"
                "In **Aeryndor** sammelst du durch das Vernichten von Rissmonolithen, Weltbossen, Dungeons und Monstern **Rangpunkte (RP)**. "
                "Dein Rang wird **direkt vor deinem Namen in der passenden Rangfarbe** (im 3D-Spiel & in der Rangliste) angezeigt und verleiht dir bis zu **+30% Gesamtschaden**!"
            ),
            "fields": [
                {"name": "✨ Ehrenhafte & Göttliche Ränge (Neutral bis Unsterblich)", "value": pos_ranks, "inline": False},
                {"name": "💀 Gesetzlose Ränge (Negativ-Rangpunkte)", "value": neg_ranks, "inline": False},
            ],
            "footer": {"text": f"Angefragt von {user_name} • Aeryndor KI-Chronist"},
        }

    # 4. Klassen & Skills (M1 / G1 / P)
    if any(k in ql for k in ("klasse", "skill", "fertigkeit", "klingenwächter", "schattenjäger", "runenmagier", "seelenweber", "seelenstein", "fb", "perfekt", "grossmeister")):
        return {
            "title": "⚔️ KI-Chronist • Klassen & Fertigkeits-Meisterschaft (M1 → G1 → P)",
            "color": 0xF59E0B,
            "description": (
                f"**Deine Frage:** *„{q[:180]}“*\n\n"
                "In Aeryndor wählst du zwischen **4 Heldenklassen**, die jeweils über **6 einzigartige aktive Kampf-Skills** verfügen:"
            ),
            "fields": [
                {
                    "name": "🛡️ Die 4 Klassen von Aeryndor",
                    "value": (
                        "• **⚔️ Klingenwächter:** Nahkampf-Tank & AoE-Brecher (*Schwertwirbel, Kampfrausch, Erdbeben-Spalter*)\n"
                        "• **🗡️ Schattenjäger:** Kritischer Assassine & Bogenschütze (*Schattenschritt, Giftwolke, Todesstoß*)\n"
                        "• **🔮 Runenmagier:** Arkaner Riss-Beschwörer (*Kometeneinschlag, Dunkle Sphäre, Runenschild*)\n"
                        "• **✨ Seelenweber:** Himmlischer Heiler & Krit-Unterstützer (*Segen des Drachen, Blitzklaue, Heilendes Licht*)"
                    ),
                    "inline": False,
                },
                {
                    "name": "📖 Skill-Aufstieg: Normal → Meister (M1) → Großmeister (G1) → Perfekt (P)",
                    "value": (
                        "1. **Stufe 1–16 (Normal):** Vergib pro Level-Up 1 Fertigkeitspunkt. Ab **17 Punkten** springt der Skill auf **M1 (Meister)**.\n"
                        "2. **M1 bis M10 (Meister):** Lies **Fertigkeitsbücher (FB)** aus zerstörten Rissmonolithen, um bis **G1 (Großmeister)** aufzusteigen.\n"
                        "3. **G1 bis P (Perfekter Meister):** Nutze **Seelensteine** von hochstufigen Rissmonolithen & Weltbossen, um die ultimative Stufe **P (Perfekt)** mit massiver Effekt-Verstärkung freizuschalten!"
                    ),
                    "inline": False,
                },
            ],
            "footer": {"text": f"Angefragt von {user_name} • Aeryndor KI-Chronist"},
        }

    # 5. Schmied, Upgrade +0 bis +9 & Runenweber
    if any(k in ql for k in ("schmied", "gorak", "upgrade", "verbessern", "+9", "segensrolle", "runen", "bonus", "ausrüstung", "waffe", "rüstung")):
        return {
            "title": "🔨 KI-Chronist • Schmiedemeister Gorak (+0 bis +9) & Runenweber",
            "color": 0xEF4444,
            "description": (
                f"**Deine Frage:** *„{q[:180]}“*\n\n"
                "Alle Waffen, Rüstungen, Helme, Schilde und Schmuckstücke können von **+0 bis +9** geschmiedet werden:"
            ),
            "fields": [
                {
                    "name": "⚒️ Erfolgschancen & Schutz vor Zerstörung",
                    "value": (
                        "• **+1 bis +3:** Sehr hohe Erfolgschance (`90%` → `70%`)\n"
                        "• **+4 bis +6:** Mittlere Erfolgschance (`60%` → `40%`), erste goldene Funken\n"
                        "• **+7 bis +9:** Herausfordernd (`30%` → `15%`), verleiht die **legendäre +9 Aura**\n"
                        "• **📜 Segensrolle:** Verhindert beim Fehlschlag die Zerstörung des Gegenstands (er fällt stattdessen nur um 1 Stufe zurück)!"
                    ),
                    "inline": False,
                },
                {
                    "name": "🔮 Runenweberin Lyra (1–5 Boni)",
                    "value": (
                        "Mit **Runen-Verzauberungen** schaltest du bis zu **5 zufällige Boni** auf deiner Ausrüstung frei "
                        "(z. B. *Stark gegen Rissmonolithen +15%*, *Kritischer Treffer +10%*, *Max. TP +2.000*, *Durchbohrender Treffer +10%*)."
                    ),
                    "inline": False,
                },
            ],
            "footer": {"text": f"Angefragt von {user_name} • Aeryndor KI-Chronist"},
        }

    # 6. Reittiere (Mounts) & Pets
    if any(k in ql for k in ("mount", "reittier", "pferd", "pet", "begleiter", "phönix", "keiler", "wolf", "drache", "reiten")):
        return {
            "title": "🐎 KI-Chronist • Reittiere (Lv. 1–50) & Begleiter (Lv. 1–120)",
            "color": 0x10B981,
            "description": (
                f"**Deine Frage:** *„{q[:180]}“*\n\n"
                "Im kombinierten **Begleiter- & Reittier-Fenster (`[P]`)** verwaltest du dein Reittier (Level 1 bis 50) und deinen Begleiter (Level 1 bis 120):"
            ),
            "fields": [
                {
                    "name": "🐎 Reittiere (Mount Level 1 bis 50) • Hotkey [P] / [STRG+G]",
                    "value": (
                        "• **Pferd (Lv. 1–34) → Kampfpferd (Lv. 35–49) → Militärgaul (Lv. 50)** durch Pferdemedaillen.\n"
                        "• Ab **Level 50 (Militärgaul)** schaltest du alle **3 aktiven Reit-Fertigkeiten** frei (*Kampf vom Pferderücken*, *Pferde-Angriff*, *Wellenangriff*).\n"
                        "• Verteile Sattel-Statuspunkte frei auf **DMG (Schaden)** und **TP/DEF** und rüste **Mount-Skins** aus."
                    ),
                    "inline": False,
                },
                {
                    "name": "🐉 Begleiter (Pet Level 1 bis 120) • Alle 24 Pet-Skills",
                    "value": (
                        "• Dein **Grüner Smaragddrache** levelt im Kampf von **Level 1 bis Level 120**.\n"
                        "• **3 Aktive Pet-Skills (Max. Lv. 5):** *Auto-Pickup, Erneuerung & Heilung*.\n"
                        "• **21 Passive Pet-Skills (Max. Lv. 20):** *Erfahrungsrausch, Dungeonmeister, Jäger, Schatzgräber, Glücksbringer, Monsterschild, 5× Elementar-Verständnis, Herrschaft, Widerstand, Zerstörung/Beschützer (FKS & DSS), Resistenz, Unberührbarkeit, Vampirismus & Reichweite*."
                    ),
                    "inline": False,
                },
            ],
            "footer": {"text": f"Angefragt von {user_name} • Aeryndor KI-Chronist"},
        }

    # 7. Städte Kaeryu & Seiryu / Lore / Geschichte
    if any(k in ql for k in ("kaeryu", "seiryu", "stadt", "städte", "geschichte", "lore", "hüter", "bruch", "fraktion", "reich")):
        return {
            "title": "🏛️ KI-Chronist • Kaeryu, Seiryu & Der Erste Bruch",
            "color": 0x38BDF8,
            "description": (
                f"**Deine Frage:** *„{q[:180]}“*\n\n"
                "Nach dem **Ersten Bruch**, der das alte Siegelnetzwerk der **Ersten Hüter** erschütterte, entstanden zwei große Zentren der Menschheit:"
            ),
            "fields": [
                {
                    "name": "🏰 Kaeryu – Die Stadt der Wächter",
                    "value": (
                        "Eine wehrhafte Festungsstadt voller Schmiedefeuer, Kriegsbanner und schwer gepanzerter Garnisonen. "
                        "Kaeryu setzt auf militärische Stärke, um die Rissmonolithen mit Klinge und Schild zu zerschlagen."
                    ),
                    "inline": False,
                },
                {
                    "name": "🏛️ Seiryu – Die Stadt des Wissens",
                    "value": (
                        "Ein prachtvolles Zentrum der Gelehrten, Runenmeister und Chronisten. "
                        "In den geheimsten Schriften von Seiryu wurde entdeckt, dass der **Rissmonolith des Ursprungsspalts (Lv. 90)** "
                        "das letzte verbliebene Siegel ist, das eine noch größere Gefahr zurückhält."
                    ),
                    "inline": False,
                },
            ],
            "footer": {"text": f"Angefragt von {user_name} • Aeryndor KI-Chronist"},
        }

    # 8. Biologen-Quests, Dungeons, Steuerung oder allgemeine Hilfe
    top_hero_str = "Noch kein Held verzeichnet"
    if lb:
        t0 = lb[0]
        top_hero_str = f"**{t0.get('name')}** (Lv. {t0.get('level')} {t0.get('className', '')} • Rang: *{t0.get('rankName', 'Neutral')}*)"

    return {
        "title": "🤖 KI-Chronist von Aeryndor • Antwort & Übersicht",
        "color": 0xD97706,
        "description": (
            f"Sei gegrüßt, **{user_name}**! Du hast gefragt:\n> *„{q[:220] if q else 'Allgemeine Hilfe zu Aeryndor'}“*\n\n"
            "Hier sind die wichtigsten Informationen aus den Archiven von **Aeryndor: Legacy of the Monoliths**:"
        ),
        "fields": [
            {
                "name": "🌍 Live-Weltstatus",
                "value": (
                    f"• **Spieler Online:** `{stats.get('onlinePlayers', 0)}`\n"
                    f"• **Registrierte Helden:** `{stats.get('registeredCharacters', 0)}`\n"
                    f"• **Aktive Rissmonolithen:** `{stats.get('activeMonoliths', 18)}`\n"
                    f"• **Aktueller Ranglisten-Anführer:** {top_hero_str}"
                ),
                "inline": False,
            },
            {
                "name": "🧭 Schnell-Wegweiser & Hotkeys im Spiel",
                "value": (
                    "• **`[I]`** Inventar & Ausrüstung (`+0` bis `+9`)\n"
                    "• **`[C]`** Charakter-Status & Attribute (`STR`, `VIT`, `DEX`, `INT`)\n"
                    "• **`[K]`** Fertigkeiten (`Lv. 1` → `M1` → `G1` → `P`)\n"
                    "• **`[J]` / `[G]`** Reittier-Menü & Auf-/Absteigen\n"
                    "• **`[P]`** Begleiter (Pet) rufen\n"
                    "• **`[M]`** Große Weltkarte & Teleport-Ring"
                ),
                "inline": False,
            },
            {
                "name": "💡 Tipp: Frag mich gezielt nach...",
                "value": (
                    "Du kannst mich nach **jedem Spielernamen** (für ein Live-Dossier), nach **Rissmonolithen (Lv. 5–90 & 3 Stufen)**, "
                    "**KI-Helden (Bots) & Tapferkeitsumhängen**, **3 Gebietsbossen (15 Min.) & Map-2-Dungeonboss Malakor**, "
                    "**Rangpunkten & Rangfarben**, **Klassen & Skills**, **Schmied (+9)**, **Reittieren & Pets** oder **Kaeryu & Seiryu** fragen!"
                ),
                "inline": False,
            },
        ],
        "footer": {"text": f"Angefragt von {user_name} • Aeryndor KI-Chronist"},
    }


def build_character_dossier_embed(char_query: str, stats: dict = None) -> dict:
    """Erstellt ein Live-Charakter-Dossier-Embed wie in der Homepage- & Ingame-Rangliste."""
    if stats is None:
        stats = fetch_live_game_stats()
    lb = stats.get("leaderboard") or []
    q = (char_query or "").strip().lower()

    match = None
    for entry in lb:
        cname = str(entry.get("name") or "").strip()
        if cname.lower() == q:
            match = entry
            break
    if not match and q:
        for entry in lb:
            cname = str(entry.get("name") or "").strip()
            if q in cname.lower():
                match = entry
                break

    if not match:
        available = ", ".join([f"`{e.get('name')}`" for e in lb[:10] if e.get("name")]) or "Noch keine Helden in der Top-Liste"
        return {
            "title": f"🔍 Charakter-Suche: „{char_query}“",
            "color": 0xEF4444,
            "description": (
                f"Es wurde kein Charakter mit dem Namen **„{char_query}“** in der aktuellen Top-30-Rangliste gefunden.\n\n"
                f"**Aktuell verzeichnete Helden (Auswahl):**\n{available}"
            ),
            "footer": {"text": "Aeryndor Live-Charakter-Inspektor"},
        }

    cname = match.get("name", "Unbekannt")
    cclass = match.get("className") or match.get("classId") or "Krieger"
    clevel = int(match.get("level") or 1)
    rep = int(match.get("reputation") or 0)
    rank_name = match.get("rankName") or "Neutral"
    rank_color = hex_to_int_color(match.get("rankColor"), 0xD97706)
    empire_raw = str(match.get("empire") or "seiryu").lower()
    empire_label = "🏰 Kaeryu (Stadt der Wächter)" if "kaeryu" in empire_raw or "pyungmoo" in empire_raw else "🏛️ Seiryu (Stadt des Wissens)"
    guild_name = match.get("guild") or "Keine Gilde"
    is_online = bool(match.get("online"))

    # Skills formatieren
    skills_list = match.get("skills") or []
    skill_lines = []
    if isinstance(skills_list, list) and skills_list:
        for sk in skills_list[:6]:
            if isinstance(sk, dict):
                sname = sk.get("name") or sk.get("id") or "Fertigkeit"
                stage = sk.get("stageLabel") or format_skill_stage(sk.get("points", 0))
                skill_lines.append(f"• **{sname}:** `{stage}`")
    skills_val = "\n".join(skill_lines) if skill_lines else "• *Noch keine Fertigkeiten auf Meisterstufe*"

    # Mount & Pet
    mount_info = match.get("mount") or {}
    pet_info = match.get("pet") or {}
    mount_str = f"🐎 **{mount_info.get('name', 'Streitross')}** (Stufe {mount_info.get('level', 1)})" if isinstance(mount_info, dict) and mount_info.get("name") else "🐎 *Kein Reittier aktiv*"
    pet_str = f"🐾 **{pet_info.get('name', 'Begleiter')}** (Lv. {pet_info.get('level', 1)})" if isinstance(pet_info, dict) and pet_info.get("name") else "🐾 *Kein Begleiter aktiv*"

    # Equipment
    eq_list = match.get("equipment") or []
    eq_lines = []
    if isinstance(eq_list, list) and eq_list:
        for eq in eq_list[:6]:
            if isinstance(eq, dict):
                ename = eq.get("name") or "Ausrüstung"
                plus = int(eq.get("plus") or 0)
                slot_lbl = eq.get("slotLabel") or eq.get("slot") or ""
                eq_lines.append(f"• {f'`[{slot_lbl}]` ' if slot_lbl else ''}**{ename} +{plus}**")
    eq_val = "\n".join(eq_lines) if eq_lines else "• *Standard-Ausrüstung*"

    play_h = round(float(match.get("playtimeSeconds") or 0) / 3600.0, 1)

    return {
        "title": f"🛡️ Charakter-Dossier: [{rank_name}] {cname} (Lv. {clevel})",
        "color": rank_color,
        "description": (
            f"**Status:** {'🟢 **Gerade Online in Aeryndor**' if is_online else '⚫ Offline'}\n"
            f"**Klasse:** `{cclass}` • **Heimatstadt:** {empire_label} • **Gilde:** `{guild_name}`"
        ),
        "fields": [
            {
                "name": "👑 Rang & Rangpunkte",
                "value": f"**{rank_name}** (`{rep:,} Rangpunkte`)",
                "inline": True,
            },
            {
                "name": "⚔️ Heldentaten (PvE)",
                "value": (
                    f"🔮 Rissmonolithen: `{int(match.get('metinsDestroyed') or 0):,}`\n"
                    f"💀 Monster besiegt: `{int(match.get('monstersKilled') or 0):,}`\n"
                    f"👑 Weltbosse: `{int(match.get('bossesKilled') or 0):,}` • ⏱️ `{play_h}h`"
                ),
                "inline": True,
            },
            {
                "name": "📖 Aktuelle Fertigkeits-Stufen (Skill-Level)",
                "value": skills_val,
                "inline": False,
            },
            {
                "name": "🗡️ Angelegte Ausrüstung",
                "value": eq_val,
                "inline": True,
            },
            {
                "name": "🐎 Reittier & Begleiter",
                "value": f"{mount_str}\n{pet_str}",
                "inline": True,
            },
        ],
        "footer": {"text": f"Live-Daten vom Aeryndor-Server • {PUBLIC_SITE_URL}/rangliste"},
    }


def build_leaderboard_embed(stats: dict = None) -> dict:
    if stats is None:
        stats = fetch_live_game_stats()
    lb = stats.get("leaderboard") or []
    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
    lines = []
    for idx, p in enumerate(lb[:10]):
        m = medals[idx] if idx < len(medals) else f"`#{idx+1}`"
        nm = p.get("name", "Unbekannt")
        lv = int(p.get("level") or 1)
        cl = p.get("className") or p.get("classId") or "Held"
        rk = p.get("rankName") or "Neutral"
        rp = int(p.get("reputation") or 0)
        met = int(p.get("metinsDestroyed") or 0)
        on_dot = "🟢" if p.get("online") else "⚫"
        lines.append(f"{m} {on_dot} **[{rk}] {nm}** — **Lv. {lv}** ({cl}) • `{rp:,} RP` • 🔮 `{met}` Monolithen")

    return {
        "title": "🏆 Live Top-10 Ehrenhalle von Aeryndor",
        "color": 0xF59E0B,
        "description": (
            "Die mächtigsten Helden von **Kaeryu** und **Seiryu** in Echtzeit vom Spielserver.\n"
            "*Tipp: Klicke auf **`🔍 Charakter-Dossier (Live-Suche)`**, um Skills, Mount & Ausrüstung eines Spielers zu inspizieren!*\n\n"
            + ("\n\n".join(lines) if lines else "*Noch keine Helden in der Rangliste verzeichnet.*")
        ),
        "fields": [
            {
                "name": "🌐 Interaktive Web-Rangliste",
                "value": f"👉 {PUBLIC_SITE_URL}/rangliste",
                "inline": False,
            }
        ],
        "footer": {"text": f"Stand: {time.strftime('%d.%m.%Y %H:%M:%S')} Uhr • Live synchronisiert"},
    }


def build_live_status_embed(stats: dict = None) -> dict:
    if stats is None:
        stats = fetch_live_game_stats()
    lb = stats.get("leaderboard") or []
    top3 = []
    for i, p in enumerate(lb[:3]):
        medal = ["🥇", "🥈", "🥉"][i]
        top3.append(f"{medal} **[{p.get('rankName', 'Neutral')}] {p.get('name')}** (Lv. {p.get('level', 1)} {p.get('className', '')})")

    return {
        "title": "🟢 AERYNDOR LIVE-SERVERSTATUS & RISS-RADAR",
        "color": 0x22C55E,
        "description": (
            "Echtzeit-Telemetrie des europäischen Hauptservers (**Aeryndor — Age of Legends**).\n"
            "Nutze die **interaktiven Buttons** unter dieser Nachricht, um den Status zu prüfen, die **Top-10-Rangliste** zu öffnen "
            "oder ein **Live-Charakter-Dossier** abzufragen!"
        ),
        "fields": [
            {
                "name": "🖥️ Server-Telemetrie",
                "value": (
                    f"• **Status:** 🟢 `ONLINE (24/7 Echtzeit-Welt)`\n"
                    f"• **Helden Online:** `{stats.get('onlinePlayers', 0)}`\n"
                    f"• **Registrierte Helden:** `{stats.get('registeredCharacters', 0)}` (`{stats.get('registeredAccounts', 0)}` Accounts)\n"
                    f"• **Aktive Rissmonolithen:** `{stats.get('activeMonoliths', 18)}` in der Welt aktiv\n"
                    f"• **Maximal-Level:** `Lv. {stats.get('maxLevel', 90)}`"
                ),
                "inline": True,
            },
            {
                "name": "🏆 Top-3 Helden der Ehrenhalle",
                "value": "\n".join(top3) if top3 else "Noch keine Helden registriert.",
                "inline": True,
            },
            {
                "name": "🌐 Offizielle Direkt-Links",
                "value": (
                    f"🏠 **Homepage:** {PUBLIC_SITE_URL}\n"
                    f"🏆 **Live-Rangliste:** {PUBLIC_SITE_URL}/rangliste\n"
                    f"⚡ **Windows-Client:** {PUBLIC_SITE_URL}/download\n"
                    f"🎮 **Browser-Version:** {PUBLIC_SITE_URL}/play"
                ),
                "inline": False,
            },
        ],
        "footer": {"text": f"Zuletzt automatisch aktualisiert: {time.strftime('%d.%m.%Y %H:%M:%S')} Uhr"},
    }


def build_daily_oracle_embed(user_id: str, user_name: str) -> dict:
    day_seed = int(hashlib.sha256(f"{user_id}-{time.strftime('%Y-%m-%d')}".encode("utf-8")).hexdigest()[:8], 16)
    rng = random.Random(day_seed)
    mono = rng.choice(MONOLITH_LORE_TABLE)
    smith_luck = rng.randint(62, 98)
    zones = [
        "Smaragdwälder von Kaeryu",
        "Verfluchte Ruinen von Seiryu",
        "Schattenklippen des Blutmondes",
        "Obsidiantal des Abgrunds",
        "Kristallgipfel der Ewigen Nacht",
        "Vorhof des Ursprungsspalts",
    ]
    blessings = [
        "Segen der Ersten Hüter (+15% Rissmonolith-Beuteglück)",
        "Flamme von Schmiedemeister Gorak (Erhöhte Schmiede-Konzentration)",
        "Auge des Seelenwebers (+12% Chance auf Seelenstein-Resonanz)",
        "Schattenmantel von Seiryu (Kritische Trefferserie im PvE)",
    ]
    return {
        "title": f"🔮 Tages-Orakel der Chronisten für {user_name}",
        "color": 0x818CF8,
        "description": "Die Gelehrten von Seiryu haben die Resonanz der Rissmonolithen für deinen heutigen Tag gedeutet:",
        "fields": [
            {
                "name": "🌠 Dein Schicksals-Rissmonolith heute",
                "value": f"**{mono[1]} (Lv. {mono[0]})**\n*{mono[2]}*",
                "inline": False,
            },
            {
                "name": "🔨 Goraks Schmiede-Resonanz",
                "value": f"**`{smith_luck}%` Gunst der Esse** (Empfohlener Versuch: mit Segensrolle)",
                "inline": True,
            },
            {
                "name": "🗺️ Empfohlene Jagdzone",
                "value": f"**{rng.choice(zones)}**",
                "inline": True,
            },
            {
                "name": "✨ Aktive Sternen-Konstellation",
                "value": f"*{rng.choice(blessings)}*",
                "inline": False,
            },
        ],
        "footer": {"text": f"Gültig am {time.strftime('%d.%m.%Y')} • Aeryndor Schicksals-Orakel"},
    }


# ============================================================================
# PANEL-DEFINITIONEN (FULL-WIDTH MARKDOWN CONTENT + DISCORD COMPONENTS V2)
# ============================================================================
def embed_to_markdown_content(emb: dict) -> str:
    """Konvertiert ein Embed-Dict in großformatiges, extrem gut lesbares Vollbreiten-Markdown."""
    parts = []
    if emb.get("title"):
        parts.append(f"# {emb['title']}")
    if emb.get("description"):
        parts.append(emb["description"])
    for f in emb.get("fields") or []:
        fname = f.get("name", "")
        fval = f.get("value", "")
        if fname:
            parts.append(f"## {fname}\n{fval}")
        elif fval:
            parts.append(fval)
    if emb.get("footer", {}).get("text"):
        parts.append(f"──────────────────────────────\n*{emb['footer']['text']}*")
    out = "\n\n".join(parts)
    return out[:1950] if len(out) > 1950 else out


def get_ki_panel_payload() -> dict:
    content = (
        "# 🤖 AERYNDOR KI-CHRONIST & INTERAKTIVES SPIELER-PANEL\n\n"
        "Willkommen im interaktiven **KI- & Kommando-Zentrum von Aeryndor**! "
        "Wähle einfach unten eine Funktion per Button-Klick oder aus dem Auswahlmenü:\n\n"
        "### 🤖 KI-Chronist von Seiryu befragen\n"
        "Öffnet ein Frage-Fenster für Sofort-Antworten zu **Rissmonolithen (Lv. 5–90 & 3 Stufen), KI-Helden (Bots), 3 Gebietsbossen (15m), Map-2-Dungeonboss Malakor, Klassen, Skills & Schmied (+9)**.\n\n"
        "### 🔍 Live Charakter-Dossier abfragen\n"
        "Inspiziere jeden Helden live vom Server: **Level, Rang & Rangpunkte, angelegte Ausrüstung (+0 bis +9), Skills, Reittier & Begleiter**.\n\n"
        "### 🏆 Live Top-10 Ehrenhalle & 🟢 Server-Radar\n"
        "Zeigt dir in Echtzeit die **10 mächtigsten Helden**, aktive **Rissmonolithen** sowie aktuelle **Spielerzahlen**.\n\n"
        "### 🎲 Persönliches Tages-Orakel\n"
        "Ziehe deinen heutigen **Schicksals-Rissmonolithen** und deine **Schmiede-Resonanz** für Upgrades bis **+9**.\n\n"
        "*💡 Hinweis: Alle Antworten aus diesem Panel erscheinen **nur für dich sichtbar**, damit dieser Kanal jederzeit sauber und übersichtlich bleibt!*"
    )

    components = [
        {
            "type": 1,
            "components": [
                {
                    "type": 2,
                    "style": 1,  # Primary (Blurple)
                    "label": "KI-Chronist fragen",
                    "emoji": {"name": "🤖"},
                    "custom_id": "btn_open_ai_modal",
                },
                {
                    "type": 2,
                    "style": 3,  # Success (Green)
                    "label": "Charakter-Dossier (Live-Suche)",
                    "emoji": {"name": "🔍"},
                    "custom_id": "btn_open_char_modal",
                },
                {
                    "type": 2,
                    "style": 2,  # Secondary
                    "label": "Live Top-10 Rangliste",
                    "emoji": {"name": "🏆"},
                    "custom_id": "btn_show_leaderboard",
                },
                {
                    "type": 2,
                    "style": 2,
                    "label": "Server- & Riss-Radar",
                    "emoji": {"name": "🟢"},
                    "custom_id": "btn_show_status",
                },
                {
                    "type": 2,
                    "style": 2,
                    "label": "Tages-Orakel",
                    "emoji": {"name": "🎲"},
                    "custom_id": "btn_daily_oracle",
                },
            ],
        },
        {
            "type": 1,
            "components": [
                {
                    "type": 3,  # String Select Menu
                    "custom_id": "select_wiki_topic",
                    "placeholder": "📚 Aeryndor-Enzyklopädie: Wähle ein Thema für Sofort-Infos...",
                    "min_values": 1,
                    "max_values": 1,
                    "options": [
                        {
                            "label": "Alle 18 Rissmonolithen (Lv. 5 bis Lv. 90)",
                            "value": "topic_monoliths",
                            "description": "Vom Rissmonolith des Erwachens bis zum Ursprungsspalt",
                            "emoji": {"name": "🔮"},
                        },
                        {
                            "label": "18 Ränge, Rangfarben & Schadensboni",
                            "value": "topic_ranks",
                            "description": "Von Tödlich bis Unsterblich (+40% Monster / +20% HM)",
                            "emoji": {"name": "📊"},
                        },
                        {
                            "label": "Klassen & Fertigkeiten (M1 → G1 → P → L1)",
                            "value": "topic_classes",
                            "description": "Klingenwächter, Schattenjäger, Runenkrieger & Seelenweber",
                            "emoji": {"name": "⚔️"},
                        },
                        {
                            "label": "Schmied (+0 bis +9) & Reine Seelensplitter",
                            "value": "topic_blacksmith",
                            "description": "Erfolgschancen, Segensrollen & Runen-Verzauberungen",
                            "emoji": {"name": "🔨"},
                        },
                        {
                            "label": "Reittiere (Lv. 1–50) & Begleiter (Lv. 1–120)",
                            "value": "topic_mounts",
                            "description": "Militärgaul (Lv. 50), Pet bis Lv. 120 & alle 24 Pet-Skills",
                            "emoji": {"name": "🐎"},
                        },
                        {
                            "label": "KI-Helden (Bots), Tapferkeitsumhänge & Koop-Raids",
                            "value": "topic_bots",
                            "description": "Intelligente Umhänge, Riss-Erweckung (Stufe 2/3) & Weltboss-Hilfe",
                            "emoji": {"name": "🤖"},
                        },
                        {
                            "label": "3 Gebietsbosse (15 Min.) & Map-2-Dungeonboss Malakor",
                            "value": "topic_bosses",
                            "description": "Lykos (Lv. 20), Brutaler Hauptmann (Lv. 35) & Malakor (Lv. 35)",
                            "emoji": {"name": "👑"},
                        },
                        {
                            "label": "Kaeryu, Seiryu, Bakra & Der Erste Bruch (Lore)",
                            "value": "topic_lore",
                            "description": "Die Geschichte der Ersten Hüter und der offenen Welt",
                            "emoji": {"name": "🏛️"},
                        },
                    ],
                }
            ],
        },
    ]
    return {"content": content, "embeds": [], "flags": 4, "components": components}


def build_discord_ranks_embed() -> dict:
    return {
        "title": "🎖️ AERYNDOR • OFFIZIELLE DISCORD-RANGHIERARCHIE",
        "color": 0xFFD700,
        "description": (
            "Alle **34 Discord-Ränge** sind nach unserer offiziellen Aeryndor-Hierarchie geordnet — "
            "von den **Team- und Verwaltungsrängen** über **Community-Ehrenränge** und **Klassenränge** "
            "bis zu den klassenunabhängigen **Spielerrängen (Wanderer bis Legende von Aeryndor)**:"
        ),
        "fields": [
            {
                "name": "👑 1. Team- und Verwaltungsränge (01–09)",
                "value": (
                    "• `01` **👑 Gründer** *(Gold)* — Serverinhaber\n"
                    "• `02` **⚜️ Projektleitung** *(Dunkelgold)* — Projektverwaltung\n"
                    "• `03` **💻 Entwickler** *(Blau)* — Entwicklung\n"
                    "• `04` **🛡️ Administrator** *(Rot)* — Serververwaltung\n"
                    "• `05` **🔮 Game Master** *(Violett)* — Ingame-Support\n"
                    "• `06` **⚔️ Moderator** *(Türkis)* — Discord-Moderation\n"
                    "• `07` **🤝 Supporter** *(Grün)* — Spielerhilfe\n"
                    "• `08` **🎪 Eventmeister** *(Orange)* — Events und Turniere\n"
                    "• `09` **🧪 Tester** *(Hellblau)* — Spieltests"
                ),
                "inline": False,
            },
            {
                "name": "🌟 2. Besondere Community-Ränge",
                "value": (
                    "• **🌟 Pionier** — Spieler der ersten Stunde\n"
                    "• **💎 Server-Booster** — Discord-Serverboost\n"
                    "• **🏆 PvP-Champion** — Aktueller Turniersieger\n"
                    "• **⚡ Rissbezwinger** — Besondere Rissmonolithen-Erfolge\n"
                    "• **🐉 Bossjäger** — Besondere Boss-Erfolge\n"
                    "• **💰 Handelsfürst** — Handels- und Markterfolge\n"
                    "• **🎬 Content Creator** — Videos und Streams\n"
                    "• **❤️ Community-Held** — Besondere Community-Beiträge\n"
                    "• **🏅 Eventgewinner** — Gewonnenes Community-Event\n"
                    "• **🏛️ Beta-Legende** — Teilnahme an der Beta"
                ),
                "inline": False,
            },
            {
                "name": "⚔️ 3. Klassenränge & Heimatstädte",
                "value": (
                    "• **⚔️ Klingenwächter** • **🗡️ Schattenjäger** • **🔮 Runenkrieger** • **✨ Seelenweber**\n"
                    "• **🏰 Kaeryu • Stadt der Wächter** • **🏛️ Seiryu • Stadt des Wissens**"
                ),
                "inline": False,
            },
            {
                "name": "📜 4. Spielerränge – Aeryndor-Stil (Klassenunabhängig)",
                "value": (
                    "• **👑 Legende von Aeryndor** — Besondere Erfolge\n"
                    "• **🌌 Monolithenwächter** — Freischaltung ab **Level 100**\n"
                    "• **🔮 Monolithenjäger** — Freischaltung ab **Level 80**\n"
                    "• **🐉 Drachenbezwinger** — Freischaltung ab **Level 60**\n"
                    "• **🎖️ Veteran** — Freischaltung ab **Level 40**\n"
                    "• **🛡️ Krieger** — Freischaltung ab **Level 25**\n"
                    "• **📜 Abenteurer** — Freischaltung ab **Level 10**\n"
                    "• **🧭 Wanderer** — Neuer Spieler"
                ),
                "inline": False,
            },
        ],
        "footer": {"text": "Aeryndor Discord-Rangsystem • Klassenunabhängige Aufstiegsränge"},
    }


def get_role_panel_payload() -> dict:
    content = (
        "# 🎭 WÄHLE DEINE STADT-, KLASSEN- & SPIELER-ROLLEN\n\n"
        "Klicke einfach auf die unteren Buttons, um deine **Discord-Rollen** sofort zu aktivieren *(ein erneuter Klick entfernt die Rolle wieder)*:\n\n"
        "### 🏰 1. Deine Heimatstadt in Aeryndor\n"
        "• **🏰 Kaeryu — Stadt der Wächter**  oder  **🏛️ Seiryu — Stadt des Wissens**\n\n"
        "### ⚔️ 2. Deine Heldenklasse (Klassenränge)\n"
        "• **⚔️ Klingenwächter**  •  **🗡️ Schattenjäger**  •  **🔮 Runenkrieger**  •  **✨ Seelenweber**\n\n"
        "### 🧭 3. Spielerränge (Aeryndor-Stil) & Event-Ping\n"
        "• **🧭 Wanderer** *(Neuer Spieler)*  •  **📜 Abenteurer** *(Ab Level 10)*  •  **🔔 Weltboss- & Event-Ping**\n"
        "• *Höhere Spielerränge (**🛡️ Krieger Lv.25**, **🎖️ Veteran Lv.40**, **🐉 Drachenbezwinger Lv.60**, **🔮 Monolithenjäger Lv.80**, **🌌 Monolithenwächter Lv.100** & **👑 Legende von Aeryndor**) sind klassenunabhängig für alle Helden erreichbar!*"
    )

    components = [
        {
            "type": 1,
            "components": [
                {"type": 2, "style": 4, "label": "Kaeryu (Wächter)", "emoji": {"name": "🏰"}, "custom_id": "role_kaeryu"},
                {"type": 2, "style": 1, "label": "Seiryu (Wissen)", "emoji": {"name": "🏛️"}, "custom_id": "role_seiryu"},
                {"type": 2, "style": 2, "label": "Wanderer (Start)", "emoji": {"name": "🧭"}, "custom_id": "role_wanderer"},
                {"type": 2, "style": 3, "label": "Abenteurer (Lv. 10+)", "emoji": {"name": "📜"}, "custom_id": "role_adventurer"},
                {"type": 2, "style": 3, "label": "Weltboss- & Event-Ping", "emoji": {"name": "🔔"}, "custom_id": "role_boss_ping"},
            ],
        },
        {
            "type": 1,
            "components": [
                {"type": 2, "style": 2, "label": "Klingenwächter", "emoji": {"name": "⚔️"}, "custom_id": "role_warrior"},
                {"type": 2, "style": 2, "label": "Schattenjäger", "emoji": {"name": "🗡️"}, "custom_id": "role_assassin"},
                {"type": 2, "style": 2, "label": "Runenkrieger", "emoji": {"name": "🔮"}, "custom_id": "role_mage"},
                {"type": 2, "style": 2, "label": "Seelenweber", "emoji": {"name": "✨"}, "custom_id": "role_shaman"},
                {"type": 2, "style": 1, "label": "Alle Discord-Ränge", "emoji": {"name": "🎖️"}, "custom_id": "btn_show_discord_ranks"},
            ],
        },
    ]
    return {"content": content, "embeds": [], "flags": 4, "components": components}


def get_status_panel_payload(stats: dict = None) -> dict:
    if stats is None:
        stats = fetch_live_game_stats()
    lb = stats.get("leaderboard") or []
    top3 = []
    for i, p in enumerate(lb[:3]):
        medal = ["🥇", "🥈", "🥉"][i]
        top3.append(f"{medal} **[{p.get('rankName', 'Neutral')}] {p.get('name')}** — **Lv. {p.get('level', 1)} {p.get('className', '')}**")
    top3_str = "\n\n".join(top3) if top3 else "• *Noch keine Helden registriert.*"

    content = (
        "# 🟢 AERYNDOR LIVE-SERVERSTATUS & OFFIZIELLE PORTALE\n\n"
        "Unser 3D Open-World Gameserver, die Datenbank, das Userpanel und die Live-Rangliste sind rund um die Uhr (**24/7**) synchronisiert.\n\n"
        "## 🖥️ Live Server-Telemetrie\n\n"
        "• **Server-Status:** 🟢 **ONLINE (24/7 Echtzeit-Welt • 144+ FPS Engine • Patch v5.0)**\n\n"
        f"• **Spieler Online:** **{stats.get('onlinePlayers', 0)}**  •  **Registrierte Helden:** **{stats.get('registeredCharacters', 0)}**\n\n"
        f"• **Aktive Rissmonolithen:** **{stats.get('activeMonoliths', 18)} Stufen** (*Level 5 bis Level 90 — Schlafend, Instabil & Erweckt + Level-Elitebosse*)\n\n"
        "• **Open-World, Bosse & KI v5.0:** **3 Gebietsbosse (`15 Min. Respawn`)** • **Map-2-Dungeonboss Malakor (`Lv. 35`)** • **12 Autonome KI-Helden (`KI v5.0 • NPC-Quests, Stadt-KI & Koop-Raids`)**\n\n"
        "## 🏆 Top-3 Helden der Ehrenhalle\n\n"
        f"{top3_str}\n\n"
        "## 🌐 Offizielle Webseiten-Links\n\n"
        f"🏰 **Startseite & Userpanel (+250 Drachenmünzen):**  {PUBLIC_SITE_URL}\n\n"
        f"🏆 **Ruhmeshalle (Live-Rangliste & Charakter-Dossier):**  {PUBLIC_SITE_URL}/rangliste\n\n"
        f"⚡ **PC-Client & Smart-Launcher Download:**  {PUBLIC_SITE_URL}/download\n\n"
        f"⚙️ **Alle 10 Spielsysteme, KI-Helden & Bosse:**  {PUBLIC_SITE_URL}/systeme\n\n"
        f"📜 **Offizielle Lore & Chronik (Kapitel I–VIII):**  {PUBLIC_SITE_URL}/lore\n\n"
        f"🎮 **Sofort im Browser spielen:**  {PUBLIC_SITE_URL}/play\n\n"
        "💬 **Dauerhafter Discord-Einladungslink:**  https://discord.gg/Q4gnqSAaSc"
    )
    components = [
        {
            "type": 1,
            "components": [
                {"type": 2, "style": 3, "label": "Live-Status prüfen", "emoji": {"name": "🔄"}, "custom_id": "btn_show_status"},
                {"type": 2, "style": 1, "label": "Top-10 Rangliste", "emoji": {"name": "🏆"}, "custom_id": "btn_show_leaderboard"},
                {"type": 2, "style": 1, "label": "Charakter-Dossier suchen", "emoji": {"name": "🔍"}, "custom_id": "btn_open_char_modal"},
                {"type": 2, "style": 2, "label": "KI-Chronist fragen", "emoji": {"name": "🤖"}, "custom_id": "btn_open_ai_modal"},
            ],
        },
        {
            "type": 1,
            "components": [
                {"type": 2, "style": 5, "label": "Homepage & Userpanel", "url": PUBLIC_SITE_URL},
                {"type": 2, "style": 5, "label": "Live-Rangliste", "url": f"{PUBLIC_SITE_URL}/rangliste"},
                {"type": 2, "style": 5, "label": "PC-Client Download", "url": f"{PUBLIC_SITE_URL}/download"},
                {"type": 2, "style": 5, "label": "Im Browser spielen", "url": f"{PUBLIC_SITE_URL}/play"},
            ],
        },
    ]
    return {"content": content, "embeds": [], "flags": 4, "components": components}


def get_support_panel_payload() -> dict:
    content = (
        "# 🎫 INTERAKTIVES SUPPORT-, TICKET- & FEEDBACK-ZENTRUM\n\n"
        "Brauchst du Hilfe bei deinem Account, hast du einen Fehler im Spiel entdeckt oder möchtest du eine Idee für Aeryndor vorschlagen?\n"
        "Klicke einfach auf einen der unteren Buttons:\n\n"
        "### 🎫 Support-Ticket öffnen\n"
        "Erstellt automatisch einen eigenen **Support-Thread** für dich und das **🛡️ Game Master Team**.\n\n"
        "### 🐛 Bug-Bericht senden\n"
        f"Öffnet ein kurzes Formular und postet deinen strukturierten Fehlerbericht direkt in <#{CHAN_BUGS_ID}>.\n\n"
        "### 💡 Vorschlag einreichen\n"
        f"Teile deine Idee per Formular direkt in <#{CHAN_IDEAS_ID}> mit der Community.\n\n"
        "### 🤖 KI-Soforthilfe fragen\n"
        "Befrage den KI-Chronisten sofort zu Rissmonolithen, Quests, Klassen und Spielsystemen."
    )
    components = [
        {
            "type": 1,
            "components": [
                {"type": 2, "style": 1, "label": "Support-Ticket öffnen", "emoji": {"name": "🎫"}, "custom_id": "btn_open_ticket_modal"},
                {"type": 2, "style": 4, "label": "Bug-Bericht senden", "emoji": {"name": "🐛"}, "custom_id": "btn_open_bug_modal"},
                {"type": 2, "style": 3, "label": "Vorschlag einreichen", "emoji": {"name": "💡"}, "custom_id": "btn_open_idea_modal"},
                {"type": 2, "style": 2, "label": "KI-Soforthilfe fragen", "emoji": {"name": "🤖"}, "custom_id": "btn_open_ai_modal"},
            ],
        }
    ]
    return {"content": content, "embeds": [], "flags": 4, "components": components}


# ============================================================================
# SETUP DER PANELS, ROLLEN-HIERARCHIE & SLASH-COMMANDS
# ============================================================================
FULL_ADMIN_PERMISSIONS = str((1 << 51) - 1)  # 2251799813685247 (ADMINISTRATOR + alle 51 Einzelrechte)


def ensure_role_hierarchy_and_permissions():
    """Stellt sicher, dass '👑 Gründer' (und die Leitungsränge) alle Vollberechtigungen
    besitzen und in der Discord-Rollenhierarchie strikt über allen anderen Rängen stehen."""
    roles = discord_api("GET", f"/guilds/{GUILD_ID}/roles") or []
    if not roles:
        return

    role_by_id = {r["id"]: r for r in roles if r.get("id")}
    full_admin_role_ids = (
        DISCORD_ROLES_BY_KEY["founder"][0],       # 👑 Gründer
        DISCORD_ROLES_BY_KEY["project_lead"][0],  # ⚜️ Projektleitung
        DISCORD_ROLES_BY_KEY["developer"][0],     # 💻 Entwickler
        DISCORD_ROLES_BY_KEY["admin"][0],         # 🛡️ Administrator
    )
    for rid in full_admin_role_ids:
        r_obj = role_by_id.get(rid)
        if r_obj and str(r_obj.get("permissions")) != FULL_ADMIN_PERMISSIONS:
            discord_api("PATCH", f"/guilds/{GUILD_ID}/roles/{rid}", {"permissions": FULL_ADMIN_PERMISSIONS})

    non_everyone = [r for r in roles if r.get("id") and r["id"] != GUILD_ID]
    non_everyone.sort(key=lambda r: int(r["id"]))
    n = len(non_everyone)
    needs_reorder = any(r.get("position") != (n - idx) for idx, r in enumerate(non_everyone))
    if needs_reorder:
        payload = [{"id": r["id"], "position": n - idx} for idx, r in enumerate(non_everyone)]
        discord_api("PATCH", f"/guilds/{GUILD_ID}/roles", payload)
        print(f"[Setup] Rollen-Hierarchie ({n} Ränge, '👑 Gründer' auf Position {n - 1}) synchronisiert.")


def setup_channels_and_panels() -> dict:
    state = load_bot_state()
    ensure_role_hierarchy_and_permissions()
    chans = discord_api("GET", f"/guilds/{GUILD_ID}/channels") or []

    # 1. Kanal #🤖│ki-panel-und-hilfe sicherstellen
    ki_chan_id = state.get("ki_channel_id")
    found_ki = None
    for c in chans:
        if c.get("id") == ki_chan_id or c.get("name") in ("🤖・ki-hilfe", "🤖│ki-panel-und-hilfe"):
            found_ki = c
            break

    if not found_ki:
        created = discord_api(
            "POST",
            f"/guilds/{GUILD_ID}/channels",
            {
                "name": "🤖・ki-hilfe",
                "type": 0,
                "parent_id": CAT_OFFICIAL_ID,
                "position": 1,
                "topic": f"🤖 Interaktives Aeryndor KI-Panel, Live-Charakter-Suche & Enzyklopädie • 🌐 {PUBLIC_SITE_URL}",
            },
        )
        if created and created.get("id"):
            ki_chan_id = created["id"]
            print(f"[Setup] Kanal #🤖・ki-hilfe erstellt: {ki_chan_id}")
    else:
        ki_chan_id = found_ki["id"]

    state["ki_channel_id"] = ki_chan_id

    # Hilfsfunktion zum Posten oder Aktualisieren einer Panel-Nachricht
    def upsert_panel(channel_id: str, state_key: str, payload: dict):
        if not channel_id:
            return
        msg_id = state.get(state_key)
        if msg_id:
            res = discord_api("PATCH", f"/channels/{channel_id}/messages/{msg_id}", payload)
            if res and res.get("id"):
                print(f"[Setup] Panel '{state_key}' in {channel_id} aktualisiert ({msg_id}).")
                return
        # Falls kein bekannter msg_id existiert, vorhandene Bot-Nachrichten prüfen
        existing_msgs = discord_api("GET", f"/channels/{channel_id}/messages?limit=10") or []
        bot_msgs = [m for m in existing_msgs if m.get("author", {}).get("id") == BOT_ID]
        if bot_msgs and state_key == "status_panel_msg_id":
            target_id = bot_msgs[0]["id"]
            res = discord_api("PATCH", f"/channels/{channel_id}/messages/{target_id}", payload)
            if res and res.get("id"):
                state[state_key] = target_id
                print(f"[Setup] Vorhandenes Status-Panel in {channel_id} übernommen ({target_id}).")
                return
        created_msg = discord_api("POST", f"/channels/{channel_id}/messages", payload)
        if created_msg and created_msg.get("id"):
            state[state_key] = created_msg["id"]
            print(f"[Setup] Neues Panel '{state_key}' in {channel_id} gepostet ({created_msg['id']}).")

    stats = fetch_live_game_stats()
    upsert_panel(ki_chan_id, "ki_panel_msg_id", get_ki_panel_payload())
    upsert_panel(ki_chan_id, "ki_role_panel_msg_id", get_role_panel_payload())
    upsert_panel(CHAN_WELCOME_ID, "welcome_role_panel_msg_id", get_role_panel_payload())
    upsert_panel(CHAN_STATUS_ID, "status_panel_msg_id", get_status_panel_payload(stats))
    upsert_panel(CHAN_SUPPORT_ID, "support_panel_msg_id", get_support_panel_payload())

    # 2. Guild Slash-Commands registrieren (/ki, /charakter, /rangliste, /status, /orakel)
    slash_commands = [
        {
            "name": "ki",
            "description": "🤖 Stelle dem KI-Chronisten von Aeryndor eine Frage zu Lore, Rissmonolithen, Klassen oder Systemen",
            "options": [
                {
                    "name": "frage",
                    "description": "Deine Frage an den KI-Chronisten",
                    "type": 3,
                    "required": True,
                }
            ],
        },
        {
            "name": "charakter",
            "description": "🔍 Inspiziere das Live-Dossier eines Spielers (Level, Rang, Skills M1/G1/P, Mount & Ausrüstung)",
            "options": [
                {
                    "name": "name",
                    "description": "Name des Charakters in Aeryndor",
                    "type": 3,
                    "required": True,
                }
            ],
        },
        {
            "name": "rangliste",
            "description": "🏆 Zeigt die aktuelle Live-Top-10-Rangliste vom Aeryndor-Server",
        },
        {
            "name": "status",
            "description": "🟢 Zeigt den Live-Serverstatus, aktive Rissmonolithen und Spielerzahlen",
        },
        {
            "name": "orakel",
            "description": "🎲 Ziehe dein heutiges Aeryndor Schicksals- & Schmiede-Orakel",
        },
    ]
    discord_api("PUT", f"/applications/{BOT_ID}/guilds/{GUILD_ID}/commands", slash_commands)
    print("[Setup] Guild Slash-Commands (/ki, /charakter, /rangliste, /status, /orakel) registriert.")

    save_bot_state(state)
    return state


# ============================================================================
# INTERACTION HANDLER (BUTTONS, SELECT MENUS, MODALS & SLASH COMMANDS)
# ============================================================================
def handle_interaction(inter: dict, bot_state: dict):
    itype = inter.get("type")
    inter_id = inter.get("id")
    inter_token = inter.get("token")
    member = inter.get("member") or {}
    user = member.get("user") or inter.get("user") or {}
    user_id = user.get("id", "0")
    user_name = member.get("nick") or user.get("global_name") or user.get("username") or "Abenteurer"

    def respond(resp_type: int, data: dict = None):
        payload = {"type": resp_type}
        if data is not None:
            if resp_type == 4 and data.get("embeds") and not data.get("content"):
                emb0 = data["embeds"][0]
                data = dict(data)
                data["content"] = embed_to_markdown_content(emb0)
                data["embeds"] = []
                data["flags"] = int(data.get("flags", 0)) | 4
            payload["data"] = data
        discord_api("POST", f"/interactions/{inter_id}/{inter_token}/callback", payload)

    # 1. Ping
    if itype == 1:
        respond(1)
        return

    # 2. Slash Commands (APPLICATION_COMMAND)
    if itype == 2:
        data = inter.get("data") or {}
        cmd_name = data.get("name", "")
        opts = {o["name"]: o.get("value") for o in (data.get("options") or [])}
        if cmd_name == "ki":
            emb = generate_ai_chronicle_embed(str(opts.get("frage", "")), user_name)
            respond(4, {"embeds": [emb]})
        elif cmd_name == "charakter":
            emb = build_character_dossier_embed(str(opts.get("name", "")))
            respond(4, {"embeds": [emb]})
        elif cmd_name == "rangliste":
            emb = build_leaderboard_embed()
            respond(4, {"embeds": [emb]})
        elif cmd_name == "status":
            emb = build_live_status_embed()
            respond(4, {"embeds": [emb]})
        elif cmd_name == "orakel":
            emb = build_daily_oracle_embed(user_id, user_name)
            respond(4, {"embeds": [emb]})
        return

    # 3. Message Component (Buttons & Select Menus)
    if itype == 3:
        data = inter.get("data") or {}
        cid = data.get("custom_id", "")

        # Self-Role Toggle Buttons
        if cid in ROLE_MAP:
            role_id, role_label = ROLE_MAP[cid]
            current_roles = set(member.get("roles") or [])
            if role_id in current_roles:
                discord_api("DELETE", f"/guilds/{GUILD_ID}/members/{user_id}/roles/{role_id}")
                respond(
                    4,
                    {
                        "flags": 64,
                        "embeds": [
                            {
                                "title": "🎭 Rolle entfernt",
                                "color": 0xEF4444,
                                "description": f"Die Rolle **{role_label}** wurde von deinem Profil entfernt.",
                            }
                        ],
                    },
                )
            else:
                discord_api("PUT", f"/guilds/{GUILD_ID}/members/{user_id}/roles/{role_id}")
                respond(
                    4,
                    {
                        "flags": 64,
                        "embeds": [
                            {
                                "title": "🎭 Rolle zugewiesen!",
                                "color": 0x22C55E,
                                "description": f"Dir wurde die Rolle **{role_label}** erfolgreich verliehen!",
                            }
                        ],
                    },
                )
            return

        # Button: KI-Chronist Modal öffnen
        if cid == "btn_open_ai_modal":
            respond(
                9,  # MODAL
                {
                    "custom_id": "modal_ask_ai",
                    "title": "🤖 KI-Chronist von Aeryndor fragen",
                    "components": [
                        {
                            "type": 1,
                            "components": [
                                {
                                    "type": 4,
                                    "custom_id": "input_ai_question",
                                    "label": "Deine Frage an den Chronisten",
                                    "style": 2,
                                    "min_length": 2,
                                    "max_length": 300,
                                    "placeholder": "z.B. Welcher Rissmonolith spawnt ab Lv. 90? Wie erreiche ich Rang Unsterblich?",
                                    "required": True,
                                }
                            ],
                        }
                    ],
                },
            )
            return

        # Button: Charakter-Dossier Modal öffnen
        if cid == "btn_open_char_modal":
            respond(
                9,  # MODAL
                {
                    "custom_id": "modal_char_lookup",
                    "title": "🔍 Live Charakter-Dossier abfragen",
                    "components": [
                        {
                            "type": 1,
                            "components": [
                                {
                                    "type": 4,
                                    "custom_id": "input_char_name",
                                    "label": "Charaktername im Spiel",
                                    "style": 1,
                                    "min_length": 2,
                                    "max_length": 32,
                                    "placeholder": "Name des Helden eingeben...",
                                    "required": True,
                                }
                            ],
                        }
                    ],
                },
            )
            return

        # Button: Live Top-10 Rangliste
        if cid == "btn_show_leaderboard":
            emb = build_leaderboard_embed()
            respond(4, {"flags": 64, "embeds": [emb]})
            return

        # Button: Live Serverstatus
        if cid == "btn_show_status":
            stats = fetch_live_game_stats()
            emb = build_live_status_embed(stats)
            respond(4, {"flags": 64, "embeds": [emb]})
            # Gleichzeitig auch das Haupt-Statuspanel im Kanal aktualisieren
            status_msg_id = bot_state.get("status_panel_msg_id")
            if status_msg_id:
                discord_api("PATCH", f"/channels/{CHAN_STATUS_ID}/messages/{status_msg_id}", get_status_panel_payload(stats))
            return

        # Button: Tages-Orakel
        if cid == "btn_daily_oracle":
            emb = build_daily_oracle_embed(user_id, user_name)
            respond(4, {"flags": 64, "embeds": [emb]})
            return

        # Button: Alle Discord-Ränge & Hierarchie anzeigen
        if cid == "btn_show_discord_ranks":
            emb = build_discord_ranks_embed()
            respond(4, {"flags": 64, "embeds": [emb]})
            return

        # Select Menu: Aeryndor-Enzyklopädie
        if cid == "select_wiki_topic":
            vals = data.get("values") or []
            choice = vals[0] if vals else ""
            topic_map = {
                "topic_monoliths": "Alle 18 Rissmonolithen und Ursprungsspalt",
                "topic_ranks": "Rangsystem Rangpunkte Rangfarben und Schadensbonus",
                "topic_classes": "Klassen und Fertigkeiten M1 G1 P",
                "topic_blacksmith": "Schmied Gorak +9 Segensrolle und Runenweber",
                "topic_mounts": "Reittiere Mounts und Pets Begleiter",
                "topic_bots": "Bots KI-Helden Tapferkeitsumhang Rissmonolithen erwecken Koop Weltboss",
                "topic_bosses": "3 Gebietsbosse 15 Minuten Respawn und Map-2-Dungeonboss Malakor",
                "topic_lore": "Kaeryu Seiryu und die Geschichte des Ersten Bruchs",
            }
            q_str = topic_map.get(choice, "Allgemeine Übersicht")
            emb = generate_ai_chronicle_embed(q_str, user_name)
            respond(4, {"flags": 64, "embeds": [emb]})
            return

        # Support-Panel Modals
        if cid == "btn_open_ticket_modal":
            respond(
                9,
                {
                    "custom_id": "modal_create_ticket",
                    "title": "🎫 Support-Ticket eröffnen",
                    "components": [
                        {
                            "type": 1,
                            "components": [
                                {
                                    "type": 4,
                                    "custom_id": "ticket_subject",
                                    "label": "Betreff / Charakter-Name",
                                    "style": 1,
                                    "min_length": 3,
                                    "max_length": 80,
                                    "placeholder": "z.B. Account-Frage / Charakter: Schattenklinge",
                                    "required": True,
                                }
                            ],
                        },
                        {
                            "type": 1,
                            "components": [
                                {
                                    "type": 4,
                                    "custom_id": "ticket_body",
                                    "label": "Wie können wir dir helfen?",
                                    "style": 2,
                                    "min_length": 10,
                                    "max_length": 1000,
                                    "placeholder": "Beschreibe dein Anliegen so genau wie möglich...",
                                    "required": True,
                                }
                            ],
                        },
                    ],
                },
            )
            return

        if cid == "btn_open_bug_modal":
            respond(
                9,
                {
                    "custom_id": "modal_report_bug",
                    "title": "🐛 Bug-Bericht einreichen",
                    "components": [
                        {
                            "type": 1,
                            "components": [
                                {
                                    "type": 4,
                                    "custom_id": "bug_title",
                                    "label": "Kurzbeschreibung / Ort des Fehlers",
                                    "style": 1,
                                    "min_length": 3,
                                    "max_length": 90,
                                    "placeholder": "z.B. UI-Anzeige beim Schmied in Kaeryu",
                                    "required": True,
                                }
                            ],
                        },
                        {
                            "type": 1,
                            "components": [
                                {
                                    "type": 4,
                                    "custom_id": "bug_steps",
                                    "label": "Details & Schritte zur Reproduktion",
                                    "style": 2,
                                    "min_length": 10,
                                    "max_length": 1000,
                                    "placeholder": "Was genau ist passiert und wie lässt es sich nachstellen?",
                                    "required": True,
                                }
                            ],
                        },
                    ],
                },
            )
            return

        if cid == "btn_open_idea_modal":
            respond(
                9,
                {
                    "custom_id": "modal_submit_idea",
                    "title": "💡 Vorschlag für Aeryndor einreichen",
                    "components": [
                        {
                            "type": 1,
                            "components": [
                                {
                                    "type": 4,
                                    "custom_id": "idea_title",
                                    "label": "Titel deiner Idee",
                                    "style": 1,
                                    "min_length": 3,
                                    "max_length": 90,
                                    "placeholder": "z.B. Neues Gilden-Turnier am Wochenende",
                                    "required": True,
                                }
                            ],
                        },
                        {
                            "type": 1,
                            "components": [
                                {
                                    "type": 4,
                                    "custom_id": "idea_body",
                                    "label": "Beschreibung deines Vorschlags",
                                    "style": 2,
                                    "min_length": 10,
                                    "max_length": 1000,
                                    "placeholder": "Warum würde dieses Feature Aeryndor bereichern?",
                                    "required": True,
                                }
                            ],
                        },
                    ],
                },
            )
            return

    # 4. Modal Submissions (MODAL_SUBMIT)
    if itype == 5:
        data = inter.get("data") or {}
        cid = data.get("custom_id", "")
        fields = {}
        for row in data.get("components") or []:
            for comp in row.get("components") or []:
                fields[comp.get("custom_id", "")] = comp.get("value", "")

        if cid == "modal_ask_ai":
            q_val = fields.get("input_ai_question", "")
            emb = generate_ai_chronicle_embed(q_val, user_name)
            respond(4, {"flags": 64, "embeds": [emb]})
            return

        if cid == "modal_char_lookup":
            c_val = fields.get("input_char_name", "")
            emb = build_character_dossier_embed(c_val)
            respond(4, {"flags": 64, "embeds": [emb]})
            return

        if cid == "modal_create_ticket":
            subj = fields.get("ticket_subject", "Support-Anfrage")
            body = fields.get("ticket_body", "")
            thread = discord_api(
                "POST",
                f"/channels/{CHAN_SUPPORT_ID}/threads",
                {
                    "name": f"🎫・ticket-{user_name[:16]}-{int(time.time()) % 10000}",
                    "type": 11,  # PUBLIC_THREAD in support channel
                    "auto_archive_duration": 1440,
                },
            )
            if thread and thread.get("id"):
                tid = thread["id"]
                ai_hint = generate_ai_chronicle_embed(f"{subj} {body}", user_name)
                discord_api(
                    "POST",
                    f"/channels/{tid}/messages",
                    {
                        "content": f"<@{user_id}> Willkommen in deinem persönlichen Support-Ticket!",
                        "embeds": [
                            {
                                "title": f"🎫 Support-Ticket: {subj}",
                                "color": 0x38BDF8,
                                "description": f"**Erstellt von:** <@{user_id}> (`{user_name}`)\n\n**Beschreibung:**\n{body}",
                                "footer": {"text": "Ein Game Master wird sich in Kürze melden • KI-Ersteinschätzung unten"},
                            },
                            ai_hint,
                        ],
                    },
                )
                respond(
                    4,
                    {
                        "flags": 64,
                        "embeds": [
                            {
                                "title": "✅ Support-Ticket erstellt!",
                                "color": 0x22C55E,
                                "description": f"Dein Ticket wurde erfolgreich geöffnet: <#{tid}>\nUnser KI-Chronist hat dort bereits erste passende Hinweise für dich hinterlegt!",
                            }
                        ],
                    },
                )
            else:
                respond(4, {"flags": 64, "content": "✅ Deine Anfrage wurde an das Support-Team übermittelt!"})
            return

        if cid == "modal_report_bug":
            b_title = fields.get("bug_title", "Fehlerbericht")
            b_steps = fields.get("bug_steps", "")
            discord_api(
                "POST",
                f"/channels/{CHAN_BUGS_ID}/messages",
                {
                    "embeds": [
                        {
                            "title": f"🐛 Bug-Meldung: {b_title}",
                            "color": 0xEF4444,
                            "description": b_steps,
                            "fields": [{"name": "Gemeldet von", "value": f"<@{user_id}> (`{user_name}`)", "inline": True}],
                            "footer": {"text": f"Eingereicht über das Aeryndor Support-Panel • {time.strftime('%d.%m.%Y %H:%M')}"},
                        }
                    ]
                },
            )
            respond(
                4,
                {
                    "flags": 64,
                    "embeds": [
                        {
                            "title": "✅ Bug-Bericht eingereicht!",
                            "color": 0x22C55E,
                            "description": f"Vielen Dank für deine Mithilfe! Dein Bericht wurde in <#{CHAN_BUGS_ID}> veröffentlicht.",
                        }
                    ],
                },
            )
            return

        if cid == "modal_submit_idea":
            i_title = fields.get("idea_title", "Community-Vorschlag")
            i_body = fields.get("idea_body", "")
            discord_api(
                "POST",
                f"/channels/{CHAN_IDEAS_ID}/messages",
                {
                    "embeds": [
                        {
                            "title": f"💡 Community-Vorschlag: {i_title}",
                            "color": 0xFACC15,
                            "description": i_body,
                            "fields": [{"name": "Vorgeschlagen von", "value": f"<@{user_id}> (`{user_name}`)", "inline": True}],
                            "footer": {"text": f"Eingereicht über das Aeryndor Feedback-Panel • {time.strftime('%d.%m.%Y %H:%M')}"},
                        }
                    ]
                },
            )
            respond(
                4,
                {
                    "flags": 64,
                    "embeds": [
                        {
                            "title": "💡 Vorschlag veröffentlicht!",
                            "color": 0x22C55E,
                            "description": f"Deine Idee wurde erfolgreich in <#{CHAN_IDEAS_ID}> zur Diskussion gestellt!",
                        }
                    ],
                },
            )
            return


# ============================================================================
# MINIMALER RFC-6455 TLS-WEBSOCKET-CLIENT FÜR DISCORD GATEWAY V10
# ============================================================================
class DiscordGatewaySocket:
    def __init__(self, host: str = "gateway.discord.gg", path: str = "/?v=10&encoding=json"):
        self.host = host
        self.path = path
        self.sock = None
        self.send_lock = threading.Lock()
        self.closed = False

    def connect(self):
        raw_sock = socket.create_connection((self.host, 443), timeout=30)
        ctx = ssl.create_default_context()
        self.sock = ctx.wrap_socket(raw_sock, server_hostname=self.host)
        ws_key = base64.b64encode(os.urandom(16)).decode("ascii")
        handshake = (
            f"GET {self.path} HTTP/1.1\r\n"
            f"Host: {self.host}\r\n"
            f"Upgrade: websocket\r\n"
            f"Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {ws_key}\r\n"
            f"Sec-WebSocket-Version: 13\r\n"
            f"User-Agent: AeryndorKIBot/2.0\r\n\r\n"
        )
        self.sock.sendall(handshake.encode("ascii"))
        resp_buf = b""
        while b"\r\n\r\n" not in resp_buf:
            chunk = self.sock.recv(1024)
            if not chunk:
                raise ConnectionError("WebSocket Handshake fehlgeschlagen (EOF)")
            resp_buf += chunk
        header_part, leftover = resp_buf.split(b"\r\n\r\n", 1)
        if b"101" not in header_part.splitlines()[0]:
            raise ConnectionError(f"Ungültige Handshake-Antwort: {header_part.decode('latin1', errors='ignore')}")
        self._rx_buf = leftover
        self.sock.settimeout(75.0)

    def _read_exact(self, n: int) -> bytes:
        while len(self._rx_buf) < n:
            chunk = self.sock.recv(max(4096, n - len(self._rx_buf)))
            if not chunk:
                raise ConnectionError("Gateway-Socket geschlossen")
            self._rx_buf += chunk
        out = self._rx_buf[:n]
        self._rx_buf = self._rx_buf[n:]
        return out

    def recv_frame(self):
        b1, b2 = self._read_exact(2)
        opcode = b1 & 0x0F
        masked = (b2 & 0x80) != 0
        length = b2 & 0x7F
        if length == 126:
            length = struct.unpack("!H", self._read_exact(2))[0]
        elif length == 127:
            length = struct.unpack("!Q", self._read_exact(8))[0]
        mask_key = self._read_exact(4) if masked else b""
        payload = self._read_exact(length) if length > 0 else b""
        if masked:
            payload = bytes(b ^ mask_key[i % 4] for i, b in enumerate(payload))
        return opcode, payload

    def send_frame(self, opcode: int, payload: bytes):
        if self.closed or not self.sock:
            return
        fin_op = 0x80 | (opcode & 0x0F)
        mask_key = os.urandom(4)
        length = len(payload)
        header = bytearray([fin_op])
        if length < 126:
            header.append(0x80 | length)
        elif length < 65536:
            header.append(0x80 | 126)
            header.extend(struct.pack("!H", length))
        else:
            header.append(0x80 | 127)
            header.extend(struct.pack("!Q", length))
        header.extend(mask_key)
        masked_payload = bytes(b ^ mask_key[i % 4] for i, b in enumerate(payload))
        with self.send_lock:
            self.sock.sendall(bytes(header) + masked_payload)

    def send_json(self, obj: dict):
        raw = json.dumps(obj).encode("utf-8")
        self.send_frame(1, raw)

    def close(self):
        self.closed = True
        try:
            if self.sock:
                self.sock.close()
        except Exception:
            pass


def run_gateway_forever(bot_state: dict):
    intents_list = [
        (1 << 0) | (1 << 9) | (1 << 12) | (1 << 15),  # Mit MESSAGE_CONTENT falls im Portal aktiviert
        (1 << 0) | (1 << 9) | (1 << 12),              # Fallback ohne privilegierte Intents
    ]
    intent_idx = 0

    # Hintergrund-Thread: Aktualisiert jede Minute das Live-Serverstatus-Panel in #🟢│server-status-und-links
    def status_updater_loop():
        while True:
            time.sleep(60)
            try:
                stats = fetch_live_game_stats()
                msg_id = bot_state.get("status_panel_msg_id")
                if msg_id:
                    discord_api("PATCH", f"/channels/{CHAN_STATUS_ID}/messages/{msg_id}", get_status_panel_payload(stats))
            except Exception as e:
                print(f"[StatusUpdater] Fehler: {e}")

    threading.Thread(target=status_updater_loop, daemon=True).start()

    while True:
        ws = DiscordGatewaySocket()
        seq = None
        stop_hb = threading.Event()
        try:
            print("[Gateway] Verbinde mit wss://gateway.discord.gg/?v=10&encoding=json ...")
            ws.connect()
            opcode, data = ws.recv_frame()
            if opcode != 1:
                raise ConnectionError(f"Unerwarteter erster Opcode: {opcode}")
            hello = json.loads(data.decode("utf-8"))
            hb_interval = float(hello.get("d", {}).get("heartbeat_interval", 41250)) / 1000.0

            def heartbeat_loop():
                while not stop_hb.wait(hb_interval * 0.9):
                    try:
                        ws.send_json({"op": 1, "d": seq})
                    except Exception:
                        break

            threading.Thread(target=heartbeat_loop, daemon=True).start()

            cur_intents = intents_list[intent_idx % len(intents_list)]
            ws.send_json(
                {
                    "op": 2,
                    "d": {
                        "token": TOKEN,
                        "intents": cur_intents,
                        "properties": {"os": "linux", "browser": "aeryndor_ki_bot", "device": "aeryndor_ki_bot"},
                        "presence": {
                            "status": "online",
                            "activities": [{"name": "Aeryndor • KI-Panel & Live-Rangliste", "type": 0}],
                        },
                    },
                }
            )

            while True:
                op, raw_payload = ws.recv_frame()
                if op == 8:  # Close frame
                    close_code = struct.unpack("!H", raw_payload[:2])[0] if len(raw_payload) >= 2 else 0
                    print(f"[Gateway] Close-Frame erhalten: Code {close_code}")
                    if close_code == 4014 and intent_idx == 0:
                        print("[Gateway] Privileged Intent nicht aktiv -> wechsle auf Standard-Intents.")
                        intent_idx = 1
                    break
                if op == 9:  # Ping
                    ws.send_frame(10, raw_payload)
                    continue
                if op != 1 or not raw_payload:
                    continue

                pkt = json.loads(raw_payload.decode("utf-8"))
                if pkt.get("s") is not None:
                    seq = pkt["s"]
                pkt_op = pkt.get("op")
                pkt_t = pkt.get("t")
                pkt_d = pkt.get("d") or {}

                if pkt_op == 11:  # Heartbeat ACK
                    continue
                if pkt_op == 1:   # Heartbeat request
                    ws.send_json({"op": 1, "d": seq})
                    continue
                if pkt_op in (7, 9):  # Reconnect / Invalid Session
                    break

                if pkt_t == "READY":
                    print(f"[Gateway] READY! Eingeloggt als {pkt_d.get('user', {}).get('username')} ({BOT_ID})")

                elif pkt_t == "INTERACTION_CREATE":
                    threading.Thread(target=handle_interaction, args=(pkt_d, bot_state), daemon=True).start()

                elif pkt_t == "MESSAGE_CREATE":
                    author = pkt_d.get("author") or {}
                    if author.get("bot") or author.get("id") == BOT_ID:
                        continue
                    chan_id = pkt_d.get("channel_id")
                    content = (pkt_d.get("content") or "").strip()
                    mentions = [u.get("id") for u in (pkt_d.get("mentions") or [])]
                    is_ki_chan = chan_id == bot_state.get("ki_channel_id")
                    is_mentioned = BOT_ID in mentions or f"<@{BOT_ID}>" in content

                    if (is_ki_chan or is_mentioned) and content:
                        clean_q = content.replace(f"<@{BOT_ID}>", "").replace(f"<@!{BOT_ID}>", "").strip()
                        uname = author.get("global_name") or author.get("username") or "Abenteurer"
                        emb = generate_ai_chronicle_embed(clean_q or "Hilfe", uname)
                        discord_api(
                            "POST",
                            f"/channels/{chan_id}/messages",
                            {
                                "embeds": [emb],
                                "message_reference": {"message_id": pkt_d.get("id")},
                            },
                        )

        except Exception as e:
            print(f"[Gateway] Verbindungsfehler ({e}) – Reconnect in 4s...")
        finally:
            stop_hb.set()
            ws.close()
        time.sleep(4)


if __name__ == "__main__":
    st = setup_channels_and_panels()
    if "--setup-only" in sys.argv:
        print("[Setup] Fertig (--setup-only).")
        sys.exit(0)
    run_gateway_forever(st)
