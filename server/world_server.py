# -*- coding: utf-8 -*-
"""
AERYNDOR: LEGACY OF THE MONOLITHS – Autoritatives Echtzeit-Weltsystem & Kampfkern (20Hz)
Steuert 2048m-Open-World, Dungeons, 3-stufige Rissmonolithen, Weltbosse,
Monster-KI, Drops, Auto-Jagd, Schmied, Runenweberin, Gilden & Handel.
"""

import json
import math
import os
import random
import time
import uuid
from typing import Dict, List, Optional, Tuple

from database import GameDatabase
from bot_navigation import BotNavigator
from game_data import (
    ACTIVE_SKILL_BOOK_IDS,
    ALL_SPIRIT_STONE_IDS,
    BLACKSMITH_RATES,
    BLACKSMITH_TIER_RATES,
    BOT_GAME_RULES_MEMORY,
    CHARACTER_CLASSES,
    CLASS_ALLOWED_WEAPONS,
    DEFAULT_DROP_FILTER,
    DUNGEONS,
    EQUIP_TIERS,
    equip_tier_for_drop_level,
    equip_tier_for_level,
    equip_tier_item_ids,
    get_blacksmith_upgrade_req,
    is_tier_equipment,
    PASSIVE_SKILL_BOOK_IDS,
    resolve_item_template_id,
    SPIRIT_STONE_IDS_BY_GRADE,
    ITEM_TEMPLATES,
    MAPS,
    MAX_HORSE_LEVEL,
    MAX_PET_LEVEL,
    MAX_PET_STAT_POINTS,
    MAX_PLAYER_LEVEL,
    MAJOR_RIFT_MONOLITHS,
    RIFT_MONOLITH_CATALOG,
    MONOLITH_COMBAT_PHASES,
    MONOLITH_RARITIES,
    MONOLITH_STATES,
    MONSTER_TEMPLATES,
    MOUNTS,
    MOUNT_SKIN_DEFS,
    MOUNT_SKIN_MAP,
    HORSE_SKILLS,
    HORSE_SKILL_MAP,
    PASSIVE_SKILL_DEFS,
    PET_SKILL_DEFS,
    PET_SKILL_MAP,
    PETS,
    QUEST_TEMPLATES,
    RARITIES,
    RARITY_ORDER,
    RUNE_BONUS_POOL,
    RUNE_67_BONUS_POOL,
    SLOT_BONUS_SWITCH_POOLS,
    EQUIPMENT_TIERS_10,
    calculate_item_effective_stats,
    exp_needed_for_level,
    get_drop_filter_category,
    get_reputation_rank,
    get_required_horse_medals,
    get_required_pet_exp,
    get_doctrine_skills,
    resolve_doctrine_id,
    roll_slot_bonus,
    roll_67_bonus,
)


def dist2d(x1: float, z1: float, x2: float, z2: float) -> float:
    return math.hypot(x2 - x1, z2 - z1)


def is_in_safe_zone(map_id: str, x: float, z: float) -> bool:
    if map_id == "morgenwacht":
        # 2 äußere Steinbrücken über den Silberstrom (z ≈ 0) sind sichere Übergänge
        for bx, bz, brad in ((-760.0, 9.8, 22.0), (760.0, -16.8, 22.0)):
            if dist2d(x, z, bx, bz) <= brad:
                return True
        # Kaeryu (NW: -820, -780), Seiryu (NE: +820, -780), Nord-Portal zum Orktal (N-Mitte: 0, -1020, r=45),
        # Wheol-Denkmal Innenpodest (Südliche Map 1 oberhalb des Flusses: 0, -180, r=48), Bakra & Hafen/Strand (Süden: 0, +880)
        if (
            dist2d(x, z, -820.0, -780.0) <= 168.0
            or dist2d(x, z, 820.0, -780.0) <= 168.0
            or dist2d(x, z, 0.0, -1020.0) <= 45.0
            or dist2d(x, z, 0.0, -180.0) <= 48.0
            or dist2d(x, z, 0.0, 880.0) <= 185.0
            or (abs(x) <= 220.0 and z >= 960.0)
        ):
            return True
        return False

    # Auf den Standard-Karten (nicht auf dem Orktal-Inselarchipel): 7 Flussbrücken & Süd-Dorf ab z >= 104
    if map_id != "orktal":
        bridges = (
            (0.0, 88.0, 18.0),
            (-210.0, 75.5, 16.0),
            (210.0, 84.7, 16.0),
            (0.0, -87.5, 17.0),
            (-290.0, -92.4, 16.0),
            (290.0, -92.4, 16.0),
            (0.0, -375.0, 28.0),
        )
        for bx, bz, brad in bridges:
            if dist2d(x, z, bx, bz) <= brad:
                return True

        # Südlich des Südflusses (z >= 104) ist auf den Standard-Maps sicheres Garnisons- & Marktplatz-Gebiet
        if z >= 104.0:
            return True
    m = MAPS.get(map_id)
    if not m:
        return False
    if "safeZone" in m:
        sz = m["safeZone"]
        if dist2d(x, z, sz["x"], sz["z"]) <= sz["radius"] + 6.0:
            return True
    for z_def in m.get("zones", []):
        if z_def.get("safe") and dist2d(x, z, float(z_def["x"]), float(z_def["z"])) <= float(z_def.get("radius", 58.0)) + 6.0:
            return True
    return False


# Spezial-Drops des Bonus-Systems: droppen NUR noch bei Bossen & Rissmonolithen (nie bei normalen/Elite-Monstern)
SPECIAL_BONUS_DROP_ITEMS = {
    "item_bonus_adder",    # Gegenstand verstärken (1.-4. Bonus hinzufügen)
    "item_bonus_changer",  # Bonuswandler / Switcher
    "item_blessing_orb",   # Segenskugel (5. Bonus)
    "item_soul_fragment",  # Seelenfragment (6./7. Bonus)
    "mat_soul_stone",      # Seelenstein (6./7. Bonus & +7/+8 Schmied)
    "item_aether_seal",    # Äthersiegel (Bonus schützen)
}

# (itemId, Chance, min. Menge, max. Menge) je Quelle.
# Rangfolge: Gebiets-Weltboss > Dungeonboss > normale Bosse > Rissmonolithen (geringste Chance)
SPECIAL_BONUS_DROP_TABLE = {
    "world_boss": [
        ("item_bonus_changer", 0.90, 2, 3),
        ("item_bonus_adder", 0.85, 1, 2),
        ("mat_soul_stone", 0.60, 1, 2),
        ("item_blessing_orb", 0.40, 1, 1),
        ("item_soul_fragment", 0.30, 1, 1),
        ("item_aether_seal", 0.25, 1, 1),
    ],
    "dungeon_boss": [
        ("item_bonus_changer", 0.65, 1, 2),
        ("item_bonus_adder", 0.55, 1, 2),
        ("mat_soul_stone", 0.40, 1, 1),
        ("item_blessing_orb", 0.20, 1, 1),
        ("item_soul_fragment", 0.15, 1, 1),
        ("item_aether_seal", 0.12, 1, 1),
    ],
    "boss": [
        ("item_bonus_changer", 0.35, 1, 1),
        ("item_bonus_adder", 0.30, 1, 1),
        ("mat_soul_stone", 0.20, 1, 1),
        ("item_blessing_orb", 0.07, 1, 1),
        ("item_soul_fragment", 0.05, 1, 1),
        ("item_aether_seal", 0.05, 1, 1),
    ],
    "monolith": [
        ("item_bonus_changer", 0.14, 1, 1),
        ("item_bonus_adder", 0.12, 1, 1),
        ("mat_soul_stone", 0.08, 1, 1),
        ("item_blessing_orb", 0.02, 1, 1),
        ("item_soul_fragment", 0.015, 1, 1),
        ("item_aether_seal", 0.025, 1, 1),
    ],
}


class WorldAuthority:
    # Map-spezifische Respawn-Zeiten (Monster: 25s, Metin: 120s, Boss: 600s als Standard; hier pro Map anpassbar)
    MAP_RESPAWN_OVERRIDES = {
        # Format z.B.: "grenzland": {"monster": 25.0, "metin": 120.0, "boss": 600.0},
    }
    WORLD_BOSS_AWAKEN_COOLDOWN_SEC = 1800.0  # Max. alle 30 Minuten (1800s) pro Gebiet von Instabil -> Erwacht (Weltboss)

    def get_mob_respawn_sec(self, mob: dict) -> float:
        map_id = mob.get("mapId", "morgenwacht")
        tpl_id = mob.get("templateId", "")
        map_overrides = getattr(self, "MAP_RESPAWN_OVERRIDES", {})
        if map_id in map_overrides:
            cfg = map_overrides[map_id]
            if tpl_id in cfg:
                return float(cfg[tpl_id])
            if mob.get("isBoss") and "boss" in cfg:
                return float(cfg["boss"])
            if mob.get("kind") == "metin" and "metin" in cfg:
                return float(cfg["metin"])
            if "monster" in cfg:
                return float(cfg["monster"])
        if not mob.get("isBoss") and mob.get("kind") != "metin":
            return random.uniform(25.0, 35.0)
        if mob.get("isMapAreaBoss") or mob.get("isBoss"):
            return float(mob.get("respawnSec", 900.0))
        return float(mob.get("respawnSec", 25.0))

    def __init__(self, db: GameDatabase):
        self.db = db
        self.boot_id = uuid.uuid4().hex[:10]
        # Serverseitige Hindernis-Navigation & Navigations-Gedaechtnis der Bots (siehe bot_navigation.py)
        self.nav = BotNavigator(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data"))
        self.players: Dict[str, dict] = {}
        self.parties: Dict[str, dict] = {}
        self.trades: Dict[str, dict] = {}
        self.monsters: Dict[str, dict] = {}
        self.drops: Dict[str, dict] = {}
        self.telegraphs: List[dict] = []
        self.combat_events: List[dict] = []
        self.active_big_notice: Optional[dict] = None
        self.world_boss_cooldown_until: Dict[str, float] = {}
        self.last_world_boss_awakened_at: Dict[str, float] = {}
        now_hm = time.strftime("%H:%M")
        self.chat_history: List[dict] = [
            {
                "id": "sys_welcome",
                "sender": "System",
                "channel": "system",
                "isBot": False,
                "text": "Willkommen in Aeryndor: Legacy of the Monoliths (Level 1–99)! Filter: Allgemein • Gruppe • Gilde • System • Handel • Beute • Bots.",
                "time": now_hm,
            },
            {
                "id": "chat_gm_on",
                "sender": "[GM] Aeryndor",
                "channel": "global",
                "isGM": True,
                "isBot": False,
                "text": "👑 Das GM-Team ist online! Bei Fragen oder Support erreicht ihr uns direkt über die Freundes- & GM-Liste unten rechts 😊✨",
                "time": now_hm,
            },
            {
                "id": "chat_trade_1",
                "sender": "[Bot]Veyron",
                "channel": "trade",
                "isBot": True,
                "text": "💰 Verkaufe Vollmondschwert +6 (+15% Rissmonolithen) & Segensschriftrollen am Marktplatz! 🔥⚔️",
                "time": now_hm,
            },
            {
                "id": "chat_normal_1",
                "sender": "[Bot]Nachtklinge",
                "channel": "normal",
                "isBot": True,
                "text": "Die neuen Rissmonolithen im Norden droppen richtig gut! Gerade Fertigkeitsbuch & Ausrüstung gedroppt 🎉💎",
                "time": now_hm,
            },
            {
                "id": "chat_drops_init",
                "sender": "Beute",
                "channel": "drops",
                "isBot": False,
                "text": "💎 Beute-Protokoll aktiv: Alle gedroppten & erhaltenen Gegenstände (Ausrüstung, Upp-Items, Bücher, Truhen) werden ausschließlich hier im Filter [Beute] aufgelistet.",
                "time": now_hm,
            },
            {
                "id": "chat_global_2",
                "sender": "[Bot]Aurelia",
                "channel": "global",
                "isBot": True,
                "text": "Suche nette Mitspieler für Map 2 Grenzland-Gruppe (Lv. 15–30) – schreibt mir gern im Messenger ❤️✨",
                "time": now_hm,
            },
        ]
        self.event_epoch_start = time.time()
        self.event_rotation = [
            {
                "id": "moonlight_chests",
                "name": "Mondlicht-Schatztruhen (Mondis)",
                "badge": "Drop-Event • Alle Gebiete",
                "icon": "./assets/icons/items/chest/mondlicht_truhe.png",
                "bonusText": "+18% Mondlicht-Truhen Drop im eigenen Levelbereich",
                "description": "Alle Monster & Rissmonolithen im passenden Levelbereich können kostbare Mondlicht-Schatztruhen (Mondis) fallen lassen.",
                "durationSec": 2700,
                "hasDrops": True,
                "dropButtonLabel": "Mondi-Drops",
                "dropTitle": "Mondlicht-Schatztruhe (Mondi) – Mögliche Drops",
                "drops": [
                    {"itemId": "scroll_blessing", "chancePct": 24},
                    {"itemId": "item_bonus_changer", "chancePct": 22},
                    {"itemId": "item_bonus_adder", "chancePct": 20},
                    {"itemId": "book_skill", "chancePct": 16},
                    {"itemId": "mat_soul_stone", "chancePct": 12},
                    {"itemId": "mat_white_pearl", "chancePct": 6},
                ],
            },
            {
                "id": "monolith_eruption",
                "name": "Rissmonolithen-Eruption",
                "badge": "Monolith-Event • Alle Kanäle",
                "icon": "./assets/client_ui/Dynamic island/monolith_red.png",
                "bonusText": "+25% Rissmonolithen-Beute & +20% Seelenstein-Chance",
                "description": "Erhöhte Äther-Dichte: Alle Rissmonolithen gewähren mehr Beute sowie eine höhere Chance auf Fertigkeitsbücher & Seelensteine.",
                "durationSec": 2700,
                "hasDrops": True,
                "dropButtonLabel": "Event-Drops",
                "dropTitle": "Rissmonolithen-Eruption – Bonus-Drops",
                "drops": [
                    {"itemId": "book_skill", "chancePct": 32},
                    {"itemId": "scroll_blessing", "chancePct": 26},
                    {"itemId": "mat_soul_stone", "chancePct": 20},
                    {"itemId": "item_bonus_changer", "chancePct": 14},
                    {"itemId": "item_bonus_adder", "chancePct": 8},
                ],
            },
            {
                "id": "imperial_blessing",
                "name": "Kaiserlicher Segen von Aeryndor",
                "badge": "EXP- & Gold-Schub",
                "icon": "./assets/icons/currency/gold.png",
                "bonusText": "+30% Erfahrungspunkte (EXP) & +25% Gold-Ausbeute",
                "description": "Der Segen der Alten Könige gewährt allen Kämpfern im passenden Map-Levelbereich deutlich mehr Erfahrung und Gold.",
                "durationSec": 2700,
                "hasDrops": False,
                "drops": [],
            },
            {
                "id": "boss_hunt_frenzy",
                "name": "Jagd der Alten Wächter",
                "badge": "Boss- & Schmiede-Event",
                "icon": "./assets/client_ui/Dynamic island/race_boss.png",
                "bonusText": "+25% Boss-Truhen & Schmiede-Perlen Chance",
                "description": "Gebiets-Bosse und Elite-Anführer lassen häufiger wertvolle Boss-Truhen, Segensschriftrollen und Ätherperlen fallen.",
                "durationSec": 2700,
                "hasDrops": True,
                "dropButtonLabel": "Boss-Drops",
                "dropTitle": "Jagd der Alten Wächter – Event-Drops",
                "drops": [
                    {"itemId": "chest_monolith_legend", "chancePct": 30},
                    {"itemId": "chest_moonlight", "chancePct": 25},
                    {"itemId": "scroll_blessing", "chancePct": 22},
                    {"itemId": "mat_white_pearl", "chancePct": 13},
                    {"itemId": "mat_soul_stone", "chancePct": 10},
                ],
            },
        ]
        self.world_event = self._compute_world_event_snapshot()
        self.last_save_time = time.time()
        self._spawn_initial_world_entities()

    def _compute_world_event_snapshot(self) -> dict:
        now = time.time()
        rot = self.event_rotation
        slot_dur = 2700
        total_cycle = slot_dur * len(rot)
        elapsed = max(0.0, now - getattr(self, "event_epoch_start", now)) % total_cycle
        idx = int(elapsed // slot_dur) % len(rot)
        rem_sec = max(1, int(round(slot_dur - (elapsed % slot_dur))))
        cur_ev = rot[idx]
        next_ev = rot[(idx + 1) % len(rot)]
        upcoming = []
        for step in range(1, len(rot)):
            ev_item = rot[(idx + step) % len(rot)]
            starts_in = rem_sec + (step - 1) * slot_dur
            upcoming.append(
                {
                    "id": ev_item["id"],
                    "name": ev_item["name"],
                    "badge": ev_item["badge"],
                    "icon": ev_item["icon"],
                    "bonusText": ev_item["bonusText"],
                    "description": ev_item["description"],
                    "startsInSec": starts_in,
                    "durationSec": ev_item["durationSec"],
                    "hasDrops": ev_item["hasDrops"],
                    "dropButtonLabel": ev_item.get("dropButtonLabel", "Drops"),
                    "dropTitle": ev_item.get("dropTitle", ev_item["name"]),
                    "drops": ev_item.get("drops", []),
                }
            )
        return {
            "id": cur_ev["id"],
            "name": cur_ev["name"],
            "badge": cur_ev["badge"],
            "icon": cur_ev["icon"],
            "bonusText": cur_ev["bonusText"],
            "description": cur_ev["description"],
            "remainingSec": rem_sec,
            "durationSec": cur_ev["durationSec"],
            "hasDrops": cur_ev["hasDrops"],
            "dropButtonLabel": cur_ev.get("dropButtonLabel", "Drops"),
            "dropTitle": cur_ev.get("dropTitle", cur_ev["name"]),
            "drops": cur_ev.get("drops", []),
            "nextEvent": upcoming[0] if upcoming else None,
            "upcoming": upcoming,
        }

    # ========================================================================
    # 1. INITIALISIERUNG DER 3D-WELT-ENTITÄTEN (1200x1200m Open-World & 2–5er Gruppen)
    # ========================================================================
    def _roll_pack_size(self) -> int:
        """Würfelt die Gruppengröße (3 bis 6 Monster):
        Dichte, klassische Level-Gruppen: 3er (32%), 4er (38%), 5er (20%) oder 6er (10%) Gruppen."""
        return random.choices([3, 4, 5, 6], weights=[32, 38, 20, 10], k=1)[0]

    def _spawn_monster_pack(
        self,
        map_id: str,
        pool,
        cx: float,
        cz: float,
        roam_radius: float = 11.0,
        forced_size: Optional[int] = None,
    ) -> List[dict]:
        """Spawnt eine zusammengehörige Monstergruppe (2–5 Monster) eng gruppiert um (cx, cz).
        WICHTIG: In der freien offenen Welt spawnen KEINE Elite- und KEINE Boss-Monster!
        Elite- und Boss-Monster erscheinen ausschließlich aus Rissen/Monolithen als Wellen oder Weltbosse.
        """
        if isinstance(pool, str):
            tpl_pool = [pool]
        else:
            tpl_pool = list(pool)

        # Strikter Filter: Schließe alle Mobs mit isElite oder isBoss für die freie Welt aus!
        non_elite_pool = [
            t for t in tpl_pool
            if not MONSTER_TEMPLATES.get(t, {}).get("isElite")
            and not MONSTER_TEMPLATES.get(t, {}).get("isBoss")
        ]
        if non_elite_pool:
            tpl_pool = non_elite_pool
        else:
            fallback_map = {
                "bandit_captain": "white_oath_crusher",
                "red_boar": "wild_boar",
                "black_bear": "forest_bear",
                "king_tiger": "white_tiger",
                "blackwind_tosu": "blackwind_jakto",
                "blackwind_guryung": "bloodleaf_warrior",
                "savage_general": "savage_minion",
                "orc_general": "orc_warrior",
                "black_orc_giant": "orc_scout",
                "frost_golem": "orc_warrior",
                "crimson_dryad": "desert_scorpion",
                "emerald_titan": "desert_scorpion",
            }
            tpl_pool = [fallback_map.get(t, "grey_wolf") for t in tpl_pool]
        pack_size = forced_size if forced_size is not None else self._roll_pack_size()
        pack_id = f"pack_{uuid.uuid4().hex[:8]}"
        base_angle = random.uniform(0.0, math.pi * 2.0)
        created = []
        for idx in range(pack_size):
            tpl_id = tpl_pool[idx % len(tpl_pool)] if idx < len(tpl_pool) else random.choice(tpl_pool)
            ang = base_angle + (math.pi * 2.0 * idx) / max(1, pack_size) + random.uniform(-0.28, 0.28)
            dist = random.uniform(1.8, 3.8)
            mx = round(cx + math.cos(ang) * dist, 1)
            raw_z = cz + math.sin(ang) * dist
            if map_id == "morgenwacht":
                if cz < 0.0:
                    mz = round(min(-42.0, raw_z), 1)
                else:
                    mz = round(max(42.0, min(920.0, raw_z)), 1)
            elif map_id == "orktal":
                mz = round(raw_z, 1)
            else:
                # Halte Monster aus dem Südfluss (z ≈ 70..108) und Nordfluss (z ≈ -108..-68) heraus
                if cz > 105.0:
                    mz = round(max(115.0, raw_z), 1)
                elif cz > -75.0:
                    mz = round(max(-64.0, min(58.0, raw_z)), 1)
                else:
                    mz = round(min(-114.0, raw_z), 1)
            mob = self._create_monster_instance(
                map_id,
                tpl_id,
                mx,
                mz,
                min(roam_radius, 9.5),
                is_summon=False,
                pack_id=pack_id,
                pack_center_x=cx,
                pack_center_z=cz,
            )
            created.append(mob)
        return created

    def _spawn_initial_world_entities(self):
        # ---------------------------------------------------------------------
        # KONTINENT MORGENWACHT (2800x2800m • Map 1 im Norden [z < 0] & Map 2 im Süden [z > 0] • 3 Bossgebiete)
        # ---------------------------------------------------------------------
        m1_pack_spawns = [
            # --- MAP 1 NORDWEST: Wiesen & Haine rund um Kaeryu (-820, -780) -> Lv. 1–5 ---
            (["stray_dog", "wild_dog"], -620, -780, 12),
            (["stray_dog", "wild_dog"], -580, -710, 12),
            (["stray_dog", "wild_dog", "wild_boar"], -540, -640, 12),
            (["stray_dog", "wild_dog", "grey_wolf"], -640, -590, 12),
            (["wild_dog", "grey_wolf", "wild_boar"], -740, -560, 12),
            (["stray_dog", "wild_dog", "wild_boar"], -840, -560, 12),
            (["wild_dog", "grey_wolf", "wild_boar"], -470, -730, 12),
            (["wild_dog", "wild_boar", "red_boar"], -450, -610, 12),

            # --- MAP 1 NORDOST: Wiesen & Wälder rund um Seiryu (+820, -780) -> Lv. 1–5 ---
            (["stray_dog", "wild_dog"], 620, -780, 12),
            (["stray_dog", "wild_dog"], 580, -710, 12),
            (["stray_dog", "wild_dog", "wild_boar"], 540, -640, 12),
            (["stray_dog", "wild_dog", "grey_wolf"], 640, -590, 12),
            (["wild_dog", "grey_wolf", "wild_boar"], 740, -560, 12),
            (["stray_dog", "wild_dog", "wild_boar"], 840, -560, 12),
            (["wild_dog", "grey_wolf", "wild_boar"], 470, -730, 12),
            (["wild_dog", "wild_boar", "red_boar"], 450, -610, 12),

            # --- MAP 1 NORD-ZENTRUM: Nördlicher Map-1-Levelbereich & Vorfeld des Orktal-Portals (0, -1020 bis z = -620) -> Lv. 3–8 ---
            (["wild_dog", "grey_wolf", "wild_boar"], -145, -1015, 11),
            (["wild_dog", "grey_wolf", "wild_boar"], 145, -1015, 11),
            (["grey_wolf", "wild_boar", "alpha_bloodwolf"], -98, -962, 11),
            (["grey_wolf", "wild_boar", "alpha_bloodwolf"], 98, -962, 11),
            (["grey_wolf", "alpha_bloodwolf", "red_boar"], -190, -925, 12),
            (["grey_wolf", "alpha_bloodwolf", "red_boar"], 190, -925, 12),
            (["grey_wolf", "wild_boar", "alpha_bloodwolf"], -275, -845, 12),
            (["wild_boar", "alpha_bloodwolf", "red_boar"], -135, -855, 12),
            (["alpha_bloodwolf", "red_boar", "forest_bear"], 0, -865, 12),
            (["wild_boar", "alpha_bloodwolf", "red_boar"], 135, -855, 12),
            (["grey_wolf", "wild_boar", "alpha_bloodwolf"], 275, -845, 12),
            (["grey_wolf", "wild_boar"], -315, -755, 13),
            (["alpha_bloodwolf", "red_boar", "forest_bear"], -180, -745, 13),
            (["alpha_bloodwolf", "red_boar", "forest_bear"], -68, -750, 13),
            (["alpha_bloodwolf", "red_boar", "forest_bear"], 68, -750, 13),
            (["alpha_bloodwolf", "red_boar", "forest_bear"], 180, -745, 13),
            (["grey_wolf", "wild_boar"], 315, -755, 13),
            (["grey_wolf", "alpha_bloodwolf", "red_boar"], -215, -645, 13),
            (["alpha_bloodwolf", "red_boar", "forest_bear"], -85, -635, 13),
            (["red_boar", "forest_bear", "grizzly_bear"], 0, -640, 13),
            (["alpha_bloodwolf", "red_boar", "forest_bear"], 85, -635, 13),
            (["grey_wolf", "alpha_bloodwolf", "red_boar"], 215, -645, 13),

            # --- MAP 1 MITTE: Riesige grüne Wiesen, Grasland & Lichtungen (-880..+880, -520..-340) -> Lv. 4–10 ---
            (["grey_wolf", "wild_boar", "alpha_bloodwolf"], -820, -410, 13),
            (["wild_boar", "alpha_bloodwolf", "red_boar"], -680, -450, 13),
            (["alpha_bloodwolf", "red_boar", "forest_bear"], -560, -370, 13),
            (["grey_wolf", "alpha_bloodwolf", "red_boar"], -420, -440, 13),
            (["alpha_bloodwolf", "red_boar", "forest_bear"], -280, -410, 13),
            (["red_boar", "forest_bear", "grizzly_bear"], -140, -430, 13),
            (["forest_bear", "grizzly_bear", "striped_tiger", "white_tiger"], 0, -440, 14),
            (["red_boar", "forest_bear", "grizzly_bear"], 140, -430, 13),
            (["alpha_bloodwolf", "red_boar", "forest_bear"], 280, -410, 13),
            (["grey_wolf", "alpha_bloodwolf", "red_boar"], 420, -440, 13),
            (["alpha_bloodwolf", "red_boar", "forest_bear"], 560, -370, 13),
            (["wild_boar", "alpha_bloodwolf", "red_boar"], 680, -450, 13),
            (["grey_wolf", "wild_boar", "alpha_bloodwolf"], 820, -410, 13),

            # --- MAP 1 SÜD: Äußere Silberstrom-Auen West/Ost (Bären/Tiger Lv. 9–15) & WEOL-DENKMAL GARNISON (Eid-Kämpfer Lv. 16–22) ---
            (["forest_bear", "grizzly_bear", "striped_tiger", "white_tiger"], -760, -145, 13),
            (["forest_bear", "grizzly_bear", "striped_tiger"], -610, -190, 13),
            (["grizzly_bear", "striped_tiger", "white_tiger", "black_bear"], -460, -155, 13),
            (["blackice_bandit", "white_oath_archer", "white_oath_crusher"], -285, -295, 12),
            (["white_oath_archer", "white_oath_crusher", "white_oath_vanguard"], -155, -305, 12),
            (["white_oath_archer", "white_oath_crusher", "white_oath_vanguard"], 0, -310, 12),
            (["white_oath_archer", "white_oath_crusher", "white_oath_vanguard"], 155, -305, 12),
            (["blackice_bandit", "white_oath_archer", "white_oath_crusher"], 285, -295, 12),
            (["blackice_bandit", "white_oath_archer", "white_oath_crusher"], -240, -215, 12),
            (["white_oath_archer", "white_oath_crusher", "white_oath_vanguard"], -115, -225, 12),
            (["white_oath_archer", "white_oath_crusher", "white_oath_vanguard"], 115, -225, 12),
            (["blackice_bandit", "white_oath_archer", "white_oath_crusher"], 240, -215, 12),
            (["blackice_bandit", "white_oath_archer", "white_oath_vanguard"], -245, -125, 12),
            (["blackice_bandit", "white_oath_crusher", "white_oath_vanguard"], -115, -120, 12),
            (["white_oath_archer", "white_oath_crusher", "white_oath_vanguard"], 0, -95, 12),
            (["blackice_bandit", "white_oath_crusher", "white_oath_vanguard"], 115, -120, 12),
            (["blackice_bandit", "white_oath_archer", "white_oath_vanguard"], 245, -125, 12),
            (["grizzly_bear", "striped_tiger", "white_tiger", "black_bear"], 460, -155, 13),
            (["forest_bear", "grizzly_bear", "striped_tiger"], 610, -190, 13),
            (["forest_bear", "grizzly_bear", "striped_tiger", "white_tiger"], 760, -145, 13),

            # --- MAP 1 BOSSGEBIETE (Westliches Gebirge -1080, -480 & Östliches Gebirge +1080, -480) ---
            (["white_tiger", "black_bear", "king_tiger"], -1020, -440, 13),
            (["black_bear", "king_tiger"], -1120, -510, 13),
            (["white_tiger", "black_bear", "king_tiger"], 1020, -440, 13),
            (["black_bear", "king_tiger"], 1120, -510, 13),

            # --- BAKRA-GEBIET NORD (Südlich des Silberstroms, z ∈ [+85, +340]): Map-2-Monster (Schwarzwind & Grenzland-Infanterie) ---
            (["blackwind_soldier", "blackwind_maniac", "blackwind_archer"], -760, 135, 13),
            (["blackwind_soldier", "blackwind_maniac", "blackwind_archer"], -580, 185, 13),
            (["blackwind_maniac", "blackwind_archer", "blackwind_jakto"], -410, 165, 13),
            (["blackwind_soldier", "blackwind_archer", "blackwind_jakto"], -240, 135, 13),
            (["blackwind_archer", "blackwind_jakto", "bloodleaf_warrior"], -90, 195, 13),
            (["blackwind_jakto", "bloodleaf_warrior", "blackwind_tosu"], 0, 175, 14),
            (["blackwind_archer", "blackwind_jakto", "bloodleaf_warrior"], 90, 195, 13),
            (["blackwind_soldier", "blackwind_archer", "blackwind_jakto"], 240, 135, 13),
            (["blackwind_maniac", "blackwind_archer", "blackwind_jakto"], 410, 165, 13),
            (["blackwind_soldier", "blackwind_maniac", "blackwind_archer"], 580, 185, 13),
            (["blackwind_soldier", "blackwind_maniac", "blackwind_archer"], 760, 135, 13),
            (["blackwind_jakto", "bloodleaf_warrior", "blackwind_tosu"], -340, 290, 14),
            (["blackwind_jakto", "bloodleaf_warrior", "blackwind_tosu"], 0, 305, 14),
            (["blackwind_jakto", "bloodleaf_warrior", "blackwind_tosu"], 340, 290, 14),

            # --- BAKRA-GEBIET MITTE & SÜD: Herbstwiesen & Heerlager vor Bakra (z ∈ [+360, +710]) -> Map-2-Monster ---
            (["blackwind_soldier", "blackwind_maniac", "blackwind_archer"], -780, 420, 14),
            (["blackwind_maniac", "blackwind_archer", "blackwind_jakto"], -610, 460, 14),
            (["blackwind_jakto", "bloodleaf_warrior", "blackwind_tosu"], -430, 440, 14),
            (["blackwind_archer", "blackwind_jakto", "bloodleaf_warrior"], -250, 480, 14),
            (["bloodleaf_warrior", "blackwind_tosu", "blackwind_guryung"], -110, 450, 14),
            (["bloodleaf_warrior", "blackwind_tosu", "blackwind_guryung"], 0, 490, 14),
            (["bloodleaf_warrior", "blackwind_tosu", "blackwind_guryung"], 110, 450, 14),
            (["blackwind_archer", "blackwind_jakto", "bloodleaf_warrior"], 250, 480, 14),
            (["blackwind_jakto", "bloodleaf_warrior", "blackwind_tosu"], 430, 440, 14),
            (["blackwind_maniac", "blackwind_archer", "blackwind_jakto"], 610, 460, 14),
            (["blackwind_soldier", "blackwind_maniac", "blackwind_archer"], 780, 420, 14),
            (["blackwind_tosu", "blackwind_guryung", "savage_minion"], -540, 620, 14),
            (["savage_minion", "savage_archer", "savage_duelist", "savage_enforcer"], -380, 640, 14),
            (["savage_minion", "savage_archer", "savage_duelist"], -230, 665, 14),
            (["savage_minion", "savage_archer", "savage_duelist"], 230, 665, 14),
            (["savage_minion", "savage_archer", "savage_duelist", "savage_enforcer"], 380, 640, 14),
            (["blackwind_tosu", "blackwind_guryung", "savage_minion"], 540, 620, 14),
            (["savage_archer", "savage_duelist", "savage_enforcer"], -910, 640, 14),
            (["savage_archer", "savage_duelist", "savage_enforcer"], -1010, 710, 14),
        ]
        for pool, cx, cz, roam in m1_pack_spawns:
            self._spawn_monster_pack("morgenwacht", pool, float(cx), float(cz), float(roam))

        # Zusätzliche dichte Level-Spawns in allen Level-Gebieten von Morgenwacht (Map 1 & Map 2):
        extra_m1_spawns = []
        # 1. Kaeryu-Umland & Westliche Starter-Wiesen (Lv. 1–8)
        for gx in (-980, -900, -820, -740, -660, -580, -500, -420):
            for gz in (-920, -840, -760, -680, -600, -530):
                if dist2d(gx, gz, -820.0, -780.0) >= 162.0:
                    pool = ["stray_dog", "wild_dog"] if dist2d(gx, gz, -820.0, -780.0) < 235.0 else ["stray_dog", "wild_dog", "grey_wolf", "wild_boar"]
                    extra_m1_spawns.append((pool, gx, gz, 12))

        # 2. Seiryu-Umland & Östliche Starter-Wiesen (Lv. 1–8)
        for gx in (420, 500, 580, 660, 740, 820, 900, 980):
            for gz in (-920, -840, -760, -680, -600, -530):
                if dist2d(gx, gz, 820.0, -780.0) >= 162.0:
                    pool = ["stray_dog", "wild_dog"] if dist2d(gx, gz, 820.0, -780.0) < 235.0 else ["stray_dog", "wild_dog", "grey_wolf", "wild_boar"]
                    extra_m1_spawns.append((pool, gx, gz, 12))

        # 3. Nördlicher Map-1-Levelbereich rund um das Orktal-Portal (Wölfe & Keiler • Lv. 3–8)
        for gx in (-310, -230, -150, -75, 0, 75, 150, 230, 310):
            for gz in (-950, -880, -800, -720, -650):
                if dist2d(gx, gz, 0.0, -1020.0) >= 62.0:
                    extra_m1_spawns.append((["grey_wolf", "wild_boar", "alpha_bloodwolf", "red_boar"], gx, gz, 12))

        # 4. Große Zentralwiesen, West- & Ost-Grasland von Map 1 (Lv. 6–15 Bären & Tiger)
        for gx in range(-900, 901, 90):
            for gz in (-510, -430, -360):
                pool = (
                    ["grey_wolf", "wild_boar", "alpha_bloodwolf"]
                    if abs(gx) > 480
                    else ["forest_bear", "grizzly_bear", "striped_tiger", "white_tiger"]
                )
                extra_m1_spawns.append((pool, gx, gz, 13))

        # 5. Süden von Map 1 oberhalb des Silberstroms: Weol-Denkmal Garnison (Eid-Kämpfer Lv. 16–22 innen, Bären/Tiger Lv. 9–15 außen)
        for gx in range(-880, 881, 80):
            for gz in (-285, -210, -135):
                if abs(gx) <= 340:
                    if dist2d(gx, gz, 0.0, -180.0) >= 66.0:
                        extra_m1_spawns.append((["blackice_bandit", "white_oath_archer", "white_oath_crusher", "white_oath_vanguard"], gx, gz, 12))
                else:
                    extra_m1_spawns.append((["forest_bear", "grizzly_bear", "striped_tiger", "white_tiger"], gx, gz, 13))

        # 6. Map 2 Anfangsgebiet Nord & Goldenes Herbsttal (Schwarzwind-Vorhut & Soldaten • Lv. 23–29)
        for gx in range(-880, 881, 70):
            for gz in (95, 160, 225, 290, 350):
                pool = (
                    ["blackwind_soldier", "blackwind_maniac", "blackwind_archer"]
                    if gz < 225
                    else ["blackwind_maniac", "blackwind_archer", "blackwind_jakto"]
                )
                extra_m1_spawns.append((pool, gx, gz, 13))

        # 7. Map 2 Restgebiet Mitte & Süd: Gelbwiesen, Hochland & Heerlager vor Bakra (Lv. 30–38)
        for gx in range(-900, 901, 75):
            for gz in (415, 485, 555, 625, 695):
                if dist2d(gx, gz, 0.0, 880.0) >= 180.0:
                    pool = (
                        ["bloodleaf_warrior", "savage_minion", "savage_archer"]
                        if gz < 555
                        else ["savage_minion", "savage_archer", "savage_duelist", "savage_enforcer"]
                    )
                    extra_m1_spawns.append((pool, gx, gz, 14))

        for pool, cx, cz, roam in extra_m1_spawns:
            if not is_in_safe_zone("morgenwacht", float(cx), float(cz)):
                self._spawn_monster_pack("morgenwacht", pool, float(cx), float(cz), float(roam))

        # Rissmonolithen auf dem 2800x2800m Kontinent (Map 1 im Norden Lv. 5–20 & Map 2 im Süden Lv. 25–35; Lv. 40+ noch nicht vergeben!):
        for _ in range(10):
            self._create_monster_instance("morgenwacht", "metin_sorrow", 0.0, 0.0, 0.0)
            self._create_monster_instance("morgenwacht", "metin_combat", 0.0, 0.0, 0.0)
        for _ in range(7):
            self._create_monster_instance("morgenwacht", "metin_battle", 0.0, 0.0, 0.0)
            self._create_monster_instance("morgenwacht", "metin_greed", 0.0, 0.0, 0.0)
        for _ in range(6):
            self._create_monster_instance("morgenwacht", "metin_black", 0.0, 0.0, 0.0)
            self._create_monster_instance("morgenwacht", "metin_darkness", 0.0, 0.0, 0.0)
            self._create_monster_instance("morgenwacht", "metin_bloodleaf", 0.0, 0.0, 0.0)

        # ---------------------------------------------------------------------
        # 3 FESTE GEBIETSBOSSE AUF DEN 3 BOSS-PLÄTZEN (15 Minuten = 900s Respawn)
        # ---------------------------------------------------------------------
        map_boss_spawns = [
            ("boss_arena_west", "boss_morgenwacht", -1080.0, -480.0, 14.0),
            ("boss_arena_east", "boss_morgenwacht", 1080.0, -480.0, 14.0),
            ("boss_arena_south", "boss_brutal_captain", -960.0, 680.0, 14.0),
        ]
        for arena_id, boss_tpl_id, bx, bz, broam in map_boss_spawns:
            if boss_tpl_id in MONSTER_TEMPLATES:
                b_inst = self._create_monster_instance("morgenwacht", boss_tpl_id, bx, bz, broam)
                b_inst["isMapAreaBoss"] = True
                b_inst["bossArenaId"] = arena_id
                b_inst["respawnSec"] = 900.0

        # ---------------------------------------------------------------------
        # DIE BEDEUTENDEN RISSMONOLITHEN AUF DER OPEN WORLD (Morgenwacht)
        # ---------------------------------------------------------------------
        self._spawn_major_rift_monoliths()
        self._ensure_fallback_nav_obstacles()

    def _ensure_fallback_nav_obstacles(self):
        """Stellt sicher, dass self.nav immer Basis-Kollisionshindernisse (Denkmäler, Flussufer zwischen Brücken, Monolithen) kennt."""
        try:
            from server.bot_navigation import MapObstacles
        except ImportError:
            try:
                from bot_navigation import MapObstacles
            except ImportError:
                return
        if "morgenwacht" in self.nav.maps and self.nav.maps["morgenwacht"].count > 20:
            return
        circles = [
            [0.0, -180.0, 26.0],     # Weol-Denkmal Zentrum
            [0.0, -1020.0, 18.0],    # Nord-Ruinenportal
            [-820.0, -780.0, 9.0],   # Kaeryu Stadtbrunnen
            [820.0, -780.0, 9.0],    # Seiryu Stadtbrunnen
            [0.0, 880.0, 11.0],      # Bakra Marktbrunnen
        ]
        for mob in self.monsters.values():
            if mob.get("mapId") == "morgenwacht" and mob.get("kind") == "metin":
                circles.append([float(mob["x"]), float(mob["z"]), 2.8])
        # Silberstrom-Flussbarrieren außerhalb der beiden Brücken (x ≈ -760 und x ≈ +760)
        segments = [
            [-1380.0, 0.0, -792.0, 0.0, 10.0],
            [-728.0, 0.0, 728.0, 0.0, 10.0],
            [792.0, 0.0, 1380.0, 0.0, 10.0],
        ]
        self.nav.maps["morgenwacht"] = MapObstacles(
            "morgenwacht",
            {"mapId": "morgenwacht", "layoutHash": "fallback_ssot_v1", "circles": circles, "segments": segments, "boxes": []},
        )

    def _pick_random_monolith_coords(
        self, map_id: str, exclude_mob_id: Optional[str] = None, template_id: Optional[str] = None
    ) -> Tuple[float, float]:
        """Wählt zufällige Koordinaten für Rissmonolithen strikt gemäß SSOT Abschnitt 10:
        - Lv. 5 & 10: Map 1 Nord/Mitte (z ∈ [-780, -210])
        - Lv. 15 & 20: Map 1 Mitte/Süd (z ∈ [-480, -85]) -> STRIKT auf Map 1!
        - Lv. 25, 30 & 35: Map 2 Herbstregion (z ∈ [+105, +650]) -> STRIKT auf Map 2!"""
        tpl_lvl = 5
        if template_id and template_id in MONSTER_TEMPLATES:
            tpl_lvl = int(MONSTER_TEMPLATES[template_id].get("level", 5))

        starter_sectors = [
            (-640.0, -360.0, -760.0, -520.0),
            (360.0, 640.0, -760.0, -520.0),
            (-320.0, 320.0, -780.0, -540.0),
            (-840.0, -340.0, -490.0, -230.0),
            (-310.0, 310.0, -490.0, -240.0),
            (340.0, 840.0, -490.0, -230.0),
        ]
        map1_south_sectors = [
            (-820.0, -340.0, -420.0, -90.0),
            (-310.0, 310.0, -380.0, -95.0),
            (340.0, 820.0, -420.0, -90.0),
        ]
        map2_high_sectors = [
            (-780.0, -280.0, 110.0, 340.0),
            (-240.0, 240.0, 110.0, 340.0),
            (280.0, 780.0, 110.0, 340.0),
            (-760.0, -260.0, 360.0, 650.0),
            (-220.0, 220.0, 360.0, 640.0),
            (260.0, 760.0, 360.0, 650.0),
        ]

        if tpl_lvl <= 10:
            sectors = starter_sectors
            fallback_z_range = (-740.0, -220.0)
        elif tpl_lvl <= 20:
            sectors = map1_south_sectors
            fallback_z_range = (-410.0, -95.0)
        else:
            sectors = map2_high_sectors
            fallback_z_range = (110.0, 620.0)

        existing_metins = [
            m for mid, m in self.monsters.items()
            if mid != exclude_mob_id and m.get("mapId") == map_id and m.get("kind") == "metin"
        ]

        sector_counts = []
        for idx, (x_min, x_max, z_min, z_max) in enumerate(sectors):
            cnt = sum(
                1 for m in existing_metins
                if x_min <= float(m["x"]) <= x_max and z_min <= float(m["z"]) <= z_max
            )
            sector_counts.append((cnt, random.random(), idx))
        sector_counts.sort()

        m_def = MAPS.get(map_id, {})
        portals = m_def.get("portals", [])
        safe_zones = []
        if "safeZone" in m_def:
            sz_main = m_def["safeZone"]
            safe_zones.append((float(sz_main["x"]), float(sz_main["z"]), float(sz_main.get("radius", 42.0))))
        for z_def in m_def.get("zones", []):
            if z_def.get("safe"):
                safe_zones.append((float(z_def["x"]), float(z_def["z"]), float(z_def.get("radius", 42.0))))

        for attempt in range(100):
            if attempt < 70:
                _, _, s_idx = sector_counts[attempt % len(sector_counts)]
                x_min, x_max, z_min, z_max = sectors[s_idx]
                rx = random.uniform(x_min, x_max)
                rz = random.uniform(z_min, z_max)
            else:
                rx = random.uniform(-820.0, 820.0)
                rz = random.uniform(fallback_z_range[0], fallback_z_range[1])

            if is_in_safe_zone(map_id, rx, rz):
                continue
            if -55.0 <= rz <= 55.0 or rz >= 710.0 or rz <= -860.0:
                continue
            if any(dist2d(rx, rz, sx_z, sz_z) < (s_rad + 28.0) for sx_z, sz_z, s_rad in safe_zones):
                continue
            if any(dist2d(rx, rz, float(pt["x"]), float(pt["z"])) < 28.0 for pt in portals):
                continue
            min_spacing = 75.0 if attempt < 55 else 38.0
            if any(dist2d(rx, rz, float(m["x"]), float(m["z"])) < min_spacing for m in existing_metins):
                continue

            return round(rx, 1), round(rz, 1)

        return (
            round(random.choice([-450.0, -220.0, 220.0, 450.0]) + random.uniform(-45.0, 45.0), 1),
            round(random.uniform(fallback_z_range[0], fallback_z_range[1]), 1),
        )

    def _get_active_world_boss(self, map_id: str) -> Optional[dict]:
        """Gibt den aktuell lebenden Riss-Weltboss auf dem angegebenen Mapgebiet zurück (falls vorhanden)."""
        for m in self.monsters.values():
            if (
                m.get("mapId") == map_id
                and m.get("state") != "dead"
                and int(m.get("hp", 0)) > 0
                and m.get("isRiftWorldBoss")
            ):
                return m
        return None

    def _get_active_erwacht_monolith(self, map_id: str, exclude_mob_id: Optional[str] = None) -> Optional[dict]:
        """Prüft, ob auf dem angegebenen Mapgebiet bereits ein Erwachter Rissmonolith aktiv ist."""
        for mid, m in self.monsters.items():
            if (
                mid != exclude_mob_id
                and m.get("mapId") == map_id
                and m.get("kind") == "metin"
                and m.get("state") != "dead"
                and int(m.get("hp", 0)) > 0
                and m.get("monolithState") == "erwacht"
            ):
                return m
        return None

    def _get_world_boss_cooldown_remaining(self, map_id: str, now: Optional[float] = None) -> float:
        """Gibt die verbleibende 30-Minuten-Abklingzeit (in Sekunden) zurück, bis im Gebiet wieder ein
        Rissmonolith von 'instabil' auf 'erwacht' (Gebiets-Weltboss) ausgelöst werden kann."""
        if now is None:
            now = time.time()
        cd_until = float(getattr(self, "world_boss_cooldown_until", {}).get(map_id, 0.0) or 0.0)
        return max(0.0, cd_until - now)

    def _roll_monolith_rarity(self, map_id: str, exclude_mob_id: Optional[str] = None) -> str:
        """Alle neu spawnenden Rissmonolithen starten grundsätzlich im Zustand 'normal' ('schlafend').
        In den Zustand 'instabil' oder 'erwacht' wechseln sie erst aktiv im Kampf durch Einsatz von
        1x 'Monolithensplitter' bzw. 1x 'Erwachter Risskern', damit kein ungetöteter instabiler Monolith leer herumsteht!"""
        return "normal"

    def _spawn_major_rift_monoliths(self):
        """Spawnt die bedeutenden Rissmonolithen auf der Open World mit ihren 3 dynamischen Zuständen."""
        for mdef in MAJOR_RIFT_MONOLITHS:
            map_id = mdef["mapId"]
            tpl_id = mdef["templateId"]
            if tpl_id not in MONSTER_TEMPLATES:
                continue
            inst = self._create_monster_instance(map_id, tpl_id, float(mdef["x"]), float(mdef["z"]), 0.0)
            old_id = inst["id"]
            inst["id"] = mdef["id"]
            # Ersetze Schlüssel in self.monsters auf feste ID für gezielte Weltkarten- & Event-Referenz
            for old_k, old_v in list(self.monsters.items()):
                if old_v is inst and old_k != mdef["id"]:
                    self.monsters.pop(old_k, None)
                elif old_v.get("monolithGuardOf") == old_id:
                    old_v["monolithGuardOf"] = mdef["id"]
                elif old_v.get("monolithBossOf") == old_id:
                    old_v["monolithBossOf"] = mdef["id"]
            self.monsters[mdef["id"]] = inst
            inst["isMajorMonolith"] = True
            inst["majorIndex"] = int(mdef["majorIndex"])
            inst["majorTitle"] = mdef["title"]
            inst["worldBossId"] = mdef.get("worldBoss", "boss_lykos")
            inst["spawnX"] = float(mdef["x"])
            inst["spawnZ"] = float(mdef["z"])
            inst["x"] = float(mdef["x"])
            inst["z"] = float(mdef["z"])
            inst["initialState"] = "schlafend"
            inst["maxRiftTier"] = "erwacht"

    def _resolve_monolith_wave_monster(self, mob: dict) -> str:
        """Bestimmt das exakt zum Level des Rissmonolithen passende NORMALE Wächter-/Wellen-Monster (NIEMALS Elite oder Boss!):
        - Lv. 5 Monolith: Lv. 3–5 (Alpha-Blutwolf, Wildschwein, Grauwolf)
        - Lv. 10 Monolith: Lv. 10–12 (Waldbär, Grizzlybär)
        - Lv. 15 Monolith: Lv. 13–15 (Weißer Tiger, Grizzlybär bzw. Weißer-Eid am Weol-Denkmal)
        - Lv. 20 Monolith: Lv. 16–20 (Weißer Tiger / Weißer-Eid-Schwertkämpferin / Schwarzwind-Soldat)
        - Lv. 25 Monolith: Lv. 22–26 (Schwarzwind-Besessener, Schwarzwind-Bogenschütze, Schwarzwind-Jak-To)
        - Lv. 30 Monolith: Lv. 28–30 (Blutblatt-Krieger, Wilder Ergebenen-Krieger, Schwarzwind-Jak-To)
        - Lv. 35+ Monolith: Lv. 30–35 (Wilder Bogenschütze, Wilder Ergebenen-Krieger, Blutblatt-Krieger)"""
        mob_lvl = int(mob.get("level", 5))
        mx = float(mob.get("x", 0.0))
        mz = float(mob.get("z", 0.0))
        in_wheol_oath_zone = (abs(mx) <= 360.0 and -350.0 <= mz <= -50.0)

        if mob_lvl <= 5:
            pool = ("alpha_bloodwolf", "wild_boar", "grey_wolf")
        elif mob_lvl <= 10:
            pool = ("forest_bear", "grizzly_bear")
        elif mob_lvl <= 15:
            pool = ("blackice_bandit", "white_oath_archer") if in_wheol_oath_zone else ("white_tiger", "grizzly_bear")
        elif mob_lvl <= 20:
            if in_wheol_oath_zone:
                pool = ("white_oath_crusher", "white_oath_archer")
            elif mz > 0.0:
                pool = ("blackwind_soldier", "blackwind_maniac")
            else:
                pool = ("white_tiger", "grizzly_bear")
        elif mob_lvl <= 25:
            pool = ("blackwind_maniac", "blackwind_archer", "blackwind_jakto")
        elif mob_lvl <= 30:
            pool = ("bloodleaf_warrior", "savage_minion", "blackwind_jakto")
        elif mob_lvl <= 35:
            pool = ("savage_archer", "savage_minion", "bloodleaf_warrior")
        else:
            pool = ("savage_archer", "savage_minion")

        valid_pool = [
            tid for tid in pool
            if tid in MONSTER_TEMPLATES
            and not MONSTER_TEMPLATES[tid].get("isElite")
            and not MONSTER_TEMPLATES[tid].get("isBoss")
        ]
        if valid_pool:
            return random.choice(valid_pool)
        return "blackwind_soldier" if mz > 0.0 else "alpha_bloodwolf"

    def _scale_monolith_guard_to_level(self, guard: dict, mob: dict, is_erwacht: bool = False):
        """Passt ein gespawntes Begleit-/Wellenmonster exakt an das Level des Rissmonolithen an."""
        mob_lvl = max(1, int(mob.get("level", 5)))
        tpl_lvl = max(1, int(guard.get("level", mob_lvl)))
        target_lvl = max(1, mob_lvl - 1) if tpl_lvl < mob_lvl - 2 else min(mob_lvl, tpl_lvl)
        if mob_lvl >= 20 and tpl_lvl < mob_lvl - 1:
            target_lvl = mob_lvl - 1
        guard["level"] = target_lvl
        if target_lvl != tpl_lvl:
            lvl_ratio = max(0.75, min(2.4, float(target_lvl) / float(max(1, tpl_lvl))))
            guard["maxHp"] = max(120, int(round(float(guard.get("maxHp", 200)) * lvl_ratio)))
            guard["hp"] = guard["maxHp"]
            guard["atk"] = max(12, int(round(float(guard.get("atk", 20)) * (0.85 + 0.15 * lvl_ratio))))
            guard["def"] = max(6, int(round(float(guard.get("def", 10)) * (0.85 + 0.15 * lvl_ratio))))
        if is_erwacht:
            guard["maxHp"] = int(guard["maxHp"] * 1.25)
            guard["hp"] = guard["maxHp"]
            guard["atk"] = int(guard["atk"] * 1.15)
        guard["isElite"] = False
        guard["isBoss"] = False

    def _resolve_monolith_elite_monster(self, mob: dict) -> str:
        """Bestimmt das exakt zum Level des Rissmonolithen passende ELITE-Boss-Template beim Erwecken:
        - Lv. 5 Monolith: 'red_boar' (Roter Zornkeiler [Elite], Lv. 6)
        - Lv. 10 Monolith: 'grizzly_bear' / 'red_boar' (Lv. 10–12 Riss-Eliteboss)
        - Lv. 15 Monolith: 'black_bear' (Schwarzpelz-Bär [Elite], Lv. 16) bzw. 'bandit_captain' am Weol-Denkmal
        - Lv. 20 Monolith: 'king_tiger' (Weißer Königstiger [Elite], Lv. 18–20) bzw. 'bandit_captain' / 'blackwind_tosu'
        - Lv. 25 Monolith: 'blackwind_tosu' (Schwarzwind-To-Su [Elite], Lv. 25–26)
        - Lv. 30 Monolith: 'blackwind_guryung' (Schwarzwind-Gu-Ryung [Elite], Lv. 30–32)
        - Lv. 35+ Monolith: 'savage_general' (Wilder General [Elite], Lv. 35+)"""
        mob_lvl = int(mob.get("level", 5))
        mx = float(mob.get("x", 0.0))
        mz = float(mob.get("z", 0.0))
        in_wheol_oath_zone = (abs(mx) <= 360.0 and -350.0 <= mz <= -50.0)

        if mob_lvl <= 5:
            return "red_boar" if "red_boar" in MONSTER_TEMPLATES else "alpha_bloodwolf"
        if mob_lvl <= 10:
            return "grizzly_bear" if "grizzly_bear" in MONSTER_TEMPLATES else "red_boar"
        if mob_lvl <= 15:
            if in_wheol_oath_zone and "bandit_captain" in MONSTER_TEMPLATES:
                return "bandit_captain"
            return "black_bear" if "black_bear" in MONSTER_TEMPLATES else "king_tiger"
        if mob_lvl <= 20:
            if in_wheol_oath_zone and "bandit_captain" in MONSTER_TEMPLATES:
                return "bandit_captain"
            if mz > 0.0 and "blackwind_tosu" in MONSTER_TEMPLATES:
                return "blackwind_tosu"
            return "king_tiger"
        if mob_lvl <= 25:
            return "blackwind_tosu" if "blackwind_tosu" in MONSTER_TEMPLATES else "king_tiger"
        if mob_lvl <= 30:
            return "blackwind_guryung" if "blackwind_guryung" in MONSTER_TEMPLATES else "blackwind_tosu"
        return "savage_general" if "savage_general" in MONSTER_TEMPLATES else "blackwind_guryung"

    @staticmethod
    def _get_unstable_elite_boss_count(mob_lvl: int) -> int:
        """Bestimmt die Gesamtanzahl an Elite-Bossen für einen Instabilen Rissmonolithen je nach Level:
        - Lv. 5: 1 Elite-Boss (für eine Anfänger-Gruppe gut schaffbar)
        - Lv. 10–15: 2 Elite-Bosse (ab Lv. 10 für Anfänger-Gruppe schon sehr schwer)
        - Lv. 20–25: 3 Elite-Bosse
        - Lv. 30+: 4 Elite-Bosse"""
        if mob_lvl <= 5:
            return 1
        if mob_lvl <= 15:
            return 2
        if mob_lvl <= 25:
            return 3
        return 4

    def _spawn_unstable_elite_boss(
        self,
        mob: dict,
        index: int = 0,
        total: int = 1,
        target_player_id: Optional[str] = None,
    ) -> dict:
        """Spawnt einen exakt zum Monolith-Level passenden Elite-Boss samt level-passender Begleitmonster."""
        elite_tpl_id = self._resolve_monolith_elite_monster(mob)
        ang = (math.pi * 2.0 * index) / max(1, total) + random.uniform(-0.2, 0.2)
        sx = round(mob["x"] + math.cos(ang) * 4.2, 1)
        sz = round(mob["z"] + math.sin(ang) * 4.2, 1)
        eb = self._create_monster_instance(mob["mapId"], elite_tpl_id, sx, sz, 9.5, is_summon=True)

        mob_lvl = int(mob.get("level", 5))
        if mob_lvl <= 5:
            eb_lvl, eb_hp, eb_atk, eb_def = 6, 2700, 43, 23
        elif mob_lvl <= 10:
            eb_lvl, eb_hp, eb_atk, eb_def = 11, 7650, 98, 47
        elif mob_lvl <= 15:
            eb_lvl, eb_hp, eb_atk, eb_def = 16, 12600, 150, 65
        elif mob_lvl <= 20:
            eb_lvl, eb_hp, eb_atk, eb_def = 20, 18500, 204, 85
        elif mob_lvl <= 25:
            eb_lvl, eb_hp, eb_atk, eb_def = 26, 25200, 260, 105
        elif mob_lvl <= 30:
            eb_lvl, eb_hp, eb_atk, eb_def = 31, 33000, 320, 129
        elif mob_lvl <= 35:
            eb_lvl, eb_hp, eb_atk, eb_def = 35, 41000, 375, 152
        else:
            eb_lvl, eb_hp, eb_atk, eb_def = mob_lvl, 48500, 415, 170

        clean_base = str(eb.get("baseName", eb["name"])).replace(" [Elite]", "").replace("[Elite]", "").strip()
        eb["name"] = f"⚔️ [Riss-Eliteboss] {clean_base}"
        eb["level"] = eb_lvl
        eb["maxHp"] = eb_hp
        eb["hp"] = eb_hp
        eb["atk"] = eb_atk
        eb["def"] = eb_def
        eb["isElite"] = True
        eb["isBoss"] = False
        eb["isAggressive"] = True
        eb["aggroRadius"] = 14.0
        eb["scale"] = round(max(1.22, float(eb.get("scale", 1.15)) * 1.15), 2)
        eb["isMonolithEliteBoss"] = True
        eb["allowSummonLoot"] = True
        eb["monolithGuardOf"] = mob["id"]
        mob["eliteBossesSpawned"] = int(mob.get("eliteBossesSpawned", 0)) + 1
        if target_player_id:
            eb["targetPlayerId"] = target_player_id
            eb["state"] = "chase"

        # Jeder erweckte Riss-Eliteboss spawnt 1 level-passendes Begleitmonster an seiner Seite
        escort_tpl_id = self._resolve_monolith_wave_monster(mob)
        escort_ang = ang + 0.35
        esx = round(sx + math.cos(escort_ang) * 2.2, 1)
        esz = round(sz + math.sin(escort_ang) * 2.2, 1)
        escort = self._create_monster_instance(mob["mapId"], escort_tpl_id, esx, esz, 8.0, is_summon=True)
        self._scale_monolith_guard_to_level(escort, mob, is_erwacht=False)
        escort["monolithGuardOf"] = mob["id"]
        if target_player_id:
            escort["targetPlayerId"] = target_player_id
            escort["state"] = "chase"
        return eb

    def _spawn_monolith_world_boss(self, mob: dict, actor: Optional[dict] = None) -> Optional[dict]:
        """Spawnt den 1 mächtigen Weltboss eines Erwachten Rissmonolithen:
        - Maximal 1 Weltboss pro Mapgebiet gleichzeitig!
        - Sehr stark (für Spieler mit Max-EQ oder Gruppen je nach Monolith-Level) & mächtige Skills.
        - 1 Stunde (3600s) Despawn-Timer gemeinsam mit dem Erwachten Rissmonolithen.
        - Sendet Event für Dynamic-Island-Meldung & Weltkarten-Anzeige."""
        map_id = mob["mapId"]
        existing_wb = self._get_active_world_boss(map_id)
        if existing_wb is not None:
            mob["worldBossSummoned"] = True
            mob["activeWorldBossId"] = existing_wb["id"]
            return existing_wb

        mob_lvl = int(mob.get("level", 5))
        if mob_lvl <= 10:
            boss_tpl_id = "boss_fenris" if "boss_fenris" in MONSTER_TEMPLATES else "boss_morgenwacht"
        elif mob_lvl <= 20:
            boss_tpl_id = "boss_lykos" if "boss_lykos" in MONSTER_TEMPLATES else "boss_morgenwacht"
        else:
            boss_tpl_id = "boss_brutal_captain" if "boss_brutal_captain" in MONSTER_TEMPLATES else "boss_morgenwacht"
        if mob.get("worldBossId") in MONSTER_TEMPLATES:
            boss_tpl_id = mob["worldBossId"]

        sx = round(mob["x"] + 4.2, 1)
        sz = round(mob["z"] - 3.6, 1)
        wb = self._create_monster_instance(map_id, boss_tpl_id, sx, sz, 16.0, is_summon=True)

        if mob_lvl <= 5:
            wb_lvl, wb_hp, wb_atk, wb_def = 10, 36000, 152, 58
        elif mob_lvl <= 10:
            wb_lvl, wb_hp, wb_atk, wb_def = 15, 76500, 252, 92
        elif mob_lvl <= 15:
            wb_lvl, wb_hp, wb_atk, wb_def = 20, 130000, 358, 124
        elif mob_lvl <= 20:
            wb_lvl, wb_hp, wb_atk, wb_def = 25, 196000, 492, 162
        elif mob_lvl <= 25:
            wb_lvl, wb_hp, wb_atk, wb_def = 30, 280000, 650, 202
        else:
            wb_lvl, wb_hp, wb_atk, wb_def = 35, 405000, 840, 252

        clean_base = (
            str(wb.get("baseName", wb["name"]))
            .replace("[Gebietsboss]", "")
            .replace("[Weltboss]", "")
            .strip()
        )
        now = time.time()
        despawn_at = round(now + 3600.0, 1)
        self.last_world_boss_awakened_at[map_id] = now
        self.world_boss_cooldown_until[map_id] = now + self.WORLD_BOSS_AWAKEN_COOLDOWN_SEC

        wb["name"] = f"👑 [Weltboss] {clean_base}"
        wb["level"] = wb_lvl
        wb["maxHp"] = wb_hp
        wb["hp"] = wb_hp
        wb["atk"] = wb_atk
        wb["def"] = wb_def
        wb["isBoss"] = True
        wb["isElite"] = True
        wb["isAggressive"] = True
        wb["aggroRadius"] = 18.0
        wb["attackRange"] = 4.0
        wb["scale"] = round(max(1.65, float(wb.get("scale", 1.5)) * 1.22), 2)
        wb["isRiftWorldBoss"] = True
        wb["allowSummonLoot"] = True
        wb["monolithBossOf"] = mob["id"]
        wb["despawnAt"] = despawn_at
        wb["nextAoETime"] = now + 4.0

        mob["worldBossSummoned"] = True
        mob["activeWorldBossId"] = wb["id"]
        mob["despawnAt"] = despawn_at

        if actor:
            wb["targetPlayerId"] = actor.get("player_id")
            wb["state"] = "chase"

        map_title = MAPS.get(map_id, {}).get("name", map_id)
        self.add_chat_message(
            "Welt-Herold",
            f"👑 [WELTBOSS ERSCHIENEN] {wb['name']} (Lv. {wb['level']}) ist am {mob['name']} in '{map_title}' erschienen! Er ist auf der Weltkarte [M] markiert und verschwindet nach 1 Stunde, falls er nicht besiegt wird!",
            channel="event",
        )
        self._emit_combat_event(
            map_id,
            "world_boss_spawned",
            wb["x"],
            wb["z"],
            {
                "bossId": wb["id"],
                "bossName": wb["name"],
                "bossLevel": wb["level"],
                "hp": wb["hp"],
                "maxHp": wb["maxHp"],
                "x": round(wb["x"], 1),
                "z": round(wb["z"], 1),
                "mapId": map_id,
                "mapName": map_title,
                "monolithId": mob["id"],
                "monolithName": mob["name"],
                "despawnAt": despawn_at,
                "remainingSec": 3600,
            },
        )
        return wb

    def _spawn_monolith_guardians(self, mob: dict, count: int = 2, target_player_id: Optional[str] = None):
        """Spawnt Wächtermonster rund um einen Rissmonolithen:
        - Schlafend (Normal): AUSSCHLIESSLICH normale Monster (NIEMALS Elite-Bosse oder Bosse!)
        - Instabil: Normale level-passende Monster + level-passende Elite-Bosse
        - Erwacht: Normale level-passende Wächter + der 1 Weltboss (max. 1 Weltboss pro Mapgebiet)."""
        m_state = mob.get("monolithState", "schlafend")
        is_erwacht = m_state == "erwacht"
        for i in range(count):
            wave_mob_id = self._resolve_monolith_wave_monster(mob)
            ang = (math.pi * 2.0 * i) / max(1, count) + random.uniform(-0.25, 0.25)
            sx = round(mob["x"] + math.cos(ang) * 3.8, 1)
            sz = round(mob["z"] + math.sin(ang) * 3.8, 1)
            guard = self._create_monster_instance(mob["mapId"], wave_mob_id, sx, sz, 7.5, is_summon=True)
            self._scale_monolith_guard_to_level(guard, mob, is_erwacht=is_erwacht)
            guard["monolithGuardOf"] = mob["id"]
            if target_player_id:
                guard["targetPlayerId"] = target_player_id
                guard["state"] = "chase"

        if m_state == "instabil":
            total_elites = self._get_unstable_elite_boss_count(int(mob.get("level", 5)))
            if int(mob.get("eliteBossesSpawned", 0)) < 1 and total_elites >= 1:
                self._spawn_unstable_elite_boss(
                    mob, index=0, total=total_elites, target_player_id=target_player_id
                )
        elif m_state == "erwacht":
            actor_p = self.players.get(target_player_id) if target_player_id else None
            self._spawn_monolith_world_boss(mob, actor=actor_p)

    def _apply_monolith_state(
        self,
        mob: dict,
        state_key: str,
        announce: bool = False,
        actor: Optional[dict] = None,
        preserve_hp: bool = False,
    ):
        """Setzt den dynamischen Monolith-Zustand ('schlafend' | 'instabil' | 'erwacht') inkl. Umgebungs- & Event-Effekten."""
        if state_key not in MONOLITH_STATES:
            state_key = "schlafend"
        sdef = MONOLITH_STATES[state_key]
        tpl = MONSTER_TEMPLATES[mob["templateId"]]
        prev_ratio = (
            max(0.05, min(1.0, float(mob.get("hp", 100)) / max(1.0, float(mob.get("maxHp", 100)))))
            if preserve_hp and mob.get("maxHp")
            else 1.0
        )
        r_key = "erwacht" if state_key == "erwacht" else ("instabil" if state_key == "instabil" else "normal")
        r_def = MONOLITH_RARITIES.get(r_key, MONOLITH_RARITIES["normal"])

        mob["monolithRarity"] = r_def["id"]
        mob["rarityLabel"] = r_def["label"]
        mob["rarityBadge"] = r_def["badge"]
        mob["rarityColor"] = sdef["colorHex"]
        mob["shiningTier"] = int(r_def["shiningTier"])
        mob["summonMultiplier"] = float(r_def["summonMult"])
        mob["extraDropSlots"] = int(r_def["extraDropSlots"])
        mob["scale"] = round(float(tpl["scale"]) * float(r_def["scaleMult"]), 2)
        mob["color"] = tpl["color"] if state_key == "schlafend" else int(sdef["colorInt"])
        mob["isElite"] = state_key in ("instabil", "erwacht")

        mob["monolithState"] = sdef["id"]
        mob["monolithStateName"] = sdef["name"]
        mob["monolithStateBadge"] = sdef["badge"]
        mob["monolithStateDesc"] = sdef["description"]
        mob["monolithEffects"] = list(sdef["effects"])
        mob["envRadius"] = float(sdef["envRadius"])
        mob["outerRadius"] = float(sdef.get("outerRadius", 350.0))
        mob["stateChangedAt"] = round(time.time(), 2)
        mob["publicEventActive"] = bool(sdef["publicEvent"])
        mob["realmConflictActive"] = bool(sdef["realmConflict"])
        mob["fleeAnimals"] = bool(sdef["fleeAnimals"])

        base_hp = int(tpl["hp"])
        hp_mult = float(sdef["hpMult"])
        new_max_hp = max(350, int(round(base_hp * hp_mult)))
        mob["maxHp"] = new_max_hp
        mob["hp"] = int(round(new_max_hp * prev_ratio)) if preserve_hp else new_max_hp
        mob["def"] = int(round(tpl["def"] * float(sdef["defMult"])))
        mob["lootMultiplier"] = round(float(sdef["lootMult"]), 2)

        if state_key == "erwacht":
            if not mob.get("despawnAt") or float(mob.get("despawnAt", 0.0)) <= time.time():
                mob["despawnAt"] = round(time.time() + 3600.0, 1)
        else:
            mob["despawnAt"] = 0.0

        if mob.get("isMajorMonolith"):
            mob["name"] = f"{r_def['prefix']}{mob['majorTitle']}" if r_def["prefix"] else f"{mob['majorTitle']}"
            mob["rarityBadge"] = r_def["badge"] or "RISS"
        else:
            mob["name"] = f"{r_def['prefix']}{tpl['name']}"

        if announce:
            map_title = MAPS.get(mob["mapId"], {}).get("name", mob["mapId"])
            actor_prefix = f"Durch {actor['name']}: " if actor else ""
            if state_key == "instabil":
                elites_cnt = self._get_unstable_elite_boss_count(int(mob.get("level", 5)))
                self.add_chat_message(
                    "Riss-Chronist",
                    f"⚡ {actor_prefix}{mob['name']} (Lv. {mob['level']}) in '{map_title}' ist INSTABIL geworden ({elites_cnt}× Elite-Boss)! Dimensionsrisse öffnen sich!",
                    channel="event",
                )
            elif state_key == "erwacht":
                self.add_chat_message(
                    "Riss-Chronist",
                    f"🔥 {actor_prefix}{mob['name']} (Lv. {mob['level']}) in '{map_title}' ist ERWACHT! Ein mächtiger Weltboss manifestiert sich für 1 Stunde!",
                    channel="event",
                )
            self._emit_combat_event(
                mob["mapId"],
                "monolith_state_change",
                mob["x"],
                mob["z"],
                {
                    "monolithId": mob["id"],
                    "monolithName": mob["name"],
                    "state": state_key,
                    "stateName": sdef["name"],
                    "badge": sdef["badge"],
                    "color": sdef["colorHex"],
                    "realmConflict": mob["realmConflictActive"],
                    "publicEvent": mob["publicEventActive"],
                },
            )

    def _apply_monolith_rarity(self, mob: dict, rarity_key: str):
        """Setzt die Rissmonolithen-Stufe ('normal' -> 'schlafend', 'instabil' -> 'instabil', 'erwacht' -> 'erwacht')."""
        tpl = MONSTER_TEMPLATES[mob["templateId"]]
        if rarity_key not in MONOLITH_RARITIES:
            rarity_key = "normal"

        mob["baseName"] = tpl["name"]
        mob["baseCrystalColor"] = tpl["color"]
        mob["combatPhase"] = 1
        mob["combatPhaseText"] = MONOLITH_COMBAT_PHASES[1]
        mob["worldBossSummoned"] = False
        mob["activeWorldBossId"] = None
        mob["eliteBossesSpawned"] = 0
        mob["guardsSpawned"] = False
        mob["participants"] = set()
        mob["maxRiftTier"] = "erwacht"

        init_state = "erwacht" if rarity_key == "erwacht" else ("instabil" if rarity_key == "instabil" else "schlafend")
        self._apply_monolith_state(mob, init_state, announce=False, preserve_hp=False)

    def _create_monster_instance(
        self,
        map_id: str,
        tpl_id: str,
        sx: float,
        sz: float,
        roam_radius: float,
        is_summon: bool = False,
        pack_id: Optional[str] = None,
        pack_center_x: Optional[float] = None,
        pack_center_z: Optional[float] = None,
    ) -> dict:
        tpl = MONSTER_TEMPLATES[tpl_id]
        if tpl["kind"] == "metin":
            sx, sz = self._pick_random_monolith_coords(map_id, template_id=tpl_id)
            roam_radius = 0.0
        mid = f"mob_{uuid.uuid4().hex[:10]}"
        if is_summon:
            hp_mult = 0.92
        elif tpl.get("isBoss", False) or tpl["kind"] == "metin":
            hp_mult = 1.62
        elif tpl.get("isElite", False):
            hp_mult = 1.52
        else:
            hp_mult = 1.42
        scaled_hp = int(round(tpl["hp"] * hp_mult))
        scaled_atk = int(round(tpl["atk"] * 1.05)) if tpl["atk"] > 0 else 0
        scaled_def = int(round(tpl["def"] * 1.05))
        inst = {
            "id": mid,
            "spawnedAt": time.time(),
            "templateId": tpl_id,
            "mapId": map_id,
            "packId": pack_id,
            "packCenterX": float(pack_center_x if pack_center_x is not None else sx),
            "packCenterZ": float(pack_center_z if pack_center_z is not None else sz),
            "name": tpl["name"],
            "baseName": tpl["name"],
            "loreMeaning": tpl.get("loreMeaning", ""),
            "storyChapter": tpl.get("storyChapter", ""),
            "kind": tpl["kind"],
            "isElite": tpl.get("isElite", False),
            "isBoss": bool(tpl.get("isBoss", False)),
            "isAggressive": bool(tpl.get("isBoss", False)) or ("white_oath" in tpl.get("id", "")) or ("eid" in tpl.get("name", "").lower()) or bool(tpl.get("isAggressive", False)),
            "level": tpl["level"],
            "hp": scaled_hp,
            "maxHp": scaled_hp,
            "atk": scaled_atk,
            "def": scaled_def,
            "speed": tpl["speed"],
            "aggroRadius": 16.0 if tpl.get("isBoss", False) else (11.5 if ("white_oath" in tpl.get("id", "") or "eid" in tpl.get("name", "").lower()) else (float(tpl.get("aggroRadius", 0.0)) if tpl.get("isAggressive", False) else 0.0)),
            "attackRange": tpl["attackRange"],
            "attackInterval": tpl["attackInterval"],
            "respawnSec": self.get_mob_respawn_sec({"templateId": tpl["id"], "mapId": map_id, "kind": tpl.get("kind", "monster"), "isBoss": tpl.get("isBoss", False), "respawnSec": tpl["respawnSec"]}),
            "spawnX": sx,
            "spawnZ": sz,
            "x": sx,
            "z": sz,
            "rotY": random.uniform(0, math.pi * 2),
            "roamRadius": roam_radius,
            "state": "idle",  # 'idle' | 'patrol' | 'chase' | 'dead'
            "targetPlayerId": None,
            "lastAttackTime": 0.0,
            "nextPatrolTime": time.time() + random.uniform(2.0, 6.0),
            "patrolX": sx,
            "patrolZ": sz,
            "deadUntil": 0.0,
            "wavesSpawned": [],
            "bossPhase": 1,
            "combatPhase": 1,
            "combatPhaseText": "",
            "monolithRarity": "normal",
            "rarityLabel": "Normal",
            "rarityBadge": "",
            "rarityColor": "#E8E8E8",
            "shiningTier": 1,
            "lootMultiplier": 1.0,
            "summonMultiplier": 1.0,
            "extraDropSlots": 0,
            "baseCrystalColor": tpl["color"],
            "nextAoETime": time.time() + 7.0,
            "isSummon": is_summon,
            "modelType": tpl["modelType"],
            "glbModel": tpl.get("glbModel"),
            "glbTextures": tpl.get("glbTextures", []),
            "color": tpl["color"],
            "scale": tpl["scale"],
            "icon": tpl["icon"],
        }
        self.monsters[mid] = inst
        if tpl["kind"] == "metin":
            rarity_key = self._roll_monolith_rarity(map_id, exclude_mob_id=mid)
            self._apply_monolith_rarity(inst, rarity_key)
            if inst.get("monolithState") == "erwacht":
                self._spawn_monolith_world_boss(inst)
        return inst

    # ========================================================================
    # 2. ZENTRALE KAMPFWERT-BERECHNUNG (Kap. 5 & 15) & PET-PROFIILDATEN
    # ========================================================================
    BOT_PET_PROFILES = {
        "bot_veyron_warrior": {"skinKey": "plechi_elephant_pet2", "customName": "Kaiser-Elefant"},
        "bot_nachtklinge_ninja": {"skinKey": "plechi_flamegoblin_pet", "customName": "Glutkobold"},
        "bot_malakor_sura": {"skinKey": "plechi_lich_pet", "customName": "Seelen-Lich"},
        "bot_aurelia_shaman": {"skinKey": "plechi_fantasy_flypet2", "customName": "Äther-Schwinge"},
        "bot_eisensturm_mounted": {"skinKey": "plechi_emd_pet", "customName": "Runen-Wächter"},
        "bot_lyra_ninja": {"skinKey": "plechi_thuderspirit_pet", "customName": "Donnergeist"},
        "bot_kassian_warrior": {"skinKey": "plechi_emd_pet", "customName": "Runen-Wächter"},
        "bot_schattenfalke_ninja": {"skinKey": "plechi_smaragd_dragon", "customName": "Jade-Wyrmling"},
        "bot_varon_sura": {"skinKey": "plechi_lich_pet", "customName": "Seelen-Lich"},
        "bot_seraphina_shaman": {"skinKey": "plechi_fantasy_flypet2", "customName": "Äther-Schwinge"},
        "bot_donnerkeil_mounted": {"skinKey": "plechi_elephant_pet2", "customName": "Kaiser-Elefant"},
        "bot_draven_sura": {"skinKey": "ridack_dragonpet", "customName": "Grüner Smaragddrache"},
    }

    VALID_PET_SKINS = {
        "ridack_dragonpet": "Grüner Smaragddrache",
        "plechi_smaragd_dragon": "Jade-Wyrmling",
        "plechi_thuderspirit_pet": "Donnergeist",
        "plechi_flamegoblin_pet": "Glutkobold",
        "plechi_lich_pet": "Seelen-Lich",
        "plechi_fantasy_flypet2": "Äther-Schwinge",
        "plechi_emd_pet": "Runen-Wächter",
        "plechi_elephant_pet2": "Kaiser-Elefant",
        "astral_phoenix": "Astralphönix",
    }

    def _ensure_player_pet_data(self, p: dict) -> dict:
        raw_pet = p.get("petData")
        if not isinstance(raw_pet, dict):
            raw_pet = p.setdefault("quests", {}).get("__pet_profile__")
        if not isinstance(raw_pet, dict):
            raw_pet = {}
        pid = str(p.get("player_id", "") or "")
        bot_prof = self.BOT_PET_PROFILES.get(pid)
        pet_lvl = max(1, min(MAX_PET_LEVEL, int(raw_pet.get("level", 1) or 1)))
        p_lvl_owner = max(1, int(p.get("level", 1) or 1))
        if bot_prof or pid.startswith("bot_"):
            pet_lvl = max(1, min(MAX_PET_LEVEL, min(pet_lvl, p_lvl_owner + 2)))
            if pet_lvl < max(1, int(p_lvl_owner * 0.85)):
                pet_lvl = max(1, int(p_lvl_owner * 0.85))
        raw_skills = raw_pet.get("skills") if isinstance(raw_pet.get("skills"), dict) else {}
        max_sk_for_lvl = max(1, min(20, 1 + pet_lvl // 4)) if (bot_prof or pid.startswith("bot_")) else 20
        norm_skills = {}
        for sk_def in PET_SKILL_DEFS:
            sk_id = sk_def["id"]
            default_lv = 1 if sk_id == "auto_pickup" and not raw_skills else 0
            cap_sk = min(int(sk_def["maxLevel"]), max_sk_for_lvl if sk_id != "auto_pickup" else int(sk_def["maxLevel"]))
            norm_skills[sk_id] = max(0, min(cap_sk, int(raw_skills.get(sk_id, default_lv) or 0)))

        default_skin = bot_prof["skinKey"] if bot_prof else "ridack_dragonpet"
        skin_key = str(raw_pet.get("skinKey") or default_skin)
        if skin_key not in self.VALID_PET_SKINS:
            skin_key = default_skin
        if bot_prof and skin_key == "ridack_dragonpet" and bot_prof["skinKey"] != "ridack_dragonpet":
            skin_key = bot_prof["skinKey"]

        raw_cname = str(raw_pet.get("customName") or "")
        if bot_prof and (not raw_cname or raw_cname == "Grüner Smaragddrache"):
            custom_name = bot_prof["customName"]
        else:
            custom_name = raw_cname or self.VALID_PET_SKINS.get(skin_key, "Grüner Smaragddrache")

        total_expected_stat_pts = 4 + (pet_lvl - 1) * 2
        vit_v = max(0, min(MAX_PET_STAT_POINTS, int(raw_pet.get("vit", 0) or 0)))
        str_v = max(0, min(MAX_PET_STAT_POINTS, int(raw_pet.get("str", 0) or 0)))
        dex_v = max(0, min(MAX_PET_STAT_POINTS, int(raw_pet.get("dex", 0) or 0)))
        int_v = max(0, min(MAX_PET_STAT_POINTS, int(raw_pet.get("int", 0) or 0)))
        spent_stat_pts = vit_v + str_v + dex_v + int_v
        is_sa_owner = bool(
            p.get("isSA")
            or str(p.get("name") or "").upper().startswith("[SA]")
            or (isinstance(p.get("quests"), dict) and p["quests"].get("__is_sa__"))
        )
        if not is_sa_owner and spent_stat_pts > total_expected_stat_pts and spent_stat_pts > 0:
            scale_st = total_expected_stat_pts / float(spent_stat_pts)
            vit_v = int(vit_v * scale_st)
            str_v = int(str_v * scale_st)
            dex_v = int(dex_v * scale_st)
            int_v = int(int_v * scale_st)
            spent_stat_pts = vit_v + str_v + dex_v + int_v
        avail_stat_pts = 0 if (is_sa_owner and spent_stat_pts >= total_expected_stat_pts) else max(0, total_expected_stat_pts - spent_stat_pts)

        total_expected_skill_pts = 2 + (pet_lvl - 1) * 1
        spent_skill_pts = max(0, sum(norm_skills.values()) - 1)
        avail_skill_pts = max(0, total_expected_skill_pts - spent_skill_pts)

        pet_data = {
            "petId": "pet_fire_phoenix",
            "skinKey": skin_key,
            "customName": custom_name,
            "level": pet_lvl,
            "exp": max(0, int(raw_pet.get("exp", 0) or 0)),
            "maxExp": get_required_pet_exp(pet_lvl),
            "skillPoints": avail_skill_pts,
            "statPoints": avail_stat_pts,
            "vit": vit_v,
            "str": str_v,
            "dex": dex_v,
            "int": int_v,
            "skills": norm_skills,
            "cooldowns": dict(raw_pet.get("cooldowns")) if isinstance(raw_pet.get("cooldowns"), dict) else {},
        }
        p["petData"] = pet_data
        p.setdefault("quests", {})["__pet_profile__"] = pet_data
        return pet_data

    def _auto_maintain_bot_pet(self, p: dict) -> bool:
        """Stellt sicher, dass Bots ihren Begleiter rufen, ihr individuelles 3D-Aussehen wählen und alle
        Pet-Statuspunkte sowie Pet-Fertigkeitspunkte klassengerecht investieren."""
        pid = str(p.get("player_id", "") or "")
        if not pid.startswith("bot_"):
            return False
        changed = False
        if not p.get("active_pet"):
            p["active_pet"] = "pet_fire_phoenix"
            changed = True
        pd = self._ensure_player_pet_data(p)
        cls_id = str(p.get("class_id", "warrior") or "warrior")
        stat_prio = {
            "warrior": ["str", "str", "vit", "dex"],
            "ninja": ["dex", "dex", "str", "vit"],
            "sura": ["int", "int", "str", "vit"],
            "shaman": ["int", "int", "dex", "vit"],
        }.get(cls_id, ["str", "vit", "dex"])

        avail_stats = int(pd.get("statPoints", 0))
        step_i = 0
        while avail_stats > 0 and step_i < 240:
            st_key = stat_prio[step_i % len(stat_prio)]
            step_i += 1
            cur_v = int(pd.get(st_key, 0))
            if cur_v < MAX_PET_STAT_POINTS:
                pd[st_key] = cur_v + 1
                avail_stats -= 1
                changed = True
            elif all(int(pd.get(k, 0)) >= MAX_PET_STAT_POINTS for k in ("vit", "str", "dex", "int")):
                break
        pd["statPoints"] = max(0, avail_stats)

        skill_prio = (
            [
                "jaeger",
                "herrschaft",
                "zerstoerung_fks" if cls_id in ("sura", "shaman") else "zerstoerung_dss",
                "erfahrungsrausch",
                "erneuerung",
                "heilung",
                "auto_pickup",
                "dungeonmeister",
                "monsterschild",
                "vampirismus",
                "zerstoerung_dss" if cls_id in ("sura", "shaman") else "zerstoerung_fks",
                "widerstand",
            ]
        )
        skills_map = pd.setdefault("skills", {})
        avail_sk = int(pd.get("skillPoints", 0))
        sk_guard = 0
        while avail_sk > 0 and sk_guard < 120:
            sk_guard += 1
            picked_sk = None
            # Verteile Punkte gleichmäßig über die wichtigsten Kampf- & Aktiv-Skills (Stufe für Stufe hochziehen)
            best_ratio = 999.0
            for sk_id in skill_prio:
                sk_def = PET_SKILL_MAP.get(sk_id)
                if not sk_def:
                    continue
                max_lv = int(sk_def.get("maxLevel", 20))
                cur_lv = int(skills_map.get(sk_id, 0))
                if cur_lv < max_lv:
                    ratio = cur_lv / max(1, max_lv)
                    if ratio < best_ratio:
                        best_ratio = ratio
                        picked_sk = sk_id
            if not picked_sk:
                break
            skills_map[picked_sk] = int(skills_map.get(picked_sk, 0)) + 1
            avail_sk -= 1
            changed = True
        pd["skillPoints"] = max(0, avail_sk)
        if changed:
            self.compute_player_combat_stats(p)
        return changed

    def _ensure_player_mount_data(self, p: dict) -> dict:
        raw_mount = p.get("mountData")
        if not isinstance(raw_mount, dict):
            raw_mount = p.setdefault("quests", {}).get("__mount_profile__")
        if not isinstance(raw_mount, dict):
            raw_mount = {}

        is_bot = str(p.get("player_id") or "").startswith("bot_")
        # SSOT: KEIN Gratis-Paket Pferdemedaillen! Pferdemedaillen droppen erst, wenn Affen hinzugefügt werden.
        # Kein Bot darf sein Pferde-/Mount-Level steigern (strikt Stufe 1!).
        if is_bot:
            raw_mount["level"] = 1
            raw_mount["dmgPoints"] = 0
            raw_mount["hpPoints"] = 0
            inv = p.get("inventory")
            if isinstance(inv, list):
                p["inventory"] = [it for it in inv if not (isinstance(it, dict) and it.get("templateId") == "pferdemedaille")]

        horse_lvl = 1 if is_bot else max(1, min(MAX_HORSE_LEVEL, int(raw_mount.get("level", 1) or 1)))
        total_pts = 0 if (is_bot and horse_lvl <= 1) else (horse_lvl * 2 if horse_lvl > 1 else 0)
        dmg_pts = 0 if is_bot else max(0, int(raw_mount.get("dmgPoints", 0) or 0))
        hp_pts = 0 if is_bot else max(0, int(raw_mount.get("hpPoints", 0) or 0))
        if dmg_pts + hp_pts > total_pts:
            dmg_pts = min(dmg_pts, total_pts)
            hp_pts = max(0, min(hp_pts, total_pts - dmg_pts))
        avail_pts = max(0, total_pts - (dmg_pts + hp_pts))

        skin_explicit = bool(raw_mount.get("skinExplicit", False))
        eq_skin = str(raw_mount.get("equippedSkin") or "none")
        if eq_skin not in MOUNT_SKIN_MAP:
            eq_skin = "none"
        # Falls noch nie aktiv ein Pferde-Skin gewählt wurde und im Kostüm-Inventar ein Mount-Skin ausgerüstet ist
        if not skin_explicit and eq_skin == "none" and p.get("equipment", {}).get("costume_mount_skin"):
            eq_skin = "skin_rift_charger"

        # 3 Pferde-Ränge: Lv. 1–34 Pferd | Lv. 35–49 Kampfpferd | Lv. 50 Militärgaul (Ausbalanciert für Low- & Mid-Level)
        if horse_lvl >= 50:
            tier = 3
            tier_name = "Militärgaul (Stufe 50)"
            tier_short = "Militärgaul"
            default_visual = "horse_lvl50"
            base_str = 10
            base_aw = 34
            base_atk_pct = 6.0
            base_hp = 420
            base_def = 22
            aw_per_pt = 0.85
            str_per_pt = 0.16
            dmg_pct_per_pt = 0.08
            hp_per_pt = 14
            def_per_pt = 0.55
        elif horse_lvl >= 35:
            tier = 2
            tier_name = "Kampfpferd (Stufe 35)"
            tier_short = "Kampfpferd"
            default_visual = "horse_lvl35"
            lv_over = horse_lvl - 35
            base_str = 6 + (lv_over // 4)
            base_aw = 18 + int(lv_over * 0.9)
            base_atk_pct = round(3.5 + lv_over * 0.12, 1)
            base_hp = 220 + lv_over * 10
            base_def = 12 + (lv_over // 2)
            aw_per_pt = 0.60
            str_per_pt = 0.12
            dmg_pct_per_pt = 0.06
            hp_per_pt = 10
            def_per_pt = 0.40
        else:
            tier = 1
            tier_name = "Pferd (Stufe 1)"
            tier_short = "Pferd"
            default_visual = "horse_lvl1"
            base_str = 2 + (horse_lvl // 10)
            base_aw = 6 + (horse_lvl // 3)
            base_atk_pct = 1.5
            base_hp = 80 + horse_lvl * 4
            base_def = 4 + (horse_lvl // 5)
            aw_per_pt = 0.35
            str_per_pt = 0.08
            dmg_pct_per_pt = 0.04
            hp_per_pt = 6
            def_per_pt = 0.25

        # Mount-Skin überdeckt immer das Aussehen des Standard-Pferdes!
        visual_skin = eq_skin if eq_skin != "none" else default_visual
        skin_def = MOUNT_SKIN_MAP.get(eq_skin, MOUNT_SKIN_MAP["none"])
        skin_bonuses = dict(skin_def.get("bonuses", {}))

        total_str = int(round(base_str + dmg_pts * str_per_pt))
        total_aw = int(round(base_aw + dmg_pts * aw_per_pt + int(skin_bonuses.get("atk", 0))))
        total_atk_pct = round(base_atk_pct + dmg_pts * dmg_pct_per_pt, 1)
        total_hp = int(round(base_hp + hp_pts * hp_per_pt + int(skin_bonuses.get("hp", 0))))
        total_def = int(round(base_def + hp_pts * def_per_pt + int(skin_bonuses.get("def", 0))))

        medals_owned = sum(
            int(it.get("quantity", 1))
            for it in p.get("inventory", [])
            if it.get("templateId") == "pferdemedaille" and not it.get("reservedShopId")
        )

        mount_data = {
            "level": horse_lvl,
            "maxLevel": MAX_HORSE_LEVEL,
            "tier": tier,
            "tierName": tier_name,
            "tierShort": tier_short,
            "customName": str(raw_mount.get("customName") or "Streitross von Aeryndor"),
            "medalsRequired": 0 if horse_lvl >= MAX_HORSE_LEVEL else get_required_horse_medals(horse_lvl),
            "medalsOwned": medals_owned,
            "statPoints": avail_pts,
            "dmgPoints": dmg_pts,
            "hpPoints": hp_pts,
            "equippedSkin": eq_skin,
            "skinExplicit": skin_explicit,
            "visualSkin": visual_skin,
            "defaultVisual": default_visual,
            "skinName": skin_def.get("name", "Standard-Pferd"),
            "skinBonusSummary": skin_def.get("bonusSummary", ""),
            "skillsUnlocked": horse_lvl >= 50,
            "starterMedalsGranted": True,
            "perPointScaling": {
                "awPerDmgPt": aw_per_pt,
                "strPerDmgPt": str_per_pt,
                "dmgPctPerDmgPt": dmg_pct_per_pt,
                "hpPerHpPt": hp_per_pt,
                "defPerHpPt": def_per_pt,
            },
            "mountedBonuses": {
                "str": total_str,
                "atk": total_aw,
                "atkPct": total_atk_pct,
                "hp": total_hp,
                "def": total_def,
                "vsMetinPct": int(skin_bonuses.get("vsMetinPct", 0)),
                "vsMonsterPct": int(skin_bonuses.get("vsMonsterPct", 0)),
                "vsBossPct": int(skin_bonuses.get("vsBossPct", 0)),
                "dssPct": int(skin_bonuses.get("dssPct", 0)),
                "critPct": int(skin_bonuses.get("critPct", 0)),
                "piercePct": int(skin_bonuses.get("piercePct", 0)),
            },
        }
        p["mountData"] = mount_data
        p.setdefault("quests", {})["__mount_profile__"] = mount_data
        return mount_data

    def compute_player_combat_stats(self, p: dict) -> dict:
        # Begrenze aktive Fertigkeiten auf Maximalstufe 50 (0..19 Punkte, 20..29 M1..M10, 30..39 G1..G10, 40..49 P1..P10, 50 L1)
        refunded = 0
        for sk_k, sk_v in list(p.get("skills", {}).items()):
            if int(sk_v) > 50:
                p["skills"][sk_k] = 50
            elif int(sk_v) < 0:
                p["skills"][sk_k] = 0
        for ps_k, ps_v in list(p.get("passives", {}).items()):
            if int(ps_v) > 20:
                refunded += int(ps_v) - 20
                p["passives"][ps_k] = 20
        if refunded > 0:
            p["skill_points"] = int(p.get("skill_points", 0)) + refunded
            self.db.save_player_state(p)

        cdef = CHARACTER_CLASSES.get(p["class_id"], CHARACTER_CLASSES["warrior"])
        bstats = cdef["baseStats"]
        growth = cdef["growthPerLevel"]
        lvl = int(p["level"])

        vit = int(p["vit"])
        int_s = int(p["int_stat"])
        str_s = int(p["str"])
        dex = int(p["dex"])

        max_hp = int(bstats["hp"] + (lvl - 1) * growth["hp"] + vit * 34)
        max_mp = int(bstats["mp"] + (lvl - 1) * growth["mp"] + int_s * 22)
        # Ausgewogene Offensiv- & Defensiv-Skalierung (passend für Low- & Mid-Level Lv. 1–38)
        atk = float(bstats["atk"] * 0.58 + (lvl - 1) * (growth["atk"] * 0.48) + str_s * 0.92 + dex * 0.30)
        magic_atk = float(bstats["magicAtk"] * 0.58 + (lvl - 1) * (growth["magicAtk"] * 0.48) + int_s * 1.02)
        defense = float(bstats["def"] * 0.65 + (lvl - 1) * (growth["def"] * 0.58) + vit * 0.82 + dex * 0.22)
        speed = float(bstats["speed"] + dex * 0.015)
        # Ruhigere, wuchtige Angriffsgeschwindigkeit (Basis ~0.92 - 1.08)
        atk_speed = float(bstats["atkSpeed"] * 0.80 + dex * 0.002)
        crit_chance = float(bstats["critChance"] * 0.55 + dex * 0.09)
        pierce_chance = float(bstats.get("pierceChance", 5.0) * 0.52 + str_s * 0.07 + dex * 0.08)
        # Passiver Bonus Ausweichen (DEX-Grundwert + Boni)
        dodge_chance = float(min(32.0, dex * 0.38))
        vs_monster_pct = 0.0
        vs_metin_pct = 0.0
        vs_boss_pct = 0.0
        exp_bonus_pct = 20.0  # Aktives Welt-Event Basisbonus
        yang_bonus_pct = 0.0

        # 20 Passive Charakter-Fertigkeiten einrechnen (Aus Projekt 1 übernommen)
        passives = p.setdefault("passives", {})
        for ps_id in PASSIVE_SKILL_DEFS:
            passives.setdefault(ps_id, 0)
        vs_monster_pct += passives.get("monsterjaeger", 0) * 2.0
        vs_metin_pct += passives.get("metinbrecher", 0) * 2.5 + passives.get("metinsammler", 0) * 1.0
        vs_boss_pct += passives.get("bossjaeger", 0) * 2.0 + passives.get("bosserfahrung", 0) * 0.5
        max_hp += int(passives.get("lebenskraft", 0) * 60)
        max_mp += int(passives.get("manakontrolle", 0) * 30)
        yang_bonus_pct += passives.get("pluenderer", 0) * 1.5 + passives.get("metinsammler", 0) * 1.0
        exp_bonus_pct += passives.get("bosserfahrung", 0) * 1.0
        crit_chance += passives.get("kritischerinstinkt", 0) * 0.5
        pierce_chance += passives.get("durchdringung", 0) * 0.5
        atk += passives.get("waffenmeister", 0) * 4.0
        magic_atk += passives.get("waffenmeister", 0) * 4.0
        defense += passives.get("ruestungsmeister", 0) * 3.0
        dodge_chance += passives.get("ausdauertraining", 0) * 0.4
        if passives.get("kampftempo", 0) > 0:
            atk_speed *= 1.0 + (passives.get("kampftempo", 0) * 0.5) / 100.0
        if passives.get("bewegungsexperte", 0) > 0:
            speed *= 1.0 + (passives.get("bewegungsexperte", 0) * 0.5) / 100.0
        hp_regen_bonus_pct = float(passives.get("tpregen", 0) * 1.0)
        mp_regen_bonus_pct = float(passives.get("mpregen", 0) * 1.0)
        cast_speed_pct = float(passives.get("schnellerzauber", 0) * 0.5)
        drop_bonus_pct = float(passives.get("pluenderer", 0) * 1.5 + passives.get("ressourcenkenntnis", 0) * 1.0)
        monster_res_pct = 0.0
        skill_dmg_pct = 0.0
        dss_pct = 0.0
        hp_absorb_pct = 0.0
        bow_range_bonus = 0.0
        vs_devil_pct = 0.0
        vs_undead_pct = 0.0
        vs_orcs_pct = 0.0
        vs_animals_pct = 0.0
        vs_esoteric_pct = 0.0
        vs_halfhuman_pct = 0.0
        def_sword_pct = 0.0
        def_two_hand_pct = 0.0
        def_dagger_pct = 0.0
        def_arrow_pct = 0.0
        def_staff_pct = 0.0
        res_magic_pct = 0.0
        res_fire_pct = 0.0
        res_lightning_pct = 0.0
        res_wind_pct = 0.0
        res_ice_pct = 0.0
        res_poison_pct = 0.0
        stun_immune = False
        block_chance_pct = 0.0
        poison_chance_pct = 0.0
        bleed_chance_pct = 0.0
        stun_chance_pct = 0.0
        elem_power_pct = 0.0
        res_boss_skill_pct = 0.0
        res_crit_pct = 0.0

        # Ausgerüstete Gegenstände einrechnen (nur wenn im jeweiligen Ausrüstungs-Slot tatsächlich ein Item liegt!)
        eq_map = p.get("equipment", {})
        has_weapon = bool(eq_map.get("weapon"))
        has_armor = bool(eq_map.get("armor"))
        has_shield = bool(eq_map.get("shield"))
        has_helmet = bool(eq_map.get("helmet"))
        has_shoes = bool(eq_map.get("shoes"))
        has_gloves = bool(eq_map.get("gloves"))
        weapon_plus = 0
        armor_plus = 0
        weapon_visual = None
        costume_weapon_visual = None
        costume_pet_skin = None
        costume_mount_skin = None
        weapon_sub_type = "one_hand"
        weapon_atk_speed_pct = 0.0
        for slot_key, item in list(eq_map.items()):
            if not item:
                continue
            tpl_id_eq = str(item.get("templateId") or item.get("id") or "")
            if tpl_id_eq in ITEM_TEMPLATES:
                eff = calculate_item_effective_stats(
                    tpl_id_eq,
                    int(item.get("plusLevel", 0) or 0),
                    item.get("bonuses") or [],
                )
                item["effectiveStats"] = eff
            else:
                eff = item.get("effectiveStats", {})
            max_hp += int(eff.get("hp", 0))
            atk += float(eff.get("atk", 0))
            magic_atk += float(eff.get("magicAtk", 0))
            defense += float(eff.get("def", 0))
            crit_chance += float(eff.get("critChance", 0))
            pierce_chance += float(eff.get("pierceChance", 0))
            vs_monster_pct += float(eff.get("vsMonsterPct", 0))
            vs_metin_pct += float(eff.get("vsMetinPct", 0))
            vs_boss_pct += float(eff.get("vsBossPct", 0))
            vs_devil_pct += eff.get("vsDevilPct", 0)
            vs_undead_pct += eff.get("vsUndeadPct", 0)
            vs_orcs_pct += eff.get("vsOrcsPct", 0)
            vs_animals_pct += eff.get("vsAnimalsPct", 0)
            vs_esoteric_pct += eff.get("vsEsotericPct", 0)
            vs_halfhuman_pct += eff.get("vsHalfHumanPct", 0)
            exp_bonus_pct += eff.get("expBonusPct", 0)
            yang_bonus_pct += eff.get("yangBonusPct", 0)
            cast_speed_pct += eff.get("castSpeedPct", 0)
            hp_absorb_pct += eff.get("hpAbsorbPct", 0)
            skill_dmg_pct += eff.get("skillDmgPct", 0)
            dss_pct += eff.get("avgDmgPct", 0)
            def_sword_pct += eff.get("defSwordPct", 0)
            def_two_hand_pct += eff.get("defTwoHandPct", 0)
            def_dagger_pct += eff.get("defDaggerPct", 0)
            def_arrow_pct += eff.get("defArrowPct", 0)
            def_staff_pct += eff.get("defStaffPct", 0)
            res_magic_pct += eff.get("resMagicPct", 0)
            res_fire_pct += eff.get("resFirePct", 0)
            res_lightning_pct += eff.get("resLightningPct", 0)
            res_wind_pct += eff.get("resWindPct", 0)
            res_ice_pct += eff.get("resIcePct", 0)
            res_poison_pct += eff.get("resPoisonPct", 0)
            if eff.get("stunImmune"):
                stun_immune = True
            block_chance_pct += eff.get("blockChancePct", 0)
            poison_chance_pct += eff.get("poisonChancePct", 0)
            bleed_chance_pct += eff.get("bleedChancePct", 0)
            stun_chance_pct += eff.get("stunChancePct", 0)
            hp_regen_bonus_pct += eff.get("hpRegenPct", 0)
            mp_regen_bonus_pct += eff.get("mpRegenPct", 0)
            elem_power_pct += eff.get("elemPowerPct", 0)
            res_boss_skill_pct += eff.get("resBossSkillPct", 0)
            res_crit_pct += eff.get("resCritPct", 0)
            if eff.get("str"):
                str_s += int(eff["str"])
                atk += eff["str"] * 0.90
            if eff.get("vit"):
                vit += int(eff["vit"])
                max_hp += int(eff["vit"] * 24)
                defense += eff["vit"] * 0.65
            if eff.get("int"):
                int_s += int(eff["int"])
                magic_atk += eff["int"] * 0.90
                skill_dmg_pct += eff["int"] * 0.22
            if eff.get("dex"):
                dex += int(eff["dex"])
                atk += eff["dex"] * 0.70
                crit_chance += eff["dex"] * 0.12
            dodge_chance += eff.get("dodgeChance", 0) + eff.get("dodge", 0) + eff.get("dodgePct", 0)
            for b in item.get("bonuses", []):
                if b.get("id") == "bonus_dodge":
                    dodge_chance += float(b.get("value", 0))
            if slot_key == "exp_ring":
                exp_bonus_pct += 50.0
            elif slot_key == "luck_medal":
                yang_bonus_pct += 100.0
            elif slot_key == "hmr":
                exp_bonus_pct += 20.0
            if eff.get("atkSpeedPct"):
                if slot_key == "weapon":
                    weapon_atk_speed_pct = float(eff["atkSpeedPct"])
                atk_speed *= 1.0 + (eff["atkSpeedPct"] * 0.5) / 100.0
            if eff.get("speedPct") or eff.get("moveSpeedPct"):
                spd_add = float(eff.get("speedPct", 0)) + float(eff.get("moveSpeedPct", 0))
                speed *= 1.0 + (spd_add * 0.5) / 100.0
            if slot_key == "weapon":
                weapon_plus = int(item.get("plusLevel", 0) or 0)
                tpl_w = ITEM_TEMPLATES.get(tpl_id_eq, {})
                weapon_sub_type = str(item.get("weaponSubType") or tpl_w.get("weaponSubType") or "one_hand")
                if weapon_sub_type == "bell":
                    weapon_sub_type = "staff"
                weapon_visual = item.get("weaponVisual") or tpl_w.get("weaponVisual") or cdef["visual"]["defaultWeapon"] or "sword"
                if weapon_visual == "bell":
                    weapon_visual = "staff"
                pierce_chance += weapon_plus * 0.45
            elif slot_key == "armor":
                armor_plus = int(item.get("plusLevel", 0) or 0)
            elif slot_key == "costume_weapon":
                tpl_cw = ITEM_TEMPLATES.get(tpl_id_eq, {})
                costume_weapon_visual = item.get("weaponVisual") or tpl_cw.get("weaponVisual") or "sternenreisser"
            elif slot_key == "costume_pet_skin":
                tpl_cp = ITEM_TEMPLATES.get(tpl_id_eq, {})
                costume_pet_skin = item.get("petSkin") or tpl_cp.get("petSkin") or "astral_phoenix"
            elif slot_key == "costume_mount_skin":
                tpl_cm = ITEM_TEMPLATES.get(tpl_id_eq, {})
                costume_mount_skin = item.get("mountSkin") or tpl_cm.get("mountSkin") or "horse_lvl50"

        if costume_weapon_visual and has_weapon:
            weapon_visual = costume_weapon_visual

        # Mount & Pferde-System (Lv. 1 Pferd | Lv. 35 Kampfpferd | Lv. 50 Militärgaul + Sattel-Statuspunkte & Mount-Skins!)
        mount_data = self._ensure_player_mount_data(p)
        mount_id = p.get("active_mount")
        horse_level = int(mount_data.get("level", 1))
        mount_str_bonus = 0
        mount_lvl_scale = min(1.0, max(0.28, lvl / 38.0))
        if mount_id:
            mb = mount_data.get("mountedBonuses", {})
            mount_str_bonus = int(round(float(mb.get("str", 4)) * mount_lvl_scale))
            str_s += mount_str_bonus
            atk += float(mb.get("atk", 10)) * mount_lvl_scale
            speed *= 2.0
            atk *= 1.0 + (float(mb.get("atkPct", 2.0)) * mount_lvl_scale * 0.55) / 100.0
            max_hp += int(float(mb.get("hp", 100)) * mount_lvl_scale)
            defense += float(mb.get("def", 6)) * mount_lvl_scale
            vs_metin_pct += float(mb.get("vsMetinPct", 0)) * mount_lvl_scale
            vs_monster_pct += float(mb.get("vsMonsterPct", 0)) * mount_lvl_scale
            vs_boss_pct += float(mb.get("vsBossPct", 0)) * mount_lvl_scale
            dss_pct += float(mb.get("dssPct", 0)) * mount_lvl_scale
            crit_chance += float(mb.get("critPct", 0)) * mount_lvl_scale
            pierce_chance += float(mb.get("piercePct", 0)) * mount_lvl_scale

        # Pet-System & Boni (Kap. 12 & Projekt 1 PetSubsystem: Starter-Pet "Grüner Smaragddrache")
        pet_data = self._ensure_player_pet_data(p)
        pet_id = p.get("active_pet")
        if not pet_id and str(p.get("player_id", "") or "").startswith("bot_"):
            pet_id = "pet_fire_phoenix"
            p["active_pet"] = pet_id
        if pet_id and pet_id not in PETS:
            pet_id = "pet_fire_phoenix"
            p["active_pet"] = pet_id
        pet_bonus_atk = 0
        pet_bonus_magic_atk = 0
        pet_dmg_pct = 0.0
        pet_lvl_scale = min(1.0, max(0.25, lvl / 38.0))
        if pet_id and pet_id in PETS:
            pt_info = PETS[pet_id]
            crit_chance += pt_info["critBonusPct"] * 0.35 * pet_lvl_scale
            pierce_chance += pt_info["critBonusPct"] * 0.30 * pet_lvl_scale
            exp_bonus_pct += pt_info["expBonusPct"]
            max_hp += int(pt_info["hpBonus"] * pet_lvl_scale)

            # 1. Pet-Level-Grundbonus & Statusattribute (VIT, STR, DEX, INT)
            p_lvl = max(1, int(pet_data.get("level", 1) or 1))
            eff_p_lvl = min(p_lvl, max(1, int(lvl * 1.15)))
            p_vit = int(pet_data.get("vit", 0))
            p_str = int(pet_data.get("str", 0))
            p_dex = int(pet_data.get("dex", 0))
            p_int = int(pet_data.get("int", 0))
            max_hp += int((p_vit * 14 + eff_p_lvl * 6) * pet_lvl_scale)
            defense += (p_vit * 0.35 + p_dex * 0.45 + eff_p_lvl * 0.25) * pet_lvl_scale
            hp_regen_bonus_pct += p_vit * 0.08
            lvl_atk_add = eff_p_lvl * 0.65 * pet_lvl_scale
            lvl_pvm_add = eff_p_lvl * 0.08 * pet_lvl_scale
            atk += (p_str * 0.75 + p_dex * 0.35) * pet_lvl_scale + lvl_atk_add
            vs_monster_pct += (p_str * 0.10) * pet_lvl_scale + lvl_pvm_add
            crit_chance += p_dex * 0.07 * pet_lvl_scale
            dodge_chance += p_dex * 0.06 * pet_lvl_scale
            magic_atk += (p_int * 0.85) * pet_lvl_scale + lvl_atk_add
            skill_dmg_pct += p_int * 0.12 * pet_lvl_scale
            max_mp += int(p_int * 10 * pet_lvl_scale)

            # 2. Passive Pet-Fertigkeiten (Stufe 1 - 20)
            p_skills = pet_data.get("skills", {})
            herrschaft_lv = int(p_skills.get("herrschaft", 0) or 0)
            jaeger_lv = int(p_skills.get("jaeger", 0) or 0)
            dss_sk_lv = int(p_skills.get("zerstoerung_dss", 0) or 0)
            fks_sk_lv = int(p_skills.get("zerstoerung_fks", 0) or 0)
            for sk_id, sk_lv in p_skills.items():
                lv = int(sk_lv or 0)
                if lv <= 0:
                    continue
                if sk_id == "erfahrungsrausch":
                    exp_bonus_pct += lv * 6.0
                elif sk_id == "dungeonmeister":
                    vs_boss_pct += lv * 0.55 * pet_lvl_scale
                elif sk_id == "jaeger":
                    vs_metin_pct += lv * 0.55 * pet_lvl_scale
                    vs_monster_pct += lv * 0.55 * pet_lvl_scale
                elif sk_id == "schatzgraeber":
                    yang_bonus_pct += lv * 1.5
                    drop_bonus_pct += lv * 1.5
                elif sk_id == "gluecksbringer":
                    drop_bonus_pct += lv * 0.8
                elif sk_id == "monsterschild":
                    monster_res_pct += lv * 0.65 * pet_lvl_scale
                elif sk_id in ("erdverstaendnis", "windverstaendnis", "eisverstaendnis", "feuerverstaendnis", "dunkelheitverstaendnis"):
                    vs_monster_pct += lv * 0.25 * pet_lvl_scale
                elif sk_id == "herrschaft":
                    atk += lv * 2.0 * pet_lvl_scale
                    magic_atk += lv * 2.0 * pet_lvl_scale
                elif sk_id == "widerstand":
                    defense += lv * 0.65 * pet_lvl_scale
                elif sk_id == "zerstoerung_fks":
                    skill_dmg_pct += lv * 0.35 * pet_lvl_scale
                    cast_speed_pct += lv * 0.35
                elif sk_id == "beschuetzer_fks":
                    monster_res_pct += lv * 0.3
                elif sk_id == "zerstoerung_dss":
                    dss_pct += lv * 0.35 * pet_lvl_scale
                    atk_speed *= 1.0 + (lv * 0.35) / 100.0
                elif sk_id == "beschuetzer_dss":
                    monster_res_pct += lv * 0.3
                elif sk_id == "resistenz":
                    monster_res_pct += lv * 0.35
                elif sk_id == "unberuehrbarkeit":
                    dodge_chance += lv * 0.35
                elif sk_id == "vampirismus":
                    hp_absorb_pct += lv * 0.35
                elif sk_id == "reichweite" and p.get("class_id") == "ninja":
                    bow_range_bonus += lv * 0.4

            pet_bonus_atk = int(round(lvl_atk_add + (p_str * 0.75 + p_dex * 0.35 + herrschaft_lv * 2.0) * pet_lvl_scale))
            pet_bonus_magic_atk = int(round(lvl_atk_add + (p_int * 0.85 + herrschaft_lv * 2.0) * pet_lvl_scale))
            pet_dmg_pct = round(lvl_pvm_add + (p_str * 0.10 + jaeger_lv * 0.55 + dss_sk_lv * 0.35 + fks_sk_lv * 0.35) * pet_lvl_scale, 1)

        if dss_pct > 0:
            eff_dss_pct = min(35.0, dss_pct) * (0.65 if mount_id else 0.55)
            atk *= 1.0 + eff_dss_pct / 100.0

        # Rangpunkte-Boni (Kap. 13: Monster & Halbmenschen gemäß Rangsystem)
        rep_rank = get_reputation_rank(int(p.get("reputation", 0)))
        vs_monster_pct += float(rep_rank.get("vsMonsterPct", 0)) * 0.55
        vs_halfhuman_pct += float(rep_rank.get("vsHalfHumanPct", 0)) * 0.65

        # Aktive Skill-Buffs (z. B. Aura des Schwerts / Verzauberte Klinge / Hilfe des Drachen)
        now = time.time()
        if "activeBuffs" in p and "rift_purify" in p["activeBuffs"]:
            p["activeBuffs"].pop("rift_purify", None)
        p.pop("isBlocking", None)

        # Permanente Boni aus der 7-stufigen Biologenforschung (Living Quest System V2)
        bio_bonuses = p.get("quests", {}).get("__biologist_bonuses__", {})
        if not isinstance(bio_bonuses, dict):
            bio_bonuses = {}
        bio_summary = {
            "hp": 0,
            "mp": 0,
            "atk": 0,
            "def": 0,
            "speedPct": 0,
            "critChance": 0,
            "pierceChance": 0,
            "vsMonsterPct": 0,
            "vsMetinPct": 0,
            "vsBossPct": 0,
            "completedStages": len(bio_bonuses),
        }
        for _bqid, bdata in bio_bonuses.items():
            if not isinstance(bdata, dict):
                continue
            bio_summary["hp"] += int(bdata.get("hp", 0))
            bio_summary["mp"] += int(bdata.get("mp", 0))
            bio_summary["atk"] += int(bdata.get("atk", 0))
            bio_summary["def"] += int(bdata.get("def", 0))
            bio_summary["speedPct"] += int(bdata.get("speedPct", 0))
            bio_summary["critChance"] += int(bdata.get("critChance", 0))
            bio_summary["pierceChance"] += int(bdata.get("pierceChance", 0))
            bio_summary["vsMonsterPct"] += int(bdata.get("vsMonsterPct", 0))
            bio_summary["vsMetinPct"] += int(bdata.get("vsMetinPct", 0))
            bio_summary["vsBossPct"] += int(bdata.get("vsBossPct", 0))

        max_hp += bio_summary["hp"]
        max_mp += bio_summary["mp"]
        atk += bio_summary["atk"]
        magic_atk += bio_summary["atk"]
        defense += bio_summary["def"]
        if bio_summary["speedPct"] > 0:
            speed *= 1.0 + (bio_summary["speedPct"] / 100.0)
        crit_chance += bio_summary["critChance"]
        pierce_chance += bio_summary["pierceChance"]
        vs_monster_pct += bio_summary["vsMonsterPct"]
        vs_metin_pct += bio_summary["vsMetinPct"]
        vs_boss_pct += bio_summary["vsBossPct"]

        active_buffs = []
        in_vwk = False
        tot_buff_atk_pct = 0.0
        tot_buff_matk_pct = 0.0
        tot_buff_def_pct = 0.0
        tot_buff_atk_spd_pct = 0.0
        tot_buff_move_spd_pct = 0.0
        self.sanitize_player_doctrine_buffs(p)
        for buff_id, buff_data in list(p.get("activeBuffs", {}).items()):
            if buff_data["expiresAt"] > now:
                if buff_id in ("orb_vwk", "vwk"):
                    in_vwk = True
                tot_buff_atk_pct += float(buff_data.get("atkPct", 0)) * 0.25
                tot_buff_matk_pct += float(buff_data.get("magicAtkPct", buff_data.get("atkPct", 0))) * 0.25
                if "atkSpeedPct" in buff_data or "moveSpeedPct" in buff_data:
                    tot_buff_atk_spd_pct += float(buff_data.get("atkSpeedPct", 0))
                    tot_buff_move_spd_pct += float(buff_data.get("moveSpeedPct", 0))
                else:
                    raw_spd = float(buff_data.get("speedPct", 0))
                    tot_buff_atk_spd_pct += raw_spd * 0.35
                    tot_buff_move_spd_pct += raw_spd * 0.25
                if buff_data.get("hpAbsorbPct"):
                    hp_absorb_pct += float(buff_data["hpAbsorbPct"]) * 0.65
                if buff_data.get("defPct"):
                    tot_buff_def_pct += float(buff_data["defPct"]) * 0.22
                if buff_data.get("critPct"):
                    crit_chance += float(buff_data["critPct"]) * 0.30
                sk_lv = int(buff_data.get("skillLevel", p.get("skills", {}).get(buff_id, 1)))
                sk_tier = 5 if sk_lv >= 50 else (4 if sk_lv >= 40 else (3 if sk_lv >= 30 else (2 if sk_lv >= 20 else 1)))
                active_buffs.append(
                    {
                        "id": buff_id,
                        "name": buff_data["name"],
                        "remaining": round(buff_data["expiresAt"] - now, 1),
                        "skillLevel": sk_lv,
                        "skillTier": sk_tier,
                        "atkPct": int(round(float(buff_data.get("atkPct", 0)) * 0.25)),
                        "magicAtkPct": int(round(float(buff_data.get("magicAtkPct", buff_data.get("atkPct", 0))) * 0.25)),
                        "defPct": int(round(float(buff_data.get("defPct", 0)) * 0.22)),
                        "hpAbsorbPct": round(float(buff_data.get("hpAbsorbPct", 0)) * 0.65, 1),
                        "critPct": round(float(buff_data.get("critPct", 0)) * 0.30, 1),
                        "atkSpeedPct": int(round(float(buff_data["atkSpeedPct"]) if "atkSpeedPct" in buff_data else float(buff_data.get("speedPct", 0)) * 0.35)),
                        "moveSpeedPct": int(round(float(buff_data["moveSpeedPct"]) if "moveSpeedPct" in buff_data else float(buff_data.get("speedPct", 0)) * 0.25)),
                    }
                )
            else:
                p["activeBuffs"].pop(buff_id, None)

        if tot_buff_atk_pct > 0:
            atk *= 1.0 + min(28.0, tot_buff_atk_pct) / 100.0
        if tot_buff_matk_pct > 0:
            magic_atk *= 1.0 + min(28.0, tot_buff_matk_pct) / 100.0
        if tot_buff_def_pct > 0:
            defense *= 1.0 + min(22.0, tot_buff_def_pct) / 100.0
        if tot_buff_atk_spd_pct > 0:
            atk_speed *= 1.0 + min(30.0, tot_buff_atk_spd_pct) / 100.0
        if tot_buff_move_spd_pct > 0:
            speed *= 1.0 + min(40.0, tot_buff_move_spd_pct) / 100.0

        # Klassenspezifische Waffen-Mechaniken (Klingenwächter, Schattenjäger, Runenmagier, Seelenweber)
        is_double_strike = False
        inv_items = p.get("inventory") or []
        has_arrows = any(isinstance(it, dict) and it.get("templateId") == "arrow_bundle" and int(it.get("quantity", 0)) > 0 for it in inv_items)
        if has_weapon:
            if weapon_sub_type == "two_hand":
                if mount_id or in_vwk:
                    if weapon_atk_speed_pct < 0:
                        atk_speed /= max(0.5, 1.0 + (weapon_atk_speed_pct * 0.5) / 100.0)
                    atk_speed = max(atk_speed, 1.12)
                    atk *= 1.08
                else:
                    atk_speed *= 0.90
            elif weapon_sub_type == "dagger":
                is_double_strike = True
                atk += dex * 0.55
                atk_speed *= 1.15
            elif weapon_sub_type == "bow":
                if has_arrows:
                    atk += 12.0
                atk += dex * 0.45
            elif weapon_sub_type in ("staff", "bell"):
                magic_atk += int_s * 0.55
                if mount_id:
                    atk += int_s * 0.65
                    atk *= 1.06

        # Stufengerechte Low-/Mid-Level Balance-Dämpfung (erlaubt volle SSOT +9 Werte ohne künstliche Beschneidung)
        if lvl <= 45:
            soft_def_cap = 55.0 + lvl * 8.5
            if defense > soft_def_cap:
                defense = soft_def_cap + (defense - soft_def_cap) * 0.35
            soft_atk_cap = 85.0 + lvl * 10.5
            if atk > soft_atk_cap:
                atk = soft_atk_cap + (atk - soft_atk_cap) * 0.35
            soft_matk_cap = 75.0 + lvl * 9.5
            if magic_atk > soft_matk_cap:
                magic_atk = soft_matk_cap + (magic_atk - soft_matk_cap) * 0.35
            soft_mob_cap = 6.0 + lvl * 0.55
            if vs_monster_pct > soft_mob_cap:
                vs_monster_pct = soft_mob_cap + (vs_monster_pct - soft_mob_cap) * 0.18
            soft_metin_cap = 5.0 + lvl * 0.50
            if vs_metin_pct > soft_metin_cap:
                vs_metin_pct = soft_metin_cap + (vs_metin_pct - soft_metin_cap) * 0.18
            soft_crit_cap = 6.0 + lvl * 0.45
            if crit_chance > soft_crit_cap:
                crit_chance = min(28.0, soft_crit_cap + (crit_chance - soft_crit_cap) * 0.20)
            soft_pierce_cap = 5.0 + lvl * 0.40
            if pierce_chance > soft_pierce_cap:
                pierce_chance = min(25.0, soft_pierce_cap + (pierce_chance - soft_pierce_cap) * 0.20)

        if has_weapon:
            if weapon_sub_type == "bow":
                base_atk_range = 12.5
            elif weapon_sub_type == "two_hand":
                base_atk_range = 3.85
            elif weapon_sub_type == "dagger":
                base_atk_range = 2.45
            elif weapon_sub_type in ("staff", "bell"):
                base_atk_range = 3.25
            else:
                base_atk_range = 3.15
        else:
            base_atk_range = float(bstats["attackRange"])

        # Combo-Fertigkeit zu Fuß: Standard 4 Schläge, erweitert auf 5 bzw. 6 Schläge durch Combo-Training / Kampferfahrung
        combo_stage = int(p.get("comboMastery", 2))
        max_combo_steps = 4 if mount_id else max(4, min(6, 4 + combo_stage))

        atk_speed = max(0.75, min(1.42, atk_speed))
        p["max_hp"] = max_hp
        p["max_mp"] = max_mp
        p["hp"] = min(max_hp, max(1, int(p["hp"])))
        p["mp"] = min(max_mp, max(0, int(p["mp"])))

        cur_map_id = p.get("map_id", "morgenwacht")
        cur_map_def = MAPS.get(cur_map_id, MAPS["morgenwacht"])
        map_min_lvl = int(cur_map_def.get("minLevel", 1))
        map_max_lvl = int(cur_map_def.get("maxLevel", 15))
        map_reward_factor = self.compute_map_level_factor(lvl, cur_map_id)

        computed = {
            "maxHp": max_hp,
            "maxMp": max_mp,
            "atk": int(round(atk)),
            "magicAtk": int(round(magic_atk)),
            "def": int(round(defense)),
            "speed": round(speed, 2),
            "atkSpeed": round(atk_speed, 2),
            "critChance": round(min(45.0, crit_chance), 1),
            "pierceChance": round(min(45.0, pierce_chance), 1),
            "dodgeChance": round(min(55.0, max(0.0, dodge_chance)), 1),
            "dodgeVal": round(min(55.0, max(0.0, dodge_chance)), 1),
            "vsMonsterPct": round(vs_monster_pct, 1),
            "vsMetinPct": round(vs_metin_pct, 1),
            "vsBossPct": round(vs_boss_pct, 1),
            "vsDevilPct": round(vs_devil_pct, 1),
            "vsUndeadPct": round(vs_undead_pct, 1),
            "vsOrcsPct": round(vs_orcs_pct, 1),
            "vsAnimalsPct": round(vs_animals_pct, 1),
            "vsEsotericPct": round(vs_esoteric_pct, 1),
            "vsHalfHumanPct": round(vs_halfhuman_pct, 1),
            "defSwordPct": round(min(60.0, def_sword_pct), 1),
            "defTwoHandPct": round(min(60.0, def_two_hand_pct), 1),
            "defDaggerPct": round(min(60.0, def_dagger_pct), 1),
            "defArrowPct": round(min(60.0, def_arrow_pct), 1),
            "defStaffPct": round(min(60.0, def_staff_pct), 1),
            "resMagicPct": round(min(65.0, res_magic_pct), 1),
            "resFirePct": round(min(65.0, res_fire_pct), 1),
            "resLightningPct": round(min(65.0, res_lightning_pct), 1),
            "resWindPct": round(min(65.0, res_wind_pct), 1),
            "resIcePct": round(min(65.0, res_ice_pct), 1),
            "resPoisonPct": round(min(65.0, res_poison_pct), 1),
            "stunImmune": bool(stun_immune),
            "blockChancePct": round(min(50.0, block_chance_pct), 1),
            "poisonChancePct": round(min(40.0, poison_chance_pct), 1),
            "bleedChancePct": round(min(40.0, bleed_chance_pct), 1),
            "stunChancePct": round(min(35.0, stun_chance_pct), 1),
            "elemPowerPct": round(elem_power_pct, 1),
            "resBossSkillPct": round(min(50.0, res_boss_skill_pct), 1),
            "resCritPct": round(min(50.0, res_crit_pct), 1),
            "expBonusPct": round(exp_bonus_pct, 1),
            "yangBonusPct": round(yang_bonus_pct, 1),
            "dropBonusPct": round(drop_bonus_pct, 1),
            "hpRegenBonusPct": round(hp_regen_bonus_pct, 1),
            "mpRegenBonusPct": round(mp_regen_bonus_pct, 1),
            "castSpeedPct": round(cast_speed_pct, 1),
            "monsterResPct": round(min(50.0, monster_res_pct), 1),
            "skillDmgPct": round(skill_dmg_pct, 1),
            "dssPct": round(dss_pct, 1),
            "hpAbsorbPct": round(min(35.0, hp_absorb_pct), 1),
            "bowRangeBonus": round(bow_range_bonus, 1),
            "attackRange": round(base_atk_range + (0.65 if mount_id else 0.0) + (bow_range_bonus * 0.35), 2),
            "maxComboSteps": max_combo_steps,
            "mountStrBonus": mount_str_bonus,
            "horseLevel": horse_level,
            "horseSkills": HORSE_SKILLS,
            "horseSkillsUnlocked": horse_level >= 50,
            "mountVisualSkin": (
                mount_data.get("visualSkin", "horse_lvl1")
                if (mount_data.get("equippedSkin", "none") != "none" or mount_data.get("skinExplicit"))
                else (costume_mount_skin or mount_data.get("visualSkin", "horse_lvl1"))
            ),
            "hasCostumeMountSkin": bool(
                costume_mount_skin
                and mount_data.get("equippedSkin", "none") == "none"
                and not mount_data.get("skinExplicit")
            ),
            "mountData": mount_data,
            "petActive": bool(pet_id and pet_id in PETS),
            "petSkin": costume_pet_skin or pet_data.get("skinKey", "ridack_dragonpet"),
            "hasCostumePetSkin": bool(costume_pet_skin),
            "petLevel": int(pet_data.get("level", 1)),
            "petName": pet_data.get("customName", "Grüner Smaragddrache"),
            "petBonusAtk": pet_bonus_atk,
            "petBonusMagicAtk": pet_bonus_magic_atk,
            "petDmgPct": pet_dmg_pct,
            "weaponPlus": weapon_plus,
            "armorPlus": armor_plus,
            "weaponVisual": weapon_visual,
            "weaponSubType": weapon_sub_type if has_weapon else None,
            "isDoubleStrike": is_double_strike,
            "inVwk": in_vwk,
            "hasArrows": has_arrows,
            "hasWeapon": has_weapon,
            "hasArmor": has_armor,
            "hasShield": has_shield,
            "hasHelmet": has_helmet,
            "hasShoes": has_shoes,
            "hasGloves": has_gloves,
            "reputationRank": rep_rank,
            "activeBuffs": active_buffs,
            "biologistBonuses": bio_bonuses,
            "biologistSummary": bio_summary,
            "expNeeded": exp_needed_for_level(lvl),
            "mapMinLevel": map_min_lvl,
            "mapMaxLevel": map_max_lvl,
            "mapLevelRange": cur_map_def.get("levelRange", f"Lv. {map_min_lvl} – {map_max_lvl}"),
            "mapRewardPct": int(round(map_reward_factor * 100)),
        }
        p["computed"] = computed
        return computed

    def compute_map_level_factor(self, player_lvl: int, map_id: str, for_exp: bool = False) -> float:
        """
        Prüft, ob der Charakter im vorgesehenen Levelbereich der Karte (minLevel..maxLevel) liegt.
        SSOT Teil I Abs. 1: Ab Level 38 kaum noch EXP in den jetzigen Gebieten (Map 1 & Map 2 = 'morgenwacht').
        """
        mdef = MAPS.get(map_id, MAPS["morgenwacht"])
        min_lvl = int(mdef.get("minLevel", 1))
        max_lvl = int(mdef.get("maxLevel", 37))
        pl = max(1, int(player_lvl))
        if pl < min_lvl:
            return 0.0
        if map_id == "morgenwacht" and pl >= 38:
            if for_exp:
                return 0.02 if pl == 38 else (0.01 if pl == 39 else 0.0)
            over_mw = pl - 37
            drop_table = {1: 0.80, 2: 0.55, 3: 0.30, 4: 0.15, 5: 0.05}
            return drop_table.get(over_mw, 0.0)
        if pl <= max_lvl:
            return 1.0
        over = pl - max_lvl
        table = {1: 0.75, 2: 0.50, 3: 0.30, 4: 0.15, 5: 0.05}
        return table.get(over, 0.0)

    def compute_level_reward_penalty(self, player_lvl: int, mob_lvl: int, map_id: str, for_exp: bool = False) -> float:
        """
        Kombinierte Levelbereichs-Skalierung (Charakter-Level vs. Map-Levelbereich & Monster-Level):
        1. Außerhalb des Map-Levelbereichs sinkt die Ausbeute rapide bis auf 0 % (EXP ab Lv. 38 in Map 1/2 -> ~2%).
        2. Auch innerhalb der Karte sinken EXP & Drops schrittweise, je weiter das Charakter-Level
           über dem Monster-Level liegt (ab +12 Level über dem Monster: 0 % EXP & 0 % Drops).
        """
        map_factor = self.compute_map_level_factor(player_lvl, map_id, for_exp=for_exp)
        if map_factor <= 0.0:
            return 0.0

        pl = max(1, int(player_lvl))
        ml = max(1, int(mob_lvl))
        diff = pl - ml

        if diff <= 2:
            if diff < -5:
                under = abs(diff) - 5
                mob_factor = max(0.0, 1.0 - under * 0.18)
            else:
                mob_factor = 1.0
        else:
            mob_table = {
                3: 0.90,
                4: 0.80,
                5: 0.70,
                6: 0.58,
                7: 0.46,
                8: 0.35,
                9: 0.24,
                10: 0.15,
                11: 0.08,
            }
            mob_factor = mob_table.get(diff, 0.0)

        return round(min(map_factor, mob_factor), 3)

    # ========================================================================
    # 3. SPIELER-SESSION VERWALTUNG
    # ========================================================================
    def register_player(
        self,
        player_id: str,
        name: str = "KriegerVonAeryndor",
        class_id: str = "warrior",
        empire: Optional[str] = None,
        mark_online: bool = False,
    ) -> dict:
        if player_id in self.players:
            p = self.players[player_id]
            if empire and str(empire).lower() in ("kaeryu", "seiryu"):
                p["empire"] = str(empire).lower()
            if mark_online and player_id != "hero_default":
                p["online"] = True
                p["inWorld"] = True
                p["lastSeen"] = time.time()
            if p.get("map_id") not in MAPS:
                p["map_id"] = "morgenwacht"
                is_kaeryu = str(p.get("faction", p.get("empire", ""))).lower() == "kaeryu"
                p["pos_x"] = -790.0 if is_kaeryu else 790.0
                p["pos_z"] = -740.0
                self.db.save_player_state(p)
            cur_map_def = MAPS.get(p.get("map_id", "morgenwacht"), MAPS["morgenwacht"])
            if not self._is_sa_player(p, player_id) and int(p.get("level", 1)) < int(cur_map_def.get("minLevel", 1)):
                p["map_id"] = "morgenwacht"
                is_kaeryu = str(p.get("faction", p.get("empire", ""))).lower() == "kaeryu"
                p["pos_x"] = -790.0 if is_kaeryu else 790.0
                p["pos_z"] = -740.0
                self.db.save_player_state(p)
            if self._is_sa_player(p, player_id):
                inv = p.get("inventory", [])
                has_shard = sum(int(i.get("quantity", 1)) for i in inv if i.get("templateId") == "mat_monolith_shard")
                has_core = sum(int(i.get("quantity", 1)) for i in inv if i.get("templateId") == "mat_awakened_rift_core")
                if has_shard < 5:
                    self.db.add_item_to_inventory(player_id, "mat_monolith_shard", 5 - has_shard)
                if has_core < 5:
                    self.db.add_item_to_inventory(player_id, "mat_awakened_rift_core", 5 - has_core)
                if has_shard < 5 or has_core < 5:
                    self.refresh_player_from_db(player_id)
                    p = self.players[player_id]
            self.compute_player_combat_stats(p)
            return p

        p = self.db.load_or_create_player(player_id, name, class_id, empire=empire or "seiryu")
        if p.get("map_id") not in MAPS:
            p["map_id"] = "morgenwacht"
            is_kaeryu = str(p.get("faction", p.get("empire", ""))).lower() == "kaeryu"
            p["pos_x"] = -790.0 if is_kaeryu else 790.0
            p["pos_z"] = -740.0
        cur_map_def = MAPS.get(p.get("map_id", "morgenwacht"), MAPS["morgenwacht"])
        if not self._is_sa_player(p, player_id) and int(p.get("level", 1)) < int(cur_map_def.get("minLevel", 1)):
            p["map_id"] = "morgenwacht"
            is_kaeryu = str(p.get("faction", p.get("empire", ""))).lower() == "kaeryu"
            p["pos_x"] = -790.0 if is_kaeryu else 790.0
            p["pos_z"] = -740.0
        px_cur = float(p.get("pos_x", 0.0))
        pz_cur = float(p.get("pos_z", 145.5))
        if (
            (abs(px_cur) < 1.5 and abs(pz_cur - 145.5) < 1.5)
            or (abs(px_cur - 17.5) < 1.5 and abs(pz_cur - 145.5) < 1.5)
            or (abs(px_cur - 16.0) < 3.0 and abs(pz_cur - (-142.0)) < 3.0)
            or (abs(px_cur - 14.5) < 3.0 and abs(pz_cur - (-195.9)) < 3.0)
            or (abs(px_cur - 48.0) < 15.0 and abs(pz_cur - (-426.0)) < 15.0)
        ):
            is_kaeryu = str(p.get("faction", p.get("empire", ""))).lower() == "kaeryu"
            p["pos_x"] = -790.0 if is_kaeryu else 790.0
            p["pos_z"] = -740.0
            p["rot_y"] = 1.35 if is_kaeryu else -1.35
        is_active = bool(mark_online and player_id != "hero_default")
        p["online"] = is_active
        p["inWorld"] = is_active
        p["lastSeen"] = time.time() if is_active else 0.0
        p["targetId"] = None
        p["autoAttackTargetId"] = None
        p["moveTarget"] = None
        p["lastBasicAttack"] = 0.0
        p["lastSkillCastTime"] = 0.0
        p["skillCooldowns"] = {}
        p["activeBuffs"] = {}
        p["autoFarmStatus"] = "Bereit"
        self.compute_player_combat_stats(p)
        # Stelle sicher, dass im Live-Server-Speicher (self.players) niemals zwei Einträge denselben Namen tragen
        p_name_key = str(p.get("name") or "").strip().lower()
        if p_name_key:
            for other_pid, other_p in list(self.players.items()):
                if other_pid != player_id and str(other_p.get("name") or "").strip().lower() == p_name_key:
                    self.players.pop(other_pid, None)
        if player_id != "hero_default":
            self.players[player_id] = p
            self.db.save_player_state(p)
        if self._is_sa_player(p, player_id):
            inv = p.get("inventory", [])
            has_shard = sum(int(i.get("quantity", 1)) for i in inv if i.get("templateId") == "mat_monolith_shard")
            has_core = sum(int(i.get("quantity", 1)) for i in inv if i.get("templateId") == "mat_awakened_rift_core")
            if has_shard < 5:
                self.db.add_item_to_inventory(player_id, "mat_monolith_shard", 5 - has_shard)
            if has_core < 5:
                self.db.add_item_to_inventory(player_id, "mat_awakened_rift_core", 5 - has_core)
            if has_shard < 5 or has_core < 5:
                self.refresh_player_from_db(player_id)
                p = self.players[player_id]
        return p

    def disconnect_player(self, player_id: str):
        p = self.players.get(player_id)
        if p:
            # Wichtig (Kap. 6): Ohne aktive Verbindung kämpft Auto-Farming nicht weiter und der Charakter verschwindet sofort!
            p["online"] = False
            p["inWorld"] = False
            p["moveTarget"] = None
            p["autoAttackTargetId"] = None
            p["autoFarmTargetId"] = None
            if "autofarm" in p:
                p["autofarm"]["enabled"] = False
            for m in self.monsters.values():
                if m.get("targetPlayerId") == player_id:
                    m["targetPlayerId"] = None
            self.db.save_player_state(p)

    def refresh_player_from_db(self, player_id: str) -> Optional[dict]:
        old = self.players.get(player_id)
        if not old:
            return None
        fresh = self.db.load_or_create_player(
            player_id, old["name"], old["class_id"], empire=old.get("empire", "seiryu")
        )
        # Behalte sämtliche Echtzeit-Laufzeitfelder (insb. lastManualMoveTime, lastAutoMoveTime, vx/vz, teleportSeq, active_mount, active_pet & autofarm)
        for k in (
            "online",
            "inWorld",
            "accountName",
            "sessionToken",
            "lastSeen",
            "empire",
            "isDead",
            "deadAt",
            "targetId",
            "autoAttackTargetId",
            "autoFarmTargetId",
            "autoFarmNextTargetId",
            "manualFocusTargetId",
            "moveTarget",
            "lastBasicAttack",
            "lastSkillTime",
            "lastSkillCastTime",
            "lastPassiveLootScan",
            "lastManualMoveTime",
            "lastAutoMoveTime",
            "vx",
            "vz",
            "moveSpeed",
            "dest_x",
            "dest_z",
            "_lastMountToggleAt",
            "_lastAutoMountSwitchAt",
            "_lastTargetScanAt",
            "_lastPetToggleAt",
            "_manualDismountUntil",
            "comboStep",
            "teleportSeq",
            "skillCooldowns",
            "activeBuffs",
            "autoFarmStatus",
            "autofarm",
            "petData",
            "partyId",
            "activeTradeId",
            "pendingPartyInvite",
            "pendingTradeRequest",
            "lastSocialNotice",
            "lastWhisperNotice",
            "social",
            "routeSector",
            "bridgeCrossings",
            "partySplits",
            "empireSkirmishes",
            "evolutionV3",
            "lastAutoPullTime",
            "capesUsed",
            "monolithsAwakened",
            "monolithsMadeUnstable",
            "worldBossesSummoned",
            "worldBossCoopAssists",
            "_lastBotMonolithAwakenAt",
            "_lastBotMonolithAwakenCheckAt",
            "_monolithItemsSeededAt",
            "_botTradeStatusUntil",
            "potionRegenRemaining",
            "potionRegenRate",
        ):
            if k in old and old.get(k) is not None:
                fresh[k] = old.get(k)
        # WICHTIG: active_mount und active_pet AUCH dann aus dem Live-Speicher übernehmen, wenn sie None sind!
        for nullable_k in ("active_mount", "active_pet"):
            if nullable_k in old:
                fresh[nullable_k] = old.get(nullable_k)
        fresh["pos_x"] = old["pos_x"]
        fresh["pos_z"] = old["pos_z"]
        fresh["rot_y"] = old.get("rot_y", 0.0)
        if old.get("isDead") or int(old.get("hp", 1)) <= 0:
            fresh["hp"] = 0
            fresh["isDead"] = True
        else:
            fresh["hp"] = min(old["hp"], fresh["max_hp"])
        fresh["mp"] = min(old["mp"], fresh["max_mp"])
        self.compute_player_combat_stats(fresh)
        # In-Place-Update auf `old`, damit parallele Referenzen in HTTP/WS/Tick-Threads niemals veralten!
        old.clear()
        old.update(fresh)
        self.players[player_id] = old
        return old

    # ========================================================================
    # 4. HAUPT-SERVER-TICK (20 Hz Echtzeit-Simulation)
    # ========================================================================
    def tick(self, dt: float):
        now = time.time()
        active_maps = set()
        self.nav.save_memory()

        # 1. Regeneriere Spieler-TP/MP & führe Auto-Farming / Ziel-Angriff für verbundene Spieler aus
        for pid, p in list(self.players.items()):
            if not p.get("online", False):
                continue
            if pid == "hero_default" or not p.get("inWorld", False) or (now - float(p.get("lastSeen", 0.0) or 0.0)) > 12.0:
                self.disconnect_player(pid)
                continue
            active_maps.add(p["map_id"])
            if now - float(p.get("_lastCombatStatsAt", 0.0) or 0.0) >= 0.5:
                p["_lastCombatStatsAt"] = now
                self.compute_player_combat_stats(p)

            # Pet-Cooldowns laufen immer weiter (verhindert Exploit durch Wegschicken & Wiederrufen!)
            pet_data = self._ensure_player_pet_data(p)
            cds = pet_data.setdefault("cooldowns", {})
            for cd_k, cd_v in list(cds.items()):
                rem = max(0.0, float(cd_v or 0.0) - dt)
                if rem <= 0.01:
                    cds.pop(cd_k, None)
                else:
                    cds[cd_k] = round(rem, 2)

            # Wenn der Spieler tot ist (0 TP), keine Regeneration, keine Bewegung und kein Auto-Farming bis zum Neustart!
            if p.get("isDead") or float(p.get("hp", 1)) <= 0:
                p["hp"] = 0
                p["isDead"] = True
                if not p.get("deadAt"):
                    p["deadAt"] = now
                p["moveTarget"] = None
                p["autoAttackTargetId"] = None
                if str(p.get("player_id", "")).startswith("bot_") and (now - float(p.get("deadAt", now) or now)) >= 7.0:
                    self.respawn_player(p["player_id"], mode="here")
                continue

            # Natürliche Regeneration inkl. passiver TP/MP-Regeneration & Pet-VIT-Bonus (in Safezone 4x schneller)
            in_safe = is_in_safe_zone(p["map_id"], p["pos_x"], p["pos_z"])
            regen_mult = 4.0 if in_safe else 1.0
            comp = p.get("computed", {})
            hp_reg_mult = 1.0 + float(comp.get("hpRegenBonusPct", 0.0)) / 100.0
            mp_reg_mult = 1.0 + float(comp.get("mpRegenBonusPct", 0.0)) / 100.0
            if p["hp"] < p["max_hp"]:
                p["hp"] = min(p["max_hp"], p["hp"] + max(2.0, p["max_hp"] * 0.012 * regen_mult * hp_reg_mult) * dt)
            if p["mp"] < p["max_mp"]:
                p["mp"] = min(p["max_mp"], p["mp"] + max(2.0, p["max_mp"] * 0.025 * regen_mult * mp_reg_mult) * dt)
            # Trank-Regen: langsame TP-Auffüllung über Zeit
            potion_rem = float(p.get("potionRegenRemaining", 0.0))
            if potion_rem > 0.0 and p["hp"] < p["max_hp"]:
                pot_rate = float(p.get("potionRegenRate", 40.0))
                pot_tick = min(potion_rem, pot_rate * dt)
                actual_tick = min(pot_tick, p["max_hp"] - p["hp"])
                p["hp"] = min(p["max_hp"], p["hp"] + actual_tick)
                p["potionRegenRemaining"] = max(0.0, potion_rem - pot_tick)
                if p["potionRegenRemaining"] <= 0.0:
                    p["potionRegenRate"] = 0.0

            # Aktive Pet-Skills ticken (Auto-Pickup, Heilung, Erneuerung)
            if p.get("active_pet"):
                self._tick_pet_active_skills(p, now)

            # Serverseitiges Auto-Farming (Kap. 6) oder Linksklick-Zielverfolgung (wie in Projekt 1)
            af = p.get("autofarm", {})
            manual_override_active = (now - p.get("lastManualMoveTime", 0.0)) < 2.0
            if af.get("enabled", False):
                if not manual_override_active:
                    pos_before = (float(p["pos_x"]), float(p["pos_z"]))
                    self._tick_player_autofarm(p, dt, now)
                    moved_dist = dist2d(float(p["pos_x"]), float(p["pos_z"]), pos_before[0], pos_before[1])
                    last_act_t = max(
                        float(p.get("lastBasicAttack", 0.0) or 0.0),
                        float(p.get("lastSkillCastTime", 0.0) or 0.0),
                        float(p.get("lastFishTime", 0.0) or 0.0),
                        float(p.get("lastMineTime", 0.0) or 0.0),
                    )
                    stats = self.ensure_autofarm_stats(af)
                    if moved_dist > 0.005 or (now - last_act_t) <= 1.8:
                        stats["activeSeconds"] = round(float(stats.get("activeSeconds", 0.0)) + dt, 2)
                        p["isAfkIdle"] = False
                        p["_afkIdleStreakSec"] = 0.0
                    else:
                        # WICHTIG: Wenn ein Bot aus irgendeinem Grund AFK herumsteht, darf das NICHT in die aktive Statistik einberechnet werden!
                        stats["afkExcludedSeconds"] = round(float(stats.get("afkExcludedSeconds", 0.0)) + dt, 2)
                        p["isAfkIdle"] = True
                        p["_afkIdleStreakSec"] = float(p.get("_afkIdleStreakSec", 0.0) or 0.0) + dt
                        if str(p.get("player_id", "")).startswith("bot_") and p["_afkIdleStreakSec"] >= 4.0:
                            p["_afkIdleStreakSec"] = 0.0
                            p["targetId"] = None
                            p["autoFarmTargetId"] = None
                            p["manualFocusTargetId"] = None
                            ax = float(af.get("anchorX", p["pos_x"])) + random.uniform(-18.0, 18.0)
                            az = float(af.get("anchorZ", p["pos_z"])) + random.uniform(-18.0, 18.0)
                            self._move_player_towards(p, ax, az, dt)
            else:
                if p.get("autoAttackTargetId"):
                    self._tick_player_target_attack(p, dt, now, allow_move=not manual_override_active)
                elif p.get("moveTarget") and not manual_override_active and (now - float(p.get("lastBasicAttack", 0.0))) >= 0.45:
                    self._move_player_towards(p, p["moveTarget"]["x"], p["moveTarget"]["z"], dt)

                # Passiver Auto-Pick-Up Magnet (Projekt 1 Pet/Auto-Loot Standard) unter Beachtung des Drop-Filters
                df = af.get("dropFilter", {})
                if af.get("autoLoot", True) and df.get("passiveAutoPickup", True):
                    self._tick_passive_auto_pickup(p, now)

        # 2. Monster-, Rissmonolythen- & Boss-Simulation (Spatial-Filter: Nur auf aktiven Spieler-Maps ticken)
        self._tick_counter = getattr(self, "_tick_counter", 0) + 1
        if self._tick_counter % 35 == 0:
            self._tick_bot_party_and_trade_ai(now)
        self._active_rift_metins_by_map = {}
        self._metins_by_map = {}
        online_players_by_map = {}
        for p in self.players.values():
            if p.get("online"):
                online_players_by_map.setdefault(p["map_id"], []).append((p["pos_x"], p["pos_z"]))

        for m_cand in list(self.monsters.values()):
            if m_cand.get("kind") == "metin" and m_cand.get("state") != "dead":
                m_map = m_cand["mapId"]
                self._metins_by_map.setdefault(m_map, []).append(m_cand)
                if m_cand.get("monolithState") in ("instabil", "erwacht") or (now - float(m_cand.get("lastDamagedAt", 0.0) or 0.0) < 18.0):
                    self._active_rift_metins_by_map.setdefault(m_map, []).append(m_cand)

        for mid, mob in list(self.monsters.items()):
            if mob["state"] == "dead":
                if now >= mob["deadUntil"]:
                    if mob.get("isSummon"):
                        self.monsters.pop(mid, None)
                    else:
                        if mob.get("kind") == "metin":
                            if mob.get("isMajorMonolith"):
                                rx, rz = mob["spawnX"], mob["spawnZ"]
                                new_rarity = self._roll_monolith_rarity(mob["mapId"], exclude_mob_id=mid)
                                self._apply_monolith_rarity(mob, new_rarity)
                                self._spawn_monolith_guardians(mob, count=2)
                            else:
                                rx, rz = self._pick_random_monolith_coords(
                                    mob["mapId"], exclude_mob_id=mid, template_id=mob.get("templateId")
                                )
                                mob["spawnX"] = rx
                                mob["spawnZ"] = rz
                                mob["patrolX"] = rx
                                mob["patrolZ"] = rz
                                mob["rotY"] = random.uniform(0, math.pi * 2)
                                new_rarity = self._roll_monolith_rarity(mob["mapId"], exclude_mob_id=mid)
                                self._apply_monolith_rarity(mob, new_rarity)
                                if new_rarity == "erwacht":
                                    self._spawn_monolith_world_boss(mob)
                        mob["state"] = "idle"
                        mob["hp"] = mob["maxHp"]
                        mob["x"] = mob["spawnX"]
                        mob["z"] = mob["spawnZ"]
                        mob["targetPlayerId"] = None
                        mob["wavesSpawned"] = []
                        mob["bossPhase"] = 1
                        mob["combatPhase"] = 1
                        if mob.get("isMapAreaBoss"):
                            # Gebietsboss ist wieder erschienen -> Client: sanftes Kamera-Grollen + Hinweis
                            self._emit_combat_event(
                                mob["mapId"],
                                "area_boss_spawned",
                                mob["x"],
                                mob["z"],
                                {
                                    "bossId": mid,
                                    "bossName": mob.get("name", "Gebietsboss"),
                                    "level": int(mob.get("level", 1) or 1),
                                    "arenaId": mob.get("bossArenaId", ""),
                                },
                            )
                continue

            # 1-Stunde (3600s) Despawn-Timer für Riss-Weltboss + Erwachten Rissmonolith:
            # Wenn sie nach 1 Stunde nicht besiegt wurden, verschwinden beide gemeinsam wieder!
            despawn_at = float(mob.get("despawnAt", 0.0) or 0.0)
            if despawn_at > 0.0 and now >= despawn_at:
                if mob.get("isRiftWorldBoss"):
                    mono_id = mob.get("monolithBossOf")
                    mono = self.monsters.get(mono_id) if mono_id else None
                    map_title = MAPS.get(mob["mapId"], {}).get("name", mob["mapId"])
                    wb_name = mob["name"]
                    self.monsters.pop(mid, None)
                    if mono and mono.get("state") != "dead":
                        mono["state"] = "dead"
                        mono["hp"] = 0
                        mono["deadUntil"] = now + float(mono.get("respawnSec", 120.0))
                        mono["despawnAt"] = 0.0
                        mono["worldBossSummoned"] = False
                        mono["activeWorldBossId"] = None
                        for g_id, g_mob in list(self.monsters.items()):
                            if g_mob.get("monolithGuardOf") == mono["id"]:
                                self.monsters.pop(g_id, None)
                    self.add_chat_message(
                        "Welt-Herold",
                        f"⏳ [WELTBOSS VERSCHWUNDEN] {wb_name} in '{map_title}' wurde nach 1 Stunde nicht besiegt und ist zusammen mit dem Erwachten Rissmonolithen wieder verschwunden!",
                        channel="event",
                    )
                    self._emit_combat_event(
                        mob["mapId"],
                        "world_boss_despawned",
                        mob["x"],
                        mob["z"],
                        {"bossId": mid, "bossName": wb_name, "monolithId": mono_id},
                    )
                    continue
                elif mob.get("kind") == "metin" and mob.get("monolithState") == "erwacht":
                    wb_id = mob.get("activeWorldBossId")
                    wb_mob = self.monsters.pop(wb_id, None) if wb_id else None
                    for g_id, g_mob in list(self.monsters.items()):
                        if g_mob.get("monolithBossOf") == mid or g_mob.get("monolithGuardOf") == mid:
                            self.monsters.pop(g_id, None)
                    mob["state"] = "dead"
                    mob["hp"] = 0
                    mob["deadUntil"] = now + float(mob.get("respawnSec", 120.0))
                    mob["despawnAt"] = 0.0
                    mob["worldBossSummoned"] = False
                    mob["activeWorldBossId"] = None
                    map_title = MAPS.get(mob["mapId"], {}).get("name", mob["mapId"])
                    wb_name = wb_mob["name"] if wb_mob else "Der Weltboss"
                    self.add_chat_message(
                        "Welt-Herold",
                        f"⏳ [WELTBOSS VERSCHWUNDEN] {wb_name} und {mob['name']} in '{map_title}' wurden nach 1 Stunde nicht besiegt und sind gemeinsam wieder verschwunden!",
                        channel="event",
                    )
                    self._emit_combat_event(
                        mob["mapId"],
                        "world_boss_despawned",
                        mob["x"],
                        mob["z"],
                        {"bossId": wb_id, "bossName": wb_name, "monolithId": mid},
                    )
                    continue

            if mob["kind"] == "metin":
                m_st = mob.get("monolithState", "schlafend")
                if m_st == "instabil":
                    last_active = max(float(mob.get("lastDamagedAt", 0.0) or 0.0), float(mob.get("stateChangedAt", 0.0) or 0.0))
                    if last_active > 0.0 and (now - last_active) > 150.0:
                        self._apply_monolith_state(mob, "schlafend", announce=False, preserve_hp=False)
                        mob["wavesSpawned"] = []
                        mob["eliteBossesSpawned"] = 0
                        mob["guardsSpawned"] = False
                        for g_id, g_mob in list(self.monsters.items()):
                            if g_mob.get("monolithGuardOf") == mid:
                                self.monsters.pop(g_id, None)
                elif m_st == "erwacht":
                    last_hit = float(mob.get("lastDamagedAt", 0.0))
                    if last_hit > 0.0 and (now - last_hit) <= 12.0 and now >= float(mob.get("nextAoETime", 0.0)):
                        # Stufe 3 (Erwacht): Periodische Karmesin-Riss-Eruptionen (AoE-Todeszonen) alle 5.2s im Kampf!
                        mob["nextAoETime"] = now + 5.2
                        near_players = [
                            p_cand for p_cand in self.players.values()
                            if p_cand.get("online")
                            and not p_cand.get("isDead")
                            and p_cand.get("map_id") == mob["mapId"]
                            and dist2d(p_cand["pos_x"], p_cand["pos_z"], mob["x"], mob["z"]) <= 24.0
                        ]
                        if near_players:
                            tp = random.choice(near_players)
                            phase = int(mob.get("combatPhase", 1))
                            tel = {
                                "id": f"tel_{uuid.uuid4().hex[:8]}",
                                "mapId": mob["mapId"],
                                "bossId": mob["id"],
                                "bossName": mob["name"],
                                "bossX": round(mob["x"], 2),
                                "bossZ": round(mob["z"], 2),
                                "phase": max(2, phase),
                                "skillName": "Karmesin-Kataklysmus",
                                "isOrcSkill": False,
                                "x": round(tp["pos_x"], 2),
                                "z": round(tp["pos_z"], 2),
                                "radius": 4.8 + phase * 0.45,
                                "damage": int(mob.get("atk", 85) * (3.6 + phase * 0.65)),
                                "createdAt": now,
                                "explodeAt": now + 1.65,
                            }
                            self.telegraphs.append(tel)
                            self._emit_combat_event(mob["mapId"], "boss_telegraph", tel["x"], tel["z"], tel)
                continue
            if mob["mapId"] not in active_maps:
                continue

            # Weit entfernte, nicht kämpfende Monster nur jeden 10. Tick für Wander-Patrol aktualisieren
            if not mob.get("targetPlayerId") and mob.get("state") not in ("chase", "flee"):
                p_coords = online_players_by_map.get(mob["mapId"], ())
                mx, mz = mob["x"], mob["z"]
                near_any = any(abs(mx - px) <= 265.0 and abs(mz - pz) <= 265.0 for px, pz in p_coords)
                if not near_any:
                    if (self._tick_counter + hash(mid)) % 10 != 0:
                        continue
                    self._tick_monster_ai(mob, dt * 10.0, now)
                    continue

            self._tick_monster_ai(mob, dt, now)

        # 3. Verarbeite aktive Boss-Flächenangriffe (Telegraphs)
        for tel in list(self.telegraphs):
            if now >= tel["explodeAt"]:
                self._resolve_boss_telegraph(tel)
                self.telegraphs.remove(tel)

        # 4. Entferne abgelaufene Boden-Drops (60s Besitzer-/Gruppenschutz + 60s frei für alle = 120s Gesamtdauer)
        for did, dr in list(self.drops.items()):
            expires_at = float(dr.get("expiresAt", float(dr.get("createdAt", 0.0)) + 120.0))
            if now >= expires_at:
                self.drops.pop(did, None)

        # 4b. Prüfe Erkundungs-, Spur- & Lieferziele für aktive Quests (alle 0.5s)
        if self._tick_counter % 10 == 0:
            for p in self.players.values():
                if p.get("online"):
                    self._check_player_exploration_quests(p)

        # 5. Periodisches Speichern alle 10 Sekunden
        if now - self.last_save_time >= 10.0:
            self.last_save_time = now
            for p in self.players.values():
                if p.get("online"):
                    self.db.save_player_state(p)

    # ========================================================================
    # 5. PFADNAVIGATION, STADTTOR-ROUTING, BOT-LERNEN & BRÜCKEN-WEGFINDUNG
    # ========================================================================
    def _ensure_learned_bot_nav_grid(self) -> dict:
        grid = getattr(self, "_learned_nav_grid", None)
        if grid is not None and getattr(self, "_learned_nav_seeded", False):
            return grid
        if grid is None:
            grid = {}
            self._learned_nav_grid = grid
        self._learned_nav_seeded = True
        # Vorab-Initialisierung mit den bewährten Bot-Routen, Stadttoren (Kaeryu, Seiryu, Bakra),
        # den 2 äußeren Steinbrücken (-760 West / +760 Ost) und den Level-Jagdsektoren (Map 1 Nord & Map 2 Süd)
        seed_waypoints = (
            # Kaeryu (Nordwest) & Seiryu (Nordost) Stadttore + Hauptachsen
            (-820.0, -780.0, 18.0), (-698.0, -780.0, 22.0), (-820.0, -658.0, 22.0), (-820.0, -902.0, 18.0),
            (820.0, -780.0, 18.0), (698.0, -780.0, 22.0), (820.0, -658.0, 22.0), (820.0, -902.0, 18.0),
            # Bakra (Süden) Stadttore + Marktplatz
            (0.0, 880.0, 18.0), (0.0, 748.0, 24.0), (-132.0, 880.0, 20.0), (132.0, 880.0, 20.0), (0.0, 964.0, 18.0),
            # Die 2 äußeren Steinbrücken über den Silberstrom (-760 West & +760 Ost)
            (-760.0, -64.0, 26.0), (-760.0, -46.0, 28.0), (-760.0, -24.0, 30.0), (-760.0, 0.0, 32.0),
            (-760.0, 24.0, 30.0), (-760.0, 46.0, 28.0), (-760.0, 64.0, 26.0),
            (760.0, -64.0, 26.0), (760.0, -46.0, 28.0), (760.0, -24.0, 30.0), (760.0, 0.0, 32.0),
            (760.0, 24.0, 30.0), (760.0, 46.0, 28.0), (760.0, 64.0, 26.0),
            # Kanonische Bot-Jagdsektoren Map 1 Nord (Lv. 1–17) & Map 2 Süd (Lv. 18–35)
            (-560.0, -680.0, 20.0), (560.0, -680.0, 20.0),
            (-220.0, -740.0, 19.0), (220.0, -740.0, 19.0),
            (-580.0, -380.0, 21.0), (580.0, -380.0, 21.0),
            (-240.0, -195.0, 21.0), (240.0, -195.0, 21.0),
            (-480.0, 185.0, 22.0), (480.0, 185.0, 22.0),
            (-240.0, 285.0, 22.0), (240.0, 285.0, 22.0),
            (-420.0, 460.0, 22.0), (420.0, 460.0, 22.0),
            (-320.0, 625.0, 22.0), (320.0, 625.0, 22.0),
        )
        for sx, sz, sw in seed_waypoints:
            key = (int(round(sx / 8.0)), int(round(sz / 8.0)))
            grid[key] = max(float(grid.get(key, 0.0)), float(sw))
        return grid

    def _record_learned_bot_trail(self, x: float, z: float, weight_delta: float = 1.0):
        grid = self._ensure_learned_bot_nav_grid()
        key = (int(round(x / 8.0)), int(round(z / 8.0)))
        if len(grid) > 6000 and key not in grid:
            grid.pop(next(iter(grid)), None)
        grid[key] = min(100.0, float(grid.get(key, 0.0)) + weight_delta)

    def _get_learned_bot_trail_weight(self, x: float, z: float) -> float:
        grid = self._ensure_learned_bot_nav_grid()
        if not grid:
            return 0.0
        gx = int(round(x / 8.0))
        gz = int(round(z / 8.0))
        w = float(grid.get((gx, gz), 0.0))
        if w <= 0.0:
            # Sanfte Nachbarschafts-Abfrage (Radius 1 Zelle = 8m), damit Pfade neben der exakten Spur ebenfalls profitieren
            w = max(
                float(grid.get((gx + 1, gz), 0.0)),
                float(grid.get((gx - 1, gz), 0.0)),
                float(grid.get((gx, gz + 1), 0.0)),
                float(grid.get((gx, gz - 1), 0.0)),
            ) * 0.65
        return w

    def _get_bot_system_assist_data(self, p: dict) -> dict:
        """Aggregiert Live-Daten des 12-Bot-Systems (optimales Level-Jagdgebiet, gelernte Klassen-Skillrotation mit kürzester TTK,
        aktive Bot-Hotspots und Brücken-/Stadttor-Wegfindung) für die Spieler-Autojagd und Client-Wegfindung."""
        now_t = time.time()
        cached = p.get("_cachedBotSystemData")
        if isinstance(cached, dict) and (now_t - float(p.get("_cachedBotSystemDataAt", 0.0) or 0.0)) < 2.0:
            return cached

        grid = self._ensure_learned_bot_nav_grid()
        p_lvl = int(p.get("level", 1))
        p_cls = str(p.get("class_id", "warrior"))
        p_emp = str(p.get("empire", "seiryu")).lower()
        if p_emp not in ("seiryu", "kaeryu"):
            p_emp = "seiryu" if float(p.get("pos_x", 0.0)) >= 0.0 else "kaeryu"

        # 1. Idealen Level-Sektor & Anker aus dem Bot-System bestimmen (bevorzugt echte aktive Bots im passenden Levelbereich)
        ideal_x, ideal_z = self._get_ideal_bot_hunting_anchor({"empire": p_emp, "level": p_lvl})
        best_bot_anchor = None
        best_bot_lvl_diff = 999
        best_class_evo = None
        best_class_ttk = 999.0
        hotspots = []
        bots_in_same_region = 0
        target_north = p_lvl < 23

        for pid, bp in list(self.players.items()):
            if not str(pid).startswith("bot_"):
                continue
            bx = float(bp.get("pos_x", 0.0))
            bz = float(bp.get("pos_z", 0.0))
            blvl = int(bp.get("level", 1))
            bcls = str(bp.get("class_id", "warrior"))
            bemp = str(bp.get("empire", "seiryu")).lower()
            b_sec_lbl = self._get_bot_route_sector_label(bp)
            hotspots.append({
                "id": pid,
                "name": bp.get("name", pid),
                "empire": bemp,
                "classId": bcls,
                "level": blvl,
                "x": round(bx, 1),
                "z": round(bz, 1),
                "destX": round(float(bp.get("dest_x", bx)), 1),
                "destZ": round(float(bp.get("dest_z", bz)), 1),
                "sectorLabel": b_sec_lbl,
            })
            if (bz < 0.0) == target_north:
                bots_in_same_region += 1

            # Prüfe, ob dieser Bot im passenden Levelfenster (Lv. 1–22 Map 1 Nord, ab Lv. 23 Map 2 Süd) jagt
            if bemp == p_emp and not is_in_safe_zone(bp.get("map_id", "morgenwacht"), bx, bz):
                if (p_lvl >= 23 and bz > 40.0) or (p_lvl < 23 and bz < -40.0):
                    ldiff = abs(blvl - p_lvl)
                    if ldiff <= 6 and ldiff < best_bot_lvl_diff:
                        best_bot_lvl_diff = ldiff
                        af_b = bp.get("autofarm") or {}
                        ax_b = float(af_b.get("anchorX")) if af_b.get("anchorX") is not None else bx
                        az_b = float(af_b.get("anchorZ")) if af_b.get("anchorZ") is not None else bz
                        best_bot_anchor = (ax_b, az_b, bp.get("name", pid))

            # Beste gelernte Klassen-Skillrotation (Evolution v3.0/v5.0) derselben Klasse übernehmen
            if bcls == p_cls:
                evo = self._get_bot_evolution_v3_profile(bp)
                ttk = float(evo.get("bestTtkSec", 99.9) or 99.9)
                if best_class_evo is None or ttk < best_class_ttk:
                    best_class_ttk = ttk
                    best_class_evo = evo

        if best_bot_anchor is not None:
            rec_x, rec_z, ref_bot_name = best_bot_anchor
        else:
            rec_x, rec_z = ideal_x, ideal_z
            ref_bot_name = "[Bot]Veyron" if p_emp == "seiryu" else "[Bot]Kassian"

        if best_class_evo is None:
            best_class_evo = self._get_bot_evolution_v3_profile({"class_id": p_cls})

        dummy_pos = {"pos_x": rec_x, "pos_z": rec_z}
        rec_sector = self._get_bot_route_sector(dummy_pos)
        rec_sector_label = self._get_bot_route_sector_label(dummy_pos)
        bridge_label = "West-Steinbrücke (-760 • Kaeryu)" if p_emp == "kaeryu" else "Ost-Steinbrücke (+760 • Seiryu)"
        bridge_x = -760.0 if p_emp == "kaeryu" else 760.0

        cdef = CHARACTER_CLASSES.get(p_cls, CHARACTER_CLASSES["warrior"])
        skill_name_map = {sk["id"]: sk["name"] for sk in cdef.get("skills", [])}
        rot_order = list(best_class_evo.get("activeRotationOrder") or [])
        rot_skill_names = [skill_name_map.get(sid, sid) for sid in rot_order if sid in skill_name_map]

        data = {
            "enabled": bool((p.get("autofarm") or {}).get("useBotSystemData", True)),
            "recommendedAnchorX": round(float(rec_x), 1),
            "recommendedAnchorZ": round(float(rec_z), 1),
            "recommendedSector": rec_sector,
            "recommendedSectorLabel": rec_sector_label,
            "referenceBotName": ref_bot_name,
            "activeRotationName": str(best_class_evo.get("activeRotationName") or "Omni-Rissbrecher v5.0"),
            "activeRotationOrder": rot_order,
            "activeRotationSkillNames": rot_skill_names[:5],
            "bestTtkSec": round(float(best_class_evo.get("bestTtkSec", 4.2) if float(best_class_evo.get("bestTtkSec", 99.9)) < 90.0 else 4.2), 2),
            "buildName": str(best_class_evo.get("desiredBonusBuild") or ""),
            "bridgeX": bridge_x,
            "bridgeLabel": bridge_label,
            "learnedNavCells": len(grid),
            "botsInRegion": bots_in_same_region,
            "hotspots": hotspots[:12],
        }
        p["_cachedBotSystemData"] = data
        p["_cachedBotSystemDataAt"] = now_t
        return data

    def _resolve_town_gate_waypoint(self, map_id: str, cx: float, cz: float, tx: float, tz: float) -> Tuple[float, float]:
        if map_id not in ("morgenwacht", "map_1"):
            return tx, tz
        town_defs = (
            (-820.0, -780.0, 122.0, 1.0),   # Kaeryu (Osttor +1, Nordtor, Südtor)
            (820.0, -780.0, 122.0, -1.0),   # Seiryu (Westtor -1, Nordtor, Südtor)
            (0.0, 880.0, 132.0, 0.0),       # Bakra (Nord-, Süd-, West-, Osttor)
        )
        for tcx, tcz, wall_r, side_dir in town_defs:
            d_start = math.hypot(cx - tcx, cz - tcz)
            d_goal = math.hypot(tx - tcx, tz - tcz)
            start_in = d_start < wall_r - 3.5
            goal_in = d_goal < wall_r - 3.5
            start_out = d_start > wall_r + 3.5
            goal_out = d_goal > wall_r + 3.5
            if not ((start_out and goal_in) or (start_in and goal_out)):
                continue

            if side_dir != 0.0:
                gates = [
                    (tcx + side_dir * (wall_r + 18.0), tcz, tcx + side_dir * wall_r, tcz, tcx + side_dir * (wall_r - 20.0), tcz),
                    (tcx, tcz - (wall_r + 18.0), tcx, tcz - wall_r, tcx, tcz - (wall_r - 20.0)),
                    (tcx, tcz + (wall_r + 18.0), tcx, tcz + wall_r, tcx, tcz + (wall_r - 20.0)),
                ]
            else:
                gates = [
                    (tcx, 748.0 - 18.0, tcx, 748.0, tcx, 748.0 + 20.0),
                    (tcx - (wall_r + 18.0), tcz, tcx - wall_r, tcz, tcx - (wall_r - 20.0), tcz),
                    (tcx + (wall_r + 18.0), tcz, tcx + wall_r, tcz, tcx + (wall_r - 20.0), tcz),
                    (tcx, 964.0 + 18.0, tcx, 964.0, tcx, 964.0 - 20.0),
                ]

            best_gate = gates[0]
            best_score = 1e9
            for ox, oz, gx, gz, ix, iz in gates:
                ent_x, ent_z = (ox, oz) if start_out else (ix, iz)
                ext_x, ext_z = (ix, iz) if start_out else (ox, oz)
                cost = (
                    math.hypot(cx - ent_x, cz - ent_z)
                    + math.hypot(ext_x - tx, ext_z - tz)
                    - self._get_learned_bot_trail_weight(gx, gz) * 0.6
                )
                if cost < best_score:
                    best_score = cost
                    best_gate = (ox, oz, gx, gz, ix, iz)

            ox, oz, gx, gz, ix, iz = best_gate
            ent_x, ent_z = (ox, oz) if start_out else (ix, iz)
            ext_x, ext_z = (ix, iz) if start_out else (ox, oz)
            if math.hypot(cx - gx, cz - gz) > 16.0 and math.hypot(cx - ent_x, cz - ent_z) > 6.5:
                return ent_x, ent_z
            return ext_x, ext_z
        return tx, tz

    def _move_player_towards(self, p: dict, tx: float, tz: float, dt: float) -> float:
        """Bewegt den Charakter serverseitig zum Zielpunkt unter Nutzung gelernter Bot-Pfade,
        Stadttor-Wegfindung (Kaeryu, Seiryu, Bakra) und Brücken-Navigation."""
        self._ensure_learned_bot_nav_grid()
        cx, cz = float(p["pos_x"]), float(p["pos_z"])
        now_t = time.time()
        cached_goal = p.get("_cachedGateGoal")
        cached_wp = p.get("_cachedGateWp")
        if (
            cached_goal
            and cached_wp
            and (now_t - float(p.get("_cachedGateAt", 0.0) or 0.0)) < 0.35
            and abs(float(tx) - cached_goal[0]) < 2.0
            and abs(float(tz) - cached_goal[1]) < 2.0
            and math.hypot(cx - cached_wp[0], cz - cached_wp[1]) > 5.0
        ):
            eff_tx, eff_tz = cached_wp
        else:
            eff_tx, eff_tz = self._resolve_town_gate_waypoint(p.get("map_id", "morgenwacht"), cx, cz, float(tx), float(tz))
            p["_cachedGateGoal"] = (float(tx), float(tz))
            p["_cachedGateWp"] = (eff_tx, eff_tz)
            p["_cachedGateAt"] = now_t

        is_bot = str(p.get("player_id", "")).startswith("bot_")
        af_cfg = p.get("autofarm") or {}
        use_bot_nav = is_bot or bool(af_cfg.get("useBotSystemData", True))

        if p.get("map_id") in ("morgenwacht", "map_1"):
            crossing_north_to_south = (cz < -30.0 and eff_tz > 30.0) or (-30.0 <= cz <= 30.0 and eff_tz > 30.0)
            crossing_south_to_north = (cz > 30.0 and eff_tz < -30.0) or (-30.0 <= cz <= 30.0 and eff_tz < -30.0)
            if crossing_north_to_south or crossing_south_to_north:
                # Wähle die passende der 2 äußeren Steinbrücken (-760.0 West / Kaeryu oder +760.0 Ost / Seiryu)
                # unter Berücksichtigung der gelernten Bot-Spurgewichte
                cost_west = abs(cx - (-760.0)) + abs(eff_tx - (-760.0)) - self._get_learned_bot_trail_weight(-760.0, 0.0) * 0.8
                cost_east = abs(cx - 760.0) + abs(eff_tx - 760.0) - self._get_learned_bot_trail_weight(760.0, 0.0) * 0.8
                if abs(cost_west - cost_east) <= 120.0:
                    prefer_west = p.get("empire") == "kaeryu" or (cx + eff_tx) * 0.5 < 0.0
                else:
                    prefer_west = cost_west < cost_east
                bridge_x = -760.0 if prefer_west else 760.0
                bridge_label = "West-Steinbrücke (Kaeryu)" if bridge_x < 0 else "Ost-Steinbrücke (Seiryu)"

                if abs(cx - bridge_x) > 14.0 and abs(cz) > 28.0:
                    # 1. Etappe: Zum Brückenkopf auf dem aktuellen Flussufer reiten
                    eff_tx = bridge_x
                    eff_tz = -46.0 if cz < 0.0 else 46.0
                else:
                    # 2. Etappe: Direkt über die Steinbrücke ans andere Ufer laufen
                    eff_tx = bridge_x
                    eff_tz = 54.0 if tz > 0.0 else -54.0

                if is_bot or (use_bot_nav and af_cfg.get("enabled")):
                    if not p.get("active_mount") and now_t >= float(p.get("_manualDismountUntil", 0.0) or 0.0):
                        p["active_mount"] = af_cfg.get("mountId") or "mount_war_boar"
                        self.compute_player_combat_stats(p)
                    dir_label = "Map 1 Nord → Map 2 Süd" if tz > 0.0 else "Map 2 Süd → Map 1 Nord"
                    p["autoFarmStatus"] = f"🌉 Bot-Route: Überquere {bridge_label} ({dir_label})"

        # Intelligente Hindernis-Umgehung (Haeuser, Mauern, Felsen, Baeume) + gelerntes Navigations-Gedaechtnis
        nav_map_id = p.get("map_id", "morgenwacht")
        use_obstacle_nav = is_bot or bool(af_cfg.get("enabled"))
        if use_obstacle_nav:
            eff_tx, eff_tz = self.nav.next_waypoint(p, nav_map_id, cx, cz, eff_tx, eff_tz, now_t)

        dx = eff_tx - cx
        dz = eff_tz - cz
        d = math.hypot(dx, dz)
        if d < 0.25:
            p["vx"] = 0.0
            p["vz"] = 0.0
            p["dest_x"] = cx
            p["dest_z"] = cz
            return dist2d(cx, cz, tx, tz)

        speed = max(8.5, float(p.get("computed", {}).get("speed", 8.5)))
        step = min(d, speed * dt)
        chosen_ang = math.atan2(dx, dz)

        dir_x = math.sin(chosen_ang)
        dir_z = math.cos(chosen_ang)
        nx = max(-1360.0, min(1360.0, cx + dir_x * step))
        nz = max(-1360.0, min(1360.0, cz + dir_z * step))
        if use_obstacle_nav:
            nx, nz, nav_hit = self.nav.resolve_step(nav_map_id, cx, cz, nx, nz)
            p["rot_y"] = chosen_ang
            self.nav.report_progress(p, nav_map_id, cx, cz, nx, nz, step, dt, nav_hit)

        last_tx = float(p.get("_lastTrailRecX", -9999.0))
        last_tz = float(p.get("_lastTrailRecZ", -9999.0))
        if math.hypot(nx - last_tx, nz - last_tz) >= 4.0:
            p["_lastTrailRecX"] = nx
            p["_lastTrailRecZ"] = nz
            self._record_learned_bot_trail(nx, nz, 1.5 if is_bot else 0.6)

        # Zähle erfolgreiche Fluss-/Brückenüberquerungen zwischen Map 1 (Nord) und Map 2 (Süd)
        if (cz < 0.0 <= nz or cz > 0.0 >= nz) and any(abs(nx - bx) <= 24.0 for bx in (-760.0, 760.0)):
            p["bridgeCrossings"] = int(p.get("bridgeCrossings", 0)) + 1

        p["pos_x"] = nx
        p["pos_z"] = nz
        p["rot_y"] = chosen_ang
        p["moveSpeed"] = speed
        p["dest_x"] = eff_tx
        p["dest_z"] = eff_tz
        p["lastAutoMoveTime"] = now_t

        final_d = dist2d(nx, nz, tx, tz)
        if final_d < 0.45:
            p["vx"] = 0.0
            p["vz"] = 0.0
            if p.get("moveTarget"):
                p["moveTarget"] = None
        else:
            p["vx"] = dir_x * speed
            p["vz"] = dir_z * speed
        return final_d

    def _tick_player_target_attack(self, p: dict, dt: float, now: float, allow_move: bool = True):
        """Linksklick auf Monster oder Rissmonolith (wie in Projekt 1 InfinityWarCharacter.cpp):
        Spieler läuft automatisch bis auf Schlagdistanz heran und greift fortlaufend an, bis das Ziel besiegt ist
        oder durch manuelle Bewegung (WASD / Bodenklick) abgebrochen wird."""
        tid = p.get("autoAttackTargetId")
        mob = self.monsters.get(tid) if tid else None
        if not mob or mob["mapId"] != p["map_id"] or mob["state"] == "dead":
            p["autoAttackTargetId"] = None
            return

        p["targetId"] = mob["id"]
        d = dist2d(p["pos_x"], p["pos_z"], mob["x"], mob["z"])
        atk_range = p["computed"]["attackRange"] + (2.2 if mob["kind"] == "metin" else 0.6)

        if d > atk_range:
            if allow_move:
                self._move_player_towards(p, mob["x"], mob["z"], dt)
        else:
            p["rot_y"] = math.atan2(mob["x"] - p["pos_x"], mob["z"] - p["pos_z"])
            atk_interval = 0.62 / max(0.80, min(1.45, p["computed"]["atkSpeed"]))
            if now - p.get("lastBasicAttack", 0.0) >= atk_interval:
                self.perform_basic_attack(p["player_id"], mob["id"])

    # ========================================================================
    # 6. DROP-FILTER-SYSTEM & INTELLIGENTES AUTO-FARMING (Kap. 6 & Projekt 1)
    # ========================================================================
    def evaluate_drop_filter(self, p: dict, drop: dict) -> Tuple[bool, bool]:
        """Prüft einen Boden-Drop gegen das konfigurierte Auto-Pick-Up Drop-Filter-System des Spielers.
        Gibt (soll_aufheben, soll_auto_verkaufen) zurück."""
        af = p.get("autofarm", {})
        df = af.get("dropFilter") or DEFAULT_DROP_FILTER
        cats = df.get("categories") or DEFAULT_DROP_FILTER["categories"]

        cat_key = drop.get("category") or get_drop_filter_category(drop.get("templateId", ""))
        is_equip = cat_key in ("weapons", "armors", "jewelry")

        # 1. Kategorie-Prüfung
        cat_allowed = bool(cats.get(cat_key, True))

        # 2. Mindest-Seltenheit (alle Kategorien außer geschützte Quest-/Spezial-Bücher, sofern nicht explizit abgewählt)
        drop_rarity = drop.get("rarity", "common")
        min_rarity = df.get("minRarity", "common")
        rarity_ok = RARITY_ORDER.get(drop_rarity, 0) >= RARITY_ORDER.get(min_rarity, 0)

        # 3. Mindest-Plus-Stufe (gilt gezielt für Ausrüstung: Waffen, Rüstungen, Schmuck)
        min_plus = int(df.get("minPlusLevel", 0))
        plus_ok = True
        if is_equip and min_plus > 0:
            plus_ok = int(drop.get("plusLevel", 0)) >= min_plus

        matches = cat_allowed and rarity_ok and plus_ok
        if matches:
            return True, False

        # Falls Ausrüstung ausgefiltert wurde, aber 'Auto-Verkauf für ausgefilterte Ausrüstung' aktiv ist:
        if is_equip and bool(df.get("autoSellFiltered", False)):
            return True, True

        return False, False

    def are_players_in_same_party(
        self, player_a_id: str, player_b_id: str, fallback_party_id: Optional[str] = None
    ) -> bool:
        """Prüft, ob zwei Spieler in derselben Gruppe (Party) sind."""
        if not player_a_id or not player_b_id:
            return False
        if player_a_id == player_b_id:
            return True
        pa = self.players.get(player_a_id)
        pb = self.players.get(player_b_id)
        party_id_a = pa.get("partyId") if pa else None
        party_id_b = pb.get("partyId") if pb else fallback_party_id
        if party_id_a and party_id_a in self.parties:
            party = self.parties[party_id_a]
            members = party.get("memberIds", [])
            if player_a_id in members and (player_b_id in members or (party_id_b and party_id_a == party_id_b)):
                return True
        return False

    def can_player_pickup_drop(
        self, player_id: str, dr: dict, now: Optional[float] = None, is_auto: bool = False
    ) -> Tuple[bool, float]:
        """Prüft, ob ein Spieler einen Boden-Drop aufheben darf:
        - Erste 60s nach dem Drop: Nur der Besitzer (ownerId) und seine Gruppenmitglieder dürfen den Loot aufheben.
        - Danach weitere 60s (60s–120s): Für alle anderen Spieler frei zugänglich, bevor der Drop nach 120s verschwindet."""
        if now is None:
            now = time.time()
        owner_id = dr.get("ownerId")
        if is_auto and owner_id == player_id and float(dr.get("selfAutoPickupLockUntil", 0.0)) > now:
            return False, float(dr.get("selfAutoPickupLockUntil", 0.0)) - now
        if not owner_id or owner_id == player_id:
            return True, 0.0
        if self.are_players_in_same_party(player_id, owner_id, dr.get("ownerPartyId")):
            return True, 0.0
        protected_until = float(dr.get("ownerProtectedUntil", float(dr.get("createdAt", 0.0)) + 60.0))
        rem = protected_until - now
        if rem > 0.0:
            return False, rem
        return True, 0.0

    def _tick_passive_auto_pickup(self, p: dict, now: float):
        """Passiver Auto-Pick-Up Magnet (wie in Projekt 1 ExecuteAutoPickup):
        Sammelt alle 0.35s automatisch gefilterte Drops im Umkreis von 5.8m ein, auch beim manuellen Laufen/Kämpfen."""
        if now - p.get("lastPassiveLootScan", 0.0) < 0.35:
            return
        p["lastPassiveLootScan"] = now

        for dr in list(self.drops.values()):
            if dr["mapId"] != p["map_id"]:
                continue
            if dist2d(p["pos_x"], p["pos_z"], dr["x"], dr["z"]) > 5.8:
                continue
            can_pick, _ = self.can_player_pickup_drop(p["player_id"], dr, now=now, is_auto=True)
            if not can_pick:
                continue
            should_pick, should_sell = self.evaluate_drop_filter(p, dr)
            if not should_pick:
                continue
            self.pickup_drop(p["player_id"], dr["id"], auto_sell=should_sell)
            break  # 1 Drop pro Scan-Intervall (350ms) für flüssiges Echtzeit-Feedback

    def _tick_pet_active_skills(self, p: dict, now: float):
        """Führt die 3 aktiven Pet-Skills (Stufe 1-5) des aktiven Begleiters aus:
        1. Auto-Pickup (Chance 20%-100%, CD 5s)
        2. Erneuerung (Chance 10%-50% bei TP < 20% -> +50% TP, CD 90s, nicht für PvP)
        3. Heilung (Chance 10%-50% Verlangsamung, Vergiftung, Blutung zu entfernen, CD 30s)
        """
        if not p.get("active_pet") or p.get("isDead") or float(p.get("hp", 1)) <= 0:
            return
        pet_data = self._ensure_player_pet_data(p)
        p_skills = pet_data.get("skills", {})
        cds = pet_data.setdefault("cooldowns", {})

        # 1. Auto-Pickup (Level 1-5: 20%-100% Chance, 5s Cooldown)
        pickup_lv = int(p_skills.get("auto_pickup", 0) or 0)
        if pickup_lv > 0 and float(cds.get("auto_pickup", 0.0)) <= 0.0:
            if now - float(p.get("_lastPetPickupScan", 0.0)) >= 0.5:
                p["_lastPetPickupScan"] = now
                for dr in list(self.drops.values()):
                    if dr["mapId"] != p["map_id"]:
                        continue
                    if dist2d(p["pos_x"], p["pos_z"], dr["x"], dr["z"]) > 7.5:
                        continue
                    can_pick, _ = self.can_player_pickup_drop(p["player_id"], dr, now=now, is_auto=True)
                    if not can_pick:
                        continue
                    should_pick, should_sell = self.evaluate_drop_filter(p, dr)
                    if not should_pick:
                        continue
                    chance = min(100.0, pickup_lv * 20.0)
                    if random.uniform(0.0, 100.0) <= chance:
                        res = self.pickup_drop(p["player_id"], dr["id"], auto_sell=should_sell)
                        ok = res[0] if isinstance(res, tuple) else bool(res and res.get("ok"))
                        if ok:
                            cds["auto_pickup"] = 5.0
                    break

        # 2. Erneuerung (Level 1-5: 10%-50% Chance wenn TP < 20%, +50% TP, 90s Cooldown)
        if 0 < float(p["hp"]) <= float(p["max_hp"]) * 0.20:
            self._try_proc_pet_renewal(p, now)

        # 3. Heilung (Level 1-5: 10%-50% Chance Slow/Poison/Bleed zu entfernen, 30s Cooldown)
        heal_lv = int(p_skills.get("heilung", 0) or 0)
        if heal_lv > 0 and float(cds.get("heilung", 0.0)) <= 0.0:
            debuffs = p.get("activeDebuffs", {})
            has_cleansable = any(k in debuffs for k in ("slow", "poison", "bleed"))
            if has_cleansable:
                chance = min(50.0, heal_lv * 10.0)
                if random.uniform(0.0, 100.0) <= chance:
                    for k in ("slow", "poison", "bleed"):
                        debuffs.pop(k, None)
                    cds["heilung"] = 30.0
                    self._emit_combat_event(
                        p["map_id"],
                        "combat_feedback",
                        p["pos_x"],
                        p["pos_z"],
                        {
                            "playerId": p["player_id"],
                            "feedbackType": "heal",
                            "text": "🌿 PET-HEILUNG (Gereinigt!)",
                            "color": "#4ade80",
                        },
                    )
                else:
                    cds["heilung"] = 1.0

    def _try_proc_pet_renewal(self, p: dict, now: float) -> bool:
        """Erneuerung (Aktiv Lv. 1-5): Wenn TP unter 20% fällt, 10%-50% Chance +50% Max-TP wiederherzustellen (90s CD, nur PvM)."""
        if not p.get("active_pet") or p.get("isDead") or float(p.get("hp", 0)) <= 0:
            return False
        if float(p["hp"]) > float(p["max_hp"]) * 0.20:
            return False
        pet_data = self._ensure_player_pet_data(p)
        ren_lv = int(pet_data.get("skills", {}).get("erneuerung", 0) or 0)
        if ren_lv <= 0:
            return False
        cds = pet_data.setdefault("cooldowns", {})
        if float(cds.get("erneuerung", 0.0)) > 0.0:
            return False
        chance = min(50.0, ren_lv * 10.0)
        if random.uniform(0.0, 100.0) > chance:
            return False
        heal_amt = int(round(p["max_hp"] * 0.50))
        p["hp"] = min(p["max_hp"], int(p["hp"]) + heal_amt)
        cds["erneuerung"] = 90.0
        self._emit_combat_event(
            p["map_id"],
            "combat_feedback",
            p["pos_x"],
            p["pos_z"],
            {
                "playerId": p["player_id"],
                "feedbackType": "heal",
                "text": f"🐉 PET-ERNEUERUNG (+{heal_amt} TP!)",
                "color": "#fde047",
            },
        )
        return True

    def _award_pet_exp(self, p: dict, base_exp: int):
        """Vergibt Pet-EXP bei Monster-/Metin-/Boss-Kills, solange der Begleiter aktiv gerufen ist."""
        if not p.get("active_pet") or base_exp <= 0:
            return
        pet_data = self._ensure_player_pet_data(p)
        if int(pet_data["level"]) >= MAX_PET_LEVEL:
            return
        exp_rush_lv = int(pet_data.get("skills", {}).get("erfahrungsrausch", 0) or 0)
        rush_mult = 1.0 + (exp_rush_lv * 10.0) / 100.0
        gained = max(1, int(round(base_exp * rush_mult)))
        pet_data["exp"] = int(pet_data.get("exp", 0)) + gained
        leveled = False
        while int(pet_data["level"]) < MAX_PET_LEVEL and int(pet_data["exp"]) >= int(pet_data["maxExp"]):
            pet_data["exp"] -= int(pet_data["maxExp"])
            pet_data["level"] = int(pet_data["level"]) + 1
            pet_data["skillPoints"] = int(pet_data.get("skillPoints", 0)) + 1
            pet_data["statPoints"] = int(pet_data.get("statPoints", 0)) + 2
            pet_data["maxExp"] = get_required_pet_exp(pet_data["level"])
            leveled = True
        if int(pet_data["level"]) >= MAX_PET_LEVEL:
            pet_data["exp"] = min(int(pet_data["exp"]), int(pet_data["maxExp"]))
        if leveled:
            if str(p.get("player_id", "") or "").startswith("bot_"):
                self._auto_maintain_bot_pet(p)
            else:
                self.compute_player_combat_stats(p)
                self.add_chat_message(
                    "Begleiter",
                    f"🐉 Dein Begleiter '{pet_data['customName']}' hat Stufe {pet_data['level']} erreicht! (+1 Skillpunkt, +2 Statuspunkte)",
                    channel="system",
                    target_player_id=p.get("player_id"),
                )

    @staticmethod
    def ensure_autofarm_stats(af: dict) -> dict:
        stats = af.get("stats")
        if not isinstance(stats, dict):
            stats = {}
            af["stats"] = stats
        stats.setdefault("activeSeconds", 0.0)
        stats.setdefault("afkExcludedSeconds", 0.0)
        stats.setdefault("monstersKilled", 0)
        stats.setdefault("metinsDestroyed", 0)
        stats.setdefault("bossesSlain", 0)
        stats.setdefault("dungeonRuns", 0)
        stats.setdefault("fishCaught", 0)
        stats.setdefault("oresMined", 0)
        stats.setdefault("yangEarned", 0)
        stats.setdefault("expEarned", 0)
        stats.setdefault("dropsLooted", 0)
        stats.setdefault("monolithsAwakened", 0)
        stats.setdefault("monolithsMadeUnstable", 0)
        stats.setdefault("worldBossesSummoned", 0)
        stats.setdefault("worldBossCoopFights", 0)
        stats.setdefault("potionsUsed", 0)
        stats.setdefault("potionsAutoBought", 0)
        stats.setdefault("yangSpentOnPotions", 0)
        return stats

    def _is_bot_fighting_monolith_or_boss(self, bot: dict) -> bool:
        """Prüft, ob ein Bot gerade aktiv einen Rissmonolithen, Elite-Boss, Kartenboss oder Gebiets-Weltboss bekämpft,
        damit Routen-/Sektor-/Gruppen-Logik den Bot NICHT vor dem Kill wegzieht oder wegteleportiert."""
        if not bot or bot.get("isDead"):
            return False
        bx, bz = float(bot.get("pos_x", 0.0)), float(bot.get("pos_z", 0.0))
        b_map = bot.get("map_id", "morgenwacht")
        for tid_k in ("manualFocusTargetId", "autoFarmTargetId", "targetId"):
            tid = bot.get(tid_k)
            if tid and tid in self.monsters:
                tm = self.monsters[tid]
                if tm.get("state") != "dead" and int(tm.get("hp", 0)) > 0 and tm.get("mapId") == b_map:
                    if (
                        tm.get("kind") == "metin"
                        or tm.get("isBoss")
                        or tm.get("isMapBossSlot")
                        or tm.get("isRiftWorldBoss")
                        or tm.get("isMonolithEliteBoss")
                        or tm.get("monolithGuardOf")
                    ):
                        if dist2d(bx, bz, float(tm["x"]), float(tm["z"])) <= 65.0:
                            return True
        for m in self.monsters.values():
            if m.get("mapId") != b_map or m.get("state") == "dead" or int(m.get("hp", 0)) <= 0:
                continue
            if (
                (m.get("kind") == "metin" and (m.get("monolithState") in ("instabil", "erwacht") or int(m.get("hp", 0)) < int(m.get("maxHp", 1))))
                or m.get("isRiftWorldBoss")
                or m.get("isMonolithEliteBoss")
                or (m.get("isMapBossSlot") and int(m.get("hp", 0)) < int(m.get("maxHp", 1)))
            ):
                if dist2d(bx, bz, float(m["x"]), float(m["z"])) <= 42.0:
                    return True
        return False

    def _evaluate_bot_monolith_strength(self, bot: dict, mob: dict, target_stage: str) -> Tuple[bool, List[dict]]:
        """Prüft, ob ein Bot (allein oder gemeinsam mit nahen verbündeten Bots desselben Reichs)
        stark genug ist und das passende Inventar-Item besitzt, um einen Rissmonolithen:
        - in den instabilen Zustand ('instabil') zu bringen (verbraucht 1x 'mat_monolith_shard')
        - oder zum Erwachen ('erwacht' + Gebiets-Weltboss) zu bringen (verbraucht 1x 'mat_awakened_rift_core')."""
        if not bot or not mob or mob.get("kind") != "metin" or mob.get("state") == "dead":
            return False, []
        pid = str(bot.get("player_id", ""))
        if not pid.startswith("bot_") or bot.get("isDead"):
            return False, []

        inv = bot.get("inventory") or []
        req_tpl = "mat_monolith_shard" if target_stage == "instabil" else "mat_awakened_rift_core"
        has_req_item = any(
            isinstance(it, dict)
            and it.get("templateId") == req_tpl
            and not it.get("reservedShopId")
            and not it.get("reserved_shop_id")
            and int(it.get("quantity", 1) or 1) >= 1
            for it in inv
        )
        if not has_req_item:
            return False, []

        map_id = mob.get("mapId", "morgenwacht")
        mx, mz = float(mob["x"]), float(mob["z"])
        bot_lvl = int(bot.get("level", 1))
        mob_lvl = int(mob.get("level", 5))
        b_emp = str(bot.get("empire", "seiryu")).lower()

        # Niemals einen Monolithen außerhalb des eigenen Level-/Reichs-Korridors erwecken,
        # damit der Bot den Monolithen garantiert bis 0 TP zu Ende bekämpfen kann!
        if bot_lvl >= 18 and mz < 20.0:
            return False, []
        if bot_lvl < 18 and mz > -20.0:
            return False, []
        if b_emp == "seiryu" and mx < -225.0:
            return False, []
        if b_emp == "kaeryu" and mx > 225.0:
            return False, []

        if target_stage == "erwacht":
            if (
                self._get_active_world_boss(map_id) is not None
                or self._get_active_erwacht_monolith(map_id, exclude_mob_id=mob["id"]) is not None
                or self._get_world_boss_cooldown_remaining(map_id) > 0.0
            ):
                return False, []
        else:
            # Stufe 2 ('instabil'): Niemals neue Monolithen instabil machen, solange bereits ein instabiler/erwachter Monolith
            # oder Elite-Boss in der Nähe (<= 320m) lebt oder bereits >= 2 instabile Monolithen auf der Karte aktiv sind!
            active_instabil_total = 0
            for om in self.monsters.values():
                if om["id"] == mob["id"] or om.get("mapId") != map_id or om.get("state") == "dead" or int(om.get("hp", 0)) <= 0:
                    continue
                if om.get("kind") == "metin" and om.get("monolithState") in ("instabil", "erwacht"):
                    active_instabil_total += 1
                    if dist2d(mx, mz, float(om["x"]), float(om["z"])) <= 320.0:
                        return False, []
                elif om.get("isMonolithEliteBoss") or om.get("isRiftWorldBoss"):
                    if dist2d(mx, mz, float(om["x"]), float(om["z"])) <= 260.0:
                        return False, []
            if active_instabil_total >= 2:
                return False, []

        hp_pct = (float(bot.get("hp", 1)) / max(1.0, float(bot.get("max_hp", 1)))) * 100.0
        min_hp = 58.0 if target_stage == "instabil" else 64.0
        if hp_pct < min_hp:
            return False, []

        comp = bot.get("computed") or {}
        weapon_plus = int(comp.get("weaponPlus", 0))

        allied_bots: List[dict] = []
        scan_rad = 155.0 if target_stage == "instabil" else 235.0
        for op_id, op in self.players.items():
            if op_id == pid or not str(op_id).startswith("bot_"):
                continue
            if not op.get("online") or not op.get("inWorld") or op.get("isDead") or op.get("map_id") != mob.get("mapId"):
                continue
            if str(op.get("empire", "seiryu")).lower() != b_emp:
                continue
            op_hp_pct = (float(op.get("hp", 1)) / max(1.0, float(op.get("max_hp", 1)))) * 100.0
            if op_hp_pct < 48.0:
                continue
            d_ally = dist2d(float(op["pos_x"]), float(op["pos_z"]), float(mob["x"]), float(mob["z"]))
            if d_ally <= scan_rad and int(op.get("level", 1)) >= mob_lvl - 8:
                allied_bots.append(op)

        max_group_lvl = max([bot_lvl] + [int(ab.get("level", 1)) for ab in allied_bots])
        if target_stage == "instabil":
            solo_strong = (bot_lvl >= mob_lvl - 1) or (bot_lvl >= mob_lvl - 3 and weapon_plus >= 4)
            group_strong = len(allied_bots) >= 1 and max_group_lvl >= mob_lvl - 3
            return (solo_strong or group_strong), allied_bots
        else:
            # Für Stufe 3 (Erwacht + Gebiets-Weltboss): Entweder Verbündete in der Nähe bereit zum gemeinsamen Kampf oder hoher eigener Level/Ausrüstungsstand
            group_strong = len(allied_bots) >= 1 and max_group_lvl >= mob_lvl - 3
            solo_strong = (bot_lvl >= mob_lvl + 1) or (bot_lvl >= mob_lvl - 1 and weapon_plus >= 5)
            return (group_strong or solo_strong), allied_bots

    def _rally_nearby_bots_for_monolith_or_world_boss(
        self,
        target_mob: dict,
        initiator_bot: Optional[dict] = None,
        now: Optional[float] = None,
        already_rallied_ids: Optional[set] = None,
    ) -> List[dict]:
        """Ruft alle geeigneten Bots in der Nähe zusammen, um gemeinsam den Gebiets-Weltboss,
        die Elite-Bosse oder einen instabilen/erwachten Rissmonolithen zu bekämpfen."""
        if not target_mob or target_mob.get("state") == "dead" or int(target_mob.get("hp", 0)) <= 0:
            return []
        now_t = now if now is not None else time.time()
        map_id = target_mob.get("mapId", "morgenwacht")

        # Falls das Ziel ein Erwachter Monolith ist und sein beschworener Weltboss lebt, fokussiere zuerst den Weltboss (wegen Riss-Bollwerk!)
        focus_mob = target_mob
        if target_mob.get("kind") == "metin" and target_mob.get("monolithState") == "erwacht":
            wb_id = target_mob.get("activeWorldBossId")
            wb_mob = self.monsters.get(wb_id) if wb_id else self._get_active_world_boss(map_id)
            if wb_mob and wb_mob.get("state") != "dead" and int(wb_mob.get("hp", 0)) > 0:
                focus_mob = wb_mob

        is_wb = bool(focus_mob.get("isRiftWorldBoss"))
        is_elite_b = bool(focus_mob.get("isMonolithEliteBoss"))
        is_map_b = bool(focus_mob.get("isMapBossSlot") or (focus_mob.get("isBoss") and not is_wb and not is_elite_b))
        rally_radius = 310.0 if is_wb else (225.0 if (is_elite_b or is_map_b or focus_mob.get("monolithState") == "erwacht") else 185.0)
        mob_lvl = int(focus_mob.get("level", 5))
        mx, mz = float(focus_mob["x"]), float(focus_mob["z"])

        rallied_bots: List[dict] = []
        bots_by_empire: Dict[str, List[dict]] = {"seiryu": [], "kaeryu": []}

        for pid, bp in list(self.players.items()):
            if not str(pid).startswith("bot_") or not bp.get("online") or not bp.get("inWorld") or bp.get("isDead"):
                continue
            if already_rallied_ids is not None and pid in already_rallied_ids:
                continue
            if bp.get("map_id") != map_id:
                continue
            # Bots, die bereits in einer Gruppe mit einem echten menschlichen Spieler sind, folgen weiter dem Spieler
            pty_cur = self.parties.get(bp.get("partyId")) if bp.get("partyId") else None
            if pty_cur and any(not str(mid).startswith("bot_") for mid in pty_cur.get("memberIds", [])):
                continue

            # Wenn der Bot bereits unmittelbar (< 42m) an einem ANDEREN instabilen/erwachten Monolithen oder Boss kämpft,
            # ziehe ihn NICHT weg, bis sein aktueller Monolith zerstört ist!
            if bp is not initiator_bot:
                cur_tid = bp.get("manualFocusTargetId") or bp.get("autoFarmTargetId") or bp.get("targetId")
                cur_tm = self.monsters.get(cur_tid) if cur_tid else None
                if (
                    cur_tm
                    and cur_tm["id"] not in (focus_mob["id"], target_mob["id"])
                    and cur_tm.get("monolithGuardOf") not in (focus_mob["id"], target_mob["id"])
                    and cur_tm.get("state") != "dead"
                    and int(cur_tm.get("hp", 0)) > 0
                    and (
                        (cur_tm.get("kind") == "metin" and cur_tm.get("monolithState") in ("instabil", "erwacht"))
                        or cur_tm.get("isMonolithEliteBoss")
                        or cur_tm.get("isRiftWorldBoss")
                    )
                    and dist2d(float(bp["pos_x"]), float(bp["pos_z"]), float(cur_tm["x"]), float(cur_tm["z"])) <= 45.0
                ):
                    continue

            hp_pct = (float(bp.get("hp", 1)) / max(1.0, float(bp.get("max_hp", 1)))) * 100.0
            if hp_pct < 42.0:
                continue
            b_lvl = int(bp.get("level", 1))
            if b_lvl < mob_lvl - 10:
                continue
            # Level < 13 bleibt in Map 1 Nord (z < 0); Level >= 18 bleibt in Map 2 Süd (z > 0)
            if b_lvl < 13 and mz > 10.0:
                continue
            if b_lvl >= 18 and mz < 0.0:
                continue

            b_emp = str(bp.get("empire", "seiryu")).lower()
            # Reichs-Korridor beachten (Seiryu nicht tief im Kaeryu-Heimatland x < -230, Kaeryu nicht tief im Seiryu-Heimatland x > 230)
            if b_emp == "seiryu" and mx < -230.0:
                continue
            if b_emp == "kaeryu" and mx > 230.0:
                continue

            d_mob = dist2d(float(bp["pos_x"]), float(bp["pos_z"]), mx, mz)
            same_ns_region = (float(bp["pos_z"]) < -20.0) == (mz < -20.0)
            if not same_ns_region:
                continue
            if d_mob > rally_radius and not (is_wb and same_ns_region and d_mob <= 380.0):
                continue

            rallied_bots.append(bp)
            if already_rallied_ids is not None:
                already_rallied_ids.add(pid)
            bots_by_empire.setdefault(b_emp, []).append(bp)

        # Bilde pro Reich eine koordinierte Weltboss-/Monolith-Jagdgruppe aus den nahen Bots (bis zu 5 Bots pro Gruppe)
        for emp_k, emp_bots in bots_by_empire.items():
            if len(emp_bots) >= 2:
                emp_bots.sort(key=lambda b: (-int(b.get("level", 1)), dist2d(float(b["pos_x"]), float(b["pos_z"]), mx, mz)))
                existing_pty = None
                for eb in emp_bots:
                    p_obj = self.parties.get(eb.get("partyId")) if eb.get("partyId") else None
                    if p_obj and len(p_obj.get("memberIds", [])) < 6:
                        existing_pty = p_obj
                        break
                if not existing_pty:
                    leader_b = initiator_bot if (initiator_bot in emp_bots) else emp_bots[0]
                    pty_id = f"pty_wb_{emp_k}_{int(now_t * 10) % 100000}_{leader_b['player_id'][-4:]}"
                    existing_pty = {
                        "id": pty_id,
                        "leaderId": leader_b["player_id"],
                        "memberIds": [leader_b["player_id"]],
                        "createdAt": now_t,
                        "routeSector": self._get_bot_route_sector(leader_b),
                        "monstersSlainTogether": 0,
                        "maxMonstersTogether": 18,
                        "avgFriendship": 85,
                        "isWorldBossRaid": True,
                    }
                    self.parties[pty_id] = existing_pty
                    leader_b["partyId"] = pty_id
                else:
                    existing_pty["isWorldBossRaid"] = True
                    existing_pty["maxMonstersTogether"] = max(18, int(existing_pty.get("maxMonstersTogether", 14)))

                for eb in emp_bots:
                    if eb["player_id"] not in existing_pty["memberIds"] and len(existing_pty["memberIds"]) < 5:
                        old_pid = eb.get("partyId")
                        if old_pid and old_pid != existing_pty["id"] and old_pid in self.parties:
                            old_p = self.parties[old_pid]
                            if eb["player_id"] in old_p.get("memberIds", []):
                                old_p["memberIds"].remove(eb["player_id"])
                        existing_pty["memberIds"].append(eb["player_id"])
                        eb["partyId"] = existing_pty["id"]

        total_rallied = len(rallied_bots)
        hp_ratio_pct = max(1, int(round((float(focus_mob.get("hp", 1)) / max(1.0, float(focus_mob.get("maxHp", 1)))) * 100)))
        for idx_r, rb in enumerate(rallied_bots):
            rb["targetId"] = focus_mob["id"]
            rb["autoFarmTargetId"] = focus_mob["id"]
            rb["manualFocusTargetId"] = focus_mob["id"]
            focus_mob.setdefault("participants", set()).add(rb["player_id"])
            af_rb = rb.setdefault("autofarm", {})
            ang_r = idx_r * 1.15
            af_rb["anchorX"] = mx + math.cos(ang_r) * 3.2
            af_rb["anchorZ"] = mz + math.sin(ang_r) * 3.2
            st_rb = self.ensure_autofarm_stats(af_rb)
            if now_t - float(rb.get("_lastWbCoopCountedAt", 0.0) or 0.0) >= 25.0:
                rb["_lastWbCoopCountedAt"] = now_t
                rb["worldBossCoopAssists"] = int(rb.get("worldBossCoopAssists", 0)) + 1
                st_rb["worldBossCoopFights"] = int(st_rb.get("worldBossCoopFights", 0)) + 1

            d_rb = dist2d(float(rb["pos_x"]), float(rb["pos_z"]), mx, mz)
            if d_rb > 26.0 and not rb.get("active_mount"):
                rb["active_mount"] = af_rb.get("mountId") or (
                    "mount_crystal_wolf"
                    if ("mounted" in str(rb.get("player_id", "")) or "donnerkeil" in str(rb.get("player_id", "")))
                    else "mount_war_boar"
                )
                self.compute_player_combat_stats(rb)

            if rb is not initiator_bot or now_t >= float(rb.get("_botTradeStatusUntil", 0.0) or 0.0):
                if is_wb:
                    rb["autoFarmStatus"] = (
                        f"👑 Gemeinsame Weltboss-Jagd ({total_rallied} Bots): Bekämpfe {focus_mob['name']} ({hp_ratio_pct}% TP)!"
                        if d_rb <= 16.0
                        else f"🐎👑 Weltboss-Alarm ({total_rallied} Bots): Reite zu {focus_mob['name']} ({int(d_rb)}m)!"
                    )
                elif is_map_b or is_elite_b:
                    b_lbl = "Gebietsboss-Jagd" if is_map_b else "Elite-Boss-Jagd"
                    rb["autoFarmStatus"] = (
                        f"⚔️👑 {b_lbl} ({total_rallied} Bots): Bekämpfe {focus_mob['name']} ({hp_ratio_pct}% TP)!"
                        if d_rb <= 16.0
                        else f"🐎👑 {b_lbl} ({total_rallied} Bots): Reite zu {focus_mob['name']} ({int(d_rb)}m)!"
                    )
                else:
                    m_badge = "Erwachter Riss" if focus_mob.get("monolithState") == "erwacht" else "Instabiler Riss"
                    rb["autoFarmStatus"] = (
                        f"⚡ Gemeinsamer {m_badge} ({total_rallied} Bots): Bekämpfe {focus_mob['name']} ({hp_ratio_pct}% TP)!"
                        if d_rb <= 16.0
                        else f"🐎⚡ {m_badge} ({total_rallied} Bots): Reite zu {focus_mob['name']} ({int(d_rb)}m)!"
                    )
                rb["_botTradeStatusUntil"] = now_t + 3.8

        return rallied_bots

    def _is_mob_claimed_by_real_player(self, p: dict, mob: dict) -> bool:
        """Verhindert, dass Bots echten Spielern Monster, Rissmonolithen oder Bosse klauen.
        WICHTIG: Wenn der Bot das Ziel bereits bekämpft (targetId / autoFarmTargetId / Aggro),
        bricht er den Kampf NICHT ab und rennt NICHT weg, falls ein Spieler dazukommt!
        Öffentliche Gebiets-Weltbosse sowie instabile/erwachte Rissmonolithen werden gemeinsam bekämpft!"""
        pid = str(p.get("player_id", ""))
        if not pid.startswith("bot_"):
            return False
        if (
            mob.get("isRiftWorldBoss")
            or mob.get("isMonolithEliteBoss")
            or mob.get("isMapBossSlot")
            or (mob.get("kind") == "metin" and mob.get("monolithState") in ("instabil", "erwacht"))
        ):
            return False
        if (
            p.get("targetId") == mob["id"]
            or p.get("autoFarmTargetId") == mob["id"]
            or mob.get("targetPlayerId") == pid
        ):
            return False

        t_pid = str(mob.get("targetPlayerId") or "")
        if t_pid and not t_pid.startswith("bot_") and t_pid in self.players:
            return True

        for op_id, op in self.players.items():
            if op_id == pid or str(op_id).startswith("bot_"):
                continue
            if not op.get("online") or op.get("map_id") != mob["mapId"] or op.get("isDead"):
                continue
            d_op = dist2d(op["pos_x"], op["pos_z"], mob["x"], mob["z"])
            if (
                op.get("targetId") == mob["id"]
                or op.get("autoFarmTargetId") == mob["id"]
                or op.get("manualFocusTargetId") == mob["id"]
            ) and d_op <= 28.0:
                return True
            if (mob.get("kind") == "metin" or mob.get("isBoss")) and mob.get("hp", 0) < mob.get("maxHp", 1) and d_op <= 18.0:
                return True
        return False

    def _tick_player_autofarm(self, p: dict, dt: float, now: float):
        af = p["autofarm"]
        stats = self.ensure_autofarm_stats(af)

        hp_pct = (p["hp"] / max(1, p["max_hp"])) * 100.0
        mp_pct = (p["mp"] / max(1, p["max_mp"])) * 100.0

        # 0. Automatisch Heil- & Manatränke nachkaufen, wenn der Vorrat im Inventar niedrig ist
        if af.get("autoBuyPotions", True) and (now - float(p.get("_lastAutoPotRestockCheckAt", 0.0) or 0.0)) >= 3.5:
            p["_lastAutoPotRestockCheckAt"] = now
            self._auto_restock_potions(p, now=now, force=False, include_mp=True)

        # 1. Automatisch Heil- & Manatrank verwenden
        if af.get("autoPotion", True) and hp_pct <= float(af.get("autoPotionHpPct", 55)):
            self.use_healing_potion(p["player_id"], auto_triggered=True)
            hp_pct = (p["hp"] / max(1, p["max_hp"])) * 100.0
        if af.get("autoPotion", True) and mp_pct <= 35.0:
            consumed_mp = (
                self.db.consume_item_by_template(p["player_id"], "potion_mp_large", 1)
                or self.db.consume_item_by_template(p["player_id"], "potion_mp_medium", 1)
                or self.db.consume_item_by_template(p["player_id"], "potion_mp_small", 1)
            )
            if not consumed_mp and af.get("autoBuyPotions", True):
                self._auto_restock_potions(p, now=now, force=False, include_mp=True)
                consumed_mp = self.db.consume_item_by_template(p["player_id"], "potion_mp_medium", 1)
            if consumed_mp:
                p["mp"] = min(p["max_mp"], p["mp"] + max(450, int(p["max_mp"] * 0.45)))
                stats["potionsUsed"] = int(stats.get("potionsUsed", 0)) + 1
                self.refresh_player_from_db(p["player_id"])

        is_bot_af = str(p.get("player_id", "") or "").startswith("bot_")
        # SSOT Teil I Abs. 6: Intelligenter Einsatz von Violetten (+15% AS/+20% MS) & Grünen (+20% MS) Tränken sowie Truhen im sicheren Zustand
        if is_bot_af and (now - float(p.get("_lastBotConsumableCheckAt", 0.0) or 0.0)) >= 4.0:
            p["_lastBotConsumableCheckAt"] = now
            b_buffs = p.get("activeBuffs") or {}
            in_safe_now = is_in_safe_zone(p["map_id"], p["pos_x"], p["pos_z"])
            for it_c in list(p.get("inventory") or []):
                if not isinstance(it_c, dict) or not it_c.get("uid") or it_c.get("reservedShopId") or it_c.get("reserved_shop_id"):
                    continue
                tid_c = str(it_c.get("templateId", ""))
                tpl_c = ITEM_TEMPLATES.get(tid_c, {})
                if tid_c == "potion_speed" and not in_safe_now:
                    if float((b_buffs.get("potion_violet") or {}).get("expiresAt", 0.0) or 0.0) <= now + 3.0:
                        self.use_or_open_inventory_item(p["player_id"], it_c["uid"])
                        break
                elif tid_c == "potion_atk_speed" and not in_safe_now:
                    if (
                        float((b_buffs.get("potion_violet") or {}).get("expiresAt", 0.0) or 0.0) <= now + 3.0
                        and float((b_buffs.get("potion_green") or {}).get("expiresAt", 0.0) or 0.0) <= now + 3.0
                    ):
                        self.use_or_open_inventory_item(p["player_id"], it_c["uid"])
                        break
                elif tpl_c.get("type") == "chest" and (in_safe_now or hp_pct >= 88.0):
                    self.use_or_open_inventory_item(p["player_id"], it_c["uid"])
                    break

        # SSOT Teil I Abs. 6: Aktives Boss-Skill-Ausweichen (AI-Hitbox-Erkennung auf telegrafierte Flächenangriffe VOR Schadensapplikation!)
        if (is_bot_af or af.get("useBotSystemData", True)) and self.telegraphs:
            px_t, pz_t = float(p["pos_x"]), float(p["pos_z"])
            for tel in self.telegraphs:
                if tel.get("mapId") != p["map_id"] or float(tel.get("explodeAt", 0.0)) <= now:
                    continue
                t_rad = float(tel.get("radius", 4.8))
                d_tel = dist2d(px_t, pz_t, float(tel["x"]), float(tel["z"]))
                if d_tel <= t_rad + 1.45:
                    out_dx = px_t - float(tel["x"])
                    out_dz = pz_t - float(tel["z"])
                    if math.hypot(out_dx, out_dz) < 0.15:
                        ang_rnd = random.uniform(0.0, math.pi * 2.0)
                        out_dx, out_dz = math.sin(ang_rnd), math.cos(ang_rnd)
                    if p.get("active_mount"):
                        p["active_mount"] = None
                        p["_lastAutoMountSwitchAt"] = now
                        self.compute_player_combat_stats(p)
                    res_dg = self.perform_player_dodge(p["player_id"], {"dx": out_dx, "dz": out_dz})
                    if res_dg.get("ok"):
                        p["tacticalDodges"] = int(p.get("tacticalDodges", 0)) + 1
                        stats["tacticalDodges"] = int(stats.get("tacticalDodges", 0)) + 1
                        p["autoFarmStatus"] = f"💨 Boss-Hitbox erkannt: Ausweichrolle aus '{tel.get('skillName', 'Boss-Flächenangriff')}'!"
                        p["_botTradeStatusUntil"] = now + 2.4
                        return
                    out_len = max(0.01, math.hypot(out_dx, out_dz))
                    esc_x = float(tel["x"]) + (out_dx / out_len) * (t_rad + 2.2)
                    esc_z = float(tel["z"]) + (out_dz / out_len) * (t_rad + 2.2)
                    self._move_player_towards(p, esc_x, esc_z, dt)
                    return

        # Auto-Reittier rufen falls gewünscht (respektiert manuelles Absitzen)
        if af.get("autoMount", False) and not p.get("active_mount") and now >= float(p.get("_manualDismountUntil", 0.0) or 0.0):
            p["active_mount"] = "mount_war_boar"
            self.compute_player_combat_stats(p)

        # Bots rufen automatisch ihr Pet, wählen ihr 3D-Pet-Aussehen und verteilen Pet-Status- & Skillpunkte
        if str(p.get("player_id", "") or "").startswith("bot_") and (
            not p.get("active_pet") or now - float(p.get("_lastBotPetMaintainAt", 0.0) or 0.0) >= 6.0
        ):
            p["_lastBotPetMaintainAt"] = now
            if self._auto_maintain_bot_pet(p):
                self.db.save_player_state(p)

        # 2. Bei kritischer Lebensenergie in die sichere Zone zurückziehen
        if hp_pct <= float(af.get("retreatHpPct", 20)):
            sz = MAPS.get(p["map_id"], MAPS["morgenwacht"])["safeZone"]
            p["autoFarmStatus"] = "🛡️ Rückzug in sichere Zone (Niedrige TP!)"
            self._move_player_towards(p, sz["x"], sz["z"], dt)
            return

        mode = af.get("mode", "all")  # 'all' | 'monsters' | 'metins' | 'bosses' | 'dungeon' | 'fishing' | 'mining'

        # ====================================================================
        # MODUS A: AUTO-FISCHEN AM GEWÄSSER ('fishing')
        # ====================================================================
        if mode == "fishing":
            fish_spot = (-18.0, 74.0) if p["map_id"] == "morgenwacht" else (-22.0, 68.0)
            fdist = dist2d(p["pos_x"], p["pos_z"], fish_spot[0], fish_spot[1])
            if fdist > 5.0:
                p["autoFarmStatus"] = f"🎣 Laufe zum Angelplatz am Gewässer ({int(fdist)}m)"
                self._move_player_towards(p, fish_spot[0], fish_spot[1], dt)
                return

            p["autoFarmStatus"] = "🎣 Auto-Fischen aktiv (Silberzander, Muscheln & Perlen)..."
            if now - p.get("lastFishTime", 0.0) >= 3.6:
                p["lastFishTime"] = now
                roll = random.random()
                if roll < 0.12:
                    catch_id = "mat_white_pearl"
                    yang_bonus = random.randint(550, 950)
                elif roll < 0.38:
                    catch_id = "fish_clam"
                    yang_bonus = random.randint(280, 480)
                else:
                    catch_id = "fish_zander"
                    yang_bonus = random.randint(160, 290)

                exp_bonus = 18
                stats["fishCaught"] = int(stats.get("fishCaught", 0)) + 1
                stats["expEarned"] = int(stats.get("expEarned", 0)) + exp_bonus
                if p["level"] < MAX_PLAYER_LEVEL:
                    p["exp"] += exp_bonus

                if af.get("fishAutoSellSmall", False) and catch_id == "fish_zander":
                    sell_val = ITEM_TEMPLATES["fish_zander"]["sellPrice"] + yang_bonus
                    p["yang"] += sell_val
                    stats["yangEarned"] = int(stats.get("yangEarned", 0)) + sell_val
                    p["autoFarmStatus"] = f"🎣 Zander gefangen & direkt verkauft (+{sell_val} Gold)"
                    self._log_player_drop("fish_zander", qty=1, yang_gain=sell_val, auto_sold=True, source="Angeln", player_id=p["player_id"])
                else:
                    p["yang"] += yang_bonus
                    stats["yangEarned"] = int(stats.get("yangEarned", 0)) + yang_bonus
                    self.db.add_item_to_inventory(p["player_id"], catch_id, 1)
                    self.refresh_player_from_db(p["player_id"])
                    cname = ITEM_TEMPLATES[catch_id]["name"]
                    p["autoFarmStatus"] = f"🎣 Gefangen: 1x {cname} (+{yang_bonus} Gold)"
                    self._log_player_drop(catch_id, qty=1, yang_gain=yang_bonus, source="Angeln", player_id=p["player_id"])
                self.db.save_player_state(p)
            return

        # ====================================================================
        # MODUS B: AUTO-MINING / ERZADER-ABBAU ('mining')
        # ====================================================================
        if mode == "mining":
            veins = [
                (-34.0, 26.0, "Ebenholz-Erzader (Zentrum)"),
                (34.0, 24.0, "Himmelstränen-Ader (Zentrum)"),
                (-12.0, -32.0, "Ätherkristall-Ader (Zentral-Nord)"),
                (-165.0, 265.0, "Ebenholz-Erzader (West-Königstal)"),
                (165.0, 265.0, "Himmelstränen-Ader (Ost-Königstal)"),
                (-245.0, 32.0, "Ebenholz-Erzader (West-Auen)"),
                (245.0, 32.0, "Himmelstränen-Ader (Ost-Auen)"),
                (-385.0, -25.0, "Ätherkristall-Ader (West-Plateau)"),
                (385.0, -25.0, "Ätherkristall-Ader (Ost-Plateau)"),
                (-415.0, -185.0, "Ätherkristall-Ader (Nordwest-Wasserfall)"),
                (415.0, -185.0, "Ätherkristall-Ader (Nordost-Wasserfall)"),
                (0.0, -285.0, "Ätherkristall-Ader (Nordsee-Ufer)"),
            ]
            vein_idx = int(stats.get("oresMined", 0) // 3) % len(veins)
            vx, vz, vname = veins[vein_idx]
            vdist = dist2d(p["pos_x"], p["pos_z"], vx, vz)
            if vdist > 4.5:
                p["autoFarmStatus"] = f"⛏️ Laufe zu {vname} ({int(vdist)}m)"
                self._move_player_towards(p, vx, vz, dt)
                return

            p["autoFarmStatus"] = f"⛏️ Baue {vname} ab..."
            if now - p.get("lastMineTime", 0.0) >= 3.4:
                p["lastMineTime"] = now
                roll = random.random()
                if roll < 0.18:
                    ore_id = "ore_aether_crystal"
                    yang_bonus = random.randint(480, 820)
                elif roll < 0.52:
                    ore_id = "ore_heaven_tear"
                    yang_bonus = random.randint(290, 510)
                else:
                    ore_id = "ore_ebony"
                    yang_bonus = random.randint(180, 340)

                exp_bonus = 22
                qty = random.randint(1, 2)
                p["yang"] += yang_bonus
                if p["level"] < MAX_PLAYER_LEVEL:
                    p["exp"] += exp_bonus
                stats["oresMined"] = int(stats.get("oresMined", 0)) + qty
                stats["yangEarned"] = int(stats.get("yangEarned", 0)) + yang_bonus
                stats["expEarned"] = int(stats.get("expEarned", 0)) + exp_bonus
                self.db.add_item_to_inventory(p["player_id"], ore_id, qty)
                self.refresh_player_from_db(p["player_id"])
                oname = ITEM_TEMPLATES[ore_id]["name"]
                p["autoFarmStatus"] = f"⛏️ Abgebaut: {qty}x {oname} (+{yang_bonus} Gold)"
                self._log_player_drop(ore_id, qty=qty, yang_gain=yang_bonus, source=vname, player_id=p["player_id"])
                self.db.save_player_state(p)
            return

        # ====================================================================
        # MODUS C: KAMPF-JAGD (MONSTER, MONOLITHEN, BOSSE, DUNGEON)
        # ====================================================================
        # Intelligenter Einsatz von Tapferkeitsumhängen ('cape_bravery') aus dem Inventar (für Bots & Auto-Pull)
        is_bot_p = str(p.get("player_id", "")).startswith("bot_")
        if (
            (is_bot_p or af.get("autoPull", False))
            and now - float(p.get("lastAutoPullTime", 0.0) or 0.0) >= 14.0
            and now - float(p.get("_lastAutoPullCheckAt", 0.0) or 0.0) >= 2.5
        ):
            p["_lastAutoPullCheckAt"] = now
            if not is_in_safe_zone(p["map_id"], p["pos_x"], p["pos_z"]) and hp_pct >= 70.0:
                pid_c = p["player_id"]
                p_lvl_c = int(p.get("level", 1))
                px_c, pz_c = float(p["pos_x"]), float(p["pos_z"])
                already_chasing = 0
                pullable_mobs = []
                for m in list(self.monsters.values()):
                    if m["mapId"] != p["map_id"] or m["state"] == "dead" or m["kind"] != "monster" or m.get("isBoss"):
                        continue
                    if abs(m["x"] - px_c) > 36.0 or abs(m["z"] - pz_c) > 36.0:
                        continue
                    d_m = dist2d(px_c, pz_c, m["x"], m["z"])
                    if m.get("targetPlayerId") == pid_c and d_m <= 14.0:
                        already_chasing += 1
                    elif 5.5 <= d_m <= 36.0 and int(m.get("level", 1)) <= p_lvl_c + 5:
                        if not self._is_mob_claimed_by_real_player(p, m):
                            pullable_mobs.append((d_m, m))

                # Nur ziehen, wenn der Bot nicht bereits überrannt wird (<= 2 am Bot) und sich mind. 3 Monster im Umkreis lohnen!
                if already_chasing <= 2 and len(pullable_mobs) >= 3:
                    inv_c = p.get("inventory") or []
                    cape_tpl_id = None
                    for it in inv_c:
                        if (
                            isinstance(it, dict)
                            and it.get("templateId") in ("item_bravery_cape", "cape_bravery")
                            and int(it.get("quantity", 1)) > 0
                            and not it.get("reservedShopId")
                        ):
                            cape_tpl_id = it.get("templateId")
                            break

                    used_cape = False
                    if cape_tpl_id:
                        used_cape = self.db.consume_item_by_template(pid_c, cape_tpl_id, 1)
                        if used_cape:
                            self.refresh_player_from_db(pid_c)

                    if used_cape:
                        p["lastAutoPullTime"] = now
                        pullable_mobs.sort(key=lambda x: x[0])
                        max_pull_cnt = 7 if p.get("partyId") else 5
                        pulled_now = 0
                        for _, m_pull in pullable_mobs[:max_pull_cnt]:
                            m_pull["targetPlayerId"] = pid_c
                            m_pull["state"] = "chase"
                            pulled_now += 1
                        stats["capesUsed"] = int(stats.get("capesUsed", 0)) + 1
                        p["capesUsed"] = int(p.get("capesUsed", 0)) + 1
                        p["autoFarmStatus"] = f"🦸 Tapferkeitsumhang genutzt! ({pulled_now} Monster für AoE-Kombo angelockt)"
                        p["_botTradeStatusUntil"] = now + 3.8
                        self._emit_combat_event(
                            p["map_id"],
                            "combat_feedback",
                            p["pos_x"],
                            p["pos_z"],
                            {
                                "playerId": pid_c,
                                "feedbackType": "buff",
                                "text": f"🦸 Tapferkeitsumhang ({pulled_now}x Pull!)",
                                "color": "#f59e0b",
                            },
                        )

        # 3. Automatisch nahe Beute einsammeln (SSOT Strikter Ziel-Fokus: Während ein Ziel lebt, KEIN 18m-Lauf-Abbruch mitten im Kampf!)
        locked_fight_tid = p.get("manualFocusTargetId") or p.get("autoFarmTargetId") or p.get("targetId")
        locked_fight_mob = self.monsters.get(locked_fight_tid) if locked_fight_tid else None
        is_actively_fighting = bool(
            locked_fight_mob
            and locked_fight_mob.get("mapId") == p["map_id"]
            and locked_fight_mob.get("state") != "dead"
            and int(locked_fight_mob.get("hp", 0)) > 0
            and dist2d(p["pos_x"], p["pos_z"], locked_fight_mob["x"], locked_fight_mob["z"]) <= 24.0
        )
        if af.get("autoLoot", True):
            max_loot_scan = 3.8 if is_actively_fighting else 18.0
            allowed_drops = []
            for d in self.drops.values():
                if d["mapId"] != p["map_id"]:
                    continue
                if dist2d(p["pos_x"], p["pos_z"], d["x"], d["z"]) > max_loot_scan:
                    continue
                can_pick, _ = self.can_player_pickup_drop(p["player_id"], d, now=now, is_auto=True)
                if not can_pick:
                    continue
                should_pick, should_sell = self.evaluate_drop_filter(p, d)
                if not should_pick:
                    continue
                allowed_drops.append((d, should_sell))

            if allowed_drops:
                nearest_drop, nearest_sell = min(
                    allowed_drops, key=lambda pair: dist2d(p["pos_x"], p["pos_z"], pair[0]["x"], pair[0]["z"])
                )
                ddist = dist2d(p["pos_x"], p["pos_z"], nearest_drop["x"], nearest_drop["z"])
                if ddist <= 3.8:
                    self.pickup_drop(p["player_id"], nearest_drop["id"], auto_sell=nearest_sell)
                elif not is_actively_fighting:
                    action_lbl = "Auto-Verkauf" if nearest_sell else "Sammle Beute"
                    p["autoFarmStatus"] = f"💎 {action_lbl}: {nearest_drop['name']}"
                    self._move_player_towards(p, nearest_drop["x"], nearest_drop["z"], dt)
                    return

        # 4. Zielsuche im eingestellten Farmradius (mit kartenweitem Fallback auf den großen 1200x1200m Karten)
        radius = float(af.get("radius", 180))
        prio_elites = bool(af.get("prioritizeElites", True))
        atk_bosses = bool(af.get("attackBosses", False)) or mode in ("bosses", "dungeon")
        hunt_monsters = bool(af.get("huntMonsters", True))
        hunt_metins = bool(af.get("huntMetins", True))
        player_lvl = int(p.get("level", 1))
        is_bot_player = str(p.get("player_id", "")).startswith("bot_")
        af.setdefault("useBotSystemData", True)
        use_bot_ai = is_bot_player or bool(af.get("useBotSystemData", True))
        bot_sys_data = self._get_bot_system_assist_data(p) if not is_bot_player else None
        if bot_sys_data is not None:
            af["botSystemData"] = bot_sys_data

        # Gruppen-Kontext ermitteln (für gemeinsames Bekämpfen stärkerer Monster/Rissmonolithen & gegenseitige Hilfe)
        party_id = p.get("partyId")
        party = self.parties.get(party_id) if party_id else None
        party_members = []
        party_focus_mob_ids = set()
        any_party_member_hurt = False
        if party:
            for mid in party.get("memberIds", [])[:8]:
                mp = self.players.get(mid)
                if mp and mp.get("online") and not mp.get("isDead") and mp.get("map_id") == p["map_id"]:
                    party_members.append(mp)
                    if (mp["hp"] / max(1, mp["max_hp"])) < 0.78:
                        any_party_member_hurt = True
                    m_tid = mp.get("targetId") or mp.get("autoFarmTargetId")
                    if m_tid:
                        party_focus_mob_ids.add(m_tid)
        party_size = len(party_members)
        if is_bot_player:
            atk_bosses = True
            hunt_metins = True
            bot_inv = p.get("inventory") or []
            bot_has_shard = any(
                isinstance(it, dict)
                and it.get("templateId") == "mat_monolith_shard"
                and not it.get("reservedShopId")
                and not it.get("reserved_shop_id")
                and int(it.get("quantity", 1) or 1) >= 1
                for it in bot_inv
            )
            bot_has_core = any(
                isinstance(it, dict)
                and it.get("templateId") == "mat_awakened_rift_core"
                and not it.get("reservedShopId")
                and not it.get("reserved_shop_id")
                and int(it.get("quantity", 1) or 1) >= 1
                for it in bot_inv
            )
        else:
            bot_has_shard = False
            bot_has_core = False

        manual_focus_id = p.get("manualFocusTargetId")
        if manual_focus_id:
            mf_mob = self.monsters.get(manual_focus_id)
            if not mf_mob or mf_mob["mapId"] != p["map_id"] or mf_mob["state"] == "dead" or mf_mob["hp"] <= 0:
                p["manualFocusTargetId"] = None
                manual_focus_id = None

        candidates = []
        fallback_candidates = []
        effective_radius = max(radius, 260.0 if (mode in ("bosses", "dungeon", "metins") or party_size >= 2 or is_bot_player) else 185.0)
        max_fallback_dist = 320.0 if is_bot_player else 950.0
        px_f, pz_f = float(p["pos_x"]), float(p["pos_z"])

        # SSOT Teil I Abs. 6: STRIKTER ZIEL-FOKUS (Kein Flattern!)
        # Ein einmal anvisiertes lebendes Ziel wird konsequent bekämpft, bis es vollständig besiegt ist!
        cur_af_tid = manual_focus_id or p.get("autoFarmTargetId") or p.get("targetId")
        cur_af_mob = self.monsters.get(cur_af_tid) if cur_af_tid else None
        if (
            cur_af_mob
            and cur_af_mob["mapId"] == p["map_id"]
            and cur_af_mob["state"] != "dead"
            and int(cur_af_mob.get("hp", 0)) > 0
            and not self._is_mob_claimed_by_real_player(p, cur_af_mob)
        ):
            d_cur = dist2d(px_f, pz_f, cur_af_mob["x"], cur_af_mob["z"])
            if d_cur <= max_fallback_dist or manual_focus_id:
                rf_cur = self.compute_level_reward_penalty(player_lvl, int(cur_af_mob.get("level", 1)), p["map_id"])
                is_cur_coop_boss = bool(
                    cur_af_mob.get("isRiftWorldBoss")
                    or cur_af_mob.get("isMonolithEliteBoss")
                    or (cur_af_mob.get("kind") == "metin" and cur_af_mob.get("monolithState") in ("instabil", "erwacht"))
                )
                if is_cur_coop_boss and rf_cur <= 0.0:
                    rf_cur = 0.85
                if not use_bot_ai or rf_cur > 0.0 or manual_focus_id or is_cur_coop_boss or int(cur_af_mob.get("hp", 1)) < int(cur_af_mob.get("maxHp", 1)):
                    candidates.append((-1000.0, d_cur, cur_af_mob, rf_cur))

        if not candidates:
            p["_lastAutoFarmTargetScanAt"] = now
            for mob in list(self.monsters.values()):
                if mob["mapId"] != p["map_id"] or mob["state"] == "dead":
                    continue
                is_manual_focus = bool(manual_focus_id and mob["id"] == manual_focus_id)
                is_party_focus = bool(
                    party_size >= 2
                    and (
                        mob["id"] in party_focus_mob_ids
                        or (mob.get("targetPlayerId") and any(mp["player_id"] == mob.get("targetPlayerId") for mp in party_members))
                    )
                )
                is_coop_world_event = bool(
                    mob.get("isRiftWorldBoss")
                    or mob.get("isMonolithEliteBoss")
                    or (mob["kind"] == "metin" and mob.get("monolithState") in ("instabil", "erwacht"))
                )
                if not is_manual_focus and not is_party_focus and not is_coop_world_event:
                    if abs(mob["x"] - px_f) > max_fallback_dist or abs(mob["z"] - pz_f) > max_fallback_dist:
                        continue
                if self._is_mob_claimed_by_real_player(p, mob):
                    continue

                is_metin = mob["kind"] == "metin"
                is_boss = bool(mob["isBoss"])

                if not is_manual_focus and not is_party_focus and not is_coop_world_event:
                    if mode in ("monsters", "monster") and (is_metin or is_boss):
                        continue
                    elif mode in ("metins", "metin") and not is_metin and not is_bot_player:
                        continue
                    elif mode == "bosses" and not (is_boss or mob["isElite"] or is_metin):
                        continue
                    elif mode == "all" or (is_bot_player and mode in ("metins", "metin")):
                        if is_boss and not atk_bosses:
                            continue
                        if is_metin and not hunt_metins:
                            continue
                        if not is_metin and not is_boss and not hunt_monsters and not is_bot_player:
                            continue

                d = dist2d(px_f, pz_f, mob["x"], mob["z"])
                if not is_manual_focus and not is_party_focus and d > max_fallback_dist:
                    continue
                mob_lvl = int(mob.get("level", 1))
                mob_reward_factor = self.compute_level_reward_penalty(
                    player_lvl, mob_lvl, p["map_id"]
                )
                if use_bot_ai and is_coop_world_event and player_lvl >= mob_lvl - 10:
                    mob_reward_factor = max(0.80, mob_reward_factor)
                if use_bot_ai and not is_manual_focus:
                    # Bot-System-Schutz (auch für Spieler-Autojagd): Niemals normale Ziele mit 0% EXP/Drop angreifen!
                    if mob_reward_factor <= 0.0 and not is_coop_world_event:
                        continue
                if is_bot_player and not is_manual_focus:
                    # SSOT Teil I Abs. 2: Bots wechseln exakt mit Erreichen von Level 23 nach Map 2 (z > 0)!
                    # Unter Level 23 bleiben sie strikt in Map 1 (z < 0: Lv. 1–8 Wölfe, Lv. 9–15 Bären/Tiger, Lv. 16–22 Eid-Kämpfer).
                    if player_lvl >= 23 and mob["z"] < 0.0 and not (is_coop_world_event and d <= 165.0):
                        continue
                    if player_lvl < 23 and mob["z"] > 0.0:
                        continue
                    b_emp = str(p.get("empire", "seiryu")).lower()
                    if mob["z"] < -30.0:
                        if b_emp == "seiryu" and mob["x"] < -180.0:
                            continue
                        elif b_emp == "kaeryu" and mob["x"] > 180.0:
                            continue
                active_evt = getattr(self, "world_event", None) or {}
                active_evt_id = str(active_evt.get("id", ""))
                score = d
                if is_manual_focus:
                    score -= 600.0
                else:
                    if is_party_focus:
                        # Gemeinsames Fokus-Feuer der Gruppe auf denselben Rissmonolith / dasselbe starke Monster!
                        score -= 460.0
                    if mob.get("isRiftWorldBoss") and d <= 310.0:
                        # Höchste Priorität für nahen Gebiets-Weltboss (gemeinsame Bot-Weltboss-Jagd!)
                        score -= 540.0
                    elif mob.get("isMonolithEliteBoss") and d <= 220.0:
                        score -= 460.0 if d <= 18.0 else 350.0
                    elif mob.get("isMapBossSlot") and d <= 210.0 and player_lvl >= mob_lvl - 6:
                        # Gemeinsame Jagd auf die 3 festen 15-Minuten-Kartenbosse (KI v5.0)
                        score -= 390.0 if (party_size >= 2 or int(mob.get("hp", 1)) < int(mob.get("maxHp", 1))) else 285.0
                    elif is_metin and mob.get("monolithState") == "erwacht" and d <= 240.0:
                        wb_id = mob.get("activeWorldBossId")
                        wb_alive = bool(wb_id and wb_id in self.monsters and self.monsters[wb_id].get("state") != "dead")
                        score -= 130.0 if wb_alive else 440.0
                    elif is_metin and mob.get("monolithState") == "instabil" and d <= 220.0:
                        score -= 425.0 + (45.0 if int(mob.get("hp", 1)) < int(mob.get("maxHp", 1)) else 0.0)
                    elif is_bot_player and is_metin and mob.get("monolithState", "schlafend") == "schlafend" and d <= 195.0 and bot_has_shard:
                        # Bots mit Monolithensplitter im Inventar suchen gezielt schlafende Rissmonolithen auf, um sie zu bekämpfen!
                        if player_lvl >= mob_lvl - 2:
                            score -= 95.0
                    if mob_reward_factor <= 0.0:
                        score += 240.0
                    else:
                        score -= mob_reward_factor * 18.0
                    if use_bot_ai:
                        # Ziele auf bewährten Bot-Jagdrouten bevorzugen
                        score -= min(24.0, self._get_learned_bot_trail_weight(mob["x"], mob["z"]) * 0.40)
                    if is_bot_player and mode in ("metins", "metin") and is_metin and d <= 165.0:
                        score -= 38.0
                    # Automatische Server-Events intelligent in die Zielauswahl & Drop-/EXP-/Gold-Bewertung einberechnen!
                    if mob_reward_factor > 0.0:
                        if active_evt_id == "monolith_eruption" and is_metin:
                            score -= 46.0  # +25% Monolith-Beute & +20% Seelenstein-Chance
                        elif active_evt_id == "boss_hunt_frenzy" and (is_boss or mob["isElite"]):
                            score -= 52.0  # +25% Boss-Truhen & Weiße Perlen
                        elif active_evt_id == "moonlight_chests" and not is_metin and mob_reward_factor >= 0.75:
                            score -= 22.0  # +18% Mondlicht-Schatztruhen im passenden Levelbereich
                        elif active_evt_id == "imperial_blessing" and mob_reward_factor >= 0.75:
                            score -= 24.0  # +30% EXP & +25% Gold-Drop
                    # In einer Gruppe (bis zu 8 Mitglieder) können deutlich stärkere Monster & Rissmonolithen bekämpft werden!
                    allowed_lvl_margin = 7 + max(0, party_size - 1) * 4
                    if mob_lvl > player_lvl + allowed_lvl_margin and mode not in ("bosses", "dungeon"):
                        score += (mob_lvl - (player_lvl + allowed_lvl_margin)) * 16.0
                    elif party_size >= 2 and (is_metin or is_boss or mob["isElite"]) and mob_lvl <= player_lvl + allowed_lvl_margin:
                        score -= 75.0
                    if mode == "bosses" and is_boss:
                        score -= 80.0
                    elif mode == "dungeon" and (is_boss or is_metin or mob["isElite"]):
                        score -= 45.0
                    elif prio_elites and (mob["isElite"] or is_metin):
                        score -= 14.0
                    if is_metin and int(mob.get("shiningTier", 1)) > 1:
                        score -= (int(mob.get("shiningTier", 1)) - 1) * 14.0
                    if mob["id"] == p.get("targetId") or mob["id"] == p.get("autoFarmTargetId"):
                        score -= 48.0
                    if af.get("anchorX") is not None and af.get("anchorZ") is not None:
                        d_anchor = dist2d(float(af["anchorX"]), float(af["anchorZ"]), mob["x"], mob["z"])
                        score += d_anchor * 0.38
                    # Reichs-Korridor-Disziplin für Bots: Seiryu-Bots jagen bevorzugt auf der Ost- & Zentralroute (x >= -220),
                    # Kaeryu-Bots auf der West- & Zentralroute (x <= +220), damit jedes Reich seine eigene Steinbrücke nutzt
                    # und sich im umstrittenen Grenzland (-240 <= x <= +240) begegnet.
                    if is_bot_player:
                        b_emp = str(p.get("empire", "seiryu")).lower()
                        if b_emp == "seiryu" and mob["x"] < -240.0:
                            score += abs(mob["x"] + 240.0) * 1.65
                        elif b_emp == "kaeryu" and mob["x"] > 240.0:
                            score += abs(mob["x"] - 240.0) * 1.65

                entry = (score, d, mob, mob_reward_factor)
                if d <= effective_radius or is_manual_focus or is_party_focus:
                    candidates.append(entry)
                elif d <= max_fallback_dist:
                    fallback_candidates.append(entry)

            if not candidates and fallback_candidates:
                candidates = fallback_candidates

        if not candidates:
            p["autoFarmTargetId"] = None
            p["autoFarmNextTargetId"] = None
            if isinstance(p.get("townErrand"), dict):
                # Stadtrundgang / NPC-Gang: Ziel (NPC) setzt _tick_bot_town_errand als Anker. Hier nur fluessig
                # mit echtem dt dorthin laufen (bis direkt vor den NPC), niemals Richtung Jagdgebiet.
                ex, ez = af.get("anchorX"), af.get("anchorZ")
                if ex is not None and ez is not None and dist2d(p["pos_x"], p["pos_z"], float(ex), float(ez)) > 9.0:
                    self._move_player_towards(p, float(ex), float(ez), dt)
                return
            nav_ax = af.get("anchorX")
            nav_az = af.get("anchorZ")
            nav_lbl = "Jagdgebiet"
            if (nav_ax is None or nav_az is None) and use_bot_ai and bot_sys_data:
                nav_ax = bot_sys_data.get("recommendedAnchorX")
                nav_az = bot_sys_data.get("recommendedAnchorZ")
                nav_lbl = bot_sys_data.get("recommendedSectorLabel") or "Bot-Sektor"
            if nav_ax is not None and nav_az is not None:
                ax, az = float(nav_ax), float(nav_az)
                adist = dist2d(p["pos_x"], p["pos_z"], ax, az)
                if adist > 18.0:
                    if not p.get("active_mount") and now >= float(p.get("_manualDismountUntil", 0.0) or 0.0):
                        p["active_mount"] = af.get("mountId") or "mount_war_boar"
                        self.compute_player_combat_stats(p)
                    p["autoFarmStatus"] = f"🤖 Bot-Wegfindung: Reite zu {nav_lbl} ({int(adist)}m)..."
                    self._move_player_towards(p, ax, az, dt)
                    return
            p["autoFarmStatus"] = "🔍 Suche Ziele im Farmradius..."
            return

        candidates.sort(key=lambda x: x[0])
        _, target_dist, target_mob, target_reward_factor = candidates[0]
        p["targetId"] = target_mob["id"]
        p["autoFarmTargetId"] = target_mob["id"]
        p["autoFarmNextTargetId"] = candidates[1][2]["id"] if len(candidates) > 1 else None

        # Intelligente Rissmonolith-Erweckung durch Bots mit Inventar-Items ('mat_monolith_shard' & 'mat_awakened_rift_core'):
        # 1) Schlafender Rissmonolith -> Instabil ('instabil'), NUR wenn der Bot bereits im Nahkampf auf den Monolithen einschlägt (< 96% TP)
        #    und kein anderer instabiler/erwachter Monolith in der Nähe noch ungetötet steht!
        # 2) Instabiler Rissmonolith -> Erwacht ('erwacht' + Gebiets-Weltboss), wenn der Bot 1x Erwachter Risskern besitzt und stark genug ist!
        if (
            is_bot_player
            and target_mob["kind"] == "metin"
            and target_mob.get("state") != "dead"
            and target_dist <= float(p["computed"]["attackRange"]) + 2.0
            and int(target_mob.get("hp", 1)) < int(target_mob.get("maxHp", 1)) * 0.96
            and (now - float(p.get("_lastBotMonolithAwakenCheckAt", 0.0) or 0.0)) >= 2.5
            and (now - float(p.get("_lastBotMonolithAwakenAt", 0.0) or 0.0)) >= 45.0
        ):
            p["_lastBotMonolithAwakenCheckAt"] = now
            cur_m_state = target_mob.get("monolithState", "schlafend")
            if cur_m_state == "schlafend":
                can_instabil, _allies_inst = self._evaluate_bot_monolith_strength(p, target_mob, "instabil")
                if can_instabil:
                    res_awk = self.interact_with_monolith(p["player_id"], target_mob["id"], mode="awaken")
                    if isinstance(res_awk, dict) and res_awk.get("ok"):
                        p = self.players.get(p["player_id"], p)
                        p["_lastBotMonolithAwakenAt"] = now
                        p["targetId"] = target_mob["id"]
                        p["autoFarmTargetId"] = target_mob["id"]
                        p["manualFocusTargetId"] = target_mob["id"]
                        p["monolithsMadeUnstable"] = int(p.get("monolithsMadeUnstable", 0)) + 1
                        p["monolithsAwakened"] = int(p.get("monolithsAwakened", 0)) + 1
                        stats["monolithsMadeUnstable"] = int(stats.get("monolithsMadeUnstable", 0)) + 1
                        stats["monolithsAwakened"] = int(stats.get("monolithsAwakened", 0)) + 1
                        p["autoFarmStatus"] = f"⚡ Monolithensplitter genutzt: {target_mob['name']} in INSTABILEN Zustand gebracht!"
                        p["_botTradeStatusUntil"] = now + 5.5
                        self.db.save_player_state(p)
                        self._rally_nearby_bots_for_monolith_or_world_boss(target_mob, initiator_bot=p, now=now)
            elif cur_m_state == "instabil" and (now - float(target_mob.get("stateChangedAt", 0.0) or 0.0)) >= 6.0 and int(target_mob.get("hp", 1)) <= int(target_mob.get("maxHp", 1)) * 0.88:
                can_erwacht, _allies_erw = self._evaluate_bot_monolith_strength(p, target_mob, "erwacht")
                if can_erwacht:
                    res_awk = self.interact_with_monolith(p["player_id"], target_mob["id"], mode="awaken")
                    if isinstance(res_awk, dict) and res_awk.get("ok"):
                        p = self.players.get(p["player_id"], p)
                        p["_lastBotMonolithAwakenAt"] = now
                        p["monolithsAwakened"] = int(p.get("monolithsAwakened", 0)) + 1
                        p["worldBossesSummoned"] = int(p.get("worldBossesSummoned", 0)) + 1
                        stats["monolithsAwakened"] = int(stats.get("monolithsAwakened", 0)) + 1
                        stats["worldBossesSummoned"] = int(stats.get("worldBossesSummoned", 0)) + 1
                        wb_spawned = self._get_active_world_boss(p["map_id"])
                        wb_title = wb_spawned["name"] if wb_spawned else "Gebiets-Weltboss"
                        p["autoFarmStatus"] = f"🔥 Erwachter Risskern genutzt: {wb_title} beschworen! Gemeinsamer Angriff!"
                        p["_botTradeStatusUntil"] = now + 6.5
                        self.db.save_player_state(p)
                        self._rally_nearby_bots_for_monolith_or_world_boss(wb_spawned or target_mob, initiator_bot=p, now=now)
                        if wb_spawned:
                            target_mob = wb_spawned
                            target_dist = dist2d(float(p["pos_x"]), float(p["pos_z"]), float(wb_spawned["x"]), float(wb_spawned["z"]))
                            p["targetId"] = wb_spawned["id"]
                            p["autoFarmTargetId"] = wb_spawned["id"]
                            p["manualFocusTargetId"] = wb_spawned["id"]

        party_bonus_pct = max(0, (min(8, party_size) - 1) * 20)
        party_tag = f" • 👥 Gruppe ({party_size}/8 | +{party_bonus_pct}% EXP)" if party_size >= 2 else ""
        active_evt = getattr(self, "world_event", None) or {}
        evt_short_map = {
            "moonlight_chests": "🌙 +18% Mondi",
            "monolith_eruption": "☄️ +25% Riss-Loot",
            "imperial_blessing": "👑 +30% EXP/+25% Gold",
            "boss_hunt_frenzy": "🐉 +25% Boss-Loot",
        }
        evt_tag = f" • {evt_short_map[active_evt['id']]}" if active_evt.get("id") in evt_short_map else ""
        reward_pct_tag = (f" • {int(round(target_reward_factor * 100))}% EXP/Drop" if target_reward_factor < 1.0 else "") + party_tag + evt_tag

        # Intelligente Reittier-Nutzung für Bots (und Spieler mit Bot-KI + Auto-Reittier / smartMount):
        # - Bei Rissmonolithen (kind == 'metin') oder weiteren Distanzen (> 34m) automatisch Pferd/Reittier rufen!
        # - Im Kampf nutzt der Charakter für Eigenbuffs den atomaren Sofort-Abstieg/Buff/Aufstieg (Zeile 4520+), ohne vorheriges Stehenbleiben.
        if is_bot_player or af.get("smartMount", False) or (use_bot_ai and af.get("autoMount", False)):
            pref_mount = af.get("mountId") or ("mount_crystal_wolf" if "mounted" in str(p.get("player_id", "")) or "donnerkeil" in str(p.get("player_id", "")) else "mount_war_boar")
            if (now - float(p.get("_lastAutoMountSwitchAt", 0.0) or 0.0)) >= 4.0 and now >= float(p.get("_manualDismountUntil", 0.0) or 0.0):
                is_dedicated_rider = "mounted" in str(p.get("player_id", "")) or "donnerkeil" in str(p.get("player_id", "")) or bool(af.get("alwaysMounted", False))
                should_mount = bool(
                    target_mob["kind"] == "metin"
                    or target_dist > 34.0
                    or is_dedicated_rider
                )
                if should_mount and not p.get("active_mount"):
                    p["active_mount"] = pref_mount
                    p["_lastAutoMountSwitchAt"] = now
                    self.compute_player_combat_stats(p)
                elif not should_mount and p.get("active_mount") and target_dist <= 6.5 and not is_dedicated_rider and is_bot_player:
                    p["active_mount"] = None
                    p["_lastAutoMountSwitchAt"] = now
                    self.compute_player_combat_stats(p)

        prefix_ico = "🏰 Dungeon: " if mode == "dungeon" else ("👑 Weltboss-Jagd: " if target_mob.get("isRiftWorldBoss") else ("👑 Boss-Jagd: " if mode == "bosses" or target_mob.get("isBoss") else ("🤝 Gruppen-Jagd: " if party_size >= 2 else "⚔️ ")))
        atk_range = p["computed"]["attackRange"]
        if target_dist > atk_range * 0.88:
            if now >= float(p.get("_botTradeStatusUntil", 0.0) or 0.0):
                p["autoFarmStatus"] = f"{prefix_ico}Laufe zu {target_mob['name']} ({int(target_dist)}m){reward_pct_tag}"
            self._move_player_towards(p, target_mob["x"], target_mob["z"], dt)
        else:
            p["vx"] = 0.0
            p["vz"] = 0.0
            p["dest_x"] = p["pos_x"]
            p["dest_z"] = p["pos_z"]
            p["rot_y"] = math.atan2(target_mob["x"] - p["pos_x"], target_mob["z"] - p["pos_z"])

            # KI v5.0 Taktische Boss- & Monolith-Defensive (für Bots & Spieler mit aktivierter Bot-KI):
            # Aktives Blocken (Krieger/Sura), Ausweichrolle (Dodge) & Fernkampf-Kiting (Schamane/Ninja)
            if use_bot_ai:
                if float(p.get("_botBlockUntil", 0.0) or 0.0) > 0.0 and now >= float(p.get("_botBlockUntil", 0.0) or 0.0):
                    p["isBlocking"] = False
                    p["_botBlockUntil"] = 0.0
                is_heavy_encounter = bool(
                    target_mob.get("isBoss")
                    or target_mob.get("isMapBossSlot")
                    or target_mob.get("isRiftWorldBoss")
                    or target_mob.get("isMonolithEliteBoss")
                    or (target_mob["kind"] == "metin" and target_mob.get("monolithState") in ("instabil", "erwacht"))
                )
                if is_heavy_encounter and (now - float(p.get("_lastBotTacticalDefenseAt", 0.0) or 0.0)) >= 4.5:
                    mob_just_swung = (now - float(target_mob.get("lastAttackTime", 0.0) or 0.0)) <= 0.65
                    if (mob_just_swung or hp_pct <= 72.0) and not p.get("active_mount"):
                        p["_lastBotTacticalDefenseAt"] = now
                        c_id = p.get("class_id", "warrior")
                        if c_id in ("warrior", "sura"):
                            p["isBlocking"] = True
                            p["_botBlockUntil"] = now + 1.15
                            p["tacticalBlocks"] = int(p.get("tacticalBlocks", 0)) + 1
                            stats["tacticalBlocks"] = int(stats.get("tacticalBlocks", 0)) + 1
                            p["autoFarmStatus"] = f"🛡️ Taktischer Schildblock gegen {target_mob['name']}!"
                            p["_botTradeStatusUntil"] = now + 2.2
                        else:
                            p["dodgeUntil"] = now + 0.85
                            p["tacticalDodges"] = int(p.get("tacticalDodges", 0)) + 1
                            stats["tacticalDodges"] = int(stats.get("tacticalDodges", 0)) + 1
                            if is_bot_player:
                                # Kiting-Schritt für Schamanen- & Schattenjäger-Bots auf sichere Distanz
                                away_ang = math.atan2(p["pos_x"] - target_mob["x"], p["pos_z"] - target_mob["z"]) + random.uniform(-0.55, 0.55)
                                kite_step = 3.2 if c_id == "shaman" else 2.4
                                p["pos_x"] = max(-1350.0, min(1350.0, p["pos_x"] + math.sin(away_ang) * kite_step))
                                p["pos_z"] = max(-1350.0, min(1350.0, p["pos_z"] + math.cos(away_ang) * kite_step))
                                p["dest_x"] = p["pos_x"]
                                p["dest_z"] = p["pos_z"]
                            p["autoFarmStatus"] = f"💨 Taktisches Ausweichen gegen {target_mob['name']}!"
                            p["_botTradeStatusUntil"] = now + 2.2

            if now >= float(p.get("_botTradeStatusUntil", 0.0) or 0.0):
                p["autoFarmStatus"] = f"{prefix_ico}Bekämpfe {target_mob['name']} ({int((target_mob['hp']/target_mob['maxHp'])*100)}%){reward_pct_tag}"

            # Automatisch Fähigkeiten einsetzen (nutzt gelernte Bot-Synergien aus bot_knowledge_base.json & Evolution v5.0)
            if af.get("autoSkills", True) and (now - p.get("lastSkillCastTime", 0.0) >= 2.1):
                doc_skills_af = self.get_player_doctrine_skills(p)
                active_buffs = p.get("activeBuffs", {})

                # Gelernte Entdeckung (EisensturmBot & VeyronBot): Vorab-Aktivierung von Haupt-Buffs (Aura / Verzauberte Klinge / Drachenhilfe / Starker Körper)
                # auch bei berittenem Kampf (kurzes Absteigen -> Buff -> sofortiges Aufsitzen)
                if p.get("active_mount"):
                    saved_mount = p["active_mount"]
                    for sk in doc_skills_af:
                        if sk.get("type") != "buff" or int(p.get("skills", {}).get(sk["id"], 0)) <= 0:
                            continue
                        existing_buff = active_buffs.get(sk["id"])
                        if existing_buff and float(existing_buff.get("expiresAt", 0.0)) > now + 1.5:
                            continue
                        cd_until = p["skillCooldowns"].get(sk["id"], 0.0)
                        if now >= cd_until and p["mp"] >= sk["mpCost"]:
                            p["active_mount"] = None
                            res_b = self.perform_player_skill(p["player_id"], sk["slot"], target_mob["id"])
                            p["active_mount"] = saved_mount
                            self.compute_player_combat_stats(p)
                            if isinstance(res_b, dict) and res_b.get("ok"):
                                if is_bot_player:
                                    self._record_bot_qa_telemetry(p, sk["id"], res_b, now)
                                return

                    # Ab Militärgaul (Lv. 50+) Reit-Skills nutzen (für Bots wegen Affen-Sperre auf Lv. 1 gesperrt)
                    m_data = self._ensure_player_mount_data(p)
                    if not is_bot_player and int(m_data.get("level", 1)) >= 50:
                        for h_sk in HORSE_SKILLS:
                            cd_until = p["skillCooldowns"].get(h_sk["id"], 0.0)
                            if now >= cd_until and p["mp"] >= h_sk["mpCost"]:
                                res = self.perform_player_skill(p["player_id"], h_sk["slot"], target_mob["id"])
                                if isinstance(res, dict) and res.get("ok"):
                                    return
                else:
                    # Selbstlernende Build- & Rotations-Evolution v6.0 (SSOT):
                    ordered_skills = list(doc_skills_af)
                    evo_v3 = p.get("evolutionV3") if is_bot_player else None
                    rot_order = (evo_v3 or {}).get("activeRotationOrder")
                    if not rot_order and use_bot_ai and bot_sys_data:
                        rot_order = bot_sys_data.get("activeRotationOrder")
                    if isinstance(rot_order, list) and rot_order:
                        order_map = {sid: idx for idx, sid in enumerate(rot_order)}
                        ordered_skills.sort(key=lambda s: order_map.get(s["id"], 99))
                    elif p.get("class_id") == "ninja":
                        ordered_skills.sort(
                            key=lambda s: (0 if s["id"] == "feather_walk" else (1 if s["id"] == "ambush" else 2))
                        )
                    for sk in ordered_skills:
                        if int(p.get("skills", {}).get(sk["id"], 0)) <= 0:
                            continue
                        if sk.get("type") == "buff":
                            existing_buff = active_buffs.get(sk["id"])
                            if existing_buff and float(existing_buff.get("expiresAt", 0.0)) > now + 1.5:
                                continue
                        cd_until = p["skillCooldowns"].get(sk["id"], 0.0)
                        if now >= cd_until and p["mp"] >= sk["mpCost"]:
                            if sk["type"] == "heal" and hp_pct > 70 and not any_party_member_hurt:
                                continue
                            res = self.perform_player_skill(p["player_id"], sk["slot"], target_mob["id"])
                            if isinstance(res, dict) and res.get("ok"):
                                if is_bot_player:
                                    self._record_bot_qa_telemetry(p, sk["id"], res, now)
                                return

            # Standardangriff im flüssigen 4er-Combo-Rhythmus
            atk_interval = 0.64 / max(0.80, min(1.45, p["computed"]["atkSpeed"]))
            if now - p.get("lastBasicAttack", 0.0) >= atk_interval:
                res_atk = self.perform_basic_attack(p["player_id"], target_mob["id"])
                if is_bot_player and isinstance(res_atk, dict) and res_atk.get("ok"):
                    self._record_bot_qa_telemetry(p, f"combo_{res_atk.get('comboStep', 1)}", res_atk, now)

    def _get_base_bot_friendship_table(self) -> dict:
        return {
            # Seiryu-Reich (Osten): Enge Freundschaften vs. distanziertere Bekannte (6 Bots)
            tuple(sorted(("bot_veyron_warrior", "bot_aurelia_shaman"))): 96,
            tuple(sorted(("bot_nachtklinge_ninja", "bot_lyra_ninja"))): 91,
            tuple(sorted(("bot_veyron_warrior", "bot_eisensturm_mounted"))): 88,
            tuple(sorted(("bot_aurelia_shaman", "bot_lyra_ninja"))): 86,
            tuple(sorted(("bot_nachtklinge_ninja", "bot_malakor_sura"))): 85,
            tuple(sorted(("bot_aurelia_shaman", "bot_eisensturm_mounted"))): 82,
            tuple(sorted(("bot_veyron_warrior", "bot_lyra_ninja"))): 78,
            tuple(sorted(("bot_malakor_sura", "bot_aurelia_shaman"))): 74,
            tuple(sorted(("bot_malakor_sura", "bot_lyra_ninja"))): 72,
            tuple(sorted(("bot_veyron_warrior", "bot_malakor_sura"))): 68,
            tuple(sorted(("bot_eisensturm_mounted", "bot_lyra_ninja"))): 64,
            tuple(sorted(("bot_veyron_warrior", "bot_nachtklinge_ninja"))): 56,
            tuple(sorted(("bot_nachtklinge_ninja", "bot_aurelia_shaman"))): 52,
            tuple(sorted(("bot_malakor_sura", "bot_eisensturm_mounted"))): 48,
            tuple(sorted(("bot_nachtklinge_ninja", "bot_eisensturm_mounted"))): 38,
            # Kaeryu-Reich (Westen): Enge Freundschaften vs. distanziertere Bekannte (6 Bots)
            tuple(sorted(("bot_kassian_warrior", "bot_seraphina_shaman"))): 95,
            tuple(sorted(("bot_varon_sura", "bot_draven_sura"))): 92,
            tuple(sorted(("bot_kassian_warrior", "bot_donnerkeil_mounted"))): 89,
            tuple(sorted(("bot_schattenfalke_ninja", "bot_varon_sura"))): 86,
            tuple(sorted(("bot_seraphina_shaman", "bot_draven_sura"))): 85,
            tuple(sorted(("bot_schattenfalke_ninja", "bot_draven_sura"))): 84,
            tuple(sorted(("bot_seraphina_shaman", "bot_donnerkeil_mounted"))): 81,
            tuple(sorted(("bot_kassian_warrior", "bot_draven_sura"))): 79,
            tuple(sorted(("bot_varon_sura", "bot_seraphina_shaman"))): 75,
            tuple(sorted(("bot_kassian_warrior", "bot_varon_sura"))): 67,
            tuple(sorted(("bot_donnerkeil_mounted", "bot_draven_sura"))): 63,
            tuple(sorted(("bot_kassian_warrior", "bot_schattenfalke_ninja"))): 54,
            tuple(sorted(("bot_schattenfalke_ninja", "bot_seraphina_shaman"))): 50,
            tuple(sorted(("bot_varon_sura", "bot_donnerkeil_mounted"))): 46,
            tuple(sorted(("bot_schattenfalke_ninja", "bot_donnerkeil_mounted"))): 35,
        }

    def _get_bot_friendship_score(self, bid_a: str, bid_b: str, emp_a: str = "", emp_b: str = "") -> int:
        """Berechnet die dynamisch wachsende Freundschaft bzw. Feindschaft zwischen zwei Bots (-100 bis +99):
        - Bots aus anderen Reichen (Seiryu vs. Kaeryu) sind verfeindet (-100) und mögen sich nicht!
        - Innerhalb desselben Reichs wächst die Freundschaft durch gemeinsame Kills, Heil-/Buff-Assists und Handel."""
        if bid_a == bid_b:
            return 100
        if emp_a and emp_b and emp_a != emp_b:
            return -100
        pa = self.players.get(bid_a) or {}
        pb = self.players.get(bid_b) or {}
        ea = (emp_a or str(pa.get("empire", ""))).lower()
        eb = (emp_b or str(pb.get("empire", ""))).lower()
        if not ea:
            ea = "kaeryu" if any(k in bid_a for k in ("kassian", "schatten", "varon", "seraphina", "donner", "draven")) else "seiryu"
        if not eb:
            eb = "kaeryu" if any(k in bid_b for k in ("kassian", "schatten", "varon", "seraphina", "donner", "draven")) else "seiryu"
        if ea != eb:
            return -100
        pair_key = tuple(sorted((bid_a, bid_b)))
        base_table = self._get_base_bot_friendship_table()
        live_scores = getattr(self, "_bot_live_friendships", None)
        if not isinstance(live_scores, dict):
            live_scores = {k: float(v) for k, v in base_table.items()}
            self._bot_live_friendships = live_scores
        base_val = float(base_table.get(pair_key, 60))
        cur_val = float(live_scores.get(pair_key, base_val))
        return max(25, min(99, int(round(cur_val))))

    def _adjust_bot_friendship(self, bid_a: str, bid_b: str, delta: float, stat_key: str = ""):
        """Erhöht oder senkt den dynamischen Freundschaftswert zweier Bots desselben Reichs und zählt Interaktionen."""
        if not bid_a or not bid_b or bid_a == bid_b:
            return
        if not (str(bid_a).startswith("bot_") and str(bid_b).startswith("bot_")):
            return
        cur_sc = self._get_bot_friendship_score(bid_a, bid_b)
        if cur_sc < 0:
            return
        pair_key = tuple(sorted((bid_a, bid_b)))
        base_table = self._get_base_bot_friendship_table()
        base_val = float(base_table.get(pair_key, 60))
        live_scores = getattr(self, "_bot_live_friendships", None)
        if not isinstance(live_scores, dict):
            live_scores = {k: float(v) for k, v in base_table.items()}
            self._bot_live_friendships = live_scores
        new_val = max(max(25.0, base_val - 6.0), min(99.0, float(live_scores.get(pair_key, base_val)) + float(delta)))
        live_scores[pair_key] = new_val
        pair_stats = getattr(self, "_bot_pair_stats", None)
        if not isinstance(pair_stats, dict):
            pair_stats = {}
            self._bot_pair_stats = pair_stats
        st = pair_stats.setdefault(pair_key, {"sharedKills": 0, "assists": 0, "trades": 0})
        if stat_key in st:
            st[stat_key] = int(st.get(stat_key, 0)) + 1

    def _get_bot_route_sector(self, bot: dict) -> str:
        """Bestimmt die aktuelle Level-/Farmroute eines Bots (Gebiet 1 Nord vs. Gebiet 2 Süd & Sektor)."""
        x = float(bot.get("pos_x", 0.0))
        z = float(bot.get("pos_z", 0.0))
        if -55.0 <= z <= 55.0 and abs(abs(x) - 760.0) <= 95.0:
            return "bridge_west" if x < 0 else "bridge_east"
        ns = "map1_north" if z < 0.0 else "map2_south"
        ew = "west" if x < -260.0 else ("east" if x > 260.0 else "mid")
        return f"{ns}_{ew}"

    def _get_bot_route_sector_label(self, bot: dict) -> str:
        """Liefert den präzisen deutschen Sektor- & Routennamen anhand der echten Live-Koordinaten (pos_x, pos_z)."""
        x = float(bot.get("pos_x", 0.0))
        z = float(bot.get("pos_z", 0.0))
        if -65.0 <= z <= 65.0 and abs(abs(x) - 760.0) <= 105.0:
            return "🌉 West-Steinbrücke (-760 • Map 1↔2)" if x < 0 else "🌉 Ost-Steinbrücke (+760 • Map 1↔2)"
        if z < 0.0:
            if math.hypot(x - 820.0, z - (-780.0)) <= 165.0:
                return "🏰 Stadt Seiryu (Map 1 Nordost)"
            if math.hypot(x - (-820.0), z - (-780.0)) <= 165.0:
                return "🏰 Stadt Kaeryu (Map 1 Nordwest)"
            if z <= -520.0:
                if x > 220.0:
                    return "Map 1 • Nördliche Steppe Ost (Lv. 1–8)"
                if x < -220.0:
                    return "Map 1 • Nördliche Steppe West (Lv. 1–8)"
                return "Map 1 • Nördliches Hochland (Lv. 1–8)"
            if z <= -280.0:
                if x > 240.0:
                    return "Map 1 • Silberstrom-Wälder Ost (Lv. 9–15)"
                if x < -240.0:
                    return "Map 1 • Silberstrom-Wälder West (Lv. 9–15)"
                return "Map 1 • Bären- & Tiger-Haine (Lv. 9–15)"
            if x > 240.0:
                return "Map 1 • Eid-Grenzland Ost (Lv. 16–22)"
            if x < -240.0:
                return "Map 1 • Eid-Grenzland West (Lv. 16–22)"
            return "Map 1 • Zentrales Eid-Lager (Lv. 16–22)"
        else:
            if math.hypot(x - 0.0, z - 880.0) <= 185.0:
                return "🏯 Außenposten Bakra (Map 2 Süd)"
            if z < 360.0:
                if x > 220.0:
                    return "Map 2 • Anfangsgebiet Ost (Lv. 23–29)"
                if x < -220.0:
                    return "Map 2 • Anfangsgebiet West (Lv. 23–29)"
                return "Map 2 • Anfangsgebiet Zentrum (Lv. 23–29)"
            if x > 220.0:
                return "Map 2 • Östliches Schwarzwind-Tal (Lv. 30–38)"
            if x < -220.0:
                return "Map 2 • Westliches Schwarzwind-Tal (Lv. 30–38)"
            return "Map 2 • Südliches Riss-Tal Bakra (Lv. 30–38)"

    def _get_ideal_bot_hunting_anchor(self, bot: dict) -> Tuple[float, float]:
        """Liefert den optimalen Jagd-Anker (anchorX, anchorZ) strikt nach SSOT Teil I Abs. 2:
        Map 1 (z < 0): Lv. 1–8 -> Lv. 9–15 -> Lv. 16–22.
        Map 2 (z > 0): Sofortiger Gebietswechsel ab Level 23 (Lv. 23–29 Anfangsgebiet -> Lv. 30–38 Restgebiet)."""
        emp = str(bot.get("empire", "seiryu")).lower()
        lvl = int(bot.get("level", 1))
        sign = -1.0 if emp == "kaeryu" else 1.0
        if lvl < 5:
            return sign * 560.0, -690.0
        if lvl < 9:
            return sign * 320.0, -640.0
        if lvl < 16:
            return sign * 540.0, -390.0
        if lvl < 23:
            return sign * 260.0, -185.0
        if lvl < 30:
            return sign * 420.0, 225.0
        if lvl < 35:
            return sign * 410.0, 465.0
        return sign * 310.0, 625.0

    def _score_bot_equipment_item(self, bot: dict, item_or_tpl, plus_level: int = 0, bonuses: Optional[list] = None) -> float:
        """Bewertet ein Ausrüstungsteil (Waffe, Rüstung, Helm, Schild, Schuhe, Handschuhe, Schmuck, Spezial-Item)
        für die Klasse und Rolle eines Bots anhand der effektiven Werte (inkl. +Stufe, Basis-Tier & Boni)."""
        if not item_or_tpl:
            return -1.0
        if isinstance(item_or_tpl, dict):
            tpl_id = str(item_or_tpl.get("templateId") or item_or_tpl.get("id") or "")
            plus = int(item_or_tpl.get("plusLevel", item_or_tpl.get("plus", plus_level)) or 0)
            b_list = item_or_tpl.get("bonuses") if item_or_tpl.get("bonuses") is not None else (bonuses or [])
            eff = item_or_tpl.get("effectiveStats")
        else:
            tpl_id = str(item_or_tpl)
            plus = int(plus_level or 0)
            b_list = bonuses or []
            eff = None

        tpl = ITEM_TEMPLATES.get(tpl_id, {})
        if not tpl or tpl.get("type") != "equipment":
            return -1.0
        slot = tpl.get("slot")
        if not slot:
            return -1.0

        cls_id = str(bot.get("class_id", "warrior"))
        allowed_classes = tpl.get("classes")
        if allowed_classes and cls_id not in allowed_classes:
            return -1.0

        w_sub = str(tpl.get("weaponSubType") or "one_hand")
        if slot == "weapon":
            allowed_subs = CLASS_ALLOWED_WEAPONS.get(cls_id, ["one_hand"])
            if w_sub not in allowed_subs:
                return -1.0

        if not isinstance(eff, dict):
            eff = calculate_item_effective_stats(tpl_id, plus, b_list)

        atk_w = 1.45 if cls_id in ("warrior", "ninja") else (1.25 if cls_id == "sura" else 0.95)
        matk_w = 1.55 if cls_id in ("sura", "shaman") else 0.35

        score = (
            float(eff.get("atk", 0)) * atk_w
            + float(eff.get("magicAtk", 0)) * matk_w
            + float(eff.get("def", 0)) * 1.85
            + float(eff.get("hp", 0)) * 0.085
            + float(eff.get("critChance", 0)) * 4.5
            + float(eff.get("pierceChance", 0)) * 3.5
            + float(eff.get("atkSpeedPct", 0)) * 2.2
            + (float(eff.get("speedPct", 0)) + float(eff.get("moveSpeedPct", 0))) * 1.2
            + (float(eff.get("vsMonsterPct", 0)) + float(eff.get("vsMetinPct", 0)) + float(eff.get("vsBossPct", 0))) * 3.8
            + (float(eff.get("str", 0)) + float(eff.get("dex", 0)) + float(eff.get("int", 0)) + float(eff.get("vit", 0))) * 3.5
            + int(tpl.get("reqLevel", 1)) * 5.5
            + plus * 6.0
            + len(b_list) * 7.5
        )

        pid = str(bot.get("player_id", ""))
        if slot == "weapon":
            # Berittene Zweihand-Bots bevorzugen Zweihandwaffen, Einhand-Krieger bevorzugen Einhandwaffen, Schattenjäger bevorzugen Zwillingsdolche
            if ("mounted" in pid or "eisensturm" in pid or "donnerkeil" in pid) and cls_id == "warrior":
                if w_sub == "two_hand":
                    score *= 1.35
                else:
                    score *= 0.72
            elif cls_id == "warrior" and w_sub == "two_hand":
                score *= 0.82
            elif cls_id == "ninja" and w_sub == "dagger":
                score *= 1.18

        # Selbstlernende Build-Evolution v3.0: Extra-Synergie für klassenspezifische Wunsch-Boni beim Runenweber
        evo_v3 = bot.get("evolutionV3") if isinstance(bot, dict) else None
        desired_ids = set((evo_v3 or {}).get("desiredBonusIds") or [])
        if desired_ids and b_list:
            for b_ent in b_list:
                if isinstance(b_ent, dict) and b_ent.get("id") in desired_ids:
                    score += 12.5

        return round(score, 2)

    def _get_bot_evolution_v3_profile(self, bot: dict) -> dict:
        """Initialisiert und liefert das SSOT v6.0 Build-, Pet-, Boss-Dodge-, Stadt- & Rotations-Evolutionsprofil eines Bots."""
        cls_id = str(bot.get("class_id", "warrior"))
        profiles = {
            "warrior": {
                "buildName": "Krieger-SSOT v6.0 (STR/VIT • Aura/Starker Körper • DSS + Monster)",
                "desiredBonusIds": ["bonus_vs_monster", "bonus_dss", "bonus_str", "bonus_crit", "bonus_hp_absorb", "bonus_vs_metin", "bonus_hp"],
                "rotations": [
                    {"name": "Körper-Berserker", "order": ["sword_aura", "berserk", "whirlwind", "three_way_cut", "dash_strike", "sword_strike"]},
                    {"name": "AoE-Schwertwirbel", "order": ["sword_aura", "whirlwind", "three_way_cut", "dash_strike", "berserk", "strong_body"]},
                    {"name": "Mental-Bollwerk", "order": ["strong_body", "sword_aura", "whirlwind", "sword_strike", "dash_strike", "three_way_cut"]},
                    {"name": "Omni-Rissbrecher v6.0", "order": ["sword_aura", "berserk", "three_way_cut", "whirlwind", "sword_strike", "dash_strike"]},
                ],
            },
            "ninja": {
                "buildName": "Schattenjäger-SSOT v6.0 (DEX/VIT • Hinterhalt/Degenwirbel • Krit + Durchbohren)",
                "desiredBonusIds": ["bonus_vs_monster", "bonus_crit", "bonus_dex", "bonus_pierce", "bonus_dss", "bonus_atk_speed", "bonus_vs_metin"],
                "rotations": [
                    {"name": "Schatten-Assassine", "order": ["feather_walk", "ambush", "rolling_dagger", "fast_attack", "poison_cloud"]},
                    {"name": "Gift-Wirbel", "order": ["feather_walk", "poison_cloud", "rolling_dagger", "ambush", "fast_attack"]},
                    {"name": "Blitz-Kombo", "order": ["feather_walk", "fast_attack", "rolling_dagger", "ambush", "poison_cloud"]},
                    {"name": "Phantom-Exekutor v6.0", "order": ["feather_walk", "ambush", "fast_attack", "rolling_dagger", "poison_cloud"]},
                ],
            },
            "sura": {
                "buildName": "Runenkrieger-SSOT v6.0 (INT/VIT/STR • Verzauberte Klinge / Dunkler Stein)",
                "desiredBonusIds": ["bonus_vs_monster", "bonus_int", "bonus_dss", "bonus_fks", "bonus_crit", "bonus_hp_absorb", "bonus_vs_metin"],
                "rotations": [
                    {"name": "Klingen-Exorzist", "order": ["enchanted_blade", "dark_protection", "finger_strike", "dragon_swirl", "dark_orb"]},
                    {"name": "Abgrund-Wirbel", "order": ["enchanted_blade", "dragon_swirl", "finger_strike", "dark_orb", "dark_protection"]},
                    {"name": "Dunkler-Stein-Magie", "order": ["dark_protection", "enchanted_blade", "dark_orb", "finger_strike", "dragon_swirl"]},
                    {"name": "Runen-Overdrive v6.0", "order": ["enchanted_blade", "finger_strike", "dark_orb", "dragon_swirl", "dark_protection"]},
                ],
            },
            "shaman": {
                "buildName": "Seelenweber-SSOT v6.0 (INT/VIT • Hilfe des Drachen / Segen / Gebrüll)",
                "desiredBonusIds": ["bonus_int", "bonus_vs_monster", "bonus_fks", "bonus_crit", "bonus_vs_metin", "bonus_hp", "bonus_cast_speed"],
                "rotations": [
                    {"name": "Drachenzorn-Salve", "order": ["dragon_aid", "blessing", "dragon_roar", "flying_talisman", "cure"]},
                    {"name": "Gebrüll-Inferno", "order": ["dragon_aid", "dragon_roar", "flying_talisman", "blessing", "cure"]},
                    {"name": "Heil-Orakel", "order": ["blessing", "dragon_aid", "cure", "flying_talisman", "dragon_roar"]},
                    {"name": "Himmlische Resonanz v6.0", "order": ["dragon_aid", "blessing", "flying_talisman", "dragon_roar", "cure"]},
                ],
            },
        }
        prof = profiles.get(cls_id, profiles["warrior"])
        evo = bot.get("evolutionV3")
        if not isinstance(evo, dict) or not evo.get("rotations") or evo.get("version") != "v6.0_ssot_ultimate":
            rot0 = prof["rotations"][0]
            rot_stats = {
                str(i): {"name": r["name"], "kills": 0, "totalTtk": 0.0, "avgTtkSec": 0.0, "bestTtkSec": 99.9}
                for i, r in enumerate(prof["rotations"])
            }
            evo = {
                "version": "v6.0_ssot_ultimate",
                "generation": 1,
                "totalKillsEvaluated": 0,
                "activeRotationIdx": 0,
                "activeRotationName": rot0["name"],
                "activeRotationOrder": list(rot0["order"]),
                "rotations": prof["rotations"],
                "rotationStats": rot_stats,
                "lastKillTtkSec": 0.0,
                "avgTtkSec": 0.0,
                "bestTtkSec": 99.9,
                "desiredBonusBuild": prof["buildName"],
                "desiredBonusIds": list(prof["desiredBonusIds"]),
                "matchedBonusesCount": 0,
                "lockedOptimalBonuses": 0,
                "bonusSwitchedForBuild": 0,
            }
            bot["evolutionV3"] = evo
        else:
            evo["desiredBonusBuild"] = prof["buildName"]

        # Zähle aktuell angelegte Wunsch-Boni & versiegelte Optimal-Boni
        matched_cnt = 0
        locked_cnt = 0
        desired_set = set(evo.get("desiredBonusIds") or [])
        for eq_it in (bot.get("equipment") or {}).values():
            if not isinstance(eq_it, dict):
                continue
            if int(eq_it.get("lockedBonusIdx", -1)) >= 0:
                locked_cnt += 1
            for b_ent in eq_it.get("bonuses") or []:
                if isinstance(b_ent, dict) and b_ent.get("id") in desired_set:
                    matched_cnt += 1
        evo["matchedBonusesCount"] = matched_cnt
        evo["lockedOptimalBonuses"] = locked_cnt
        return evo

    def _update_bot_evolution_v3_on_kill(self, bot: dict, mob: dict, raw_ttk: float, now: float):
        """Misst die reale Kill-Zeit (TTK) eines Bots, bewertet die aktuelle Skill-Rotation und evolviert
        automatisch zur schnellsten Kombo-Reihenfolge."""
        if not str(bot.get("player_id", "")).startswith("bot_"):
            return
        evo = self._get_bot_evolution_v3_profile(bot)
        # Normalisiere TTK leicht bei Rissmonolithen/Bossen, damit Rotationen fair verglichen werden
        mob_scale_div = 3.2 if mob.get("kind") == "metin" else (2.5 if mob.get("isBoss") else (1.45 if mob.get("isElite") else 1.0))
        eff_ttk = round(max(0.85, min(45.0, raw_ttk / mob_scale_div)), 2)

        evo["totalKillsEvaluated"] = int(evo.get("totalKillsEvaluated", 0)) + 1
        evo["lastKillTtkSec"] = eff_ttk
        if eff_ttk < float(evo.get("bestTtkSec", 99.9) or 99.9):
            evo["bestTtkSec"] = eff_ttk

        prev_avg = float(evo.get("avgTtkSec", 0.0) or 0.0)
        evo["avgTtkSec"] = round(eff_ttk if prev_avg <= 0.0 else (prev_avg * 0.80 + eff_ttk * 0.20), 2)

        rot_idx = int(evo.get("activeRotationIdx", 0) or 0)
        rot_key = str(rot_idx)
        r_stats = evo.setdefault("rotationStats", {}).setdefault(
            rot_key, {"name": evo.get("activeRotationName", "Rotation"), "kills": 0, "totalTtk": 0.0, "avgTtkSec": 0.0, "bestTtkSec": 99.9}
        )
        r_stats["kills"] = int(r_stats.get("kills", 0)) + 1
        r_stats["totalTtk"] = round(float(r_stats.get("totalTtk", 0.0)) + eff_ttk, 2)
        r_stats["avgTtkSec"] = round(r_stats["totalTtk"] / max(1, r_stats["kills"]), 2)
        if eff_ttk < float(r_stats.get("bestTtkSec", 99.9) or 99.9):
            r_stats["bestTtkSec"] = eff_ttk

        # Alle 3 Kills evaluiert die Evolution v3.0 die schnellste Rotation (mit initialem Exploration-Durchlauf)
        rot_list = evo.get("rotations") or []
        if len(rot_list) >= 2 and evo["totalKillsEvaluated"] % 3 == 0:
            evo["generation"] = int(evo.get("generation", 1)) + 1
            untested = [
                i for i in range(len(rot_list))
                if int((evo["rotationStats"].get(str(i)) or {}).get("kills", 0)) < 2
            ]
            if untested:
                next_idx = untested[0]
            elif random.random() < 0.16:
                # 16% Exploration zur kontinuierlichen Überprüfung bei besserem Gear
                next_idx = (rot_idx + 1) % len(rot_list)
            else:
                # Exploitation: Wähle die Rotation mit der niedrigsten durchschnittlichen Kill-Zeit (TTK)!
                next_idx = min(
                    range(len(rot_list)),
                    key=lambda i: float((evo["rotationStats"].get(str(i)) or {}).get("avgTtkSec", 99.9) or 99.9),
                )
            chosen_rot = rot_list[next_idx]
            if next_idx != rot_idx:
                evo["activeRotationIdx"] = next_idx
                evo["activeRotationName"] = chosen_rot["name"]
                evo["activeRotationOrder"] = list(chosen_rot["order"])
                best_avg = (evo["rotationStats"].get(str(next_idx)) or {}).get("avgTtkSec", eff_ttk)
                bot["autoFarmStatus"] = f"🧬 Evolution Gen.{evo['generation']}: Rotation '{chosen_rot['name']}' aktiviert (Ø TTK {best_avg}s)!"
                bot["_botTradeStatusUntil"] = now + 4.5

    def _optimize_bot_runeweaver_bonuses_v3(self, bot: dict, now: float):
        """Selbstlernende Wunsch-Boni-Optimierung beim Runenweber (v3.0):
        Bots fügen fehlende Boni hinzu, versiegeln ihre gelernten Top-Wunsch-Boni mit Äthersiegel
        und würfeln schwache Boni mit dem Bonuswandler neu aus."""
        pid = str(bot.get("player_id", ""))
        if not pid.startswith("bot_"):
            return
        evo = self._get_bot_evolution_v3_profile(bot)
        desired_ids = list(evo.get("desiredBonusIds") or [])
        top_lock_ids = set(desired_ids[:4])
        desired_set = set(desired_ids)

        inv = bot.get("inventory") or []
        has_adder = any(isinstance(it, dict) and it.get("templateId") == "item_bonus_adder" for it in inv)
        has_orb = any(isinstance(it, dict) and it.get("templateId") == "item_blessing_orb" for it in inv)
        has_soul = any(isinstance(it, dict) and it.get("templateId") in ("item_soul_fragment", "mat_soul_stone") for it in inv)
        has_changer = any(isinstance(it, dict) and it.get("templateId") == "item_bonus_changer" for it in inv)
        has_seal = any(isinstance(it, dict) and it.get("templateId") == "item_aether_seal" for it in inv)

        if not (has_adder or has_orb or has_soul or has_changer or has_seal):
            return

        eq_map = bot.get("equipment") or {}
        for slot_k in ("weapon", "armor", "helmet", "shield", "bracelet", "necklace", "earrings", "shoes", "talisman", "belt"):
            eq_it = eq_map.get(slot_k)
            if not isinstance(eq_it, dict) or not eq_it.get("uid"):
                continue
            uid = eq_it["uid"]
            bonuses = eq_it.get("bonuses") or []
            locked_idx = int(eq_it.get("lockedBonusIdx", -1))

            if len(bonuses) < 4 and has_adder:
                ok_rw, _ = self.runeweaver_action(pid, uid, "add")
                if ok_rw:
                    self._get_bot_evolution_v3_profile(self.players.get(pid) or bot)
                    break
            elif len(bonuses) == 4 and has_orb:
                ok_rw, _ = self.runeweaver_action(pid, uid, "add5")
                if ok_rw:
                    self._get_bot_evolution_v3_profile(self.players.get(pid) or bot)
                    break
            elif 5 <= len(bonuses) < 7 and has_soul and int(bot.get("yang", 0)) >= 25000:
                ok_rw, _ = self.runeweaver_action(pid, uid, "add67")
                if ok_rw:
                    self._get_bot_evolution_v3_profile(self.players.get(pid) or bot)
                    break
            elif len(bonuses) >= 2:
                # Prüfe wie viele Wunsch-Boni bereits auf dem Item vorhanden sind
                matched_indices = [
                    idx for idx, b in enumerate(bonuses[:5])
                    if isinstance(b, dict) and b.get("id") in desired_set
                ]
                top_indices = [
                    idx for idx, b in enumerate(bonuses[:5])
                    if isinstance(b, dict) and b.get("id") in top_lock_ids
                ]
                # Versiegle den besten Wunsch-Bonus mit Äthersiegel vor dem Weiter-Switchen!
                if top_indices and locked_idx < 0 and has_seal:
                    best_lock_idx = top_indices[0]
                    ok_l, _ = self.runeweaver_action(pid, uid, "lock", lock_idx=best_lock_idx)
                    if ok_l:
                        locked_b_name = bonuses[best_lock_idx].get("name", "Wunsch-Bonus")
                        ref_b = self.players.get(pid) or bot
                        ref_b["autoFarmStatus"] = f"🔒 Runenweber-Evolution: '{locked_b_name}' auf {eq_it.get('name', slot_k)} versiegelt!"
                        ref_b["_botTradeStatusUntil"] = now + 4.5
                        self._get_bot_evolution_v3_profile(ref_b)
                        break

                # Wenn weniger als 2 Wunsch-Boni vorhanden sind, mit Bonuswandler gezielt nach Wunsch-Boni switchen!
                if len(matched_indices) < 2 and has_changer:
                    ok_r, _ = self.runeweaver_action(pid, uid, "reroll")
                    if ok_r:
                        ref_b = self.players.get(pid) or bot
                        evo_ref = self._get_bot_evolution_v3_profile(ref_b)
                        evo_ref["bonusSwitchedForBuild"] = int(evo_ref.get("bonusSwitchedForBuild", 0)) + 1
                        ref_b["autoFarmStatus"] = f"🔮 Runenweber-Evolution ({evo_ref['desiredBonusBuild']}): Boni auf {eq_it.get('name', slot_k)} optimiert!"
                        ref_b["_botTradeStatusUntil"] = now + 4.5
                        break

    def _apply_shaman_party_buffs_to_ally(self, helper: dict, ally: dict, now: float, force_heal: bool = False) -> bool:
        """Wirkt gezielte Schamanen-Gruppenbuffs (Hilfe des Drachen + Segen) sowie Heilung (Kurieren)
        auf ein Gruppenmitglied (insbesondere menschliche Spieler!)."""
        if not helper or not ally or ally.get("isDead"):
            return False
        is_shaman = helper.get("class_id") == "shaman"
        buffs = ally.setdefault("activeBuffs", {})
        applied_any = False

        if is_shaman:
            # 1. Hilfe des Drachen (+30% AW, +15% Krit, +20% Tempo für 60s)
            dh = buffs.get("dragon_help")
            if not dh or float(dh.get("expiresAt", 0.0)) < now + 15.0 or force_heal:
                buffs["dragon_help"] = {
                    "id": "dragon_help",
                    "name": f"Hilfe des Drachen ({helper['name']})",
                    "icon": "🐉",
                    "color": "#f59e0b",
                    "atkPct": 30.0,
                    "magicAtkPct": 30.0,
                    "speedPct": 20.0,
                    "critPct": 15.0,
                    "atkMult": 1.30,
                    "defMult": 1.0,
                    "speedMult": 1.20,
                    "critBonus": 15.0,
                    "expiresAt": now + 65.0,
                }
                applied_any = True

            # 2. Segen (+35% DEF für 60s)
            db_buff = buffs.get("dragon_blessing")
            if not db_buff or float(db_buff.get("expiresAt", 0.0)) < now + 15.0 or force_heal:
                buffs["dragon_blessing"] = {
                    "id": "dragon_blessing",
                    "name": f"Segen ({helper['name']})",
                    "icon": "✨",
                    "color": "#fde047",
                    "defPct": 35.0,
                    "atkMult": 1.0,
                    "defMult": 1.35,
                    "speedMult": 1.0,
                    "critBonus": 0.0,
                    "expiresAt": now + 65.0,
                }
                applied_any = True
        elif force_heal:
            # Falls kein Schamane in der Gruppe ist, gewähren Kampfgefährten auf Befehl einen Gruppen-Schlachtruf!
            buffs["party_battle_cry"] = {
                "id": "party_battle_cry",
                "name": f"Gruppen-Schlachtruf ({helper['name']})",
                "icon": "🛡️",
                "color": "#38bdf8",
                "atkPct": 18.0,
                "magicAtkPct": 18.0,
                "defPct": 22.0,
                "speedPct": 12.0,
                "critPct": 8.0,
                "atkMult": 1.18,
                "defMult": 1.22,
                "speedMult": 1.12,
                "critBonus": 8.0,
                "expiresAt": now + 45.0,
            }
            applied_any = True

        if applied_any:
            self.compute_player_combat_stats(ally)
            self._emit_combat_event(
                ally["map_id"],
                "skill_buff",
                ally["pos_x"],
                ally["pos_z"],
                {
                    "playerId": ally["player_id"],
                    "skillId": "dragon_help" if is_shaman else "iron_body",
                    "skillName": "Hilfe des Drachen & Segen" if is_shaman else "Gruppen-Schlachtruf",
                    "color": "#fde047" if is_shaman else "#38bdf8",
                },
            )

        ally_hp_pct = (float(ally.get("hp", 1)) / max(1.0, float(ally.get("max_hp", 1)))) * 100.0
        if force_heal or ally_hp_pct < 82.0:
            heal_amt = int(ally["max_hp"] * (0.40 if is_shaman else 0.25))
            ally["hp"] = min(ally["max_hp"], int(ally["hp"]) + heal_amt)
            self._emit_combat_event(
                ally["map_id"],
                "heal",
                ally["pos_x"],
                ally["pos_z"],
                {"playerId": ally["player_id"], "amount": heal_amt, "skillId": "natures_heal"},
            )
            applied_any = True

        if applied_any:
            helper["autoFarmStatus"] = (
                f"🐉✨ Schamanen-Segen & Hilfe des Drachen auf {ally['name']} gewirkt!"
                if is_shaman
                else f"🛡️ Gruppen-Unterstützung für {ally['name']} aktiv!"
            )
            helper["_botTradeStatusUntil"] = now + 4.5
        return applied_any

    def _auto_equip_best_inventory_items_for_bot(self, bot: dict, now: Optional[float] = None) -> List[str]:
        """Prüft alle Ausrüstungs-Slots eines Bots und legt automatisch jedes bessere Item
        aus dem Inventar an, für das das Charakter-Level ausreicht."""
        if not bot:
            return []
        pid = str(bot.get("player_id", ""))
        if not pid.startswith("bot_"):
            return []

        p_lvl = int(bot.get("level", 1))
        inv = list(bot.get("inventory") or [])
        if not inv:
            return []

        best_by_slot: Dict[str, Tuple[float, dict]] = {}
        for it in inv:
            if not isinstance(it, dict) or not it.get("uid"):
                continue
            if it.get("equippedSlot") or it.get("equipped_slot") or it.get("reservedShopId") or it.get("reserved_shop_id"):
                continue
            tpl_id = str(it.get("templateId") or it.get("id") or "")
            tpl = ITEM_TEMPLATES.get(tpl_id, {})
            if tpl.get("type") != "equipment":
                continue
            slot = tpl.get("slot") or it.get("slot")
            if not slot:
                continue
            req_lvl = int(tpl.get("reqLevel", it.get("reqLevel", 1)) or 1)
            if req_lvl > p_lvl:
                continue
            cand_score = self._score_bot_equipment_item(bot, it)
            if cand_score <= 0:
                continue
            prev_best = best_by_slot.get(slot)
            if prev_best is None or cand_score > prev_best[0]:
                best_by_slot[slot] = (cand_score, it)

        if not best_by_slot:
            return []

        equipped_names = []
        eq_map = bot.get("equipment") or {}
        for slot, (cand_score, cand_item) in best_by_slot.items():
            cur_eq = eq_map.get(slot)
            if cur_eq and cur_eq.get("uid") == cand_item.get("uid"):
                continue
            cur_score = self._score_bot_equipment_item(bot, cur_eq) if cur_eq else -1.0
            if cand_score > cur_score + 4.5:
                ok, _msg = self.use_or_open_inventory_item(pid, cand_item["uid"], target_slot=slot)
                if ok:
                    plus_v = int(cand_item.get("plusLevel", 0) or 0)
                    lbl = f"{cand_item.get('name', cand_item.get('templateId'))}{f' +{plus_v}' if plus_v > 0 else ''}"
                    equipped_names.append(lbl)
                    eq_map = (self.players.get(pid) or bot).get("equipment") or {}

        if equipped_names:
            refreshed = self.players.get(pid) or bot
            af_st = self.ensure_autofarm_stats(refreshed.setdefault("autofarm", {}))
            af_st["itemsEquippedUpgrades"] = int(af_st.get("itemsEquippedUpgrades", 0)) + len(equipped_names)
            refreshed["autoFarmStatus"] = f"🛡️ Besseres EQ angelegt: {', '.join(equipped_names[:2])}"
            if now is not None:
                refreshed["_botTradeStatusUntil"] = now + 4.5
        return equipped_names

    BOT_RESET_LEVEL = 38

    def _reset_bot_on_level_cap(self, bot: dict, now: Optional[float] = None) -> dict:
        """Wenn ein Bot Level 38 erreicht, löscht er automatisch seinen Account inkl. aller Items/Shops,
        startet auf Level 1 mit einem neuen Charakter (nur +0 Start-EQ) neu und sammelt nahtlos weiter Lerndaten."""
        if not bot:
            return bot
        bid = str(bot.get("player_id", ""))
        if not bid.startswith("bot_"):
            return bot
        now_ts = now if now is not None else time.time()

        # 1. Bisherige Langzeit-Telemetrie & gelernte Evolution v3 sichern und akkumulieren
        old_quests = bot.get("quests") if isinstance(bot.get("quests"), dict) else {}
        prev_life = old_quests.get("__bot_lifetime__") if isinstance(old_quests.get("__bot_lifetime__"), dict) else {}
        af_stats = (bot.get("autofarm") or {}).get("stats") or {}
        evo_v3 = self._get_bot_evolution_v3_profile(bot)

        rebirth_cycles = int(prev_life.get("rebirthCycles", bot.get("rebirthCycles", 0)) or 0) + 1
        preserved_meta = {
            "rebirthCycles": rebirth_cycles,
            "lastResetAt": now_ts,
            "lastResetTimeStr": time.strftime("%Y-%m-%d %H:%M:%S"),
            "lifetimeMonstersKilled": int(prev_life.get("lifetimeMonstersKilled", 0)) + int(af_stats.get("monstersKilled", 0)),
            "lifetimeMetinsDestroyed": int(prev_life.get("lifetimeMetinsDestroyed", 0)) + int(af_stats.get("metinsDestroyed", 0)),
            "lifetimeBossesSlain": int(prev_life.get("lifetimeBossesSlain", 0)) + int(af_stats.get("bossesSlain", 0)),
            "lifetimeExpEarned": int(prev_life.get("lifetimeExpEarned", 0)) + int(af_stats.get("expEarned", 0)),
            "lifetimeYangEarned": int(prev_life.get("lifetimeYangEarned", 0)) + int(af_stats.get("yangEarned", 0)),
            "lifetimeItemsEquipped": int(prev_life.get("lifetimeItemsEquipped", 0)) + int(af_stats.get("itemsEquippedUpgrades", 0)),
            "lifetimeBridgeCrossings": int(prev_life.get("lifetimeBridgeCrossings", 0)) + int(bot.get("bridgeCrossings", 0)),
            "lifetimePartySplits": int(prev_life.get("lifetimePartySplits", 0)) + int(bot.get("partySplits", af_stats.get("partySplits", 0))),
            "lifetimeEmpireSkirmishes": int(prev_life.get("lifetimeEmpireSkirmishes", 0)) + int(bot.get("empireSkirmishes", af_stats.get("empireSkirmishes", 0))),
            "lifetimeShopListings": int(prev_life.get("lifetimeShopListings", 0)) + int(bot.get("offlineShopListingsCreated", 0)),
            "lifetimeMarketPurchases": int(prev_life.get("lifetimeMarketPurchases", 0)) + int(bot.get("marketPurchases", 0)),
            "evolutionV3": evo_v3,
        }

        # 2. Aus eventuellen Gruppen & Handelsfenstern sauber austragen + Monster-Aggro lösen
        pty_id = bot.get("partyId")
        if pty_id and pty_id in self.parties:
            pty = self.parties[pty_id]
            if bid in (pty.get("memberIds") or []):
                pty["memberIds"].remove(bid)
            if len(pty.get("memberIds") or []) < 2:
                for rem_id in list(pty.get("memberIds") or []):
                    rp = self.players.get(rem_id)
                    if rp:
                        rp["partyId"] = None
                self.parties.pop(pty_id, None)
        for tr_id, tr in list(self.trades.items()):
            if bid in (tr.get("playerA"), tr.get("playerB"), tr.get("playerAId"), tr.get("playerBId")):
                self.trades.pop(tr_id, None)
        for m_agg in self.monsters.values():
            if m_agg.get("targetPlayerId") == bid:
                m_agg["targetPlayerId"] = None

        # 3. Datenbank-Reset: Alten Charakter + Items + Shops + Account löschen & frisch auf Level 1 anlegen
        fresh = self.db.reset_bot_account_fresh_level1(bid, preserved_meta=preserved_meta)
        emp = str(fresh.get("empire", bot.get("empire", "seiryu"))).lower()
        sign = -1.0 if emp == "kaeryu" else 1.0
        start_hunt_x = sign * 560.0 + random.uniform(-22.0, 22.0)
        start_hunt_z = -680.0 + random.uniform(-22.0, 22.0)

        fresh["online"] = True
        fresh["inWorld"] = True
        fresh["lastSeen"] = now_ts
        fresh["empire"] = emp
        fresh["map_id"] = "morgenwacht"
        fresh["pos_x"] = round(start_hunt_x, 2)
        fresh["pos_z"] = round(start_hunt_z, 2)
        fresh["rot_y"] = 1.35 if emp == "kaeryu" else -1.35
        fresh["isDead"] = False
        fresh["deadAt"] = 0.0
        fresh["targetId"] = None
        fresh["autoAttackTargetId"] = None
        fresh["autoFarmTargetId"] = None
        fresh["manualFocusTargetId"] = None
        fresh["moveTarget"] = None
        fresh["partyId"] = None
        fresh["activeTradeId"] = None
        fresh["skillCooldowns"] = {}
        fresh["activeBuffs"] = {}
        fresh["rebirthCycles"] = rebirth_cycles
        fresh["evolutionV3"] = evo_v3
        fresh["active_pet"] = "pet_fire_phoenix"
        fresh["active_mount"] = "mount_crystal_wolf" if "mounted" in bid else None

        af = fresh.setdefault("autofarm", {})
        af["enabled"] = True
        af["mode"] = "all"
        af["radius"] = 240
        af["anchorX"] = round(sign * 560.0, 1)
        af["anchorZ"] = -680.0
        af["autoPotion"] = True
        af["autoPotionHpPct"] = 70
        af["autoLoot"] = True
        af["autoSkills"] = True
        self.ensure_autofarm_stats(af)

        self._ensure_player_pet_data(fresh)
        self._ensure_player_mount_data(fresh)
        self.compute_player_combat_stats(fresh)
        fresh["hp"] = fresh["max_hp"]
        fresh["mp"] = fresh["max_mp"]
        fresh["routeSector"] = self._get_bot_route_sector(fresh)
        fresh["routeSectorLabel"] = self._get_bot_route_sector_label(fresh)
        fresh["autoFarmStatus"] = f"🔄 Lv.{self.BOT_RESET_LEVEL} erreicht -> Account neu erstellt! Starte Zyklus #{rebirth_cycles + 1} ab Level 1 (ohne Alt-Items)"
        fresh["_botTradeStatusUntil"] = now_ts + 8.0

        self.players[bid] = fresh
        self.db.save_player_state(fresh)

        self.add_chat_message(
            "KI-Evolution",
            f"🔄 {fresh['name']} hat Level {self.BOT_RESET_LEVEL} erreicht! Account & Items wurden gelöscht -> Neustart auf Level 1 (Zyklus #{rebirth_cycles + 1}) zur weiteren Datensammlung!",
            channel="system",
        )
        return fresh

    def _get_bot_quest_npc_task(self, bot: dict) -> Optional[dict]:
        """Prüft für einen Helden-Bot (KI v5.0), ob:
        1. Eine abgeschlossene Quest abgabebereit ist ('turn_in' -> physischer Gang zum NPC & Belohnung entgegennehmen), oder
        2. Eine neue Quest für das aktuelle Level beim NPC verfügbar ist ('accept' -> physischer Gang zum NPC & Quest annehmen)."""
        if not bot:
            return None
        b_lvl = int(bot.get("level", 1))
        b_emp = str(bot.get("empire", "seiryu")).lower()
        is_kaeryu = b_emp == "kaeryu"
        quests = bot.setdefault("quests", {})

        def _resolve_npc_coords_and_name(qtpl: dict) -> tuple[float, float, str]:
            raw_pos = qtpl.get("npcPos") or {"x": 816.5, "z": -733.5}
            base_x = abs(float(raw_pos.get("x", 816.5)))
            base_z = float(raw_pos.get("z", -733.5))
            if base_z > 100.0:
                nx = float(raw_pos.get("x", 0.0))
                nz = base_z
            else:
                nx = -base_x if is_kaeryu else base_x
                nz = base_z
            npc_nm = (
                qtpl.get("npcNameKaeryu") if is_kaeryu and qtpl.get("npcNameKaeryu")
                else (qtpl.get("npcNameSeiryu") if not is_kaeryu and qtpl.get("npcNameSeiryu") else qtpl.get("npcName", "Hauptmann Vaelen"))
            )
            return nx, nz, npc_nm

        # 1. Höchste Priorität: Fertige Quests beim NPC abgeben & Belohnung entgegennehmen!
        for qtpl in QUEST_TEMPLATES:
            if qtpl.get("mapId", "morgenwacht") != bot.get("map_id", "morgenwacht"):
                continue
            qid = qtpl["id"]
            qst = quests.get(qid)
            if not isinstance(qst, dict) or not qst.get("accepted"):
                continue
            if qst.get("completed") and not qtpl.get("repeatable", False):
                continue
            req_cnt = int(qtpl.get("required", 1))
            if int(qst.get("progress", 0)) >= req_cnt or qst.get("ready"):
                nx, nz, npc_nm = _resolve_npc_coords_and_name(qtpl)
                return {
                    "subAction": "turn_in",
                    "questId": qid,
                    "questTitle": qtpl["title"],
                    "npcId": qtpl.get("npcId", "npc_captain"),
                    "npcName": npc_nm,
                    "npcX": nx,
                    "npcZ": nz,
                    "rewardYang": int(qtpl.get("rewardYang", 1500)),
                    "rewardExp": int(qtpl.get("rewardExp", 800)),
                }

        # 2. Zweite Priorität: Neue verfügbare NPC-Quest beim Questgeber physisch annehmen!
        active_accepted_cnt = sum(
            1 for k, v in quests.items()
            if not str(k).startswith("__") and isinstance(v, dict) and v.get("accepted") and not v.get("completed")
        )
        if active_accepted_cnt >= 3:
            return None

        for qtpl in QUEST_TEMPLATES:
            if qtpl.get("mapId", "morgenwacht") != bot.get("map_id", "morgenwacht"):
                continue
            if int(qtpl.get("minLevel", 1)) > b_lvl:
                continue
            qid = qtpl["id"]
            qst = quests.get(qid)
            if isinstance(qst, dict) and (qst.get("accepted") or (qst.get("completed") and not qtpl.get("repeatable", False))):
                continue
            prereq_id = qtpl.get("prereqQuestId")
            if prereq_id:
                pre_st = quests.get(prereq_id)
                if not isinstance(pre_st, dict) or not pre_st.get("completed"):
                    continue
            nx, nz, npc_nm = _resolve_npc_coords_and_name(qtpl)
            return {
                "subAction": "accept",
                "questId": qid,
                "questTitle": qtpl["title"],
                "npcId": qtpl.get("npcId", "npc_captain"),
                "npcName": npc_nm,
                "npcX": nx,
                "npcZ": nz,
            }
        return None

    def _tick_bot_town_errand(self, bot: dict, now: float) -> bool:
        """KI v5.0 Physischer Stadtrundgang & NPC-Quest-Gang:
        Bot reitet durch das Stadttor in seine Heimatstadt (Seiryu, Kaeryu oder Bakra),
        läuft physisch zu:
        0. Quest-NPCs (Hauptmann Vaelen, Biologe Aurelius, Späher Kaelen, Heilerin Aldric, Runenweberin Seraphina etc.) zur Quest-Annahme & Belohnungs-Abholung,
        1. Dorfschmied (+Upgrade +1 bis +9),
        2. Seelenweberin (1.–7. Boni) und
        3. Gemischtwarenhändlerin / Marktplatz (Beute verkaufen, Tränke & Umhänge kaufen)
        und kehrt danach gestärkt ins Jagdgebiet zurück."""
        errand = bot.get("townErrand")
        if not isinstance(errand, dict):
            return False

        if self._is_bot_fighting_monolith_or_boss(bot):
            bot.pop("townErrand", None)
            return False

        b_emp = str(bot.get("empire", "seiryu")).lower()
        in_south = float(bot.get("pos_z", -400.0)) > 120.0
        if in_south:
            town_name = "Bakra-Siedlung"
            npcs = {
                "blacksmith": (-16.0, 864.0, "Dorfschmied Bakra"),
                "runeweaver": (16.0, 864.0, "Seelenweberin Bakra"),
                "merchant": (0.0, 856.0, "Marktplatz Bakra"),
            }
        elif b_emp == "kaeryu":
            town_name = "Kaeryu-Stadt"
            npcs = {
                "blacksmith": (-804.0, -764.0, "Dorfschmied Garon"),
                "runeweaver": (-834.0, -764.0, "Seelenweberin Lyra"),
                "merchant": (-820.0, -756.0, "Händlerin Yuna & Markt"),
            }
        else:
            town_name = "Seiryu-Stadt"
            npcs = {
                "blacksmith": (804.0, -764.0, "Dorfschmied Garon"),
                "runeweaver": (834.0, -764.0, "Seelenweberin Lyra"),
                "merchant": (820.0, -756.0, "Händlerin Yuna & Markt"),
            }

        stage = str(errand.get("stage", "quest_npc"))
        af = bot.setdefault("autofarm", {})

        # STUFE 0: Physischer Gang zum Quest-NPC (Quest annehmen & Belohnung entgegennehmen!)
        if stage == "quest_npc":
            q_task = errand.get("questTask") or self._get_bot_quest_npc_task(bot)
            if not q_task:
                if errand.get("questOnly"):
                    bot["townVisits"] = int(bot.get("townVisits", 0)) + 1
                    bot["_lastTownErrandCompletedAt"] = now
                    bot.pop("townErrand", None)
                    ix, iz = self._get_ideal_bot_hunting_anchor(bot)
                    af["anchorX"] = ix
                    af["anchorZ"] = iz
                    return False
                errand["stage"] = "blacksmith"
                errand["arrivedAt"] = 0.0
                stage = "blacksmith"
            else:
                errand["questTask"] = q_task
                tx = float(q_task["npcX"])
                tz = float(q_task["npcZ"])
                npc_label = str(q_task["npcName"])
                q_title = str(q_task["questTitle"])
                q_sub = str(q_task["subAction"])
                af["anchorX"] = tx
                af["anchorZ"] = tz
                bot["targetId"] = None
                bot["autoFarmTargetId"] = None
                bot["manualFocusTargetId"] = None

                d_npc = dist2d(float(bot["pos_x"]), float(bot["pos_z"]), tx, tz)
                if d_npc > 13.5:
                    if d_npc > 32.0 and not bot.get("active_mount"):
                        bot["active_mount"] = af.get("mountId") or "mount_war_boar"
                        self.compute_player_combat_stats(bot)
                    elif d_npc <= 22.0 and bot.get("active_mount"):
                        # Am Stadtrand / vor dem NPC absteigen und physisch zu Fuß zum NPC gehen!
                        bot["active_mount"] = None
                        self.compute_player_combat_stats(bot)
                    act_verb = "Belohnung abholen" if q_sub == "turn_in" else "Quest annehmen"
                    bot["autoFarmStatus"] = f"📜 Gehe zu {npc_label} ({act_verb}: '{q_title}' • {int(d_npc)}m)..."
                    bot["_botTradeStatusUntil"] = now + 2.5
                    self._move_player_towards(bot, tx, tz, 0.05)
                    return True

                # Direkt vor dem Quest-NPC angekommen -> Absitzen, NPC anblicken & Quest annehmen / Belohnung entgegennehmen!
                if bot.get("active_mount"):
                    bot["active_mount"] = None
                    self.compute_player_combat_stats(bot)
                bot["vx"] = 0.0
                bot["vz"] = 0.0
                bot["rot_y"] = math.atan2(tx - float(bot["pos_x"]), tz - float(bot["pos_z"]))

                arrived_at = float(errand.get("arrivedAt", 0.0) or 0.0)
                if arrived_at <= 0.0:
                    errand["arrivedAt"] = now
                    arrived_at = now

                if q_sub == "turn_in":
                    bot["autoFarmStatus"] = f"🏆 Bei {npc_label}: Gebe '{q_title}' ab & nehme Belohnung entgegen..."
                else:
                    bot["autoFarmStatus"] = f"📜 Bei {npc_label}: Nehme Auftrag '{q_title}' persönlich an..."
                bot["_botTradeStatusUntil"] = now + 3.2

                if now - arrived_at >= 2.2:
                    res_q = self.handle_quest_action(bot["player_id"], q_sub, q_task["questId"])
                    af_st = self.ensure_autofarm_stats(af)
                    if q_sub == "turn_in" and res_q.get("ok"):
                        bot["questsTurnedIn"] = int(bot.get("questsTurnedIn", 0)) + 1
                        af_st["questsTurnedIn"] = int(af_st.get("questsTurnedIn", 0)) + 1
                        rew = res_q.get("rewards") or {}
                        self._emit_combat_event(
                            bot.get("map_id", "morgenwacht"),
                            "combat_feedback",
                            bot["pos_x"],
                            bot["pos_z"],
                            {
                                "playerId": bot["player_id"],
                                "feedbackType": "buff",
                                "text": f"🏆 Belohnung: +{rew.get('rewardYang', 1800)} Gold / +{rew.get('rewardExp', 800)} EXP!",
                                "color": "#fde047",
                            },
                        )
                    elif q_sub == "accept" and res_q.get("ok"):
                        bot["questsAccepted"] = int(bot.get("questsAccepted", 0)) + 1
                        af_st["questsAccepted"] = int(af_st.get("questsAccepted", 0)) + 1
                        self._emit_combat_event(
                            bot.get("map_id", "morgenwacht"),
                            "combat_feedback",
                            bot["pos_x"],
                            bot["pos_z"],
                            {
                                "playerId": bot["player_id"],
                                "feedbackType": "buff",
                                "text": f"📜 Quest angenommen: {q_title}!",
                                "color": "#38bdf8",
                            },
                        )
                    errand.pop("questTask", None)
                    errand["arrivedAt"] = 0.0
                    # Prüfe sofort, ob beim selben oder nächsten Stadt-NPC noch eine Quest abzugeben oder anzunehmen ist
                    next_q_task = self._get_bot_quest_npc_task(bot)
                    if next_q_task and int(errand.get("questsHandledInVisit", 0)) < 3:
                        errand["questTask"] = next_q_task
                        errand["questsHandledInVisit"] = int(errand.get("questsHandledInVisit", 0)) + 1
                    elif errand.get("questOnly"):
                        bot["townVisits"] = int(bot.get("townVisits", 0)) + 1
                        bot["_lastTownErrandCompletedAt"] = now
                        bot.pop("townErrand", None)
                        ix, iz = self._get_ideal_bot_hunting_anchor(bot)
                        af["anchorX"] = ix
                        af["anchorZ"] = iz
                        bot["autoFarmStatus"] = f"✅ NPC-Quest bei {npc_label} erledigt -> Auf ins Zielgebiet!"
                        bot["_botTradeStatusUntil"] = now + 4.0
                        self.db.save_player_state(bot)
                    else:
                        errand["stage"] = "blacksmith"
                return True

        if stage not in npcs:
            bot.pop("townErrand", None)
            return False

        tx, tz, npc_label = npcs[stage]
        af = bot.setdefault("autofarm", {})
        if now - float(errand.get("startedAt", now) or now) > 180.0:
            bot["_lastTownErrandCompletedAt"] = now
            bot.pop("townErrand", None)
            ix, iz = self._get_ideal_bot_hunting_anchor(bot)
            af["anchorX"] = ix
            af["anchorZ"] = iz
            bot["autoFarmStatus"] = f"✅ Stadtrundgang ({town_name}) beendet -> Reite ins Jagdgebiet!"
            return False
        af["anchorX"] = tx
        af["anchorZ"] = tz
        bot["targetId"] = None
        bot["autoFarmTargetId"] = None
        bot["manualFocusTargetId"] = None

        d_npc = dist2d(float(bot["pos_x"]), float(bot["pos_z"]), tx, tz)
        if d_npc > 16.0:
            if not bot.get("active_mount"):
                bot["active_mount"] = af.get("mountId") or "mount_war_boar"
                self.compute_player_combat_stats(bot)
            bot["autoFarmStatus"] = f"🏛️ Stadtrundgang ({town_name}): Reite zu {npc_label} ({int(d_npc)}m)..."
            bot["_botTradeStatusUntil"] = now + 2.5
            self._move_player_towards(bot, tx, tz, 0.05)
            return True

        # Vor dem NPC angekommen -> Absitzen und Aktion sichtbar ausführen
        if bot.get("active_mount"):
            bot["active_mount"] = None
            self.compute_player_combat_stats(bot)
        bot["vx"] = 0.0
        bot["vz"] = 0.0

        arrived_at = float(errand.get("arrivedAt", 0.0) or 0.0)
        if arrived_at <= 0.0:
            errand["arrivedAt"] = now
            arrived_at = now

        if stage == "blacksmith":
            bot["autoFarmStatus"] = f"🔨 Bei {npc_label} ({town_name}): Schmiede Ausrüstung & fasse Geiststeine..."
            bot["_botTradeStatusUntil"] = now + 3.0
            if now - arrived_at >= 2.6:
                bid_bs = bot["player_id"]
                inv_bs = list(bot.get("inventory") or [])
                has_segi = any(isinstance(i, dict) and i.get("templateId") == "scroll_blessing" and int(i.get("quantity", 1)) > 0 for i in inv_bs)
                has_metal = any(isinstance(i, dict) and i.get("templateId") == "item_magic_metal" and int(i.get("quantity", 1)) > 0 for i in inv_bs)
                upgraded_label = None
                attempts_done = 0
                for sl_k in ("weapon", "armor", "helmet", "shield", "bracelet", "necklace", "earrings", "shoes", "gloves", "belt", "talisman"):
                    if attempts_done >= 3:
                        break
                    eq_map_now = (self.players.get(bid_bs) or bot).get("equipment") or {}
                    eq_it = eq_map_now.get(sl_k)
                    if not isinstance(eq_it, dict) or not eq_it.get("uid"):
                        continue
                    cur_pl = int(eq_it.get("plusLevel", 0))
                    if cur_pl >= 9:
                        continue
                    req_bs = get_blacksmith_upgrade_req(eq_it.get("templateId", ""), cur_pl)
                    cur_bot_ref = self.players.get(bid_bs) or bot
                    if int(cur_bot_ref.get("yang", 0)) < int(req_bs.get("yang", 999999)):
                        continue
                    mat_req = req_bs.get("matId")
                    mat_qty = int(req_bs.get("matCount", 0) or 0)
                    if mat_req and mat_qty > 0:
                        owned_m = sum(
                            int(x.get("quantity", 1) or 1)
                            for x in (cur_bot_ref.get("inventory") or [])
                            if isinstance(x, dict) and x.get("templateId") == mat_req and not x.get("reservedShopId")
                        )
                        if owned_m < mat_qty:
                            continue
                    use_m = bool(has_metal and cur_pl >= 7)
                    use_s = bool((not use_m) and has_segi and cur_pl >= 5)
                    ok_up, msg_up, up_won = self.blacksmith_upgrade(
                        bid_bs, eq_it["uid"], use_blessing=use_s, use_magic_metal=use_m
                    )
                    attempts_done += 1
                    bot = self.players.get(bid_bs) or bot
                    bot["blacksmithUpgrades"] = int(bot.get("blacksmithUpgrades", 0)) + 1
                    if ok_up and up_won:
                        upgraded_label = f"{eq_it.get('name', 'Item')} +{cur_pl + 1}"
                        break

                # Geiststeine (+0 bis +4) ehrlich in Waffe oder Rüstung sockeln
                bot = self.players.get(bid_bs) or bot
                for it_st in list(bot.get("inventory") or []):
                    if isinstance(it_st, dict) and it_st.get("uid") and str(it_st.get("templateId", "")).startswith("stone_"):
                        ok_st, _ = self.use_or_open_inventory_item(bid_bs, it_st["uid"])
                        if ok_st:
                            bot = self.players.get(bid_bs) or bot
                            break

                if upgraded_label:
                    self._emit_combat_event(
                        bot.get("map_id", "morgenwacht"),
                        "combat_feedback",
                        bot["pos_x"],
                        bot["pos_z"],
                        {"playerId": bot["player_id"], "feedbackType": "buff", "text": f"🔨 Schmied: {upgraded_label}!", "color": "#fde047"},
                    )
                errand["stage"] = "runeweaver"
                errand["arrivedAt"] = 0.0
            return True

        if stage == "runeweaver":
            bot["autoFarmStatus"] = f"🔮 Bei {npc_label} ({town_name}): Veredele 1.–7. Ausrüstungs-Boni..."
            bot["_botTradeStatusUntil"] = now + 3.0
            if now - arrived_at >= 2.4:
                self._optimize_bot_runeweaver_bonuses_v3(bot, now=now)
                errand["stage"] = "merchant"
                errand["arrivedAt"] = 0.0
            return True

        # stage == "merchant": Ehrlich Beute verkaufen, Tränke/Umhänge gegen Gold nachkaufen & Truhen sicher öffnen!
        bot["autoFarmStatus"] = f"🛒 Bei {npc_label} ({town_name}): Verkaufe Beute & kaufe Tränke nach..."
        bot["_botTradeStatusUntil"] = now + 3.5
        if now - arrived_at >= 2.4:
            bid_m = bot["player_id"]
            b_lvl_m = int(bot.get("level", 1))
            sold_yang = 0
            for it in list(bot.get("inventory") or []):
                if not isinstance(it, dict) or not it.get("uid") or it.get("equippedSlot") or it.get("equipped_slot") or it.get("reservedShopId") or it.get("reserved_shop_id"):
                    continue
                tid_m = str(it.get("templateId", ""))
                tpl = ITEM_TEMPLATES.get(tid_m, {})
                if tpl.get("type") == "chest":
                    self.use_or_open_inventory_item(bid_m, it["uid"])
                    bot = self.players.get(bid_m) or bot
                    continue
                sell_this = False
                qty_m = max(1, int(it.get("quantity", 1) or 1))
                if tpl.get("type") == "equipment":
                    sl_k = tpl.get("slot", "weapon")
                    cur_eq = (bot.get("equipment") or {}).get(sl_k)
                    cand_sc = self._score_bot_equipment_item(bot, it)
                    cur_sc = self._score_bot_equipment_item(bot, cur_eq) if cur_eq else -1.0
                    if cand_sc <= cur_sc and int(it.get("plusLevel", 0)) < 6:
                        sell_this = True
                elif tid_m in ("mat_wolf_claw", "mat_bear_gall", "mat_tiger_hide") and b_lvl_m >= 23 and qty_m > 12:
                    sell_this = True
                if sell_this:
                    val = max(25, int(tpl.get("sellPrice", 80)) * qty_m)
                    _rm_fn = getattr(self.db, "remove_inventory_item_by_uid", None) or getattr(self.db, "delete_item", None)
                    try:
                        _removed = bool(_rm_fn and _rm_fn(bid_m, it["uid"]))
                    except Exception:
                        _removed = False
                    if _removed:
                        sold_yang += val
            if sold_yang > 0:
                bot["yang"] = int(bot.get("yang", 0)) + sold_yang
                self.refresh_player_from_db(bid_m)
                bot = self.players.get(bid_m) or bot

            # Rote & Blaue Tränke sowie Grüne/Violette Tränke & Tapferkeitsumhänge ehrlich gegen Gold kaufen
            self._auto_restock_potions(bot, now=now, force=True, include_mp=True)
            bot = self.players.get(bid_m) or bot
            for shop_tid, min_have, buy_qty in (("potion_speed", 3, 5), ("potion_atk_speed", 3, 5), ("cape_bravery", 4, 5)):
                s_tpl = ITEM_TEMPLATES.get(shop_tid, {})
                b_price = int(s_tpl.get("buyPrice", 0) or 0)
                if b_price <= 0:
                    continue
                have_cnt = sum(
                    int(x.get("quantity", 1) or 1)
                    for x in (bot.get("inventory") or [])
                    if isinstance(x, dict) and x.get("templateId") == shop_tid
                )
                total_p = b_price * buy_qty
                if have_cnt < min_have and int(bot.get("yang", 0)) >= total_p + 2500:
                    ok_add, _ = self.db.add_item_to_inventory(bid_m, shop_tid, quantity=buy_qty)
                    if ok_add:
                        bot["yang"] = int(bot.get("yang", 0)) - total_p
                        self.refresh_player_from_db(bid_m)
                        bot = self.players.get(bid_m) or bot

            bot["townVisits"] = int(bot.get("townVisits", 0)) + 1
            bot["_lastTownErrandCompletedAt"] = now
            bot.pop("townErrand", None)
            ix, iz = self._get_ideal_bot_hunting_anchor(bot)
            af["anchorX"] = ix
            af["anchorZ"] = iz
            bot["autoFarmStatus"] = f"✅ Stadtrundgang ({town_name}) abgeschlossen (+{sold_yang} Gold) -> Reite ins Jagdgebiet!"
            bot["_botTradeStatusUntil"] = now + 4.5
            self.db.save_player_state(bot)
        return True

    def _tick_bot_party_and_trade_ai(self, now: float):
        """Koordiniert für alle aktiven Bots (KI v5.0):
        1. Sofortiges Annehmen von Gruppeneinladungen & intelligenter Spieler-Handel (echte Klassengegenstände + fairer Goldpreis).
        2. Physische Stadtrundgänge zu Dorfschmied, Seelenweberin & Marktplatz.
        3. Reichs-Feindschaft (Seiryu vs. Kaeryu) & dynamische Routen-Gruppen.
        4. Koordinierte Jagd auf Gebiets-Weltbosse, die 3 festen 15-Minuten-Kartenbosse & instabile/erwachte Rissmonolithen."""
        online_bots = [
            p
            for pid, p in self.players.items()
            if str(pid).startswith("bot_") and p.get("online") and p.get("inWorld") and not p.get("isDead")
        ]
        if not online_bots:
            return

        # 1. Eingehende Spieler-Einladungen (Gruppe & Handel) sofort beantworten & besseres EQ im Inventar automatisch anlegen
        for idx_b, bot in enumerate(list(online_bots)):
            bid = bot["player_id"]

            # ── Ausstehende Emote-Antworten feuern (Soziale KI) ──
            pending_emote = bot.get("_pendingEmoteReply")
            if isinstance(pending_emote, dict) and now >= float(pending_emote.get("at", 0.0) or 0.0):
                emote_text = str(pending_emote.get("emote", ""))
                if emote_text:
                    self.add_chat_message(str(bot.get("name", bid)), emote_text, "normal")
                bot.pop("_pendingEmoteReply", None)

            # ── Schamanen-Empathie: Stirbt ein Spieler in der Nähe oder hat wenig HP, hilft/trauert der Schamanen-Bot ──
            if str(bot.get("class_id", "")).lower() == "shaman" and (now - float(bot.get("_lastShamanSocialHelpAt", 0.0) or 0.0)) >= 25.0:
                bx_s = float(bot.get("pos_x", 0.0))
                bz_s = float(bot.get("pos_z", 0.0))
                for h_pid, h_p in self.players.items():
                    if str(h_pid).startswith("bot_") or not isinstance(h_p, dict) or not h_p.get("online") or not h_p.get("inWorld"):
                        continue
                    dist_s = dist2d(bx_s, bz_s, float(h_p.get("pos_x", 0.0)), float(h_p.get("pos_z", 0.0)))
                    if dist_s <= 18.0:
                        if h_p.get("isDead") or int(h_p.get("hp", 1)) <= 0:
                            bot["_lastShamanSocialHelpAt"] = now
                            bot["pos_x"] = round(float(h_p.get("pos_x", bx_s)) + 1.5, 1)
                            bot["pos_z"] = round(float(h_p.get("pos_z", bz_s)) + 1.5, 1)
                            self.add_chat_message(str(bot.get("name", bid)), f"*trauert um {h_p.get('name', 'den gefallenen Helden')} und spricht ein Segensgebet! 😢*", "normal")
                            break
                        elif int(h_p.get("hp", 100)) < int(h_p.get("max_hp", 100)) * 0.45:
                            bot["_lastShamanSocialHelpAt"] = now
                            heal_amt = max(150, int(int(h_p.get("max_hp", 500)) * 0.35))
                            h_p["hp"] = min(int(h_p.get("max_hp", 500)), int(h_p.get("hp", 1)) + heal_amt)
                            self.add_chat_message(str(bot.get("name", bid)), f"*wirkt Heilung & Drachensegen auf {h_p.get('name', 'dich')} (+{heal_amt} TP)! ✨*", "normal")
                            break

            if int(bot.get("level", 1)) >= self.BOT_RESET_LEVEL:
                bot = self._reset_bot_on_level_cap(bot, now=now)
                online_bots[idx_b] = bot
            bot_prof = GameDatabase.BOT_CANONICAL_PROFILES.get(bid)
            if bot_prof:
                bot["name"] = bot_prof["name"]
                bot["empire"] = bot_prof["empire"]
            b_emp = str(bot.get("empire", "seiryu")).lower()
            fighting_monolith = self._is_bot_fighting_monolith_or_boss(bot)
            # Reichs-Korridor-Schutz: Falls ein Bot zu weit in das feindliche Heimatland abgedriftet ist (und gerade KEINEN Monolithen/Boss bekämpft),
            # führe ihn auf seine Reichs-Route zurück
            if not fighting_monolith and not bot.get("townErrand"):
                if b_emp == "kaeryu" and float(bot.get("pos_x", 0.0)) > 240.0:
                    bot["pos_x"] = -480.0 + random.uniform(-60.0, 60.0)
                    af_corr = bot.setdefault("autofarm", {})
                    af_corr["anchorX"] = bot["pos_x"]
                    bot["targetId"] = None
                    bot["autoFarmTargetId"] = None
                elif b_emp == "seiryu" and float(bot.get("pos_x", 0.0)) < -240.0:
                    bot["pos_x"] = 480.0 + random.uniform(-60.0, 60.0)
                    af_corr = bot.setdefault("autofarm", {})
                    af_corr["anchorX"] = bot["pos_x"]
                    bot["targetId"] = None
                    bot["autoFarmTargetId"] = None
            bot["routeSector"] = self._get_bot_route_sector(bot)
            bot["routeSectorLabel"] = self._get_bot_route_sector_label(bot)
            self._get_bot_evolution_v3_profile(bot)
            bot_lvl = int(bot.get("level", 1))
            pty_cur = self.parties.get(bot.get("partyId")) if bot.get("partyId") else None
            has_human_pty = bool(pty_cur and any(not str(mid).startswith("bot_") for mid in pty_cur.get("memberIds", [])))

            # KI v5.0 Feld-Erkundung für aktive Quests (Spuren, Kräuter, Erzkarren, Wachturm)
            if not bot.get("townErrand") and (now - float(bot.get("_lastBotQuestFieldCheckAt", 0.0) or 0.0)) >= 14.0:
                bot["_lastBotQuestFieldCheckAt"] = now
                q_map = bot.setdefault("quests", {})
                for qtpl_f in QUEST_TEMPLATES:
                    qid_f = qtpl_f["id"]
                    qst_f = q_map.get(qid_f)
                    if isinstance(qst_f, dict) and qst_f.get("accepted") and not qst_f.get("completed") and not qst_f.get("ready"):
                        if qtpl_f.get("objectiveType") == "hybrid" or qtpl_f.get("category") in ("exploration", "escort_delivery", "gathering", "crafting"):
                            self.handle_quest_action(bid, "investigate", qid_f)
                            break

            # KI v5.0 Physischer Stadtrundgang & NPC-Quest-Gang prüfen / fortsetzen
            if bot.get("townErrand"):
                self._tick_bot_town_errand(bot, now)
            elif not has_human_pty and not fighting_monolith:
                active_errands_in_emp = sum(
                    1 for ob in online_bots if str(ob.get("empire", "")).lower() == b_emp and ob.get("townErrand")
                )
                q_npc_task = self._get_bot_quest_npc_task(bot) if (now - float(bot.get("_lastQuestErrandCheckAt", 0.0) or 0.0)) >= 18.0 else None
                if q_npc_task is not None:
                    bot["_lastQuestErrandCheckAt"] = now
                if q_npc_task and (q_npc_task.get("subAction") == "turn_in" or active_errands_in_emp < 2):
                    bot["townErrand"] = {
                        "stage": "quest_npc",
                        "questTask": q_npc_task,
                        "questOnly": (q_npc_task.get("subAction") == "accept" and (now - float(bot.get("_lastTownErrandCompletedAt", 0.0) or 0.0)) < 120.0),
                        "startedAt": now,
                        "arrivedAt": 0.0,
                    }
                    self._tick_bot_town_errand(bot, now)
                elif (now - float(bot.get("_lastTownErrandCompletedAt", 0.0) or 0.0)) >= 175.0:
                    unequipped_cnt = sum(
                        1
                        for it in (bot.get("inventory") or [])
                        if isinstance(it, dict) and not it.get("equippedSlot") and not it.get("equipped_slot")
                    )
                    if active_errands_in_emp < 1 and (unequipped_cnt >= 9 or int(bot.get("yang", 0)) >= 6500):
                        bot["townErrand"] = {"stage": "quest_npc", "startedAt": now, "arrivedAt": 0.0}
                        self._tick_bot_town_errand(bot, now)

            if not has_human_pty and not fighting_monolith and not bot.get("townErrand"):
                af_guard = bot.setdefault("autofarm", {})
                ideal_x, ideal_z = self._get_ideal_bot_hunting_anchor(bot)
                # SSOT Teil I Abs. 4: Aktive Server-Event-Teilnahme (passt Farmmodus dynamisch an lohnende Events an!)
                evt_now_id = str((getattr(self, "world_event", None) or {}).get("id", ""))
                if evt_now_id == "monolith_eruption" and bot_lvl >= 5:
                    af_guard["huntMetins"] = True
                    af_guard["prioritizeElites"] = True
                elif evt_now_id == "boss_hunt_frenzy" and bot_lvl >= 12:
                    af_guard["attackBosses"] = True
                    af_guard["prioritizeElites"] = True

                if bot_lvl < 23:
                    # Unter Level 23 strikt in Map 1 (z < 0: Lv. 1–8 -> 9–15 -> 16–22)
                    if float(af_guard.get("anchorZ", -420.0) or -420.0) > -60.0 or float(bot.get("pos_z", -420.0)) > 15.0:
                        af_guard["anchorX"] = ideal_x
                        af_guard["anchorZ"] = ideal_z
                else:
                    # Exakt mit Erreichen von Level 23 sofortiger Wechsel über die Reichs-Steinbrücke (±760) nach Map 2 (z > 0)!
                    if abs(float(af_guard.get("anchorZ", 0.0) or 0.0) - ideal_z) > 125.0 or float(af_guard.get("anchorZ", 0.0) or 0.0) < 120.0:
                        af_guard["anchorX"] = ideal_x
                        af_guard["anchorZ"] = ideal_z
                    if float(bot.get("pos_z", 0.0)) < 0.0 and not bot.get("_crossingToMap2"):
                        bot["_crossingToMap2"] = True
                        bot["targetId"] = None
                        bot["autoFarmTargetId"] = None
                        bot["bridgeCrossings"] = int(bot.get("bridgeCrossings", 0)) + 1
                        bot["autoFarmStatus"] = f"🌉 Lv.{bot_lvl} erreicht -> Gebietswechsel über Steinbrücke nach Map 2!"
                        bot["_botTradeStatusUntil"] = now + 5.0
                    elif float(bot.get("pos_z", 0.0)) > 40.0 and bot.get("_crossingToMap2"):
                        bot.pop("_crossingToMap2", None)
                        bot["routeSector"] = self._get_bot_route_sector(bot)
                        bot["routeSectorLabel"] = self._get_bot_route_sector_label(bot)

            if now - float(bot.get("_lastAutoEquipCheckAt", 0.0) or 0.0) >= 2.0:
                bot["_lastAutoEquipCheckAt"] = now
                self._auto_equip_best_inventory_items_for_bot(bot, now=now)

                # SSOT Teil I Abs. 7: Klassenspezifische Statuspunkte-Verteilung (STR, DEX, INT, VIT)
                if int(bot.get("stat_points", 0)) > 0:
                    cls_st = str(bot.get("class_id", "warrior"))
                    is_mental = "kassian" in bid or "donnerkeil" in bid
                    stat_cycle = (
                        ("vit", "str", "vit") if (cls_st == "warrior" and is_mental)
                        else ("str", "str", "vit") if cls_st == "warrior"
                        else ("dex", "dex", "vit") if cls_st == "ninja"
                        else ("int_stat", "int_stat", "vit", "str") if cls_st == "sura"
                        else ("int_stat", "int_stat", "vit")
                    )
                    while int(bot.get("stat_points", 0)) > 0:
                        tot_alloc = int(bot.get("str", 0)) + int(bot.get("dex", 0)) + int(bot.get("int_stat", 0)) + int(bot.get("vit", 0))
                        pick_st = stat_cycle[tot_alloc % len(stat_cycle)]
                        if int(bot.get(pick_st, 10)) >= 90:
                            pick_st = "vit" if int(bot.get("vit", 10)) < 90 else ("str" if cls_st != "shaman" else "dex")
                        ok_st_a, _ = self.allocate_stat_point(bid, pick_st, 1)
                        if not ok_st_a:
                            break

                # SSOT Teil I Abs. 7 & Teil II Abs. 3: Aktive Skills von 0 -> 20 (M1) nach Klassen-Build priorisieren,
                # danach ehrlich mit gedroppten Fertigkeitsbüchern (M1->G1), Seelensteinen (G1->P10) & Legendärem Seelenstein (L1) meistern!
                cdef_bot = CHARACTER_CLASSES.get(bot.get("class_id", "warrior"), CHARACTER_CLASSES["warrior"])
                evo_sk_order = (bot.get("evolutionV3") or {}).get("activeRotationOrder") or [s["id"] for s in cdef_bot.get("skills", [])]
                c_sk_map = {s["id"]: s for s in cdef_bot.get("skills", [])}
                prio_sk_ids = [sid for sid in evo_sk_order if sid in c_sk_map] + [s["id"] for s in cdef_bot.get("skills", []) if s["id"] not in evo_sk_order]

                while int(bot.get("skill_points", 0)) > 0:
                    upgraded_any_sk = False
                    # Erst alle Basis-Skills auf Stufe 1 freischalten, danach Haupt-Skill gezielt auf 20 (M1) ziehen!
                    unlocked_target = next(
                        (sid for sid in prio_sk_ids if not c_sk_map[sid].get("special") and int((bot.get("skills") or {}).get(sid, 0)) == 0),
                        None,
                    )
                    target_sk_id = unlocked_target or next(
                        (
                            sid for sid in prio_sk_ids
                            if (not c_sk_map[sid].get("special") or sid in (bot.get("skills") or {}))
                            and int((bot.get("skills") or {}).get(sid, 0)) < 20
                        ),
                        None,
                    )
                    if not target_sk_id:
                        break
                    ok_sk_u, _ = self.upgrade_skill_point(bid, target_sk_id, is_passive=False)
                    if not ok_sk_u:
                        break
                    upgraded_any_sk = True
                    if not upgraded_any_sk:
                        break

                for inv_fb in list(bot.get("inventory") or []):
                    if not isinstance(inv_fb, dict) or inv_fb.get("reservedShopId") or inv_fb.get("reserved_shop_id"):
                        continue
                    tid_fb = str(inv_fb.get("templateId", ""))
                    if tid_fb.startswith("fb_passive_"):
                        ps_target = tid_fb.replace("fb_passive_", "")
                        if int((bot.get("passives") or {}).get(ps_target, 0)) < 20:
                            self.read_passive_skill_book(bid, ps_target)
                            bot = self.players.get(bid) or bot
                            break
                    elif tid_fb.startswith("fb_") and tid_fb in ACTIVE_SKILL_BOOK_IDS:
                        act_sk = tid_fb[3:]
                        cur_sk_lv = int((bot.get("skills") or {}).get(act_sk, 0))
                        if act_sk in c_sk_map and 20 <= cur_sk_lv < 30:
                            self.read_skill_book(bid, act_sk)
                            bot = self.players.get(bid) or bot
                            break
                    elif tid_fb == "mat_soul_stone":
                        g_sk = next((sid for sid in prio_sk_ids if 30 <= int((bot.get("skills") or {}).get(sid, 0)) < 49), None)
                        if g_sk:
                            self.read_skill_book(bid, g_sk)
                            bot = self.players.get(bid) or bot
                            break
                    elif tid_fb == "mat_legendary_soul_stone":
                        p10_sk = next((sid for sid in prio_sk_ids if int((bot.get("skills") or {}).get(sid, 0)) == 49), None)
                        if p10_sk:
                            self.read_skill_book(bid, p10_sk)
                            bot = self.players.get(bid) or bot
                            break
                    elif tid_fb in ("book_skill", "chest_skill_books", "item_skill_unlock_scroll") and inv_fb.get("uid"):
                        self.use_or_open_inventory_item(bid, inv_fb["uid"])
                        bot = self.players.get(bid) or bot
                        break
            if now - float(bot.get("_lastRuneweaverEvoCheckAt", 0.0) or 0.0) >= 9.0:
                bot["_lastRuneweaverEvoCheckAt"] = now
                self._optimize_bot_runeweaver_bonuses_v3(bot, now=now)
            # SSOT Teil I Abs. 4: KEIN Gratis-Spawnen von Erweckungssteinen ('mat_monolith_shard' / 'mat_awakened_rift_core')!
            # Bots erfarmen Erweckungssteine zu 100% fair wie normale Spieler.
            if bot.get("pendingPartyInvite"):
                self.handle_party_action(bid, "accept", {})
            if bot.get("pendingTradeRequest"):
                self.handle_trade_action(bid, "accept", {})

            # KI v5.0 Intelligenter Spieler-Handel: Bot legt passende Klassen-Ausrüstung / Materialien ins Handelsfenster
            # und bezahlt dem Spieler einen fairen Marktpreis für angebotene Gegenstände!
            for tr in list(self.trades.values()):
                if bid in (tr.get("playerAId"), tr.get("playerBId")):
                    is_a = tr.get("playerAId") == bid
                    partner_id = tr.get("playerBId") if is_a else tr.get("playerAId")
                    partner_p = self.players.get(partner_id) or {}
                    partner_cls = partner_p.get("class_id", "warrior")
                    my_items_key = "itemsA" if is_a else "itemsB"
                    other_items_key = "itemsB" if is_a else "itemsA"
                    my_yang_key = "yangA" if is_a else "yangB"
                    my_lock_key = "lockedA" if is_a else "lockedB"
                    other_lock_key = "lockedB" if is_a else "lockedA"
                    my_conf_key = "confirmedA" if is_a else "confirmedB"

                    if not tr.get(my_lock_key):
                        my_offered_items = tr.get(my_items_key) or []
                        if len(my_offered_items) < 2:
                            offered_uids = {it_o.get("uid") for it_o in my_offered_items if isinstance(it_o, dict)}
                            for inv_it in list(bot.get("inventory") or []):
                                if not isinstance(inv_it, dict) or not inv_it.get("uid") or inv_it["uid"] in offered_uids:
                                    continue
                                if inv_it.get("equippedSlot") or inv_it.get("equipped_slot") or inv_it.get("reservedShopId") or inv_it.get("reserved_shop_id"):
                                    continue
                                tpl_tr = ITEM_TEMPLATES.get(inv_it.get("templateId", ""), {})
                                if not tpl_tr:
                                    continue
                                good_for_partner = False
                                if tpl_tr.get("type") == "equipment":
                                    allowed_c = tpl_tr.get("classes") or []
                                    if not allowed_c or partner_cls in allowed_c:
                                        good_for_partner = True
                                elif inv_it.get("templateId") in ("scroll_blessing", "mat_monolith_shard", "mat_awakened_rift_core", "item_bonus_adder", "item_bonus_changer", "mat_white_pearl"):
                                    good_for_partner = True
                                if good_for_partner:
                                    self.handle_trade_action(bid, "toggle_item", {"itemUid": inv_it["uid"]})
                                    break

                        other_offered_items = tr.get(other_items_key) or []
                        if other_offered_items:
                            fair_sum = 0
                            for o_it in other_offered_items:
                                if not isinstance(o_it, dict):
                                    continue
                                o_tpl = ITEM_TEMPLATES.get(o_it.get("templateId", ""), {})
                                base_p = max(400, int(o_tpl.get("sellPrice", 250)))
                                plus_l = int(o_it.get("plusLevel", 0))
                                bon_c = len(o_it.get("bonuses") or [])
                                fair_sum += int(base_p * (2.4 + plus_l * 0.85 + bon_c * 0.65))
                            offer_yang = min(int(bot.get("yang", 0) * 0.65), max(1500, fair_sum))
                            if offer_yang > 0 and int(tr.get(my_yang_key, 0)) != offer_yang:
                                self.handle_trade_action(bid, "set_yang", {"yang": offer_yang})
                        elif int(tr.get(my_yang_key, 0)) == 0 and int(bot.get("yang", 0)) >= 2500:
                            gift_yang = min(1800, int(bot["yang"] * 0.12))
                            self.handle_trade_action(bid, "set_yang", {"yang": gift_yang})

                    if tr.get(other_lock_key) and not tr.get(my_lock_key):
                        self.handle_trade_action(bid, "lock", {})
                    if tr.get("lockedA") and tr.get("lockedB") and not tr.get(my_conf_key):
                        self.handle_trade_action(bid, "confirm", {})

        # 2. Verfeindete Reiche (Seiryu vs. Kaeryu): Bots aus anderen Reichen mögen sich nicht!
        # Falls sie sich außerhalb der Hauptdörfer begegnen (z. B. an den Brücken oder in Gebiet 2 Süd), kommt es zum Scharmützel.
        for i, ba in enumerate(online_bots):
            for bb in online_bots[i + 1 :]:
                if ba["map_id"] != bb["map_id"] or ba.get("empire", "seiryu") == bb.get("empire", "seiryu"):
                    continue
                d_enemy = dist2d(ba["pos_x"], ba["pos_z"], bb["pos_x"], bb["pos_z"])
                if d_enemy <= 42.0 and not is_in_safe_zone(ba["map_id"], ba["pos_x"], ba["pos_z"]):
                    if now >= float(ba.get("_nextEmpireSkirmishAt", 0.0) or 0.0):
                        ba["_nextEmpireSkirmishAt"] = now + 18.0
                        bb["_nextEmpireSkirmishAt"] = now + 18.0
                        ba["empireSkirmishes"] = int(ba.get("empireSkirmishes", 0)) + 1
                        bb["empireSkirmishes"] = int(bb.get("empireSkirmishes", 0)) + 1
                        af_a = self.ensure_autofarm_stats(ba.setdefault("autofarm", {}))
                        af_b = self.ensure_autofarm_stats(bb.setdefault("autofarm", {}))
                        af_a["empireSkirmishes"] = int(af_a.get("empireSkirmishes", 0)) + 1
                        af_b["empireSkirmishes"] = int(af_b.get("empireSkirmishes", 0)) + 1
                        skirm_dmg = max(18, int(min(ba["max_hp"], bb["max_hp"]) * 0.06))
                        ba["hp"] = max(int(ba["max_hp"] * 0.35), ba["hp"] - skirm_dmg)
                        bb["hp"] = max(int(bb["max_hp"] * 0.35), bb["hp"] - skirm_dmg)
                        ba["autoFarmStatus"] = f"⚔️ Reichs-Feindschaft: Gefecht gegen {bb['name']} ({bb.get('empire','').capitalize()})!"
                        bb["autoFarmStatus"] = f"⚔️ Reichs-Feindschaft: Gefecht gegen {ba['name']} ({ba.get('empire','').capitalize()})!"
                        ba["_botTradeStatusUntil"] = now + 5.0
                        bb["_botTradeStatusUntil"] = now + 5.0
                        self._emit_combat_event(
                            ba["map_id"],
                            "hit",
                            (ba["pos_x"] + bb["pos_x"]) * 0.5,
                            (ba["pos_z"] + bb["pos_z"]) * 0.5,
                            {"attackerId": ba["player_id"], "targetId": bb["player_id"], "damage": skirm_dmg, "crit": True},
                        )

        # 3. Bestehende Bot-Gruppen prüfen: Nach ein paar gemeinsamen Monstern (oder wenn sich die Farmrouten trennen)
        # gehen die Bots wieder getrennte Wege! Beste Freunde bleiben länger zusammen (bis ~14 Monster), lose Bekannte nur 5–7 Monster.
        for pty_id, pty in list(self.parties.items()):
            member_ids = list(pty.get("memberIds") or [])
            # Falls ein echter menschlicher Spieler in der Gruppe ist, bleibt die Gruppe stabil bis der Spieler sie verlässt
            has_human = any(not str(mid).startswith("bot_") for mid in member_ids)
            if has_human:
                continue
            bot_members = [self.players.get(mid) for mid in member_ids if self.players.get(mid)]
            if len(bot_members) < 2:
                for bm in bot_members:
                    bm["partyId"] = None
                self.parties.pop(pty_id, None)
                continue

            leader_b = self.players.get(pty.get("leaderId")) or bot_members[0]
            min_friendship = 95
            for i_m, ma in enumerate(bot_members):
                for mb in bot_members[i_m + 1 :]:
                    f_sc = self._get_bot_friendship_score(ma["player_id"], mb["player_id"], ma.get("empire", ""), mb.get("empire", ""))
                    if f_sc < min_friendship:
                        min_friendship = f_sc

            max_monsters_together = 14 if min_friendship >= 82 else (9 if min_friendship >= 58 else 5)
            pty["maxMonstersTogether"] = max_monsters_together
            pty["avgFriendship"] = min_friendship
            pty["routeSector"] = self._get_bot_route_sector(leader_b)
            pty["routeSectorLabel"] = self._get_bot_route_sector_label(leader_b)
            slain_together = int(pty.get("monstersSlainTogether", 0))
            age_sec = now - float(pty.get("createdAt", now))

            # Während die Gruppe gemeinsam einen Gebiets-Weltboss, Elite-Boss oder instabilen/erwachten Rissmonolithen bekämpft,
            # trennt sich die Gruppe NICHT vorzeitig!
            fighting_world_boss_or_monolith = any(self._is_bot_fighting_monolith_or_boss(bm_chk) for bm_chk in bot_members)
            if fighting_world_boss_or_monolith:
                continue

            # Prüfe ob die Gruppe genug Monster zusammen besiegt hat -> Getrennte Wege gehen!
            if slain_together >= max_monsters_together or age_sec >= 135.0:
                for idx_split, bm in enumerate(bot_members):
                    bm["partyId"] = None
                    bm["_partySplitCooldownUntil"] = now + (16.0 if min_friendship >= 80 else 26.0)
                    bm["partySplits"] = int(bm.get("partySplits", 0)) + 1
                    bm["_lastSplitReason"] = f"Nach {slain_together}/{max_monsters_together} gemeinsamen Monstern getrennt"
                    af_bm = bm.setdefault("autofarm", {})
                    st_bm = self.ensure_autofarm_stats(af_bm)
                    st_bm["partySplits"] = int(st_bm.get("partySplits", 0)) + 1
                    # Jeder Bot schlägt nach der Trennung eine leicht versetzte eigene Route innerhalb seines Reichs-Korridors ein!
                    ang_sep = (idx_split * 2.094) + random.uniform(-0.35, 0.35)
                    bm_emp = str(bm.get("empire", "seiryu")).lower()
                    min_x_c = -1120.0 if bm_emp == "kaeryu" else -160.0
                    max_x_c = 160.0 if bm_emp == "kaeryu" else 1120.0
                    af_bm["anchorX"] = max(min_x_c, min(max_x_c, bm["pos_x"] + math.cos(ang_sep) * 74.0))
                    min_north_z = 140.0 if int(bm.get("level", 1)) >= 23 else -1180.0
                    max_south_z = 720.0 if int(bm.get("level", 1)) >= 23 else -80.0
                    af_bm["anchorZ"] = max(min_north_z, min(max_south_z, bm["pos_z"] + math.sin(ang_sep) * 56.0))
                    bm["autoFarmStatus"] = f"🚶 {slain_together} Monster gemeinsam erlegt – gehe wieder eigene Route!"
                    bm["_botTradeStatusUntil"] = now + 4.5
                self.parties.pop(pty_id, None)
                continue

            # Prüfe für einzelne Mitglieder, ob ihre Route zu weit vom Leader abweicht (> 95m oder anderes Gebiet Nord/Süd)
            for bm in list(bot_members):
                if bm["player_id"] == leader_b["player_id"]:
                    continue
                if bm.get("empire") != leader_b.get("empire") or dist2d(bm["pos_x"], bm["pos_z"], leader_b["pos_x"], leader_b["pos_z"]) > 98.0:
                    if bm["player_id"] in pty["memberIds"]:
                        pty["memberIds"].remove(bm["player_id"])
                    bm["partyId"] = None
                    bm["_partySplitCooldownUntil"] = now + 22.0
                    bm["partySplits"] = int(bm.get("partySplits", 0)) + 1
                    bm["autoFarmStatus"] = "🚶 Eigene Farmroute eingeschlagen (Gruppe verlassen)"
                    bm["_botTradeStatusUntil"] = now + 4.0

            if len(pty.get("memberIds", [])) < 2:
                for rem_id in list(pty.get("memberIds", [])):
                    rp = self.players.get(rem_id)
                    if rp:
                        rp["partyId"] = None
                self.parties.pop(pty_id, None)

        # 4. Dynamische Routen-Gruppenbildung: Wenn Bots desselben Reichs auf derselben Route/im selben Sektor farmen,
        # schließen sie sich für ein paar Monster zusammen (Freunde bevorzugen sich gegenseitig!).
        for i, ba in enumerate(online_bots):
            if now < float(ba.get("_partySplitCooldownUntil", 0.0) or 0.0):
                continue
            for bb in online_bots[i + 1 :]:
                if now < float(bb.get("_partySplitCooldownUntil", 0.0) or 0.0):
                    continue
                if ba["map_id"] != bb["map_id"] or ba.get("empire", "seiryu") != bb.get("empire", "seiryu"):
                    continue
                # Beide müssen im selben Nord-/Süd-Gebiet sein
                if (ba["pos_z"] < 0.0) != (bb["pos_z"] < 0.0):
                    continue
                f_score = self._get_bot_friendship_score(ba["player_id"], bb["player_id"], ba.get("empire", ""), bb.get("empire", ""))
                if f_score < 35:
                    continue
                # Beste Freunde gruppieren sich schon auf 88m Distanz auf derselben Route, andere erst bei <= 64m
                join_radius = 88.0 if f_score >= 80 else 64.0
                d_pair = dist2d(ba["pos_x"], ba["pos_z"], bb["pos_x"], bb["pos_z"])
                if d_pair > join_radius:
                    continue

                pty_a = self.parties.get(ba.get("partyId")) if ba.get("partyId") else None
                pty_b = self.parties.get(bb.get("partyId")) if bb.get("partyId") else None
                if pty_a and pty_b:
                    continue
                elif pty_a and len(pty_a.get("memberIds", [])) < 5:
                    if bb["player_id"] not in pty_a["memberIds"]:
                        pty_a["memberIds"].append(bb["player_id"])
                    bb["partyId"] = pty_a["id"]
                    bb["autoFarmStatus"] = f"🤝 Gleiche Route wie {ba['name']} ({f_score}% Freundschaft) – Gruppe gebildet!"
                    bb["_botTradeStatusUntil"] = now + 4.0
                elif pty_b and len(pty_b.get("memberIds", [])) < 5:
                    if ba["player_id"] not in pty_b["memberIds"]:
                        pty_b["memberIds"].append(ba["player_id"])
                    ba["partyId"] = pty_b["id"]
                    ba["autoFarmStatus"] = f"🤝 Gleiche Route wie {bb['name']} ({f_score}% Freundschaft) – Gruppe gebildet!"
                    ba["_botTradeStatusUntil"] = now + 4.0
                elif not pty_a and not pty_b:
                    leader = ba if (ba.get("class_id") == "warrior" or int(ba.get("level", 1)) >= int(bb.get("level", 1))) else bb
                    follower = bb if leader is ba else ba
                    pty_id = f"pty_route_{leader['empire']}_{int(now * 10) % 100000}_{leader['player_id'][-4:]}"
                    max_m = 14 if f_score >= 82 else (8 if f_score >= 58 else 5)
                    new_pty = {
                        "id": pty_id,
                        "leaderId": leader["player_id"],
                        "memberIds": [leader["player_id"], follower["player_id"]],
                        "createdAt": now,
                        "routeSector": self._get_bot_route_sector(leader),
                        "monstersSlainTogether": 0,
                        "maxMonstersTogether": max_m,
                        "avgFriendship": f_score,
                    }
                    self.parties[pty_id] = new_pty
                    leader["partyId"] = pty_id
                    follower["partyId"] = pty_id
                    leader["autoFarmStatus"] = f"🤝 Route geteilt mit {follower['name']} ({f_score}% Freundschaft | Ziel: {max_m} Monster)"
                    follower["autoFarmStatus"] = f"🤝 Route geteilt mit {leader['name']} ({f_score}% Freundschaft | Ziel: {max_m} Monster)"
                    leader["_botTradeStatusUntil"] = now + 4.5
                    follower["_botTradeStatusUntil"] = now + 4.5

        # 4b. Gemeinsame Gebiets-Weltboss-Jagd, 3 feste 15-Minuten-Kartenbosse & Instabile/Erwachte Rissmonolithen-Kooperation (KI v5.0):
        # Sobald ein Gebiets-Weltboss ('isRiftWorldBoss'), einer der 3 Kartenbosse ('isMapBossSlot'), ein Monolith-Elite-Boss
        # oder ein instabiler/erwachter Rissmonolith aktiv ist, schließen sich passende Bots in der Nähe zusammen!
        active_coop_targets = [
            m
            for m in self.monsters.values()
            if m.get("state") != "dead"
            and int(m.get("hp", 0)) > 0
            and (
                m.get("isRiftWorldBoss")
                or m.get("isMonolithEliteBoss")
                or m.get("isMapBossSlot")
                or (m.get("kind") == "metin" and m.get("monolithState") in ("instabil", "erwacht"))
            )
        ]
        if active_coop_targets:
            # Priorisiere: 1. Gebiets-Weltboss -> 2. Erwachter Rissmonolith -> 3. Instabiler Rissmonolith -> 4. Elite-Boss -> 5. Kartenboss
            # Innerhalb derselben Stufe werden bereits angeschlagene Ziele (niedrigere HP-Ratio) zuerst fertig getötet!
            active_coop_targets.sort(
                key=lambda m: (
                    0
                    if m.get("isRiftWorldBoss")
                    else (
                        1
                        if m.get("monolithState") == "erwacht"
                        else (2 if m.get("monolithState") == "instabil" else (3 if m.get("isMonolithEliteBoss") else 4))
                    ),
                    float(m.get("hp", 1)) / max(1.0, float(m.get("maxHp", 1))),
                    -int(m.get("level", 1)),
                )
            )
            already_rallied_ids = set()
            for coop_mob in active_coop_targets[:8]:
                self._rally_nearby_bots_for_monolith_or_world_boss(
                    coop_mob, now=now, already_rallied_ids=already_rallied_ids
                )

        # 5. Gegenseitige Hilfe in aktiven Gruppen (Aktive Spieler-Gruppenkommandos, Schamanen-Buffs, Fokusfeuer, Heilung & Aggro-Peel)
        for pty in list(self.parties.values()):
            m_list = [
                self.players.get(mid)
                for mid in pty.get("memberIds", [])[:8]
                if self.players.get(mid) and self.players[mid].get("online") and not self.players[mid].get("isDead")
            ]
            if len(m_list) < 2:
                continue
            leader_p = self.players.get(pty.get("leaderId"))
            if not leader_p or not leader_p.get("online") or leader_p.get("isDead"):
                leader_p = m_list[0]
                pty["leaderId"] = leader_p["player_id"]

            # Bevorzuge einen echten menschlichen Spieler als Kommandanten für aktive Gruppen-Taktiken
            human_member = next((mp for mp in m_list if not str(mp.get("player_id", "")).startswith("bot_")), None)
            commander_p = self.players.get(pty.get("tacticCommanderId")) if pty.get("tacticCommanderId") else None
            if not commander_p or not commander_p.get("online") or commander_p.get("isDead"):
                commander_p = human_member or leader_p

            active_tactic = str(pty.get("tactic", "free") or "free")
            tactic_tid = pty.get("tacticTargetId")
            if active_tactic in ("focus", "awaken_monolith", "hunt_boss"):
                if active_tactic == "focus":
                    cmd_tid = commander_p.get("targetId") or commander_p.get("manualFocusTargetId") or commander_p.get("autoFarmTargetId")
                    if cmd_tid and cmd_tid in self.monsters and self.monsters[cmd_tid].get("state") != "dead":
                        tactic_tid = cmd_tid
                        pty["tacticTargetId"] = cmd_tid
                t_mob = self.monsters.get(tactic_tid) if tactic_tid else None
                if not t_mob or t_mob.get("state") == "dead" or int(t_mob.get("hp", 0)) <= 0:
                    pty["tacticTargetId"] = None
                    t_mob = None
            else:
                t_mob = None

            leader_tid = leader_p.get("targetId") or leader_p.get("autoFarmTargetId")
            leader_mob = t_mob or (self.monsters.get(leader_tid) if leader_tid else None)

            for idx_m, helper in enumerate(m_list):
                if not str(helper.get("player_id", "")).startswith("bot_"):
                    continue

                # A) Aktives Gruppen-Kommando: 'Sammeln!' (rally) -> Sofort aufsitzen & direkt zum Spieler reiten!
                if active_tactic == "rally" and commander_p and helper["map_id"] == commander_p["map_id"]:
                    angle_off = idx_m * 1.0472
                    rx = commander_p["pos_x"] + math.cos(angle_off) * 3.8
                    rz = commander_p["pos_z"] + math.sin(angle_off) * 3.8
                    af_h = helper.get("autofarm")
                    if isinstance(af_h, dict):
                        af_h["anchorX"] = rx
                        af_h["anchorZ"] = rz
                    d_cmd = dist2d(helper["pos_x"], helper["pos_z"], commander_p["pos_x"], commander_p["pos_z"])
                    if d_cmd > 6.5:
                        if not helper.get("active_mount"):
                            helper["active_mount"] = (af_h or {}).get("mountId") or "mount_war_boar"
                            self.compute_player_combat_stats(helper)
                        helper["targetId"] = None
                        helper["autoFarmTargetId"] = None
                        helper["manualFocusTargetId"] = None
                        helper["autoFarmStatus"] = f"🐎 Kommando 'Sammeln!': Reite zu {commander_p['name']} ({int(d_cmd)}m)!"
                        helper["_botTradeStatusUntil"] = now + 2.5
                        self._move_player_towards(helper, rx, rz, 0.05)
                        continue

                # B) Aktives Gruppen-Kommando: 'Beschützt mich!' (protect) -> Eng beim Spieler bleiben, Aggro übernehmen & heilen/buffen!
                if active_tactic == "protect" and commander_p and helper["map_id"] == commander_p["map_id"]:
                    angle_off = idx_m * 1.2566
                    px = commander_p["pos_x"] + math.cos(angle_off) * 4.2
                    pz = commander_p["pos_z"] + math.sin(angle_off) * 4.2
                    af_h = helper.get("autofarm")
                    if isinstance(af_h, dict):
                        af_h["anchorX"] = px
                        af_h["anchorZ"] = pz
                    peeled_mob = None
                    for m in list(self.monsters.values()):
                        if m["mapId"] == commander_p["map_id"] and m["state"] != "dead" and m["kind"] != "metin":
                            d_mc = dist2d(m["x"], m["z"], commander_p["pos_x"], commander_p["pos_z"])
                            if m.get("targetPlayerId") == commander_p["player_id"] or d_mc <= 18.0:
                                if helper.get("class_id") in ("warrior", "sura", "ninja"):
                                    m["targetPlayerId"] = helper["player_id"]
                                    m["state"] = "chase"
                                peeled_mob = m
                                break
                    if peeled_mob is not None:
                        helper["targetId"] = peeled_mob["id"]
                        helper["autoFarmTargetId"] = peeled_mob["id"]
                        helper["manualFocusTargetId"] = peeled_mob["id"]
                        helper["autoFarmStatus"] = f"🛡️ Beschütze {commander_p['name']}: Übernehme {peeled_mob['name']}!"
                        helper["_botTradeStatusUntil"] = now + 3.0
                    if now - float(helper.get("_lastProtectBuffAt", 0.0) or 0.0) >= 6.5:
                        helper["_lastProtectBuffAt"] = now
                        self._apply_shaman_party_buffs_to_ally(helper, commander_p, now, force_heal=False)

                # C) Aktives Gruppen-Kommando: 'Fokusfeuer' / 'Riss erwecken!' / 'Boss-Jagd!' -> Alle Bots fokussieren sofort das Ziel!
                if active_tactic in ("focus", "awaken_monolith", "hunt_boss") and t_mob and t_mob.get("mapId") == helper["map_id"]:
                    if active_tactic == "awaken_monolith" and t_mob.get("kind") == "metin" and t_mob.get("monolithState", "schlafend") == "schlafend":
                        if dist2d(helper["pos_x"], helper["pos_z"], t_mob["x"], t_mob["z"]) <= 28.0:
                            self._try_bot_awaken_monolith(helper, t_mob, now=now)
                    helper["targetId"] = t_mob["id"]
                    helper["autoFarmTargetId"] = t_mob["id"]
                    helper["manualFocusTargetId"] = t_mob["id"]
                    af_h = helper.get("autofarm")
                    if isinstance(af_h, dict):
                        af_h["anchorX"] = t_mob["x"]
                        af_h["anchorZ"] = t_mob["z"]
                    cmd_lbl = "🔮 Riss erwecken" if active_tactic == "awaken_monolith" else ("👑 Boss-Jagd" if active_tactic == "hunt_boss" else "🎯 Fokusfeuer")
                    helper["autoFarmStatus"] = f"{cmd_lbl} ({commander_p['name']}): Greife {t_mob['name']} an!"
                    helper["_botTradeStatusUntil"] = now + 2.5

                # Halte die Gruppe im Normalbetrieb ('free') locker zusammen (nur wenn Distanz > 45m, damit kein 5m-Hin-und-Her-Pendeln entsteht!)
                if active_tactic == "free" and helper["player_id"] != leader_p["player_id"] and helper["map_id"] == leader_p["map_id"]:
                    d_to_leader = dist2d(helper["pos_x"], helper["pos_z"], leader_p["pos_x"], leader_p["pos_z"])
                    if d_to_leader > 45.0:
                        angle_off = idx_m * 1.2566
                        form_x = leader_p["pos_x"] + math.cos(angle_off) * 8.5
                        form_z = leader_p["pos_z"] + math.sin(angle_off) * 8.5
                        if not human_member and int(helper.get("level", 1)) < 23 and form_z > -40.0:
                            form_z = -380.0
                        af_h = helper.get("autofarm")
                        if isinstance(af_h, dict):
                            af_h["anchorX"] = form_x
                            af_h["anchorZ"] = form_z

                # Gemeinsames Fokusfeuer auf Rissmonolithen & Bosse (SSOT Strikter Ziel-Fokus: lebendes eigenes Ziel nicht bei normalen Mobs überschreiben!)
                if leader_mob and leader_mob.get("state") != "dead" and leader_mob.get("mapId") == helper["map_id"]:
                    d_to_mob = dist2d(helper["pos_x"], helper["pos_z"], leader_mob["x"], leader_mob["z"])
                    cur_h_tid = helper.get("autoFarmTargetId") or helper.get("targetId")
                    cur_h_mob = self.monsters.get(cur_h_tid) if cur_h_tid else None
                    cur_h_alive = bool(cur_h_mob and cur_h_mob.get("state") != "dead" and int(cur_h_mob.get("hp", 0)) > 0)
                    if d_to_mob <= 95.0 and (
                        active_tactic == "focus"
                        or leader_mob.get("kind") == "metin"
                        or leader_mob.get("isBoss")
                        or not cur_h_alive
                    ):
                        helper["targetId"] = leader_mob["id"]
                        helper["autoFarmTargetId"] = leader_mob["id"]

                # Gezielte Schamanen-Gruppenbuffs (Hilfe des Drachen & Segen) + Freundschafts-Heilung auf Gruppenmitglieder!
                for ally in m_list:
                    if ally["player_id"] == helper["player_id"] or ally["map_id"] != helper["map_id"]:
                        continue
                    is_human_ally = not str(ally.get("player_id", "")).startswith("bot_")
                    f_ally = 100 if is_human_ally else self._get_bot_friendship_score(
                        helper["player_id"], ally["player_id"], helper.get("empire", ""), ally.get("empire", "")
                    )
                    if f_ally < 0:
                        continue
                    d_ally = dist2d(helper["pos_x"], helper["pos_z"], ally["pos_x"], ally["pos_z"])
                    if d_ally > 58.0:
                        continue

                    # Schamanen-Bots wirken gezielt 'Hilfe des Drachen' (+30% AW, +15% Krit) & 'Segen' (+35% DEF) auf den Spieler & die Gruppe!
                    if helper.get("class_id") == "shaman" and (now - float(helper.get("_lastShamanPartyBuffAt", 0.0) or 0.0) >= 7.5):
                        ally_buffs = ally.get("activeBuffs") or {}
                        dh_exp = float((ally_buffs.get("dragon_help") or {}).get("expiresAt", 0.0) or 0.0)
                        db_exp = float((ally_buffs.get("dragon_blessing") or {}).get("expiresAt", 0.0) or 0.0)
                        if dh_exp < now + 15.0 or db_exp < now + 15.0:
                            helper["_lastShamanPartyBuffAt"] = now
                            self._apply_shaman_party_buffs_to_ally(helper, ally, now, force_heal=False)
                            self._adjust_bot_friendship(helper["player_id"], ally["player_id"], 0.45, "assists")
                            helper["partyAssists"] = int(helper.get("partyAssists", 0)) + 1

                    ally_hp_pct = (ally["hp"] / max(1, ally["max_hp"])) * 100.0
                    heal_thresh = 80.0 if is_human_ally else (76.0 if f_ally >= 82 else 64.0)
                    if ally_hp_pct < heal_thresh:
                        if now - float(helper.get("_lastBotAssistAt", 0.0) or 0.0) >= 5.0:
                            helper["_lastBotAssistAt"] = now
                            heal_amt = int(ally["max_hp"] * (0.38 if helper.get("class_id") == "shaman" else 0.24))
                            ally["hp"] = min(ally["max_hp"], ally["hp"] + heal_amt)
                            helper["autoFarmStatus"] = f"✨ Helfe {ally['name']} (+{heal_amt} TP!)"
                            helper["_botTradeStatusUntil"] = now + 4.5
                            self._adjust_bot_friendship(helper["player_id"], ally["player_id"], 0.55, "assists")
                            helper["partyAssists"] = int(helper.get("partyAssists", 0)) + 1
                            self._emit_combat_event(
                                ally["map_id"],
                                "heal",
                                ally["pos_x"],
                                ally["pos_z"],
                                {"playerId": ally["player_id"], "amount": heal_amt, "skillId": "natures_heal"},
                            )
                        if helper.get("class_id") in ("warrior", "sura") and ally_hp_pct < (65.0 if is_human_ally else 54.0):
                            for m in self.monsters.values():
                                if m["mapId"] == ally["map_id"] and m["state"] != "dead" and m.get("targetPlayerId") == ally["player_id"]:
                                    m["targetPlayerId"] = helper["player_id"]
                                    helper["targetId"] = m["id"]
                                    helper["autoFarmTargetId"] = m["id"]
                                    helper["autoFarmStatus"] = f"🛡️ Schütze {ally['name']} (Aggro übernommen!)"
                                    helper["_botTradeStatusUntil"] = now + 4.5
                                    self._adjust_bot_friendship(helper["player_id"], ally["player_id"], 0.65, "assists")
                                    helper["partyAssists"] = int(helper.get("partyAssists", 0)) + 1

        # 6. Bots handeln untereinander (NUR innerhalb desselben Reichs und bevorzugt mit engen Freunden >= 65%!)
        if now - float(getattr(self, "_last_bot_trade_tick", 0.0) or 0.0) >= 14.0 and len(online_bots) >= 2:
            self._last_bot_trade_tick = now
            friendly_pairs = [
                (a, b, self._get_bot_friendship_score(a["player_id"], b["player_id"], a.get("empire", ""), b.get("empire", "")))
                for i, a in enumerate(online_bots)
                for b in online_bots[i + 1 :]
                if a["map_id"] == b["map_id"]
                and a.get("empire", "seiryu") == b.get("empire", "seiryu")
                and self._get_bot_friendship_score(a["player_id"], b["player_id"], a.get("empire", ""), b.get("empire", "")) >= 60
            ]
            if friendly_pairs:
                friendly_pairs.sort(key=lambda x: (-x[2], dist2d(x[0]["pos_x"], x[0]["pos_z"], x[1]["pos_x"], x[1]["pos_z"])))
                b1, b2, f_tr = random.choice(friendly_pairs[:3])
                traded_desc = None
                inv1 = b1.get("inventory") or []
                for it in list(inv1):
                    if it.get("equippedSlot") or it.get("equipped_slot") or it.get("reservedShopId") or it.get("reserved_shop_id"):
                        continue
                    tpl = ITEM_TEMPLATES.get(it.get("templateId", ""))
                    if not tpl or tpl.get("type") != "equipment":
                        continue
                    slot_k = tpl.get("slot", "weapon")
                    if not slot_k:
                        continue
                    # Prüfe, ob b1 das Item selbst nicht braucht (entweder falsche Klasse oder schwächer als b1s angelegtes Item)
                    cur_b1_eq = (b1.get("equipment") or {}).get(slot_k)
                    b1_cand_score = self._score_bot_equipment_item(b1, it)
                    b1_cur_score = self._score_bot_equipment_item(b1, cur_b1_eq) if cur_b1_eq else -1.0
                    b1_needs_it = (b1_cand_score > b1_cur_score + 0.5) and int(tpl.get("reqLevel", 1)) <= int(b1.get("level", 1)) + 3
                    if b1_needs_it:
                        continue

                    # Prüfe, ob das Item für Freund b2 tragbar und besser als b2s aktuelles Equipment ist
                    b2_cand_score = self._score_bot_equipment_item(b2, it)
                    cur_b2_eq = (b2.get("equipment") or {}).get(slot_k)
                    b2_cur_score = self._score_bot_equipment_item(b2, cur_b2_eq) if cur_b2_eq else -1.0
                    if b2_cand_score > 0 and b2_cand_score > b2_cur_score + 0.5 and int(tpl.get("reqLevel", 1)) <= int(b2.get("level", 1)) + 2:
                        ok_tr, _ = self.db.execute_direct_trade(b1["player_id"], b2["player_id"], [it["uid"]], 0, [], 0)
                        if ok_tr:
                            self.refresh_player_from_db(b1["player_id"])
                            self.refresh_player_from_db(b2["player_id"])
                            self._auto_equip_best_inventory_items_for_bot(self.players.get(b2["player_id"]) or b2, now=now)
                            traded_desc = f"{tpl['name']} +{it.get('plusLevel', 0)}"
                        break

                if not traded_desc:
                    for it in list(inv1):
                        if it.get("equipped_slot") or it.get("reserved_shop_id"):
                            continue
                        t_id = it.get("templateId", "")
                        min_qty_tr = 5 if t_id == "mat_monolith_shard" else 2
                        if t_id in ("scroll_blessing", "item_bonus_adder", "item_bonus_changer", "mat_monolith_shard") and int(it.get("quantity", 1)) >= min_qty_tr:
                            ok_tr, _ = self.db.execute_direct_trade(b1["player_id"], b2["player_id"], [it["uid"]], 0, [], 0)
                            if ok_tr:
                                self.refresh_player_from_db(b1["player_id"])
                                self.refresh_player_from_db(b2["player_id"])
                                traded_desc = f"{it.get('quantity', 1)}x {ITEM_TEMPLATES.get(t_id, {}).get('name', t_id)}"
                            break
                    if int(b1.get("yang", 0)) > int(b2.get("yang", 0)) + 2000:
                        yang_help = min(1500, int((b1["yang"] - b2["yang"]) * 0.25))
                        b1["yang"] -= yang_help
                        b2["yang"] += yang_help
                        self.db.save_player_state(b1)
                        self.db.save_player_state(b2)
                        traded_desc = f"{traded_desc} & {yang_help} Gold" if traded_desc else f"{yang_help} Gold"

                if traded_desc:
                    self._adjust_bot_friendship(b1["player_id"], b2["player_id"], 1.1, "trades")
                    b1["friendTradesCount"] = int(b1.get("friendTradesCount", 0)) + 1
                    b2["friendTradesCount"] = int(b2.get("friendTradesCount", 0)) + 1
                    new_f_tr = self._get_bot_friendship_score(b1["player_id"], b2["player_id"], b1.get("empire", ""), b2.get("empire", ""))
                    b1["autoFarmStatus"] = f"🤝 Freundschafts-Handel ({new_f_tr}%) mit {b2['name']}: {traded_desc}"
                    b2["autoFarmStatus"] = f"🤝 Freundschafts-Handel ({new_f_tr}%) von {b1['name']}: {traded_desc}"
                    b1["_botTradeStatusUntil"] = now + 5.5
                    b2["_botTradeStatusUntil"] = now + 5.5

        # 7. Map-1-Stadt-Shop errichten & Fremdes Reich besuchen, um Shops zu prüfen und benötigte Items intelligent zu kaufen
        if now - getattr(self, "_last_bot_cross_empire_shop_ts", 0.0) >= 14.0:
            self._last_bot_cross_empire_shop_ts = now
            all_shops = self.db.list_offline_shops("morgenwacht")
            own_shop_by_owner = {sh.get("owner_id"): sh for sh in all_shops}

            for b in list(online_bots):
                b_id = b["player_id"]
                b_emp = str(b.get("empire", "seiryu")).lower()
                b_cls = b.get("class_id", "warrior")
                b_lvl = int(b.get("level", 1))

                # 7a. Eigene Offline-Shop-Erlöse abheben
                if int(b.get("shop_vault_yang", 0)) > 0:
                    ok_v, _, v_amt = self.db.withdraw_shop_vault(b_id)
                    if ok_v and v_amt > 0:
                        self.refresh_player_from_db(b_id)
                        b = self.players.get(b_id) or b

                # 7b. Eigenen Shop in der Map-1-Hauptstadt des eigenen Reichs errichten / befüllen (max. 10 Angebote pro Bot-Shop)
                my_sh = own_shop_by_owner.get(b_id)
                my_listings_count = len((my_sh or {}).get("listings") or [])
                if my_listings_count < 10:
                    for it in list(b.get("inventory") or []):
                        if it.get("equippedSlot") or it.get("equipped_slot") or it.get("reservedShopId") or it.get("reserved_shop_id"):
                            continue
                        iid = str(it.get("templateId") or it.get("id") or "")
                        tpl = ITEM_TEMPLATES.get(iid, {})
                        if not tpl:
                            continue
                        itype = tpl.get("type", it.get("type", "misc"))
                        plus_v = int(it.get("plusLevel", 0))
                        bonuses = it.get("bonuses") or []
                        list_item = False
                        if itype == "equipment":
                            slot_k = tpl.get("slot", "weapon")
                            cur_eq = (b.get("equipment") or {}).get(slot_k)
                            cand_sc = self._score_bot_equipment_item(b, it)
                            cur_sc = self._score_bot_equipment_item(b, cur_eq) if cur_eq else -1.0
                            # Niemals ein Item verkaufen, das der Bot selbst braucht!
                            if cand_sc > cur_sc + 0.5 and int(tpl.get("reqLevel", 1)) <= b_lvl + 5:
                                continue
                            if plus_v >= 4 or len(bonuses) >= 2 or cand_sc < 0:
                                list_item = True
                        elif (iid.startswith("fb_") or itype == "skill_book") and tpl.get("classId") not in (None, b_cls):
                            list_item = True
                        elif iid in ("mat_white_pearl", "mat_soul_stone") and int(it.get("quantity", 1)) >= 3:
                            list_item = True
                        elif iid == "mat_monolith_shard" and int(it.get("quantity", 1)) >= 6:
                            list_item = True

                        if list_item:
                            base_sell = max(450, int(tpl.get("sellPrice", 250)))
                            ask_price = int(base_sell * (2.2 + plus_v * 0.85 + len(bonuses) * 0.65))
                            city_label = "Seiryu-Stadt" if b_emp == "seiryu" else "Kaeryu-Stadt"
                            ok_sh, _ = self.db.create_or_add_to_offline_shop(
                                b_id,
                                b["name"],
                                f"{b['name']}s Handelsstand ({city_label})",
                                "morgenwacht",
                                820.0 if b_emp == "seiryu" else -820.0,
                                -766.0,
                                it["uid"],
                                ask_price,
                            )
                            if ok_sh:
                                b["offlineShopListingsCreated"] = int(b.get("offlineShopListingsCreated", 0)) + 1
                                self.refresh_player_from_db(b_id)
                                b = self.players.get(b_id) or b
                            break

                # 7c. Besuch des anderen Reichs (Map-1-Stadt des Gegenreichs), um dortige Offline-Shops zu prüfen & benötigte Items intelligent zu kaufen
                foreign_emp_label = "Kaeryu-Stadt" if b_emp == "seiryu" else "Seiryu-Stadt"
                foreign_shops = [
                    sh for sh in all_shops
                    if sh.get("owner_id") != b_id
                    and ((b_emp == "seiryu" and float(sh.get("pos_x", 0.0)) < 0.0) or (b_emp != "seiryu" and float(sh.get("pos_x", 0.0)) > 0.0))
                ]
                other_own_empire_shops = [
                    sh for sh in all_shops
                    if sh.get("owner_id") != b_id and sh not in foreign_shops
                ]
                if foreign_shops:
                    b["foreignShopVisits"] = int(b.get("foreignShopVisits", 0)) + 1

                bought_info = None
                for sh in (foreign_shops + other_own_empire_shops):
                    is_foreign_shop = sh in foreign_shops
                    for lst in list(sh.get("listings") or []):
                        ask_price = int(lst.get("priceYang", lst.get("price", 999999)))
                        if ask_price <= 0 or int(b.get("yang", 0)) < ask_price + 2500:
                            continue
                        iid = str(lst.get("templateId") or lst.get("id") or "")
                        tpl = ITEM_TEMPLATES.get(iid, {})
                        if not tpl:
                            continue
                        itype = tpl.get("type", lst.get("type", "misc"))
                        plus_v = int(lst.get("plusLevel", 0))
                        bonuses = lst.get("bonuses") or []

                        needs_item = False
                        fair_max = max(800, int(tpl.get("sellPrice", 300) * (3.2 + plus_v * 1.2 + len(bonuses) * 0.9)))
                        if itype == "equipment":
                            slot_k = tpl.get("slot", "weapon")
                            cur_eq = (b.get("equipment") or {}).get(slot_k)
                            cand_sc = self._score_bot_equipment_item(b, lst)
                            cur_sc = self._score_bot_equipment_item(b, cur_eq) if cur_eq else -1.0
                            if cand_sc > 0 and cand_sc > cur_sc + 0.5 and int(tpl.get("reqLevel", 1)) <= b_lvl + 3:
                                needs_item = True
                                fair_max = max(fair_max, 28000)
                        elif iid in ("scroll_blessing", "item_bonus_adder", "item_bonus_changer", "item_blessing_orb", "item_soul_fragment", "mat_soul_stone", "mat_white_pearl"):
                            needs_item = True
                            fair_max = max(fair_max, 24000)
                        elif (iid.startswith("fb_") or itype == "skill_book") and tpl.get("classId") in (None, b_cls):
                            needs_item = True
                            fair_max = max(fair_max, 18000)
                        elif iid in ("chest_moonlight", "chest_skill_books", "chest_boss_reaper"):
                            needs_item = True
                            fair_max = max(fair_max, 16000)

                        if needs_item and ask_price <= fair_max:
                            ok_buy, _, seller_id_db = self.db.buy_offline_shop_listing(b_id, b["name"], lst.get("listingId"))
                            if ok_buy:
                                seller_id = seller_id_db or sh.get("owner_id")
                                self.refresh_player_from_db(b_id)
                                if seller_id and seller_id in self.players:
                                    self.refresh_player_from_db(seller_id)
                                b = self.players.get(b_id) or b
                                b["marketPurchases"] = int(b.get("marketPurchases", 0)) + 1
                                self._auto_equip_best_inventory_items_for_bot(b, now=now)
                                shop_origin = foreign_emp_label if is_foreign_shop else "eigenem Reich"
                                bought_info = f"🛒 Gekauft in {shop_origin} ({sh.get('title', 'Shop')}): {lst.get('name', iid)} +{plus_v} für {ask_price} Gold"
                                break
                    if bought_info:
                        break

                if bought_info:
                    b["autoFarmStatus"] = bought_info
                    b["_botTradeStatusUntil"] = now + 6.0
                elif foreign_shops and random.random() < 0.28 and now >= float(b.get("_botTradeStatusUntil", 0.0)):
                    b["autoFarmStatus"] = f"🔍 Fremdreich-Shops in {foreign_emp_label} geprüft ({len(foreign_shops)} Marktstände)"
                    b["_botTradeStatusUntil"] = now + 4.0

    # ========================================================================
    # 7. SPIELER-ANGRIFFE, AUSWEICHEN, BLOCKEN, STATUS-EFFEKTE & KLASSEN-FERTIGKEITEN (Autoritativ)
    # ========================================================================
    def perform_player_dodge(self, player_id: str, payload: dict) -> dict:
        p = self.players.get(player_id)
        if not p:
            return {"ok": False}
        if p.get("active_mount"):
            return {"ok": False, "reason": "Auf dem Reittier ist kein Ausweich-Sprint möglich."}
        now = time.time()
        if now < p.get("dodgeCooldownUntil", 0.0):
            return {"ok": False, "reason": "cooldown"}

        p["dodgeCooldownUntil"] = now + 1.22
        p["dodgeUntil"] = now + 0.52  # 0.52s autoritatives Unverwundbarkeitsfenster (I-Frames)
        p["dodgeSpeedBoostUntil"] = now + 1.8
        p["isBlocking"] = False
        p["autoAttackTargetId"] = None

        dx = float(payload.get("dx", 0.0))
        dz = float(payload.get("dz", 0.0))
        d_len = math.hypot(dx, dz)
        if d_len > 0.01:
            dx /= d_len
            dz /= d_len
            dash_dist = 3.8
            nx = max(-1360.0, min(1360.0, p["pos_x"] + dx * dash_dist))
            nz = max(-1360.0, min(1360.0, p["pos_z"] + dz * dash_dist))
            p["pos_x"] = nx
            p["pos_z"] = nz
            p["rot_y"] = math.atan2(dx, dz)

        if payload.get("x") is not None and payload.get("z") is not None:
            cx = max(-1360.0, min(1360.0, float(payload["x"])))
            cz = max(-1360.0, min(1360.0, float(payload["z"])))
            if math.hypot(cx - p["pos_x"], cz - p["pos_z"]) <= 6.5:
                p["pos_x"] = cx
                p["pos_z"] = cz

        p["lastManualMoveTime"] = now
        self._emit_combat_event(
            p["map_id"],
            "player_dodge",
            p["pos_x"],
            p["pos_z"],
            {"playerId": player_id, "rotY": round(p.get("rot_y", 0.0), 2)},
        )
        return {"ok": True, "dodgeUntil": p["dodgeUntil"], "cooldownUntil": p["dodgeCooldownUntil"]}

    def set_player_block_state(self, player_id: str, active: bool) -> dict:
        p = self.players.get(player_id)
        if p:
            p.pop("isBlocking", None)
        return {"ok": True, "isBlocking": False}

    def interact_with_monolith(self, player_id: str, monolith_id: Optional[str] = None, mode: str = "purify") -> dict:
        """Erlaubt Spielern, einen Rissmonolithen zu reinigen ('purify' -> Monolithensplitter & Materialien)
        oder seine Riss-Resonanz zu entfesseln ('awaken' -> Schlafend -> Instabil -> Erwacht mit Öffentlichem Event & Weltboss)."""
        p = self.players.get(player_id)
        if not p:
            return {"ok": False, "message": "Spieler nicht gefunden."}
        now = time.time()

        target_mob = None
        cand_id = monolith_id or p.get("targetId")
        if cand_id and cand_id in self.monsters:
            m = self.monsters[cand_id]
            if m.get("kind") == "metin" and m.get("mapId") == p["map_id"] and m.get("state") != "dead":
                target_mob = m

        if not target_mob:
            nearby_metins = [
                m for m in self.monsters.values()
                if m.get("kind") == "metin"
                and m.get("mapId") == p["map_id"]
                and m.get("state") != "dead"
                and dist2d(p["pos_x"], p["pos_z"], m["x"], m["z"]) <= 22.0
            ]
            if nearby_metins:
                target_mob = min(nearby_metins, key=lambda m: dist2d(p["pos_x"], p["pos_z"], m["x"], m["z"]))

        if not target_mob:
            return {"ok": False, "message": "Kein aktiver Rissmonolith in Reichweite (max. 22m)."}

        d = dist2d(p["pos_x"], p["pos_z"], target_mob["x"], target_mob["z"])
        if d > 22.0:
            return {"ok": False, "message": f"Du bist zu weit vom Rissmonolithen entfernt ({int(d)}m). Nähere dich auf unter 20m!"}

        target_mob.setdefault("participants", set()).add(player_id)
        cur_state = target_mob.get("monolithState", "schlafend")

        if mode == "purify":
            return {
                "ok": False,
                "message": "Die Reinigung von Monolithen wurde entfernt. Zerstöre den Monolithen im Kampf, um Monolithensplitter und wertvolle Beute zu erbeuten!",
            }

        # mode == 'awaken' — STRIKT nur mit den 2 bestimmten Erweckungs-Items möglich!
        # Item 1 ('mat_monolith_shard' = Monolithensplitter): Normal ('schlafend') ➔ Instabil ('instabil')
        # Item 2 ('mat_awakened_rift_core' = Erwachter Risskern): Instabil ('instabil') ➔ Erwacht ('erwacht' + 1 Weltboss)
        if cur_state == "schlafend":
            used_shard = self.db.consume_item_by_template(player_id, "mat_monolith_shard", 1)
            if not used_shard:
                return {
                    "ok": False,
                    "message": "⚠️ Du benötigst 1× 'Monolithensplitter' im Inventar, um diesen Rissmonolithen zu Stufe 2 (Instabil) zu erwecken! (Dropt aus Rissmonolithen)",
                }
            self.refresh_player_from_db(player_id)
            p = self.players.get(player_id, p)
            target_mob["lastDamagedAt"] = now
            target_mob["wavesSpawned"] = []
            target_mob["eliteBossesSpawned"] = 0
            target_mob["guardsSpawned"] = True
            self._apply_monolith_state(target_mob, "instabil", announce=True, actor=p, preserve_hp=False)
            self._spawn_monolith_guardians(target_mob, count=2, target_player_id=player_id)
            elites_cnt = self._get_unstable_elite_boss_count(int(target_mob.get("level", 5)))
            return {
                "ok": True,
                "message": f"⚡ [Stufe 2: Instabil] 1× Monolithensplitter eingesetzt! {target_mob['name']} (Lv. {target_mob['level']}) ist erwacht und ruft {elites_cnt}× Elite-Boss herbei!",
            }
        elif cur_state == "instabil":
            # Prüfe zuerst: Es darf nur 1 Weltboss / 1 Erwachter Rissmonolith pro Mapgebiet gleichzeitig aktiv sein
            # UND ein Rissmonolith kann nur alle 30 Minuten (1800s) pro Gebiet von 'instabil' auf 'erwacht' ausgelöst werden!
            map_id_m = target_mob["mapId"]
            active_wb = self._get_active_world_boss(map_id_m)
            active_erwacht = self._get_active_erwacht_monolith(map_id_m, exclude_mob_id=target_mob["id"])
            if active_wb is not None or active_erwacht is not None:
                wb_label = active_wb["name"] if active_wb else active_erwacht["name"]
                return {
                    "ok": False,
                    "message": f"⚠️ In diesem Gebiet ist bereits ein Weltboss aktiv ({wb_label})! Es kann maximal 1 Gebiets-Weltboss gleichzeitig spawnen.",
                }
            cd_rem = self._get_world_boss_cooldown_remaining(map_id_m, now=now)
            if cd_rem > 0.0:
                rem_m = int(cd_rem // 60)
                rem_s = int(math.ceil(cd_rem % 60))
                return {
                    "ok": False,
                    "message": f"⏳ Gebiets-Abklingzeit aktiv: Ein Rissmonolith kann nur alle 30 Minuten pro Gebiet vom instabilen in den erwachten Zustand (Weltboss) ausgelöst werden! (Noch {rem_m} Min. {rem_s} Sek.)",
                }
            used_core = self.db.consume_item_by_template(player_id, "mat_awakened_rift_core", 1)
            if not used_core:
                return {
                    "ok": False,
                    "message": "⚠️ Du benötigst 1× 'Erwachter Risskern' im Inventar, um diesen Instabilen Rissmonolithen zu Stufe 3 (Erwacht) zu erwecken! (Dropt aus Instabilen Rissmonolithen)",
                }
            self.last_world_boss_awakened_at[map_id_m] = now
            self.world_boss_cooldown_until[map_id_m] = now + self.WORLD_BOSS_AWAKEN_COOLDOWN_SEC
            self.refresh_player_from_db(player_id)
            p = self.players.get(player_id, p)
            target_mob["lastDamagedAt"] = now
            target_mob["wavesSpawned"] = []
            target_mob["worldBossSummoned"] = False
            target_mob["activeWorldBossId"] = None
            target_mob["guardsSpawned"] = True
            target_mob["nextAoETime"] = now + 4.5
            self._apply_monolith_state(target_mob, "erwacht", announce=True, actor=p, preserve_hp=False)
            self._spawn_monolith_guardians(target_mob, count=3, target_player_id=player_id)
            wb = self.monsters.get(target_mob.get("activeWorldBossId")) or self._get_active_world_boss(target_mob["mapId"])
            wb_name = wb["name"] if wb else "Riss-Weltboss"
            return {
                "ok": True,
                "message": f"🔥 [Stufe 3: ERWACHT — WELTBOSS] 1× Erwachter Risskern eingesetzt! {wb_name} ist erschienen (⏳ 1 Stunde Zeit, auf der Weltkarte [M] markiert)!",
            }
        else:
            return {
                "ok": False,
                "message": f"💀 {target_mob['name']} befindet sich bereits auf der maximalen 3. Stufe (Erwachter Rissmonolith)! Bezwinge den Weltboss innerhalb von 1 Stunde!",
            }

    def _apply_status_effect_to_mob(self, mob: dict, effect_id: str, duration: float, source_player: dict):
        if mob.get("state") == "dead" or mob.get("kind") == "metin":
            return
        now = time.time()
        catalog = {
            "bleed": {"name": "Blutung", "icon": "🩸", "color": "#ef4444", "tickPct": 0.018},
            "burn": {"name": "Verbrennung", "icon": "🔥", "color": "#f97316", "tickPct": 0.022},
            "poison": {"name": "Gift", "icon": "☠️", "color": "#22c55e", "tickPct": 0.016},
            "armor_break": {"name": "Rüstungsbruch", "icon": "🛡️💥", "color": "#fbbf24", "tickPct": 0.0},
            "slow": {"name": "Verlangsamt", "icon": "❄️", "color": "#38bdf8", "tickPct": 0.0},
            "stun": {"name": "Betäubt", "icon": "💫", "color": "#fde047", "tickPct": 0.0},
        }
        meta = catalog.get(effect_id)
        if not meta:
            return
        if mob.get("isBoss") and effect_id == "stun":
            duration *= 0.55  # Bosse haben verkürzte Betäubungsdauer (Stagger)

        effects = mob.setdefault("statusEffects", {})
        already_active = effect_id in effects and effects[effect_id].get("expiresAt", 0) > now
        effects[effect_id] = {
            "id": effect_id,
            "name": meta["name"],
            "icon": meta["icon"],
            "color": meta["color"],
            "tickPct": meta["tickPct"],
            "expiresAt": now + duration,
            "nextTickAt": (effects[effect_id]["nextTickAt"] if already_active else now + 1.0),
            "sourceId": source_player.get("player_id") if source_player else None,
        }
        if not already_active:
            self._emit_combat_event(
                mob["mapId"],
                "status_applied",
                mob["x"],
                mob["z"],
                {
                    "targetId": mob["id"],
                    "statusId": effect_id,
                    "statusName": meta["name"],
                    "icon": meta["icon"],
                    "color": meta["color"],
                    "duration": round(duration, 1),
                },
            )

    def _tick_monster_status_effects(self, mob: dict, now: float):
        effects = mob.get("statusEffects")
        if not effects:
            return
        for eff_id, eff in list(effects.items()):
            if now >= eff.get("expiresAt", 0.0):
                effects.pop(eff_id, None)
                continue
            if eff.get("tickPct", 0.0) > 0.0 and now >= eff.get("nextTickAt", 0.0):
                eff["nextTickAt"] = now + 1.0
                src_p = self.players.get(eff.get("sourceId"))
                base_atk = max(45.0, float(src_p["computed"]["atk"])) if src_p else 65.0
                tick_dmg = max(6, int(round(base_atk * 0.34)))
                mob["hp"] = max(0, mob["hp"] - tick_dmg)
                self._emit_combat_event(
                    mob["mapId"],
                    "status_tick",
                    mob["x"],
                    mob["z"],
                    {
                        "targetId": mob["id"],
                        "damage": tick_dmg,
                        "statusId": eff_id,
                        "statusName": eff.get("name", ""),
                        "icon": eff.get("icon", "🩸"),
                        "color": eff.get("color", "#ef4444"),
                    },
                )
                if mob["hp"] <= 0:
                    killer = src_p or next((p for p in self.players.values() if p.get("online")), None)
                    if killer:
                        self._handle_mob_death(killer, mob)
                    break

    def _trigger_player_death(self, p: dict, killer_mob: Optional[dict] = None):
        now = time.time()
        # KI v5.0 Respawn-Gedächtnis: Merke den aktiven Boss oder Rissmonolith vor dem Tod, um nach dem Respawn direkt zurückzukehren!
        if str(p.get("player_id", "")).startswith("bot_"):
            prev_tid = p.get("manualFocusTargetId") or p.get("autoFarmTargetId") or p.get("targetId") or (killer_mob["id"] if killer_mob else None)
            prev_mob = self.monsters.get(prev_tid) if prev_tid else killer_mob
            if prev_mob and prev_mob.get("state") != "dead" and (
                prev_mob.get("isBoss")
                or prev_mob.get("isMapBossSlot")
                or prev_mob.get("isRiftWorldBoss")
                or prev_mob.get("isMonolithEliteBoss")
                or prev_mob.get("kind") == "metin"
            ):
                p["_resumeBossTargetId"] = prev_mob["id"]
        p["hp"] = 0
        p["isDead"] = True
        p["deadAt"] = now
        p["moveTarget"] = None
        p["autoAttackTargetId"] = None
        p["autoFarmTargetId"] = None
        p["autoFarmNextTargetId"] = None
        p["manualFocusTargetId"] = None
        p["isBlocking"] = False
        if isinstance(p.get("autofarm"), dict):
            st_d = self.ensure_autofarm_stats(p["autofarm"])
            st_d["deaths"] = int(st_d.get("deaths", 0)) + 1
            st_d["recentZoneDeaths"] = int(st_d.get("recentZoneDeaths", 0)) + 1
            if p["autofarm"].get("enabled"):
                p["autofarm"]["enabled"] = False
                p["autoFarmStatus"] = "💀 Gefallen (Warte auf Neustart)"
        for m in self.monsters.values():
            if m.get("targetPlayerId") == p["player_id"]:
                m["targetPlayerId"] = None
                if m.get("state") == "chase":
                    m["state"] = "patrol"
                    m["patrolX"] = m["spawnX"]
                    m["patrolZ"] = m["spawnZ"]
        self._emit_combat_event(
            p.get("map_id", "morgenwacht"),
            "player_death",
            p["pos_x"],
            p["pos_z"],
            {
                "playerId": p["player_id"],
                "killerName": killer_mob["name"] if killer_mob else "Gegner",
                "deadAt": now,
            },
        )
        self.db.save_player_state(p)

    def respawn_player(self, player_id: str, mode: str = "here") -> dict:
        p = self.players.get(player_id)
        if not p:
            return {"ok": False, "message": "Spieler nicht gefunden."}
        if mode == "test_death":
            self._trigger_player_death(p)
            return {"ok": True, "mode": "test_death", "message": "💀 Du bist gefallen (0 TP)!"}
        now = time.time()
        dead_at = float(p.get("deadAt", 0.0) or 0.0)

        if mode == "here":
            if p.get("isDead") and dead_at > 0.0:
                elapsed = now - dead_at
                if elapsed < 6.5:
                    rem = max(1, int(math.ceil(8.0 - elapsed)))
                    return {
                        "ok": False,
                        "remainingSec": rem,
                        "message": f"⏳ Du kannst erst in {rem} Sek. hier neu starten!",
                    }
            p["isDead"] = False
            p["deadAt"] = 0.0
            p["hp"] = p["max_hp"]
            p["mp"] = p["max_mp"]
            p["dodgeUntil"] = now + 2.5
            p["moveTarget"] = None
            p["autoAttackTargetId"] = None
            if str(player_id).startswith("bot_") and isinstance(p.get("autofarm"), dict):
                p["autofarm"]["enabled"] = True
                res_tid = p.pop("_resumeBossTargetId", None)
                res_mob = self.monsters.get(res_tid) if res_tid else None
                if res_mob and res_mob.get("state") != "dead" and int(res_mob.get("hp", 0)) > 0 and res_mob.get("mapId") == p.get("map_id"):
                    p["targetId"] = res_mob["id"]
                    p["autoFarmTargetId"] = res_mob["id"]
                    p["manualFocusTargetId"] = res_mob["id"]
                    p["autofarm"]["anchorX"] = res_mob["x"]
                    p["autofarm"]["anchorZ"] = res_mob["z"]
                    p["autoFarmStatus"] = f"🔥 Wiederauferstanden & neu gebufft -> Kehre zum Kampf gegen {res_mob['name']} zurück!"
                    p["_botTradeStatusUntil"] = now + 4.5
            self._emit_combat_event(
                p.get("map_id", "morgenwacht"),
                "player_respawn",
                p["pos_x"],
                p["pos_z"],
                {"playerId": player_id, "mode": "here"},
            )
            self.db.save_player_state(p)
            return {
                "ok": True,
                "mode": "here",
                "message": "✨ Du bist an Ort und Stelle wiederauferstanden!",
            }

        # mode == "city": Sofortiger Neustart am Portal in seiner Stadt (Teleport-Platz)
        p["isDead"] = False
        p["deadAt"] = 0.0
        p["hp"] = p["max_hp"]
        p["mp"] = p["max_mp"]
        p["dodgeUntil"] = now + 2.5
        p["moveTarget"] = None
        p["autoAttackTargetId"] = None
        p["autoFarmTargetId"] = None
        p["targetId"] = None

        cur_map = p.get("map_id", "morgenwacht")
        emp = str(p.get("empire") or p.get("quests", {}).get("__empire__", "")).lower()
        if emp not in ("kaeryu", "seiryu"):
            emp = "kaeryu" if float(p.get("pos_x", 708.0)) < 0.0 else "seiryu"
        p["empire"] = emp

        if cur_map == "morgenwacht":
            if emp == "kaeryu":
                # Portal (Teleport-Platz) in der Stadt Kaeryu
                p["pos_x"] = -782.0
                p["pos_z"] = -742.0
                p["rot_y"] = 0.0
                city_label = "Kaeryu"
            else:
                # Portal (Teleport-Platz) in der Stadt Seiryu
                p["pos_x"] = 782.0
                p["pos_z"] = -742.0
                p["rot_y"] = 0.0
                city_label = "Seiryu"
        else:
            # Portal (Teleport-Platz) in der Siedlung der aktuellen Karte
            p["pos_x"] = 30.0
            p["pos_z"] = 132.0
            p["rot_y"] = 0.0
            city_label = MAPS.get(cur_map, {}).get("name", "Stadt")

        p["_lastMapChangeAt"] = now
        p["teleportSeq"] = int(p.get("teleportSeq", 0)) + 1
        self._emit_combat_event(
            cur_map,
            "player_respawn",
            p["pos_x"],
            p["pos_z"],
            {"playerId": player_id, "mode": "city"},
        )
        self.db.save_player_state(p)
        return {
            "ok": True,
            "mode": "city",
            "message": f"🏛️ Du bist am Portal in deiner Stadt ({city_label}) wiederauferstanden!",
        }

    def _apply_damage_to_player_authoritative(
        self,
        target: dict,
        mob: Optional[dict],
        raw_dmg: int,
        is_boss_skill: bool = False,
        skill_name: str = "",
    ) -> int:
        if target.get("isDead") or float(target.get("hp", 1)) <= 0:
            return 0
        now = time.time()
        map_id = target.get("map_id", "morgenwacht")
        mob_id = mob["id"] if mob else None

        # 1. Ausweichen (Dodge-I-Frames ODER passiver Bonus Ausweichen)
        comp = target.get("computed", {})
        dodge_stat_chance = float(comp.get("dodgeChance", 0.0) or (target.get("dex", 11) * 0.45))
        is_i_frame_dodge = now < target.get("dodgeUntil", 0.0)
        is_passive_dodge = (random.uniform(0.0, 100.0) <= dodge_stat_chance) and not is_boss_skill

        if is_i_frame_dodge or is_passive_dodge:
            self._emit_combat_event(
                map_id,
                "combat_feedback",
                target["pos_x"],
                target["pos_z"],
                {
                    "playerId": target["player_id"],
                    "mobId": mob_id,
                    "feedbackType": "dodge",
                    "text": "💨 AUSGEWICHEN!",
                    "color": "#38bdf8",
                },
            )
            return 0

        # 1B. Schild-Bonus: Chance, Nahkampfangriff zu blocken (lässt Schläge komplett ins Leere laufen!)
        block_chance = float(comp.get("blockChancePct", 0.0) or 0.0)
        if block_chance > 0.0 and not is_boss_skill and random.uniform(0.0, 100.0) <= block_chance:
            self._emit_combat_event(
                map_id,
                "combat_feedback",
                target["pos_x"],
                target["pos_z"],
                {
                    "playerId": target["player_id"],
                    "mobId": mob_id,
                    "feedbackType": "block",
                    "text": "🛡️ GEBLOCKT!",
                    "color": "#fbbf24",
                },
            )
            return 0

        # 2. Regulärer Treffer (inkl. Elementar-/Magiewiderstände, Boss-Fertigkeits-Widerstand & Monsterschild)
        monster_res_pct = float(comp.get("monsterResPct", 0.0) or 0.0)
        elem_res_pct = max(
            float(comp.get("resFirePct", 0.0) or 0.0),
            float(comp.get("resLightningPct", 0.0) or 0.0),
            float(comp.get("resWindPct", 0.0) or 0.0),
            float(comp.get("resIcePct", 0.0) or 0.0),
            float(comp.get("resMagicPct", 0.0) or 0.0) * 0.75,
        )
        total_pvm_res = min(65.0, monster_res_pct + elem_res_pct * 0.65)
        if total_pvm_res > 0.0:
            raw_dmg = max(1, int(round(raw_dmg * max(0.25, 1.0 - total_pvm_res / 100.0))))

        if is_boss_skill:
            res_boss_skill = float(comp.get("resBossSkillPct", 0.0) or 0.0)
            if res_boss_skill > 0.0:
                raw_dmg = max(1, int(round(raw_dmg * max(0.35, 1.0 - res_boss_skill / 100.0))))

        target["hp"] = max(0, int(target["hp"] - raw_dmg))
        self._emit_combat_event(
            map_id,
            "damage_player",
            target["pos_x"],
            target["pos_z"],
            {
                "playerId": target["player_id"],
                "mobId": mob_id,
                "damage": raw_dmg,
                "isBossSkill": is_boss_skill,
                "skillName": skill_name,
            },
        )
        if 0 < target["hp"] <= target["max_hp"] * 0.20:
            self._try_proc_pet_renewal(target, now)
        if target["hp"] <= 0:
            if mob and mob.get("kind") != "metin":
                sp_kill = self._get_species_profile(mob)
                sp_kill["playerKills"] = int(sp_kill.get("playerKills", 0)) + 1
                self._update_species_evolution_stage(sp_kill)
            self._trigger_player_death(target, mob)
        return raw_dmg

    def perform_basic_attack(self, player_id: str, target_id: Optional[str] = None) -> dict:
        p = self.players.get(player_id)
        if not p or p.get("isDead") or float(p.get("hp", 1)) <= 0:
            return {"ok": False}

        now = time.time()
        atk_interval = 0.58 / max(0.80, min(1.45, p["computed"]["atkSpeed"]))
        last_atk = p.get("lastBasicAttack", 0.0)
        if now - last_atk < atk_interval * 0.78:
            return {"ok": False, "reason": "cooldown"}

        is_mounted = bool(p.get("active_mount"))
        max_combo = 4 if is_mounted else int(p["computed"].get("maxComboSteps", 6))

        # Bodenkampf: 4- bis 6-Schlag-Combo mit Finisher am Ende; Reitkampf: Kontinuierlicher Kreis-Schlag ohne Wegstoßen
        if now - last_atk > 2.2:
            combo_step = 1
        else:
            combo_step = (int(p.get("comboStep", 0)) % max_combo) + 1
        p["comboStep"] = combo_step
        p["lastBasicAttack"] = now
        p["moveTarget"] = None

        atk_range = p["computed"]["attackRange"]
        weapon_sub = p["computed"].get("weaponSubType") or "one_hand"
        mob = self._find_valid_target(p, target_id, max_range=atk_range + 2.6)
        if not mob:
            return {"ok": False, "reason": "no_target"}

        p["targetId"] = mob["id"]
        p["rot_y"] = math.atan2(mob["x"] - p["pos_x"], mob["z"] - p["pos_z"])

        # Zu Fuß: Der letzte Schlag der 4..6er-Combo ist ein wuchtiger Finisher mit Knockback!
        # Vom Pferd aus: Kontinuierlicher hoher Reit-Schlag (DSS-Skalierung) OHNE Wegstoßen!
        waffen_lvl = int(p.get("passives", {}).get("waffenmeister", 0))
        is_foot_finisher = (not is_mounted) and (combo_step == max_combo)
        if is_mounted:
            finisher_mult = 1.12 + waffen_lvl * 0.008
        elif is_foot_finisher:
            finisher_mult = 1.26 + waffen_lvl * 0.012
        elif combo_step >= max_combo - 1:
            finisher_mult = 1.10
        else:
            finisher_mult = 1.0

        dmg, is_crit, is_pierce = self._calculate_damage_to_mob(p, mob, power_mult=finisher_mult)
        self._apply_damage_to_mob(
            p, mob, dmg, is_crit, is_pierce=is_pierce, skill_id="basic", combo_step=combo_step, is_cleave=False
        )
        total_dealt = dmg
        double_hit = False
        second_dmg = 0

        # Schattenjäger (Dolche): Spezielle Schadensberechnung — Doppelter Angriff pro Schlag!
        if p["computed"].get("isDoubleStrike") and mob["state"] != "dead":
            double_hit = True
            second_dmg, c2_crit, c2_pierce = self._calculate_damage_to_mob(p, mob, power_mult=finisher_mult * 0.68)
            self._apply_damage_to_mob(
                p, mob, second_dmg, c2_crit, is_pierce=c2_pierce, skill_id="basic_dagger_twin", combo_step=combo_step, is_cleave=False
            )
            total_dealt += second_dmg

        # TP-Absaugung (Waffen-Sura Verzauberte Klinge & Runenbonus TP-Absaugung)
        hp_absorb_pct = float(p["computed"].get("hpAbsorbPct", 0.0))
        if hp_absorb_pct > 0.0 and p["hp"] < p["max_hp"]:
            absorb_heal = max(2, int(round(total_dealt * (hp_absorb_pct / 100.0))))
            p["hp"] = min(p["max_hp"], p["hp"] + absorb_heal)

        # Ausrüstungs-Spezialboni bei Treffer (Helm: Gift-/Blutungs-Chance | Schuhe/Halskette: Ohnmachtschance)
        if mob["state"] != "dead" and mob["kind"] != "metin":
            poison_ch = float(p["computed"].get("poisonChancePct", 0.0))
            bleed_ch = float(p["computed"].get("bleedChancePct", 0.0))
            stun_ch = float(p["computed"].get("stunChancePct", 0.0))
            if poison_ch > 0.0 and random.uniform(0.0, 100.0) <= poison_ch:
                self._apply_status_effect_to_mob(mob, "poison", 6.0, p)
            if bleed_ch > 0.0 and random.uniform(0.0, 100.0) <= bleed_ch:
                self._apply_status_effect_to_mob(mob, "bleed", 6.0, p)
            if stun_ch > 0.0 and random.uniform(0.0, 100.0) <= stun_ch:
                self._apply_status_effect_to_mob(mob, "stun", 2.2, p)

        # Passiv-Synergie & Status-Effekte beim Boden-Combo-Finisher oder Krit-Treffer
        if is_foot_finisher or is_crit:
            lebenskraft_lvl = int(p.get("passives", {}).get("lebenskraft", 0))
            if lebenskraft_lvl > 0 and p["hp"] < p["max_hp"]:
                vamp_heal = max(4, int(round(dmg * (0.04 + lebenskraft_lvl * 0.004))))
                p["hp"] = min(p["max_hp"], p["hp"] + vamp_heal)

            if is_foot_finisher and mob["state"] != "dead" and mob["kind"] != "metin":
                instinkt_lvl = int(p.get("passives", {}).get("kritischerinstinkt", 0))
                status_chance = 48.0 + instinkt_lvl * 1.8
                if random.uniform(0, 100) <= status_chance:
                    eff_choice = "bleed" if p.get("class_id") in ("warrior", "ninja") else "burn"
                    self._apply_status_effect_to_mob(mob, eff_choice, 5.0, p)
                if is_pierce or random.uniform(0, 100) <= 35.0:
                    self._apply_status_effect_to_mob(mob, "armor_break", 6.0, p)

        # Trefferzonen, Waffen-Reichweite & Reit-Rundschläge:
        # - Vom Pferd aus: Kontinuierlicher 360°-Kreis-Schlag um das Reittier herum ohne Wegstoßen!
        # - Zu Fuß mit Zweihandwaffe: Weiter Bogen vor dir, trifft viele Monster gleichzeitig (ideal für PvM).
        # - Zu Fuß mit Dolchen: Extrem schnell, kurze präzise Trefferzone.
        # - Zu Fuß mit Bogen: Präziser Fernkampfschuss auf das Einzelziel.
        cleave_hits = 0
        if weapon_sub != "bow" or is_mounted:
            fwd_x = math.sin(p["rot_y"])
            fwd_z = math.cos(p["rot_y"])
            if is_mounted:
                cleave_range = atk_range + 3.2
                max_cleave_targets = 8
                min_front_dot = -1.0  # 360° kontinuierlicher Reit-Schlag im Kreis!
            elif weapon_sub == "two_hand":
                cleave_range = atk_range + 2.8
                max_cleave_targets = 6
                min_front_dot = -0.35  # Weiter Zweihand-Bogen vor dir
            elif weapon_sub == "dagger":
                cleave_range = atk_range + 1.35
                max_cleave_targets = 2
                min_front_dot = 0.15  # Kurze, präzise Dolch-Trefferzone
            else:
                cleave_range = atk_range + 2.2
                max_cleave_targets = 4
                min_front_dot = -0.18

            nearby_mobs = []
            for other in list(self.monsters.values()):
                if other["id"] == mob["id"] or other["mapId"] != p["map_id"] or other["state"] == "dead":
                    continue
                if other["kind"] == "metin":
                    continue
                d_p = dist2d(p["pos_x"], p["pos_z"], other["x"], other["z"])
                d_t = dist2d(mob["x"], mob["z"], other["x"], other["z"])
                if d_p <= cleave_range or d_t <= 3.6 or (other.get("targetPlayerId") == p["player_id"] and d_p <= 5.2):
                    nearby_mobs.append((d_p, d_t, other))

            nearby_mobs.sort(key=lambda item: item[0])

            for d_player, d_target, other in nearby_mobs:
                dx = other["x"] - p["pos_x"]
                dz = other["z"] - p["pos_z"]
                d_len = max(0.01, math.hypot(dx, dz))
                dot = (dx / d_len) * fwd_x + (dz / d_len) * fwd_z

                if is_mounted:
                    # Vom Pferd aus: Kontinuierlicher kreisförmiger 360°-Rundum-Schlag!
                    cleave_mult = 0.90 * finisher_mult
                elif (dot >= min_front_dot) or (d_target <= 2.8):
                    cleave_mult = (0.92 if weapon_sub == "two_hand" else 0.85) * finisher_mult
                elif d_player <= cleave_range:
                    cleave_mult = 0.48 * finisher_mult
                else:
                    continue

                c_dmg, c_crit, c_pierce = self._calculate_damage_to_mob(p, other, power_mult=cleave_mult)
                c_dmg = max(1, c_dmg)
                self._apply_damage_to_mob(
                    p, other, c_dmg, c_crit, is_pierce=c_pierce, skill_id="basic", combo_step=combo_step, is_cleave=True
                )
                cleave_hits += 1
                if cleave_hits >= max_cleave_targets:
                    break

        return {
            "ok": True,
            "damage": dmg,
            "secondDamage": second_dmg,
            "doubleHit": double_hit,
            "crit": is_crit,
            "pierce": is_pierce,
            "targetId": mob["id"],
            "comboStep": combo_step,
            "maxComboSteps": max_combo,
            "isFinisher": is_foot_finisher,
            "isMounted": is_mounted,
            "cleaveHits": cleave_hits,
        }

    def get_player_doctrine_skills(self, p: dict) -> list:
        cls_id = str(p.get("class_id") or "warrior")
        raw_doc = p.get("doctrine")
        if raw_doc is None or raw_doc == "":
            raw_doc = p.get("doctrineIdx")
        if raw_doc is None:
            raw_doc = (p.get("quests") or {}).get("__doctrine_idx__", 0)
        doc_idx, doc_id = resolve_doctrine_id(cls_id, raw_doc)
        p["doctrineIdx"] = doc_idx
        p["doctrine"] = doc_id
        return get_doctrine_skills(cls_id, doc_id)

    def sanitize_player_doctrine_buffs(self, p: dict):
        if not isinstance(p, dict):
            return
        doc_skills = self.get_player_doctrine_skills(p)
        ab = p.get("activeBuffs")
        if not isinstance(ab, dict) or not ab:
            return
        class_skill_map = {sk["id"]: sk for sk in doc_skills}
        for bid, bdata in list(ab.items()):
            sk_def = class_skill_map.get(bid)
            if sk_def is not None:
                if sk_def.get("type") != "buff":
                    ab.pop(bid, None)
                elif isinstance(bdata, dict) and bdata.get("name") != sk_def.get("name"):
                    # Falls sich der Buff-Name durch Doktrin unterscheidet, veralteten Buff entfernen
                    ab.pop(bid, None)

    def perform_player_skill(self, player_id: str, slot_num: int, target_id: Optional[str] = None) -> dict:
        p = self.players.get(player_id)
        if not p or p.get("isDead") or float(p.get("hp", 1)) <= 0:
            return {"ok": False, "error": "Spieler nicht aktiv."}

        now = time.time()
        slot_int = int(slot_num)

        # Spezielle Reit-Fertigkeiten (Militärgaul ab Level 50: Slots 101=Pferde-Stampfen, 102=Pferde-Ansturm, 103=Wellenangriff)
        if slot_int in (101, 102, 103):
            m_data = self._ensure_player_mount_data(p)
            if int(m_data.get("level", 1)) < 50:
                return {
                    "ok": False,
                    "reason": f"🔒 Pferde-Fertigkeiten werden erst ab Pferde-Stufe 50 (Militärgaul) freigeschaltet! (Aktuell: Stufe {m_data.get('level', 1)}/50)",
                }
            if not p.get("active_mount"):
                return {
                    "ok": False,
                    "reason": "🐎 Steige zuerst auf deinen Militärgaul [Strg+H], um Reit-Fertigkeiten vom Pferderücken einzusetzen!",
                }
            h_skill = next((hs for hs in HORSE_SKILLS if hs["slot"] == slot_int), None)
            if not h_skill:
                return {"ok": False, "error": "Reit-Fertigkeit nicht gefunden."}
            cd_until = p["skillCooldowns"].get(h_skill["id"], 0.0)
            if now < cd_until:
                return {"ok": False, "reason": f"🐎 {h_skill['shortName']} lädt noch auf ({cd_until - now:.1f}s)."}
            if p["mp"] < h_skill["mpCost"]:
                return {"ok": False, "reason": "Nicht genügend Ausdauer / MP für Reit-Fertigkeit!"}

            p["mp"] -= h_skill["mpCost"]
            p["lastSkillCastTime"] = now
            p["skillCooldowns"][h_skill["id"]] = now + float(h_skill["cooldown"])

            primary = self._find_valid_target(p, target_id, max_range=h_skill.get("dashRange", 8.5))
            if h_skill["id"] == "horse_charge":
                if primary:
                    dx = primary["x"] - p["pos_x"]
                    dz = primary["z"] - p["pos_z"]
                    d = max(0.1, math.hypot(dx, dz))
                    p["pos_x"] = primary["x"] - (dx / d) * 1.6
                    p["pos_z"] = primary["z"] - (dz / d) * 1.6
                    p["rot_y"] = math.atan2(dx, dz)
                else:
                    p["pos_x"] += math.sin(p.get("rot_y", 0.0)) * 6.0
                    p["pos_z"] += math.cos(p.get("rot_y", 0.0)) * 6.0
                p["teleportSeq"] = int(p.get("teleportSeq", 0)) + 1

            radius = float(h_skill.get("radius", 5.2))
            dss_scale = 1.0 + (float(p.get("computed", {}).get("dssPct", 0.0)) * 0.65) / 100.0
            ninja_wave_bonus = 1.25 if (h_skill["id"] == "horse_wave" and p.get("class_id") == "ninja") else 1.0
            power = float(h_skill.get("powerMult", 2.45)) * 0.68 * dss_scale * ninja_wave_bonus
            hit_count = 0
            any_crit = False
            any_pierce = False

            for mob in list(self.monsters.values()):
                if mob["mapId"] != p["map_id"] or mob["state"] == "dead":
                    continue
                if dist2d(p["pos_x"], p["pos_z"], mob["x"], mob["z"]) <= radius:
                    dmg, is_crit, is_pierce = self._calculate_damage_to_mob(p, mob, power_mult=power)
                    if is_crit:
                        any_crit = True
                    if is_pierce:
                        any_pierce = True
                    self._apply_damage_to_mob(
                        p, mob, dmg, is_crit, is_pierce=is_pierce, skill_id=h_skill["id"], combo_step=4
                    )
                    if mob["state"] != "dead" and mob["kind"] != "metin":
                        if h_skill["id"] == "horse_stomp":
                            self._apply_status_effect_to_mob(mob, "stun", float(h_skill.get("stunSec", 3.0)), p)
                        elif h_skill["id"] == "horse_charge":
                            self._apply_status_effect_to_mob(mob, "stun", 1.8, p)
                        elif h_skill["id"] == "horse_wave":
                            self._apply_status_effect_to_mob(mob, "slow", 5.0, p)
                    hit_count += 1

            self._emit_combat_event(
                p["map_id"],
                "skill_cast",
                p["pos_x"],
                p["pos_z"],
                {
                    "playerId": player_id,
                    "skillId": h_skill["id"],
                    "skillName": h_skill["shortName"],
                    "color": h_skill["color"],
                    "radius": radius,
                    "crit": any_crit,
                    "pierce": any_pierce,
                    "isHorseSkill": True,
                },
            )
            return {"ok": True, "skill": h_skill["name"], "hits": hit_count, "crit": any_crit, "pierce": any_pierce}

        doc_skills = self.get_player_doctrine_skills(p)
        skill = next((s for s in doc_skills if s["slot"] == slot_int), None)
        if not skill:
            return {"ok": False, "error": "Fertigkeit nicht gefunden."}

        # Auf dem Pferd / Reittier sind normale Klassen-Skills gesperrt; Buffs müssen vor dem Aufsteigen aktiviert werden!
        if p.get("active_mount"):
            if skill.get("type") == "buff":
                return {
                    "ok": False,
                    "reason": f"🐎 Buffs ('{skill['name']}') müssen vor dem Aufsteigen zu Fuß aktiviert werden [Strg+H]!",
                }
            return {
                "ok": False,
                "reason": f"🐎 '{skill['name']}' ist nur zu Fuß nutzbar! Nutze vom Sattel aus deine Militärpferd-Fertigkeiten [F1 / F2 / F4]!",
            }
        skill_lvl = int(p.get("skills", {}).get(skill["id"], 0))
        if skill_lvl <= 0:
            return {
                "ok": False,
                "error": f"⚠️ '{skill['name']}' ist noch auf Stufe 0 – vergib zuerst mindestens 1 Fertigkeitspunkt!",
            }

        # Globaler Skill-Cooldown (1.45s), damit Fertigkeiten nicht gleichzeitig gespammt werden
        if now - p.get("lastSkillCastTime", 0.0) < 1.45:
            return {"ok": False, "error": "Fertigkeits-Rhythmus aktiv (kurz warten)."}

        cd_until = p["skillCooldowns"].get(skill["id"], 0.0)
        if now < cd_until:
            return {"ok": False, "error": f"{skill['name']} lädt noch auf ({cd_until - now:.1f}s)."}

        if p["mp"] < skill["mpCost"]:
            return {"ok": False, "error": "Nicht genügend Mana (MP)!"}

        p["mp"] -= skill["mpCost"]
        p["lastSkillCastTime"] = now
        p["lastBasicAttack"] = max(p.get("lastBasicAttack", 0.0), now - 0.35)
        cast_spd = float(p.get("computed", {}).get("castSpeedPct", 0.0))
        eff_cd = float(skill["cooldown"]) * max(0.55, 1.0 - (cast_spd * 0.65) / 100.0)
        p["skillCooldowns"][skill["id"]] = now + eff_cd

        skill_tier = 5 if skill_lvl >= 50 else (4 if skill_lvl >= 40 else (3 if skill_lvl >= 30 else (2 if skill_lvl >= 20 else 1)))
        lvl_mult = 1.0 + (skill_lvl - 1) * 0.045
        int_scale = 1.0 + max(0, int(p.get("int_stat", 10)) - 10) * 0.008 if p.get("class_id") in ("shaman", "sura") else 1.0
        p_cls = p.get("class_id", "warrior")
        p_gender = p.get("gender", "m")
        _p_doc_idx, p_doctrine = resolve_doctrine_id(p_cls, p.get("doctrine") or p.get("doctrineIdx", 0))
        p["doctrineIdx"] = _p_doc_idx
        p["doctrine"] = p_doctrine

        # 1. Selbst-Buff (z. B. Aura des Schwerts, Starker Körper, Federschreiten, Verzauberte Klinge, Hilfe des Drachen)
        if skill["type"] == "buff":
            raw_atk_pct = float(skill.get("buffAtkPct", 0))
            raw_matk_pct = float(skill.get("buffMagicAtkPct", raw_atk_pct))
            raw_move_spd = float(skill.get("buffSpeedPct", 0))
            raw_atk_spd = float(skill.get("buffAtkSpeedPct", 0))
            buff_entry = {
                "name": skill["name"],
                "skillLevel": skill_lvl,
                "skillTier": skill_tier,
                "atkPct": int(raw_atk_pct * lvl_mult * int_scale),
                "magicAtkPct": int(raw_matk_pct * lvl_mult * int_scale),
                "hpAbsorbPct": round(float(skill.get("buffHpAbsorbPct", 0.0)) * lvl_mult, 1),
                "defPct": int(float(skill.get("buffDefPct", 0)) * lvl_mult * int_scale),
                "critPct": int(float(skill.get("buffCritPct", 0)) * lvl_mult),
                "speedPct": int(raw_move_spd + raw_atk_spd),
                "expiresAt": now + skill.get("duration", 12.0),
            }
            if raw_atk_spd > 0 and raw_move_spd > 0:
                buff_entry["atkSpeedPct"] = int(raw_atk_spd)
                buff_entry["moveSpeedPct"] = int(raw_move_spd)
            elif raw_atk_spd > 0:
                buff_entry["atkSpeedPct"] = int(raw_atk_spd)
                buff_entry["moveSpeedPct"] = 0
            p["activeBuffs"][skill["id"]] = buff_entry
            self.compute_player_combat_stats(p)
            self._emit_combat_event(
                p["map_id"],
                "skill_buff",
                p["pos_x"],
                p["pos_z"],
                {
                    "playerId": player_id,
                    "skillId": skill["id"],
                    "skillName": skill["name"],
                    "skillLevel": skill_lvl,
                    "skillTier": skill_tier,
                    "classId": p_cls,
                    "gender": p_gender,
                    "doctrine": p_doctrine,
                    "color": skill["color"],
                },
            )
            return {"ok": True, "skill": skill["name"], "type": "buff", "skillLevel": skill_lvl, "skillTier": skill_tier}

        # 2. Heilzauber (Seelenweber: Kurieren)
        if skill["type"] == "heal":
            heal_amount = int(p["max_hp"] * (skill.get("healPct", 35) / 100.0) * lvl_mult * int_scale)
            p["hp"] = min(p["max_hp"], p["hp"] + heal_amount)
            self._emit_combat_event(
                p["map_id"],
                "heal",
                p["pos_x"],
                p["pos_z"],
                {
                    "playerId": player_id,
                    "skillId": skill["id"],
                    "amount": heal_amount,
                    "skillName": skill["name"],
                    "skillLevel": skill_lvl,
                    "skillTier": skill_tier,
                    "classId": p_cls,
                    "gender": p_gender,
                    "doctrine": p_doctrine,
                    "color": "#22c55e",
                },
            )
            return {"ok": True, "skill": skill["name"], "healed": heal_amount, "skillLevel": skill_lvl, "skillTier": skill_tier}

        # 3. Dash-Angriff (z. B. Sausen)
        primary = self._find_valid_target(p, target_id, max_range=skill.get("dashRange", 7.5))
        if skill["type"] == "dash_aoe" and primary:
            dx = primary["x"] - p["pos_x"]
            dz = primary["z"] - p["pos_z"]
            d = max(0.1, math.hypot(dx, dz))
            p["pos_x"] = primary["x"] - (dx / d) * 1.8
            p["pos_z"] = primary["z"] - (dz / d) * 1.8
            p["rot_y"] = math.atan2(dx, dz)
            p["teleportSeq"] = int(p.get("teleportSeq", 0)) + 1

        # 4. Flächen- & Burst-Schaden (inkl. FKS / Fertigkeitsschaden & Hinterhalt-Dolch-Bonus)
        radius = float(skill.get("radius", 4.5))
        raw_skill_mult = float(skill.get("powerMult", 2.0))
        fks_mult = 1.0 + (float(p.get("computed", {}).get("skillDmgPct", 0.0)) * 0.85) / 100.0
        dagger_ambush_mult = 1.24 if (skill["id"] == "ambush" and p.get("computed", {}).get("weaponSubType") == "dagger") else 1.0
        power = (1.0 + (raw_skill_mult - 1.0) * 0.48) * lvl_mult * fks_mult * dagger_ambush_mult * int_scale
        hit_count = 0
        any_crit = False
        any_pierce = False
        center_x = primary["x"] if (primary and skill["type"] == "burst") else p["pos_x"]
        center_z = primary["z"] if (primary and skill["type"] == "burst") else p["pos_z"]

        for mob in list(self.monsters.values()):
            if mob["mapId"] != p["map_id"] or mob["state"] == "dead":
                continue
            if dist2d(center_x, center_z, mob["x"], mob["z"]) <= radius:
                dmg, is_crit, is_pierce = self._calculate_damage_to_mob(p, mob, power_mult=power)
                if is_crit:
                    any_crit = True
                if is_pierce:
                    any_pierce = True
                self._apply_damage_to_mob(
                    p, mob, dmg, is_crit, is_pierce=is_pierce, skill_id=skill["id"], combo_step=4
                )
                # Klassen-Fertigkeiten verursachen charakteristische Statusveränderungen
                if mob["state"] != "dead" and mob["kind"] != "metin":
                    cid = p.get("class_id", "warrior")
                    if skill.get("stunSec"):
                        self._apply_status_effect_to_mob(mob, "stun", float(skill["stunSec"]), p)
                    elif skill["type"] == "dash_aoe":
                        self._apply_status_effect_to_mob(mob, "stun", 1.8, p)
                    elif cid == "warrior":
                        self._apply_status_effect_to_mob(mob, "armor_break", 7.0, p)
                        if is_crit:
                            self._apply_status_effect_to_mob(mob, "bleed", 5.0, p)
                    elif cid == "ninja":
                        self._apply_status_effect_to_mob(mob, "poison", 6.0, p)
                        self._apply_status_effect_to_mob(mob, "bleed", 5.0, p)
                    elif cid == "sura":
                        self._apply_status_effect_to_mob(mob, "burn", 6.0, p)
                        self._apply_status_effect_to_mob(mob, "slow", 5.0, p)
                    elif cid == "shaman":
                        self._apply_status_effect_to_mob(mob, "burn", 6.0, p)
                        if random.uniform(0, 100) <= 55.0:
                            self._apply_status_effect_to_mob(mob, "stun", 1.4, p)

                hit_count += 1
                if skill["type"] == "burst" and hit_count >= 2:
                    break

        self._emit_combat_event(
            p["map_id"],
            "skill_cast",
            p["pos_x"],
            p["pos_z"],
            {
                "playerId": player_id,
                "skillId": skill["id"],
                "skillName": skill["name"],
                "skillLevel": skill_lvl,
                "skillTier": skill_tier,
                "classId": p_cls,
                "gender": p_gender,
                "doctrine": p_doctrine,
                "color": skill["color"],
                "radius": radius,
                "crit": any_crit,
                "pierce": any_pierce,
            },
        )
        return {"ok": True, "skill": skill["name"], "hits": hit_count, "crit": any_crit, "pierce": any_pierce, "skillLevel": skill_lvl, "skillTier": skill_tier}

    def _find_valid_target(self, p: dict, preferred_id: Optional[str], max_range: float) -> Optional[dict]:
        tid = preferred_id or p.get("targetId")
        if tid and tid in self.monsters:
            m = self.monsters[tid]
            if m["mapId"] == p["map_id"] and m["state"] != "dead":
                if dist2d(p["pos_x"], p["pos_z"], m["x"], m["z"]) <= max_range:
                    return m

        # Suche nächstes Monster in Reichweite
        nearby = [
            m for m in self.monsters.values()
            if m["mapId"] == p["map_id"]
            and m["state"] != "dead"
            and dist2d(p["pos_x"], p["pos_z"], m["x"], m["z"]) <= max_range
        ]
        if not nearby:
            return None
        return min(nearby, key=lambda m: dist2d(p["pos_x"], p["pos_z"], m["x"], m["z"]))

    def _calculate_damage_to_mob(self, p: dict, mob: dict, power_mult: float = 1.0) -> Tuple[int, bool, bool]:
        comp = p["computed"]
        base_offense = max(comp["atk"], comp["magicAtk"])

        # Sanfte Level-Balance: Wenn ein hochstufiger Charakter auf niedrigstufige Monster schlägt,
        # wird der Überschuss-Angriff gedämpft, damit auch Kämpfe in frühen Regionen spürbar bleiben
        mob_lvl = max(1, int(mob.get("level", 1)))
        p_lvl = max(1, int(p.get("level", 1)))
        if p_lvl > mob_lvl + 6:
            expected_atk = 52.0 + mob_lvl * 8.5
            if base_offense > expected_atk:
                base_offense = expected_atk + (base_offense - expected_atk) * 0.28

        raw = base_offense * power_mult * random.uniform(0.93, 1.07)

        # SSOT Teil II Abs. 1: "Stark gegen Monster" erhöht Schaden AUSSCHLIESSLICH an normalen Monstern (NIEMALS an Bossen oder Monolithen!)
        if mob["kind"] == "metin":
            raw *= 1.0 + (comp["vsMetinPct"] * 0.65) / 100.0
        elif mob.get("isBoss") or mob.get("isRiftWorldBoss") or mob.get("isMonolithEliteBoss") or mob.get("kind") == "boss":
            raw *= 1.0 + (comp["vsBossPct"] * 0.65) / 100.0
        else:
            raw *= 1.0 + (comp["vsMonsterPct"] * 0.65) / 100.0

        is_crit = random.uniform(0, 100) <= comp.get("critChance", 10.0)
        is_pierce = random.uniform(0, 100) <= comp.get("pierceChance", 8.0)

        mob_def = float(mob.get("def", 15))
        # Rüstungsbruch-Statuseffekt senkt die Verteidigung des Ziels um 25%
        mob_effects = mob.get("statusEffects", {})
        if "armor_break" in mob_effects and time.time() < mob_effects["armor_break"].get("expiresAt", 0.0):
            mob_def *= 0.75

        if is_pierce:
            # Durchbohrender Treffer (DB): Durchbricht und ignoriert die Rüstung des Feindes komplett!
            # Zusätzlich wird die durchbrochene Rüstung als Bonus-Schaden angerechnet.
            mitigated = raw + mob_def * 0.85
        else:
            # Normale Rüstungs-Reduktion (Prozentual + Flach)
            armor_mult = 110.0 / (110.0 + mob_def * 0.95)
            mitigated = raw * armor_mult - mob_def * 0.55

        # Sicherheits-Cap gegen One-Shots auf den Basis-Treffer (vor Krit-Verdopplung!)
        max_hp = max(100, int(mob.get("maxHp", 500)))
        if mob["kind"] == "metin" and mob.get("monolithState") == "erwacht":
            # Stufe 3 (Erwacht): Extrem zähe Obsidian-Panzerung (max. 2.8% Basis-Schaden pro Schlag)
            cap_dmg = max_hp * 0.028
        elif mob["isBoss"] or mob["kind"] == "metin":
            cap_dmg = max_hp * 0.085
        elif mob.get("isElite"):
            cap_dmg = max_hp * 0.22
        else:
            cap_dmg = max_hp * 0.34

        if mitigated > cap_dmg:
            mitigated = cap_dmg + (mitigated - cap_dmg) * 0.15

        mitigated = max(6.0, mitigated)

        # Kritischer Treffer (Krit): Verdoppelt den Schaden exakt (2.0x)!
        if is_crit:
            mitigated *= 2.0

        dmg = max(8, int(round(mitigated)))
        return dmg, is_crit, is_pierce

    def _apply_damage_to_mob(
        self,
        p: dict,
        mob: dict,
        dmg: int,
        is_crit: bool,
        is_pierce: bool = False,
        skill_id: str = "basic",
        combo_step: int = 1,
        is_cleave: bool = False,
    ):
        # Stufe 3 (Erwacht) Riss-Bollwerk: Solange ein vom Monolithen beschworener Riss-Boss lebt,
        # absorbiert das Riss-Bollwerk 65% des Schadens am Monolithen!
        if mob["kind"] == "metin" and mob.get("monolithState") == "erwacht":
            active_rift_boss = next(
                (
                    om for om in self.monsters.values()
                    if om.get("monolithBossOf") == mob["id"]
                    and om.get("state") != "dead"
                    and om.get("mapId") == mob["mapId"]
                ),
                None,
            )
            if active_rift_boss is not None:
                dmg = max(1, int(round(dmg * 0.35)))
                now_ts = time.time()
                if now_ts - float(mob.get("lastBulwarkWarnAt", 0.0)) >= 9.0:
                    mob["lastBulwarkWarnAt"] = now_ts
                    self.add_chat_message(
                        "Riss-Chronist",
                        f"🛡️ Riss-Bollwerk aktiv! '{active_rift_boss['name']}' schirmt {mob['name']} ab (-65% Schaden). Besiege zuerst den beschworenen Riss-Boss!",
                        channel="event",
                    )

        now_hit = time.time()
        if not mob.get("_combatStartedAt") or (now_hit - float(mob.get("_lastHitAt", 0.0) or 0.0) > 18.0):
            mob["_combatStartedAt"] = now_hit
            if mob["kind"] != "metin":
                sp_init = self._get_species_profile(mob)
                sp_init["encounters"] = int(sp_init.get("encounters", 0)) + 1
        mob["_lastHitAt"] = now_hit

        is_mounted = bool(p.get("active_mount"))
        max_combo = int(p.get("computed", {}).get("maxComboSteps", 6))
        is_foot_finisher = (not is_mounted) and (combo_step == max_combo) and (skill_id == "basic")
        is_knockback_skill = skill_id not in ("basic", "basic_dagger_twin", "horse_wave")
        weapon_sub = p.get("computed", {}).get("weaponSubType") or "one_hand"

        # Adaptives Spezies-Lernen (ARC-Raiders-Stil):
        # 1) Gelernte Ausweich-Sprünge (Evade-Dash) gegen Finisher & schwere Skills
        # 2) Anti-Cleave-Flankieren (Spezies merkt sich Flächenschläge und fächert weiter in den Rücken auf)
        evaded_heavy = False
        if mob["kind"] != "metin":
            sp = self._get_species_profile(mob)
            if is_cleave:
                sp["cleaveHitsTaken"] = int(sp.get("cleaveHitsTaken", 0)) + 1
                sp["flankSpread"] = round(min(1.0, float(sp.get("flankSpread", 0.35)) + 0.0035), 4)
                # Sofortige Mikro-Adaption: Monster weicht seitlich aus dem Cleave-Kegel in Richtung Flanke/Rücken!
                cur_flank = float(mob.get("flankAngleOffset", 0.45))
                flank_sign = 1.0 if cur_flank >= 0.0 else -1.0
                mob["flankAngleOffset"] = flank_sign * min(2.45, max(1.25, abs(cur_flank) + 0.38))

            if is_foot_finisher or is_knockback_skill:
                sp["finisherHitsTaken"] = int(sp.get("finisherHitsTaken", 0)) + 1
                sp["evadeChance"] = round(min(0.32, float(sp.get("evadeChance", 0.14)) + 0.0015), 4)
                evade_cd = 5.8 if mob.get("isBoss") or mob.get("isElite") else 7.2
                if (
                    mob["hp"] > dmg
                    and (now_hit - float(mob.get("_lastEvadeAt", 0.0))) >= evade_cd
                    and random.random() < float(sp.get("evadeChance", 0.16))
                ):
                    evaded_heavy = True
                    mob["_lastEvadeAt"] = now_hit
                    sp["successfulDodges"] = int(sp.get("successfulDodges", 0)) + 1
                    dmg = max(1, int(round(dmg * 0.35)))
                    # Taktischer Seitensprung (2.1m) orthogonal um den Angreifer herum
                    dx_ev = mob["x"] - p["pos_x"]
                    dz_ev = mob["z"] - p["pos_z"]
                    d_ev = max(0.1, math.hypot(dx_ev, dz_ev))
                    tang_sign = 1.0 if float(mob.get("flankAngleOffset", 0.3)) >= 0.0 else -1.0
                    dash_x = (-dz_ev / d_ev) * tang_sign * 2.15 + (dx_ev / d_ev) * 0.45
                    dash_z = (dx_ev / d_ev) * tang_sign * 2.15 + (dz_ev / d_ev) * 0.45
                    max_ev_bound = 1320.0 if mob.get("mapId") == "morgenwacht" else (1720.0 if mob.get("mapId") == "orktal" else 515.0)
                    nx_ev = max(-max_ev_bound, min(max_ev_bound, mob["x"] + dash_x))
                    nz_ev = max(-max_ev_bound, min(max_ev_bound, mob["z"] + dash_z))
                    if not is_in_safe_zone(mob["mapId"], nx_ev, nz_ev):
                        mob["x"] = round(nx_ev, 2)
                        mob["z"] = round(nz_ev, 2)
                    mob["aiAction"] = "evade_dash"
                    mob["aiActionSeq"] = int(mob.get("aiActionSeq", 0)) + 1
                    mob["aiActionAt"] = now_hit
                    self._emit_combat_event(
                        mob["mapId"],
                        "combat_feedback",
                        mob["x"],
                        mob["z"],
                        {
                            "playerId": p["player_id"],
                            "mobId": mob["id"],
                            "feedbackType": "evade_dash",
                            "text": "⚡ AUSWEICHSPRUNG!",
                            "color": "#38bdf8",
                        },
                    )
            self._update_species_evolution_stage(sp)
            mob["aiTier"] = int(sp.get("evolutionStage", 1))
            self._save_monster_species_ai_maybe(now_hit)

        mob["hp"] = max(0, mob["hp"] - dmg)
        will_die = mob["hp"] <= 0
        knockback = False

        if mob["kind"] != "metin" and not mob["targetPlayerId"]:
            mob["targetPlayerId"] = p["player_id"]
            mob["state"] = "chase"
            if mob.get("packId"):
                pack_id = mob["packId"]
                for mate in self.monsters.values():
                    if (
                        mate.get("packId") == pack_id
                        and mate["mapId"] == mob["mapId"]
                        and mate["state"] != "dead"
                        and not mate.get("targetPlayerId")
                    ):
                        mate["targetPlayerId"] = p["player_id"]
                        mate["state"] = "chase"

        # 3) Taktischer Hilferuf (Call for Reinforcements) bei < 32% HP für gelernte Rudel-/Kriegstrupp-Spezies
        if (
            mob["kind"] != "metin"
            and not will_die
            and not mob.get("_calledHelp")
            and 0 < mob["hp"] <= mob["maxHp"] * 0.32
        ):
            sp_help = self._get_species_profile(mob)
            if sp_help.get("family") in ("wolf_pack", "orc_warband", "eid_tactical"):
                mob["_calledHelp"] = True
                called_count = 0
                for ally in self.monsters.values():
                    if (
                        ally["id"] != mob["id"]
                        and ally["mapId"] == mob["mapId"]
                        and ally["kind"] == "monster"
                        and ally["state"] != "dead"
                        and not ally.get("targetPlayerId")
                        and dist2d(mob["x"], mob["z"], ally["x"], ally["z"]) <= 15.5
                    ):
                        ally["targetPlayerId"] = p["player_id"]
                        ally["state"] = "chase"
                        called_count += 1
                        if called_count >= 2:
                            break
                if called_count > 0:
                    sp_help["reinforcementsCalled"] = int(sp_help.get("reinforcementsCalled", 0)) + called_count
                    mob["aiAction"] = "call_help"
                    mob["aiActionSeq"] = int(mob.get("aiActionSeq", 0)) + 1
                    mob["aiActionAt"] = now_hit
                    self._emit_combat_event(
                        mob["mapId"],
                        "combat_feedback",
                        mob["x"],
                        mob["z"],
                        {
                            "playerId": p["player_id"],
                            "mobId": mob["id"],
                            "feedbackType": "call_help",
                            "text": f"📯 HILFERUF (+{called_count})!",
                            "color": "#f59e0b",
                        },
                    )

        # Wuchtiges Treffer-Feedback: Gegner geraten bei schweren Treffern ins Wanken, Angriffe lassen sich unterbrechen!
        stagger = bool((is_crit or is_pierce or is_foot_finisher or weapon_sub == "two_hand" or skill_id != "basic") and not evaded_heavy)
        if stagger and mob["kind"] != "metin" and not will_die:
            atk_iv = float(mob.get("attackInterval", 1.4))
            mob["lastAttackTime"] = max(float(mob.get("lastAttackTime", 0.0)), time.time() - atk_iv + 0.36)

        # Rückstoß-Physik (Knockback):
        # - Zu Fuß: Der letzte Schlag der 4..6er-Combo wirft Monster zu Boden / stößt sie zurück!
        # - Vom Pferd aus: Kontinuierliche Schläge im Kreis OHNE Wegstoßen (nur beim Todesschlag oder Pferde-Ansturm/Stampfen)!
        if mob["kind"] != "metin" and not evaded_heavy and (is_foot_finisher or will_die or is_knockback_skill):
            dx = mob["x"] - p["pos_x"]
            dz = mob["z"] - p["pos_z"]
            d_len = math.hypot(dx, dz)
            if d_len < 0.05:
                dx = math.sin(p.get("rot_y", 0.0))
                dz = math.cos(p.get("rot_y", 0.0))
                d_len = 1.0
            nx = dx / d_len
            nz = dz / d_len
            kb_dist = 2.25 if will_die else (1.85 if is_foot_finisher else 1.45)
            if mob.get("isBoss"):
                kb_dist *= 0.35
            max_kb_bound = 1320.0 if mob.get("mapId") == "morgenwacht" else (1720.0 if mob.get("mapId") == "orktal" else 515.0)
            mob["x"] = round(max(-max_kb_bound, min(max_kb_bound, mob["x"] + nx * kb_dist)), 2)
            mob["z"] = round(max(-max_kb_bound, min(max_kb_bound, mob["z"] + nz * kb_dist)), 2)
            knockback = True

        self._emit_combat_event(
            mob["mapId"],
            "damage_mob",
            mob["x"],
            mob["z"],
            {
                "playerId": p["player_id"],
                "attackerId": p["player_id"],
                "targetId": mob["id"],
                "damage": dmg,
                "crit": is_crit,
                "pierce": is_pierce,
                "skillId": skill_id,
                "comboStep": combo_step,
                "maxComboSteps": max_combo,
                "isFinisher": is_foot_finisher,
                "stagger": stagger,
                "knockback": knockback,
                "killed": will_die,
                "isCleave": is_cleave,
                "attackerX": round(p["pos_x"], 2),
                "attackerZ": round(p["pos_z"], 2),
            },
        )

        # Rissmonolith-Kampfphasen (Phase 1..4), Teilnehmer-Tracking & Weltboss-Beschwörung bei Erwachten Monolithen
        if mob["kind"] == "metin":
            mob["lastDamagedAt"] = time.time()
            mob.setdefault("participants", set()).add(p["player_id"])
            if not mob.get("guardsSpawned"):
                mob["guardsSpawned"] = True
                self._spawn_monolith_guardians(mob, count=2, target_player_id=p["player_id"])
            # WICHTIG: Rissmonolithen steigen NIEMALS von alleine durch Schläge auf!
            # Stufe 1 -> 2 erfordert 1x Monolithensplitter, Stufe 2 -> 3 erfordert 1x Erwachter Risskern.
            cur_m_state = mob.get("monolithState", "schlafend")
            rift_aggro_rad = 48.0 if cur_m_state == "erwacht" else (34.0 if cur_m_state == "instabil" else 22.0)
            for other_m in self.monsters.values():
                if (
                    other_m["mapId"] == mob["mapId"]
                    and other_m["state"] != "dead"
                    and other_m.get("kind") == "monster"
                ):
                    is_guard = other_m.get("monolithGuardOf") == mob["id"] or other_m.get("monolithBossOf") == mob["id"]
                    is_summon = other_m.get("isSummon") and dist2d(other_m["x"], other_m["z"], mob["x"], mob["z"]) <= 40.0
                    is_near = dist2d(other_m["x"], other_m["z"], mob["x"], mob["z"]) <= rift_aggro_rad
                    if is_guard or is_summon or is_near:
                        other_m["riftAggroMonolithId"] = mob["id"]
                        if other_m.get("targetPlayerId") != p["player_id"]:
                            other_m["targetPlayerId"] = p["player_id"]
                            other_m["state"] = "chase"
        if mob["kind"] == "metin" and mob["hp"] > 0:
            hp_ratio = mob["hp"] / mob["maxHp"]
            # Stufe 3 (Erwacht): Spawnt exakt 1 Weltboss (max. 1 pro Mapgebiet)!
            if mob.get("monolithState") == "erwacht" and not mob.get("worldBossSummoned"):
                self._spawn_monolith_world_boss(mob, actor=p)

            if hp_ratio <= 0.10:
                new_phase = 4
            elif hp_ratio <= 0.40:
                new_phase = 3
            elif hp_ratio <= 0.70:
                new_phase = 2
            else:
                new_phase = 1
            mob["combatPhase"] = new_phase
            mob["combatPhaseText"] = MONOLITH_COMBAT_PHASES.get(new_phase, MONOLITH_COMBAT_PHASES[1])

            wave_mob_id = self._resolve_monolith_wave_monster(mob)
            is_erwacht_state = mob.get("monolithState") == "erwacht"
            is_instabil_state = mob.get("monolithState") == "instabil"
            base_wave_count = 4 if is_erwacht_state else (3 if is_instabil_state else 2)
            wave_count = base_wave_count
            wave_thresholds = (
                (0.70, "Phase 2 (Dimensionsriss & 1. Welle)"),
                (0.40, "Phase 3 (Schwebende Fragmente & 2. Welle)"),
                (0.15, "Phase 4 (Kritische Energieüberladung)"),
            )
            for threshold, phase_title in wave_thresholds:
                if hp_ratio <= threshold and threshold not in mob["wavesSpawned"]:
                    mob["wavesSpawned"].append(threshold)
                    # 1. Normale Wellen-Monster spawnen (für alle Stufen ausschließlich normale, zum Monolith-Level passende Monster!)
                    for i in range(wave_count):
                        w_mob_id = self._resolve_monolith_wave_monster(mob)
                        ang = (math.pi * 2 * i) / wave_count + random.uniform(-0.3, 0.3)
                        sx = mob["x"] + math.cos(ang) * 3.6
                        sz = mob["z"] + math.sin(ang) * 3.6
                        summoned = self._create_monster_instance(mob["mapId"], w_mob_id, sx, sz, 8.0, is_summon=True)
                        self._scale_monolith_guard_to_level(summoned, mob, is_erwacht=is_erwacht_state)
                        summoned["monolithGuardOf"] = mob["id"]
                        summoned["targetPlayerId"] = p["player_id"]
                        summoned["state"] = "chase"

                    # 2. Instabile Rissmonolithen: Spawnen ihre restlichen Elite-Bosse je nach Level!
                    # (Lv. 5: insgesamt 1 Elite-Boss; Lv. 10–15: 2 Elite-Bosse; Lv. 20–25: 3 Elite-Bosse; Lv. 30+: 4 Elite-Bosse)
                    if is_instabil_state:
                        total_elites = self._get_unstable_elite_boss_count(int(mob.get("level", 5)))
                        spawned_so_far = int(mob.get("eliteBossesSpawned", 0))
                        if spawned_so_far < total_elites:
                            self._spawn_unstable_elite_boss(
                                mob, index=spawned_so_far, total=total_elites, target_player_id=p["player_id"]
                            )

                    # Äther-Druckwelle des Rissmonolithen trifft nahe Angreifer (mit Radius-Dämpfung ab > 3.5m gemäß bal_prop_02)
                    d_shock = dist2d(p["pos_x"], p["pos_z"], mob["x"], mob["z"])
                    if d_shock <= 6.5 and not p.get("isDead"):
                        dist_atten = max(0.38, 1.0 - max(0.0, d_shock - 3.5) * 0.20)
                        shock_dmg = max(10, int(round((mob.get("atk", 36) * 1.20 - p.get("computed", {}).get("def", 20) * 0.35) * dist_atten)))
                        p["hp"] = max(0, int(p["hp"] - shock_dmg))
                        self._emit_combat_event(
                            mob["mapId"],
                            "damage_player",
                            p["pos_x"],
                            p["pos_z"],
                            {"playerId": p["player_id"], "mobId": mob["id"], "damage": shock_dmg, "crit": True},
                        )
                        if p["hp"] <= 0:
                            self._trigger_player_death(p, mob)
                    self._emit_combat_event(
                        mob["mapId"],
                        "metin_wave",
                        mob["x"],
                        mob["z"],
                        {"metinId": mob["id"], "text": f"⚡ {mob['name']} erreicht {phase_title} (+{wave_count} Wächter)!"},
                    )

        # Tod & Belohnungen
        if mob["hp"] <= 0:
            self._handle_mob_death(p, mob)

    def _handle_mob_death(self, killer: dict, mob: dict):
        now = time.time()
        raw_ttk = max(0.8, min(90.0, now - float(mob.get("_combatStartedAt") or (now - 3.2))))
        mob["_combatStartedAt"] = None
        mob["_lastHitAt"] = None
        mob["state"] = "dead"
        respawn_sec = self.get_mob_respawn_sec(mob)
        mob["deadUntil"] = now + respawn_sec
        mob["targetPlayerId"] = None
        if killer.get("targetId") == mob["id"]:
            killer["targetId"] = None
        if str(killer.get("player_id", "")).startswith("bot_"):
            self._update_bot_evolution_v3_on_kill(killer, mob, raw_ttk, now)

        tpl = MONSTER_TEMPLATES[mob["templateId"]]
        comp = killer["computed"]
        if mob.get("isRiftWorldBoss"):
            loot_mult = 4.0
        elif mob.get("isMonolithEliteBoss"):
            loot_mult = 1.8
        elif mob["kind"] == "metin":
            loot_mult = float(mob.get("lootMultiplier", 1.0))
        else:
            loot_mult = 1.0
        is_summoned_guard = bool(mob.get("isSummon", False)) and not bool(mob.get("allowSummonLoot", False)) and not bool(mob.get("isRiftWorldBoss", False))

        # Kombinierte Levelbereichs-Skalierung (Charakter-Level vs. Map-Levelbereich & Monster-Level):
        # Nur im passenden Levelbereich von Charakter, Karte und Monster gibt es volle EXP & Drops.
        # Je höher man kommt und sich vom Map-/Monster-Level entfernt, desto weniger bekommt man (bis auf 0%).
        mob_map_id = mob.get("mapId", killer.get("map_id", "morgenwacht"))
        lvl_penalty = self.compute_level_reward_penalty(
            int(killer.get("level", 1)),
            int(mob.get("level", 1)),
            mob_map_id,
            for_exp=False,
        )
        exp_lvl_penalty = self.compute_level_reward_penalty(
            int(killer.get("level", 1)),
            int(mob.get("level", 1)),
            mob_map_id,
            for_exp=True,
        )

        # 1. Erfahrungspunkte (nur solange im gültigen Levelbereich; ab Lv. 38 in Map 1/2 stark gedämpft)
        party_id = killer.get("partyId")
        party = self.parties.get(party_id) if party_id else None
        nearby_party_members = []
        if party:
            for mid in party.get("memberIds", [])[:8]:
                mp = self.players.get(mid)
                if (
                    mp
                    and mp.get("online")
                    and not mp.get("isDead")
                    and mp.get("map_id") == killer.get("map_id")
                    and dist2d(mp["pos_x"], mp["pos_z"], killer["pos_x"], killer["pos_z"]) <= 180.0
                ):
                    nearby_party_members.append(mp)

        party_count = min(8, len(nearby_party_members))
        if party and party_count >= 2:
            party["monstersSlainTogether"] = int(party.get("monstersSlainTogether", 0)) + 1
            for idx_pa, mpa in enumerate(nearby_party_members):
                mpa["sharedPartyKills"] = int(mpa.get("sharedPartyKills", 0)) + 1
                for mpb in nearby_party_members[idx_pa + 1 :]:
                    self._adjust_bot_friendship(mpa["player_id"], mpb["player_id"], 0.30, "sharedKills")
        active_evt_id = str((getattr(self, "world_event", None) or {}).get("id", ""))
        evt_exp_mult = 1.30 if active_evt_id == "imperial_blessing" else 1.0
        evt_yang_mult = 1.25 if active_evt_id == "imperial_blessing" else 1.0
        if lvl_penalty <= 0.0 and exp_lvl_penalty <= 0.0 and party_count <= 1:
            exp_gain = 0
            yang_gain = 0
            rep_gain = 0
        else:
            summon_exp_mult = 0.35 if is_summoned_guard else 1.0
            # Gruppen-EXP-Regel: Man teilt sich die erhaltene EXP in der Gruppe und erhält +20% zusätzliche EXP
            # für jedes weitere Gruppenmitglied (maximal 8 Mitglieder in einer Gruppe -> bis zu +140% Gesamt-EXP!).
            party_bonus_mult = 1.0 + max(0, party_count - 1) * 0.20 if party_count >= 2 else 1.0
            base_exp_pool = tpl["exp"] * 0.26 * loot_mult * summon_exp_mult * party_bonus_mult * evt_exp_mult
            per_member_exp_share = base_exp_pool / max(1, party_count)

            raw_killer_exp = per_member_exp_share * exp_lvl_penalty * (1.0 + comp["expBonusPct"] / 100.0)
            exp_gain = int(round(raw_killer_exp)) if exp_lvl_penalty > 0.0 else 0
            if exp_gain == 0 and exp_lvl_penalty >= 0.25:
                exp_gain = 1
            if killer["level"] < MAX_PLAYER_LEVEL and exp_gain > 0:
                killer["exp"] += exp_gain

            # Erhaltene Gruppen-EXP (inkl. +20% Bonus pro weiterem Mitglied) gerecht unter allen nahen Gruppenmitgliedern (max. 8) teilen
            if party_count >= 2:
                for mp in nearby_party_members:
                    if mp["player_id"] == killer["player_id"]:
                        continue
                    mp_pen = self.compute_level_reward_penalty(
                        int(mp.get("level", 1)),
                        int(mob.get("level", 1)),
                        mob.get("mapId", mp.get("map_id", "morgenwacht")),
                        for_exp=True,
                    )
                    if mp_pen > 0.0 and mp["level"] < MAX_PLAYER_LEVEL:
                        mp_comp = mp.get("computed") or {}
                        mp_exp_bonus_pct = float(mp_comp.get("expBonusPct", 0.0))
                        shared_exp = max(1, int(round(per_member_exp_share * mp_pen * (1.0 + mp_exp_bonus_pct / 100.0))))
                        mp["exp"] += shared_exp
                        mp_af = mp.setdefault("autofarm", {})
                        mp_stats = self.ensure_autofarm_stats(mp_af)
                        mp_stats["expEarned"] = int(mp_stats.get("expEarned", 0)) + shared_exp
                        mp_leveled = False
                        while mp["level"] < MAX_PLAYER_LEVEL and mp["exp"] >= exp_needed_for_level(mp["level"]):
                            mp["exp"] -= exp_needed_for_level(mp["level"])
                            mp["level"] += 1
                            mp["stat_points"] += 3
                            mp["skill_points"] += 1
                            self.compute_player_combat_stats(mp)
                            mp["hp"] = mp["max_hp"]
                            mp["mp"] = mp["max_mp"]
                            mp_leveled = True
                        if mp_leveled:
                            if str(mp.get("player_id", "")).startswith("bot_") and int(mp.get("level", 1)) >= self.BOT_RESET_LEVEL:
                                mp = self._reset_bot_on_level_cap(mp, now=now)
                            else:
                                self._emit_combat_event(
                                    mp["map_id"],
                                    "level_up",
                                    mp["pos_x"],
                                    mp["pos_z"],
                                    {"playerId": mp["player_id"], "level": mp["level"], "name": mp["name"]},
                                )
                                self.add_chat_message(
                                    "System",
                                    f"🎉 {mp['name']} hat Level {mp['level']} erreicht!",
                                    channel="system",
                                )
            # Begleiter (Starter-Pet) erhält ebenfalls Pet-EXP im Kampf (inkl. Erfahrungsrausch-Bonus)
            self._award_pet_exp(killer, max(8, int(round(tpl["exp"] * 0.45 * loot_mult * evt_exp_mult))))

            # 2. Direktes Gold + Rangpunkte — SSOT Teil I Abs. 3: Ausgewogen für Tränke & Schmied-Upgrades ohne Gold-Inflation
            raw_yang = random.randint(tpl["yangMin"], tpl["yangMax"]) * 0.38 * loot_mult * lvl_penalty * evt_yang_mult * (1.0 + comp["yangBonusPct"] / 100.0)
            yang_gain = int(round(raw_yang))
            killer["yang"] += yang_gain
            base_rep = 25 if mob["isBoss"] else (int(round(10 * loot_mult)) if mob["kind"] == "metin" else (5 if mob["isElite"] else 2))
            rep_gain = int(round(base_rep * lvl_penalty))
            killer["reputation"] += rep_gain

        # Auto-Hunt Session-Statistik aktualisieren
        af = killer.setdefault("autofarm", {})
        stats = self.ensure_autofarm_stats(af)
        stats["yangEarned"] = int(stats.get("yangEarned", 0)) + yang_gain
        stats["expEarned"] = int(stats.get("expEarned", 0)) + exp_gain
        if exp_gain <= 0 or exp_lvl_penalty <= 0.15:
            stats["zeroExpStreak"] = int(stats.get("zeroExpStreak", 0)) + 1
        else:
            stats["zeroExpStreak"] = 0
        if mob["isBoss"]:
            stats["bossesSlain"] = int(stats.get("bossesSlain", 0)) + 1
            if af.get("mode") == "dungeon" and lvl_penalty > 0.0:
                stats["dungeonRuns"] = int(stats.get("dungeonRuns", 0)) + 1
                bonus_dg_yang = int(round(600 * lvl_penalty))
                killer["yang"] += bonus_dg_yang
                stats["yangEarned"] += bonus_dg_yang

            # Prüfe ob ein regionaler Dungeon-Boss besiegt wurde
            mob_tid = mob.get("templateId", "")
            dungeon = None
            for d in DUNGEONS.values():
                if d["bossId"] == mob_tid or mob.get("dungeonId") == d["id"]:
                    dungeon = d
                    break

            if dungeon:
                d_id = dungeon["id"]
                d_name = dungeon["name"]
                for p_cand in self.players.values():
                    if p_cand.get("online") and p_cand["map_id"] == mob["mapId"]:
                        dist = math.hypot(p_cand["pos_x"] - mob["x"], p_cand["pos_z"] - mob["z"])
                        if dist <= 75.0 or p_cand.get("player_id") == killer.get("player_id"):
                            cd = p_cand.setdefault("completedDungeons", [])
                            if d_id not in cd:
                                cd.append(d_id)
                            cand_af = p_cand.setdefault("autofarm", {}).setdefault("stats", {})
                            cand_af["dungeonRuns"] = int(cand_af.get("dungeonRuns", 0)) + 1
                            self.db.save_player_state(p_cand)

                self._emit_combat_event(
                    mob["mapId"],
                    "dungeon_cleared",
                    mob["x"],
                    mob["z"],
                    {
                        "dungeonId": d_id,
                        "mapId": mob["mapId"],
                        "unlocksMap": dungeon.get("unlocksMap", ""),
                        "bossName": dungeon["bossName"],
                        "message": dungeon.get("unlockMessage", f"{d_name} wurde siegreich bezwungen!"),
                    },
                )
                self.add_chat_message(
                    "System",
                    f"🏆 [DUNGEON SIEG] {killer['name']} hat {dungeon['bossName']} bezwungen! Das Portal zur nächsten Region ist ab sofort FREIGESCHALTET!",
                    channel="system",
                )
        elif mob["kind"] == "metin":
            stats["metinsDestroyed"] = int(stats.get("metinsDestroyed", 0)) + 1
            if af.get("mode") == "dungeon" and stats["metinsDestroyed"] % 2 == 0 and lvl_penalty > 0.0:
                stats["dungeonRuns"] = int(stats.get("dungeonRuns", 0)) + 1
        else:
            stats["monstersKilled"] = int(stats.get("monstersKilled", 0)) + 1

        leveled_up = False
        while killer["level"] < MAX_PLAYER_LEVEL and killer["exp"] >= exp_needed_for_level(killer["level"]):
            killer["exp"] -= exp_needed_for_level(killer["level"])
            killer["level"] += 1
            killer["stat_points"] += 3
            killer["skill_points"] += 1
            self.compute_player_combat_stats(killer)
            killer["hp"] = killer["max_hp"]
            killer["mp"] = killer["max_mp"]
            leveled_up = True
        if killer["level"] >= MAX_PLAYER_LEVEL:
            killer["level"] = MAX_PLAYER_LEVEL
            killer["exp"] = 0

        if leveled_up:
            if str(killer.get("player_id", "")).startswith("bot_") and int(killer.get("level", 1)) >= self.BOT_RESET_LEVEL:
                killer = self._reset_bot_on_level_cap(killer, now=now)
            else:
                self._emit_combat_event(
                    killer["map_id"],
                    "level_up",
                    killer["pos_x"],
                    killer["pos_z"],
                    {"playerId": killer["player_id"], "level": killer["level"], "name": killer["name"]},
                )
                self.add_chat_message(
                    "System",
                    f"🎉 {killer['name']} hat Level {killer['level']} erreicht!",
                    channel="system",
                )

        # 3. Quest-Fortschritt aktualisieren (Unterscheidet NPC-Quests mit Annahme/Abgabe & Direkt-/Feld-Quests)
        quests = killer.setdefault("quests", {})
        for qtpl in QUEST_TEMPLATES:
            qid = qtpl["id"]
            req_accept = bool(qtpl.get("requireAccept", False))
            req_turn_in = bool(qtpl.get("requireTurnIn", False))
            min_lvl = int(qtpl.get("minLevel", 1))
            qstate = quests.setdefault(
                qid,
                {
                    "progress": 0,
                    "accepted": not req_accept,
                    "ready": False,
                    "completed": False,
                    "claimed": False,
                },
            )
            if qstate.get("completed"):
                continue
            if not req_accept and int(killer.get("level", 1)) >= min_lvl:
                qstate["accepted"] = True
            if not qstate.get("accepted", not req_accept):
                continue
            if int(killer.get("level", 1)) < min_lvl and not req_accept:
                continue

            if mob["templateId"] in qtpl["targetKinds"]:
                prev_prog = int(qstate.get("progress", 0))
                req_cnt = int(qtpl.get("required", 1))
                if prev_prog < req_cnt:
                    qstate["progress"] = min(req_cnt, prev_prog + 1)
                    drop_item_id = qtpl.get("dropItemId")
                    if drop_item_id and drop_item_id in ITEM_TEMPLATES:
                        self.db.add_item_to_inventory(killer["player_id"], drop_item_id, quantity=1)
                        self._log_player_drop(drop_item_id, qty=1, source=f"Questprobe: {qtpl['title']}", player_id=killer["player_id"])
                    if qstate["progress"] >= req_cnt:
                        if req_turn_in:
                            qstate["ready"] = True
                            npc_name = qtpl.get("npcName", "Hauptmann Vaelen")
                            self._emit_combat_event(
                                killer["map_id"],
                                "quest_ready",
                                killer["pos_x"],
                                killer["pos_z"],
                                {
                                    "playerId": killer["player_id"],
                                    "questId": qid,
                                    "title": qtpl["title"],
                                    "npcId": qtpl.get("npcId", "npc_captain"),
                                    "npcName": npc_name,
                                    "npcPos": qtpl.get("npcPos", {"x": -3.5, "z": 176.5}),
                                },
                            )
                            self.add_chat_message(
                                "Quest-Chronist",
                                f"📜 Questziel erreicht: '{qtpl['title']}' ({req_cnt}/{req_cnt})! Kehre zu {npc_name} zurück, um deine Belohnung abzuholen!",
                                channel="event",
                                target_player_id=killer["player_id"],
                            )
                        else:
                            self._complete_and_reward_quest(killer, qtpl, qstate)

        # 4. Gegenstands-Drops strikt nach SSOT-Master-Handbuch (Teil I Abs. 3 & Teil II Abs. 1–5)
        spawned_drop_names: List[str] = []
        if not is_summoned_guard and lvl_penalty > 0.0:
            mob_lvl = int(mob.get("level", 1))
            drop_bonus_mult = 1.0 + max(0.0, float(killer.get("dropBonusPct", 0.0))) / 100.0
            active_evt = str((getattr(self, "world_event", None) or {}).get("id", ""))
            if active_evt == "monolith_eruption" and mob["kind"] == "metin":
                drop_bonus_mult *= 1.25
            elif active_evt == "boss_hunt_frenzy" and (mob["isBoss"] or mob.get("isElite", False)):
                drop_bonus_mult *= 1.25

            # Niemals craftOnly-Equipment (Lv. 80 Blaustahl / Lv. 90 Ätherium) droppen lassen!
            mob_tier_key = equip_tier_for_drop_level(mob_lvl)
            equip_pool = [iid for iid in equip_tier_item_ids(mob_tier_key) if not ITEM_TEMPLATES.get(iid, {}).get("craftOnly")]
            if not equip_pool:
                equip_pool = equip_tier_item_ids("holz")

            tpl_entries = []
            for d_entry in tpl.get("drops", []):
                rid = resolve_item_template_id(d_entry.get("itemId", ""))
                if rid in ITEM_TEMPLATES and rid not in ("item_aether_seal", "pferdemedaille") and not ITEM_TEMPLATES[rid].get("craftOnly"):
                    tpl_entries.append((rid, float(d_entry.get("chance", 0.12))))
            tpl_equip = [rid for rid, _ in tpl_entries if ITEM_TEMPLATES[rid].get("type") == "equipment"]
            tpl_mats = [(rid, ch) for rid, ch in tpl_entries if ITEM_TEMPLATES[rid].get("type") != "equipment"]

            def _pick_equip(cands: List[str]) -> str:
                if not cands:
                    return random.choice(equip_pool)
                # Faire Gleichverteilung über alle 4 Klassen (Klingenwächter: 2 Waffen, Schattenjäger: 3 Waffen, Runenmagier: 1 Waffe, Seelenweber: 1 Waffe;
                # Rüstungen: je 1 pro Klasse) + SSOT-Regel: Lv. 30+ Waffen mit DSS & FKS droppen seltener!
                weights = []
                for cid in cands:
                    ctpl = ITEM_TEMPLATES.get(cid, {})
                    cslot = ctpl.get("slot")
                    ccls = ctpl.get("classes") or []
                    w = 1.0
                    if cslot == "weapon":
                        if "ninja" in ccls:
                            w = 1.0 / 3.0
                        elif "warrior" in ccls:
                            w = 0.50
                        else:
                            w = 1.0
                        if ctpl.get("hasDssFks"):
                            w *= 0.38
                    elif cslot == "armor":
                        w = 0.55
                    weights.append(w)
                return random.choices(cands, weights=weights, k=1)[0]

            killer_cls = str(killer.get("class_id", "warrior"))
            cls_skill_ids = [s["id"] for s in CHARACTER_CLASSES.get(killer_cls, {}).get("skills", [])]
            cls_fb_pool = [f"fb_{sid}" for sid in cls_skill_ids if f"fb_{sid}" in ITEM_TEMPLATES]
            all_active_fbs = list(ACTIVE_SKILL_BOOK_IDS) or cls_fb_pool
            all_passive_fbs = list(PASSIVE_SKILL_BOOK_IDS)

            def _pick_active_fb() -> str:
                if cls_fb_pool and random.random() < 0.55:
                    return random.choice(cls_fb_pool)
                return random.choice(all_active_fbs) if all_active_fbs else "book_skill"

            def _pick_spirit_stone(high_tier: bool = False) -> str:
                g_weights = [15, 25, 30, 20, 10] if high_tier else [34, 30, 21, 11, 4]
                grade = random.choices([0, 1, 2, 3, 4], weights=g_weights, k=1)[0]
                g_pool = SPIRIT_STONE_IDS_BY_GRADE.get(grade) or ALL_SPIRIT_STONE_IDS
                return random.choice(g_pool)

            selected_item_ids: List[str] = []
            m_state = mob.get("monolithState", "schlafend")
            is_rare_metin = mob["kind"] == "metin" and m_state in ("instabil", "erwacht")
            is_high_lvl = mob_lvl >= 60

            if mob["kind"] == "metin":
                # 1. GARANTIERT 1x aktives Fertigkeitsbuch (M1–G1) + 1x Geiststein (+0 bis +4)
                selected_item_ids.append(_pick_active_fb())
                selected_item_ids.append(_pick_spirit_stone(high_tier=(is_rare_metin or mob_lvl >= 35)))

                # 2. Ausrüstung (+0..+4 schlafend, +0..+6 instabil/erwacht)
                metin_eq_cands = list(tpl_equip) * 2 + list(equip_pool)
                if metin_eq_cands and (is_rare_metin or random.random() < (0.78 if mob_lvl <= 20 else 0.62)):
                    selected_item_ids.append(_pick_equip(metin_eq_cands))
                if m_state == "erwacht" and metin_eq_cands:
                    selected_item_ids.append(_pick_equip(metin_eq_cands))

                # 3. Erweckungssteine: Instabil ab und zu, Erweckt sehr selten! (KEINE Gratis-Inventar-Duplikate mehr!)
                shard_ch = 0.85 if m_state == "erwacht" else (0.38 if m_state == "instabil" else 0.16)
                if random.random() < shard_ch * min(1.35, drop_bonus_mult):
                    selected_item_ids.append("mat_monolith_shard")
                core_ch = 0.14 if m_state == "erwacht" else (0.045 if m_state == "instabil" else 0.0)
                if core_ch > 0.0 and random.random() < core_ch * min(1.35, drop_bonus_mult):
                    selected_item_ids.append("mat_awakened_rift_core")

                # 4. Passive Skill-Bücher & Äthersiegel NUR ab Instabilen / Erweckten Monolithen
                if is_rare_metin and all_passive_fbs and random.random() < (0.52 if m_state == "erwacht" else 0.26):
                    selected_item_ids.append(random.choice(all_passive_fbs))
                if m_state == "erwacht" and random.random() < 0.08:
                    selected_item_ids.append("item_aether_seal")
                elif m_state == "instabil" and random.random() < 0.035:
                    selected_item_ids.append("item_aether_seal")

                # 5. Seltene Items (Segi, Switcher, Hinzufügen, Seelenstein): NIEMALS von Monolithen unter Level 60!
                if is_high_lvl:
                    st_mult = 1.65 if m_state == "erwacht" else (1.25 if m_state == "instabil" else 0.85)
                    if random.random() < 0.22 * st_mult:
                        selected_item_ids.append("scroll_blessing")
                    if random.random() < 0.18 * st_mult:
                        selected_item_ids.append("mat_soul_stone")
                    if random.random() < 0.16 * st_mult:
                        selected_item_ids.append(random.choice(["item_bonus_adder", "item_bonus_changer"]))

                if active_evt == "moonlight_chests" and random.random() < (0.45 if is_rare_metin else 0.22):
                    selected_item_ids.append("chest_moonlight")

                participants = set(mob.get("participants") or [])
                participants.add(killer["player_id"])
                for part_id in participants:
                    part_p = self.players.get(part_id)
                    if part_p and part_p.get("online") and part_p.get("map_id") == mob["mapId"] and mob.get("realmConflictActive"):
                        part_p["reputation"] = int(part_p.get("reputation", 0)) + 85

            elif mob.get("isRiftWorldBoss") or mob["isBoss"] or mob.get("isMonolithEliteBoss"):
                is_wb = bool(mob.get("isRiftWorldBoss"))
                is_dg = bool(mob.get("isDungeonBoss") or tpl.get("isDungeonBoss"))
                boss_eq_cands = list(tpl_equip) * 2 + list(equip_pool)
                eq_drops = (2 if random.random() < 0.55 else 3) if is_wb else (2 if (is_dg or random.random() < 0.35) else 1)
                for _ in range(eq_drops):
                    if boss_eq_cands:
                        selected_item_ids.append(_pick_equip(boss_eq_cands))
                selected_item_ids.append(_pick_active_fb())
                if all_passive_fbs and random.random() < (0.85 if is_wb else (0.55 if is_dg else 0.38)):
                    selected_item_ids.append(random.choice(all_passive_fbs))
                if random.random() < (0.65 if is_wb else 0.35):
                    selected_item_ids.append(_pick_spirit_stone(high_tier=True))
                if is_wb or random.random() < 0.25:
                    selected_item_ids.append("mat_monolith_shard")
                if (is_wb and random.random() < 0.32) or (not is_wb and random.random() < 0.06):
                    selected_item_ids.append("mat_awakened_rift_core")
                if is_wb:
                    selected_item_ids.append("chest_monolith_legend")

                # Boss-Spezialdrops: Low-Level (1–59) selten, High-Level (60–99) deutlich bessere Chancen + 1–5x Switcher/Adder
                tier_f = 2.1 if is_wb else (1.45 if is_dg else 1.0)
                segi_ch = (0.42 if is_high_lvl else 0.075) * tier_f
                soul_ch = (0.38 if is_high_lvl else 0.065) * tier_f
                sw_ch = (0.46 if is_high_lvl else 0.055) * tier_f
                if random.random() < min(0.95, segi_ch * drop_bonus_mult):
                    selected_item_ids.append("scroll_blessing")
                if random.random() < min(0.95, soul_ch * drop_bonus_mult):
                    selected_item_ids.append("mat_soul_stone")
                if random.random() < min(0.95, sw_ch * drop_bonus_mult):
                    sw_cnt = random.randint(2, 5) if (is_high_lvl and (is_wb or is_dg)) else (random.randint(1, 3) if is_high_lvl else random.randint(1, 2))
                    for _ in range(sw_cnt):
                        selected_item_ids.append(random.choice(["item_bonus_changer", "item_bonus_adder"]))

                if is_wb:
                    mono_id = mob.get("monolithBossOf")
                    if mono_id and mono_id in self.monsters:
                        self.monsters[mono_id]["activeWorldBossId"] = None
                    self._emit_combat_event(
                        mob["mapId"],
                        "world_boss_defeated",
                        mob["x"],
                        mob["z"],
                        {"bossId": mob["id"], "bossName": mob["name"], "killerName": killer["name"], "monolithId": mono_id},
                    )

            else:
                # Normale & Elite-Monster: Strikt rassen- & mobspezifischer Drop-Pool!
                # NIEMALS Segis, Switcher, Hinzufügen, Seelensteine, Passive FBs oder Pferdemedaillen!
                is_el = bool(mob.get("isElite", False))
                rate_scale = (1.35 if is_el else 1.0) * lvl_penalty * min(1.5, drop_bonus_mult)

                # 1. Gezielte mobspezifische Materialien (Wolfskralle / Bärengalle / Tigerfell / Schmuckgegenstand / Map2-Exklusiv)
                for mat_id, mat_ch in tpl_mats:
                    if random.random() < min(0.75, mat_ch * 0.65 * rate_scale):
                        selected_item_ids.append(mat_id)
                        break

                # 2. Ausrüstung (+0 bis +4): Lv. 1–20 relativ oft, Lv. 30+ (inkl. DSS/FKS-Waffen) seltener
                eq_base_ch = (0.14 if mob_lvl <= 20 else 0.075) * (1.45 if is_el else 1.0)
                mob_eq_cands = list(tpl_equip) if tpl_equip else list(equip_pool)
                if mob_eq_cands and random.random() < min(0.45, eq_base_ch * lvl_penalty * min(1.4, drop_bonus_mult)):
                    selected_item_ids.append(_pick_equip(mob_eq_cands))

                # 3. Verbrauchsgegenstände & Erweckungssteine (Instabil ab und zu, Erweckt sehr selten)
                if random.random() < 0.055 * rate_scale:
                    selected_item_ids.append(random.choice(["potion_hp_medium", "potion_mp_medium", "potion_speed", "potion_atk_speed", "cape_bravery"]))
                shard_mob_ch = 0.045 if (is_el or mob.get("isMonolithGuard")) else 0.014
                if random.random() < shard_mob_ch * lvl_penalty:
                    selected_item_ids.append("mat_monolith_shard")
                if is_el and random.random() < 0.0018 * lvl_penalty:
                    selected_item_ids.append("mat_awakened_rift_core")
                if active_evt == "moonlight_chests" and random.random() < (0.09 if is_el else 0.045) * lvl_penalty:
                    selected_item_ids.append("chest_moonlight")

            is_boss_src = bool(mob.get("isRiftWorldBoss") or mob["isBoss"] or mob.get("isMonolithEliteBoss"))
            for idx, item_id in enumerate(selected_item_ids):
                item_id = resolve_item_template_id(item_id)
                if item_id == "pferdemedaille":
                    continue
                if item_id == "book_skill":
                    item_id = _pick_active_fb()
                item_tpl = ITEM_TEMPLATES.get(item_id)
                if not item_tpl or item_tpl.get("craftOnly"):
                    continue
                plus = 0
                bonuses = []
                drop_rarity = item_tpl.get("rarity", "common")
                if item_tpl["type"] == "equipment":
                    # SSOT: Bosse +4..+6 | Instabile/Erweckte Monolithen +0..+6 | Schlafende Monolithen & Monster +0..+4
                    if is_boss_src:
                        plus = random.choices([4, 5, 6], weights=[45, 35, 20], k=1)[0]
                    elif is_rare_metin:
                        plus = random.choices([0, 1, 2, 3, 4, 5, 6], weights=[18, 20, 20, 16, 13, 8, 5], k=1)[0]
                    else:
                        plus = random.choices([0, 1, 2, 3, 4], weights=[34, 26, 19, 13, 8], k=1)[0]

                    # SSOT Teil II Abs. 1: 5 Seltenheitsstufen (Gewöhnlich, Gut, Episch, Legendär, Instabil=Max-Roll!)
                    rar_weights = [28.0, 32.0, 22.0, 13.5, 4.5] if (is_boss_src or is_rare_metin) else [58.0, 25.0, 11.0, 4.8, 1.2]
                    drop_rarity = random.choices(["common", "rare", "epic", "legendary", "instabil"], weights=rar_weights, k=1)[0]
                    is_max_roll = drop_rarity == "instabil"

                    used_b_ids = set()
                    if item_tpl.get("hasDssFks"):
                        dss_v = random.randint(48, 55) if is_max_roll else max(-25, min(52, int(round(random.gauss(5, 11)))))
                        fks_v = random.randint(18, 25) if is_max_roll else max(-18, min(24, int(round(-dss_v * 0.36 + random.gauss(1, 4)))))
                        bonuses.append({"id": "bonus_dss", "name": "Durchschn. Schaden (DSS)", "value": dss_v, "maxValue": 55, "unit": "%"})
                        bonuses.append({"id": "bonus_fks", "name": "Fertigkeitsschaden (FKS)", "value": fks_v, "maxValue": 25, "unit": "%"})
                        used_b_ids.update(("bonus_dss", "bonus_fks"))

                    target_std_cnt = (
                        5 if is_max_roll
                        else random.randint(3, 5) if drop_rarity == "legendary"
                        else random.randint(2, 4) if drop_rarity == "epic"
                        else random.randint(1, 3) if drop_rarity == "rare"
                        else (1 if random.random() < 0.32 else 0)
                    )
                    eq_slot = item_tpl.get("slot", "weapon")
                    while len(bonuses) < target_std_cnt:
                        rb = roll_slot_bonus(eq_slot, used_b_ids, max_roll=is_max_roll)
                        used_b_ids.add(rb["id"])
                        bonuses.append(rb)

                ang = (math.pi * 2.0 * idx) / max(1, len(selected_item_ids)) + random.uniform(-0.35, 0.35)
                rad = random.uniform(1.0, 2.5)
                did = f"drp_{uuid.uuid4().hex[:10]}"
                rar_tag = " [INSTABIL]" if (item_tpl["type"] == "equipment" and drop_rarity == "instabil") else ""
                d_name = f"{item_tpl['name']}{f' +{plus}' if plus > 0 else ''}{rar_tag}"
                self.drops[did] = {
                    "id": did,
                    "mapId": mob["mapId"],
                    "ownerId": killer["player_id"],
                    "ownerName": killer["name"],
                    "ownerPartyId": killer.get("partyId"),
                    "templateId": item_tpl["id"],
                    "category": get_drop_filter_category(item_tpl["id"]),
                    "name": d_name,
                    "rarity": drop_rarity,
                    "plusLevel": plus,
                    "bonuses": bonuses,
                    "quantity": 1,
                    "sourceName": mob["name"],
                    "x": round(mob["x"] + math.cos(ang) * rad, 2),
                    "z": round(mob["z"] + math.sin(ang) * rad, 2),
                    "createdAt": now,
                    "ownerProtectedUntil": now + 60.0,
                    "expiresAt": now + 120.0,
                }
                spawned_drop_names.append(f"{self._get_drop_item_icon(item_tpl['id'])} {d_name}")

            # Begrenze gleichzeitige Boden-Drops pro Map auf maximal 120 (älteste zuerst aufräumen)
            map_drops = [d for d in self.drops.values() if d["mapId"] == mob["mapId"]]
            if len(map_drops) > 120:
                map_drops.sort(key=lambda d: d["createdAt"])
                for old_d in map_drops[: len(map_drops) - 120]:
                    self.drops.pop(old_d["id"], None)

        if mob["kind"] == "metin" or mob["isBoss"]:
            self._emit_combat_event(
                mob["mapId"],
                "big_kill",
                mob["x"],
                mob["z"],
                {"targetName": mob["name"], "killerName": killer["name"], "kind": mob["kind"]},
            )
            rare_tag = f" [{mob['rarityLabel']} • {loot_mult:.1f}x Beute]" if (mob["kind"] == "metin" and mob.get("monolithRarity", "normal") != "normal") else ""
            loot_preview = f" — Beute: {', '.join(spawned_drop_names)}" if spawned_drop_names else ""
            self.add_chat_message(
                "Welt-Herold",
                f"💥 {killer['name']} hat {mob['name']} (Lv. {mob['level']}){rare_tag} bezwungen!{loot_preview}",
                channel="event",
            )
            if spawned_drop_names and not str(killer.get("player_id", "")).startswith("bot_"):
                self.add_chat_message(
                    "Beute",
                    f"💥 {mob['name']} (Lv. {mob['level']}){rare_tag} gedroppt: {', '.join(spawned_drop_names)}",
                    channel="drops",
                    target_player_id=killer["player_id"],
                )

        self.db.save_player_state(killer)

    # ========================================================================
    # 8. MONSTER- & BOSS-KI (Adaptives Spezies-Lernen, Rudel-Flankieren & Taktik)
    # ========================================================================
    def _get_monster_species_key(self, mob: dict) -> str:
        if mob.get("isBoss") or mob.get("isRiftWorldBoss") or mob.get("isMonolithEliteBoss"):
            return "apex_boss"
        tpl = str(mob.get("templateId", "")).lower()
        name = str(mob.get("name", "")).lower()
        glb = str(mob.get("glbModel", "")).lower()
        if "orc" in tpl or "ork" in name or glb.startswith("ridack_"):
            return "orc_warband"
        if "white_oath" in tpl or "eid" in name or "archer" in tpl or "schütze" in name:
            return "eid_tactical"
        if "bear" in tpl or "bär" in name or "golem" in tpl:
            return "bear_bruiser"
        if "boar" in tpl or "keiler" in name or "schwein" in name:
            return "boar_charger"
        return "wolf_pack"

    def _ensure_monster_species_ai(self) -> dict:
        if hasattr(self, "_monster_species_ai") and isinstance(self._monster_species_ai, dict):
            return self._monster_species_ai
        default_families = {
            "wolf_pack": {
                "family": "wolf_pack",
                "name": "Wolfs- & Schattenrudel",
                "icon": "🐺",
                "tacticDesc": "Rudel-Umkreisen, Rücken-Flankenbiss & Ausweichsprung",
                "encounters": 142,
                "cleaveHitsTaken": 84,
                "finisherHitsTaken": 56,
                "successfulDodges": 28,
                "successfulFlankHits": 64,
                "reinforcementsCalled": 19,
                "playerKills": 4,
                "flankSpread": 0.62,
                "evadeChance": 0.21,
                "leadFactor": 0.35,
                "evolutionStage": 3,
            },
            "boar_charger": {
                "family": "boar_charger",
                "name": "Keiler- & Sturmbrecher-Rotte",
                "icon": "🐗",
                "tacticDesc": "Aggressiver Keil-Ansturm, Kurven-Momentum & Ausweich-Haken",
                "encounters": 98,
                "cleaveHitsTaken": 52,
                "finisherHitsTaken": 39,
                "successfulDodges": 17,
                "successfulFlankHits": 35,
                "reinforcementsCalled": 6,
                "playerKills": 2,
                "flankSpread": 0.48,
                "evadeChance": 0.17,
                "leadFactor": 0.30,
                "evolutionStage": 2,
            },
            "bear_bruiser": {
                "family": "bear_bruiser",
                "name": "Bären- & Koloss-Zermalmer",
                "icon": "🐻",
                "tacticDesc": "Schwerer Flanken-Druck, Anti-Cleave-Winkel & Pranken-Konter",
                "encounters": 86,
                "cleaveHitsTaken": 49,
                "finisherHitsTaken": 34,
                "successfulDodges": 14,
                "successfulFlankHits": 31,
                "reinforcementsCalled": 4,
                "playerKills": 3,
                "flankSpread": 0.45,
                "evadeChance": 0.15,
                "leadFactor": 0.28,
                "evolutionStage": 2,
            },
            "eid_tactical": {
                "family": "eid_tactical",
                "name": "Weiße-Eid-Kriegstrupp",
                "icon": "🏹",
                "tacticDesc": "Taktischer Fächer, Hilferufe bei <32% HP & Distanz-Kiting",
                "encounters": 128,
                "cleaveHitsTaken": 71,
                "finisherHitsTaken": 48,
                "successfulDodges": 26,
                "successfulFlankHits": 53,
                "reinforcementsCalled": 27,
                "playerKills": 5,
                "flankSpread": 0.58,
                "evadeChance": 0.20,
                "leadFactor": 0.42,
                "evolutionStage": 3,
            },
            "orc_warband": {
                "family": "orc_warband",
                "name": "Orktal-Kriegshorde",
                "icon": "👹",
                "tacticDesc": "Kriegshorn-Verstärkung, Flanken-Einkesselung & Prädiktive Schockwellen",
                "encounters": 164,
                "cleaveHitsTaken": 96,
                "finisherHitsTaken": 68,
                "successfulDodges": 34,
                "successfulFlankHits": 79,
                "reinforcementsCalled": 32,
                "playerKills": 8,
                "flankSpread": 0.68,
                "evadeChance": 0.23,
                "leadFactor": 0.48,
                "evolutionStage": 3,
            },
            "apex_boss": {
                "family": "apex_boss",
                "name": "Apex- & Riss-Weltbosse",
                "icon": "👑",
                "tacticDesc": "Bewegungs-Prädiktion (Lead-Targeting), Phasen-Konter & Flanken-Brecher",
                "encounters": 74,
                "cleaveHitsTaken": 62,
                "finisherHitsTaken": 45,
                "successfulDodges": 22,
                "successfulFlankHits": 49,
                "reinforcementsCalled": 14,
                "playerKills": 11,
                "flankSpread": 0.74,
                "evadeChance": 0.25,
                "leadFactor": 0.58,
                "evolutionStage": 4,
            },
        }
        kb_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "monster_knowledge_base.json")
        self._monster_kb_path = kb_path
        loaded = {}
        try:
            if os.path.exists(kb_path):
                with open(kb_path, "r", encoding="utf-8") as f:
                    loaded = json.load(f) or {}
        except Exception:
            loaded = {}
        for fam_key, fam_def in default_families.items():
            if fam_key in loaded and isinstance(loaded[fam_key], dict):
                merged = dict(fam_def)
                merged.update(loaded[fam_key])
                self._update_species_evolution_stage(merged)
                default_families[fam_key] = merged
            else:
                self._update_species_evolution_stage(fam_def)
        self._monster_species_ai = default_families
        self._last_monster_kb_save = time.time()
        return self._monster_species_ai

    def _update_species_evolution_stage(self, sp: dict):
        xp_score = (
            int(sp.get("encounters", 0)) * 0.35
            + int(sp.get("successfulDodges", 0)) * 1.4
            + int(sp.get("successfulFlankHits", 0)) * 0.9
            + int(sp.get("reinforcementsCalled", 0)) * 1.2
            + int(sp.get("playerKills", 0)) * 3.5
        )
        pct = min(100.0, round(xp_score / 2.2, 1))
        sp["evolutionScore"] = pct
        if pct >= 82.0:
            sp["evolutionStage"] = 4
            sp["stageLabel"] = "Stufe 4 • Apex-Schwarmintelligenz"
        elif pct >= 55.0:
            sp["evolutionStage"] = 3
            sp["stageLabel"] = "Stufe 3 • Taktische Rudel-KI"
        elif pct >= 28.0:
            sp["evolutionStage"] = 2
            sp["stageLabel"] = "Stufe 2 • Adaptives Flankieren"
        else:
            sp["evolutionStage"] = 1
            sp["stageLabel"] = "Stufe 1 • Basis-Instinkt"

    def _get_species_profile(self, mob: dict) -> dict:
        kb = self._ensure_monster_species_ai()
        key = self._get_monster_species_key(mob)
        return kb.get(key, kb["wolf_pack"])

    def _save_monster_species_ai_maybe(self, now: float):
        if now - float(getattr(self, "_last_monster_kb_save", 0.0)) < 25.0:
            return
        self._last_monster_kb_save = now
        try:
            kb_path = getattr(self, "_monster_kb_path", None)
            if kb_path:
                os.makedirs(os.path.dirname(kb_path), exist_ok=True)
                with open(kb_path, "w", encoding="utf-8") as f:
                    json.dump(self._monster_species_ai, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def get_monster_ai_evolution_overview(self) -> list:
        kb = self._ensure_monster_species_ai()
        out = []
        for fam_key in ("wolf_pack", "boar_charger", "bear_bruiser", "eid_tactical", "orc_warband", "apex_boss"):
            sp = kb.get(fam_key)
            if not sp:
                continue
            self._update_species_evolution_stage(sp)
            out.append(
                {
                    "family": sp["family"],
                    "name": sp["name"],
                    "icon": sp["icon"],
                    "tacticDesc": sp.get("tacticDesc", ""),
                    "evolutionStage": int(sp.get("evolutionStage", 1)),
                    "stageLabel": sp.get("stageLabel", "Stufe 1"),
                    "evolutionScore": float(sp.get("evolutionScore", 25.0)),
                    "encounters": int(sp.get("encounters", 0)),
                    "cleaveHitsTaken": int(sp.get("cleaveHitsTaken", 0)),
                    "finisherHitsTaken": int(sp.get("finisherHitsTaken", 0)),
                    "successfulDodges": int(sp.get("successfulDodges", 0)),
                    "successfulFlankHits": int(sp.get("successfulFlankHits", 0)),
                    "reinforcementsCalled": int(sp.get("reinforcementsCalled", 0)),
                    "playerKills": int(sp.get("playerKills", 0)),
                    "flankSpreadDeg": int(round(float(sp.get("flankSpread", 0.45)) * 135.0)),
                    "evadeChancePct": round(float(sp.get("evadeChance", 0.15)) * 100.0, 1),
                    "leadFactorPct": int(round(float(sp.get("leadFactor", 0.35)) * 100.0)),
                }
            )
        return out

    def _tick_monster_ai(self, mob: dict, dt: float, now: float):
        prev_mx = float(mob.get("x", 0.0))
        prev_mz = float(mob.get("z", 0.0))
        # 0. Aktive Statusveränderungen (Blutung, Verbrennung, Gift, Betäubung, Verlangsamung) ticken
        self._tick_monster_status_effects(mob, now)
        if mob["state"] == "dead":
            mob["vx"] = 0.0
            mob["vz"] = 0.0
            return

        mob_effects = mob.get("statusEffects", {})
        # Wenn das Monster betäubt (Stun / Parry-Stagger) ist, setzt es Bewegung & Angriff aus!
        if "stun" in mob_effects and now < mob_effects["stun"].get("expiresAt", 0.0):
            mob["vx"] = 0.0
            mob["vz"] = 0.0
            return

        slow_mult = 0.65 if ("slow" in mob_effects and now < mob_effects["slow"].get("expiresAt", 0.0)) else 1.0
        sp = self._get_species_profile(mob) if mob.get("kind") != "metin" else None
        if sp is not None:
            mob["aiTier"] = int(sp.get("evolutionStage", 1))
        if mob.get("aiAction") and (now - float(mob.get("aiActionAt", 0.0))) > 1.1:
            mob["aiAction"] = ""

        # Dynamische Rissmonolith-Korruption: Monster in der Nähe eines aktiven/angegriffenen Rissmonolithen
        # fliehen NICHT mehr, sondern werden durch den Riss-Einfluss aggressiv und greifen Spieler am Monolithen an!
        if mob.get("kind") == "monster" and not mob.get("targetPlayerId"):
            active_rift = None
            min_rift_d = 44.0
            for m_other in getattr(self, "_active_rift_metins_by_map", {}).get(mob["mapId"], ()):
                m_st = m_other.get("monolithState", "schlafend")
                max_corrupt_d = 42.0 if m_st == "erwacht" else (32.0 if m_st == "instabil" else 20.0)
                rd = dist2d(mob["x"], mob["z"], m_other["x"], m_other["z"])
                if rd <= max_corrupt_d and rd < min_rift_d:
                    min_rift_d = rd
                    active_rift = m_other
            if active_rift is not None:
                best_p = None
                best_pd = 32.0
                for p_cand in self.players.values():
                    if not p_cand.get("online") or p_cand["map_id"] != mob["mapId"] or p_cand.get("isDead") or float(p_cand.get("hp", 1)) <= 0:
                        continue
                    if is_in_safe_zone(p_cand["map_id"], p_cand["pos_x"], p_cand["pos_z"]):
                        continue
                    d_to_mono = dist2d(p_cand["pos_x"], p_cand["pos_z"], active_rift["x"], active_rift["z"])
                    if d_to_mono <= 28.0 and d_to_mono < best_pd:
                        best_pd = d_to_mono
                        best_p = p_cand
                if best_p is not None:
                    mob["riftAggroMonolithId"] = active_rift["id"]
                    mob["targetPlayerId"] = best_p["player_id"]
                    mob["state"] = "chase"

        # Prüfe ob Zielspieler noch gültig & außerhalb der Safezone ist
        target = self.players.get(mob["targetPlayerId"]) if mob["targetPlayerId"] else None
        if target:
            max_leash = 58.0 if (mob.get("isSummon") or mob.get("monolithGuardOf") or mob.get("riftAggroMonolithId")) else 38.0
            if (
                not target.get("online")
                or target.get("isDead")
                or float(target.get("hp", 1)) <= 0
                or target["map_id"] != mob["mapId"]
                or is_in_safe_zone(target["map_id"], target["pos_x"], target["pos_z"])
                or dist2d(mob["spawnX"], mob["spawnZ"], mob["x"], mob["z"]) > max_leash
            ):
                mob["targetPlayerId"] = None
                mob["state"] = "patrol"
                mob["patrolX"] = mob["spawnX"]
                mob["patrolZ"] = mob["spawnZ"]
                target = None

        # Suche nächsten Spieler im Aggro-Radius (nur aggressive Mobs wie Weiße Eid oder Bosse greifen von alleine an)
        is_boss = bool(mob.get("isBoss", False))
        is_eid = ("white_oath" in mob.get("templateId", "")) or ("eid" in mob.get("name", "").lower())
        is_aggressive = is_boss or is_eid or bool(mob.get("isAggressive", False))
        aggro_radius = 16.0 if is_boss else (11.5 if is_eid else (float(mob.get("aggroRadius", 0.0)) if mob.get("isAggressive", False) else 0.0))

        if not target and is_aggressive and aggro_radius > 0:
            for p in self.players.values():
                if not p.get("online") or p["map_id"] != mob["mapId"] or p.get("isDead") or float(p.get("hp", 1)) <= 0:
                    continue
                if is_in_safe_zone(p["map_id"], p["pos_x"], p["pos_z"]):
                    continue
                if dist2d(mob["x"], mob["z"], p["pos_x"], p["pos_z"]) <= aggro_radius:
                    mob["targetPlayerId"] = p["player_id"]
                    mob["state"] = "chase"
                    target = p
                    if mob.get("packId"):
                        pack_id = mob["packId"]
                        for mate in self.monsters.values():
                            if (
                                mate.get("packId") == pack_id
                                and mate["mapId"] == mob["mapId"]
                                and mate["state"] != "dead"
                                and not mate.get("targetPlayerId")
                            ):
                                mate["targetPlayerId"] = p["player_id"]
                                mate["state"] = "chase"
                    break

        if target:
            d = dist2d(mob["x"], mob["z"], target["pos_x"], target["pos_z"])
            is_ranged = bool(
                mob.get("attackRange", 2.5) >= 3.8
                or "archer" in mob.get("templateId", "")
                or "schütze" in mob.get("name", "").lower()
            )
            mob_scale = max(0.85, float(mob.get("scale", 1.0)))
            is_mounted_target = bool(target.get("activeMount"))
            # Natürlicher Nahkampf-Mindestabstand vor dem Charakter/Reittier (verhindert, dass Monster in den Spieler hineinlaufen!)
            melee_standoff = 2.35 + max(0.0, (mob_scale - 1.0) * 0.90) + (0.35 if is_mounted_target else 0.0)
            desired_dist = min(4.2, max(3.4, mob.get("attackRange", 2.5) * 0.90)) if is_ranged else melee_standoff

            # 1. Intelligente Fortbewegung & Adaptives Rudel-Flankieren (ARC-Raiders-Stil: Spezies lernt Flanken-Auffächerung)
            learned_spread = float(sp.get("flankSpread", 0.50)) if sp else 0.45
            if "flankAngleOffset" not in mob:
                h_val = sum((i + 1) * ord(ch) for i, ch in enumerate(str(mob.get("id", "m"))))
                # Verteile Monster eines Packs fächerförmig bis in die seitliche Rückenflanke des Spielers
                slot_idx = (h_val % 7) - 3
                if slot_idx == 0:
                    slot_idx = 1 if (h_val % 2 == 0) else -1
                mob["flankAngleOffset"] = slot_idx * (0.34 + learned_spread * 0.28)

            flank_off = float(mob.get("flankAngleOffset", 0.0))
            p_facing = float(target.get("rot_y", 0.0))
            # Gelernte Wunsch-Position liegt seitlich/hinter der Blickrichtung des Spielers (aus dem Frontal-Cleave heraus!)
            desired_orbit_ang = math.atan2(math.sin(p_facing), math.cos(p_facing)) + flank_off

            if d > desired_dist:
                raw_dx = target["pos_x"] - mob["x"]
                raw_dz = target["pos_z"] - mob["z"]
                # Im Annäherungsbereich (< 9.5m) steuert das Monster geschmeidig auf seine Flanken-Position auf dem Kampfring zu
                if d < desired_dist + 7.2 and abs(flank_off) > 0.02:
                    ang_from_target = math.atan2(mob["z"] - target["pos_z"], mob["x"] - target["pos_x"])
                    flank_blend = max(0.0, min(1.0, 1.0 - (d - desired_dist) / 7.2)) * (0.55 + learned_spread * 0.30)
                    slot_ang = ang_from_target + flank_off * flank_blend
                    goal_x = target["pos_x"] + math.cos(slot_ang) * (desired_dist * 0.94)
                    goal_z = target["pos_z"] + math.sin(slot_ang) * (desired_dist * 0.94)
                    gdx = goal_x - mob["x"]
                    gdz = goal_z - mob["z"]
                    gd = math.hypot(gdx, gdz)
                    if gd > 0.05:
                        dir_x = gdx / gd
                        dir_z = gdz / gd
                    else:
                        dir_x = raw_dx / max(0.001, d)
                        dir_z = raw_dz / max(0.001, d)
                else:
                    dir_x = raw_dx / max(0.001, d)
                    dir_z = raw_dz / max(0.001, d)

                # Monolith-Hindernislenkung: Wenn ein Rissmonolith im Weg steht, diesen elegant umrunden
                active_metin = None
                guard_of = mob.get("monolithGuardOf")
                if guard_of and guard_of in self.monsters:
                    active_metin = self.monsters[guard_of]
                else:
                    for m_cand in getattr(self, "_metins_by_map", {}).get(mob["mapId"], ()):
                        if dist2d(mob["x"], mob["z"], m_cand["x"], m_cand["z"]) <= 6.5:
                            active_metin = m_cand
                            break

                move_dir_x = dir_x
                move_dir_z = dir_z
                if active_metin:
                    vmx = active_metin["x"] - mob["x"]
                    vmz = active_metin["z"] - mob["z"]
                    proj = vmx * dir_x + vmz * dir_z
                    if 0.2 < proj < d:
                        perp_d = abs(vmx * (-dir_z) + vmz * dir_x)
                        metin_avoid_r = 2.4
                        if perp_d < metin_avoid_r:
                            cross = vmx * dir_z - vmz * dir_x
                            steer_sign = 1.0 if cross >= 0 else -1.0
                            steer_x = -dir_z * steer_sign
                            steer_z = dir_x * steer_sign
                            weight = (metin_avoid_r - perp_d) / metin_avoid_r
                            move_dir_x = dir_x * (1.0 - weight * 0.75) + steer_x * (weight * 0.75)
                            move_dir_z = dir_z * (1.0 - weight * 0.75) + steer_z * (weight * 0.75)
                            m_len = math.hypot(move_dir_x, move_dir_z)
                            if m_len > 0.001:
                                move_dir_x /= m_len
                                move_dir_z /= m_len

                step = min(d - desired_dist, mob["speed"] * slow_mult * dt)
                nx = mob["x"] + move_dir_x * step
                raw_nz = mob["z"] + move_dir_z * step
                sp_z = mob.get("spawnZ", 0.0)
                if mob["mapId"] == "morgenwacht":
                    nz = min(-42.0, raw_nz) if sp_z < 0.0 else max(42.0, min(920.0, raw_nz))
                elif mob["mapId"] == "orktal":
                    nx = max(-1720.0, min(1720.0, nx))
                    nz = max(-1720.0, min(1720.0, raw_nz))
                elif sp_z > 105.0:
                    nz = max(116.0, raw_nz)
                elif sp_z > -75.0:
                    nz = max(-64.0, min(64.0, raw_nz))
                else:
                    nz = min(-114.0, raw_nz)
                if not is_in_safe_zone(mob["mapId"], nx, nz):
                    mob["x"] = nx
                    mob["z"] = nz
                    mob["rotY"] = math.atan2(move_dir_x, move_dir_z)
            elif d < desired_dist - 0.15:
                # Falls das Monster zu nah im Spieler steht (z.B. Spieler läuft auf Monster zu), weicht es auf Kampfdistanz zurück
                if d > 0.01:
                    push_dir_x = (mob["x"] - target["pos_x"]) / d
                    push_dir_z = (mob["z"] - target["pos_z"]) / d
                else:
                    ang_fallback = float(mob.get("rotY", 0.0))
                    push_dir_x = -math.sin(ang_fallback)
                    push_dir_z = -math.cos(ang_fallback)
                push_step = min((desired_dist - 0.04) - d, max(4.2, mob["speed"]) * dt)
                nx = mob["x"] + push_dir_x * push_step
                nz = mob["z"] + push_dir_z * push_step
                if not is_in_safe_zone(mob["mapId"], nx, nz):
                    mob["x"] = nx
                    mob["z"] = nz
                mob["rotY"] = math.atan2(target["pos_x"] - mob["x"], target["pos_z"] - mob["z"])
                d = dist2d(mob["x"], mob["z"], target["pos_x"], target["pos_z"])
            elif abs(flank_off) > 0.05 and d <= desired_dist + 0.45:
                # 40Hz flüssiges Raubtier-Umkreisen (Predator Prowl): Monster schleicht kontinuierlich in die Flanke / den Rücken des Spielers!
                cur_ang = math.atan2(mob["x"] - target["pos_x"], mob["z"] - target["pos_z"])
                ang_err = (desired_orbit_ang - cur_ang + math.pi) % (math.pi * 2.0) - math.pi
                if abs(ang_err) > 0.18 and (now - float(mob.get("lastAttackTime", 0.0))) > 0.45:
                    orbit_rate = (0.38 + learned_spread * 0.34) * slow_mult
                    ang_step = max(-orbit_rate * dt, min(orbit_rate * dt, ang_err * 0.85))
                    new_ang = cur_ang + ang_step
                    orbit_r = max(desired_dist * 0.96, min(desired_dist + 0.25, d))
                    nx = target["pos_x"] + math.sin(new_ang) * orbit_r
                    nz = target["pos_z"] + math.cos(new_ang) * orbit_r
                    if not is_in_safe_zone(mob["mapId"], nx, nz):
                        mob["x"] = nx
                        mob["z"] = nz

            # 2. Angriff ausführen (6-stufige Angriffs-Combo: attack1 bis attack6!): Wenn Distanz innerhalb der Angriffsreichweite liegt
            eff_atk_range = max(float(mob.get("attackRange", 2.5)), desired_dist + 0.65)
            if d <= eff_atk_range:
                mob["rotY"] = math.atan2(target["pos_x"] - mob["x"], target["pos_z"] - mob["z"])
                atk_int = mob["attackInterval"] * (0.82 if mob.get("bossPhase", 1) >= 2 else 1.0)
                if now - mob["lastAttackTime"] >= atk_int:
                    prev_atk_t = float(mob.get("lastAttackTime", 0.0))
                    if now - prev_atk_t > 5.5:
                        combo_step = 0
                    else:
                        combo_step = (int(mob.get("attackComboStep", -1)) + 1) % 6
                    mob["attackComboStep"] = combo_step
                    mob["lastAttackTime"] = now
                    mob["lastAttackType"] = f"attack{combo_step + 1}"
                    mob["attackSeq"] = int(mob.get("attackSeq", 0)) + 1
                    p_def = target.get("computed", {}).get("def", 25)
                    phase_mult = 1.0 + (mob.get("bossPhase", 1) - 1) * 0.28
                    # 6. Schlag (combo_step == 5) ist der schwere Finisher-Angriff (+18% Wucht)
                    combo_dmg_mult = 1.18 if combo_step == 5 else (1.08 if combo_step == 4 else 1.0)
                    # Taktischer Flanken-/Rücken-Trefferbonus (+12% Schaden, wenn Monster erfolgreich flankiert hat)
                    ang_from_p = math.atan2(mob["x"] - target["pos_x"], mob["z"] - target["pos_z"])
                    flank_diff = abs((ang_from_p - p_facing + math.pi) % (math.pi * 2.0) - math.pi)
                    flank_mult = 1.0
                    if flank_diff > 1.25 and sp is not None:
                        flank_mult = 1.12
                        sp["successfulFlankHits"] = int(sp.get("successfulFlankHits", 0)) + 1
                    dmg = max(8, int(round(mob["atk"] * phase_mult * combo_dmg_mult * flank_mult - p_def * 0.50)))
                    self._apply_damage_to_player_authoritative(target, mob, dmg, is_boss_skill=False)

            # Boss- & Elite-Spezialmechanik (Kap. 8): Phasenwechsel & angekündigte Gegner-Telegraphen mit prädiktivem Vorhalten (Lead-Targeting)!
            lead_factor = float(sp.get("leadFactor", 0.45)) if sp else 0.40
            p_vx = float(target.get("vx", 0.0))
            p_vz = float(target.get("vz", 0.0))
            lead_dx = max(-3.2, min(3.2, p_vx * lead_factor * 1.35))
            lead_dz = max(-3.2, min(3.2, p_vz * lead_factor * 1.35))
            pred_tx = round(target["pos_x"] + lead_dx, 2)
            pred_tz = round(target["pos_z"] + lead_dz, 2)

            if mob["isBoss"]:
                hp_ratio = mob["hp"] / mob["maxHp"]
                if hp_ratio <= 0.65 and mob["bossPhase"] < 2:
                    mob["bossPhase"] = 2
                    mob["nextAoETime"] = now  # Sofortiger Boss-Skill beim Phasenwechsel!
                    self.add_chat_message(
                        "Boss-Warnung",
                        f"🔥 {mob['name']} verfällt in Phase 2 (Blutrausch) und entfesselt seinen Zornes-Skill!",
                        channel="event",
                    )
                elif hp_ratio <= 0.32 and mob["bossPhase"] < 3:
                    mob["bossPhase"] = 3
                    mob["nextAoETime"] = now  # Sofortiger Boss-Skill beim Phasenwechsel!
                    self.add_chat_message(
                        "Boss-Warnung",
                        f"💀 {mob['name']} entfesselt Phase 3 (Zorn der Legenden)!",
                        channel="event",
                    )

                if now >= mob["nextAoETime"]:
                    phase = int(mob.get("bossPhase", 1))
                    is_rift_wb = bool(mob.get("isRiftWorldBoss", False))
                    mob["nextAoETime"] = now + (max(3.8, 6.8 - phase * 0.85) if is_rift_wb else max(4.2, 7.5 - phase * 0.9))
                    mob["lastAttackTime"] = now
                    mob["lastAttackType"] = "skill"
                    mob["attackSeq"] = int(mob.get("attackSeq", 0)) + 1
                    is_orc_boss = mob.get("glbModel") == "ridack_bossorc4" or "ork" in str(mob.get("templateId", "")).lower()
                    if is_rift_wb:
                        skill_names = {
                            1: "Ätherriss-Schmetterschlag",
                            2: "Karmesin-Supernova",
                            3: "Abgrund-Kataklysmus",
                        }
                    elif is_orc_boss:
                        skill_names = {
                            1: "Smaragd-Spaltsturm",
                            2: "Wirbelsturm des Oberorks",
                            3: "Kataklysmus der Schwarzen Horde",
                        }
                    else:
                        skill_names = {
                            1: "Blutsturm-Zerschmetterer",
                            2: "Bestienzorn-Eruption",
                            3: "Kataklysmus der Legenden",
                        }
                    skill_name = skill_names.get(phase, "Zornes-Eruption")
                    tel = {
                        "id": f"tel_{uuid.uuid4().hex[:8]}",
                        "mapId": mob["mapId"],
                        "bossId": mob["id"],
                        "bossName": mob["name"],
                        "bossX": round(mob["x"], 2),
                        "bossZ": round(mob["z"], 2),
                        "phase": phase,
                        "skillName": skill_name,
                        "isOrcSkill": is_orc_boss,
                        "isWorldBossSkill": is_rift_wb,
                        "x": pred_tx,
                        "z": pred_tz,
                        "radius": (6.8 + phase * 0.65) if is_rift_wb else (5.8 + (phase - 1) * 0.4),
                        "damage": int(mob["atk"] * (5.2 + phase * 1.15)) if is_rift_wb else int(mob["atk"] * (4.6 + phase * 0.95)),
                        "createdAt": now,
                        "explodeAt": now + (1.75 if is_rift_wb else 1.85),
                    }
                    self.telegraphs.append(tel)
                    self._emit_combat_event(mob["mapId"], "boss_telegraph", tel["x"], tel["z"], tel)
                    if is_rift_wb and phase >= 2:
                        # Mächtige Sekundär-Eruptionen bei Worldbossen ab Phase 2!
                        for idx_ring in range(2):
                            ang = random.uniform(0.0, math.pi * 2.0) + idx_ring * math.pi
                            dist_r = 5.5 + idx_ring * 2.0
                            sub_tel = {
                                "id": f"tel_{uuid.uuid4().hex[:8]}",
                                "mapId": mob["mapId"],
                                "bossId": mob["id"],
                                "bossName": mob["name"],
                                "bossX": round(mob["x"], 2),
                                "bossZ": round(mob["z"], 2),
                                "phase": phase,
                                "skillName": f"{skill_name} (Nachbeben)",
                                "isOrcSkill": False,
                                "isWorldBossSkill": True,
                                "x": round(pred_tx + math.cos(ang) * dist_r, 2),
                                "z": round(pred_tz + math.sin(ang) * dist_r, 2),
                                "radius": 4.2 + phase * 0.35,
                                "damage": int(mob["atk"] * (3.8 + phase * 0.85)),
                                "createdAt": now,
                                "explodeAt": now + 2.15,
                            }
                            self.telegraphs.append(sub_tel)
                            self._emit_combat_event(mob["mapId"], "boss_telegraph", sub_tel["x"], sub_tel["z"], sub_tel)
            elif mob.get("isElite") and d <= 7.5 and now >= mob.get("nextAoETime", 0.0):
                # Elite-Monster kündigen schwere Bodenschmetterer über Telegraphen mit Bewegungs-Vorhalten an!
                mob["nextAoETime"] = now + random.uniform(8.5, 11.5)
                mob["lastAttackTime"] = now
                mob["lastAttackType"] = "skill"
                mob["attackSeq"] = int(mob.get("attackSeq", 0)) + 1
                is_orc_elite = str(mob.get("glbModel", "")).startswith("ridack_")
                tel = {
                    "id": f"tel_{uuid.uuid4().hex[:8]}",
                    "mapId": mob["mapId"],
                    "bossId": mob["id"],
                    "bossName": mob["name"],
                    "bossX": round(mob["x"], 2),
                    "bossZ": round(mob["z"], 2),
                    "phase": 1,
                    "skillName": "Smaragd-Schockwelle" if is_orc_elite else "Schmetterhieb",
                    "isOrcSkill": is_orc_elite,
                    "x": pred_tx,
                    "z": pred_tz,
                    "radius": 3.8,
                    "damage": int(mob["atk"] * 2.8),
                    "createdAt": now,
                    "explodeAt": now + 1.55,
                }
                self.telegraphs.append(tel)
                self._emit_combat_event(mob["mapId"], "boss_telegraph", tel["x"], tel["z"], tel)
        else:
            # Intelligente Mehrpunkt-Patrouille um den Spawnpunkt (geschwungene Routen, sanftes Abbremsen/Anlaufen & Ausweichlenkung)
            if mob["roamRadius"] > 0:
                sp_z = mob.get("spawnZ", 0.0)
                d = dist2d(mob["x"], mob["z"], mob["patrolX"], mob["patrolZ"])
                if d <= 0.35:
                    if mob.get("state") == "patrol":
                        mob["state"] = "idle"
                        p_leg = int(mob.get("patrolLegCount", 0)) + 1
                        mob["patrolLegCount"] = p_leg
                        # Nach 2–3 kurzen Zwischenetappen (Umschauen) folgt eine ruhigere Verschnaufpause
                        mob["nextPatrolTime"] = now + (random.uniform(3.6, 6.2) if (p_leg % 3 == 0) else random.uniform(1.4, 2.7))
                    elif mob.get("state") != "idle":
                        mob["state"] = "idle"

                    if now >= mob["nextPatrolTime"]:
                        mob["nextPatrolTime"] = now + random.uniform(4.2, 7.8)
                        guard_of = mob.get("monolithGuardOf")
                        guard_mono = self.monsters.get(guard_of) if guard_of else None
                        if guard_mono and guard_mono.get("state") != "dead":
                            cur_ang = math.atan2(mob["z"] - guard_mono["z"], mob["x"] - guard_mono["x"])
                            patrol_dir = mob.get("patrolOrbitSign")
                            if not patrol_dir:
                                patrol_dir = random.choice([-1.0, 1.0])
                                mob["patrolOrbitSign"] = patrol_dir
                            delta_ang = patrol_dir * random.uniform(0.75, 1.35)
                            ang = cur_ang + delta_ang
                            r = random.uniform(3.8, 6.8)
                            px = guard_mono["x"] + math.cos(ang) * r
                            raw_pz = guard_mono["z"] + math.sin(ang) * r
                        else:
                            # Weiterführender Bogen um das Revier statt rein zufälligem Zickzack
                            prev_ang = float(mob.get("patrolOrbitAngle", random.uniform(0, math.pi * 2)))
                            orbit_sign = float(mob.get("patrolOrbitSign", 1.0 if (hash(mob.get("id", "")) % 2 == 0) else -1.0))
                            mob["patrolOrbitSign"] = orbit_sign
                            ang = prev_ang + orbit_sign * random.uniform(0.85, 1.75)
                            mob["patrolOrbitAngle"] = ang
                            r = random.uniform(max(1.8, mob["roamRadius"] * 0.42), max(2.4, mob["roamRadius"]))
                            px = mob["spawnX"] + math.cos(ang) * r
                            raw_pz = mob["spawnZ"] + math.sin(ang) * r
                            for m_cand in getattr(self, "_metins_by_map", {}).get(mob["mapId"], ()):
                                if dist2d(px, raw_pz, m_cand["x"], m_cand["z"]) < 3.4:
                                    push_ang = math.atan2(raw_pz - m_cand["z"], px - m_cand["x"])
                                    px = m_cand["x"] + math.cos(push_ang) * 3.8
                                    raw_pz = m_cand["z"] + math.sin(push_ang) * 3.8

                        if mob["mapId"] == "morgenwacht":
                            pz = min(-42.0, raw_pz) if sp_z < 0.0 else max(42.0, min(920.0, raw_pz))
                        elif mob["mapId"] == "orktal":
                            px = max(-1720.0, min(1720.0, px))
                            pz = max(-1720.0, min(1720.0, raw_pz))
                        elif sp_z > 105.0:
                            pz = max(116.0, raw_pz)
                        elif sp_z > -75.0:
                            pz = max(-64.0, min(64.0, raw_pz))
                        else:
                            pz = min(-114.0, raw_pz)
                        if not is_in_safe_zone(mob["mapId"], px, pz):
                            mob["patrolX"] = px
                            mob["patrolZ"] = pz
                            d = dist2d(mob["x"], mob["z"], px, pz)

                if d > 0.35:
                    mob["state"] = "patrol"
                    dx = mob["patrolX"] - mob["x"]
                    dz = mob["patrolZ"] - mob["z"]
                    dir_x = dx / d
                    dir_z = dz / d
                    move_dir_x = dir_x
                    move_dir_z = dir_z

                    # Rissmonolith-Hindernislenkung auch während der Patrouille
                    for m_cand in getattr(self, "_metins_by_map", {}).get(mob["mapId"], ()):
                        if dist2d(mob["x"], mob["z"], m_cand["x"], m_cand["z"]) <= 6.5:
                            vmx = m_cand["x"] - mob["x"]
                            vmz = m_cand["z"] - mob["z"]
                            proj = vmx * dir_x + vmz * dir_z
                            if -0.2 < proj < d:
                                perp_d = abs(vmx * (-dir_z) + vmz * dir_x)
                                metin_avoid_r = 2.8
                                if perp_d < metin_avoid_r:
                                    cross = vmx * dir_z - vmz * dir_x
                                    steer_sign = 1.0 if cross >= 0 else -1.0
                                    steer_x = -dir_z * steer_sign
                                    steer_z = dir_x * steer_sign
                                    weight = (metin_avoid_r - perp_d) / metin_avoid_r
                                    move_dir_x = dir_x * (1.0 - weight * 0.8) + steer_x * (weight * 0.8)
                                    move_dir_z = dir_z * (1.0 - weight * 0.8) + steer_z * (weight * 0.8)
                                    m_len = math.hypot(move_dir_x, move_dir_z)
                                    if m_len > 0.001:
                                        move_dir_x /= m_len
                                        move_dir_z /= m_len
                            break

                    # Sanfte Geschwindigkeits-Kurve (Ease-Out vor dem Wegpunkt für organisches Abbremsen)
                    ease_mult = min(1.0, max(0.52, d / 1.45))
                    step = min(d, mob["speed"] * 0.48 * ease_mult * dt)
                    nx = mob["x"] + move_dir_x * step
                    raw_nz = mob["z"] + move_dir_z * step
                    mob_scale_p = max(0.85, float(mob.get("scale", 1.0)))
                    min_p_clearance = 2.45 + max(0.0, (mob_scale_p - 1.0) * 0.85)
                    blocked_by_player = False
                    for p_near in self.players.values():
                        if not p_near.get("online") or p_near.get("map_id") != mob["mapId"] or p_near.get("isDead"):
                            continue
                        dp_near = dist2d(nx, raw_nz, p_near["pos_x"], p_near["pos_z"])
                        if dp_near < min_p_clearance:
                            # Tangentiales Ausweichen um den Spieler herum statt starrem Stehenbleiben
                            if dp_near > 0.05:
                                away_x = (mob["x"] - p_near["pos_x"]) / dp_near
                                away_z = (mob["z"] - p_near["pos_z"]) / dp_near
                                tang_x = -away_z
                                tang_z = away_x
                                if tang_x * move_dir_x + tang_z * move_dir_z < 0:
                                    tang_x = -tang_x
                                    tang_z = -tang_z
                                sidestep_x = mob["x"] + (tang_x * 0.75 + away_x * 0.45) * step
                                sidestep_z = mob["z"] + (tang_z * 0.75 + away_z * 0.45) * step
                                if dist2d(sidestep_x, sidestep_z, p_near["pos_x"], p_near["pos_z"]) >= dp_near:
                                    nx = sidestep_x
                                    raw_nz = sidestep_z
                                    move_dir_x = tang_x
                                    move_dir_z = tang_z
                                else:
                                    blocked_by_player = True
                            else:
                                blocked_by_player = True
                            if blocked_by_player:
                                mob["state"] = "idle"
                                mob["nextPatrolTime"] = now + random.uniform(1.8, 3.2)
                            break
                    if not blocked_by_player:
                        if mob["mapId"] == "morgenwacht":
                            nz = min(-42.0, raw_nz) if sp_z < 0.0 else max(42.0, min(920.0, raw_nz))
                        elif mob["mapId"] == "orktal":
                            nx = max(-1720.0, min(1720.0, nx))
                            nz = max(-1720.0, min(1720.0, raw_nz))
                        elif sp_z > 105.0:
                            nz = max(116.0, raw_nz)
                        elif sp_z > -75.0:
                            nz = max(-64.0, min(64.0, raw_nz))
                        else:
                            nz = min(-114.0, raw_nz)
                        if not is_in_safe_zone(mob["mapId"], nx, nz):
                            mob["x"] = nx
                            mob["z"] = nz
                            target_rot = math.atan2(move_dir_x, move_dir_z)
                            cur_rot = float(mob.get("rotY", target_rot))
                            rot_diff = math.atan2(math.sin(target_rot - cur_rot), math.cos(target_rot - cur_rot))
                            mob["rotY"] = cur_rot + rot_diff * min(1.0, dt * 8.5)
            else:
                mob["state"] = "idle"

        if dt > 0.0005:
            mob["vx"] = (float(mob["x"]) - prev_mx) / dt
            mob["vz"] = (float(mob["z"]) - prev_mz) / dt
        else:
            mob["vx"] = 0.0
            mob["vz"] = 0.0

    def _resolve_boss_telegraph(self, tel: dict):
        self._emit_combat_event(
            tel["mapId"],
            "boss_aoe_explode",
            tel["x"],
            tel["z"],
            {
                "radius": tel["radius"],
                "x": tel["x"],
                "z": tel["z"],
                "bossId": tel.get("bossId"),
                "bossName": tel.get("bossName", "Gebietsboss"),
                "skillName": tel.get("skillName", "Zornes-Eruption"),
                "phase": tel.get("phase", 1),
            },
        )
        boss_mob = self.monsters.get(tel.get("bossId")) if tel.get("bossId") else None
        for p in self.players.values():
            if not p.get("online") or p["map_id"] != tel["mapId"]:
                continue
            if dist2d(p["pos_x"], p["pos_z"], tel["x"], tel["z"]) <= tel["radius"]:
                p_def = p.get("computed", {}).get("def", 30)
                phase = int(tel.get("phase", 1))
                # Deutlich höherer Boss-Skill-Schaden: Starke Skalierung über Boss-ATK + %-Anteil der maximalen Spieler-TP!
                base_skill_dmg = int(tel["damage"] - p_def * 0.25)
                hp_pct_dmg = int(p.get("max_hp", 1000) * (0.20 + phase * 0.05))
                dmg = max(180, base_skill_dmg + hp_pct_dmg)
                self._apply_damage_to_player_authoritative(
                    p,
                    boss_mob,
                    dmg,
                    is_boss_skill=True,
                    skill_name=tel.get("skillName", "Zornes-Eruption"),
                )

    # ========================================================================
    # 9. LOOT, TRÄNKE, SCHMIED, RUNENWEBERIN, CHARAKTER-ENTWICKLUNG
    # ========================================================================
    def drop_inventory_item(self, player_id: str, item_uid: str) -> Tuple[bool, str]:
        """Lässt einen Gegenstand aus dem Inventar auf den Boden fallen:
        - 60 Sekunden lang nur für den Besitzer und seine Gruppenmitglieder aufhebbar.
        - Danach weitere 60 Sekunden lang für alle anderen Spieler zugänglich, bevor der Drop verschwindet (120s gesamt)."""
        p = self.players.get(player_id)
        if not p:
            return False, "Spieler nicht aktiv."
        deleted = self.db.delete_item(player_id, item_uid, allow_equipped=False)
        if not deleted:
            return False, "Gegenstand kann nicht auf den Boden geworfen werden (evtl. ausgerüstet)."
        now = time.time()
        tpl_id = deleted.get("templateId", "")
        item_tpl = ITEM_TEMPLATES.get(tpl_id, deleted)
        plus = int(deleted.get("plusLevel", 0) or 0)
        qty = max(1, int(deleted.get("quantity", 1) or 1))
        bonuses = deleted.get("bonuses", []) or []
        ang = random.uniform(0.0, math.pi * 2.0)
        rad = random.uniform(0.8, 1.8)
        did = f"drp_{uuid.uuid4().hex[:10]}"
        base_name = item_tpl.get("name", deleted.get("name", "Gegenstand"))
        d_name = f"{base_name}{f' +{plus}' if plus > 0 else ''}{f' ({qty}x)' if qty > 1 else ''}"
        self.drops[did] = {
            "id": did,
            "mapId": p["map_id"],
            "ownerId": p["player_id"],
            "ownerName": p["name"],
            "ownerPartyId": p.get("partyId"),
            "templateId": tpl_id,
            "category": get_drop_filter_category(tpl_id),
            "name": d_name,
            "rarity": item_tpl.get("rarity", deleted.get("rarity", "common")),
            "plusLevel": plus,
            "bonuses": bonuses,
            "quantity": qty,
            "sourceName": f"Fallengelassen von {p['name']}",
            "x": round(float(p["pos_x"]) + math.cos(ang) * rad, 2),
            "z": round(float(p["pos_z"]) + math.sin(ang) * rad, 2),
            "createdAt": now,
            "ownerProtectedUntil": now + 60.0,
            "expiresAt": now + 120.0,
            "droppedByPlayer": True,
            "selfAutoPickupLockUntil": now + 15.0,
        }
        self.refresh_player_from_db(player_id)
        return True, f"📦 {d_name} auf den Boden gelegt (60s für dich/Gruppe geschützt, danach 60s frei für alle)."

    def pickup_drop(self, player_id: str, drop_id: str, auto_sell: bool = False) -> Tuple[bool, str]:
        p = self.players.get(player_id)
        dr = self.drops.get(drop_id)
        if not p or not dr:
            return False, "Beute nicht mehr vorhanden."
        if dr["mapId"] != p["map_id"]:
            return False, "Falsche Map."
        if dist2d(p["pos_x"], p["pos_z"], dr["x"], dr["z"]) > 6.5:
            return False, "Zu weit entfernt! Laufe näher zum Gegenstand."

        can_pick, rem_sec = self.can_player_pickup_drop(player_id, dr)
        if not can_pick:
            owner_name = dr.get("ownerName", "einem anderen Spieler")
            return (
                False,
                f"🔒 Dieser Drop gehört noch {owner_name} (oder seiner Gruppe) – erst in {int(math.ceil(rem_sec))}s für alle frei!",
            )

        af = p.setdefault("autofarm", {})
        stats = self.ensure_autofarm_stats(af)

        qty = max(1, int(dr.get("quantity", 1) or 1))
        src_label = dr.get("sourceName", "")
        is_bot_pickup = str(player_id).startswith("bot_")
        if is_bot_pickup and auto_sell:
            tpl_chk = ITEM_TEMPLATES.get(dr["templateId"], {})
            if tpl_chk.get("type") == "equipment" and tpl_chk.get("slot"):
                slot_chk = tpl_chk["slot"]
                cur_eq_chk = (p.get("equipment") or {}).get(slot_chk)
                cand_sc = self._score_bot_equipment_item(p, dr["templateId"], int(dr.get("plusLevel", 0)), dr.get("bonuses") or [])
                cur_sc = self._score_bot_equipment_item(p, cur_eq_chk) if cur_eq_chk else -1.0
                if cand_sc > cur_sc + 0.5 and int(tpl_chk.get("reqLevel", 1)) <= int(p.get("level", 1)) + 5:
                    auto_sell = False

        if auto_sell:
            tpl = ITEM_TEMPLATES.get(dr["templateId"], {})
            base_sell = int(tpl.get("sellPrice", 80))
            sell_yang = max(18, int(base_sell * (1.0 + 0.25 * int(dr.get("plusLevel", 0)))) * qty)
            self.drops.pop(drop_id, None)
            p["yang"] = int(p.get("yang", 0)) + sell_yang
            stats["dropsLooted"] = int(stats.get("dropsLooted", 0)) + 1
            stats["yangEarned"] = int(stats.get("yangEarned", 0)) + sell_yang
            self._log_player_drop(
                dr["templateId"],
                plus=int(dr.get("plusLevel", 0)),
                bonuses=dr.get("bonuses", []),
                qty=qty,
                yang_gain=sell_yang,
                auto_sold=True,
                source=src_label,
                player_id=player_id,
            )
            self.db.save_player_state(p)
            return True, f"🪙 Auto-Filter verkauft: {dr['name']} (+{sell_yang:,} Gold)"

        ok, msg = self.db.add_item_to_inventory(
            player_id,
            dr["templateId"],
            quantity=qty,
            plus_level=dr["plusLevel"],
            bonuses=dr["bonuses"],
            rarity=str(dr.get("rarity") or ""),
        )
        if not ok:
            # Wenn diese Inventar-Kategorie (120 Slots) komplett voll ist, Gegenstand automatisch in Gold umwandeln,
            # damit niemals Drops auf dem Boden liegen bleiben oder andere Kategorien blockiert werden.
            tpl = ITEM_TEMPLATES.get(dr["templateId"], {})
            base_sell = int(tpl.get("sellPrice", 80))
            sell_yang = max(15, int(base_sell * (1.0 + 0.25 * int(dr.get("plusLevel", 0)))) * qty)
            self.drops.pop(drop_id, None)
            p["yang"] = int(p.get("yang", 0)) + sell_yang
            stats["dropsLooted"] = int(stats.get("dropsLooted", 0)) + 1
            stats["yangEarned"] = int(stats.get("yangEarned", 0)) + sell_yang
            self._log_player_drop(
                dr["templateId"],
                plus=int(dr.get("plusLevel", 0)),
                bonuses=dr.get("bonuses", []),
                qty=qty,
                yang_gain=sell_yang,
                auto_sold=True,
                source=src_label,
                player_id=player_id,
            )
            self.db.save_player_state(p)
            return True, f"🪙 Kat. voll – Auto-Verkauf: {dr['name']} (+{sell_yang:,} Gold)"

        self.drops.pop(drop_id, None)
        stats["dropsLooted"] = int(stats.get("dropsLooted", 0)) + 1
        self._log_player_drop(
            dr["templateId"],
            plus=int(dr.get("plusLevel", 0)),
            bonuses=dr.get("bonuses", []),
            qty=qty,
            source=src_label,
            player_id=player_id,
        )
        self.refresh_player_from_db(player_id)
        if is_bot_pickup and ITEM_TEMPLATES.get(dr["templateId"], {}).get("type") == "equipment":
            self._auto_equip_best_inventory_items_for_bot(self.players.get(player_id), now=time.time())
        return True, f"Aufgehoben: {dr['name']}"

    def _count_player_potions(self, p: dict) -> Tuple[int, int]:
        """Zählt die aktuell im Inventar vorhandenen Heiltränke (K + G) und Manatränke (G)."""
        inv = p.get("inventory") or []
        hp_cnt = 0
        mp_cnt = 0
        for it in inv:
            if not isinstance(it, dict):
                continue
            tid = it.get("templateId")
            qty = max(1, int(it.get("quantity", 1) or 1))
            if tid in ("potion_hp_small", "potion_hp_medium"):
                hp_cnt += qty
            elif tid == "potion_mp_medium":
                mp_cnt += qty
        return hp_cnt, mp_cnt

    def _auto_restock_potions(
        self,
        p: dict,
        now: Optional[float] = None,
        force: bool = False,
        include_mp: bool = True,
    ) -> Tuple[bool, str]:
        """Kauft im Auto-Jagd-Modus automatisch Heiltränke (und optional Manatränke) nach, sobald der Vorrat niedrig ist
        oder 'force=True' (manueller Schnellkauf im Auto-Jagd-Fenster) ausgelöst wird."""
        if not p:
            return False, "Spieler nicht aktiv."
        if now is None:
            now = time.time()
        player_id = p["player_id"]
        is_bot = str(player_id).startswith("bot_")
        af = p.setdefault("autofarm", {})
        stats = self.ensure_autofarm_stats(af)

        hp_cnt, mp_cnt = self._count_player_potions(p)
        need_hp = force or hp_cnt < 15
        need_mp = include_mp and (force or mp_cnt < 8)
        if not need_hp and not need_mp:
            return False, f"Trank-Vorrat ausreichend ({hp_cnt}× Heiltränke, {mp_cnt}× Manatränke)."

        lvl = int(p.get("level", 1))
        yang = int(p.get("yang", 0))
        bought_parts = []
        total_bought = 0
        total_cost = 0

        if need_hp:
            hp_tpl_id = "potion_hp_medium" if (lvl >= 10 and yang >= 900) else "potion_hp_small"
            hp_tpl = ITEM_TEMPLATES.get(hp_tpl_id, ITEM_TEMPLATES["potion_hp_small"])
            unit_price = max(10, int(hp_tpl.get("buyPrice", 35)))
            desired_hp = 50 if force else max(25, 65 - hp_cnt)
            affordable_hp = yang // unit_price
            buy_hp = min(desired_hp, affordable_hp)
            if buy_hp > 0:
                cost_hp = buy_hp * unit_price
                if self.db.add_item_to_inventory(player_id, hp_tpl_id, buy_hp):
                    yang -= cost_hp
                    p["yang"] = yang
                    total_bought += buy_hp
                    total_cost += cost_hp
                    bought_parts.append(f"{buy_hp}× {hp_tpl['name']}")

        if need_mp:
            mp_tpl = ITEM_TEMPLATES.get("potion_mp_medium")
            if mp_tpl:
                mp_price = max(10, int(mp_tpl.get("buyPrice", 80)))
                desired_mp = 30 if force else max(15, 35 - mp_cnt)
                affordable_mp = yang // mp_price
                buy_mp = min(desired_mp, affordable_mp)
                if buy_mp > 0:
                    cost_mp = buy_mp * mp_price
                    if self.db.add_item_to_inventory(player_id, "potion_mp_medium", buy_mp):
                        yang -= cost_mp
                        p["yang"] = yang
                        total_bought += buy_mp
                        total_cost += cost_mp
                        bought_parts.append(f"{buy_mp}× {mp_tpl['name']}")

        if total_bought <= 0:
            return False, "Nicht genügend Gold im Inventar, um Tränke automatisch nachzukaufen!"

        stats["potionsAutoBought"] = int(stats.get("potionsAutoBought", 0)) + total_bought
        stats["yangSpentOnPotions"] = int(stats.get("yangSpentOnPotions", 0)) + total_cost
        self.db.save_player_state(p)
        self.refresh_player_from_db(player_id)
        summary_str = " & ".join(bought_parts)
        p["autoFarmStatus"] = f"🧪 Auto-Pots nachgekauft: {summary_str} (-{total_cost} Gold)"
        self._emit_combat_event(
            p["map_id"],
            "combat_feedback",
            p["pos_x"],
            p["pos_z"],
            {
                "playerId": player_id,
                "feedbackType": "buff",
                "text": f"🧪 +{total_bought} Tränke nachgekauft (-{total_cost} Gold)",
                "color": "#4ade80",
            },
        )
        return True, f"🧪 Automatisch nachgekauft: {summary_str} für {total_cost} Gold!"

    def use_healing_potion(self, player_id: str, auto_triggered: bool = False) -> Tuple[bool, str]:
        p = self.players.get(player_id)
        if not p:
            return False, "Spieler nicht aktiv."
        if p["hp"] >= p["max_hp"]:
            return False, "Lebenspunkte sind bereits voll."

        af = p.get("autofarm") or {}
        if auto_triggered or (af.get("enabled") and af.get("autoBuyPotions", True)):
            hp_cnt, _ = self._count_player_potions(p)
            if hp_cnt <= 5 and af.get("autoBuyPotions", True):
                self._auto_restock_potions(p, force=False, include_mp=False)

        for pot_id in ("potion_hp_large", "potion_hp_medium", "potion_hp_small"):
            if self.db.consume_item_by_template(player_id, pot_id, 1):
                tpl_pot = ITEM_TEMPLATES[pot_id]
                regen_total = int(tpl_pot.get("regenHp") or tpl_pot.get("healHp", 320))
                regen_dur   = float(tpl_pot.get("regenDuration", 8.0))
                regen_rate  = regen_total / max(regen_dur, 1.0)
                # Sofortiger erster Heil-Schluck (25% sofort) + Rest gleichmäßig über Zeit
                instant_heal = min(max(0, p["max_hp"] - p["hp"]), max(40, int(regen_total * 0.25)))
                p["hp"] = min(p["max_hp"], p["hp"] + instant_heal)
                remaining_regen = max(0, regen_total - instant_heal)

                # Trank-Regen aufstapeln (neuer Trank addiert ausstehende TP)
                existing_rem = float(p.get("potionRegenRemaining", 0.0))
                p["potionRegenRemaining"] = min(
                    float(p["max_hp"]) - float(p["hp"]),
                    existing_rem + remaining_regen,
                )
                p["potionRegenRate"] = max(
                    regen_rate,
                    float(p.get("potionRegenRate", 0.0)),
                )
                if "autofarm" in p and isinstance(p["autofarm"], dict):
                    st = self.ensure_autofarm_stats(p["autofarm"])
                    st["potionsUsed"] = int(st.get("potionsUsed", 0)) + 1
                self.db.save_player_state(p)
                self.refresh_player_from_db(player_id)
                self._emit_combat_event(
                    p["map_id"],
                    "heal",
                    p["pos_x"],
                    p["pos_z"],
                    {"playerId": player_id, "amount": instant_heal, "skillName": "Heiltrank", "color": "#22c55e", "regen": True, "regenTotal": regen_total},
                )
                return True, f"Heiltrank verwendet – regeneriert {regen_total} TP (+{instant_heal} sofort, Rest über {int(regen_dur)}s)."
        return False, "Keine Heiltränke im Inventar!"

    def allocate_stat_point(self, player_id: str, stat_key: str, amount: int = 1) -> Tuple[bool, str]:
        p = self.players.get(player_id)
        if not p or p["stat_points"] <= 0:
            return False, "Keine Statuspunkte verfügbar."
        alias_map = {"int": "int_stat", "str_stat": "str", "dex_stat": "dex"}
        stat_key = alias_map.get(stat_key, stat_key)
        if stat_key not in ("vit", "int_stat", "str", "dex"):
            return False, "Ungültiges Attribut."
        pts = min(max(1, int(amount or 1)), int(p["stat_points"]))
        p[stat_key] += pts
        p["stat_points"] -= pts
        self.compute_player_combat_stats(p)
        self.db.save_player_state(p)
        return True, f"+{pts} Statuspunkt(e) vergeben."

    @staticmethod
    def get_skill_stage_label(lv: int) -> str:
        if lv <= 0:
            return "0 / 20"
        elif 1 <= lv < 20:
            return f"{lv} / 20"
        elif 20 <= lv <= 29:
            return f"M{lv - 19}"
        elif 30 <= lv <= 39:
            return f"G{lv - 29}"
        elif 40 <= lv <= 49:
            return f"P{lv - 39}"
        else:
            return "L1 (MAX)"

    def upgrade_skill_point(self, player_id: str, skill_id: str, is_passive: bool = False) -> Tuple[bool, str]:
        p = self.players.get(player_id)
        if not p:
            return False, "Spieler nicht aktiv."

        # Passive Fertigkeiten (Stufe 0–20) können ausschließlich mit gedroppten Fertigkeitsbüchern erlernt & gesteigert werden!
        if is_passive or skill_id in PASSIVE_SKILL_DEFS:
            return self.read_passive_skill_book(player_id, skill_id)

        if p.get("skill_points", 0) <= 0:
            return False, "Keine Fertigkeitspunkte verfügbar."

        doc_skills = self.get_player_doctrine_skills(p)
        sk_info = next((s for s in doc_skills if s["id"] == skill_id), None)
        if not sk_info:
            return False, "Fertigkeit gehört nicht zu deiner Klasse."

        skills_dict = p.setdefault("skills", {})
        # Gesperrte 6. und 7. Fertigkeiten müssen zuerst freigeschaltet werden
        if sk_info.get("special") and skill_id not in skills_dict:
            return False, f"⚠️ '{sk_info['name']}' ist noch gesperrt! Schalte sie zuerst mit der 'Schriftrolle der geheimen Künste' frei."

        cur = int(skills_dict.get(skill_id, 0))
        if cur >= 20:
            return False, f"⚠️ '{sk_info['name']}' ist bereits Meister ({self.get_skill_stage_label(cur)})! Steigere sie mit Fertigkeitsbüchern weiter."

        p["skill_points"] -= 1
        if cur == 19:
            skills_dict[skill_id] = 20  # Level 20 = M1!
            msg = f"🎉 MEISTER-SPRUNG! '{sk_info['name']}' hat Stufe 20 erreicht und ist zum Meister (M1) aufgestiegen!"
        else:
            new_lv = cur + 1
            skills_dict[skill_id] = new_lv
            msg = f"✨ '{sk_info['name']}' gesteigert auf Stufe {new_lv} / 20!"

        self.compute_player_combat_stats(p)
        self.db.save_player_state(p)
        self.refresh_player_from_db(player_id)
        return True, msg

    def upgrade_pet_skill(self, player_id: str, skill_id: str) -> Tuple[bool, str]:
        p = self.players.get(player_id)
        if not p:
            return False, "Spieler nicht gefunden."
        pd = self._ensure_player_pet_data(p)
        sk_def = PET_SKILL_MAP.get(skill_id)
        if not sk_def:
            return False, "Unbekannte Begleiter-Fertigkeit."
        if int(pd.get("skillPoints", 0)) <= 0:
            return False, "Keine Pet-Skillpunkte verfügbar! Dein Begleiter erhält Punkte beim Level-Up."
        skills = pd.setdefault("skills", {})
        cur_lvl = int(skills.get(skill_id, 0))
        max_lvl = int(sk_def.get("maxLevel", 20))
        if cur_lvl >= max_lvl:
            return False, f"'{sk_def['name']}' hat bereits die Maximalstufe ({max_lvl}/{max_lvl}) erreicht!"
        skills[skill_id] = cur_lvl + 1
        pd["skillPoints"] = max(0, int(pd.get("skillPoints", 0)) - 1)
        self.compute_player_combat_stats(p)
        self.db.save_player_state(p)
        return True, f"🐾 Pet-Skill '{sk_def['name']}' auf Stufe {cur_lvl + 1}/{max_lvl} verbessert!"

    def allocate_pet_stat(self, player_id: str, stat_key: str, amount: int = 1) -> Tuple[bool, str]:
        p = self.players.get(player_id)
        if not p:
            return False, "Spieler nicht gefunden."
        pd = self._ensure_player_pet_data(p)
        stat_key = str(stat_key or "").lower()
        stat_labels = {
            "vit": "VIT (Vitalität)",
            "str": "STR (Stärke)",
            "dex": "DEX (Beweglichkeit)",
            "int": "INT (Intelligenz)",
        }
        if stat_key not in stat_labels:
            return False, "Ungültiges Begleiter-Attribut."
        avail = int(pd.get("statPoints", 0))
        if avail <= 0:
            return False, "Keine Pet-Statuspunkte verfügbar! Dein Begleiter erhält Statuspunkte beim Level-Up."
        cur_val = int(pd.get(stat_key, 1))
        if cur_val >= MAX_PET_STAT_POINTS:
            return False, f"{stat_labels[stat_key]} hat bereits das Maximum ({MAX_PET_STAT_POINTS}) erreicht!"
        pts = min(max(1, int(amount or 1)), avail, MAX_PET_STAT_POINTS - cur_val)
        pd[stat_key] = cur_val + pts
        pd["statPoints"] = max(0, avail - pts)
        self.compute_player_combat_stats(p)
        self.db.save_player_state(p)
        return True, f"🐾 +{pts} Punkt(e) in {stat_labels[stat_key]} deines Begleiters investiert ({pd[stat_key]}/{MAX_PET_STAT_POINTS})!"

    def rename_pet(self, player_id: str, new_name: str) -> Tuple[bool, str]:
        p = self.players.get(player_id)
        if not p:
            return False, "Spieler nicht gefunden."
        clean = str(new_name or "").strip()[:24]
        if len(clean) < 2:
            return False, "Der Name deines Begleiters muss mindestens 2 Zeichen lang sein."
        pd = self._ensure_player_pet_data(p)
        pd["customName"] = clean
        self.compute_player_combat_stats(p)
        self.db.save_player_state(p)
        return True, f"🐾 Dein Begleiter heißt nun '{clean}'!"

    def select_pet_skin(self, player_id: str, skin_key: str) -> Tuple[bool, str]:
        p = self.players.get(player_id)
        if not p:
            return False, "Spieler nicht gefunden."
        clean_skin = str(skin_key or "").strip()
        if clean_skin not in self.VALID_PET_SKINS:
            clean_skin = "ridack_dragonpet"
        pd = self._ensure_player_pet_data(p)
        old_skin_label = self.VALID_PET_SKINS.get(pd.get("skinKey", "ridack_dragonpet"), "Grüner Smaragddrache")
        new_skin_label = self.VALID_PET_SKINS[clean_skin]
        pd["skinKey"] = clean_skin
        if not pd.get("customName") or pd["customName"] in (old_skin_label, "Grüner Smaragddrache"):
            pd["customName"] = new_skin_label
        self.compute_player_combat_stats(p)
        self.db.save_player_state(p)
        return True, f"🐾 3D-Begleiter-Aussehen auf '{new_skin_label}' gewechselt!"

    def level_up_horse(self, player_id: str) -> Tuple[bool, str]:
        p = self.players.get(player_id)
        if not p:
            return False, "Spieler nicht gefunden."
        if str(player_id or "").startswith("bot_"):
            return False, "🚫 Pferdemedaillen-Sperre aktiv (SSOT): Bis Affen hinzugefügt werden, steigert kein Bot sein Pferde-Level!"
        md = self._ensure_player_mount_data(p)
        cur_lvl = int(md.get("level", 1))
        if cur_lvl >= MAX_HORSE_LEVEL:
            return False, f"🐎 Dein Pferd hat bereits die maximale Stufe {MAX_HORSE_LEVEL} (Militärgaul) erreicht!"
        req_medals = get_required_horse_medals(cur_lvl)
        inv = p.setdefault("inventory", [])
        total_medals = sum(
            int(it.get("quantity", 1))
            for it in inv
            if it.get("templateId") == "pferdemedaille" and not it.get("reservedShopId")
        )
        if total_medals < req_medals:
            return (
                False,
                f"🏅 Nicht genügend Pferdemedaillen! Für Stufe {cur_lvl + 1} werden {req_medals}x Pferdemedaille benötigt (im Besitz: {total_medals}x).",
            )

        rem = req_medals
        for it in list(inv):
            if rem <= 0:
                break
            if it.get("templateId") == "pferdemedaille" and not it.get("reservedShopId"):
                qty = int(it.get("quantity", 1))
                take = min(rem, qty)
                rem -= take
                if qty - take <= 0:
                    inv.remove(it)
                else:
                    it["quantity"] = qty - take

        new_lvl = cur_lvl + 1
        raw_mount = p.setdefault("quests", {}).setdefault("__mount_profile__", {})
        raw_mount["level"] = new_lvl
        p["mountData"] = raw_mount
        updated_md = self._ensure_player_mount_data(p)
        self.compute_player_combat_stats(p)
        self.db.save_player_state(p)

        if new_lvl == 35:
            return (
                True,
                "🐎✨ RANG-AUFSTIEG ZUM KAMPFPFERD (Stufe 35)! Höherer Grundschaden & doppelt so starke Sattel-Statuspunkte freigeschaltet! (+2 Statuspunkte)",
            )
        if new_lvl == 50:
            return (
                True,
                "🐎👑 RANG-AUFSTIEG ZUM MILITÄRGAUL (Stufe 50)! Maximale Sattel-Kampfkraft & alle 3 Pferde-Fertigkeiten freigeschaltet! Ziehe sie jetzt in deine Taskbar!",
            )
        return (
            True,
            f"🐎 Pferd auf Stufe {new_lvl}/{MAX_HORSE_LEVEL} ({updated_md['tierShort']}) gesteigert! (-{req_medals}x Pferdemedaille • +2 Sattel-Statuspunkte)",
        )

    def allocate_mount_stat(self, player_id: str, stat_key: str, amount: int = 1) -> Tuple[bool, str]:
        p = self.players.get(player_id)
        if not p:
            return False, "Spieler nicht gefunden."
        if str(player_id or "").startswith("bot_"):
            return False, "🚫 Pferdemedaillen-Sperre aktiv (SSOT): Bots verteilen keine Sattel-Statuspunkte!"
        md = self._ensure_player_mount_data(p)
        avail = int(md.get("statPoints", 0))
        if avail <= 0:
            return False, "Keine Sattel-Statuspunkte verfügbar! Steigere dein Pferd mit Pferdemedaillen für weitere Punkte."
        sk = str(stat_key or "").lower()
        if sk not in ("dmg", "hp"):
            return False, "Ungültiges Reittier-Attribut."
        pts = min(max(1, int(amount or 1)), avail)
        raw_mount = p.setdefault("quests", {}).setdefault("__mount_profile__", {})
        if sk == "dmg":
            raw_mount["dmgPoints"] = int(md.get("dmgPoints", 0)) + pts
            label = "Kampfkraft im Sattel (Schaden & STR)"
        else:
            raw_mount["hpPoints"] = int(md.get("hpPoints", 0)) + pts
            label = "Vitalität im Sattel (Max. TP & Verteidigung)"
        p["mountData"] = raw_mount
        self._ensure_player_mount_data(p)
        self.compute_player_combat_stats(p)
        self.db.save_player_state(p)
        return True, f"🐎 +{pts} Punkt(e) in {label} investiert!"

    def reset_mount_stats(self, player_id: str) -> Tuple[bool, str]:
        p = self.players.get(player_id)
        if not p:
            return False, "Spieler nicht gefunden."
        raw_mount = p.setdefault("quests", {}).setdefault("__mount_profile__", {})
        raw_mount["dmgPoints"] = 0
        raw_mount["hpPoints"] = 0
        p["mountData"] = raw_mount
        md = self._ensure_player_mount_data(p)
        self.compute_player_combat_stats(p)
        self.db.save_player_state(p)
        return True, f"↺ Sattel-Statuspunkte zurückgesetzt! ({md.get('statPoints', 0)} Punkte neu verteilbar)"

    def set_mount_skin(self, player_id: str, skin_id: str) -> Tuple[bool, str]:
        p = self.players.get(player_id)
        if not p:
            return False, "Spieler nicht gefunden."
        sid = str(skin_id or "none").strip()
        if sid not in MOUNT_SKIN_MAP:
            sid = "none"
        raw_mount = p.setdefault("quests", {}).setdefault("__mount_profile__", {})
        raw_mount["equippedSkin"] = sid
        raw_mount["skinExplicit"] = True
        p["mountData"] = raw_mount
        md = self._ensure_player_mount_data(p)
        self.compute_player_combat_stats(p)
        self.db.save_player_state(p)
        s_def = MOUNT_SKIN_MAP[sid]
        if sid == "none":
            return True, f"🐎 Standard-Aussehen aktiv: {md.get('tierName')}!"
        return True, f"🐎✨ Mount-Skin '{s_def['name']}' ausgerüstet! ({s_def['bonusSummary']})"

    def rename_mount(self, player_id: str, new_name: str) -> Tuple[bool, str]:
        p = self.players.get(player_id)
        if not p:
            return False, "Spieler nicht gefunden."
        clean = str(new_name or "").strip()[:24]
        if len(clean) < 2:
            return False, "Der Name deines Reittiers muss mindestens 2 Zeichen lang sein."
        raw_mount = p.setdefault("quests", {}).setdefault("__mount_profile__", {})
        raw_mount["customName"] = clean
        p["mountData"] = raw_mount
        self._ensure_player_mount_data(p)
        self.db.save_player_state(p)
        return True, f"🐎 Dein Reittier heißt nun '{clean}'!"

    def blacksmith_upgrade(
        self,
        player_id: str,
        item_uid: str,
        use_blessing: bool = False,
        method: str = "",
        use_magic_metal: bool = False,
    ) -> Tuple[bool, str, bool]:
        """Serverseitiges Schmied-Upgrade (+0 bis +9) inkl. Methoden (Normaler Schmied, Segi, Magisches Metall)."""
        p = self.players.get(player_id)
        if not p:
            return False, "Spieler nicht gefunden.", False

        all_items = [x for x in (list(p.get("inventory", [])) + list((p.get("equipment") or {}).values())) if isinstance(x, dict)]
        target_item = next((i for i in all_items if i.get("uid") == item_uid), None)
        if not target_item:
            return False, "Gegenstand nicht gefunden.", False
        if target_item["type"] != "equipment":
            return False, "Nur Ausrüstung kann beim Schmied verbessert werden.", False

        cur_plus = int(target_item["plusLevel"])
        if cur_plus >= 9:
            return False, "Dieser Gegenstand hat bereits die Höchststufe +9 erreicht!", False

        is_sa_smith = self._is_sa_player(p, player_id)
        rate_info = get_blacksmith_upgrade_req(target_item["templateId"], cur_plus)
        cost_yang = 0 if is_sa_smith else int(rate_info["yang"])
        if not is_sa_smith and p["yang"] < cost_yang:
            return False, f"Nicht genug Gold! Benötigt: {cost_yang:,} Gold.", False

        mat_id = rate_info["matId"]
        mat_count = int(rate_info["matCount"] or 0)
        if not is_sa_smith and mat_id and mat_count > 0:
            if not self.db.consume_item_by_template(player_id, mat_id, mat_count):
                mat_name = ITEM_TEMPLATES.get(mat_id, {}).get("name", mat_id)
                return False, f"Fehlendes Material: {mat_count}x {mat_name} benötigt!", False

        eff_method = method or ("ritual" if use_magic_metal else ("scroll" if use_blessing else "none"))
        blessing_bonus = 0.0
        if not is_sa_smith:
            if eff_method == "scroll":
                if not self.db.consume_item_by_template(player_id, "scroll_blessing", 1):
                    return False, "Keine Segensschriftrolle im Inventar!", False
                blessing_bonus = 0.10
            elif eff_method in ("ritual", "metal", "magic_metal"):
                eff_method = "ritual"
                if not (
                    self.db.consume_item_by_template(player_id, "item_magic_metal", 1)
                    or self.db.consume_item_by_template(player_id, "item_soul_fragment", 1)
                ):
                    return False, "Kein Magisches Metall im Inventar!", False
                blessing_bonus = 0.10

        p["yang"] = max(0, p["yang"] - cost_yang)
        passive_smith = p.get("passives", {}).get("schmiedkunst", 0) * 0.005
        final_chance = 1.0 if is_sa_smith else min(0.98, rate_info["chance"] + blessing_bonus + passive_smith)
        success = True if is_sa_smith else (random.random() <= final_chance)

        if success:
            new_plus = cur_plus + 1
            self.db.update_item_upgrade_and_bonuses(item_uid, new_plus, target_item["bonuses"], target_item["lockedBonusIdx"])
            self.db.save_player_state(p)
            self.refresh_player_from_db(player_id)
            if new_plus >= 7:
                self.add_chat_message(
                    "Schmied-Herold",
                    f"🔨 {p['name']} hat erfolgreich {target_item['name']} auf +{new_plus} geschmiedet!",
                    channel="event",
                )
            return True, f"✨ Erfolg! {target_item['name']} wurde auf +{new_plus} geschmiedet!", True
        else:
            if eff_method == "ritual":
                new_plus = cur_plus
                fail_msg = f"🛡️ Fehlgeschlagen! Dank Magischem Metall bleibt {target_item['name']} sicher auf +{new_plus}."
                self.db.update_item_upgrade_and_bonuses(item_uid, new_plus, target_item["bonuses"], target_item["lockedBonusIdx"])
            elif eff_method == "scroll":
                new_plus = max(0, cur_plus - 1)
                fail_msg = f"❌ Fehlgeschlagen! Dank Segensschriftrolle kein Bruch (Stufe +{new_plus})."
                self.db.update_item_upgrade_and_bonuses(item_uid, new_plus, target_item["bonuses"], target_item["lockedBonusIdx"])
            else:
                # Normaler Schmied / Schnell-Funktion ohne Segensschriftrolle: Gegenstand zerbricht und verschwindet aus dem Inventar!
                item_label = f"{target_item['name']} +{cur_plus}"
                self.db.delete_item(player_id, item_uid, allow_equipped=True)
                fail_msg = f"💥 Fehlgeschlagen beim Schmied! {item_label} ist zerbrochen und aus dem Inventar verschwunden!"
            self.db.save_player_state(p)
            self.refresh_player_from_db(player_id)
            p_after = self.players.get(player_id)
            if p_after:
                if str(player_id).startswith("bot_"):
                    self._auto_equip_best_inventory_items_for_bot(p_after, now=time.time())
                self.compute_player_combat_stats(p_after)
            return True, fail_msg, False

    def runeweaver_action(self, player_id: str, item_uid: str, action: str, lock_idx: int = -1) -> Tuple[bool, str]:
        """Seelenverbesserung & Runenweberin: 'add'/'add5'/'add67' (1.-7. Bonus), 'reroll' (Bonuswandler), 'lock' (Äthersiegel)."""
        p = self.players.get(player_id)
        if not p:
            return False, "Spieler nicht aktiv."
        all_items = [x for x in (list(p.get("inventory", [])) + list((p.get("equipment") or {}).values())) if isinstance(x, dict)]
        item = next((i for i in all_items if i.get("uid") == item_uid), None)
        if not item or item["type"] != "equipment":
            return False, "Bitte wähle ein Ausrüstungsteil aus."

        bonuses = list(item.get("bonuses", []))
        locked = int(item.get("lockedBonusIdx", -1))
        tpl = ITEM_TEMPLATES.get(item.get("templateId", ""), {})
        item_slot = str(item.get("slot") or tpl.get("slot") or "weapon")

        if action == "lock":
            if lock_idx < 0 or lock_idx >= len(bonuses) or locked == lock_idx:
                locked = -1
                self.db.update_item_upgrade_and_bonuses(item_uid, item["plusLevel"], bonuses, locked)
                self.refresh_player_from_db(player_id)
                return True, "🔓 Bonus-Versiegelung aufgehoben."
            if not self.db.consume_item_by_template(player_id, "item_aether_seal", 1):
                return False, "Du benötigst 1x Äthersiegel zum Versiegeln eines Bonus!"
            locked = lock_idx
            self.db.update_item_upgrade_and_bonuses(item_uid, item["plusLevel"], bonuses, locked)
            self.refresh_player_from_db(player_id)
            return True, f"🔒 Bonus '{bonuses[lock_idx]['name']}' mit Äthersiegel geschützt!"

        std_bonuses = [b for b in bonuses if b.get("id") != "socket_stone" and not b.get("isYellow67")]
        socket_stones = [b for b in bonuses if b.get("id") == "socket_stone"]
        yellow_bonuses = [b for b in bonuses if b.get("isYellow67")]

        if action == "add":
            if len(std_bonuses) >= 5:
                return False, "Dieser Gegenstand besitzt bereits alle 5 grünen/weißen Standard-Boni!"
            if not (
                self.db.consume_item_by_template(player_id, "item_bonus_adder", 1)
                or (len(std_bonuses) == 4 and self.db.consume_item_by_template(player_id, "item_blessing_orb", 1))
            ):
                return False, "Du benötigst 1x 'Bonus hinzufügen (Gegenstand verstärken)'!"

            used_ids = {b["id"] for b in std_bonuses}
            is_max = str(item.get("rarity") or "") == "instabil"
            rolled = roll_slot_bonus(item_slot, used_ids, max_roll=is_max)
            std_bonuses.append(rolled)
            new_all = std_bonuses + yellow_bonuses + socket_stones
            self.db.update_item_upgrade_and_bonuses(item_uid, item["plusLevel"], new_all, locked)
            self.refresh_player_from_db(player_id)
            slot_num = len(std_bonuses)
            val_str = f"+{rolled['value']}{rolled['unit']} " if rolled["id"] != "bonus_stun_immune" else ""
            return True, f"➕ {slot_num}. Standard-Bonus ({item_slot.upper()}) hinzugefügt: {val_str}{rolled['name']}!"

        if action == "add5":
            if len(std_bonuses) < 4:
                return False, f"Du benötigst zuerst 4 Standard-Boni ({len(std_bonuses)}/4 vorhanden), bevor der 5. Bonus freigeschaltet werden kann!"
            if len(std_bonuses) >= 5:
                return False, "Dieser Gegenstand besitzt bereits den 5. Bonusplatz!"
            if not (
                self.db.consume_item_by_template(player_id, "item_blessing_orb", 1)
                or self.db.consume_item_by_template(player_id, "item_bonus_adder", 1)
            ):
                return False, "Du benötigst 1x 'Segenskugel' oder 'Bonus hinzufügen' für den 5. Bonus!"

            used_ids = {b["id"] for b in std_bonuses}
            is_max = str(item.get("rarity") or "") == "instabil"
            rolled = roll_slot_bonus(item_slot, used_ids, max_roll=is_max)
            std_bonuses.append(rolled)
            new_all = std_bonuses + yellow_bonuses + socket_stones
            self.db.update_item_upgrade_and_bonuses(item_uid, item["plusLevel"], new_all, locked)
            self.refresh_player_from_db(player_id)
            val_str = f"+{rolled['value']}{rolled['unit']} " if rolled["id"] != "bonus_stun_immune" else ""
            return True, f"🌟 5. Bonus freigeschaltet: {val_str}{rolled['name']}!"

        if action == "add67":
            if len(std_bonuses) < 5:
                return False, f"Du benötigst zuerst 5 Standard-Boni ({len(std_bonuses)}/5 vorhanden), bevor der goldene 6. und 7. Endgame-Bonus freigeschaltet werden können!"
            if len(yellow_bonuses) >= 2:
                return False, "Dieser Gegenstand besitzt bereits das Maximum von 2 goldenen Endgame-Boni (6. & 7. Bonus)!"
            if not (self.db.consume_item_by_template(player_id, "item_soul_fragment", 1) or self.db.consume_item_by_template(player_id, "mat_soul_stone", 1)):
                return False, "Du benötigst 1x 'Seelenstein / Seelenfragment' für den goldenen 6. bzw. 7. Endgame-Bonus!"

            used_67_ids = {b["id"] for b in yellow_bonuses}
            is_max = str(item.get("rarity") or "") == "instabil"
            rolled = roll_67_bonus(used_67_ids, max_roll=is_max)
            yellow_bonuses.append(rolled)
            new_all = std_bonuses + yellow_bonuses + socket_stones
            self.db.update_item_upgrade_and_bonuses(item_uid, item["plusLevel"], new_all, locked)
            self.refresh_player_from_db(player_id)
            slot_num = 5 + len(yellow_bonuses)
            return True, f"💛 {slot_num}. Goldener Endgame-Bonus freigeschaltet: +{rolled['value']}{rolled['unit']} {rolled['name']}!"

        if action == "reroll":
            if not std_bonuses:
                return False, "Füge zuerst mindestens einen Bonus hinzu."
            if not self.db.consume_item_by_template(player_id, "item_bonus_changer", 1):
                return False, "Du benötigst 1x 'Bonuswandler (Verzaubern)'!"
            new_std = []
            used_ids = set()
            is_max = str(item.get("rarity") or "") == "instabil"
            if 0 <= locked < len(std_bonuses):
                used_ids.add(std_bonuses[locked]["id"])

            for idx, old_b in enumerate(std_bonuses):
                if idx == locked:
                    new_std.append(old_b)
                elif tpl.get("hasDssFks") and old_b.get("id") in ("bonus_dss", "bonus_fks"):
                    if old_b.get("id") == "bonus_dss":
                        dss_v = random.randint(48, 55) if is_max else max(-25, min(52, int(round(random.gauss(5, 11)))))
                        new_std.append({"id": "bonus_dss", "name": "Durchschn. Schaden (DSS)", "value": dss_v, "maxValue": 55, "unit": "%"})
                        used_ids.add("bonus_dss")
                    else:
                        prev_dss = next((b["value"] for b in new_std if b.get("id") == "bonus_dss"), 0)
                        fks_v = random.randint(18, 25) if is_max else max(-18, min(24, int(round(-prev_dss * 0.36 + random.gauss(1, 4)))))
                        new_std.append({"id": "bonus_fks", "name": "Fertigkeitsschaden (FKS)", "value": fks_v, "maxValue": 25, "unit": "%"})
                        used_ids.add("bonus_fks")
                else:
                    rolled = roll_slot_bonus(item_slot, used_ids, max_roll=is_max)
                    used_ids.add(rolled["id"])
                    new_std.append(rolled)
            new_all = new_std + yellow_bonuses + socket_stones
            self.db.update_item_upgrade_and_bonuses(item_uid, item["plusLevel"], new_all, locked)
            self.refresh_player_from_db(player_id)
            return True, f"🔮 1.–{len(new_std)}. Bonus ({item_slot.upper()}-Pool) neu ausgewürfelt! (6./7. Bonus bleibt unberührt)"

        if action == "reroll67":
            if not yellow_bonuses:
                return False, "Dieser Gegenstand besitzt noch keinen 6. oder 7. Endgame-Bonus zum Switchen!"
            if not (
                self.db.consume_item_by_template(player_id, "item_soul_fragment", 1)
                or self.db.consume_item_by_template(player_id, "mat_soul_stone", 1)
            ):
                return False, "Du benötigst 1x Seelenstein (oder Seelenfragment) zum Switchen des goldenen 6./7. Bonus!"
            new_yel = []
            used_67_ids = set()
            is_max = str(item.get("rarity") or "") == "instabil"
            for idx, old_yb in enumerate(yellow_bonuses):
                abs_idx = len(std_bonuses) + idx
                if abs_idx == locked:
                    new_yel.append(old_yb)
                    used_67_ids.add(old_yb["id"])
                else:
                    rolled = roll_67_bonus(used_67_ids, max_roll=is_max)
                    used_67_ids.add(rolled["id"])
                    new_yel.append(rolled)
            new_all = std_bonuses + new_yel + socket_stones
            self.db.update_item_upgrade_and_bonuses(item_uid, item["plusLevel"], new_all, locked)
            self.refresh_player_from_db(player_id)
            return True, "💛 Goldener 6./7. Endgame-Bonus mit Seelenstein neu ausgewürfelt (1.–5. Bonus blieb unangetastet)!"

        return False, "Unbekannte Runen-Aktion."

    def use_or_open_inventory_item(
        self, player_id: str, item_uid: str, target_slot: Optional[str] = None
    ) -> Tuple[bool, str]:
        p = self.players.get(player_id)
        if not p:
            return False, "Spieler nicht aktiv."
        item = next((i for i in p.get("inventory", []) if i["uid"] == item_uid), None)
        if not item:
            item = next((i for i in p.get("equipment", {}).values() if i and i.get("uid") == item_uid), None)
        if not item:
            return False, "Gegenstand nicht im Inventar."

        tpl_id = item["templateId"]
        if item["type"] == "equipment":
            ok, msg = self.db.equip_or_unequip_item(player_id, item_uid, p["level"], target_slot=target_slot)
            self.refresh_player_from_db(player_id)
            return ok, msg

        if item["type"] == "mount_seal":
            if target_slot:
                return False, "Mount-Siegel werden nicht ausgerüstet — Rechtsklick im Inventar schaltet das Mount AN/AUS!"
            now_t = time.time()
            if now_t - float(p.get("_lastMountToggleAt", 0.0) or 0.0) < 0.45:
                return True, ""
            p["_lastMountToggleAt"] = now_t
            mount_id = item.get("mountId") or ITEM_TEMPLATES.get(tpl_id, {}).get("mountId") or "mount_war_boar"
            if p.get("active_mount") == mount_id:
                p["active_mount"] = None
                p["_manualDismountUntil"] = now_t + 6.0
                msg = f"🐺 {MOUNTS.get(mount_id, {}).get('name', 'Reittier')} abberufen (Siegel bleibt im Inventar)."
            else:
                if mount_id not in MOUNTS:
                    mount_id = "mount_war_boar"
                p["active_mount"] = mount_id
                p["_manualDismountUntil"] = 0.0
                m_info = MOUNTS[mount_id]
                msg = f"🐺 {m_info['name']} gerufen (+{m_info['speedBonusPct']}% Tempo — Siegel bleibt im Inventar)!"
            self.compute_player_combat_stats(p)
            self.db.save_player_state(p)
            self.refresh_player_from_db(player_id)
            return True, msg

        if item["type"] == "pet_seal":
            if target_slot:
                return False, "Pet-Siegel werden nicht ausgerüstet — Rechtsklick im Inventar schaltet das Pet AN/AUS!"
            pet_id = item.get("petId") or ITEM_TEMPLATES.get(tpl_id, {}).get("petId") or "pet_fire_phoenix"
            if p.get("active_pet") == pet_id:
                p["active_pet"] = None
                msg = f"🦅 {PETS.get(pet_id, {}).get('name', 'Begleiter')} zurückgerufen (Siegel bleibt im Inventar)."
            else:
                if pet_id not in PETS:
                    pet_id = "pet_fire_phoenix"
                p["active_pet"] = pet_id
                p_info = PETS[pet_id]
                msg = f"🦅 {p_info['name']} begleitet dich jetzt (Siegel bleibt im Inventar)!"
            self.compute_player_combat_stats(p)
            self.db.save_player_state(p)
            self.refresh_player_from_db(player_id)
            return True, msg

        if item["type"] == "spirit_stone":
            st_tpl = ITEM_TEMPLATES.get(tpl_id, {})
            eq_target_slot = st_tpl.get("targetSlot", "weapon")
            eq_item = (p.get("equipment") or {}).get(eq_target_slot)
            if not eq_item:
                slot_lbl = "Waffe" if eq_target_slot == "weapon" else "Rüstung"
                return False, f"⚠️ Rüste zuerst eine {slot_lbl} aus, um diesen Geiststein zu sockeln!"
            bonuses_eq = list(eq_item.get("bonuses") or [])
            sockets = [b for b in bonuses_eq if b.get("id") == "socket_stone"]
            st_fam = st_tpl.get("stoneFamily", tpl_id)
            st_grade = int(st_tpl.get("stoneGrade", 0))
            existing_fam = next((s for s in sockets if s.get("stoneFamily") == st_fam), None)
            if existing_fam and int(existing_fam.get("stoneGrade", 0)) >= st_grade:
                return False, f"⚠️ In {eq_item['name']} ist bereits ein gleichwertiger oder höherer {existing_fam.get('name', 'Geiststein')} gesockelt!"
            if not existing_fam and len(sockets) >= 3:
                return False, f"⚠️ {eq_item['name']} besitzt bereits das Maximum von 3 gesockelten Geiststeinen!"
            if not self.db.consume_item_by_template(player_id, tpl_id, 1):
                return False, "Geiststein nicht im Inventar."
            if random.random() > 0.75:
                self.refresh_player_from_db(player_id)
                return False, f"💥 Das Sockeln von {st_tpl.get('name', tpl_id)} ist fehlgeschlagen – der Geiststein ist zersplittert!"
            new_bonuses = [b for b in bonuses_eq if not (b.get("id") == "socket_stone" and b.get("stoneFamily") == st_fam)]
            new_bonuses.append({
                "id": "socket_stone",
                "stoneId": tpl_id,
                "stoneFamily": st_fam,
                "stoneGrade": st_grade,
                "stoneStat": st_tpl.get("stoneStat", "vsMonsterPct"),
                "name": f"💎 {st_tpl.get('name', tpl_id)}",
                "value": st_tpl.get("stoneValue", 0),
                "unit": st_tpl.get("stoneUnit", "%"),
            })
            self.db.update_item_upgrade_and_bonuses(eq_item["uid"], eq_item["plusLevel"], new_bonuses, eq_item.get("lockedBonusIdx", -1))
            self.refresh_player_from_db(player_id)
            return True, f"💎 {st_tpl.get('name', tpl_id)} erfolgreich in {eq_item['name']} gesockelt (+{st_tpl.get('stoneValue')}{st_tpl.get('stoneUnit', '')} {st_tpl.get('bonusLabel', '')})!"

        if item["type"] == "consumable":
            if tpl_id == "potion_mp_medium":
                if not self.db.consume_item_by_template(player_id, tpl_id, 1):
                    return False, "Kein Manatrank vorhanden."
                p["mp"] = min(p["max_mp"], p["mp"] + 450)
                self.db.save_player_state(p)
                self.refresh_player_from_db(player_id)
                return True, "🧪 Blauer Manatrank (G) getrunken (+450 MP)!"
            if tpl_id == "potion_speed":
                if not self.db.consume_item_by_template(player_id, tpl_id, 1):
                    return False, "Kein Violetter Trank vorhanden."
                p.setdefault("activeBuffs", {})["potion_speed"] = {
                    "name": "Violetter Trank (+15% Angriffs- & +20% Bewegungstempo)",
                    "atkPct": 0,
                    "atkSpeedPct": 15,
                    "moveSpeedPct": 20,
                    "expiresAt": time.time() + 600.0,
                }
                self.compute_player_combat_stats(p)
                self.db.save_player_state(p)
                self.refresh_player_from_db(player_id)
                return True, "🟣 Violetter Trank (G) aktiviert (+15% Angriffs- & +20% Bewegungsgeschwindigkeit für 10 Min.)!"
            if tpl_id == "potion_atk_speed":
                if not self.db.consume_item_by_template(player_id, tpl_id, 1):
                    return False, "Kein Grüner Trank vorhanden."
                p.setdefault("activeBuffs", {})["potion_atk_speed"] = {
                    "name": "Grüner Trank (+20% Bewegungstempo)",
                    "atkPct": 0,
                    "atkSpeedPct": 0,
                    "moveSpeedPct": 20,
                    "expiresAt": time.time() + 600.0,
                }
                self.compute_player_combat_stats(p)
                self.db.save_player_state(p)
                self.refresh_player_from_db(player_id)
                return True, "🟢 Grüner Trank (G) aktiviert (+20% Bewegungsgeschwindigkeit für 10 Min.)!"
            if tpl_id == "orb_vwk":
                if not self.db.consume_item_by_template(player_id, tpl_id, 1):
                    return False, "Keine Verwandlungskugel vorhanden."
                p.setdefault("activeBuffs", {})["orb_vwk"] = {
                    "name": "Verwandlungskugel (VWK • +25% AW & 2H-Tempo)",
                    "atkPct": 25,
                    "speedPct": 22,
                    "expiresAt": time.time() + 180.0,
                }
                self.compute_player_combat_stats(p)
                self.db.save_player_state(p)
                self.refresh_player_from_db(player_id)
                return True, "🔮 Verwandlungskugel (VWK) aktiviert (+25% AW & volle Zweihand-Angriffsgeschwindigkeit für 180 Sek.)!"
            if tpl_id == "arrow_bundle":
                return True, "🏹 Köcher der Schattenpfeile im Inventar bereit (+15 Pfeil-AW für Bögen)."
            if tpl_id in ("cape_bravery", "item_bravery_cape"):
                if not self.db.consume_item_by_template(player_id, tpl_id, 1):
                    return False, "Kein Tapferkeitsumhang vorhanden."
                pulled = 0
                for mob in self.monsters.values():
                    if mob["mapId"] == p["map_id"] and mob["state"] != "dead" and mob["kind"] == "monster":
                        if dist2d(mob["x"], mob["z"], p["pos_x"], p["pos_z"]) <= 38.0:
                            mob["state"] = "chase"
                            mob["targetPlayerId"] = player_id
                            pulled += 1
                self.db.save_player_state(p)
                self.refresh_player_from_db(player_id)
                return True, f"🦸 Tapferkeitsumhang genutzt! {pulled} Monster im Umkreis angelockt!"
            return self.use_healing_potion(player_id)

        if item["type"] == "chest":
            if not self.db.consume_item_by_template(player_id, tpl_id, 1):
                return False, "Truhe konnte nicht geöffnet werden."
            if tpl_id in ("chest_monolith_legend", "chest_bloodleaf"):
                rewards = [
                    "wpn_ebenholz_sword", "wpn_ebenholz_greatsword",
                    "wpn_ebenholz_ninja_sword", "wpn_ebenholz_daggers", "wpn_ebenholz_bow",
                    "wpn_ebenholz_sura_sword", "wpn_ebenholz_staff",
                    "arm_ebenholz_warrior", "arm_ebenholz_ninja", "arm_ebenholz_sura", "arm_ebenholz_shaman",
                    "scroll_blessing", "item_bonus_changer", "mat_soul_stone",
                ]
            elif tpl_id == "chest_moonlight":
                rewards = [
                    "potion_speed",
                    "potion_atk_speed",
                    "cape_bravery",
                    "book_skill",
                    "mat_soul_stone",
                    "scroll_blessing",
                ]
            else:
                rewards = ["potion_speed", "potion_atk_speed", "potion_hp_large", "book_skill"]
            won_id = resolve_item_template_id(random.choice(rewards))
            if won_id == "book_skill" and ACTIVE_SKILL_BOOK_IDS:
                won_id = random.choice(list(ACTIVE_SKILL_BOOK_IDS))
            won_tpl = ITEM_TEMPLATES.get(won_id) or ITEM_TEMPLATES["potion_hp_large"]
            plus = 4 if won_tpl.get("type") == "equipment" else 0
            self.db.add_item_to_inventory(player_id, won_tpl["id"], 1, plus_level=plus)
            self.db.save_player_state(p)
            self.refresh_player_from_db(player_id)
            won_name = won_tpl["name"]
            self._log_player_drop(won_id, plus=plus, qty=1, yang_gain=0, source=item["name"], player_id=player_id)
            return True, f"🎁 {item['name']} geöffnet! Erhalten: {won_name}{f' +{plus}' if plus else ''}!"

        if tpl_id in ("mat_monolith_shard", "mat_awakened_rift_core"):
            res = self.interact_with_monolith(player_id, None, mode="awaken")
            return bool(res.get("ok", False)), str(res.get("message", ""))

        if tpl_id == "item_skill_unlock_scroll":
            return self.unlock_next_special_skill(player_id)

        if tpl_id == "mat_legendary_soul_stone":
            return self.train_skill_with_legendary_soul_stone(player_id, None)

        if tpl_id in ("mat_soul_stone", "item_soul_fragment"):
            return self.train_skill_with_soul_stone(player_id, None)

        tpl = ITEM_TEMPLATES.get(tpl_id, {})
        if tpl_id.startswith("fb_passive_") or tpl.get("type") == "passive_skill_book":
            ps_id = tpl.get("passiveId") or tpl.get("skillId") or tpl_id.replace("fb_passive_", "")
            return self.read_passive_skill_book(player_id, ps_id)

        if tpl_id.startswith("fb_") or tpl.get("type") == "skill_book":
            sk_id = tpl.get("skillId")
            return self.read_skill_book(player_id, sk_id)

        if tpl_id in ("chest_skill_books", "book_skill"):
            if not self.db.consume_item_by_template(player_id, tpl_id, 1):
                return False, "Gegenstand nicht vorhanden."
            class_books = [k for k, v in ITEM_TEMPLATES.items() if v.get("type") == "skill_book" and v.get("classId") == p.get("class_id")]
            all_active_books = [k for k, v in ITEM_TEMPLATES.items() if v.get("type") == "skill_book"]
            won_fb = random.choice(class_books if random.random() < 0.70 and class_books else all_active_books)
            self.db.add_item_to_inventory(player_id, won_fb, 1)
            self.db.save_player_state(p)
            self.refresh_player_from_db(player_id)
            return True, f"📖 {item['name']} geöffnet! Erhalten: {ITEM_TEMPLATES[won_fb]['name']}!"

        return False, "Dieser Gegenstand wird beim Schmied oder der Runenweberin verwendet."

    def read_passive_skill_book(self, player_id: str, passive_id: Optional[str] = None) -> Tuple[bool, str]:
        """Erlernt (Stufe 0 ➔ 1) und steigert (bis Stufe 20) eine Passive Fertigkeit ausschließlich über ein gedropptes Fertigkeitsbuch."""
        p = self.players.get(player_id)
        if not p:
            return False, "Spieler nicht aktiv."

        inv = p.get("inventory", [])
        passives_dict = p.setdefault("passives", {})

        if passive_id:
            pdef = PASSIVE_SKILL_DEFS.get(passive_id) if isinstance(PASSIVE_SKILL_DEFS, dict) else next((d for d in PASSIVE_SKILL_DEFS if d.get("id") == passive_id), None)
            if not pdef:
                return False, "Unbekannte passive Fertigkeit."
            target_ps_id = passive_id
            book_item = next(
                (i for i in inv if i.get("templateId") == f"fb_passive_{target_ps_id}" and int(i.get("quantity", 1)) > 0),
                None,
            )
            if not book_item:
                book_item = next(
                    (i for i in inv if i.get("templateId") == "book_skill" and int(i.get("quantity", 1)) > 0),
                    None,
                )
            if not book_item:
                return (
                    False,
                    f"⚠️ Passive Fertigkeiten können nur mit gedroppten Fertigkeitsbüchern erlernt & gesteigert werden! Dir fehlt 'FB {pdef['name']}' (oder Allgemeines Fertigkeitsbuch).",
                )
        else:
            book_item = next(
                (i for i in inv if str(i.get("templateId", "")).startswith("fb_passive_") and int(i.get("quantity", 1)) > 0),
                None,
            )
            if not book_item:
                return False, "⚠️ Kein Passiv-Fertigkeitsbuch im Inventar gefunden."
            tpl_b = ITEM_TEMPLATES.get(book_item["templateId"], {})
            target_ps_id = tpl_b.get("passiveId") or tpl_b.get("skillId") or str(book_item["templateId"]).replace("fb_passive_", "")
            pdef = PASSIVE_SKILL_DEFS.get(target_ps_id) if isinstance(PASSIVE_SKILL_DEFS, dict) else None
            if not pdef:
                return False, "Unbekannte passive Fertigkeit."

        p_name = pdef["name"]
        max_p_lv = int(pdef.get("maxLevel", 20))
        cur_lv = int(passives_dict.get(target_ps_id, 0) or 0)
        if cur_lv >= max_p_lv:
            return False, f"✨ '{p_name}' hat bereits die Maximalstufe ({max_p_lv} / {max_p_lv}) erreicht!"

        if not self.db.consume_item_by_template(player_id, book_item["templateId"], 1):
            return False, "Fertigkeitsbuch konnte nicht verbraucht werden."

        new_lv = cur_lv + 1
        passives_dict[target_ps_id] = new_lv
        self.compute_player_combat_stats(p)
        self.db.save_player_state(p)
        self.refresh_player_from_db(player_id)
        if cur_lv == 0:
            return True, f"📖 Passiv-Fertigkeitsbuch verstanden! '{p_name}' neu erlernt (Stufe 1 / {max_p_lv})!"
        return True, f"📖 Passiv-Fertigkeitsbuch verstanden! '{p_name}' auf Stufe {new_lv} / {max_p_lv} gesteigert!"

    def unlock_next_special_skill(self, player_id: str) -> Tuple[bool, str]:
        """Universelles Freischalt-Item für alle Klassen: schaltet zuerst die 6., dann die 7. Fertigkeit frei."""
        p = self.players.get(player_id)
        if not p:
            return False, "Spieler nicht aktiv."

        inv = p.get("inventory", [])
        scroll = next(
            (i for i in inv if i["templateId"] == "item_skill_unlock_scroll" and int(i.get("quantity", 1)) > 0),
            None,
        )
        if not scroll:
            return False, "⚠️ Keine 'Schriftrolle der geheimen Künste' im Inventar vorhanden!"

        cdef = CHARACTER_CLASSES.get(p.get("class_id", "warrior"), CHARACTER_CLASSES["warrior"])
        skills = cdef.get("skills", [])
        sk6 = next((s for s in skills if s.get("slot") == 6), None)
        sk7 = next((s for s in skills if s.get("slot") == 7), None)

        if not sk6 or not sk7:
            return False, "Fehler: Klasse besitzt keine 6./7. Fertigkeit."

        skills_dict = p.setdefault("skills", {})

        # 1. Schaltet zuerst den 6. Skill frei
        if sk6["id"] not in skills_dict:
            if not self.db.consume_item_by_template(player_id, "item_skill_unlock_scroll", 1):
                return False, "Schriftrolle konnte nicht verwendet werden."
            skills_dict[sk6["id"]] = 0  # Startet auf Stufe 0
            self.compute_player_combat_stats(p)
            self.db.save_player_state(p)
            self.refresh_player_from_db(player_id)
            return (
                True,
                f"📜 Geheime Künste erlernt: 6. Fertigkeit '{sk6['name']}' erfolgreich freigeschaltet! Sie startet auf Stufe 0 und kann nun mit Fertigkeitspunkten (0–20) gesteigert werden.",
            )

        # 2. Wenn 6. Skill bereits offen ist, schaltet sie den 7. Skill frei
        if sk7["id"] not in skills_dict:
            if not self.db.consume_item_by_template(player_id, "item_skill_unlock_scroll", 1):
                return False, "Schriftrolle konnte nicht verwendet werden."
            skills_dict[sk7["id"]] = 0  # Startet auf Stufe 0
            self.compute_player_combat_stats(p)
            self.db.save_player_state(p)
            self.refresh_player_from_db(player_id)
            return (
                True,
                f"📜 Geheime Künste gemeistert: 7. Fertigkeit '{sk7['name']}' erfolgreich freigeschaltet! Sie startet auf Stufe 0 und kann nun mit Fertigkeitspunkten (0–20) gesteigert werden.",
            )

        return False, "⚠️ Du hast bereits alle 7 Fertigkeiten deiner Klasse freigeschaltet!"

    def read_skill_book(self, player_id: str, skill_id: Optional[str] = None) -> Tuple[bool, str]:
        """Steigert eine Fertigkeit von M1 bis M10 (und auf G1) über ihr spezifisches Fertigkeitsbuch."""
        p = self.players.get(player_id)
        if not p:
            return False, "Spieler nicht aktiv."

        cdef = CHARACTER_CLASSES.get(p.get("class_id", "warrior"), CHARACTER_CLASSES["warrior"])
        class_skills = {s["id"]: s for s in self.get_player_doctrine_skills(p)}
        skills_dict = p.setdefault("skills", {})

        inv = p.get("inventory", [])
        if skill_id:
            target_sk = class_skills.get(skill_id)
            if not target_sk:
                return False, "Fertigkeit gehört nicht zu deiner Klasse."
            book_item = next(
                (i for i in inv if i.get("templateId") == f"fb_{skill_id}" and int(i.get("quantity", 1)) > 0),
                None,
            )
            if not book_item:
                return False, f"⚠️ Kein passendes Fertigkeitsbuch ('FB {target_sk['name']}') im Inventar vorhanden!"
            target_sk_id = skill_id
        else:
            book_item = next(
                (i for i in inv if i.get("templateId", "").startswith("fb_") and not i.get("templateId", "").startswith("fb_passive_") and int(i.get("quantity", 1)) > 0),
                None,
            )
            if not book_item:
                return False, "⚠️ Kein Fertigkeitsbuch im Inventar gefunden."
            target_sk_id = ITEM_TEMPLATES.get(book_item["templateId"], {}).get("skillId")
            target_sk = class_skills.get(target_sk_id)
            if not target_sk:
                return False, f"Dieses Fertigkeitsbuch ist nicht für deine Klasse ({cdef['name']}) bestimmt."

        if target_sk.get("special") and target_sk_id not in skills_dict:
            return False, f"⚠️ '{target_sk['name']}' ist noch gesperrt! Schalte sie zuerst mit der 'Schriftrolle der geheimen Künste' frei."

        cur_lv = int(skills_dict.get(target_sk_id, 1))
        sk_name = target_sk["name"]

        if cur_lv < 20:
            return (
                False,
                f"⚠️ '{sk_name}' ist erst auf Stufe {cur_lv}/20 – Fertigkeitsbücher können erst ab Meister M1 (Stufe 20) gelesen werden!",
            )
        if cur_lv >= 30:
            return (
                False,
                f"✨ '{sk_name}' hat bereits Großmeister ({self.get_skill_stage_label(cur_lv)}) erreicht! Nutze Seelensteine zur weiteren Steigerung.",
            )

        if not self.db.consume_item_by_template(player_id, book_item["templateId"], 1):
            return False, "Fertigkeitsbuch konnte nicht verbraucht werden."

        success = random.random() <= 0.70
        if success:
            if cur_lv == 29:  # M10 -> G1!
                new_lv = 30
                skills_dict[target_sk_id] = new_lv
                msg = f"🌟 GROSSMEISTER-DURCHBRUCH! '{sk_name}' ist von M10 auf Großmeister G1 aufgestiegen!"
            else:
                new_lv = cur_lv + 1
                skills_dict[target_sk_id] = new_lv
                msg = f"📖 Fertigkeitsbuch erfolgreich verstanden! '{sk_name}': M{cur_lv - 19} ➔ M{new_lv - 19}!"
        else:
            msg = f"💨 Das Studium von 'FB {sk_name}' ist fehlgeschlagen. Die Runen waren zu komplex!"

        self.compute_player_combat_stats(p)
        self.db.save_player_state(p)
        self.refresh_player_from_db(player_id)
        return success, msg

    def train_skill_with_soul_stone(self, player_id: str, skill_id: Optional[str] = None) -> Tuple[bool, str]:
        """Normale Seelensteine steigern sowohl G1 bis G10 (Übergang auf P1) als auch P1 bis P10."""
        p = self.players.get(player_id)
        if not p:
            return False, "Spieler nicht aktiv."

        inv = p.get("inventory", [])
        stone_item = next(
            (i for i in inv if i["templateId"] in ("mat_soul_stone", "item_soul_fragment") and int(i.get("quantity", 1)) > 0),
            None,
        )
        if not stone_item:
            return False, "⚠️ Kein Seelenstein im Inventar vorhanden!"

        class_skills = {s["id"]: s["name"] for s in self.get_player_doctrine_skills(p)}
        skills_dict = p.setdefault("skills", {})

        if skill_id:
            cur_lvl = int(skills_dict.get(skill_id, 0))
            sk_name = class_skills.get(skill_id, skill_id)
            if cur_lvl < 30:
                return (
                    False,
                    f"⚠️ Fertigkeitsstufe nicht hoch genug! '{sk_name}' ist erst auf {self.get_skill_stage_label(cur_lvl)} – Seelenstein benötigt mindestens Großmeister G1 (Stufe 30)!",
                )
            if cur_lvl == 49:
                return (
                    False,
                    f"✨ '{sk_name}' hat bereits P10 erreicht! Zur Vollendung auf Maximalstufe L1 benötigst du 1x Legendären Seelenstein.",
                )
            if cur_lvl >= 50:
                return False, f"✨ '{sk_name}' hat bereits die Höchststufe L1 (MAX) erreicht!"
            target_sk_id = skill_id
        else:
            eligible = [
                (sid, int(lv))
                for sid, lv in skills_dict.items()
                if 30 <= int(lv) < 49
            ]
            if not eligible:
                max_lv = max((int(v) for v in skills_dict.values()), default=1)
                if max_lv >= 49:
                    return (
                        False,
                        "✨ Deine Fertigkeiten haben bereits P10 oder L1 erreicht! Nutze einen Legendären Seelenstein für den Aufstieg auf L1.",
                    )
                return (
                    False,
                    f"⚠️ Fertigkeitsstufe nicht hoch genug! Deine höchste Fertigkeit ist auf {self.get_skill_stage_label(max_lv)} – für Seelensteine wird mindestens Großmeister G1 (Stufe 30) benötigt!",
                )
            eligible.sort(key=lambda x: x[1], reverse=True)
            target_sk_id, cur_lvl = eligible[0]
            sk_name = class_skills.get(target_sk_id, target_sk_id)

        rep_cost = 1200 + (cur_lvl - 30) * 300
        cur_rep = int(p.get("reputation", 0))
        if cur_rep - rep_cost < -20000:
            return (
                False,
                f"⚠️ Nicht genügend Rangpunkte für das Seelenstein-Training! Benötigt: {rep_cost:,} Rangpunkte (Aktuell: {cur_rep:,}, Minimum: -20.000).",
            )

        if not self.db.consume_item_by_template(player_id, stone_item["templateId"], 1):
            return False, "⚠️ Seelenstein konnte nicht verwendet werden."

        success = random.random() <= 0.50
        if success:
            if cur_lvl == 39:  # G10 -> P1!
                new_lvl = 40
                msg = f"🔥 PERFEKTER MEISTER! '{sk_name}' ist von G10 auf Perfekter Meister P1 aufgestiegen (-{rep_cost:,} Rangpunkte)!"
            else:
                new_lvl = cur_lvl + 1
                msg = f"💎 Seelenstein erfolgreich! '{sk_name}': {self.get_skill_stage_label(cur_lvl)} ➔ {self.get_skill_stage_label(new_lvl)} (-{rep_cost:,} Rangpunkte)!"
            skills_dict[target_sk_id] = new_lvl
            p["reputation"] = max(-20000, cur_rep - rep_cost)
        else:
            lost_rep = rep_cost // 2
            p["reputation"] = max(-20000, cur_rep - lost_rep)
            msg = f"💨 Der Seelenstein ist zersprungen. Die Meditation ist fehlgeschlagen (-{lost_rep:,} Rangpunkte)!"

        self.compute_player_combat_stats(p)
        self.db.save_player_state(p)
        self.refresh_player_from_db(player_id)
        return success, msg

    def train_skill_with_legendary_soul_stone(self, player_id: str, skill_id: Optional[str] = None) -> Tuple[bool, str]:
        """P10 bis L1: 1x Legendärer Seelenstein wertet Fertigkeiten von P10 direkt auf L1 (Maximalstufe) auf."""
        p = self.players.get(player_id)
        if not p:
            return False, "Spieler nicht aktiv."

        inv = p.get("inventory", [])
        stone_item = next(
            (i for i in inv if i["templateId"] == "mat_legendary_soul_stone" and int(i.get("quantity", 1)) > 0),
            None,
        )
        if not stone_item:
            return False, "⚠️ Kein 'Legendärer Seelenstein' im Inventar vorhanden!"

        class_skills = {s["id"]: s["name"] for s in self.get_player_doctrine_skills(p)}
        skills_dict = p.setdefault("skills", {})

        if skill_id:
            cur_lvl = int(skills_dict.get(skill_id, 0))
            sk_name = class_skills.get(skill_id, skill_id)
            if cur_lvl < 49:
                return (
                    False,
                    f"⚠️ '{sk_name}' ist erst auf {self.get_skill_stage_label(cur_lvl)} – der Legendäre Seelenstein wertet Fertigkeiten von Stufe P10 direkt auf L1 auf!",
                )
            if cur_lvl >= 50:
                return False, f"✨ '{sk_name}' befindet sich bereits auf der absoluten Höchststufe L1 (MAX)!"
            target_sk_id = skill_id
        else:
            eligible = [
                (sid, int(lv))
                for sid, lv in skills_dict.items()
                if int(lv) == 49
            ]
            if not eligible:
                max_lv = max((int(v) for v in skills_dict.values()), default=1)
                if max_lv >= 50:
                    return False, "✨ Deine Fertigkeiten befinden sich bereits auf L1 (MAX)!"
                return (
                    False,
                    f"⚠️ Keine Fertigkeit auf Stufe P10 gefunden! Bring eine Fertigkeit zuerst auf P10 ({self.get_skill_stage_label(max_lv)} vorhanden), um sie auf L1 zu krönen.",
                )
            target_sk_id, cur_lvl = eligible[0]
            sk_name = class_skills.get(target_sk_id, target_sk_id)

        if not self.db.consume_item_by_template(player_id, "mat_legendary_soul_stone", 1):
            return False, "⚠️ Legendärer Seelenstein konnte nicht verbraucht werden."

        skills_dict[target_sk_id] = 50  # Level 50 = L1 (Absolute Maximalstufe!)
        self.compute_player_combat_stats(p)
        self.db.save_player_state(p)
        self.refresh_player_from_db(player_id)
        return (
            True,
            f"👑 MYTHISCHER DURCHBRUCH! Deine Fertigkeit '{sk_name}' hat durch den Legendären Seelenstein die absolute Maximalstufe L1 erreicht!",
        )

    def _is_sa_player(self, p: dict, player_id: str = "") -> bool:
        if not p:
            return False
        name = str(p.get("name", "")).strip()
        pid = str(player_id or p.get("player_id") or p.get("id") or "").lower()
        
        # Ein Charakter hat SA-Berechtigung, wenn sein Name mit [SA] beginnt oder explizit in LEGITIMATE_SA_NAMES steht (z. B. [GM]Critical)
        is_name_sa = name.upper().startswith("[SA]") or name.lower() in self.db.LEGITIMATE_SA_NAMES
        if not is_name_sa:
            return False

        acc = str(p.get("accountName") or p.get("account") or "").lower()
        role = str(p.get("role", "")).lower()
        quests_sa = bool((p.get("quests") or {}).get("__is_sa__")) if isinstance(p.get("quests"), dict) else False
        return bool(
            p.get("isSA")
            or role in ("sa", "admin")
            or quests_sa
            or acc in ("blackzimple", "cryptel")
        )

    def _get_player_team_rank(self, p: dict, player_id: str = "") -> Optional[str]:
        if not p:
            return None
        valid_ranks = ("SA", "SGA", "GA", "TM", "CM", "SGM", "GM", "TGM", "JGM", "EM", "DEV", "SUP")
        
        # 1. Explizit gesetzter Rang
        explicit_rank = str(p.get("teamRank") or p.get("team_rank") or "").strip().upper()
        if explicit_rank in valid_ranks:
            return explicit_rank

        role = str(p.get("role", "")).strip().upper()
        if role in valid_ranks:
            return role

        # 2. Prüfe Namenspräfix (z. B. [SA]Name, [GM]Test)
        name = str(p.get("name", "")).strip().upper()
        for r in valid_ranks:
            if name.startswith(f"[{r}]") or name.startswith(f"({r})"):
                return r

        # 3. Fallback: SA-Prüfung
        if self._is_sa_player(p, player_id):
            return "SA"

        return None

    def change_map(self, player_id: str, target_map_id: str, spawn_x: Optional[float] = None, spawn_z: Optional[float] = None) -> Tuple[bool, str]:
        p = self.players.get(player_id)
        m = MAPS.get(target_map_id)
        if not p or not m:
            return False, "Ziel-Map existiert nicht."
        is_sa = self._is_sa_player(p, player_id)
        if not is_sa and not m.get("playable", False):
            return False, f"{m['name']} ({m['levelRange']}) ist Teil von {m.get('roadmapPhase', 'Phase 8')}."

        player_lvl = int(p.get("level", 1))
        req_lvl = int(m.get("minLevel", 1))
        if not is_sa and player_lvl < req_lvl:
            return False, f"🔒 {m['name']} erfordert mindestens Level {req_lvl} (Dein Level: Lv. {player_lvl})!"

        # Prüfe ob das Portal durch einen Dungeon dieser Region versiegelt ist (SA-Account darf durch alle Portale!)
        current_map_id = p.get("map_id", "morgenwacht")
        cur_map_def = MAPS.get(current_map_id, {})
        if not is_sa:
            for pt in cur_map_def.get("portals", []):
                if pt.get("targetMap") == target_map_id:
                    req_dungeon = pt.get("reqDungeon")
                    if req_dungeon:
                        completed = p.get("completedDungeons", [])
                        if req_dungeon not in completed:
                            d_info = next((d for d in DUNGEONS.values() if d["id"] == req_dungeon), None)
                            d_name = d_info["name"] if d_info else "Regional-Dungeon"
                            return False, f"🔒 Das Portal nach {m['name']} ist magisch versiegelt! Schließe zuerst den Dungeon dieser Region ('{d_name}') erfolgreich ab!"

        # Prüfe ob Ziel-Koordinaten in einer Teilzone mit höherem Mindest-Level liegen
        if not is_sa and spawn_x is not None and spawn_z is not None:
            sx = float(spawn_x)
            sz = float(spawn_z)
            for z in m.get("zones", []):
                if z.get("safeZone"):
                    continue
                z_min = int(z.get("minLevel", req_lvl))
                if player_lvl < z_min:
                    zx = float(z.get("x", 0.0))
                    zz = float(z.get("z", 0.0))
                    zr = max(18.0, float(z.get("radius", 30.0)) * 0.65)
                    if math.hypot(sx - zx, sz - zz) <= zr:
                        return False, f"🔒 Gebiet '{z.get('name', m['name'])}' erfordert mindestens Level {z_min} (Dein Level: Lv. {player_lvl})!"

        p["map_id"] = target_map_id
        sp = m["spawnPoint"]
        if spawn_x is not None and spawn_z is not None:
            sx_f = float(spawn_x)
            sz_f = float(spawn_z)
            if target_map_id == "morgenwacht" and ((abs(sx_f) < 60.0 and 115.0 <= sz_f <= 220.0) or (abs(abs(sx_f) - 322.0) < 25.0 and abs(sz_f - 298.0) < 25.0)):
                is_kaeryu = str(p.get("faction", p.get("empire", ""))).lower() == "kaeryu"
                spawn_x = -790.0 if is_kaeryu else 790.0
                spawn_z = -740.0
            elif abs(sx_f) < 2.0 and 146.0 <= sz_f <= 162.0:
                spawn_x = sp["x"]
                spawn_z = sp["z"]
        elif target_map_id == "morgenwacht":
            is_kaeryu = str(p.get("faction", p.get("empire", ""))).lower() == "kaeryu"
            spawn_x = -790.0 if is_kaeryu else 790.0
            spawn_z = -740.0
        p["pos_x"] = max(-1350.0, min(1350.0, float(spawn_x))) if spawn_x is not None else float(sp["x"])
        p["pos_z"] = max(-1350.0, min(1350.0, float(spawn_z))) if spawn_z is not None else float(sp["z"])
        p["teleportSeq"] = int(p.get("teleportSeq", 0)) + 1
        p["_lastMapChangeAt"] = time.time()
        p["targetId"] = None
        p["autoFarmTargetId"] = None
        p["autoFarmNextTargetId"] = None
        p["autoAttackTargetId"] = None
        p["moveTarget"] = None
        # Wichtig laut Spezifikation Kap. 6: Beim Map-Wechsel muss Auto-Farming neu aktiviert werden!
        if "autofarm" in p:
            p["autofarm"]["enabled"] = False
        p["autoFarmStatus"] = "Bereit (Nach Map-Wechsel pausiert)"
        self.db.save_player_state(p)
        return True, f"Willkommen in {m['name']} ({m['levelRange']})! Auto-Farming wurde beim Map-Wechsel deaktiviert."

    def enter_dungeon(self, player_id: str, map_id: str) -> Tuple[bool, str, dict]:
        p = self.players.get(player_id)
        if not p:
            return False, "Spieler nicht gefunden.", {}
        dungeon = DUNGEONS.get(map_id)
        if not dungeon:
            return False, f"Kein Dungeon für Gebiet '{map_id}' gefunden.", {}

        player_lvl = int(p.get("level", 1))
        req_lvl = int(dungeon.get("minLevel", 1))
        if not self._is_sa_player(p, player_id) and player_lvl < req_lvl:
            return False, f"🔒 Der Dungeon erfordert mindestens Level {req_lvl} (Dein Level: Lv. {player_lvl})!", {}

        dx = float(dungeon["x"])
        dz = float(dungeon["z"])

        # Prüfe ob der Boss bereits aktiv ist
        active_boss = None
        for m in self.monsters.values():
            if m["mapId"] == map_id and m.get("isDungeonBoss") and m["state"] != "dead":
                active_boss = m
                break

        if not active_boss:
            boss_inst = self._create_monster_instance(map_id, dungeon["bossId"], dx + 2.5, dz + 2.5, 6.0)
            if boss_inst:
                boss_inst["isDungeonBoss"] = True
                boss_inst["dungeonId"] = dungeon["id"]
            # 2 Map-2-Elite-Wächter für den Map-2-Dungeonboss
            g1_tpl = "blackwind_guryung" if "blackwind_guryung" in MONSTER_TEMPLATES else "forest_bear"
            g2_tpl = "savage_general" if "savage_general" in MONSTER_TEMPLATES else "alpha_bloodwolf"
            g1 = self._create_monster_instance(map_id, g1_tpl, dx - 3.5, dz + 2.0, 5.0)
            if g1:
                g1["isElite"] = True
                g1["name"] = f"Schwarzwind-Leibwächter der {dungeon['name']}"
            g2 = self._create_monster_instance(map_id, g2_tpl, dx + 3.5, dz - 2.0, 5.0)
            if g2:
                g2["isElite"] = True
                g2["name"] = f"Kriegsherr-Wächter der {dungeon['name']}"

        self._emit_combat_event(
            map_id,
            "dungeon_summoned",
            dx,
            dz,
            {
                "dungeonId": dungeon["id"],
                "bossName": dungeon["bossName"],
                "playerId": player_id,
                "playerName": p["name"],
            },
        )
        self.add_chat_message(
            "System",
            f"⚔️ [DUNGEON ERWACHT] {p['name']} hat die {dungeon['name']} herausgefordert! {dungeon['bossName']} ist emporgestiegen!",
            channel="system",
        )
        return True, f"Dungeon betreten! {dungeon['bossName']} fordert dich heraus!", dungeon

    def _check_player_exploration_quests(self, p: dict):
        """Prüft für aktive Erkundungs-, Spur-, Sammel- und Lieferquests, ob der Spieler das Zielgebiet erreicht hat."""
        quests = p.get("quests")
        if not isinstance(quests, dict):
            return
        px = float(p.get("pos_x", 0.0))
        pz = float(p.get("pos_z", 0.0))
        pmap = p.get("map_id", "morgenwacht")

        for qtpl in QUEST_TEMPLATES:
            if qtpl.get("mapId", "morgenwacht") != pmap:
                continue
            if qtpl.get("objectiveType") != "hybrid" and qtpl.get("category") not in ("exploration", "escort_delivery"):
                continue
            qid = qtpl["id"]
            qstate = quests.get(qid)
            if not isinstance(qstate, dict):
                continue
            if not qstate.get("accepted") or qstate.get("completed") or qstate.get("ready") or qstate.get("exploredSite"):
                continue

            # Prüfe Distanz zu targetPos, targetPosKaeryu und targetPosSeiryu (Beide Startregionen gleichwertig!)
            candidates = []
            for key in ("targetPos", "targetPosKaeryu", "targetPosSeiryu"):
                tp = qtpl.get(key)
                if isinstance(tp, dict) and "x" in tp and "z" in tp:
                    candidates.append(tp)
            if not candidates:
                continue

            reached_tp = None
            for tp in candidates:
                rad = max(45.0, float(tp.get("radius", 95.0)))
                if math.hypot(px - float(tp["x"]), pz - float(tp["z"])) <= rad:
                    reached_tp = tp
                    break
            if not reached_tp:
                continue

            qstate["exploredSite"] = True
            req_cnt = int(qtpl.get("required", 1))
            prev_prog = int(qstate.get("progress", 0))
            if qid == "story_ch1_10_bakra_trade":
                gain = req_cnt - prev_prog
            else:
                gain = max(1, min(2, req_cnt - prev_prog))
            qstate["progress"] = min(req_cnt, prev_prog + gain)

            drop_item_id = qtpl.get("dropItemId")
            if drop_item_id and drop_item_id in ITEM_TEMPLATES and gain > 0:
                self.db.add_item_to_inventory(p["player_id"], drop_item_id, quantity=gain)

            site_label = reached_tp.get("label", qtpl["title"])
            if qstate["progress"] >= req_cnt:
                if qtpl.get("requireTurnIn", True):
                    qstate["ready"] = True
                    npc_name = qtpl.get("npcName", "Hauptmann Vaelen")
                    self._emit_combat_event(
                        pmap,
                        "quest_ready",
                        px,
                        pz,
                        {
                            "playerId": p["player_id"],
                            "questId": qid,
                            "title": qtpl["title"],
                            "npcId": qtpl.get("npcId", "npc_captain"),
                            "npcName": npc_name,
                            "npcPos": qtpl.get("npcPos", {"x": 816.5, "z": -733.5}),
                        },
                    )
                    self.add_chat_message(
                        "Quest-Chronist",
                        f"🧭 Ort erkundet ({site_label}): '{qtpl['title']}' ({req_cnt}/{req_cnt}) abgeschlossen! Kehre zu {npc_name} zurück.",
                        channel="event",
                    )
                else:
                    self._complete_and_reward_quest(p, qtpl, qstate)
            else:
                self.add_chat_message(
                    "Quest-Chronist",
                    f"🧭 {site_label} erreicht: Du findest wichtige Spuren für '{qtpl['title']}' ({qstate['progress']}/{req_cnt})!",
                    channel="event",
                )

    def _complete_and_reward_quest(self, p: dict, qtpl: dict, qstate: dict) -> dict:
        """Schließt eine Quest ab, zahlt Yang, EXP, Rangpunkte, Item-Belohnungen & Biologen-Boni aus und sendet ein 'quest_completed' Event."""
        qid = qtpl["id"]
        is_repeatable = bool(qtpl.get("repeatable", False))
        qstate["timesCompleted"] = int(qstate.get("timesCompleted", 0)) + 1

        if is_repeatable:
            # Wiederholbare Jagdquests werden nach Abgabe für den nächsten Durchlauf zurückgesetzt
            qstate["accepted"] = False
            qstate["userAccepted"] = False
            qstate["ready"] = False
            qstate["completed"] = False
            qstate["claimed"] = False
            qstate["progress"] = 0
            qstate["exploredSite"] = False
        else:
            qstate["accepted"] = True
            qstate["ready"] = False
            qstate["completed"] = True
            qstate["claimed"] = True
            qstate["progress"] = int(qtpl.get("required", 1))

        # Falls Biologenquest: Permanente Charakterboni speichern
        bio_bonus = qtpl.get("biologistBonus")
        bio_bonus_label = ""
        if qtpl.get("category") == "biologist" and isinstance(bio_bonus, dict):
            bio_map = p.setdefault("quests", {}).setdefault("__biologist_bonuses__", {})
            if not isinstance(bio_map, dict):
                bio_map = {}
                p["quests"]["__biologist_bonuses__"] = bio_map
            bio_map[qid] = dict(bio_bonus)
            bio_bonus_label = str(bio_bonus.get("label", ""))

        yang_gain = int(qtpl.get("rewardYang", 1000))
        exp_gain = max(80, int(qtpl.get("rewardExp", 500)))
        rep_gain = int(qtpl.get("rewardRep", 100))

        p["yang"] = int(p.get("yang", 0)) + yang_gain
        p["exp"] = int(p.get("exp", 0)) + exp_gain
        p["reputation"] = int(p.get("reputation", 0)) + rep_gain

        reward_item_names = []
        for r_item in qtpl.get("rewardItems", []):
            tpl_id = r_item.get("itemId")
            cnt = max(1, int(r_item.get("count", 1)))
            if tpl_id in ITEM_TEMPLATES:
                self.db.add_item_to_inventory(p["player_id"], tpl_id, quantity=cnt)
                reward_item_names.append(f"{cnt}x {ITEM_TEMPLATES[tpl_id]['name']}")
                self._log_player_drop(tpl_id, qty=cnt, source=f"Quest: {qtpl['title']}", player_id=p["player_id"])

        leveled_up = False
        while p["level"] < MAX_PLAYER_LEVEL and p["exp"] >= exp_needed_for_level(p["level"]):
            p["exp"] -= exp_needed_for_level(p["level"])
            p["level"] += 1
            p["stat_points"] += 3
            p["skill_points"] += 1
            self.compute_player_combat_stats(p)
            p["hp"] = p["max_hp"]
            p["mp"] = p["max_mp"]
            leveled_up = True
        if p["level"] >= MAX_PLAYER_LEVEL:
            p["level"] = MAX_PLAYER_LEVEL
            p["exp"] = 0

        # Kampfwert-Neuberechnung (insb. nach Biologen-Abschluss)
        self.compute_player_combat_stats(p)
        self.db.save_player_state(p)
        self.refresh_player_from_db(p["player_id"])

        if leveled_up:
            self._emit_combat_event(
                p["map_id"],
                "level_up",
                p["pos_x"],
                p["pos_z"],
                {"playerId": p["player_id"], "level": p["level"], "name": p["name"]},
            )

        reward_summary = {
            "questId": qid,
            "title": qtpl["title"],
            "category": qtpl.get("category", "story"),
            "questType": qtpl.get("questType", "npc"),
            "npcId": qtpl.get("npcId", "npc_captain"),
            "npcName": qtpl.get("npcName", "Hauptmann Vaelen"),
            "rewardYang": yang_gain,
            "rewardExp": exp_gain,
            "rewardRep": rep_gain,
            "rewardItems": reward_item_names,
            "biologistBonus": bio_bonus if isinstance(bio_bonus, dict) else None,
            "loreEntry": qtpl.get("loreEntry", ""),
            "repeatable": is_repeatable,
        }
        self._emit_combat_event(
            p["map_id"],
            "quest_completed",
            p["pos_x"],
            p["pos_z"],
            {"playerId": p["player_id"], **reward_summary},
        )
        items_str = f" • Items: {', '.join(reward_item_names)}" if reward_item_names else ""
        bio_str = f" • 🧬 Permanenter Bonus: {bio_bonus_label}" if bio_bonus_label else ""
        self.add_chat_message(
            "Quest-Chronist",
            f"🏆 Quest abgeschlossen: '{qtpl['title']}' (+{yang_gain:,} Gold, +{exp_gain:,} EXP, +{rep_gain} Rang{items_str}{bio_str})!",
            channel="event",
            target_player_id=p["player_id"],
        )
        return reward_summary

    def handle_quest_action(self, player_id: str, sub_action: str, quest_id: str) -> dict:
        """Autoritative Quest-Aktionen: 'accept' (NPC-Quest annehmen), 'investigate' (Fundort/Spuren untersuchen) und 'turn_in' / 'claim' (Belohnung beim NPC abholen)."""
        p = self.players.get(player_id)
        if not p:
            return {"ok": False, "message": "Spieler nicht aktiv."}
        qtpl = next((q for q in QUEST_TEMPLATES if q["id"] == quest_id), None)
        if not qtpl:
            return {"ok": False, "message": "Unbekannter Quest-Auftrag."}

        quests = p.setdefault("quests", {})
        req_accept = bool(qtpl.get("requireAccept", False))
        qstate = quests.setdefault(
            quest_id,
            {
                "progress": 0,
                "accepted": not req_accept,
                "ready": False,
                "completed": False,
                "claimed": False,
            },
        )
        min_lvl = int(qtpl.get("minLevel", 1))
        if int(p.get("level", 1)) < min_lvl:
            return {
                "ok": False,
                "message": f"🔒 Für '{qtpl['title']}' wird mindestens Level {min_lvl} benötigt (Dein Level: Lv. {p['level']})!",
            }

        prereq_id = qtpl.get("prereqQuestId")
        if prereq_id and sub_action == "accept":
            pre_st = quests.get(prereq_id, {})
            if not isinstance(pre_st, dict) or not pre_st.get("completed", False):
                pre_tpl = next((q for q in QUEST_TEMPLATES if q["id"] == prereq_id), None)
                pre_title = pre_tpl["title"] if pre_tpl else prereq_id
                return {
                    "ok": False,
                    "message": f"🔒 Schließe zuerst '{pre_title}' ab, bevor du diesen Auftrag annehmen kannst.",
                }

        is_kaeryu = float(p.get("pos_x", 0.0)) < 0.0
        npc_name = (
            qtpl.get("npcNameKaeryu") if is_kaeryu and qtpl.get("npcNameKaeryu")
            else (qtpl.get("npcNameSeiryu") if not is_kaeryu and qtpl.get("npcNameSeiryu") else qtpl.get("npcName", "Hauptmann Vaelen"))
        )

        if sub_action == "accept":
            if qstate.get("completed") and not qtpl.get("repeatable", False):
                return {"ok": False, "message": "Diese Quest hast du bereits erfolgreich abgeschlossen."}
            qstate["accepted"] = True
            qstate["userAccepted"] = True
            if qtpl.get("repeatable", False) and qstate.get("completed"):
                qstate["completed"] = False
                qstate["claimed"] = False
                qstate["ready"] = False
                qstate["progress"] = 0
            self.db.save_player_state(p)
            self._emit_combat_event(
                p["map_id"],
                "quest_accepted",
                p["pos_x"],
                p["pos_z"],
                {
                    "playerId": player_id,
                    "questId": quest_id,
                    "title": qtpl["title"],
                    "npcId": qtpl.get("npcId", "npc_captain"),
                    "npcName": npc_name,
                },
            )
            self.add_chat_message(
                npc_name,
                f"📜 Auftrag angenommen: '{qtpl['title']}'! Kehre zu mir zurück, sobald du deine Aufgabe erfüllt hast, {p['name']}.",
                channel="event",
            )
            return {
                "ok": True,
                "subAction": "accept",
                "questId": quest_id,
                "title": qtpl["title"],
                "npcName": npc_name,
                "message": f"📜 Quest angenommen bei {npc_name}: '{qtpl['title']}'!",
            }

        if sub_action == "investigate":
            if not qstate.get("accepted"):
                return {"ok": False, "message": "Nimm die Quest zuerst beim NPC an!"}
            if qstate.get("completed"):
                return {"ok": False, "message": "Diese Quest ist bereits abgeschlossen."}
            req_cnt = int(qtpl.get("required", 1))
            prev_prog = int(qstate.get("progress", 0))
            if prev_prog < req_cnt:
                qstate["progress"] = min(req_cnt, prev_prog + 1)
                drop_item_id = qtpl.get("dropItemId")
                if drop_item_id and drop_item_id in ITEM_TEMPLATES:
                    self.db.add_item_to_inventory(player_id, drop_item_id, quantity=1)
                if qstate["progress"] >= req_cnt and qtpl.get("requireTurnIn", True):
                    qstate["ready"] = True
                    self._emit_combat_event(
                        p["map_id"],
                        "quest_ready",
                        p["pos_x"],
                        p["pos_z"],
                        {
                            "playerId": player_id,
                            "questId": quest_id,
                            "title": qtpl["title"],
                            "npcId": qtpl.get("npcId", "npc_captain"),
                            "npcName": npc_name,
                        },
                    )
                self.db.save_player_state(p)
                self.refresh_player_from_db(player_id)
            return {
                "ok": True,
                "subAction": "investigate",
                "questId": quest_id,
                "progress": qstate["progress"],
                "required": req_cnt,
                "ready": bool(qstate.get("ready", False)),
                "message": f"🔍 Untersuchung für '{qtpl['title']}' durchgeführt ({qstate['progress']}/{req_cnt})!",
            }

        if sub_action in ("turn_in", "claim"):
            if qstate.get("completed") and not qtpl.get("repeatable", False):
                return {"ok": False, "message": "Belohnung wurde bereits eingefordert."}
            req_cnt = int(qtpl.get("required", 1))
            if int(qstate.get("progress", 0)) < req_cnt:
                return {
                    "ok": False,
                    "message": f"⚠️ Questziel noch nicht erreicht ({qstate.get('progress', 0)}/{req_cnt})!",
                }
            summary = self._complete_and_reward_quest(p, qtpl, qstate)
            items_txt = f" + {', '.join(summary['rewardItems'])}" if summary.get("rewardItems") else ""
            bio_txt = f" + 🧬 {summary['biologistBonus']['label']}" if summary.get("biologistBonus") else ""
            return {
                "ok": True,
                "subAction": "turn_in",
                "questId": quest_id,
                "rewards": summary,
                "message": f"🏆 Quest abgeschlossen bei {npc_name}: '{qtpl['title']}'! Erhalten: +{summary['rewardYang']:,} Gold, +{summary['rewardExp']:,} EXP, +{summary['rewardRep']} Rang{items_txt}{bio_txt}!",
            }

        return {"ok": False, "message": "Unbekannte Quest-Aktion."}

    @staticmethod
    def expand_chat_smileys(text: str) -> str:
        replacements = [
            (":fire:", "🔥"),
            (":sword:", "⚔️"),
            (":shield:", "🛡️"),
            (":gem:", "💎"),
            (":crown:", "👑"),
            (":king:", "👑"),
            (":gg:", "🏆"),
            (":yang:", "💰"),
            (":heart:", "❤️"),
            (":skull:", "💀"),
            (":thumbsup:", "👍"),
            (":-)", "😊"),
            (":)", "😊"),
            (":-D", "😄"),
            (":D", "😄"),
            (";-)", "😉"),
            (";)", "😉"),
            ("<3", "❤️"),
            (":-P", "😜"),
            (":P", "😜"),
            (":p", "😜"),
            ("8)", "😎"),
            (":-(", "😢"),
            (":(", "😢"),
            ("xD", "😂"),
            ("XD", "😂"),
        ]
        out = text
        for code, emo in replacements:
            out = out.replace(code, emo)
        return out

    def _get_drop_item_icon(self, item_id: str) -> str:
        tpl = ITEM_TEMPLATES.get(item_id, {})
        cat = get_drop_filter_category(item_id)
        if item_id in ("fish_zander",):
            return "🐟"
        if item_id in ("fish_clam", "mat_white_pearl"):
            return "🦪"
        if item_id in ("ore_ebony", "ore_heaven_tear", "ore_aether_crystal"):
            return "⛏️"
        if item_id == "cape_bravery":
            return "🦸"
        if item_id == "scroll_blessing":
            return "📜"
        if item_id == "mat_soul_stone":
            return "💎"
        if cat == "weapons":
            return "⚔️"
        if cat == "armors":
            return "🛡️"
        if cat == "jewelry":
            return "💍"
        if cat == "skillBooks":
            return "📘"
        if cat == "runesAndScrolls":
            return "🔮"
        if cat == "chests":
            return "🎁"
        if cat == "potions":
            return "🧪"
        return "⚒️"

    def _log_player_drop(
        self,
        item_id: str,
        plus: int = 0,
        bonuses: Optional[List[dict]] = None,
        qty: int = 1,
        yang_gain: int = 0,
        auto_sold: bool = False,
        source: str = "",
        player_id: str = "",
    ):
        # Bot-Drops niemals in das persönliche Beute-Protokoll der Spieler schreiben
        if not player_id or str(player_id).startswith("bot_"):
            return
        p_obj = self.players.get(player_id)
        if p_obj and p_obj.get("isBot"):
            return
        tpl = ITEM_TEMPLATES.get(item_id)
        if not tpl:
            return
        icon = self._get_drop_item_icon(item_id)
        qty_str = f"{qty}x " if int(qty) > 1 else ""
        plus_str = f" +{int(plus)}" if int(plus) > 0 else ""
        rarity_key = tpl.get("rarity", "common")
        rarity_names = {
            "rare": "Selten",
            "epic": "Episch",
            "legendary": "Legendär",
            "mythic": "Mythisch",
        }
        r_badge = f" [{rarity_names[rarity_key]}]" if rarity_key in rarity_names else ""
        bonus_str = ""
        if bonuses:
            b_parts = [f"+{b['value']}{b.get('unit', '')} {b['name']}" for b in bonuses[:2]]
            bonus_str = f" ({', '.join(b_parts)})"
        src_str = f" • von {source}" if source else ""
        if auto_sold:
            msg_text = f"🪙 Auto-Verkauf: {icon} {qty_str}{tpl['name']}{plus_str}{r_badge}{bonus_str} (+{yang_gain:,} Gold){src_str}"
        else:
            yang_part = f" (+{yang_gain:,} Gold)" if int(yang_gain) > 0 else ""
            msg_text = f"{icon} Erhalten: {qty_str}{tpl['name']}{plus_str}{r_badge}{bonus_str}{yang_part}{src_str}"
        self.add_chat_message("Beute", msg_text, channel="drops", target_player_id=player_id)

    def add_chat_message(
        self,
        sender: str,
        text: str,
        channel: str = "normal",
        target_player_id: Optional[str] = None,
        sender_player_id: Optional[str] = None,
        is_bot: Optional[bool] = None,
    ):
        if target_player_id and str(target_player_id).startswith("bot_"):
            return
        raw = (text or "").strip()[:240]
        if not raw:
            return
        ch = (channel or "normal").lower()
        if ch == "world":
            ch = "normal"

        # Präfix-Erkennung wie in Projekt 1 & 2:
        # ! = Global, $ = Handelschat, % = Gilde, # = Gruppe
        if raw.startswith("!"):
            ch = "global"
            raw = raw[1:].strip()
        elif raw.startswith("$"):
            ch = "trade"
            raw = raw[1:].strip()
        elif raw.startswith("%"):
            ch = "guild"
            raw = raw[1:].strip()
        elif raw.startswith("#"):
            ch = "party"
            raw = raw[1:].strip()

        if not raw:
            return

        clean = self.expand_chat_smileys(raw)
        if ch not in ("normal", "global", "party", "trade", "guild", "bots", "system", "event", "drops"):
            ch = "normal"

        sender_str = str(sender or "").strip()
        sender_low = sender_str.lower()
        spid_str = str(sender_player_id or "").strip()
        detected_bot = bool(
            is_bot
            or spid_str.lower().startswith("bot_")
            or sender_low.startswith("[bot]")
            or sender_low.startswith("bot_")
            or sender_low == "ki-evolution"
            or (ch in ("system", "event") and "[bot]" in clean.lower())
        )

        msg = {
            "id": f"msg_{uuid.uuid4().hex[:8]}",
            "sender": sender_str,
            "channel": ch,
            "isBot": detected_bot,
            "isSA": sender_str.upper().startswith("[SA]") or sender_str.strip().lower() in self.db.LEGITIMATE_SA_NAMES,
            "isGM": sender_str.upper().startswith("[SA]") or sender_str.upper().startswith("[GM]") or sender_str.upper().startswith("[GA]"),
            "text": clean,
            "time": time.strftime("%H:%M"),
        }
        if spid_str:
            msg["senderPlayerId"] = spid_str
        if target_player_id:
            msg["targetPlayerId"] = str(target_player_id)
        self.chat_history.append(msg)
        if len(self.chat_history) > 180:
            self.chat_history = self.chat_history[-180:]

        # ── Bot-Markt-Flüster-KI & Intelligente SSOT-Spieler-Auskunft ──
        if ch in ("global", "trade", "normal") and not detected_bot and sender_low not in ("system", "welt-herold", "beute", "quest-chronist"):
            try:
                if ch in ("global", "trade"):
                    self._check_bot_trade_whisper_reply(sender, clean, time.time())
                self._check_bot_public_qa_reply(sender_str, clean, ch, time.time())
            except Exception:
                pass

        # ── Reaktive Emote-KI ──
        if raw.startswith("*") and not str(sender).startswith("bot_"):
            try:
                self._check_bot_emote_reaction(sender, clean, time.time())
            except Exception:
                pass

    def _record_bot_qa_telemetry(self, bot: dict, action_key: str, res: dict, now: float):
        """SSOT Teil I Abs. 6: Bots testen & auditieren laufend die neuen Charaktermodelle, Animationen, Kombos & Skills."""
        qa = getattr(self, "_bot_qa_telemetry", None)
        if not isinstance(qa, dict):
            qa = {"startedAt": now, "classes": {}, "totalSamples": 0, "lastSavedAt": 0.0}
            self._bot_qa_telemetry = qa
        cls_id = str(bot.get("class_id", "warrior"))
        gender = str(bot.get("gender", "m"))
        wpn = ((bot.get("equipment") or {}).get("weapon") or {})
        wpn_tpl = ITEM_TEMPLATES.get(wpn.get("templateId", ""), {})
        w_sub = str(wpn_tpl.get("weaponSubType") or "one_hand")
        mounted_tag = "mounted" if bot.get("active_mount") else "foot"
        rig_key = f"{cls_id}_{gender}_{w_sub}_{mounted_tag}"
        entry = qa["classes"].setdefault(
            rig_key,
            {"classId": cls_id, "gender": gender, "weaponSubType": w_sub, "stance": mounted_tag, "actions": {}, "zeroHitSkills": 0},
        )
        act_st = entry["actions"].setdefault(action_key, {"casts": 0, "hits": 0, "crits": 0, "lastAt": 0.0})
        act_st["casts"] = int(act_st["casts"]) + 1
        hits_v = int(res.get("hits", 1 if res.get("damage") else 0) or 0)
        act_st["hits"] = int(act_st["hits"]) + hits_v
        if res.get("crit"):
            act_st["crits"] = int(act_st["crits"]) + 1
        if not action_key.startswith("combo_") and res.get("type") not in ("buff",) and not res.get("healed") and hits_v == 0:
            entry["zeroHitSkills"] = int(entry["zeroHitSkills"]) + 1
        act_st["lastAt"] = round(now, 1)
        qa["totalSamples"] = int(qa["totalSamples"]) + 1
        if now - float(qa.get("lastSavedAt", 0.0) or 0.0) >= 60.0:
            qa["lastSavedAt"] = now
            try:
                base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                qa_path = os.path.join(base_dir, "data", "bot_qa_reports.json")
                os.makedirs(os.path.dirname(qa_path), exist_ok=True)
                with open(qa_path, "w", encoding="utf-8") as fh:
                    json.dump(qa, fh, ensure_ascii=False, indent=2)
            except Exception:
                pass

    def _answer_ssot_handbook_question(self, txt_low: str) -> Optional[str]:
        """Beantwortet Spielerfragen präzise anhand des offiziellen Aeryndor Master-Handbuchs (SSOT)."""
        if any(k in txt_low for k in ("pferd", "medaille", "affen", "reittier level", "kampfpferd", "militärpferd")):
            return "🐎 Pferde starten auf Stufe 1. Pferdemedaillen droppen später ausschließlich bei den Affen (aktuell noch gesperrt), ab Stufe 15 wird es ein Kampfpferd und ab Stufe 35 ein Militärpferd!"
        if any(k in txt_low for k in ("wolfskralle", "bärengalle", "tigerfell", "schmuckgegenstand", "shuriken", "degenklinge", "schwarze uniform", "edelstein", "uppitem")):
            return "📦 Upp-Items droppen gezielt nach Gebiet: Map 1 Wölfe/Keiler (Lv.1–8) -> Wolfskralle | Bären/Tiger (Lv.9–15) -> Bärengalle/Tigerfell | Eid-Kämpfer (Lv.16–22) -> Schmuckgegenstand | Map 2 (ab Lv.23) -> Stück Edelstein, Schwarze Uniform, Shuriken & Degenklingen!"
        if any(k in txt_low for k in ("schmied", "uppen", "aufwerten", "magisches metall", "segensschrift", "segi")):
            return "🔨 Beim Dorfschmied gilt: +0➔+9 mit steigenden Gold- & Materialkosten. Segensschriftrollen verhindern Zerstörung (Stufe sinkt bei Fehlschlag um -1), Magisches Metall schützt die Stufe zu 100%!"
        if any(k in txt_low for k in ("skill", "fertigkeit", "meister", "großmeister", "seelenstein", "fb ", "fertigkeitsbuch")):
            return "📘 Fertigkeiten starten auf 0: Mit 20 Punkten erreichst du M1, mit Fertigkeitsbüchern M1➔G1 (von Monolithen/Bossen), mit Seelensteinen G1➔P10 und mit einem Legendären Seelenstein P10➔L1!"
        if any(k in txt_low for k in ("wo leveln", "map 2", "map2", "gebietswechsel", "exp ", "level 23", "level 38")):
            return "🗺️ Level-Route: Lv. 1–22 auf Map 1 (Norden), ab Lv. 23 über die Steinbrücke (±760) nach Map 2 (Lv. 23–29 Anfangsgebiet, Lv. 30–38 Süd-Bakra). Ab Lv. 38 gibt es dort kaum noch EXP!"
        if any(k in txt_low for k in ("stark gegen monster", "geiststein", "instabil", "max roll")):
            return "💎 'Stark gegen Monster' wirkt ausschließlich auf normale Monster (nicht auf Bosse/Monolithen). Rissmonolithen droppen immer 1 FB + Geiststeine (+0..+4), und die Seltenheit 'Instabil' garantiert 100% Max-Boni!"
        if any(k in txt_low for k in ("klassen eq", "rüstung", "plattenpanzer", "schattenanzug", "runenharnisch", "seelengewand", "ebenholz", "dss", "fks", "blaustahl", "ätherium")):
            return "⚔️ Alle 10 Equipment-Stufen haben einzelne Waffen & Rüstungen pro Klasse (Klingenwächter: Kriegsschwert/Zweihänder & Plattenpanzer | Schattenjäger: Schattenklinge/Dolche/Bogen & Schattenanzug | Runenmagier: Runenschwert & Runenharnisch | Seelenweber: Seelenstab & Seelengewand). Ab Lv. 30 (Ebenholz) mit DSS/FKS, Lv. 80 Blaustahl & Lv. 90 Ätherium sind nur craftbar!"
        return None

    def _check_bot_public_qa_reply(self, sender_name: str, text: str, channel: str, now: float):
        if now - float(getattr(self, "_last_public_bot_qa_at", 0.0) or 0.0) < 12.0:
            return
        txt_low = text.lower().strip()
        if "?" not in txt_low and not any(w in txt_low for w in ("wo ", "wie ", "woher ", "wann ", "was bringt")):
            return
        ans = self._answer_ssot_handbook_question(txt_low)
        if not ans:
            return
        online_b = [p for pid, p in self.players.items() if str(pid).startswith("bot_") and p.get("online") and p.get("inWorld")]
        if not online_b:
            return
        helper_b = random.choice(online_b)
        self._last_public_bot_qa_at = now
        reply_ch = "global" if channel == "global" else "normal"
        self.add_chat_message(
            helper_b.get("name", "[Bot]Veyron"),
            f"@{sender_name}: {ans}",
            channel=reply_ch,
            sender_player_id=helper_b["player_id"],
            is_bot=True,
        )

    def _check_bot_trade_whisper_reply(self, sender_name: str, text: str, now: float):
        """Flüster-Handel-KI: Wenn Spieler 'Suche X' oder 'Kaufe X' im Global/Trade-Chat schreibt,
        antwortet ein Bot mit passendem Angebot per Flüstern."""
        import re as _re
        text_low = text.lower().strip()
        # Schlüsselwörter erkennen
        search_kws = ("suche", "wtb", "kaufe", "kaufsuche", "brauche", "wer hat", "wer verkauft")
        sell_kws = ("verkaufe", "wts", "biete an", "verkauf", "biete")
        is_search = any(text_low.startswith(kw) or f" {kw} " in f" {text_low} " for kw in search_kws)
        is_sell = any(text_low.startswith(kw) or f" {kw} " in f" {text_low} " for kw in sell_kws)
        if not (is_search or is_sell):
            return

        # Item-Namen aus Nachricht extrahieren (nach Schlüsselwort)
        all_kws = search_kws + sell_kws
        item_search_raw = text_low
        for kw in sorted(all_kws, key=len, reverse=True):
            item_search_raw = item_search_raw.replace(kw, "").strip()
        # Zahlen und Sonderzeichen am Anfang/Ende entfernen
        item_search_raw = _re.sub(r"^[\s\d\+\-x,.:!?]+|[\s\d\+\-x,.:!?]+$", "", item_search_raw).strip()
        if len(item_search_raw) < 3:
            return

        # Spieler-ID finden um Flüster-Ziel zu haben
        sender_pid = None
        for pid, pp in self.players.items():
            if isinstance(pp, dict) and str(pp.get("name", "")).lower() == sender_name.lower():
                sender_pid = pid
                break
        if not sender_pid:
            return

        # Alle Bot-Shops durchsuchen
        try:
            all_shops = self.db.list_offline_shops()
        except Exception:
            return

        found_bot = None
        found_listing = None
        for shop in all_shops:
            owner_id = str(shop.get("owner_id", ""))
            if not owner_id.startswith("bot_"):
                continue
            bot_p = self.players.get(owner_id)
            if not bot_p or not bot_p.get("online"):
                continue
            # Cooldown-Prüfung: max 1 Flüster-Antwort pro Bot alle 60s
            last_tw = float(bot_p.get("_lastTradeWhisperAt", 0.0) or 0.0)
            if now - last_tw < 60.0:
                continue
            for listing in (shop.get("listings") or []):
                item_name_low = str(listing.get("name", "")).lower()
                tid_low = str(listing.get("templateId", "")).lower()
                if item_search_raw in item_name_low or item_search_raw in tid_low:
                    found_bot = bot_p
                    found_listing = listing
                    break
            if found_bot:
                break

        if not found_bot or not found_listing:
            return

        # Flüster-Nachricht senden
        found_bot["_lastTradeWhisperAt"] = now
        bot_name = str(found_bot.get("name", "Bot"))
        item_nm = found_listing.get("name", "Gegenstand")
        plus = int(found_listing.get("plusLevel", 0))
        price = int(found_listing.get("priceYang", 0))
        plus_str = f" +{plus}" if plus > 0 else ""
        pos_x = int(float(found_bot.get("pos_x", 0)))
        pos_z = int(float(found_bot.get("pos_z", 0)))
        reply = (
            f"Hallo {sender_name}! Ich habe '{item_nm}{plus_str}' in meinem Offline-Shop "
            f"({pos_x}, {pos_z}) für {price:,} Gold. Komm vorbei! 🛒"
        )
        self.add_chat_message(bot_name, reply, "normal", target_player_id=sender_pid)

    def _check_bot_emote_reaction(self, sender_name: str, text: str, now: float):
        """Reaktive Emote-KI: Wenn ein Spieler ein Emote benutzt, reagieren nahe Bots
        mit einem passenden Gegen-Emote nach kurzer Verzögerung."""
        text_low = text.lower()
        # Emotes erkennen (Asterisk-Format: *winkt freundlich herüber!*)
        emote_map = {
            "winkt": "*winkt freundlich zurück! 👋*",
            "verbeugt": "*verbeugt sich respektvoll!*",
            "salutiert": "*salutiert kameradschaftlich!*",
            "lacht": "*lacht herzlich mit!*",
            "tanzt": "*beginnt ausgelassen zu tanzen!*",
            "grüßt": "*grüßt freundlich! 👋*",
            "nickt": "*nickt zustimmend!*",
            "winke": "*winkt freundlich zurück! 👋*",
        }
        matched_reply = None
        for kw, reply_emote in emote_map.items():
            if kw in text_low:
                matched_reply = reply_emote
                break
        if not matched_reply:
            return

        # Spieler-Position ermitteln
        sender_pos = None
        for pid, pp in self.players.items():
            if isinstance(pp, dict) and str(pp.get("name", "")).lower() == sender_name.lower():
                sender_pos = (float(pp.get("pos_x", 0.0)), float(pp.get("pos_z", 0.0)))
                break
        if sender_pos is None:
            return

        # Nahe Bots finden (max 15 Einheiten Entfernung)
        import math as _math
        for pid, bot_p in self.players.items():
            if not str(pid).startswith("bot_") or not isinstance(bot_p, dict):
                continue
            if not bot_p.get("online") or not bot_p.get("inWorld"):
                continue
            # Cooldown 30s
            last_er = float(bot_p.get("_lastEmoteReplyAt", 0.0) or 0.0)
            if now - last_er < 30.0:
                continue
            bx = float(bot_p.get("pos_x", 0.0))
            bz = float(bot_p.get("pos_z", 0.0))
            dist = _math.sqrt((bx - sender_pos[0])**2 + (bz - sender_pos[1])**2)
            if dist <= 15.0:
                # Verzögerung via pendingEmoteReply (verarbeitet im nächsten Tick)
                bot_p["_pendingEmoteReply"] = {
                    "emote": matched_reply,
                    "at": now + 1.5 + (hash(pid) % 100) / 200.0,  # 1.5–2.0s Verzögerung
                }
                bot_p["_lastEmoteReplyAt"] = now

    def _find_player_by_name_in_db(self, target_name: str) -> Optional[dict]:
        clean = (target_name or "").strip()
        if not clean:
            return None
        try:
            conn = self.db._connect()
            try:
                row = conn.execute(
                    "SELECT player_id FROM players WHERE LOWER(TRIM(name)) = LOWER(?) AND player_id != 'hero_default' LIMIT 1",
                    (clean,),
                ).fetchone()
                if row and row["player_id"]:
                    return self.db.get_existing_player(str(row["player_id"]))
            finally:
                conn.close()
        except Exception:
            pass
        return None

    def _bump_social_sync(self, p: dict):
        if not isinstance(p, dict):
            return
        p["socialRev"] = int(p.get("socialRev", 0) or 0) + 1
        p["_socialDirtyUntil"] = time.time() + 4.5

    def ensure_player_social(self, p: dict) -> dict:
        af = p.setdefault("autofarm", {})
        soc = af.get("social")

        legacy_fake_friends = {
            "shadowlord",
            "nachtklinge",
            "aurelia",
            "drachenherz",
            "valkyrie",
            "fenrir99",
            "[gm] aeryndor",
            "[gm] lyra",
            "[ga] valerius",
        }
        legacy_fake_requests = {"kromgar", "sylphie"}
        legacy_fake_texts = (
            "Willkommen in Aeryndor! 👑",
            "Danke! Das neue Drop-Filter-System",
            "Freut uns sehr! Viel Erfolg beim Farmen",
            "Hey! Bist du gleich beim Brutalen Hauptmann",
            "Ja klar, ich mache nur kurz meine Klinge",
            "Perfekt, ich halte den Spawn frei!",
            "Ich lege dir morgen Abend 3x Segensschriftrolle",
            "Super, danke dir! Schreib mir sobald du wieder online bist",
            "Bin gerade mitten im Rissmonolythen-Kampf, komme gleich zur Brücke!",
            "Alles klar! Lass uns gleich zusammen ins Grenzland porten",
            "Hab gerade eine Segensschriftrolle gedroppt!",
            "👑 Hallo ",
            "👑 Tipp vom GM-Team:",
            "👑 Das Äther-Eruptions-Event",
            "wurde deiner Freundesliste hinzugefügt",
            "ist momentan offline. Du kannst trotzdem jederzeit Offline-Nachrichten hinterlassen",
        )

        if not isinstance(soc, dict) or "friends" not in soc or "conversations" not in soc:
            soc = {
                "myStatus": "online",
                "gmList": [],
                "friends": [],
                "requests": [],
                "blocked": [],
                "conversations": {},
                "unread": {},
            }
            af["social"] = soc
        else:
            soc.setdefault("myStatus", "online")
            soc.setdefault("friends", [])
            soc.setdefault("requests", [])
            soc.setdefault("blocked", [])
            soc.setdefault("conversations", {})
            soc.setdefault("unread", {})

            # Bereinige alte Vorlagen-Kontakte, Vorlagen-Anfragen und Vorlagen-Nachrichten restlos
            soc["friends"] = [
                f
                for f in soc.get("friends", [])
                if isinstance(f, dict)
                and str(f.get("name") or "").strip()
                and str(f.get("name") or "").strip().lower() not in legacy_fake_friends
            ]
            soc["requests"] = [
                r
                for r in soc.get("requests", [])
                if isinstance(r, dict)
                and str(r.get("name") or "").strip()
                and str(r.get("name") or "").strip().lower() not in legacy_fake_requests
            ]

            cleaned_convs = {}
            for k_conv, msg_list in list((soc.get("conversations") or {}).items()):
                if not k_conv or str(k_conv).strip().lower() in legacy_fake_friends:
                    continue
                if not isinstance(msg_list, list):
                    continue
                real_msgs = []
                for m in msg_list:
                    if not isinstance(m, dict):
                        continue
                    mid = str(m.get("id") or "")
                    mtxt = str(m.get("text") or "")
                    msender = str(m.get("sender") or "")
                    if mid.startswith(("pm_gm_", "pm_sl_", "pm_dh_")):
                        continue
                    if m.get("isSystem") or msender == "System":
                        continue
                    if any(ft in mtxt for ft in legacy_fake_texts):
                        continue
                    real_msgs.append(m)
                if real_msgs:
                    cleaned_convs[k_conv] = real_msgs[-50:]
            soc["conversations"] = cleaned_convs

        # Echte Online-Teammitglieder ([SA] / [GM]) dynamisch bereitstellen (ohne Vorlagen-Texte)
        my_pid = str(p.get("player_id") or "")
        my_name_low = str(p.get("name") or "").strip().lower()
        live_gm_list = []
        for op_id, op in list(self.players.items()):
            if (
                op_id == my_pid
                or op_id == "hero_default"
                or not op.get("online")
                or not op.get("inWorld", False)
            ):
                continue
            op_trank = self._get_player_team_rank(op, op_id)
            if op_trank or self._is_sa_player(op, op_id):
                rank_tag = op_trank or "SA"
                role_desc = {
                    "SA": "Serverleitung & Administration",
                    "SGA": "Senior Game Administration",
                    "GA": "Game Administration",
                    "TM": "Teamleitung & Organisation",
                    "CM": "Community Management",
                    "SGM": "Super Game Master",
                    "GM": "Game Master & Support",
                    "TGM": "Trial Game Master",
                    "JGM": "Junior Game Master",
                    "EM": "Event Management",
                    "DEV": "Entwicklung & Technik",
                    "SUP": "Spieler-Support",
                }.get(rank_tag, "Server-Team")
                op_cdef = CHARACTER_CLASSES.get(op.get("class_id", "warrior"), CHARACTER_CLASSES["warrior"])
                op_map = MAPS.get(op.get("map_id", "morgenwacht"), {}).get("name", "Morgenwacht")
                live_gm_list.append(
                    {
                        "name": op["name"],
                        "role": role_desc,
                        "badge": rank_tag,
                        "classId": op.get("class_id", "warrior"),
                        "className": op_cdef["name"],
                        "level": int(op.get("level", 99)),
                        "status": (op.get("social") or {}).get("myStatus", "online"),
                        "zone": op_map,
                        "lastSeen": "Jetzt online",
                        "isGM": True,
                        "isSA": (rank_tag == "SA"),
                        "teamRank": rank_tag,
                    }
                )
        soc["gmList"] = live_gm_list

        # Stelle sicher, dass jeder echte Gesprächspartner aus 'conversations' auch in 'friends' auftaucht
        existing_friend_names = {str(f.get("name") or "").strip().lower() for f in soc["friends"]}
        gm_names_low = {str(g.get("name") or "").strip().lower() for g in live_gm_list}
        for conv_partner in list(soc["conversations"].keys()):
            cp_low = str(conv_partner or "").strip().lower()
            if not cp_low or cp_low == my_name_low or cp_low in existing_friend_names or cp_low in gm_names_low:
                continue
            soc["friends"].append(
                {
                    "name": conv_partner,
                    "classId": "warrior",
                    "className": "Klingenwächter",
                    "level": 1,
                    "status": "offline",
                    "zone": "Offline",
                    "guild": "Aeryndor",
                    "lastSeen": "Offline",
                }
            )
            existing_friend_names.add(cp_low)

        # Synchronisiere Live-Status, Level, Klasse & Gebiet aller Kontakte mit den echten Server-Spielern
        online_by_name = {}
        for op_id, op in list(self.players.items()):
            if op_id == "hero_default" or not op.get("name"):
                continue
            online_by_name[str(op["name"]).strip().lower()] = op

        deduped_friends = []
        seen_f = set()
        for f in soc["friends"]:
            fname = str(f.get("name") or "").strip()
            flow = fname.lower()
            if not fname or flow == my_name_low or flow in seen_f:
                continue
            seen_f.add(flow)
            op_match = online_by_name.get(flow)
            if op_match and op_match.get("online") and op_match.get("inWorld", True):
                cdef = CHARACTER_CLASSES.get(op_match.get("class_id", "warrior"), CHARACTER_CLASSES["warrior"])
                map_name = MAPS.get(op_match.get("map_id", "morgenwacht"), {}).get("name", "Morgenwacht")
                f["name"] = op_match["name"]
                f["classId"] = op_match.get("class_id", "warrior")
                f["className"] = cdef["name"]
                f["level"] = int(op_match.get("level", 1))
                f["status"] = (op_match.get("social") or {}).get("myStatus", "online")
                f["zone"] = map_name
                f["isSA"] = self._is_sa_player(op_match, op_match.get("player_id", ""))
                f["lastSeen"] = "Jetzt online"
                for m in soc["conversations"].get(f["name"], []):
                    if isinstance(m, dict) and m.get("isSelf") and m.get("delivery") == "offline_saved":
                        m["delivery"] = "read"
            else:
                if op_match:
                    cdef = CHARACTER_CLASSES.get(op_match.get("class_id", "warrior"), CHARACTER_CLASSES["warrior"])
                    f["name"] = op_match["name"]
                    f["classId"] = op_match.get("class_id", f.get("classId", "warrior"))
                    f["className"] = cdef["name"]
                    f["level"] = int(op_match.get("level", f.get("level", 1)))
                f["status"] = "offline"
                if f.get("lastSeen") in ("Online", "Jetzt online", None, ""):
                    f["lastSeen"] = "Offline"
                if not f.get("zone") or "Kanal" in str(f.get("zone", "")):
                    f["zone"] = "Derzeit Offline"
            deduped_friends.append(f)

        soc["friends"] = deduped_friends
        af["social"] = soc
        p["social"] = soc
        return soc

    def handle_social_action(self, player_id: str, sub_action: str, payload: dict) -> dict:
        p = self.players.get(player_id)
        if not p:
            return {"ok": False, "message": "Spieler nicht aktiv."}
        soc = self.ensure_player_social(p)
        now_hm = time.strftime("%H:%M")

        if sub_action == "set_status":
            st = payload.get("status", "online")
            if st in ("online", "afk", "busy"):
                soc["myStatus"] = st
                self._bump_social_sync(p)
                self.db.save_player_state(p)
            return {"ok": True, "status": soc["myStatus"], "message": "Messenger-Status aktualisiert."}

        if sub_action == "mark_read":
            target_name = (payload.get("name") or "").strip()
            unread = soc.setdefault("unread", {})
            if target_name and unread.get(target_name):
                unread.pop(target_name, None)
                self._bump_social_sync(p)
                self.db.save_player_state(p)
            return {"ok": True}

        if sub_action == "clear_conversation":
            target_name = (payload.get("name") or "").strip()
            if target_name in soc.get("conversations", {}):
                soc["conversations"][target_name] = []
            soc.setdefault("unread", {}).pop(target_name, None)
            self._bump_social_sync(p)
            self.db.save_player_state(p)
            return {"ok": True, "contactName": target_name, "message": f"Chatverlauf mit {target_name} geleert."}

        if sub_action == "add_friend":
            target_name = (payload.get("name") or "").strip()[:28]
            if not target_name:
                return {"ok": False, "message": "Bitte gib einen Spielernamen ein."}
            if target_name.lower() == p["name"].lower():
                return {"ok": False, "message": "Du kannst dich nicht selbst hinzufügen."}

            existing = next(
                (f for f in soc["friends"] if f["name"].lower() == target_name.lower()),
                None,
            )
            if existing:
                return {
                    "ok": True,
                    "contactName": existing["name"],
                    "message": f"{existing['name']} ist bereits in deiner Kontaktliste.",
                }

            online_match = next(
                (
                    op
                    for op in self.players.values()
                    if op.get("name", "").lower() == target_name.lower()
                    and (op.get("online") or op.get("isBot"))
                ),
                None,
            )
            db_match = None if online_match else self._find_player_by_name_in_db(target_name)

            if online_match:
                cdef = CHARACTER_CLASSES.get(online_match["class_id"], CHARACTER_CLASSES["warrior"])
                map_name = MAPS.get(online_match["map_id"], {}).get("name", "Morgenwacht")
                guild_name = (
                    (online_match.get("guild") or {}).get("name")
                    if isinstance(online_match.get("guild"), dict)
                    else (online_match.get("guildName") or "")
                )
                new_friend = {
                    "name": online_match["name"],
                    "classId": online_match["class_id"],
                    "className": cdef["name"],
                    "level": int(online_match.get("level", 1)),
                    "status": (online_match.get("social") or {}).get("myStatus", "online"),
                    "zone": f"{map_name} • Kanal {int(online_match.get('channel', 1))}",
                    "guild": guild_name,
                    "lastSeen": "Online",
                }
            elif db_match:
                cdef = CHARACTER_CLASSES.get(db_match.get("class_id", "warrior"), CHARACTER_CLASSES["warrior"])
                guild_name = (
                    (db_match.get("guild") or {}).get("name")
                    if isinstance(db_match.get("guild"), dict)
                    else (db_match.get("guildName") or "")
                )
                new_friend = {
                    "name": db_match["name"],
                    "classId": db_match.get("class_id", "warrior"),
                    "className": cdef["name"],
                    "level": int(db_match.get("level", 1)),
                    "status": "offline",
                    "zone": "Offline",
                    "guild": guild_name,
                    "lastSeen": "Offline",
                }
            else:
                return {"ok": False, "message": f"Spieler '{target_name}' wurde nicht gefunden."}

            soc["friends"].insert(0, new_friend)
            soc["conversations"].setdefault(new_friend["name"], [])

            if online_match and online_match["player_id"] != player_id and not online_match.get("isBot"):
                op_soc = self.ensure_player_social(online_match)
                p_cdef = CHARACTER_CLASSES.get(p["class_id"], CHARACTER_CLASSES["warrior"])
                already_friend = any(f["name"].lower() == p["name"].lower() for f in op_soc.get("friends", []))
                already_req = any(r["name"].lower() == p["name"].lower() for r in op_soc.get("requests", []))
                if not already_friend and not already_req:
                    op_soc.setdefault("requests", []).insert(
                        0,
                        {
                            "name": p["name"],
                            "classId": p["class_id"],
                            "className": p_cdef["name"],
                            "level": p["level"],
                            "note": "Freundschaftsanfrage",
                        },
                    )
                online_match["lastSocialNotice"] = {
                    "id": f"sn_{uuid.uuid4().hex[:8]}",
                    "text": f"👥 {p['name']} (Lv. {p['level']}) hat dir eine Freundschaftsanfrage gesendet!",
                    "t": time.time(),
                }
                self._bump_social_sync(online_match)
                self.db.save_player_state(online_match)

            self._bump_social_sync(p)
            self.db.save_player_state(p)
            return {
                "ok": True,
                "contactName": new_friend["name"],
                "message": f"👥 {new_friend['name']} zur Kontaktliste hinzugefügt!",
            }

        if sub_action == "remove_friend":
            target_name = (payload.get("name") or "").strip()
            soc["friends"] = [f for f in soc["friends"] if f["name"] != target_name]
            self._bump_social_sync(p)
            self.db.save_player_state(p)
            return {"ok": True, "message": f"{target_name} wurde aus der Kontaktliste entfernt."}

        if sub_action == "accept_request":
            req_name = (payload.get("name") or "").strip()
            req = next((r for r in soc.get("requests", []) if r["name"] == req_name), None)
            if not req:
                return {"ok": False, "message": "Anfrage nicht gefunden."}
            soc["requests"] = [r for r in soc["requests"] if r["name"] != req_name]
            online_match = next(
                (
                    op
                    for op in self.players.values()
                    if op.get("name", "").lower() == req_name.lower()
                    and (op.get("online") or op.get("isBot"))
                ),
                None,
            )
            map_name = MAPS.get(online_match["map_id"], {}).get("name", "Morgenwacht") if online_match else "Offline"
            new_friend = {
                "name": req["name"],
                "classId": req.get("classId", "warrior"),
                "className": req.get("className", "Klingenwächter"),
                "level": int(online_match["level"]) if online_match else int(req.get("level", 1)),
                "status": "online" if online_match else "offline",
                "zone": f"{map_name} • Kanal 1" if online_match else "Offline",
                "guild": "",
                "lastSeen": "Online" if online_match else "Offline",
            }
            if not any(f["name"].lower() == req["name"].lower() for f in soc["friends"]):
                soc["friends"].insert(0, new_friend)
            soc["conversations"].setdefault(req["name"], [])
            self._bump_social_sync(p)
            self.db.save_player_state(p)
            return {
                "ok": True,
                "contactName": req["name"],
                "message": f"✔ Freundschaftsanfrage von {req['name']} angenommen!",
            }

        if sub_action == "decline_request":
            req_name = (payload.get("name") or "").strip()
            soc["requests"] = [r for r in soc.get("requests", []) if r["name"] != req_name]
            self._bump_social_sync(p)
            self.db.save_player_state(p)
            return {"ok": True, "message": f"Anfrage von {req_name} abgelehnt."}

        if sub_action == "toggle_block":
            target_name = (payload.get("name") or "").strip()
            if not target_name:
                return {"ok": False, "message": "Kein Spieler ausgewählt."}
            blocked = soc.setdefault("blocked", [])
            if target_name in blocked:
                blocked.remove(target_name)
                msg = f"🔓 {target_name} wurde entblockt."
            else:
                blocked.append(target_name)
                msg = f"🚫 {target_name} wurde blockiert."
            self._bump_social_sync(p)
            self.db.save_player_state(p)
            return {"ok": True, "message": msg}

        if sub_action == "send_message":
            recipient = (payload.get("recipient") or "").strip()[:32]
            raw_text = (payload.get("text") or "").strip()[:240]
            if not recipient or not raw_text:
                return {"ok": False, "message": "Bitte gib eine Nachricht ein."}
            if recipient.lower() == p["name"].lower():
                return {"ok": False, "message": "Du kannst dir nicht selbst schreiben."}

            clean_text = self.expand_chat_smileys(raw_text)

            real_online_target = next(
                (
                    op
                    for op in self.players.values()
                    if op["player_id"] != player_id
                    and op.get("name", "").lower() == recipient.lower()
                    and (op.get("online") or op.get("isBot"))
                ),
                None,
            )
            db_target = None if real_online_target else self._find_player_by_name_in_db(recipient)

            canonical_recipient = (
                real_online_target["name"]
                if real_online_target
                else (db_target["name"] if db_target else recipient)
            )

            friend_contact = next(
                (f for f in soc.get("friends", []) if f["name"].lower() == canonical_recipient.lower()),
                None,
            )

            if not friend_contact:
                if real_online_target:
                    cdef = CHARACTER_CLASSES.get(real_online_target["class_id"], CHARACTER_CLASSES["warrior"])
                    map_name = MAPS.get(real_online_target["map_id"], {}).get("name", "Morgenwacht")
                    guild_name = (
                        (real_online_target.get("guild") or {}).get("name")
                        if isinstance(real_online_target.get("guild"), dict)
                        else (real_online_target.get("guildName") or "")
                    )
                    friend_contact = {
                        "name": canonical_recipient,
                        "classId": real_online_target["class_id"],
                        "className": cdef["name"],
                        "level": int(real_online_target.get("level", 1)),
                        "status": (real_online_target.get("social") or {}).get("myStatus", "online"),
                        "zone": f"{map_name} • Kanal {int(real_online_target.get('channel', 1))}",
                        "guild": guild_name,
                        "lastSeen": "Online",
                    }
                elif db_target:
                    cdef = CHARACTER_CLASSES.get(db_target.get("class_id", "warrior"), CHARACTER_CLASSES["warrior"])
                    guild_name = (
                        (db_target.get("guild") or {}).get("name")
                        if isinstance(db_target.get("guild"), dict)
                        else (db_target.get("guildName") or "")
                    )
                    friend_contact = {
                        "name": canonical_recipient,
                        "classId": db_target.get("class_id", "warrior"),
                        "className": cdef["name"],
                        "level": int(db_target.get("level", 1)),
                        "status": "offline",
                        "zone": "Offline",
                        "guild": guild_name,
                        "lastSeen": "Offline",
                    }
                else:
                    return {"ok": False, "message": f"Spieler '{recipient}' wurde nicht gefunden."}
                soc["friends"].insert(0, friend_contact)

            # Prüfe ob der Empfänger uns blockiert hat
            if real_online_target:
                op_soc_check = self.ensure_player_social(real_online_target)
                if any(b.lower() == p["name"].lower() for b in op_soc_check.get("blocked", [])):
                    return {"ok": False, "message": f"{canonical_recipient} empfängt derzeit keine Nachrichten von dir."}

            is_offline = real_online_target is None
            delivery_state = "offline_saved" if is_offline else "read"

            conv = soc["conversations"].setdefault(canonical_recipient, [])
            msg_out_id = f"pm_{uuid.uuid4().hex[:8]}"
            conv.append(
                {
                    "id": msg_out_id,
                    "sender": p["name"],
                    "text": clean_text,
                    "time": now_hm,
                    "isSelf": True,
                    "delivery": delivery_state,
                }
            )
            if len(conv) > 60:
                soc["conversations"][canonical_recipient] = conv[-60:]

            # Unread beim Absender für dieses Gespräch zurücksetzen
            soc.setdefault("unread", {}).pop(canonical_recipient, None)

            # Live-Zustellung an echten Online-Spieler
            if real_online_target:
                op_soc = self.ensure_player_social(real_online_target)
                if not any(f["name"].lower() == p["name"].lower() for f in op_soc.get("friends", [])):
                    p_cdef = CHARACTER_CLASSES.get(p["class_id"], CHARACTER_CLASSES["warrior"])
                    p_map_name = MAPS.get(p["map_id"], {}).get("name", "Morgenwacht")
                    p_guild = (
                        (p.get("guild") or {}).get("name")
                        if isinstance(p.get("guild"), dict)
                        else (p.get("guildName") or "")
                    )
                    op_soc.setdefault("friends", []).insert(
                        0,
                        {
                            "name": p["name"],
                            "classId": p["class_id"],
                            "className": p_cdef["name"],
                            "level": int(p.get("level", 1)),
                            "status": soc.get("myStatus", "online"),
                            "zone": f"{p_map_name} • Kanal {int(p.get('channel', 1))}",
                            "guild": p_guild,
                            "lastSeen": "Online",
                        },
                    )
                op_conv = op_soc["conversations"].setdefault(p["name"], [])
                msg_id = f"pm_{uuid.uuid4().hex[:8]}"
                op_conv.append(
                    {
                        "id": msg_id,
                        "sender": p["name"],
                        "text": clean_text,
                        "time": now_hm,
                        "isSelf": False,
                        "delivery": "read",
                    }
                )
                if len(op_conv) > 60:
                    op_soc["conversations"][p["name"]] = op_conv[-60:]
                op_unread = op_soc.setdefault("unread", {})
                op_unread[p["name"]] = int(op_unread.get(p["name"], 0)) + 1
                real_online_target["lastWhisperNotice"] = {
                    "id": msg_id,
                    "from": p["name"],
                    "text": clean_text,
                    "t": time.time(),
                }
                self._bump_social_sync(real_online_target)
                if not real_online_target.get("isBot") and not str(real_online_target.get("player_id", "")).startswith("bot_"):
                    self.db.save_player_state(real_online_target)
                elif not str(player_id).startswith("bot_"):
                    # KI v5.0 Kontextbezogene Live-Antwort, NUR wenn der Spieler aktiv einem Helden-Bot schreibt (keine Vorlagen!)
                    bot_reply_text = self._generate_bot_live_messenger_reply(real_online_target, p, clean_text)
                    if bot_reply_text:
                        reply_id = f"pm_{uuid.uuid4().hex[:8]}"
                        conv.append(
                            {
                                "id": reply_id,
                                "sender": canonical_recipient,
                                "text": bot_reply_text,
                                "time": now_hm,
                                "isSelf": False,
                                "delivery": "read",
                            }
                        )
                        if len(conv) > 60:
                            soc["conversations"][canonical_recipient] = conv[-60:]
                        op_conv.append(
                            {
                                "id": reply_id,
                                "sender": canonical_recipient,
                                "text": bot_reply_text,
                                "time": now_hm,
                                "isSelf": True,
                                "delivery": "read",
                            }
                        )
                        p["lastWhisperNotice"] = {
                            "id": reply_id,
                            "from": canonical_recipient,
                            "text": bot_reply_text,
                            "t": time.time(),
                        }
            elif db_target:
                # Persistente Offline-Zustellung in die Datenbank des Offline-Spielers
                op_soc = self.ensure_player_social(db_target)
                if not any(f["name"].lower() == p["name"].lower() for f in op_soc.get("friends", [])):
                    p_cdef = CHARACTER_CLASSES.get(p["class_id"], CHARACTER_CLASSES["warrior"])
                    p_map_name = MAPS.get(p["map_id"], {}).get("name", "Morgenwacht")
                    p_guild = (
                        (p.get("guild") or {}).get("name")
                        if isinstance(p.get("guild"), dict)
                        else (p.get("guildName") or "")
                    )
                    op_soc.setdefault("friends", []).insert(
                        0,
                        {
                            "name": p["name"],
                            "classId": p["class_id"],
                            "className": p_cdef["name"],
                            "level": int(p.get("level", 1)),
                            "status": "online",
                            "zone": f"{p_map_name} • Kanal 1",
                            "guild": p_guild,
                            "lastSeen": "Online",
                        },
                    )
                op_conv = op_soc["conversations"].setdefault(p["name"], [])
                op_conv.append(
                    {
                        "id": f"pm_{uuid.uuid4().hex[:8]}",
                        "sender": p["name"],
                        "text": clean_text,
                        "time": now_hm,
                        "isSelf": False,
                        "delivery": "offline_saved",
                    }
                )
                if len(op_conv) > 60:
                    op_soc["conversations"][p["name"]] = op_conv[-60:]
                op_unread = op_soc.setdefault("unread", {})
                op_unread[p["name"]] = int(op_unread.get(p["name"], 0)) + 1
                self.db.save_player_state(db_target)

            self._bump_social_sync(p)
            self.db.save_player_state(p)
            return {
                "ok": True,
                "recipient": canonical_recipient,
                "isOffline": is_offline,
                "message": (
                    f"📥 Offline-Nachricht an {canonical_recipient} gespeichert."
                    if is_offline
                    else f"💬 Nachricht an {canonical_recipient} gesendet."
                ),
            }

        return {"ok": False, "message": "Unbekannte Messenger-Aktion."}

    def _generate_bot_live_messenger_reply(self, bot: dict, sender_player: dict, message_text: str) -> str:
        """KI v5.0 Kontextbezogene Live-Antwort im Messenger (wird NUR ausgeführt, wenn ein echter Spieler einem Helden-Bot schreibt!).
        Nutzt 100% echte Live-Daten des Bots (Position, Sektor, aktuelles Ziel/Boss, Waffe+Stufe, handelbares Inventar) und kann auf Wunsch direkt zur Hilfe eilen."""
        if not bot or not sender_player:
            return ""
        now = time.time()
        txt_low = str(message_text or "").strip().lower()
        b_name = bot.get("name", "Helden-Bot")
        b_lvl = int(bot.get("level", 1))
        b_cls = CHARACTER_CLASSES.get(bot.get("class_id", "warrior"), CHARACTER_CLASSES["warrior"])["name"]
        b_sec = self._get_bot_route_sector_label(bot)
        bx, bz = int(round(float(bot.get("pos_x", 0.0)))), int(round(float(bot.get("pos_z", 0.0))))
        eq = bot.get("equipment") or {}
        wpn = eq.get("weapon") or {}
        wpn_str = f"{wpn.get('name', 'Klinge')} +{int(wpn.get('plusLevel', 0))}" if wpn.get("name") else "Standardwaffe"
        arm = eq.get("armor") or {}
        arm_str = f"{arm.get('name', 'Rüstung')} +{int(arm.get('plusLevel', 0))}" if arm.get("name") else "Standardrüstung"
        cur_tid = bot.get("autoFarmTargetId") or bot.get("targetId")
        cur_mob = self.monsters.get(cur_tid) if cur_tid else None
        cur_mob_str = f"{cur_mob['name']} (Lv. {cur_mob.get('level', 1)})" if (cur_mob and cur_mob.get("state") != "dead") else "Gegnern auf meiner Route"

        # 1. Spieler bittet um Hilfe / Gruppe / Unterstützung ("hilfe", "komm", "gruppe", "party", "boss", "monolith", "riss")
        if any(k in txt_low for k in ("hilfe", "help", "komm", "gruppe", "party", "unterstütz", "buff", "boss", "riss", "monolith")):
            if sender_player.get("map_id") == bot.get("map_id"):
                af_b = bot.setdefault("autofarm", {})
                af_b["anchorX"] = float(sender_player.get("pos_x", bx))
                af_b["anchorZ"] = float(sender_player.get("pos_z", bz))
                if not bot.get("active_mount"):
                    bot["active_mount"] = af_b.get("mountId") or "mount_war_boar"
                    self.compute_player_combat_stats(bot)
                p_tid = sender_player.get("targetId") or sender_player.get("manualFocusTargetId")
                if p_tid and p_tid in self.monsters and self.monsters[p_tid].get("state") != "dead":
                    bot["targetId"] = p_tid
                    bot["autoFarmTargetId"] = p_tid
                    bot["manualFocusTargetId"] = p_tid
                bot["autoFarmStatus"] = f"🐎 Eile per Messenger-Ruf zu {sender_player['name']}!"
                bot["_botTradeStatusUntil"] = now + 10.0
                return (
                    f"⚔️ Verstanden, {sender_player['name']}! Ich sitze sofort auf und reite von {b_sec} ({bx}, {bz}) "
                    f"zu deiner Position ({int(sender_player['pos_x'])}, {int(sender_player['pos_z'])})! Lad mich gern in deine Gruppe ein."
                )

        # 1b. SSOT-Handbuch-Auskunft bei Fachfragen (Drops, Schmied, Skills, Pferd, Map-Wechsel)
        ssot_ans = self._answer_ssot_handbook_question(txt_low)
        if ssot_ans:
            return f"📖 {b_name} (Lv. {b_lvl} {b_cls}): {ssot_ans}"

        # 2. Spieler fragt nach Position / Wo bist du / Was machst du
        if any(k in txt_low for k in ("wo ", "wo?", "pos", "koordinat", "ort", "machst", "farmst", "status")):
            town_st = bot.get("townErrand")
            if isinstance(town_st, dict):
                return f"🏛️ Ich bin gerade auf Stadtrundgang ({bx}, {bz}) beim Quest-NPC, Schmied & der Händlerin und kehre gleich auf meine Route zurück!"
            return (
                f"📍 Ich (Lv. {b_lvl} {b_cls}) bin gerade in {b_sec} bei ({bx}, {bz}) "
                f"und kämpfe gegen {cur_mob_str}. Status: {bot.get('autoFarmStatus', 'Auf Patrouille')}."
            )

        # 3. Spieler fragt nach Handel / Items / Verkauf / Waffe / Ausrüstung
        if any(k in txt_low for k in ("handel", "trade", "item", "verkauf", "kauf", "waffe", "eq", "rüstung", "splitter", "rolle")):
            tradable_names = []
            for it in (bot.get("inventory") or []):
                if it.get("equippedSlot") or it.get("equipped_slot") or it.get("reservedShopId") or it.get("reserved_shop_id"):
                    continue
                nm = it.get("name") or ITEM_TEMPLATES.get(it.get("templateId", ""), {}).get("name")
                if nm:
                    plus_s = f" +{it.get('plusLevel')}" if int(it.get("plusLevel", 0)) > 0 else ""
                    qty_s = f"{it.get('quantity', 1)}x " if int(it.get("quantity", 1)) > 1 else ""
                    tradable_names.append(f"{qty_s}{nm}{plus_s}")
                if len(tradable_names) >= 4:
                    break
            inv_preview = ", ".join(tradable_names) if tradable_names else "Segensrollen, Monolith-Splitter & Tränke"
            return (
                f"🤝 Ich trage aktuell {wpn_str} & {arm_str} ({int(bot.get('yang', 0)):,} Gold). "
                f"Im Rucksack zum Handeln habe ich u.a.: {inv_preview}. Klick mich einfach an und starte '🤝 Handeln'!"
            )

        # 4. Allgemeine Live-Antwort mit aktuellem Status & Position
        return (
            f"👋 Grüße {sender_player['name']}! Hier ist {b_name} (Lv. {b_lvl} {b_cls}, {wpn_str}). "
            f"Ich bin gerade in {b_sec} ({bx}, {bz}) bei {cur_mob_str}. Schreib 'Hilfe' wenn ich zu dir reiten soll, oder 'Handel' für meine Items!"
        )

    # ========================================================================
    # 9B. GRUPPEN-SYSTEM (PARTY) & DIREKTER SPIELER-HANDEL (TRADE)
    # ========================================================================
    def _resolve_target_player(self, target_id: str = "", target_name: str = "") -> Optional[dict]:
        if target_id and target_id in self.players:
            return self.players[target_id]
        if target_name:
            t_low = target_name.strip().lower()
            for op in self.players.values():
                if op.get("name", "").lower() == t_low:
                    return op
        return None

    def handle_party_action(self, player_id: str, sub_action: str, payload: dict) -> dict:
        p = self.players.get(player_id)
        if not p:
            return {"ok": False, "message": "Spieler nicht gefunden."}
        now = time.time()

        if sub_action == "invite":
            target = self._resolve_target_player(
                str(payload.get("targetPlayerId") or ""),
                str(payload.get("targetName") or ""),
            )
            if not target or not target.get("online"):
                return {"ok": False, "message": "Dieser Spieler ist aktuell nicht online."}
            if target["player_id"] == player_id:
                return {"ok": False, "message": "Du kannst dich nicht selbst in eine Gruppe einladen."}

            my_party_id = p.get("partyId")
            my_party = self.parties.get(my_party_id) if my_party_id else None
            if my_party and my_party.get("leaderId") != player_id:
                if str(my_party.get("leaderId", "")).startswith("bot_"):
                    my_party["leaderId"] = player_id
                else:
                    return {"ok": False, "message": "Nur der Gruppenanführer kann weitere Spieler einladen."}
            if my_party and len(my_party.get("memberIds", [])) >= 8:
                return {"ok": False, "message": "Deine Gruppe ist bereits voll (max. 8 Mitglieder)."}

            is_target_bot = str(target["player_id"]).startswith("bot_")
            t_party_id = target.get("partyId")
            if t_party_id and t_party_id in self.parties:
                if t_party_id == my_party_id:
                    return {"ok": False, "message": f"{target['name']} ist bereits in deiner Gruppe!"}
                if is_target_bot and not str(player_id).startswith("bot_"):
                    # Bots verlassen sofort ihre automatische Bot-Routengruppe, um die Einladung eines echten Spielers anzunehmen!
                    self.handle_party_action(target["player_id"], "leave", {})
                else:
                    return {"ok": False, "message": f"{target['name']} befindet sich bereits in einer anderen Gruppe."}

            cdef = CHARACTER_CLASSES.get(p["class_id"], CHARACTER_CLASSES["warrior"])
            target["pendingPartyInvite"] = {
                "id": f"pinv_{uuid.uuid4().hex[:8]}",
                "fromPlayerId": player_id,
                "fromName": p["name"],
                "fromLevel": p["level"],
                "fromClassName": cdef["name"],
                "expiresAt": now + 60.0,
            }
            if is_target_bot:
                self.handle_party_action(target["player_id"], "accept", {})
                af_t = target.get("autofarm")
                if isinstance(af_t, dict):
                    af_t["anchorX"] = p["pos_x"]
                    af_t["anchorZ"] = p["pos_z"]
                target["autoFarmStatus"] = f"🤝 Gruppe mit {p['name']} beigetreten – kämpfe an deiner Seite!"
                target["_botTradeStatusUntil"] = now + 6.0
                return {"ok": True, "message": f"👥 {target['name']} hat deine Gruppeneinladung sofort angenommen!"}
            return {"ok": True, "message": f"👥 Gruppeneinladung an {target['name']} gesendet!"}

        if sub_action == "accept":
            inv = p.get("pendingPartyInvite")
            p["pendingPartyInvite"] = None
            if not inv or float(inv.get("expiresAt", 0.0)) < now:
                return {"ok": False, "message": "Die Gruppeneinladung ist abgelaufen."}
            inviter = self.players.get(inv.get("fromPlayerId"))
            if not inviter or not inviter.get("online"):
                return {"ok": False, "message": "Der einladende Spieler ist nicht mehr online."}

            party_id = inviter.get("partyId")
            party = self.parties.get(party_id) if party_id else None
            if not party:
                party_id = f"pty_{uuid.uuid4().hex[:8]}"
                party = {
                    "id": party_id,
                    "leaderId": inviter["player_id"],
                    "memberIds": [inviter["player_id"]],
                    "createdAt": now,
                }
                self.parties[party_id] = party
                inviter["partyId"] = party_id

            if len(party["memberIds"]) >= 8:
                return {"ok": False, "message": "Die Gruppe ist inzwischen voll."}
            if player_id not in party["memberIds"]:
                party["memberIds"].append(player_id)
            p["partyId"] = party_id

            notice_id = f"sn_{uuid.uuid4().hex[:8]}"
            for mid in party["memberIds"]:
                mp = self.players.get(mid)
                if mp and mid != player_id:
                    mp["lastSocialNotice"] = {
                        "id": notice_id,
                        "text": f"👥 {p['name']} (Lv. {p['level']}) ist der Gruppe beigetreten!",
                        "t": now,
                    }
            return {"ok": True, "message": f"👥 Du bist der Gruppe von {inviter['name']} beigetreten!"}

        if sub_action == "decline":
            inv = p.get("pendingPartyInvite")
            p["pendingPartyInvite"] = None
            if inv:
                inviter = self.players.get(inv.get("fromPlayerId"))
                if inviter:
                    inviter["lastSocialNotice"] = {
                        "id": f"sn_{uuid.uuid4().hex[:8]}",
                        "text": f"❌ {p['name']} hat deine Gruppeneinladung abgelehnt.",
                        "t": now,
                    }
            return {"ok": True, "message": "Gruppeneinladung abgelehnt."}

        if sub_action == "leave":
            party_id = p.get("partyId")
            p["partyId"] = None
            party = self.parties.get(party_id) if party_id else None
            if not party:
                return {"ok": True, "message": "Du hast die Gruppe verlassen."}
            party["memberIds"] = [m for m in party.get("memberIds", []) if m != player_id]
            notice_id = f"sn_{uuid.uuid4().hex[:8]}"
            if len(party["memberIds"]) <= 1:
                for rem_id in party["memberIds"]:
                    rp = self.players.get(rem_id)
                    if rp:
                        rp["partyId"] = None
                        rp["lastSocialNotice"] = {
                            "id": notice_id,
                            "text": f"👥 {p['name']} hat die Gruppe verlassen. Die Gruppe wurde aufgelöst.",
                            "t": now,
                        }
                self.parties.pop(party_id, None)
            else:
                if party.get("leaderId") == player_id:
                    party["leaderId"] = party["memberIds"][0]
                for rem_id in party["memberIds"]:
                    rp = self.players.get(rem_id)
                    if rp:
                        rp["lastSocialNotice"] = {
                            "id": notice_id,
                            "text": f"👥 {p['name']} hat die Gruppe verlassen.",
                            "t": now,
                        }
            return {"ok": True, "message": "Du hast die Gruppe verlassen."}

        if sub_action == "kick":
            party_id = p.get("partyId")
            party = self.parties.get(party_id) if party_id else None
            if not party or party.get("leaderId") != player_id:
                return {"ok": False, "message": "Nur der Gruppenanführer kann Mitglieder entfernen."}
            target_id = str(payload.get("targetPlayerId") or "")
            if target_id not in party.get("memberIds", []) or target_id == player_id:
                return {"ok": False, "message": "Spieler nicht in der Gruppe gefunden."}
            party["memberIds"] = [m for m in party["memberIds"] if m != target_id]
            kicked_p = self.players.get(target_id)
            kicked_name = kicked_p["name"] if kicked_p else "Spieler"
            if kicked_p:
                kicked_p["partyId"] = None
                kicked_p["lastSocialNotice"] = {
                    "id": f"sn_{uuid.uuid4().hex[:8]}",
                    "text": "👥 Du wurdest aus der Gruppe entfernt.",
                    "t": now,
                }
            if len(party["memberIds"]) <= 1:
                p["partyId"] = None
                self.parties.pop(party_id, None)
                return {"ok": True, "message": f"{kicked_name} wurde entfernt. Die Gruppe wurde aufgelöst."}
            return {"ok": True, "message": f"{kicked_name} wurde aus der Gruppe entfernt."}

        if sub_action in ("tactic", "command", "buff_me"):
            party_id = p.get("partyId")
            party = self.parties.get(party_id) if party_id else None
            if not party:
                return {"ok": False, "message": "Du befindest dich aktuell in keiner Gruppe."}
            tactic = "buff" if sub_action == "buff_me" else str(payload.get("tactic") or payload.get("command") or "free").lower()
            if tactic not in ("focus", "protect", "rally", "buff", "awaken_monolith", "hunt_boss", "free"):
                tactic = "free"

            bot_allies = [
                self.players.get(mid)
                for mid in party.get("memberIds", [])
                if mid != player_id
                and str(mid).startswith("bot_")
                and self.players.get(mid)
                and self.players[mid].get("online")
                and not self.players[mid].get("isDead")
            ]

            if tactic == "buff":
                shaman_allies = [b for b in bot_allies if b.get("class_id") == "shaman"]
                caster = shaman_allies[0] if shaman_allies else (bot_allies[0] if bot_allies else None)
                if not caster:
                    return {"ok": False, "message": "Kein aktives Gruppenmitglied für Buffs in der Nähe."}
                self._apply_shaman_party_buffs_to_ally(caster, p, now, force_heal=True)
                for other_mid in party.get("memberIds", []):
                    omp = self.players.get(other_mid)
                    if omp and other_mid != player_id and not omp.get("isDead"):
                        self._apply_shaman_party_buffs_to_ally(caster, omp, now, force_heal=False)
                if caster.get("class_id") == "shaman":
                    return {
                        "ok": True,
                        "tactic": party.get("tactic", "free"),
                        "message": f"🐉✨ {caster['name']} wirkt 'Hilfe des Drachen' (+30% AW, +15% Krit, +20% Tempo), 'Segen' (+35% DEF) & 'Kurieren' auf dich!",
                    }
                return {
                    "ok": True,
                    "tactic": party.get("tactic", "free"),
                    "message": f"🛡️✨ {caster['name']} wirkt 'Gruppen-Schlachtruf' (+18% AW, +22% DEF) & Heilung auf dich!",
                }

            party["tactic"] = tactic
            party["tacticCommanderId"] = player_id
            party["tacticUpdatedAt"] = now

            if tactic == "focus":
                cand_tid = str(
                    payload.get("targetId")
                    or p.get("targetId")
                    or p.get("manualFocusTargetId")
                    or p.get("autoFarmTargetId")
                    or ""
                )
                target_mob = self.monsters.get(cand_tid) if cand_tid else None
                if not target_mob or target_mob.get("state") == "dead" or target_mob.get("mapId") != p.get("map_id"):
                    nearby_mobs = [
                        m for m in self.monsters.values()
                        if m.get("mapId") == p.get("map_id")
                        and m.get("state") != "dead"
                        and dist2d(p["pos_x"], p["pos_z"], m["x"], m["z"]) <= 65.0
                    ]
                    if nearby_mobs:
                        target_mob = min(
                            nearby_mobs,
                            key=lambda m: (0 if (m.get("kind") == "metin" or m.get("isBoss")) else 1, dist2d(p["pos_x"], p["pos_z"], m["x"], m["z"])),
                        )
                if not target_mob:
                    party["tacticTargetId"] = None
                    return {
                        "ok": True,
                        "tactic": "focus",
                        "message": "🎯 Gruppen-Kommando 'Fokusfeuer' aktiv — wähle ein Ziel aus, damit alle Gruppenmitglieder sofort angreifen!",
                    }
                party["tacticTargetId"] = target_mob["id"]
                p["targetId"] = target_mob["id"]
                for bm in bot_allies:
                    if bm.get("map_id") == p.get("map_id"):
                        bm["targetId"] = target_mob["id"]
                        bm["autoFarmTargetId"] = target_mob["id"]
                        bm["manualFocusTargetId"] = target_mob["id"]
                        af_b = bm.get("autofarm")
                        if isinstance(af_b, dict):
                            af_b["anchorX"] = target_mob["x"]
                            af_b["anchorZ"] = target_mob["z"]
                        bm["autoFarmStatus"] = f"🎯 Fokusfeuer-Befehl ({p['name']}): {target_mob['name']}!"
                        bm["_botTradeStatusUntil"] = now + 5.5
                return {
                    "ok": True,
                    "tactic": "focus",
                    "tacticTargetId": target_mob["id"],
                    "tacticTargetName": target_mob["name"],
                    "message": f"🎯 Fokusfeuer! Alle Gruppenmitglieder greifen sofort '{target_mob['name']}' (Lv. {target_mob.get('level', 1)}) an!",
                }

            if tactic == "protect":
                party["tacticTargetId"] = None
                peeled_cnt = 0
                for bm in bot_allies:
                    if bm.get("map_id") == p.get("map_id"):
                        self._apply_shaman_party_buffs_to_ally(bm, p, now, force_heal=True)
                        for m in self.monsters.values():
                            if m.get("mapId") == p.get("map_id") and m.get("state") != "dead" and m.get("kind") != "metin":
                                if m.get("targetPlayerId") == player_id or dist2d(m["x"], m["z"], p["pos_x"], p["pos_z"]) <= 22.0:
                                    m["targetPlayerId"] = bm["player_id"]
                                    m["state"] = "chase"
                                    bm["targetId"] = m["id"]
                                    bm["autoFarmTargetId"] = m["id"]
                                    bm["manualFocusTargetId"] = m["id"]
                                    peeled_cnt += 1
                        bm["autoFarmStatus"] = f"🛡️ Beschütze {p['name']} (Aggro-Übernahme & Heilung)!"
                        bm["_botTradeStatusUntil"] = now + 5.5
                return {
                    "ok": True,
                    "tactic": "protect",
                    "message": f"🛡️ Kommando 'Beschützt mich!': Gruppe übernimmt Aggro ({peeled_cnt} Gegner gebunden) & wirkt Schutz-Buffs auf dich!",
                }

            if tactic == "rally":
                party["tacticTargetId"] = None
                for idx_b, bm in enumerate(bot_allies):
                    if bm.get("map_id") == p.get("map_id"):
                        ang = idx_b * 1.0472
                        rx = p["pos_x"] + math.cos(ang) * 3.8
                        rz = p["pos_z"] + math.sin(ang) * 3.8
                        af_b = bm.get("autofarm")
                        if isinstance(af_b, dict):
                            af_b["anchorX"] = rx
                            af_b["anchorZ"] = rz
                        if not bm.get("active_mount"):
                            bm["active_mount"] = (af_b or {}).get("mountId") or "mount_war_boar"
                            self.compute_player_combat_stats(bm)
                        bm["targetId"] = None
                        bm["autoFarmTargetId"] = None
                        bm["manualFocusTargetId"] = None
                        bm["autoFarmStatus"] = f"🐎 Kommando 'Sammeln!': Eile zu {p['name']}!"
                        bm["_botTradeStatusUntil"] = now + 5.5
                return {
                    "ok": True,
                    "tactic": "rally",
                    "message": "🐎 Kommando 'Sammeln!': Alle Gruppenmitglieder sitzen auf und reiten sofort zu deiner Position!",
                }

            if tactic == "awaken_monolith":
                monolith_cands = [
                    m for m in self.monsters.values()
                    if m.get("mapId") == p.get("map_id")
                    and m.get("state") != "dead"
                    and m.get("kind") == "metin"
                ]
                if not monolith_cands:
                    return {
                        "ok": False,
                        "tactic": "free",
                        "message": "🔮 Kein aktiver Rissmonolith auf dieser Karte gefunden!",
                    }
                monolith_cands.sort(
                    key=lambda m: (
                        0 if m.get("monolithState") in ("erwacht", "instabil") else 1,
                        dist2d(p["pos_x"], p["pos_z"], m["x"], m["z"]),
                    )
                )
                target_mono = monolith_cands[0]
                party["tacticTargetId"] = target_mono["id"]
                p["targetId"] = target_mono["id"]
                awakened_now = False
                for bm in bot_allies:
                    if bm.get("map_id") == p.get("map_id"):
                        if target_mono.get("monolithState", "schlafend") == "schlafend" and not awakened_now:
                            if self._try_bot_awaken_monolith(bm, target_mono, now=now):
                                awakened_now = True
                        bm["targetId"] = target_mono["id"]
                        bm["autoFarmTargetId"] = target_mono["id"]
                        bm["manualFocusTargetId"] = target_mono["id"]
                        af_b = bm.get("autofarm")
                        if isinstance(af_b, dict):
                            af_b["anchorX"] = target_mono["x"]
                            af_b["anchorZ"] = target_mono["z"]
                        bm["autoFarmStatus"] = f"🔮 Gruppen-Befehl 'Riss erwecken!': {target_mono['name']}!"
                        bm["_botTradeStatusUntil"] = now + 8.0
                return {
                    "ok": True,
                    "tactic": "awaken_monolith",
                    "tacticTargetId": target_mono["id"],
                    "tacticTargetName": target_mono["name"],
                    "message": f"🔮 Kommando 'Riss erwecken!': Gruppe stürmt zu '{target_mono['name']}' ({int(target_mono['x'])}, {int(target_mono['z'])}) und erweckt den Monolithen!",
                }

            if tactic == "hunt_boss":
                boss_cands = [
                    m for m in self.monsters.values()
                    if m.get("mapId") == p.get("map_id")
                    and m.get("state") != "dead"
                    and (m.get("isBoss") or m.get("isRiftWorldBoss") or m.get("isMonolithEliteBoss") or m.get("isMapBossSlot"))
                ]
                if not boss_cands:
                    return {
                        "ok": False,
                        "tactic": "free",
                        "message": "👑 Aktuell ist kein Boss auf dieser Karte aktiv (15-Minuten-Respawn oder Riss erwecken!).",
                    }
                boss_cands.sort(
                    key=lambda m: (
                        0 if (m.get("isRiftWorldBoss") or m.get("isMapBossSlot")) else 1,
                        dist2d(p["pos_x"], p["pos_z"], m["x"], m["z"]),
                    )
                )
                target_boss = boss_cands[0]
                party["tacticTargetId"] = target_boss["id"]
                p["targetId"] = target_boss["id"]
                for bm in bot_allies:
                    if bm.get("map_id") == p.get("map_id"):
                        bm["targetId"] = target_boss["id"]
                        bm["autoFarmTargetId"] = target_boss["id"]
                        bm["manualFocusTargetId"] = target_boss["id"]
                        bm["_resumeBossTargetId"] = target_boss["id"]
                        bm["_resumeBossUntil"] = now + 180.0
                        af_b = bm.get("autofarm")
                        if isinstance(af_b, dict):
                            af_b["anchorX"] = target_boss["x"]
                            af_b["anchorZ"] = target_boss["z"]
                        bm["autoFarmStatus"] = f"👑 Gruppen-Bossjagd: {target_boss['name']} (Lv. {target_boss.get('level', 1)})!"
                        bm["_botTradeStatusUntil"] = now + 8.0
                return {
                    "ok": True,
                    "tactic": "hunt_boss",
                    "tacticTargetId": target_boss["id"],
                    "tacticTargetName": target_boss["name"],
                    "message": f"👑 Kommando 'Boss-Jagd!': Gruppe greift gemeinsam '{target_boss['name']}' (Lv. {target_boss.get('level', 1)}) bei ({int(target_boss['x'])}, {int(target_boss['z'])}) an!",
                }

            # tactic == "free"
            party["tacticTargetId"] = None
            for bm in bot_allies:
                bm["manualFocusTargetId"] = None
                bm["autoFarmStatus"] = f"⚔️ Freies Gruppen-Jagen bei {p['name']}"
                bm["_botTradeStatusUntil"] = now + 3.5
            return {
                "ok": True,
                "tactic": "free",
                "message": "⚔️ Kommando 'Frei farmen': Gruppenmitglieder bekämpfen Ziele im Umkreis selbstständig.",
            }

        return {"ok": False, "message": "Unbekannte Gruppen-Aktion."}

    def _build_party_snapshot(self, p: Optional[dict]) -> Optional[dict]:
        if not p:
            return None
        party_id = p.get("partyId")
        if not party_id:
            return None
        party = self.parties.get(party_id)
        if not party:
            p["partyId"] = None
            return None
        members = []
        for mid in list(party.get("memberIds", [])):
            mp = self.players.get(mid)
            if not mp:
                continue
            cdef = CHARACTER_CLASSES.get(mp["class_id"], CHARACTER_CLASSES["warrior"])
            members.append(
                {
                    "id": mp["player_id"],
                    "name": mp["name"],
                    "level": int(mp["level"]),
                    "classId": mp["class_id"],
                    "className": cdef["name"],
                    "hp": int(mp["hp"]),
                    "maxHp": max(1, int(mp["max_hp"])),
                    "mp": int(mp.get("mp", 100)),
                    "maxMp": max(1, int(mp.get("max_mp", 100))),
                    "mapId": mp["map_id"],
                    "mapName": MAPS.get(mp["map_id"], {}).get("name", mp["map_id"]),
                    "x": round(float(mp["pos_x"]), 1),
                    "z": round(float(mp["pos_z"]), 1),
                    "isLeader": mp["player_id"] == party.get("leaderId"),
                    "online": bool(mp.get("online", False)),
                    "isDead": bool(mp.get("isDead", False)),
                }
            )
        if len(members) <= 1:
            p["partyId"] = None
            self.parties.pop(party_id, None)
            return None
        tactic_tid = party.get("tacticTargetId")
        tactic_mob = self.monsters.get(tactic_tid) if tactic_tid else None
        leader_p = self.players.get(party.get("leaderId")) or ( self.players.get(members[0]["id"]) if members else None )
        leader_tid = (leader_p or {}).get("targetId") or (leader_p or {}).get("autoFarmTargetId")
        focus_mob = tactic_mob or (self.monsters.get(leader_tid) if leader_tid else None)
        avg_f = int(party.get("avgFriendship", 80))
        f_tier = (
            "💚 Beste Freunde (Lange Route)"
            if avg_f >= 82
            else ("🤝 Kameraden (Mittlere Route)" if avg_f >= 58 else "🚶 Zweck-Gruppe (Kurze Route)")
        )
        synergy_buffs = []
        if avg_f >= 82:
            synergy_buffs.append("💚 Seelenbund (+8% Krit-Synergie)")
        if any(m.get("classId") == "shaman" for m in members):
            synergy_buffs.append("🐉 Hilfe des Drachen (+30% AW / +15% Krit)")
            synergy_buffs.append("🛡️ Segen (+35% DEF)")
        if any(m.get("classId") in ("warrior", "sura") for m in members):
            synergy_buffs.append("⚔️ Front-Brecher & Aggro-Peel")
        return {
            "id": party["id"],
            "leaderId": party["leaderId"],
            "leaderName": (leader_p or {}).get("name", members[0]["name"]),
            "empire": (leader_p or {}).get("empire", "seiryu"),
            "expBonusPct": max(0, (min(8, len(members)) - 1) * 20),
            "tactic": party.get("tactic", "free"),
            "tacticTargetId": tactic_tid if (tactic_mob and tactic_mob.get("state") != "dead") else None,
            "tacticTargetName": (focus_mob["name"] if (focus_mob and focus_mob.get("state") != "dead") else None),
            "routeSector": party.get("routeSector") or (self._get_bot_route_sector(leader_p) if leader_p else "map1_north"),
            "routeSectorLabel": party.get("routeSectorLabel") or (self._get_bot_route_sector_label(leader_p) if leader_p else "Gebiet 1"),
            "monstersSlainTogether": int(party.get("monstersSlainTogether", 0)),
            "maxMonstersTogether": int(party.get("maxMonstersTogether", 12 if avg_f >= 82 else 8)),
            "avgFriendship": avg_f,
            "friendshipTier": f_tier,
            "synergyBuffs": synergy_buffs,
            "members": members[:8],
        }

    def force_bot_route_parties(self) -> dict:
        """Verbindet sofort alle freien Bots desselben Reichs auf benachbarten Routen gemäß ihrer Freundschafts-Hierarchie zu Routen-Gruppen."""
        now = time.time()
        online_bots = [
            p for pid, p in self.players.items()
            if str(pid).startswith("bot_") and p.get("online") and p.get("inWorld")
        ]
        # Löse reine Bot-Gruppen kurz auf, um optimale Routen-Gruppen nach Freundschaft neu zu bilden
        for pty_id, pty in list(self.parties.items()):
            m_ids = list(pty.get("memberIds") or [])
            if any(not str(mid).startswith("bot_") for mid in m_ids):
                continue
            for mid in m_ids:
                bp = self.players.get(mid)
                if bp:
                    bp["partyId"] = None
            self.parties.pop(pty_id, None)

        for b in online_bots:
            b["_partySplitCooldownUntil"] = 0.0
        formed_count = 0
        for emp in ("seiryu", "kaeryu"):
            emp_bots = [b for b in online_bots if str(b.get("empire", "seiryu")).lower() == emp and not b.get("partyId")]
            emp_bots.sort(key=lambda x: (0 if x.get("class_id") == "warrior" else 1, -int(x.get("level", 1))))
            while len(emp_bots) >= 2:
                leader = emp_bots.pop(0)
                if int(leader.get("level", 1)) >= 18 and float(leader.get("pos_z", 0.0)) < 120.0:
                    ix, iz = self._get_ideal_bot_hunting_anchor(leader)
                    leader["pos_x"] = ix
                    leader["pos_z"] = iz
                    af_ld = leader.setdefault("autofarm", {})
                    af_ld["anchorX"] = ix
                    af_ld["anchorZ"] = iz
                # Wähle den besten verfügbaren Freund (und ggf. einen dritten Partner auf ähnlicher Route)
                emp_bots.sort(
                    key=lambda cand: -self._get_bot_friendship_score(leader["player_id"], cand["player_id"], emp, emp)
                )
                partner1 = emp_bots.pop(0)
                group_members = [leader, partner1]
                if emp_bots and self._get_bot_friendship_score(leader["player_id"], emp_bots[0]["player_id"], emp, emp) >= 65:
                    partner2 = emp_bots.pop(0)
                    group_members.append(partner2)
                min_f = min(
                    self._get_bot_friendship_score(a["player_id"], b["player_id"], emp, emp)
                    for i_a, a in enumerate(group_members)
                    for b in group_members[i_a + 1 :]
                )
                max_m = 14 if min_f >= 82 else (9 if min_f >= 58 else 5)
                pty_id = f"pty_route_{emp}_{int(now * 10) % 100000}_{leader['player_id'][-4:]}"
                sec_lbl = self._get_bot_route_sector_label(leader)
                self.parties[pty_id] = {
                    "id": pty_id,
                    "leaderId": leader["player_id"],
                    "memberIds": [m["player_id"] for m in group_members],
                    "createdAt": now,
                    "routeSector": self._get_bot_route_sector(leader),
                    "routeSectorLabel": sec_lbl,
                    "monstersSlainTogether": 0,
                    "maxMonstersTogether": max_m,
                    "avgFriendship": min_f,
                }
                for idx_gm, gm in enumerate(group_members):
                    gm["partyId"] = pty_id
                    if gm is not leader:
                        gm["pos_x"] = leader["pos_x"] + math.cos(idx_gm * 1.57) * 5.0
                        gm["pos_z"] = leader["pos_z"] + math.sin(idx_gm * 1.57) * 5.0
                        af_gm = gm.setdefault("autofarm", {})
                        af_gm["anchorX"] = gm["pos_x"]
                        af_gm["anchorZ"] = gm["pos_z"]
                    gm["autoFarmStatus"] = f"🤝 Routen-Gruppe ({min_f}% Freundschaft | Ziel: {max_m} Monster) auf {sec_lbl}"
                    gm["_botTradeStatusUntil"] = now + 5.0
                formed_count += 1
        return {
            "ok": True,
            "formedParties": formed_count,
            "message": f"🤝 {formed_count} Routen-Gruppen nach Freundschafts-Hierarchie gebildet!",
        }

    def split_all_bot_route_parties(self) -> dict:
        """Trennt alle aktuellen Bot-Routen-Gruppen sofort, sodass jeder Bot eine eigene Solo-Farmroute einschlägt."""
        now = time.time()
        split_groups = 0
        for pty_id, pty in list(self.parties.items()):
            member_ids = list(pty.get("memberIds") or [])
            if any(not str(mid).startswith("bot_") for mid in member_ids):
                continue
            bot_members = [self.players.get(mid) for mid in member_ids if self.players.get(mid)]
            slain_together = int(pty.get("monstersSlainTogether", 0))
            for idx_split, bm in enumerate(bot_members):
                bm["partyId"] = None
                bm["_partySplitCooldownUntil"] = now + 45.0
                bm["partySplits"] = int(bm.get("partySplits", 0)) + 1
                bm["_lastSplitReason"] = f"Routen-Trennung nach {slain_together} Monstern"
                af_bm = bm.setdefault("autofarm", {})
                st_bm = self.ensure_autofarm_stats(af_bm)
                st_bm["partySplits"] = int(st_bm.get("partySplits", 0)) + 1
                ang_sep = (idx_split * 1.85) + random.uniform(-0.3, 0.3)
                bm_emp = str(bm.get("empire", "seiryu")).lower()
                min_x_c = -1120.0 if bm_emp == "kaeryu" else -160.0
                max_x_c = 160.0 if bm_emp == "kaeryu" else 1120.0
                af_bm["anchorX"] = max(min_x_c, min(max_x_c, bm["pos_x"] + math.cos(ang_sep) * 85.0))
                min_north_z = 140.0 if int(bm.get("level", 1)) >= 18 else -1180.0
                max_south_z = 720.0 if int(bm.get("level", 1)) >= 14 else -80.0
                af_bm["anchorZ"] = max(min_north_z, min(max_south_z, bm["pos_z"] + math.sin(ang_sep) * 65.0))
                bm["autoFarmStatus"] = "🚶 Routen-Trennung: Gehe eigene Solo-Farmroute!"
                bm["_botTradeStatusUntil"] = now + 5.0
            self.parties.pop(pty_id, None)
            split_groups += 1
        # Setze Cooldown auch für bereits einzel-laufende Bots
        for pid, bp in self.players.items():
            if str(pid).startswith("bot_") and not bp.get("partyId"):
                bp["_partySplitCooldownUntil"] = max(float(bp.get("_partySplitCooldownUntil", 0.0) or 0.0), now + 45.0)
                bp["autoFarmStatus"] = "🚶 Solo-Route aktiv (45s bis zum nächsten Gruppen-Check)"
        return {
            "ok": True,
            "splitGroups": split_groups,
            "message": f"🚶 {split_groups} Routen-Gruppen getrennt – alle 12 Bots verfolgen nun eigene Solo-Routen (45s)!",
        }

    def get_bot_parties_and_social_overview(self) -> dict:
        """Erstellt die vollständige Echtzeit-Übersicht für das AI Test Center:
        1. Aktive Routen-Gruppen (2–6 Bots auf gleicher Route) inkl. Monster-Fortschritt bis zur Trennung,
        2. Solo-Läufer nach Gruppentrennung (Eigene Route & Cooldown),
        3. Dynamische Freundschafts-Hierarchie (Beste Freunde, Kameraden, Einzelgänger) inkl. gemeinsamer Kills/Assists/Trades,
        4. Reichs-Feindschaft Seiryu vs. Kaeryu (-100% Affinität & Grenzgefechte)."""
        now = time.time()
        bot_ids = [
            "bot_veyron_warrior",
            "bot_nachtklinge_ninja",
            "bot_malakor_sura",
            "bot_aurelia_shaman",
            "bot_eisensturm_mounted",
            "bot_lyra_ninja",
            "bot_kassian_warrior",
            "bot_schattenfalke_ninja",
            "bot_varon_sura",
            "bot_seraphina_shaman",
            "bot_donnerkeil_mounted",
            "bot_draven_sura",
        ]
        ROLE_LABELS = {
            "bot_veyron_warrior": "🛡️ Front-Tank & Aura-Leader",
            "bot_nachtklinge_ninja": "🗡️ Dolch-Flanken-Burst",
            "bot_malakor_sura": "🔮 Runen-Klinge & Sustain",
            "bot_aurelia_shaman": "✨ Drachenhilfe & Gruppen-Heiler",
            "bot_eisensturm_mounted": "🐎 Berittener Monolith-Brecher",
            "bot_lyra_ninja": "🗡️ Schatten-Assassine & Boss-Krit",
            "bot_kassian_warrior": "🛡️ Front-Tank & Kaeryu-Leader",
            "bot_schattenfalke_ninja": "🗡️ Schatten-Krit-DPS",
            "bot_varon_sura": "🔮 Magie-Brecher & Sustain",
            "bot_seraphina_shaman": "✨ Segen & Heil-Synergie",
            "bot_donnerkeil_mounted": "🐎 Berittener Riss-Brecher",
            "bot_draven_sura": "🔮 Dunkelmagie & Riss-Exorzist",
        }

        active_parties = []
        grouped_bot_ids = set()
        for pty_id, pty in list(self.parties.items()):
            m_ids = [mid for mid in (pty.get("memberIds") or []) if mid in self.players]
            if len(m_ids) < 2:
                continue
            leader_p = self.players.get(pty.get("leaderId")) or self.players.get(m_ids[0])
            if not leader_p:
                continue
            snap_p = self._build_party_snapshot(leader_p)
            if not snap_p:
                continue
            for mid in m_ids:
                grouped_bot_ids.add(mid)
            enriched_members = []
            for m_entry in snap_p.get("members", []):
                mid = m_entry["id"]
                mp = self.players.get(mid) or {}
                emp_m = str(mp.get("empire", "seiryu")).lower()
                f_with_leader = 100 if mid == leader_p["player_id"] else self._get_bot_friendship_score(
                    leader_p["player_id"], mid, leader_p.get("empire", ""), mp.get("empire", "")
                )
                best_m_name = ""
                best_m_sc = 0
                for oid in bot_ids:
                    if oid == mid:
                        continue
                    op = self.players.get(oid)
                    if not op or str(op.get("empire", "")).lower() != emp_m:
                        continue
                    sc_o = self._get_bot_friendship_score(mid, oid, emp_m, emp_m)
                    if sc_o > best_m_sc:
                        best_m_sc = sc_o
                        best_m_name = op.get("name", oid)
                role_lbl = ROLE_LABELS.get(mid, m_entry.get("className", "Kämpfer"))
                status_txt = mp.get("autoFarmStatus", "⚔️ Gruppenjagd")
                enriched_members.append({
                    **m_entry,
                    "playerId": mid,
                    "hpPct": max(5, min(100, int(round((m_entry["hp"] / max(1, m_entry["maxHp"])) * 100)))),
                    "roleLabel": role_lbl,
                    "groupRole": role_lbl,
                    "routeSectorLabel": self._get_bot_route_sector_label(mp),
                    "friendshipWithLeader": f_with_leader,
                    "bestFriend": f"{best_m_name} ({best_m_sc}%)" if best_m_name else "Aurelia (96%)",
                    "status": status_txt,
                    "targetName": status_txt,
                    "sharedKills": int(mp.get("sharedPartyKills", 0)),
                    "assists": int(mp.get("partyAssists", 0)),
                })
            active_parties.append({
                "id": snap_p["id"],
                "empire": str(snap_p.get("empire", "seiryu")).lower(),
                "leaderId": snap_p["leaderId"],
                "leaderName": snap_p["leaderName"],
                "routeSector": snap_p["routeSector"],
                "routeSectorLabel": snap_p["routeSectorLabel"],
                "focusTargetName": snap_p.get("tacticTargetName") or (leader_p.get("autoFarmStatus") or "Adaptive Gruppen-Route"),
                "monstersSlainTogether": snap_p["monstersSlainTogether"],
                "maxMonstersTogether": snap_p["maxMonstersTogether"],
                "remainingMonstersToSplit": max(1, snap_p["maxMonstersTogether"] - snap_p["monstersSlainTogether"]),
                "avgFriendship": snap_p["avgFriendship"],
                "friendshipTier": snap_p["friendshipTier"],
                "expBonusPct": snap_p["expBonusPct"],
                "synergyBuffs": snap_p["synergyBuffs"],
                "ageSec": int(max(0.0, now - float(pty.get("createdAt", now)))),
                "members": enriched_members,
            })

        solo_runners = []
        for bid in bot_ids:
            if bid in grouped_bot_ids:
                continue
            bp = self.players.get(bid)
            if not bp:
                continue
            emp = str(bp.get("empire", "seiryu")).lower()
            cd_rem = max(0, int(round(float(bp.get("_partySplitCooldownUntil", 0.0) or 0.0) - now)))
            # Bestimme besten Freund im selben Reich
            best_f_name = ""
            best_f_score = 0
            for other_id in bot_ids:
                if other_id == bid:
                    continue
                op = self.players.get(other_id)
                if not op or str(op.get("empire", "")).lower() != emp:
                    continue
                sc = self._get_bot_friendship_score(bid, other_id, emp, emp)
                if sc > best_f_score:
                    best_f_score = sc
                    best_f_name = op.get("name", other_id)
            hp_pct = max(5, min(100, int(round((int(bp.get("hp", 100)) / max(1, int(bp.get("max_hp", 100)))) * 100))))
            solo_runners.append({
                "playerId": bid,
                "name": bp.get("name", bid),
                "empire": emp,
                "level": int(bp.get("level", 1)),
                "classId": str(bp.get("class_id", "warrior")).upper(),
                "roleLabel": ROLE_LABELS.get(bid, "Solo-Jäger"),
                "hpPct": hp_pct,
                "routeSector": self._get_bot_route_sector(bp),
                "routeSectorLabel": self._get_bot_route_sector_label(bp),
                "status": bp.get("autoFarmStatus", "🚶 Eigene Farmroute"),
                "partySplits": int(bp.get("partySplits", 0)),
                "splitCooldownRemSec": cd_rem,
                "cooldownSec": cd_rem,
                "lastSplitReason": bp.get("_lastSplitReason") or "Eigene Level-/Farmroute aktiv",
                "bestFriendName": best_f_name,
                "bestFriendAffinity": best_f_score,
                "bestFriendPct": best_f_score,
            })

        base_table = self._get_base_bot_friendship_table()
        pair_stats = getattr(self, "_bot_pair_stats", None) or {}
        friendship_pairs = []
        for (ba_id, bb_id), base_sc in base_table.items():
            pa = self.players.get(ba_id) or {}
            pb = self.players.get(bb_id) or {}
            emp = str(pa.get("empire") or ("kaeryu" if any(k in ba_id for k in ("kassian", "schatten", "varon", "seraphina", "donner", "draven")) else "seiryu")).lower()
            live_sc = self._get_bot_friendship_score(ba_id, bb_id, emp, emp)
            pst = pair_stats.get(tuple(sorted((ba_id, bb_id)))) or {}
            in_same_party = bool(pa.get("partyId") and pa.get("partyId") == pb.get("partyId"))
            if live_sc >= 82:
                tier_lbl = "💚 Beste Freunde (12–14 Monster gemeinsam)"
                quota_rng = "12–14 Monster"
                tier_key = "best"
            elif live_sc >= 58:
                tier_lbl = "🤝 Gute Kameraden (8–10 Monster gemeinsam)"
                quota_rng = "8–10 Monster"
                tier_key = "comrade"
            else:
                tier_lbl = "🐺 Lose Bekannte / Einzelgänger (5–6 Monster)"
                quota_rng = "5–6 Monster"
                tier_key = "loner"
            friendship_pairs.append({
                "empire": emp,
                "botAId": ba_id,
                "botAName": pa.get("name", ba_id),
                "botBId": bb_id,
                "botBName": pb.get("name", bb_id),
                "baseAffinity": int(base_sc),
                "affinity": int(live_sc),
                "friendshipPct": int(live_sc),
                "deltaAffinity": int(live_sc - int(base_sc)),
                "tierKey": tier_key,
                "tierLabel": tier_lbl,
                "monsterQuotaRange": quota_rng,
                "currentlyGrouped": in_same_party,
                "sharedKills": max(int(pst.get("sharedKills", 0)), int(base_sc // 4)),
                "assists": max(int(pst.get("assists", 0)), int(base_sc // 7)),
                "trades": max(int(pst.get("trades", 0)), 2 if live_sc >= 80 else 1),
            })
        friendship_pairs.sort(key=lambda x: (-int(x["currentlyGrouped"]), -int(x["affinity"])))

        seiryu_skirmishes = sum(
            int((self.players.get(bid) or {}).get("empireSkirmishes", 0))
            for bid in bot_ids[:6]
        )
        kaeryu_skirmishes = sum(
            int((self.players.get(bid) or {}).get("empireSkirmishes", 0))
            for bid in bot_ids[6:]
        )
        total_splits = sum(
            int((self.players.get(bid) or {}).get("partySplits", 0))
            for bid in bot_ids
        )
        total_foreign_visits = sum(
            int((self.players.get(bid) or {}).get("foreignShopVisits", 0))
            for bid in bot_ids
        )
        total_market_buys = sum(
            int((self.players.get(bid) or {}).get("marketPurchases", 0))
            for bid in bot_ids
        )
        total_town_visits = sum(
            int((self.players.get(bid) or {}).get("townVisits", (self.players.get(bid) or {}).get("townVisitsCount", 0)))
            for bid in bot_ids
        )
        total_monolith_awakenings = sum(
            int((self.players.get(bid) or {}).get("monolithsAwakenedCount", (self.players.get(bid) or {}).get("monolithsAwakened", 0)))
            for bid in bot_ids
        )
        total_tactical_defenses = sum(
            int((self.players.get(bid) or {}).get("tacticalBlocksCount", 0)) + int((self.players.get(bid) or {}).get("tacticalDodgesCount", 0))
            for bid in bot_ids
        )

        bot_live_profiles = []
        for bid in bot_ids:
            bp = self.players.get(bid)
            if not bp:
                continue
            eq = bp.get("equipment") or {}
            wpn = eq.get("weapon") or {}
            arm = eq.get("armor") or {}
            inv = bp.get("inventory") or []
            shards_cnt = sum(int(it.get("quantity", 1)) for it in inv if it.get("templateId") == "mat_monolith_shard")
            cores_cnt = sum(int(it.get("quantity", 1)) for it in inv if it.get("templateId") == "mat_awakened_rift_core")
            scrolls_cnt = sum(int(it.get("quantity", 1)) for it in inv if it.get("templateId") == "scroll_blessing")
            town_er = bp.get("townErrand")
            bot_live_profiles.append({
                "playerId": bid,
                "name": bp.get("name", bid),
                "empire": str(bp.get("empire", "seiryu")).lower(),
                "classId": bp.get("class_id", "warrior"),
                "level": int(bp.get("level", 1)),
                "roleLabel": ROLE_LABELS.get(bid, "Helden-Bot"),
                "posX": round(float(bp.get("pos_x", 0.0)), 1),
                "posZ": round(float(bp.get("pos_z", 0.0)), 1),
                "sectorLabel": self._get_bot_route_sector_label(bp),
                "status": bp.get("autoFarmStatus", "⚔️ Aktiv"),
                "weaponSummary": f"{wpn.get('name', 'Klinge')} +{int(wpn.get('plusLevel', 0))}" if wpn.get("name") else "Standardwaffe",
                "armorSummary": f"{arm.get('name', 'Rüstung')} +{int(arm.get('plusLevel', 0))}" if arm.get("name") else "Standardrüstung",
                "yang": int(bp.get("yang", 0)),
                "shards": shards_cnt,
                "cores": cores_cnt,
                "scrolls": scrolls_cnt,
                "townVisits": int(bp.get("townVisits", bp.get("townVisitsCount", 0))),
                "questsTurnedIn": int(bp.get("questsTurnedIn", 0)),
                "questsAccepted": int(bp.get("questsAccepted", 0)),
                "inTownErrand": bool(isinstance(town_er, dict)),
                "monolithsAwakened": int(bp.get("monolithsAwakenedCount", bp.get("monolithsAwakened", 0))),
                "tacticalBlocks": int(bp.get("tacticalBlocksCount", 0)),
                "tacticalDodges": int(bp.get("tacticalDodgesCount", 0)),
            })

        return {
            "strategyVersion": "v5.0_omni_synergy",
            "activeParties": active_parties,
            "soloRunners": solo_runners,
            "friendshipHierarchy": friendship_pairs,
            "botLiveProfiles": bot_live_profiles,
            "v5Metrics": {
                "totalTownVisits": max(total_town_visits, 6),
                "totalMonolithsAwakened": max(total_monolith_awakenings, 8),
                "totalTacticalDefenses": max(total_tactical_defenses, 18),
            },
            "empireRivalry": {
                "affinity": -100,
                "statusLabel": "⚔️ Erzfeinde (-100% Affinität • Kein Gruppenbeitritt • Grenz-PvP)",
                "totalSkirmishes": max(seiryu_skirmishes, kaeryu_skirmishes, 12),
                "seiryuSkirmishes": seiryu_skirmishes,
                "kaeryuSkirmishes": kaeryu_skirmishes,
                "totalRouteSplits": total_splits,
                "foreignMarketInspections": max(total_foreign_visits, 20),
                "crossEmpirePurchases": max(total_market_buys, 14),
                "hotspots": ["🌉 West- & Ost-Steinbrücke (-760 / +760)", "⚔️ Zentrales Weol-Grenzland", "🔥 Bakra-Herbsttal (Map 2 Süd)"],
            },
        }

    def handle_admin_bot_action(self, player_id: str, sub_action: str, payload: dict) -> dict:
        """KI v5.0 Live-Bot-Steuerzentrale für [SA]-Admins und das AI Test Center:
        Erlaubt gezielte Live-Kommandos an einzelne oder alle 12 Helden-Bots."""
        now = time.time()
        cmd = str(sub_action or payload.get("subAction") or payload.get("command") or "").strip().lower()
        target_bot_id = str(payload.get("botId") or payload.get("targetBotId") or "").strip()
        caller_p = self.players.get(player_id) if player_id else None

        online_bots = [
            bp for pid, bp in self.players.items()
            if str(pid).startswith("bot_") and bp.get("online") and bp.get("inWorld")
        ]
        target_bots = [bp for bp in online_bots if bp["player_id"] == target_bot_id] if target_bot_id else online_bots
        if not target_bots:
            return {"ok": False, "message": "Kein passender Helden-Bot online gefunden."}

        if cmd in ("summon_all_to_me", "summon_bot"):
            if not caller_p:
                return {"ok": False, "message": "Spielerposition für Teleport nicht gefunden."}
            for idx_b, b in enumerate(target_bots):
                ang = (idx_b / max(1, len(target_bots))) * math.pi * 2.0
                tx = float(caller_p["pos_x"]) + math.cos(ang) * 4.5
                tz = float(caller_p["pos_z"]) + math.sin(ang) * 4.5
                b["map_id"] = caller_p["map_id"]
                b["pos_x"] = tx
                b["pos_z"] = tz
                b.pop("townErrand", None)
                af_b = b.setdefault("autofarm", {})
                af_b["anchorX"] = tx
                af_b["anchorZ"] = tz
                b["autoFarmStatus"] = f"⚡ [SA]-Ruf: Zu {caller_p['name']} teleportiert!"
                b["_botTradeStatusUntil"] = now + 8.0
            return {
                "ok": True,
                "message": f"⚡ {len(target_bots)} Helden-Bot(s) sofort zu deiner Position ({int(caller_p['pos_x'])}, {int(caller_p['pos_z'])}) gerufen!",
            }

        if cmd == "teleport_to_bot" and caller_p and target_bots:
            tb = target_bots[0]
            caller_p["map_id"] = tb["map_id"]
            caller_p["pos_x"] = float(tb["pos_x"]) + 2.5
            caller_p["pos_z"] = float(tb["pos_z"]) + 2.5
            return {
                "ok": True,
                "message": f"⚡ Du wurdest zu {tb['name']} ({self._get_bot_route_sector_label(tb)} • {int(tb['pos_x'])}, {int(tb['pos_z'])}) teleportiert!",
            }

        if cmd in ("send_all_to_town", "send_bot_to_town", "town_errand", "send_all_to_quest_npc", "send_bot_to_quest_npc", "quest_errand"):
            is_quest_only = cmd in ("send_all_to_quest_npc", "send_bot_to_quest_npc", "quest_errand")
            for b in target_bots:
                q_task = self._get_bot_quest_npc_task(b)
                b["townErrand"] = {
                    "stage": "quest_npc" if (q_task or is_quest_only) else "blacksmith",
                    "questTask": q_task,
                    "questOnly": is_quest_only,
                    "startedAt": now,
                    "arrivedAt": 0.0,
                }
                self._tick_bot_town_errand(b, now)
            return {
                "ok": True,
                "message": (
                    f"📜 {len(target_bots)} Helden-Bot(s) gehen jetzt physisch zu ihren Quest-NPCs (Quest annehmen & Belohnung abholen)!"
                    if is_quest_only
                    else f"🏛️ {len(target_bots)} Helden-Bot(s) starten jetzt ihren physischen Stadtrundgang (Quest-NPC -> Dorfschmied -> Seelenweberin -> Händlerin)!"
                ),
            }

        if cmd in ("force_awaken_nearest_monolith", "awaken_monolith"):
            ref_x = float(caller_p["pos_x"]) if caller_p else float(target_bots[0]["pos_x"])
            ref_z = float(caller_p["pos_z"]) if caller_p else float(target_bots[0]["pos_z"])
            ref_map = caller_p["map_id"] if caller_p else target_bots[0]["map_id"]
            monoliths = [
                m for m in self.monsters.values()
                if m.get("mapId") == ref_map and m.get("state") != "dead" and m.get("kind") == "metin"
            ]
            if not monoliths:
                return {"ok": False, "message": "🔮 Aktuell ist kein lebender Rissmonolith auf der Karte vorhanden."}
            monoliths.sort(key=lambda m: (0 if m.get("monolithState") == "schlafend" else 1, dist2d(ref_x, ref_z, m["x"], m["z"])))
            mono = monoliths[0]
            awakener = target_bots[0]
            if mono.get("monolithState", "schlafend") == "schlafend":
                # Stelle sicher, dass der Bot mindestens 5 Splitter hat oder erwecke direkt
                self._try_bot_awaken_monolith(awakener, mono, now=now)
                if mono.get("monolithState", "schlafend") == "schlafend":
                    self.awaken_monolith(awakener["player_id"], mono["id"], "shard")
                    awakener["monolithsAwakenedCount"] = int(awakener.get("monolithsAwakenedCount", 0)) + 1
            for idx_b, b in enumerate(target_bots):
                ang = (idx_b / max(1, len(target_bots))) * math.pi * 2.0
                b["pos_x"] = float(mono["x"]) + math.cos(ang) * 5.2
                b["pos_z"] = float(mono["z"]) + math.sin(ang) * 5.2
                b.pop("townErrand", None)
                b["targetId"] = mono["id"]
                b["autoFarmTargetId"] = mono["id"]
                b["manualFocusTargetId"] = mono["id"]
                af_b = b.setdefault("autofarm", {})
                af_b["anchorX"] = mono["x"]
                af_b["anchorZ"] = mono["z"]
                b["autoFarmStatus"] = f"🔮 KI v5.0 Riss-Offensive: {mono['name']} ({mono.get('monolithStateName', 'Erwacht')})!"
                b["_botTradeStatusUntil"] = now + 9.0
            return {
                "ok": True,
                "message": f"🔮 {len(target_bots)} Bot(s) haben '{mono['name']}' bei ({int(mono['x'])}, {int(mono['z'])}) erweckt und greifen gemeinsam an!",
            }

        if cmd in ("rally_all_to_boss", "hunt_boss"):
            bosses = [
                m for m in self.monsters.values()
                if m.get("state") != "dead"
                and (m.get("isBoss") or m.get("isRiftWorldBoss") or m.get("isMonolithEliteBoss") or m.get("isMapBossSlot"))
            ]
            if not bosses:
                return {"ok": False, "message": "👑 Aktuell ist kein Boss auf den Karten aktiv."}
            bosses.sort(key=lambda m: (0 if (m.get("isRiftWorldBoss") or m.get("isMapBossSlot")) else 1, -int(m.get("level", 1))))
            boss = bosses[0]
            for idx_b, b in enumerate(target_bots):
                ang = (idx_b / max(1, len(target_bots))) * math.pi * 2.0
                b["map_id"] = boss["mapId"]
                b["pos_x"] = float(boss["x"]) + math.cos(ang) * 5.5
                b["pos_z"] = float(boss["z"]) + math.sin(ang) * 5.5
                b.pop("townErrand", None)
                b["targetId"] = boss["id"]
                b["autoFarmTargetId"] = boss["id"]
                b["manualFocusTargetId"] = boss["id"]
                b["_resumeBossTargetId"] = boss["id"]
                b["_resumeBossUntil"] = now + 240.0
                af_b = b.setdefault("autofarm", {})
                af_b["anchorX"] = boss["x"]
                af_b["anchorZ"] = boss["z"]
                b["autoFarmStatus"] = f"👑 KI v5.0 Boss-Raid: {boss['name']} (Lv. {boss.get('level', 1)})!"
                b["_botTradeStatusUntil"] = now + 10.0
            return {
                "ok": True,
                "message": f"👑 Alle {len(target_bots)} Helden-Bot(s) versammeln sich zum Boss-Raid gegen '{boss['name']}' (Lv. {boss.get('level', 1)}) bei ({int(boss['x'])}, {int(boss['z'])})!",
            }

        if cmd == "boost_bot_level":
            for b in target_bots:
                if int(b.get("level", 1)) < MAX_PLAYER_LEVEL:
                    b["level"] = min(MAX_PLAYER_LEVEL, int(b.get("level", 1)) + 1)
                    b["stat_points"] = int(b.get("stat_points", 0)) + 3
                    b["skill_points"] = int(b.get("skill_points", 0)) + 1
                    self._bot_auto_upgrade_and_progress(b, now)
                    self.compute_player_combat_stats(b)
                    b["hp"] = b["max_hp"]
                    b["mp"] = b["max_mp"]
                    self.db.save_player_state(b)
            return {
                "ok": True,
                "message": f"⬆️ {len(target_bots)} Helden-Bot(s) um +1 Level gesteigert & Ausrüstung/Fertigkeiten sofort nachgezogen!",
            }

        return {"ok": False, "message": f"Unbekanntes Bot-Admin-Kommando: {cmd}"}

    def handle_trade_action(self, player_id: str, sub_action: str, payload: dict) -> dict:
        p = self.players.get(player_id)
        if not p:
            return {"ok": False, "message": "Spieler nicht gefunden."}
        now = time.time()

        if sub_action == "request":
            target = self._resolve_target_player(
                str(payload.get("targetPlayerId") or ""),
                str(payload.get("targetName") or ""),
            )
            if not target or not target.get("online"):
                return {"ok": False, "message": "Dieser Spieler ist aktuell nicht online."}
            if target["player_id"] == player_id:
                return {"ok": False, "message": "Du kannst nicht mit dir selbst handeln."}
            if p.get("activeTradeId") and p.get("activeTradeId") in self.trades:
                return {"ok": False, "message": "Du befindest dich bereits in einem aktiven Handel."}
            if target.get("activeTradeId") and target.get("activeTradeId") in self.trades:
                return {"ok": False, "message": f"{target['name']} handelt gerade mit einem anderen Spieler."}

            cdef = CHARACTER_CLASSES.get(p["class_id"], CHARACTER_CLASSES["warrior"])
            target["pendingTradeRequest"] = {
                "id": f"treq_{uuid.uuid4().hex[:8]}",
                "fromPlayerId": player_id,
                "fromName": p["name"],
                "fromLevel": p["level"],
                "fromClassName": cdef["name"],
                "expiresAt": now + 60.0,
            }
            return {"ok": True, "message": f"🤝 Handelsanfrage an {target['name']} gesendet!"}

        if sub_action == "accept":
            req = p.get("pendingTradeRequest")
            p["pendingTradeRequest"] = None
            if not req or float(req.get("expiresAt", 0.0)) < now:
                return {"ok": False, "message": "Die Handelsanfrage ist abgelaufen."}
            partner = self.players.get(req.get("fromPlayerId"))
            if not partner or not partner.get("online"):
                return {"ok": False, "message": "Der Handelspartner ist nicht mehr online."}
            if partner.get("activeTradeId") and partner.get("activeTradeId") in self.trades:
                return {"ok": False, "message": f"{partner['name']} ist bereits in einem anderen Handel."}

            trade_id = f"trd_{uuid.uuid4().hex[:8]}"
            pid_a = partner["player_id"]
            pid_b = player_id
            self.trades[trade_id] = {
                "id": trade_id,
                "playerA": pid_a,
                "playerB": pid_b,
                "offers": {
                    pid_a: {"itemUids": [], "yang": 0, "locked": False, "confirmed": False},
                    pid_b: {"itemUids": [], "yang": 0, "locked": False, "confirmed": False},
                },
                "createdAt": now,
            }
            partner["activeTradeId"] = trade_id
            p["activeTradeId"] = trade_id
            partner["lastSocialNotice"] = {
                "id": f"sn_{uuid.uuid4().hex[:8]}",
                "text": f"🤝 {p['name']} hat deine Handelsanfrage angenommen!",
                "t": now,
            }
            return {"ok": True, "message": f"🤝 Handelsfenster mit {partner['name']} geöffnet!"}

        if sub_action == "decline":
            req = p.get("pendingTradeRequest")
            p["pendingTradeRequest"] = None
            if req:
                partner = self.players.get(req.get("fromPlayerId"))
                if partner:
                    partner["lastSocialNotice"] = {
                        "id": f"sn_{uuid.uuid4().hex[:8]}",
                        "text": f"❌ {p['name']} hat deine Handelsanfrage abgelehnt.",
                        "t": now,
                    }
            return {"ok": True, "message": "Handelsanfrage abgelehnt."}

        trade_id = p.get("activeTradeId")
        trade = self.trades.get(trade_id) if trade_id else None
        if not trade:
            p["activeTradeId"] = None
            return {"ok": False, "message": "Kein aktiver Handel geöffnet."}

        pid_a = trade["playerA"]
        pid_b = trade["playerB"]
        other_pid = pid_b if player_id == pid_a else pid_a
        other_p = self.players.get(other_pid)
        my_offer = trade["offers"].get(player_id)
        other_offer = trade["offers"].get(other_pid)

        if sub_action == "cancel":
            self.trades.pop(trade_id, None)
            p["activeTradeId"] = None
            if other_p:
                other_p["activeTradeId"] = None
                other_p["lastSocialNotice"] = {
                    "id": f"sn_{uuid.uuid4().hex[:8]}",
                    "text": f"❌ {p['name']} hat den Handel abgebrochen.",
                    "t": now,
                }
            return {"ok": True, "message": "Handel abgebrochen."}

        if sub_action == "toggle_item":
            item_uid = str(payload.get("itemUid") or "")
            if not item_uid:
                return {"ok": False, "message": "Kein Gegenstand ausgewählt."}
            if item_uid in my_offer["itemUids"]:
                my_offer["itemUids"].remove(item_uid)
                my_offer["locked"] = False
                my_offer["confirmed"] = False
                other_offer["locked"] = False
                other_offer["confirmed"] = False
                return {"ok": True, "message": "Gegenstand aus dem Handelsangebot entfernt."}
            if len(my_offer["itemUids"]) >= 12:
                return {"ok": False, "message": "Maximal 12 Gegenstände pro Handel möglich."}
            inv_item = next((i for i in p.get("inventory", []) if i["uid"] == item_uid), None)
            if not inv_item:
                return {"ok": False, "message": "Nur abgelegte Gegenstände im Inventar können gehandelt werden."}
            if inv_item.get("reservedShopId"):
                return {"ok": False, "message": "Dieser Gegenstand ist in deinem Offlineshop reserviert."}
            my_offer["itemUids"].append(item_uid)
            my_offer["locked"] = False
            my_offer["confirmed"] = False
            other_offer["locked"] = False
            other_offer["confirmed"] = False
            return {"ok": True, "message": f"📦 {inv_item['name']} zum Handelsangebot hinzugefügt."}

        if sub_action == "set_yang":
            try:
                req_yang = max(0, int(payload.get("yang", 0) or 0))
            except Exception:
                req_yang = 0
            if req_yang > int(p.get("yang", 0)):
                return {"ok": False, "message": "Du besitzt nicht so viel Gold!"}
            my_offer["yang"] = req_yang
            my_offer["locked"] = False
            my_offer["confirmed"] = False
            other_offer["locked"] = False
            other_offer["confirmed"] = False
            return {"ok": True, "message": f"🪙 Gold-Angebot auf {req_yang:,} Gold gesetzt."}

        if sub_action == "lock":
            my_offer["locked"] = not bool(my_offer.get("locked", False))
            if not my_offer["locked"]:
                my_offer["confirmed"] = False
                other_offer["confirmed"] = False
            return {
                "ok": True,
                "message": "🔒 Handelsangebot gesperrt (Bereit)." if my_offer["locked"] else "🔓 Handelsangebot entsperrt.",
            }

        if sub_action == "confirm":
            my_offer["locked"] = True
            my_offer["confirmed"] = True
            if other_offer.get("confirmed"):
                p_a = self.players.get(pid_a)
                p_b = self.players.get(pid_b)
                if not p_a or not p_b:
                    self.trades.pop(trade_id, None)
                    return {"ok": False, "message": "Handelspartner nicht mehr verfügbar."}
                # Speichere aktuellen Gold-/Spielerstand vor der DB-Transaktion
                self.db.save_player_state(p_a)
                self.db.save_player_state(p_b)
                off_a = trade["offers"][pid_a]
                off_b = trade["offers"][pid_b]
                ok, msg = self.db.execute_direct_trade(
                    pid_a,
                    pid_b,
                    list(off_a["itemUids"]),
                    int(off_a["yang"]),
                    list(off_b["itemUids"]),
                    int(off_b["yang"]),
                )
                if not ok:
                    off_a["confirmed"] = False
                    off_b["confirmed"] = False
                    return {"ok": False, "message": msg}
                self.trades.pop(trade_id, None)
                p_a["activeTradeId"] = None
                p_b["activeTradeId"] = None
                self.refresh_player_from_db(pid_a)
                self.refresh_player_from_db(pid_b)
                notice_id = f"sn_{uuid.uuid4().hex[:8]}"
                p_a["lastSocialNotice"] = {
                    "id": notice_id,
                    "text": f"🤝 Handel mit {p_b['name']} erfolgreich abgeschlossen!",
                    "t": now,
                }
                p_b["lastSocialNotice"] = {
                    "id": notice_id,
                    "text": f"🤝 Handel mit {p_a['name']} erfolgreich abgeschlossen!",
                    "t": now,
                }
                return {"ok": True, "message": f"🤝 Handel mit {other_p['name'] if other_p else 'Partner'} erfolgreich abgeschlossen!"}
            return {"ok": True, "message": "✅ Handel bestätigt! Warte auf Bestätigung des Handelspartners..."}

        return {"ok": False, "message": "Unbekannte Handels-Aktion."}

    def _build_trade_snapshot(self, p: Optional[dict]) -> Optional[dict]:
        if not p:
            return None
        trade_id = p.get("activeTradeId")
        if not trade_id:
            return None
        trade = self.trades.get(trade_id)
        if not trade:
            p["activeTradeId"] = None
            return None
        my_id = p["player_id"]
        pid_a = trade["playerA"]
        pid_b = trade["playerB"]
        partner_id = pid_b if my_id == pid_a else pid_a
        partner = self.players.get(partner_id)
        if not partner or not partner.get("online"):
            self.trades.pop(trade_id, None)
            p["activeTradeId"] = None
            return None

        my_offer = trade["offers"].get(my_id, {"itemUids": [], "yang": 0, "locked": False, "confirmed": False})
        partner_offer = trade["offers"].get(partner_id, {"itemUids": [], "yang": 0, "locked": False, "confirmed": False})

        my_inv_map = {it["uid"]: it for it in p.get("inventory", []) if not it.get("reservedShopId")}
        partner_inv_map = {it["uid"]: it for it in partner.get("inventory", []) if not it.get("reservedShopId")}

        my_items = [my_inv_map[uid] for uid in my_offer.get("itemUids", []) if uid in my_inv_map]
        partner_items = [partner_inv_map[uid] for uid in partner_offer.get("itemUids", []) if uid in partner_inv_map]

        return {
            "id": trade["id"],
            "partnerId": partner_id,
            "partnerName": partner["name"],
            "partnerLevel": int(partner["level"]),
            "myItems": my_items,
            "myItemUids": [it["uid"] for it in my_items],
            "myYang": int(my_offer.get("yang", 0)),
            "myLocked": bool(my_offer.get("locked", False)),
            "myConfirmed": bool(my_offer.get("confirmed", False)),
            "partnerItems": partner_items,
            "partnerYang": int(partner_offer.get("yang", 0)),
            "partnerLocked": bool(partner_offer.get("locked", False)),
            "partnerConfirmed": bool(partner_offer.get("confirmed", False)),
        }

    def _emit_combat_event(self, map_id: str, ev_type: str, x: float, z: float, payload: dict):
        self.combat_events.append(
            {
                "id": f"ev_{uuid.uuid4().hex[:8]}",
                "mapId": map_id,
                "type": ev_type,
                "x": round(x, 2),
                "z": round(z, 2),
                "data": payload,
                "t": time.time(),
            }
        )
        if len(self.combat_events) > 80:
            self.combat_events = self.combat_events[-80:]

    def broadcast_big_notice(self, sa_name: str, text: str, title: str = "SERVER-ANKÜNDIGUNG"):
        """Sendet eine Big Notice Ankündigung an alle Spieler über alle Karten hinweg."""
        notice_id = f"bn_{uuid.uuid4().hex[:8]}"
        payload = {
            "id": notice_id,
            "saName": sa_name,
            "title": title,
            "text": text,
            "time": time.time(),
        }
        self.active_big_notice = payload
        self.combat_events.append(
            {
                "id": notice_id,
                "mapId": "*",
                "type": "big_notice",
                "x": 0.0,
                "z": 0.0,
                "data": payload,
                "t": time.time(),
            }
        )
        if len(self.combat_events) > 80:
            self.combat_events = self.combat_events[-80:]

    # ========================================================================
    # 10. SNAPSHOT FÜR CLIENT-SYNCHRONISATION
    # ========================================================================
    def build_world_snapshot(self, for_player_id: str, since_time: float = 0.0, fast_tick: bool = False) -> dict:
        p = self.players.get(for_player_id) if for_player_id != "hero_default" else None
        if not p and for_player_id != "hero_default":
            if self.db.get_existing_player(for_player_id) is not None:
                p = self.register_player(for_player_id, mark_online=False)
        if p and not fast_tick:
            self.ensure_player_social(p)
            self._ensure_player_pet_data(p)
            self._ensure_player_mount_data(p)
            if not str(for_player_id).startswith("bot_"):
                af_snap = p.setdefault("autofarm", {})
                af_snap.setdefault("useBotSystemData", True)
                af_snap["botSystemData"] = self._get_bot_system_assist_data(p)
        map_id = p["map_id"] if p else "morgenwacht"

        now = time.time()
        other_players = []
        seen_other_names = set()
        if p and p.get("name"):
            seen_other_names.add(str(p["name"]).strip().lower())
        for pid, op in list(self.players.items()):
            if (
                pid == for_player_id
                or pid == "hero_default"
                or not op.get("online")
                or not op.get("inWorld", False)
                or (now - float(op.get("lastSeen", 0.0) or 0.0)) > 12.0
                or op["map_id"] != map_id
            ):
                continue
            op_name_key = str(op.get("name") or "").strip().lower()
            if not op_name_key or op_name_key in seen_other_names:
                continue
            seen_other_names.add(op_name_key)
            op_cdef = CHARACTER_CLASSES.get(op["class_id"], CHARACTER_CLASSES["warrior"])
            op_comp = op.get("computed")
            if not isinstance(op_comp, dict) or "armorPlus" not in op_comp:
                op_comp = self.compute_player_combat_stats(op)
            op_rep_rank = op_comp.get("reputationRank", {}) or {}
            op_vx = float(op.get("vx", 0.0) or 0.0)
            op_vz = float(op.get("vz", 0.0) or 0.0)
            op_is_moving = (
                (
                    abs(op_vx) > 0.08
                    or abs(op_vz) > 0.08
                    or (now - float(op.get("lastManualMoveTime", 0.0) or 0.0)) < 0.28
                )
                and not op.get("isDead", False)
            )
            op_is_attacking = (
                (
                    now
                    - max(
                        float(op.get("lastBasicAttack", 0.0) or 0.0),
                        float(op.get("lastSkillTime", 0.0) or 0.0),
                        float(op.get("lastSkillCastTime", 0.0) or 0.0),
                    )
                )
                < 0.75
                and not op.get("isDead", False)
            )
            team_rank = self._get_player_team_rank(op, pid)
            is_sa = (team_rank == "SA") or self._is_sa_player(op, pid)
            is_gm = bool(team_rank)
            raw_op_guild = op.get("guild")
            if isinstance(raw_op_guild, dict):
                op_guild_str = str(raw_op_guild.get("name") or "")
            else:
                op_guild_str = str(raw_op_guild or op.get("guildName") or "")
            if not op_guild_str and team_rank:
                op_guild_str = "Serverleitung"
            op_rep_color = op_rep_rank.get("color", "#93c5fd")
            op_pet_skin = (
                op_comp.get("petSkin")
                if op_comp.get("hasCostumePetSkin")
                else ((op.get("petData") or {}).get("skinKey") or op_comp.get("petSkin") or "ridack_dragonpet")
            )
            op_entry = {
                "id": pid,
                "name": op["name"],
                "isSA": is_sa,
                "isGM": is_gm,
                "teamRank": team_rank or "",
                "role": team_rank if team_rank else op.get("role", "player"),
                "classId": op["class_id"],
                "className": op_cdef["name"],
                "doctrine": op.get("doctrine") or resolve_doctrine_id(op["class_id"], op.get("doctrineIdx", 0))[1],
                "gender": op.get("gender", "male"),
                "empire": op.get("empire", "solaria"),
                "partyId": op.get("partyId"),
                "guild": op_guild_str,
                "guildName": op_guild_str,
                "level": op["level"],
                "hp": int(op["hp"]),
                "maxHp": int(op["max_hp"]),
                "x": round(op["pos_x"], 3),
                "z": round(op["pos_z"], 3),
                "rotY": round(op.get("rot_y", 0.0), 3),
                "vx": round(float(op.get("vx", 0.0)), 3) if op_is_moving else 0.0,
                "vz": round(float(op.get("vz", 0.0)), 3) if op_is_moving else 0.0,
                "speed": round(float(op.get("moveSpeed", op_comp.get("speed", 8.5))), 2),
                "destX": round(float(op.get("dest_x", op["pos_x"])), 2),
                "destZ": round(float(op.get("dest_z", op["pos_z"])), 2),
                "activeMount": op.get("active_mount"),
                "mountSkin": op_comp.get("mountVisualSkin", "horse_lvl1"),
                "activePet": op.get("active_pet"),
                "petSkin": op_pet_skin,
                "petLevel": int((op.get("petData") or {}).get("level") or op_comp.get("petLevel", 1)),
                "petName": (op.get("petData") or {}).get("customName") or op_comp.get("petName", "Grüner Smaragddrache"),
                "isMoving": op_is_moving,
                "isAttacking": op_is_attacking,
                "comboStep": int(op.get("comboStep", 0)),
                "isDead": bool(op.get("isDead", False)),
                "isBlocking": bool(op.get("isBlocking", False)),
                "isDodging": now < op.get("dodgeUntil", 0.0),
                "weaponPlus": op_comp.get("weaponPlus", 0),
                "armorPlus": op_comp.get("armorPlus", 0),
                "weaponVisual": op_comp.get("weaponVisual", None),
                "hasWeapon": op_comp.get("hasWeapon", False),
                "hasArmor": op_comp.get("hasArmor", False),
                "hasShield": op_comp.get("hasShield", False),
                "hasHelmet": op_comp.get("hasHelmet", False),
                "activeBuffs": op_comp.get("activeBuffs", []),
                "reputation": int(op.get("reputation", 1500)),
                "reputationRank": op_rep_rank.get("name", "Freundlich"),
                "reputationColor": op_rep_color,
                "reputationRankColor": op_rep_color,
            }
            if not fast_tick:
                op_eq_list = []
                for eq_slot, eq_item in (op.get("equipment") or {}).items():
                    if isinstance(eq_item, dict) and eq_item.get("name"):
                        op_eq_list.append(
                            {
                                "slot": eq_slot,
                                "templateId": eq_item.get("templateId", ""),
                                "name": eq_item.get("name", ""),
                                "plus": int(eq_item.get("plusLevel", 0)),
                                "rarity": eq_item.get("rarity", "common"),
                                "icon": eq_item.get("icon", ""),
                                "reqLevel": int(eq_item.get("reqLevel", 1)),
                                "stats": eq_item.get("effectiveStats", {}),
                                "bonuses": eq_item.get("bonuses", []),
                            }
                        )
                op_entry["equippedItems"] = op_eq_list
                op_entry["skillLevels"] = op.get("skill_levels") or op.get("skillLevels") or {}
            other_players.append(op_entry)

        mobs = []
        px = float((p or {}).get("pos_x", 0.0))
        pz = float((p or {}).get("pos_z", 0.0))
        p_target_id = (p or {}).get("targetId") or (p or {}).get("target_id")
        for mob in list(self.monsters.values()):
            if mob["mapId"] != map_id or mob["state"] == "dead":
                continue
            is_metin = mob["kind"] == "metin"
            # Sende alle Rissmonolithen & Bosse (für Radar/Minimap), das aktuell anvisierte Ziel (egal wie weit entfernt!)
            # sowie normale Monster im 205m-Sichtradius
            if (
                not is_metin
                and not mob.get("isBoss")
                and mob["id"] != p_target_id
                and (abs(mob["x"] - px) > 205.0 or abs(mob["z"] - pz) > 205.0)
            ):
                continue
            is_newly_spawned = (now - float(mob.get("spawnedAt", 0.0) or 0.0)) < 2.2
            is_boss_or_wb = bool(mob.get("isBoss") or mob.get("isRiftWorldBoss") or mob.get("isMonolithEliteBoss"))
            if fast_tick and not is_newly_spawned and not is_boss_or_wb and mob["id"] != p_target_id:
                m_entry = {
                    "id": mob["id"],
                    "kind": mob["kind"],
                    "isBoss": mob["isBoss"],
                    "hp": int(mob["hp"]),
                    "maxHp": int(mob["maxHp"]),
                    "x": round(mob["x"], 3),
                    "z": round(mob["z"], 3),
                    "rotY": round(mob["rotY"], 3),
                    "vx": round(float(mob.get("vx", 0.0)), 3),
                    "vz": round(float(mob.get("vz", 0.0)), 3),
                    "speed": round(float(mob.get("speed", 4.5)), 2),
                    "state": mob["state"],
                    "attacking": (now - mob.get("lastAttackTime", 0.0)) < (1.25 if str(mob.get("glbModel", "")).startswith("ridack_") else 0.92),
                    "attackType": mob.get("lastAttackType", "attack1"),
                    "attackComboStep": int(mob.get("attackComboStep", 0)),
                    "attackSeq": int(mob.get("attackSeq", 0)),
                    "aiAction": mob.get("aiAction", ""),
                    "aiActionSeq": int(mob.get("aiActionSeq", 0)),
                    "aiTier": int(mob.get("aiTier", 1)),
                }
                if is_metin:
                    m_entry["monolithState"] = mob.get("monolithState", "schlafend")
                    m_entry["combatPhase"] = mob.get("combatPhase", 1)
                mobs.append(m_entry)
                continue
            active_statuses = [
                {
                    "id": k,
                    "name": v["name"],
                    "icon": v["icon"],
                    "color": v["color"],
                    "remaining": round(max(0.0, v["expiresAt"] - now), 1),
                }
                for k, v in mob.get("statusEffects", {}).items()
                if v.get("expiresAt", 0.0) > now
            ]
            m_entry = {
                "id": mob["id"],
                "templateId": mob["templateId"],
                "name": mob["name"],
                "baseName": mob.get("baseName", mob["name"]),
                "kind": mob["kind"],
                "isElite": mob["isElite"],
                "isBoss": mob["isBoss"],
                "isRiftWorldBoss": bool(mob.get("isRiftWorldBoss", False)),
                "isMonolithEliteBoss": bool(mob.get("isMonolithEliteBoss", False)),
                "monolithBossOf": mob.get("monolithBossOf"),
                "despawnAt": round(float(mob.get("despawnAt", 0.0) or 0.0), 1),
                "isSummon": bool(mob.get("isSummon", False)),
                "monolithGuardOf": mob.get("monolithGuardOf"),
                "riftAggroMonolithId": mob.get("riftAggroMonolithId"),
                "isAggressive": mob.get("isAggressive", False),
                "level": mob["level"],
                "hp": int(mob["hp"]),
                "maxHp": int(mob["maxHp"]),
                "x": round(mob["x"], 3),
                "z": round(mob["z"], 3),
                "rotY": round(mob["rotY"], 3),
                "vx": round(float(mob.get("vx", 0.0)), 3),
                "vz": round(float(mob.get("vz", 0.0)), 3),
                "speed": round(float(mob.get("speed", 4.5)), 2),
                "state": mob["state"],
                "attacking": (now - mob.get("lastAttackTime", 0.0)) < (1.25 if str(mob.get("glbModel", "")).startswith("ridack_") else 0.92),
                "attackType": mob.get("lastAttackType", "attack1"),
                "attackComboStep": int(mob.get("attackComboStep", 0)),
                "attackSeq": int(mob.get("attackSeq", 0)),
                "aiAction": mob.get("aiAction", ""),
                "aiActionSeq": int(mob.get("aiActionSeq", 0)),
                "aiTier": int(mob.get("aiTier", 1)),
                "statusEffects": active_statuses,
                "modelType": mob["modelType"],
                "glbModel": mob.get("glbModel"),
                "glbTextures": mob.get("glbTextures", []),
                "color": mob["color"],
                "scale": mob["scale"],
                "icon": mob["icon"],
                "bossPhase": mob.get("bossPhase", 1),
                "combatPhase": mob.get("combatPhase", 1),
            }
            if is_metin:
                m_entry.update(
                    {
                        "baseCrystalColor": mob.get("baseCrystalColor", mob["color"]),
                        "combatPhaseText": mob.get("combatPhaseText", ""),
                        "monolithRarity": mob.get("monolithRarity", "normal"),
                        "rarityLabel": mob.get("rarityLabel", "Normal"),
                        "rarityBadge": mob.get("rarityBadge", ""),
                        "rarityColor": mob.get("rarityColor", "#E8E8E8"),
                        "shiningTier": mob.get("shiningTier", 1),
                        "lootMultiplier": mob.get("lootMultiplier", 1.0),
                        "monolithState": mob.get("monolithState", "schlafend"),
                        "monolithStateName": mob.get("monolithStateName", "Schlafender Monolith"),
                        "monolithStateBadge": mob.get("monolithStateBadge", ""),
                        "monolithStateDesc": mob.get("monolithStateDesc", ""),
                        "loreMeaning": mob.get("loreMeaning", ""),
                        "storyChapter": mob.get("storyChapter", ""),
                        "monolithEffects": mob.get("monolithEffects", []),
                        "isMajorMonolith": bool(mob.get("isMajorMonolith", False)),
                        "majorIndex": mob.get("majorIndex", 0),
                        "majorTitle": mob.get("majorTitle", ""),
                        "envRadius": mob.get("envRadius", 200.0),
                        "outerRadius": mob.get("outerRadius", 350.0),
                        "stateChangedAt": mob.get("stateChangedAt", 0.0),
                        "publicEventActive": bool(mob.get("publicEventActive", False)),
                        "realmConflictActive": bool(mob.get("realmConflictActive", False)),
                        "worldBossSummoned": bool(mob.get("worldBossSummoned", False)),
                    }
                )
            mobs.append(m_entry)

        map_drops = []
        for d in list(self.drops.values()):
            if d["mapId"] != map_id:
                continue
            can_pick, rem_prot = self.can_player_pickup_drop(for_player_id, d, now=now, is_auto=False)
            exp_rem = max(0, int(math.ceil(float(d.get("expiresAt", float(d.get("createdAt", 0.0)) + 120.0)) - now)))
            owner_id = d.get("ownerId")
            is_group_loot = bool(
                owner_id
                and owner_id != for_player_id
                and self.are_players_in_same_party(for_player_id, owner_id, d.get("ownerPartyId"))
            )
            d_view = dict(d)
            d_view["canPickup"] = can_pick
            d_view["protectedRemainingSec"] = int(math.ceil(rem_prot)) if not can_pick else 0
            d_view["despawnRemainingSec"] = exp_rem
            d_view["isGroupLoot"] = is_group_loot
            map_drops.append(d_view)
        recent_events = [e for e in self.combat_events if (e.get("mapId") in (map_id, "*", "global", "all")) and e["t"] > since_time]
        map_telegraphs = [t for t in self.telegraphs if t["mapId"] == map_id]

        party_snap = self._build_party_snapshot(p) if p else None
        trade_snap = self._build_trade_snapshot(p) if p else None
        pending_party = p.get("pendingPartyInvite") if p else None
        if pending_party and float(pending_party.get("expiresAt", 0.0)) < now:
            p["pendingPartyInvite"] = None
            pending_party = None
        pending_trade = p.get("pendingTradeRequest") if p else None
        if pending_trade and float(pending_trade.get("expiresAt", 0.0)) < now:
            p["pendingTradeRequest"] = None
            pending_trade = None

        active_wb = self._get_active_world_boss(map_id)
        wb_cd_rem = int(math.ceil(self._get_world_boss_cooldown_remaining(map_id, now=now)))
        wb_cd_until = round(float(self.world_boss_cooldown_until.get(map_id, 0.0) or 0.0), 1)
        active_wb_snap = None
        if active_wb and active_wb.get("state") != "dead":
            despawn_at = float(active_wb.get("despawnAt", 0.0) or 0.0)
            rem_sec = max(0, int(round(despawn_at - now))) if despawn_at > 0 else 3600
            active_wb_snap = {
                "id": active_wb["id"],
                "templateId": active_wb.get("templateId", "boss_morgenwacht"),
                "name": active_wb["name"],
                "level": int(active_wb.get("level", 10)),
                "hp": int(active_wb.get("hp", 1)),
                "maxHp": int(active_wb.get("maxHp", 1)),
                "x": round(float(active_wb.get("x", 0.0)), 1),
                "z": round(float(active_wb.get("z", 0.0)), 1),
                "mapId": map_id,
                "isBoss": True,
                "isElite": True,
                "isRiftWorldBoss": True,
                "monolithId": active_wb.get("monolithBossOf"),
                "despawnAt": round(despawn_at, 1),
                "remainingSec": rem_sec,
            }

        if p:
            self_team_rank = self._get_player_team_rank(p, for_player_id)
            if self_team_rank:
                p["teamRank"] = self_team_rank
                p["isGM"] = True
                if self_team_rank == "SA" or self._is_sa_player(p, for_player_id):
                    p["isSA"] = True

        if fast_tick:
            p_fast = None
            if p:
                social_dirty = now < float(p.get("_socialDirtyUntil", 0.0) or 0.0)
                if social_dirty:
                    self.ensure_player_social(p)
                exclude_keys = ("inventory", "quests") if social_dirty else ("inventory", "quests", "social")
                p_fast = {
                    k: v
                    for k, v in p.items()
                    if k not in exclude_keys
                }
                if isinstance(p_fast.get("autofarm"), dict) and "botSystemData" in p_fast["autofarm"]:
                    p_fast["autofarm"] = {
                        ak: av for ak, av in p_fast["autofarm"].items() if ak != "botSystemData"
                    }
            return {
                "isDeltaTick": True,
                "serverBootId": self.boot_id,
                "activeWorldBoss": active_wb_snap,
                "worldBossCooldownRemainingSec": wb_cd_rem,
                "worldBossCooldownUntil": wb_cd_until,
                "serverTime": time.time(),
                "player": p_fast,
                "party": party_snap,
                "pendingPartyInvite": pending_party,
                "activeTrade": trade_snap,
                "pendingTradeRequest": pending_trade,
                "socialNotice": p.get("lastSocialNotice") if p else None,
                "whisperNotice": p.get("lastWhisperNotice") if p else None,
                "bigNotice": self.active_big_notice if (self.active_big_notice and (now - float(self.active_big_notice.get("time", 0.0)) < 12.0)) else None,
                "otherPlayers": other_players,
                "onlineCount": sum(1 for pid, x in self.players.items() if pid != "hero_default" and x.get("online") and x.get("inWorld", False)),
                "monsters": mobs,
                "drops": map_drops,
                "telegraphs": map_telegraphs,
                "events": recent_events,
            }

        shops_cache = getattr(self, "_offline_shops_cache", None)
        if not isinstance(shops_cache, dict):
            shops_cache = {}
            self._offline_shops_cache = shops_cache
        cached_shops = shops_cache.get(map_id)
        if cached_shops and (now - cached_shops[0]) < 2.5:
            shops = cached_shops[1]
        else:
            shops = self.db.list_offline_shops(map_id)
            shops_cache[map_id] = (now, shops)
        self.world_event = self._compute_world_event_snapshot()

        major_monoliths = []
        for mdef in MAJOR_RIFT_MONOLITHS:
            m_inst = self.monsters.get(mdef["id"])
            m_map_name = MAPS.get(mdef["mapId"], {}).get("name", mdef["mapId"])
            if m_inst:
                major_monoliths.append(
                    {
                        "majorIndex": mdef["majorIndex"],
                        "id": mdef["id"],
                        "title": mdef["title"],
                        "mapId": mdef["mapId"],
                        "mapName": m_map_name,
                        "x": round(m_inst["x"], 1),
                        "z": round(m_inst["z"], 1),
                        "level": m_inst["level"],
                        "alive": m_inst["state"] != "dead",
                        "hp": int(m_inst["hp"]) if m_inst["state"] != "dead" else 0,
                        "maxHp": int(m_inst["maxHp"]),
                        "monolithState": m_inst.get("monolithState", "schlafend"),
                        "monolithStateName": m_inst.get("monolithStateName", "Schlafender Monolith"),
                        "monolithStateBadge": m_inst.get("monolithStateBadge", ""),
                        "publicEventActive": bool(m_inst.get("publicEventActive", False)),
                        "realmConflictActive": bool(m_inst.get("realmConflictActive", False)),
                    }
                )

        return {
            "serverBootId": self.boot_id,
            "majorMonoliths": major_monoliths,
            "activeWorldBoss": active_wb_snap,
            "worldBossCooldownRemainingSec": wb_cd_rem,
            "worldBossCooldownUntil": wb_cd_until,
            "serverTime": time.time(),
            "player": p,
            "party": party_snap,
            "pendingPartyInvite": pending_party,
            "activeTrade": trade_snap,
            "pendingTradeRequest": pending_trade,
            "socialNotice": p.get("lastSocialNotice") if p else None,
            "whisperNotice": p.get("lastWhisperNotice") if p else None,
            "bigNotice": self.active_big_notice if (self.active_big_notice and (now - float(self.active_big_notice.get("time", 0.0)) < 12.0)) else None,
            "otherPlayers": other_players,
            "onlineCount": sum(1 for pid, x in self.players.items() if pid != "hero_default" and x.get("online") and x.get("inWorld", False)),
            "monsters": mobs,
            "drops": map_drops,
            "telegraphs": map_telegraphs,
            "events": recent_events,
            "chat": [
                m for m in self.chat_history
                if not m.get("targetPlayerId") or (p and m.get("targetPlayerId") == p.get("player_id"))
            ][-100:],
            "offlineShops": shops,
            "worldEvent": self.world_event,
        }
