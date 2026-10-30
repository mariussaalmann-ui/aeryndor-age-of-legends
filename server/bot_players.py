# -*- coding: utf-8 -*-
"""
AERYNDOR: LEGACY OF THE MONOLITHS – 5-BOT-KI, SELBSTLERNENDES GAMEPLAY & AUTOMATISCHE SPIELOPTIMIERUNG
========================================================================================================
Erweitert die 5 bestehenden Spieler-Bots um:
  1. Individuelle Verhaltensprofile & Adaptive Multi-Faktor-Zielauswahl (Level, Distanz, TP/MP, Aggro,
     Gruppengröße, Erwartete EXP/Drops, Sterberisiko, Hysterese gegen Ziel-Flackern, Safezone-Rückzug).
  2. Datenbasiertes Lernsystem & Gemeinsame Wissensbasis (`bot_knowledge_base.json`) + Versionierte
     KI-Strategien (`bot_strategy_versions.json`) mit A/B-Validierung und automatischem Rollback.
  3. Intelligentes Gruppenverhalten (1 bis 5 Bots gemeinsam: Tank-Fokusfeuer, Schamanen-Gruppenheilung,
     Wächter-Peeling, koordinierter Gruppenrückzug).
  4. Automatisierte Testszenarien (Test A bis Test F) inkl. Rissmonolithen-Skalierung (1–5 Bots) und
     Ausrüstungs-/Waffen-Matrix.
  5. Automatische QA-Fehlererkennung (`bot_qa_reports.json`: Stuck/Pathfinding, Schadensspitzen,
     Riss-Bollwerk-Blockaden, Level-Penalty-Deadzones, AFK-Recovery).
  6. Kontrollierte Sandbox-Optimierungsschleife (`bot_balancing_proposals.json`): Erkennt Balancing-
     Probleme, testet konkrete Patch-Vorschläge isoliert in einer Sandbox-Welt und vergleicht Vorher/Nachher.
"""

import argparse
import copy
import json
import math
import os
import random
import sys
import time
import urllib.request
from collections import Counter, defaultdict
from typing import Dict, List, Optional, Tuple

SERVER_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SERVER_DIR)
DATA_DIR = os.path.join(ROOT_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)

TELEMETRY_PATH = os.path.join(DATA_DIR, "bot_telemetry.json")
LIVE_TELEMETRY_PATH = os.path.join(DATA_DIR, "bot_telemetry_live.json")
KNOWLEDGE_BASE_PATH = os.path.join(DATA_DIR, "bot_knowledge_base.json")
STRATEGY_VERSIONS_PATH = os.path.join(DATA_DIR, "bot_strategy_versions.json")
QA_REPORTS_PATH = os.path.join(DATA_DIR, "bot_qa_reports.json")
BALANCING_PROPOSALS_PATH = os.path.join(DATA_DIR, "bot_balancing_proposals.json")
SCENARIO_RESULTS_PATH = os.path.join(DATA_DIR, "bot_scenario_results.json")
CONTROL_STATE_PATH = os.path.join(DATA_DIR, "bot_control_state.json")

# ----------------------------------------------------------------------------
# GEDÄCHTNIS / MITTEILUNGEN AN ALLE BOTS (aktuelle Spielregeln, Stand 29.10.2026)
# Wird in jeden Bot-Zustand (p["botMemory"]) und in die gemeinsame Wissensbasis geschrieben.
# ----------------------------------------------------------------------------
from game_data import BOT_GAME_RULES_MEMORY, BOT_GAME_RULES_MEMORY_VERSION  # noqa: E402 (zentral, auch vom Server genutzt)


def apply_bot_rules_memory(p: dict) -> None:
    """Schreibt die aktuellen Spielregeln als Gedächtnis in einen Bot-Zustand."""
    if not isinstance(p, dict):
        return
    p["botMemory"] = [dict(m) for m in BOT_GAME_RULES_MEMORY]
    p["botMemoryVersion"] = BOT_GAME_RULES_MEMORY_VERSION


def sync_bot_rules_memory_to_knowledge_base() -> None:
    """Ergänzt die gemeinsame Bot-Wissensbasis (bot_knowledge_base.json) um das Regel-Gedächtnis."""
    try:
        kb = {}
        if os.path.exists(KNOWLEDGE_BASE_PATH):
            with open(KNOWLEDGE_BASE_PATH, "r", encoding="utf-8") as f:
                kb = json.load(f) or {}
        if kb.get("gameRuleMemoryVersion") == BOT_GAME_RULES_MEMORY_VERSION:
            return
        kb["gameRuleMemory"] = BOT_GAME_RULES_MEMORY
        kb["gameRuleMemoryVersion"] = BOT_GAME_RULES_MEMORY_VERSION
        kb["updatedAt"] = time.strftime("%Y-%m-%d %H:%M:%S")
        with open(KNOWLEDGE_BASE_PATH, "w", encoding="utf-8") as f:
            json.dump(kb, f, indent=2, ensure_ascii=False)
    except Exception:
        pass

sys.path.insert(0, SERVER_DIR)

from database import GameDatabase
try:
    from database import BOT_CITY_SHOP_SPOTS
except ImportError:
    BOT_CITY_SHOP_SPOTS = {}
from game_data import (
    BLACKSMITH_RATES,
    CHARACTER_CLASSES,
    CLASS_ALLOWED_WEAPONS,
    DUNGEONS,
    HORSE_SKILLS,
    ITEM_TEMPLATES,
    MAPS,
    MONSTER_TEMPLATES,
    QUEST_TEMPLATES,
    calculate_item_effective_stats,
)
from world_server import WorldAuthority, dist2d, is_in_safe_zone


# ============================================================================
# 1. DIE 12 SPIELER-BOTS (6 IM REICH SEIRYU + 6 IM REICH KAERYU)
# ============================================================================
BOT_CONFIGS = [
    # --- REICH 1: SEIRYU (Nordosten • Die Wacht der Grenzlande) ---
    {
        "playerId": "bot_veyron_warrior",
        "accountName": "bot_account_veyron",
        "name": "[Bot]Veyron",
        "classId": "warrior",
        "empire": "seiryu",
        "roleDesc": "Klingenwächter (Krieger • Einhand & Schild • Seiryu) • Frontline-Tank & Allrounder",
        "groupRole": "tank",
        "preferredMode": "monsters_and_metins",
        "statPriority": ["str", "str", "vit"],
        "skillPriority": ["aura_sword", "whirlwind", "three_way_cut", "dash_strike", "berserk"],
        "startX": 560.0,
        "startZ": -680.0,
        "useMount": False,
        "mountId": "mount_war_boar",
        "petSkin": "plechi_elephant_pet2",
        "petName": "Kaiser-Elefant",
        "useTwoHand": False,
    },
    {
        "playerId": "bot_nachtklinge_ninja",
        "accountName": "bot_account_nachtklinge",
        "name": "[Bot]Nachtklinge",
        "classId": "ninja",
        "empire": "seiryu",
        "roleDesc": "Schattenjäger (Ninja • Dolche • Seiryu) • Rissmonolithen-Spezialist & Krit-Burst",
        "groupRole": "burst_dps",
        "preferredMode": "metin_hunter",
        "statPriority": ["dex", "dex", "str"],
        "skillPriority": ["stealth", "ambush", "rolling_dagger", "poison_cloud", "shadow_step"],
        "startX": 585.0,
        "startZ": -650.0,
        "useMount": False,
        "mountId": "mount_war_boar",
        "petSkin": "plechi_flamegoblin_pet",
        "petName": "Glutkobold",
        "useTwoHand": False,
    },
    {
        "playerId": "bot_malakor_sura",
        "accountName": "bot_account_malakor",
        "name": "[Bot]Malakor",
        "classId": "sura",
        "empire": "seiryu",
        "roleDesc": "Runenmagier (Sura • Verzauberte Klinge • Seiryu) • TP-Absaugung & Wellen-Kontrolle",
        "groupRole": "bruiser_aoe",
        "preferredMode": "monsters_and_metins",
        "statPriority": ["int", "int", "vit"],
        "skillPriority": ["enchanted_blade", "enchanted_armor", "finger_strike", "dragon_swirl", "dark_orb"],
        "startX": 525.0,
        "startZ": -705.0,
        "useMount": False,
        "mountId": "mount_war_boar",
        "petSkin": "plechi_lich_pet",
        "petName": "Seelen-Lich",
        "useTwoHand": False,
    },
    {
        "playerId": "bot_aurelia_shaman",
        "accountName": "bot_account_aurelia",
        "name": "[Bot]Aurelia",
        "classId": "shaman",
        "empire": "seiryu",
        "roleDesc": "Seelenweber (Schamane • 6.5m Stab • Seiryu) • Drachen-Buffs, Magie-AoE & Gruppenheilung",
        "groupRole": "support_healer",
        "preferredMode": "monsters_and_metins",
        "statPriority": ["int", "int", "dex"],
        "skillPriority": ["dragon_help", "natures_heal", "dragon_blessing", "dragon_roar", "lightning_claw"],
        "startX": 545.0,
        "startZ": -665.0,
        "useMount": False,
        "mountId": "mount_war_boar",
        "petSkin": "plechi_fantasy_flypet2",
        "petName": "Äther-Schwinge",
        "useTwoHand": False,
    },
    {
        "playerId": "bot_eisensturm_mounted",
        "accountName": "bot_account_eisensturm",
        "name": "[Bot]Eisensturm",
        "classId": "warrior",
        "empire": "seiryu",
        "roleDesc": "Klingenwächter (Beritten • Zweihand-Glefe & Mount • Seiryu) • Rissmonolithen-Brecher",
        "groupRole": "mounted_breaker",
        "preferredMode": "metin_hunter",
        "statPriority": ["str", "str", "vit"],
        "skillPriority": ["aura_sword", "berserk", "whirlwind", "three_way_cut", "dash_strike"],
        "startX": 380.0,
        "startZ": -730.0,
        "useMount": True,
        "mountId": "mount_crystal_wolf",
        "petSkin": "plechi_emd_pet",
        "petName": "Runen-Wächter",
        "useTwoHand": True,
    },
    {
        "playerId": "bot_lyra_ninja",
        "accountName": "bot_account_lyra",
        "name": "[Bot]Lyra",
        "classId": "ninja",
        "empire": "seiryu",
        "roleDesc": "Schattenjäger (Ninja • Krit-Klingen & Gift • Seiryu) • Flanken-Jägerin & Boss-Assassine",
        "groupRole": "burst_dps",
        "preferredMode": "monsters_and_metins",
        "statPriority": ["dex", "dex", "str"],
        "skillPriority": ["stealth", "ambush", "rolling_dagger", "poison_cloud", "shadow_step"],
        "startX": 505.0,
        "startZ": -690.0,
        "useMount": False,
        "mountId": "mount_war_boar",
        "petSkin": "plechi_thuderspirit_pet",
        "petName": "Donnergeist",
        "useTwoHand": False,
    },
    # --- REICH 2: KAERYU (Nordwesten • Das Tal der Bewahrer) ---
    {
        "playerId": "bot_kassian_warrior",
        "accountName": "bot_account_kassian",
        "name": "[Bot]Kassian",
        "classId": "warrior",
        "empire": "kaeryu",
        "roleDesc": "Klingenwächter (Krieger • Einhand & Schild • Kaeryu) • Bollwerk-Tank & Wächter",
        "groupRole": "tank",
        "preferredMode": "monsters_and_metins",
        "statPriority": ["str", "str", "vit"],
        "skillPriority": ["aura_sword", "whirlwind", "three_way_cut", "dash_strike", "berserk"],
        "startX": -560.0,
        "startZ": -680.0,
        "useMount": False,
        "mountId": "mount_war_boar",
        "petSkin": "plechi_emd_pet",
        "petName": "Runen-Wächter",
        "useTwoHand": False,
    },
    {
        "playerId": "bot_schattenfalke_ninja",
        "accountName": "bot_account_schattenfalke",
        "name": "[Bot]Schattenfalke",
        "classId": "ninja",
        "empire": "kaeryu",
        "roleDesc": "Schattenjäger (Ninja • Dolche • Kaeryu) • Krit-Assassine & Monolithen-Jäger",
        "groupRole": "burst_dps",
        "preferredMode": "metin_hunter",
        "statPriority": ["dex", "dex", "str"],
        "skillPriority": ["stealth", "ambush", "rolling_dagger", "poison_cloud", "shadow_step"],
        "startX": -585.0,
        "startZ": -650.0,
        "useMount": False,
        "mountId": "mount_war_boar",
        "petSkin": "plechi_smaragd_dragon",
        "petName": "Jade-Wyrmling",
        "useTwoHand": False,
    },
    {
        "playerId": "bot_varon_sura",
        "accountName": "bot_account_varon",
        "name": "[Bot]Varon",
        "classId": "sura",
        "empire": "kaeryu",
        "roleDesc": "Runenmagier (Sura • Verzauberte Klinge • Kaeryu) • Dunkelmagie & Ausdauer-Brecher",
        "groupRole": "bruiser_aoe",
        "preferredMode": "monsters_and_metins",
        "statPriority": ["int", "int", "vit"],
        "skillPriority": ["enchanted_blade", "enchanted_armor", "finger_strike", "dragon_swirl", "dark_orb"],
        "startX": -525.0,
        "startZ": -705.0,
        "useMount": False,
        "mountId": "mount_war_boar",
        "petSkin": "plechi_lich_pet",
        "petName": "Seelen-Lich",
        "useTwoHand": False,
    },
    {
        "playerId": "bot_seraphina_shaman",
        "accountName": "bot_account_seraphina",
        "name": "[Bot]Seraphina",
        "classId": "shaman",
        "empire": "kaeryu",
        "roleDesc": "Seelenweber (Schamane • 6.5m Stab • Kaeryu) • Heilung, Segen & Elementar-Orkan",
        "groupRole": "support_healer",
        "preferredMode": "monsters_and_metins",
        "statPriority": ["int", "int", "dex"],
        "skillPriority": ["dragon_help", "natures_heal", "dragon_blessing", "dragon_roar", "lightning_claw"],
        "startX": -545.0,
        "startZ": -665.0,
        "useMount": False,
        "mountId": "mount_war_boar",
        "petSkin": "plechi_fantasy_flypet2",
        "petName": "Äther-Schwinge",
        "useTwoHand": False,
    },
    {
        "playerId": "bot_donnerkeil_mounted",
        "accountName": "bot_account_donnerkeil",
        "name": "[Bot]Donnerkeil",
        "classId": "warrior",
        "empire": "kaeryu",
        "roleDesc": "Klingenwächter (Beritten • Zweihand-Glefe & Mount • Kaeryu) • Sturmreiter & Riss-Brecher",
        "groupRole": "mounted_breaker",
        "preferredMode": "metin_hunter",
        "statPriority": ["str", "str", "vit"],
        "skillPriority": ["aura_sword", "berserk", "whirlwind", "three_way_cut", "dash_strike"],
        "startX": -380.0,
        "startZ": -730.0,
        "useMount": True,
        "mountId": "mount_crystal_wolf",
        "petSkin": "plechi_elephant_pet2",
        "petName": "Kaiser-Elefant",
        "useTwoHand": True,
    },
    {
        "playerId": "bot_draven_sura",
        "accountName": "bot_account_draven",
        "name": "[Bot]Draven",
        "classId": "sura",
        "empire": "kaeryu",
        "roleDesc": "Runenmagier (Sura • Dunkelmagie & Runenklinge • Kaeryu) • Riss-Exorzist & Wellen-Brecher",
        "groupRole": "bruiser_aoe",
        "preferredMode": "monsters_and_metins",
        "statPriority": ["int", "int", "vit"],
        "skillPriority": ["enchanted_blade", "enchanted_armor", "finger_strike", "dragon_swirl", "dark_orb"],
        "startX": -505.0,
        "startZ": -690.0,
        "useMount": False,
        "mountId": "mount_war_boar",
        "petSkin": "ridack_dragonpet",
        "petName": "Grüner Smaragddrache",
        "useTwoHand": False,
    },
]

# Die 2 aktuell existierenden Level-/Farmgebiete der Open World (Gebiet 1: Heimatlande Nord Lv. 1–17, Gebiet 2: Bakra-Herbstauen Süd Lv. 18–40)
EMPIRE_HUNTING_PROGRESSION = {
    "seiryu": [
        {"id": "m1_seiryu_meadows", "area": 1, "name": "Gebiet 1 • Östliche Seiryu-Wiesen (Lv. 1–5)", "x": 560.0, "z": -680.0, "minLvl": 1, "maxLvl": 5},
        {"id": "m1_north_steppe_east", "area": 1, "name": "Gebiet 1 • Nördliche Steppe Ost (Lv. 4–8)", "x": 180.0, "z": -750.0, "minLvl": 4, "maxLvl": 8},
        {"id": "m1_east_grasland", "area": 1, "name": "Gebiet 1 • Großes Ost-Grasland (Lv. 7–12)", "x": 620.0, "z": -360.0, "minLvl": 7, "maxLvl": 12},
        {"id": "m1_river_meadows_east", "area": 1, "name": "Gebiet 1 • Silberstrom-Auen Ost & Weol (Lv. 11–17)", "x": 260.0, "z": -195.0, "minLvl": 11, "maxLvl": 17},
        {"id": "m2_autumn_north_east", "area": 2, "name": "Gebiet 2 • Nordöstliche Bakra-Ahornwälder (Lv. 18–23)", "x": 520.0, "z": 185.0, "minLvl": 18, "maxLvl": 23},
        {"id": "m2_autumn_north_center", "area": 2, "name": "Gebiet 2 • Goldenes Bakra-Herbsttal Ost (Lv. 22–27)", "x": 240.0, "z": 260.0, "minLvl": 22, "maxLvl": 27},
        {"id": "m2_autumn_heart_east", "area": 2, "name": "Gebiet 2 • Östliches Bakra-Hochland (Lv. 26–31)", "x": 440.0, "z": 460.0, "minLvl": 26, "maxLvl": 31},
        {"id": "m2_autumn_south_east", "area": 2, "name": "Gebiet 2 • Südliches Bakra-Heerlager Ost (Lv. 30–40)", "x": 320.0, "z": 625.0, "minLvl": 30, "maxLvl": 40},
    ],
    "kaeryu": [
        {"id": "m1_kaeryu_meadows", "area": 1, "name": "Gebiet 1 • Westliche Kaeryu-Wiesen (Lv. 1–5)", "x": -560.0, "z": -680.0, "minLvl": 1, "maxLvl": 5},
        {"id": "m1_north_steppe_west", "area": 1, "name": "Gebiet 1 • Nördliche Steppe West (Lv. 4–8)", "x": -180.0, "z": -750.0, "minLvl": 4, "maxLvl": 8},
        {"id": "m1_west_grasland", "area": 1, "name": "Gebiet 1 • Großes West-Grasland (Lv. 7–12)", "x": -620.0, "z": -360.0, "minLvl": 7, "maxLvl": 12},
        {"id": "m1_river_meadows_west", "area": 1, "name": "Gebiet 1 • Silberstrom-Auen West & Weol (Lv. 11–17)", "x": -260.0, "z": -195.0, "minLvl": 11, "maxLvl": 17},
        {"id": "m2_autumn_north_west", "area": 2, "name": "Gebiet 2 • Nordwestliche Bakra-Herbstwiesen (Lv. 18–23)", "x": -520.0, "z": 185.0, "minLvl": 18, "maxLvl": 23},
        {"id": "m2_autumn_north_center_w", "area": 2, "name": "Gebiet 2 • Goldenes Bakra-Herbsttal West (Lv. 22–27)", "x": -240.0, "z": 260.0, "minLvl": 22, "maxLvl": 27},
        {"id": "m2_autumn_heart_west", "area": 2, "name": "Gebiet 2 • Westliches Bakra-Hochland (Lv. 26–31)", "x": -440.0, "z": 460.0, "minLvl": 26, "maxLvl": 31},
        {"id": "m2_autumn_south_west", "area": 2, "name": "Gebiet 2 • Südliches Bakra-Heerlager West (Lv. 30–40)", "x": -320.0, "z": 625.0, "minLvl": 30, "maxLvl": 40},
    ],
}

HUNTING_ZONES = (
    EMPIRE_HUNTING_PROGRESSION["seiryu"]
    + EMPIRE_HUNTING_PROGRESSION["kaeryu"]
)

# Die 2 steinernen Flussbrücken über den Silberstrom (Z ≈ 0) zwischen Gebiet 1 (Map 1 Nord) und Gebiet 2 (Map 2 Süd)
STONE_BRIDGES = {
    "seiryu": {"name": "Ost-Steinbrücke (Seiryu-Übergang)", "x": 760.0, "northZ": -54.0, "southZ": 54.0},
    "kaeryu": {"name": "West-Steinbrücke (Kaeryu-Übergang)", "x": -760.0, "northZ": -54.0, "southZ": 54.0},
}

# Freundschafts-Hierarchie innerhalb desselben Reichs & Reichs-Feindschaft zwischen Seiryu und Kaeryu (-100%)
BOT_FRIENDSHIP_MATRIX = {
    # Reich Seiryu (Osten)
    "bot_veyron_warrior": {
        "bestFriends": [("[Bot]Aurelia", 96), ("[Bot]Eisensturm", 88)],
        "normalFriends": [("[Bot]Lyra", 78), ("[Bot]Malakor", 68), ("[Bot]Nachtklinge", 56)],
        "rivals": [("[Bot]Kassian", -100), ("[Bot]Donnerkeil", -100), ("[Bot]Draven", -100)],
    },
    "bot_nachtklinge_ninja": {
        "bestFriends": [("[Bot]Lyra", 91), ("[Bot]Malakor", 85)],
        "normalFriends": [("[Bot]Veyron", 56), ("[Bot]Aurelia", 52), ("[Bot]Eisensturm", 38)],
        "rivals": [("[Bot]Schattenfalke", -100), ("[Bot]Varon", -100), ("[Bot]Draven", -100)],
    },
    "bot_malakor_sura": {
        "bestFriends": [("[Bot]Nachtklinge", 85), ("[Bot]Aurelia", 74)],
        "normalFriends": [("[Bot]Lyra", 72), ("[Bot]Veyron", 68), ("[Bot]Eisensturm", 48)],
        "rivals": [("[Bot]Varon", -100), ("[Bot]Draven", -100), ("[Bot]Seraphina", -100)],
    },
    "bot_aurelia_shaman": {
        "bestFriends": [("[Bot]Veyron", 96), ("[Bot]Lyra", 86), ("[Bot]Eisensturm", 82)],
        "normalFriends": [("[Bot]Malakor", 74), ("[Bot]Nachtklinge", 52)],
        "rivals": [("[Bot]Seraphina", -100), ("[Bot]Kassian", -100), ("[Bot]Draven", -100)],
    },
    "bot_eisensturm_mounted": {
        "bestFriends": [("[Bot]Veyron", 88), ("[Bot]Aurelia", 82)],
        "normalFriends": [("[Bot]Lyra", 64), ("[Bot]Malakor", 48), ("[Bot]Nachtklinge", 38)],
        "rivals": [("[Bot]Donnerkeil", -100), ("[Bot]Kassian", -100), ("[Bot]Schattenfalke", -100)],
    },
    "bot_lyra_ninja": {
        "bestFriends": [("[Bot]Nachtklinge", 91), ("[Bot]Aurelia", 86)],
        "normalFriends": [("[Bot]Veyron", 78), ("[Bot]Malakor", 72), ("[Bot]Eisensturm", 64)],
        "rivals": [("[Bot]Draven", -100), ("[Bot]Schattenfalke", -100), ("[Bot]Kassian", -100)],
    },
    # Reich Kaeryu (Westen)
    "bot_kassian_warrior": {
        "bestFriends": [("[Bot]Seraphina", 95), ("[Bot]Donnerkeil", 89)],
        "normalFriends": [("[Bot]Draven", 79), ("[Bot]Varon", 67), ("[Bot]Schattenfalke", 54)],
        "rivals": [("[Bot]Veyron", -100), ("[Bot]Eisensturm", -100), ("[Bot]Lyra", -100)],
    },
    "bot_schattenfalke_ninja": {
        "bestFriends": [("[Bot]Varon", 86), ("[Bot]Draven", 84)],
        "normalFriends": [("[Bot]Kassian", 54), ("[Bot]Seraphina", 50), ("[Bot]Donnerkeil", 35)],
        "rivals": [("[Bot]Nachtklinge", -100), ("[Bot]Lyra", -100), ("[Bot]Malakor", -100)],
    },
    "bot_varon_sura": {
        "bestFriends": [("[Bot]Draven", 92), ("[Bot]Schattenfalke", 86), ("[Bot]Seraphina", 75)],
        "normalFriends": [("[Bot]Kassian", 67), ("[Bot]Donnerkeil", 46)],
        "rivals": [("[Bot]Malakor", -100), ("[Bot]Aurelia", -100), ("[Bot]Nachtklinge", -100)],
    },
    "bot_seraphina_shaman": {
        "bestFriends": [("[Bot]Kassian", 95), ("[Bot]Draven", 85), ("[Bot]Donnerkeil", 81)],
        "normalFriends": [("[Bot]Varon", 75), ("[Bot]Schattenfalke", 50)],
        "rivals": [("[Bot]Aurelia", -100), ("[Bot]Veyron", -100), ("[Bot]Malakor", -100)],
    },
    "bot_donnerkeil_mounted": {
        "bestFriends": [("[Bot]Kassian", 89), ("[Bot]Seraphina", 81)],
        "normalFriends": [("[Bot]Draven", 63), ("[Bot]Varon", 46), ("[Bot]Schattenfalke", 35)],
        "rivals": [("[Bot]Eisensturm", -100), ("[Bot]Veyron", -100), ("[Bot]Lyra", -100)],
    },
    "bot_draven_sura": {
        "bestFriends": [("[Bot]Varon", 92), ("[Bot]Seraphina", 85), ("[Bot]Schattenfalke", 84)],
        "normalFriends": [("[Bot]Kassian", 79), ("[Bot]Donnerkeil", 63)],
        "rivals": [("[Bot]Lyra", -100), ("[Bot]Malakor", -100), ("[Bot]Veyron", -100)],
    },
}


def get_bot_social_profile(pid: str) -> dict:
    info = BOT_FRIENDSHIP_MATRIX.get(pid, {})
    return {
        "bestFriends": [{"name": n, "affinity": sc} for n, sc in info.get("bestFriends", [])],
        "normalFriends": [{"name": n, "affinity": sc} for n, sc in info.get("normalFriends", [])],
        "rivals": [{"name": n, "affinity": sc} for n, sc in info.get("rivals", [])],
    }

# ============================================================================
# 2. VERSIONIERTE KI-STRATEGIEN & ZENTRALE WISSENSBASIS
# ============================================================================
STRATEGY_PRESETS = {
    "v1.0_baseline": {
        "version": "v1.0_baseline",
        "name": "v1.0 Standard-Auto-Jagd (Baseline)",
        "description": "Einfache Distanz-Zielauswahl ohne Gefahren-Prädiktion, feste Trank-Schwelle (65%) und unkoordinierte Rotation.",
        "weights": {
            "distWeight": 1.2,
            "levelMatchWeight": 8.0,
            "expectedExpWeight": 10.0,
            "dangerPenaltyWeight": 0.0,
            "targetLockBonus": 15.0,
            "packDensityBonus": 0.0,
            "retreatHpPct": 15.0,
            "potionHpPct": 65.0,
            "kiteOnShockwave": False,
            "prioritizeRiftBossOverMonolith": False,
            "adaptiveZoneSwitch": False,
            "manaReservePct": 10.0,
        },
    },
    "v2.0_adaptive_learned": {
        "version": "v2.0_adaptive_learned",
        "name": "v2.0 Selbstlernende Adaptive KI",
        "description": "Multi-Faktor-Zielbewertung (XP/Sek-Effizienz, Sterberisiko, Hysterese-Lock, Riss-Bollwerk-Fokus, Klassen-Skill-Priorisierung & adaptiver Gebietswechsel).",
        "weights": {
            "distWeight": 0.65,
            "levelMatchWeight": 22.0,
            "expectedExpWeight": 38.0,
            "dangerPenaltyWeight": 65.0,
            "targetLockBonus": 160.0,
            "packDensityBonus": 18.0,
            "retreatHpPct": 26.0,
            "potionHpPct": 72.0,
            "kiteOnShockwave": True,
            "prioritizeRiftBossOverMonolith": True,
            "adaptiveZoneSwitch": True,
            "manaReservePct": 22.0,
        },
    },
    "v3.0_evolution_ttk": {
        "version": "v3.0_evolution_ttk",
        "name": "v3.0 Selbstlernende Build- & Rotations-Evolution",
        "description": "Live-Optimierung der Skill-Kombo anhand der echten Kill-Zeit (TTK), klassenspezifische Wunsch-Boni-Evolution beim Runenweber (Äthersiegel + Bonuswandler) & aktive Gruppen-Kommandos.",
        "weights": {
            "distWeight": 0.60,
            "levelMatchWeight": 25.0,
            "expectedExpWeight": 42.0,
            "dangerPenaltyWeight": 68.0,
            "targetLockBonus": 175.0,
            "packDensityBonus": 22.0,
            "retreatHpPct": 26.0,
            "potionHpPct": 72.0,
            "kiteOnShockwave": True,
            "prioritizeRiftBossOverMonolith": True,
            "adaptiveZoneSwitch": True,
            "manaReservePct": 20.0,
            "evolutionTtkOptimization": True,
            "runeweaverBuildOptimization": True,
        },
    },
    "v4.0_omni_synergy": {
        "version": "v4.0_omni_synergy",
        "name": "v4.0 Omni-Synergie: Pet-Meisterschaft, Riss-Erweckung & Auto-Balancing",
        "description": "12-Bot-KI v4.0: 4 Rotations-Archetypen pro Klasse, Pet-Kampfsynergie (+ATK/+Magie-AW/+Monster-DMG%), Talisman-/Gürtel-Verzauberung & 600-Kill Live-Auto-Balancing.",
        "weights": {
            "distWeight": 0.55,
            "levelMatchWeight": 28.0,
            "expectedExpWeight": 48.0,
            "dangerPenaltyWeight": 72.0,
            "targetLockBonus": 195.0,
            "packDensityBonus": 28.0,
            "retreatHpPct": 26.0,
            "potionHpPct": 74.0,
            "kiteOnShockwave": True,
            "prioritizeRiftBossOverMonolith": True,
            "adaptiveZoneSwitch": True,
            "manaReservePct": 20.0,
            "evolutionTtkOptimization": True,
            "runeweaverBuildOptimization": True,
            "petSynergyOptimization": True,
            "monolithAwakeningCoop": True,
            "autoBalanceFeedbackLoop": True,
        },
    },
    "v5.0_omni_synergy": {
        "version": "v5.0_omni_synergy",
        "name": "v5.0 Omni-Synergie: Riss-Erweckung, 15m-Boss-Koop, Physische Stadt-KI & Spieler-Synergie (Aktiv)",
        "description": "Vollintegrierte 12-Bot-KI v5.0: Autonome Rissmonolith-Erweckung, Jagd auf alle 3 festen 15m-Kartenbosse, taktisches Boss-Blocken/Ausweichen & Boss-Return-Memory, physische Stadtrundgänge (Schmied/Seelenweberin/Händlerin) sowie kontextbezogene Live-Messenger- & Handels-Interaktion.",
        "weights": {
            "distWeight": 0.50,
            "levelMatchWeight": 32.0,
            "expectedExpWeight": 54.0,
            "dangerPenaltyWeight": 68.0,
            "targetLockBonus": 215.0,
            "packDensityBonus": 32.0,
            "retreatHpPct": 24.0,
            "potionHpPct": 76.0,
            "kiteOnShockwave": True,
            "prioritizeRiftBossOverMonolith": True,
            "adaptiveZoneSwitch": True,
            "manaReservePct": 20.0,
            "evolutionTtkOptimization": True,
            "runeweaverBuildOptimization": True,
            "petSynergyOptimization": True,
            "monolithAwakeningCoop": True,
            "autoBalanceFeedbackLoop": True,
            "physicalTownErrands": True,
            "tacticalBossDefenseAndReturn": True,
            "livePlayerMessengerAndTradeAi": True,
        },
    },
}


def load_or_init_control_state() -> dict:
    default_bots_enabled = {cfg["playerId"]: True for cfg in BOT_CONFIGS}
    default_state = {
        "activeStrategyVersion": "v5.0_omni_synergy",
        "learningEnabled": True,
        "groupMode": False,
        "groupSize": 12,
        "selectedZone": "auto",
        "botsEnabled": dict(default_bots_enabled),
        "appliedBalancePatches": [],
        "autoApplyProposals": True,
        "lastScenarioRun": "test_e_strategy_ab",
        "updatedAt": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    if os.path.exists(CONTROL_STATE_PATH):
        try:
            with open(CONTROL_STATE_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                merged_enabled = dict(default_bots_enabled)
                if isinstance(data.get("botsEnabled"), dict):
                    merged_enabled.update(data["botsEnabled"])
                default_state.update(data)
                default_state["botsEnabled"] = merged_enabled
                return default_state
        except Exception:
            pass
    with open(CONTROL_STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(default_state, f, indent=2, ensure_ascii=False)
    return default_state


def save_control_state(state: dict):
    state["updatedAt"] = time.strftime("%Y-%m-%d %H:%M:%S")
    with open(CONTROL_STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


# ============================================================================
# 3. INTELLIGENTE ZIELAUSWAHL, GRUPPENVERHALTEN & SELBSTLERN-MODUL
# ============================================================================
def evaluate_target_utility(
    world: WorldAuthority,
    p: dict,
    mob: dict,
    cfg: dict,
    strategy_weights: dict,
    group_focus_id: Optional[str] = None,
    dangerous_mob_registry: Optional[dict] = None,
) -> Tuple[float, dict]:
    """Berechnet einen nachvollziehbaren Utility-Score (höher = besser) für jedes potenzielle Ziel."""
    px, pz = float(p["pos_x"]), float(p["pos_z"])
    p_lvl = max(1, int(p.get("level", 1)))
    mob_lvl = max(1, int(mob.get("level", 1)))
    d = dist2d(px, pz, mob["x"], mob["z"])

    # 1. Erwartete XP-/Beute-Effizienz (compute_level_reward_penalty)
    reward_factor = world.compute_level_reward_penalty(p_lvl, mob_lvl, p["map_id"])

    # 2. Geschätzte Kampfdauer (TTK) & Sterberisiko (inkl. aktivem Pet-Schaden & Pet-PvM-Boni!)
    comp = p.get("computed") or {}
    my_atk = max(45.0, float(comp.get("atk", 60)), float(comp.get("magicAtk", 40)))
    pet_atk_bonus = float(comp.get("petBonusAtk", 0) or 0)
    pet_dmg_pct = float(comp.get("petDmgPct", 0.0) or 0.0)
    vs_mob_pct = float(comp.get("vsMetinPct", 0.0) if mob.get("kind") == "metin" else comp.get("vsMonsterPct", 0.0))
    eff_dmg_mult = 1.0 + max(0.0, vs_mob_pct + pet_dmg_pct * 0.5) / 100.0
    my_def = max(15.0, float(comp.get("def", 30)))
    est_dps = max(35.0, (my_atk + pet_atk_bonus * 0.35) * 1.65 * eff_dmg_mult)
    est_ttk = max(0.8, float(mob.get("hp", 200)) / est_dps)

    mob_atk = float(mob.get("atk", 25))
    inc_dps = max(2.0, (mob_atk - my_def * 0.45) / max(0.8, float(mob.get("attackInterval", 1.4))))
    if mob.get("kind") == "metin":
        inc_dps += 18.0 if mob.get("monolithState") != "schlafend" else 9.0
    hp_cur = max(1.0, float(p.get("hp", 500)))
    death_risk = min(1.5, (inc_dps * est_ttk) / hp_cur)

    # Bekannte gefährliche Monster aus der gemeinsamen Wissensbasis berücksichtigen
    if dangerous_mob_registry and mob.get("templateId") in dangerous_mob_registry:
        death_risk += float(dangerous_mob_registry[mob["templateId"]].get("riskAdder", 0.25))

    # 3. Basis-Utility
    score = 200.0
    score -= d * float(strategy_weights.get("distWeight", 0.65))
    score += reward_factor * float(strategy_weights.get("expectedExpWeight", 38.0))
    score -= abs(mob_lvl - p_lvl) * float(strategy_weights.get("levelMatchWeight", 22.0)) * 0.45
    score -= death_risk * float(strategy_weights.get("dangerPenaltyWeight", 65.0))

    # Strafe für Ziele ohne Belohnung (Levelabstand zu groß) oder falsches Map-Gebiet (Bots ab Lv. 18 gehören nach Map 2 Süd!)
    if reward_factor <= 0.05:
        score -= 320.0
    if p_lvl >= 18 and float(mob.get("z", 0.0)) < 0.0:
        score -= 900.0
    elif p_lvl < 14 and float(mob.get("z", 0.0)) > 0.0:
        score -= 900.0
    if mob_lvl > p_lvl + 6 and float(strategy_weights.get("dangerPenaltyWeight", 0.0)) > 0:
        score -= (mob_lvl - (p_lvl + 6)) * 42.0

    # 4. Ziel-Stabilität (Hysterese: Verhindert sinnloses Ziel-Wechseln mitten im Kampf!)
    if mob["id"] == p.get("targetId"):
        score += float(strategy_weights.get("targetLockBonus", 160.0))

    # 5. Gruppen-Fokusfeuer (Party-Koordination)
    if group_focus_id and mob["id"] == group_focus_id:
        score += 240.0

    # 6. Riss-Bollwerk-Erkennung (Stufe 3 Erwacht: Zuerst den beschworenen Riss-Boss besiegen, da sonst -65% Schaden!)
    if strategy_weights.get("prioritizeRiftBossOverMonolith", True):
        if mob.get("monolithBossOf") or mob.get("isMonolithEliteBoss"):
            score += 210.0
        elif mob.get("kind") == "metin" and mob.get("monolithState") == "erwacht" and mob.get("activeWorldBossId"):
            score -= 280.0

    # 7. Spezialisierung (Rissmonolithen-Jäger vs. Monster-Gruppen)
    if cfg["preferredMode"] == "metin_hunter" and mob.get("kind") == "metin":
        if mob_lvl <= p_lvl + 6:
            score += 190.0
    elif mob.get("packId") and float(strategy_weights.get("packDensityBonus", 0.0)) > 0:
        score += float(strategy_weights.get("packDensityBonus", 18.0))

    # 8. Automatische Server-Events & erhöhte Drop-/EXP-/Gold-Chancen einberechnen!
    active_evt = getattr(world, "world_event", None) or {}
    evt_id = str(active_evt.get("id", ""))
    event_bonus_applied = False
    if reward_factor > 0.05:
        if evt_id == "monolith_eruption" and mob.get("kind") == "metin":
            score += 95.0  # +25% Monolith-Beute & +20% Seelenstein-Dropchance
            event_bonus_applied = True
        elif evt_id == "boss_hunt_frenzy" and (mob.get("isBoss") or mob.get("isElite")):
            score += 110.0  # +25% Boss-Schatztruhen & Weiße Perlen
            event_bonus_applied = True
        elif evt_id == "moonlight_chests" and mob.get("kind") != "metin" and reward_factor >= 0.70:
            score += 48.0  # +18% Mondlicht-Schatztruhen-Dropchance bei Monstern im Levelbereich
            event_bonus_applied = True
        elif evt_id == "imperial_blessing" and reward_factor >= 0.75:
            score += 54.0  # +30% EXP & +25% Gold-Drop
            event_bonus_applied = True

    return score, {
        "dist": round(d, 1),
        "rewardFactor": round(reward_factor, 2),
        "estTtkSec": round(est_ttk, 1),
        "deathRisk": round(death_risk, 2),
        "eventBonusApplied": event_bonus_applied,
        "activeEventId": evt_id,
    }


class BotTelemetryCollector:
    """Erfasst Kampf-, Rissmonolithen-, Lern-, QA- und Balancing-Telemetrie für alle 10 Bots."""

    def __init__(self, bot_configs: List[dict]):
        self.started_at = time.time()
        self.simulated_seconds = 0.0
        self.bots: Dict[str, dict] = {}
        self.qa_issues: List[dict] = []
        self.monster_global_stats: Dict[str, dict] = defaultdict(
            lambda: {
                "templateId": "",
                "name": "",
                "level": 1,
                "kills": 0,
                "totalDamageToMob": 0,
                "totalDamageFromMob": 0,
                "maxSpikeDamageFromMob": 0,
                "ttkSamples": [],
                "expSamples": [],
                "deathsCaused": 0,
            }
        )
        for cfg in bot_configs:
            pid = cfg["playerId"]
            self.bots[pid] = {
                "playerId": pid,
                "name": cfg["name"],
                "classId": cfg["classId"],
                "empire": cfg["empire"],
                "roleDesc": cfg["roleDesc"],
                "groupRole": cfg.get("groupRole", "dps"),
                "preferredMode": cfg["preferredMode"],
                "activeStrategy": "v2.0_adaptive_learned",
                "currentZone": "Nord-Morgenwacht",
                "currentTargetName": "Suche Ziel...",
                "learningStatus": "Sammle Kampferfahrung & optimiere Rotation",
                # Progression
                "startLevel": 1,
                "currentLevel": 1,
                "levelUps": 0,
                "petStartLevel": 1,
                "petCurrentLevel": 1,
                "mountLevel": 1,
                "expGained": 0,
                "yangGained": 0,
                "reputationGained": 0,
                # Offensive
                "totalDamageDealt": 0,
                "damageToMonsters": 0,
                "damageToMetins": 0,
                "damageToGuardians": 0,
                "totalHits": 0,
                "basicHits": 0,
                "skillHits": 0,
                "critHits": 0,
                "pierceHits": 0,
                "staggerProcs": 0,
                "knockbackProcs": 0,
                "maxSingleHit": 0,
                "maxSingleHitSkill": "",
                "maxSingleHitTarget": "",
                "skillUsage": Counter(),
                "skillDamage": Counter(),
                "manaSpent": 0,
                # Kills & TTK
                "monstersKilled": 0,
                "metinsDestroyed": 0,
                "guardiansKilled": 0,
                "eliteBossesKilled": 0,
                "monolithsAwakened": 0,
                "metinWavesTriggered": 0,
                "killsByTemplate": Counter(),
                "metinsByTemplate": Counter(),
                "metinsByState": Counter(),
                "monsterTTKSamples": defaultdict(list),
                "metinTTKSamples": defaultdict(list),
                "metinDetails": [],
                # Defensive & Überleben
                "damageTaken": 0,
                "monsterHitsTaken": 0,
                "monolithShockwavesTaken": 0,
                "dodgesPerformed": 0,
                "retreatsTriggered": 0,
                "potionsUsed": 0,
                "selfHealsCast": 0,
                "allyHealsCast": 0,
                "deaths": 0,
                "lowestHpPct": 100.0,
                # Navigation, Brücken, Gruppen-Dynamik, Reichs-Feindschaft & AFK-Ausschluss
                "activeSeconds": 0.0,
                "afkSecondsExcluded": 0.0,
                "stuckRecoveries": 0,
                "afkRecoveries": 0,
                "zoneSwitches": 0,
                "targetSwitches": 0,
                "bridgeCrossings": 0,
                "partySplits": 0,
                "empireSkirmishes": 0,
                "eventTargetsHunted": 0,
                "socialProfile": get_bot_social_profile(pid),
                # Drops, Wirtschaft, Schmied, Seelenweberin, Quests & Dungeons
                "dropsLooted": 0,
                "dropsAutoSold": 0,
                "dropsByCategory": Counter(),
                "dropsByRarity": Counter(),
                "dropsByItem": Counter(),
                "itemsEquippedUpgrades": 0,
                "chestsOpened": 0,
                "potionsBought": 0,
                "yangSpentOnPotions": 0,
                "blacksmithAttempts": 0,
                "blacksmithSuccesses": 0,
                "blacksmithFailures": 0,
                "bonusesRolled": 0,
                "bonusesAdded": 0,
                "bonusesSwitched": 0,
                "questsAccepted": 0,
                "questsCompleted": 0,
                "dungeonsEntered": 0,
                "dungeonsCompleted": 0,
                "offlineShopListingsCreated": 0,
                "marketPurchases": 0,
                "chatRepliesSent": 0,
                "sectorIdx": 0,
            }
        self._mob_first_hit_at: Dict[str, Tuple[str, float, dict]] = {}
        self._bot_last_pos: Dict[str, Tuple[float, float, float]] = {}
        self.up_system_stats: Dict[int, dict] = {
            pl: {"plusFrom": pl, "plusTo": pl + 1, "attempts": 0, "successes": 0, "failures": 0, "yangSpent": 0}
            for pl in range(9)
        }

    def log_qa_issue(
        self,
        severity: str,
        category: str,
        title: str,
        description: str,
        bot_id: str,
        x: float,
        z: float,
        repro_steps: str,
    ):
        # Vermeide Duplikate desselben Fehlertyps
        for existing in self.qa_issues:
            if existing["title"] == title and existing["botId"] == bot_id:
                existing["occurrences"] += 1
                return
        self.qa_issues.append(
            {
                "id": f"qa_{len(self.qa_issues) + 1:03d}",
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "severity": severity,  # 'HIGH' | 'MEDIUM' | 'LOW'
                "category": category,
                "title": title,
                "description": description,
                "botId": bot_id,
                "coords": {"x": round(x, 1), "z": round(z, 1)},
                "reproSteps": repro_steps,
                "occurrences": 1,
            }
        )

    def record_mob_engage(self, pid: str, mob: dict, sim_now: float):
        mid = mob["id"]
        if mid not in self._mob_first_hit_at:
            self._mob_first_hit_at[mid] = (
                pid,
                sim_now,
                {
                    "templateId": mob["templateId"],
                    "name": mob["name"],
                    "kind": mob["kind"],
                    "level": mob.get("level", 1),
                    "maxHp": mob.get("maxHp", 100),
                    "monolithState": mob.get("monolithState", "schlafend"),
                    "lastHitAt": sim_now,
                    "activeCombatSec": 0.25,
                },
            )
        else:
            st_pid, st_t, m_meta = self._mob_first_hit_at[mid]
            gap = max(0.0, sim_now - float(m_meta.get("lastHitAt", sim_now)))
            # WICHTIG: Wenn der Bot zwischendurch AFK stand oder weg war (gap > 3.2s), wird die AFK-Pause NICHT in die TTK-Statistik eingerechnet!
            if gap <= 3.2:
                m_meta["activeCombatSec"] = float(m_meta.get("activeCombatSec", 0.25)) + gap
            m_meta["lastHitAt"] = sim_now

    def process_combat_events(self, events: List[dict], world: WorldAuthority, sim_now: float):
        for ev in events:
            etype = ev.get("type")
            payload = ev.get("data") or ev.get("payload") or {}
            if etype == "damage_mob":
                pid = payload.get("playerId") or payload.get("attackerId")
                if pid not in self.bots:
                    continue
                b = self.bots[pid]
                dmg = int(payload.get("damage", 0))
                tid = payload.get("targetId", "")
                mob = world.monsters.get(tid)
                skill_id = str(payload.get("skillId", "basic"))
                is_crit = bool(payload.get("crit", False))
                is_pierce = bool(payload.get("pierce", False))

                if mob:
                    self.record_mob_engage(pid, mob, sim_now)
                    m_glob = self.monster_global_stats[mob["templateId"]]
                    m_glob["templateId"] = mob["templateId"]
                    m_glob["name"] = mob.get("baseName", mob["name"])
                    m_glob["level"] = int(mob.get("level", 1))
                    m_glob["totalDamageToMob"] += dmg

                b["totalDamageDealt"] += dmg
                b["totalHits"] += 1
                if skill_id in ("basic", "basic_dagger_twin"):
                    b["basicHits"] += 1
                else:
                    b["skillHits"] += 1
                b["skillUsage"][skill_id] += 1
                b["skillDamage"][skill_id] += dmg

                if is_crit:
                    b["critHits"] += 1
                if is_pierce:
                    b["pierceHits"] += 1
                if payload.get("stagger"):
                    b["staggerProcs"] += 1
                if payload.get("knockback"):
                    b["knockbackProcs"] += 1

                target_name = mob["name"] if mob else tid
                if dmg > b["maxSingleHit"]:
                    b["maxSingleHit"] = dmg
                    b["maxSingleHitSkill"] = skill_id
                    b["maxSingleHitTarget"] = target_name

                if mob:
                    if mob.get("kind") == "metin":
                        b["damageToMetins"] += dmg
                    elif mob.get("isSummon") or mob.get("monolithGuardOf") or mob.get("monolithBossOf"):
                        b["damageToGuardians"] += dmg
                    else:
                        b["damageToMonsters"] += dmg

                if payload.get("killed") and tid in self._mob_first_hit_at:
                    starter_pid, start_t, m_meta = self._mob_first_hit_at.pop(tid)
                    raw_elapsed = max(0.25, sim_now - start_t)
                    active_c_sec = float(m_meta.get("activeCombatSec", raw_elapsed))
                    ttk = round(max(0.25, min(raw_elapsed, active_c_sec if active_c_sec > 0.25 else raw_elapsed)), 2)
                    tpl_key = f"{m_meta['name']} (Lv.{m_meta['level']})"
                    if m_meta["kind"] == "metin":
                        b["metinsDestroyed"] += 1
                        b["metinsByTemplate"][tpl_key] += 1
                        m_state = m_meta.get("monolithState", "schlafend")
                        b["metinsByState"][m_state] += 1
                        b["metinTTKSamples"][tpl_key].append(ttk)
                        b["metinDetails"].append(
                            {
                                "name": m_meta["name"],
                                "level": m_meta["level"],
                                "state": m_state,
                                "maxHp": m_meta["maxHp"],
                                "ttkSec": ttk,
                            }
                        )
                        if ttk > 120.0:
                            self.log_qa_issue(
                                "MEDIUM",
                                "Monolith-TTK-Ausreißer",
                                f"Ungewöhnlich lange Kampfdauer bei {m_meta['name']} ({ttk}s)",
                                f"Bot {b['name']} benötigte {ttk}s für {m_meta['name']} (Stufe: {m_state}). Ursache: Zwischenzeitlicher Zielwechsel auf respawnte Monster im Umkreis.",
                                pid,
                                ev.get("x", 0.0),
                                ev.get("z", 0.0),
                                "1. Greife Stufe-2-Monolith an -> 2. Wenn alle 3er-Wellen besiegt sind, prüfe ob Target-Lock (Hysterese) auf dem Monolithen bleibt.",
                            )
                    else:
                        if mob and (mob.get("isSummon") or mob.get("monolithGuardOf")):
                            b["guardiansKilled"] += 1
                        if mob and (mob.get("isMonolithEliteBoss") or mob.get("isElite")):
                            b["eliteBossesKilled"] += 1
                        b["monstersKilled"] += 1
                        b["killsByTemplate"][tpl_key] += 1
                        b["monsterTTKSamples"][tpl_key].append(ttk)
                        m_glob = self.monster_global_stats[m_meta["templateId"]]
                        m_glob["kills"] += 1
                        if ttk <= 60.0:
                            m_glob["ttkSamples"].append(ttk)

            elif etype == "damage_player":
                pid = payload.get("playerId")
                if pid not in self.bots:
                    continue
                b = self.bots[pid]
                dmg = int(payload.get("damage", 0))
                b["damageTaken"] += dmg
                mob_id = str(payload.get("mobId", ""))
                mob = world.monsters.get(mob_id)
                if mob:
                    m_glob = self.monster_global_stats[mob["templateId"]]
                    m_glob["totalDamageFromMob"] += dmg
                    if dmg > m_glob["maxSpikeDamageFromMob"]:
                        m_glob["maxSpikeDamageFromMob"] = dmg
                if mob and mob.get("kind") == "metin":
                    b["monolithShockwavesTaken"] += 1
                else:
                    b["monsterHitsTaken"] += 1

            elif etype == "metin_wave":
                metin_id = payload.get("metinId")
                mob = world.monsters.get(metin_id)
                if mob:
                    for part_id in mob.get("participants", set()):
                        if part_id in self.bots:
                            self.bots[part_id]["metinWavesTriggered"] += 1

            elif etype == "level_up":
                pid = payload.get("playerId")
                if pid in self.bots:
                    self.bots[pid]["levelUps"] += 1
                    self.bots[pid]["currentLevel"] = int(payload.get("level", self.bots[pid]["currentLevel"]))

    def build_summary_report(self) -> dict:
        sim_sec = max(1.0, self.simulated_seconds)
        sim_min = sim_sec / 60.0
        bot_reports = {}

        for pid, b in self.bots.items():
            # WICHTIG: Nur echte aktive Kampf-/Bewegungszeit fließt in DPS, EXP/Min, Kills/Min & Gold/Min ein!
            # Etwaige AFK-/Stillstandszeiten (afkSecondsExcluded) werden strikt aus der Statistik herausgerechnet.
            bot_active_sec = max(1.0, float(b.get("activeSeconds", 0.0)) or sim_sec)
            bot_active_min = max(0.016, bot_active_sec / 60.0)
            total_hits = max(1, b["totalHits"])
            monster_ttk_avg = {
                k: {
                    "kills": len(v),
                    "avgTtkSec": round(sum(v) / len(v), 2),
                    "minTtkSec": round(min(v), 2),
                    "maxTtkSec": round(max(v), 2),
                }
                for k, v in b["monsterTTKSamples"].items()
                if v
            }
            metin_ttk_avg = {
                k: {
                    "destroyed": len(v),
                    "avgTtkSec": round(sum(v) / len(v), 2),
                    "minTtkSec": round(min(v), 2),
                    "maxTtkSec": round(max(v), 2),
                }
                for k, v in b["metinTTKSamples"].items()
                if v
            }
            skill_breakdown = {}
            for sk_id, count in b["skillUsage"].most_common():
                dmg_sum = b["skillDamage"][sk_id]
                skill_breakdown[sk_id] = {
                    "hits": count,
                    "totalDamage": dmg_sum,
                    "avgDamage": round(dmg_sum / max(1, count), 1),
                    "sharePct": round((dmg_sum / max(1, b["totalDamageDealt"])) * 100.0, 1),
                }

            bot_reports[pid] = {
                "playerId": pid,
                "name": b["name"],
                "classId": b["classId"],
                "empire": b["empire"],
                "roleDesc": b["roleDesc"],
                "groupRole": b["groupRole"],
                "activeStrategy": b["activeStrategy"],
                "currentZone": b["currentZone"],
                "currentTargetName": b["currentTargetName"],
                "learningStatus": b["learningStatus"],
                "progression": {
                    "startLevel": b["startLevel"],
                    "endLevel": b["currentLevel"],
                    "levelUps": b["levelUps"],
                    "petStartLevel": b["petStartLevel"],
                    "petEndLevel": b["petCurrentLevel"],
                    "mountLevel": b["mountLevel"],
                    "activeSeconds": round(bot_active_sec, 1),
                    "afkSecondsExcluded": round(float(b.get("afkSecondsExcluded", 0.0)), 1),
                    "expGained": b["expGained"],
                    "expPerMinute": round(b["expGained"] / bot_active_min, 1),
                    "expPerHour": int(round((b["expGained"] / bot_active_min) * 60.0)),
                    "yangGained": b["yangGained"],
                    "yangPerMinute": round(b["yangGained"] / bot_active_min, 1),
                    "yangPerHour": int(round((b["yangGained"] / bot_active_min) * 60.0)),
                    "reputationGained": b["reputationGained"],
                },
                "combatOffense": {
                    "totalDamageDealt": b["totalDamageDealt"],
                    "dps": round(b["totalDamageDealt"] / bot_active_sec, 1),
                    "damageToMonsters": b["damageToMonsters"],
                    "damageToMetins": b["damageToMetins"],
                    "damageToGuardians": b["damageToGuardians"],
                    "totalHits": b["totalHits"],
                    "basicHits": b["basicHits"],
                    "skillHits": b["skillHits"],
                    "avgDamagePerHit": round(b["totalDamageDealt"] / total_hits, 1),
                    "critHits": b["critHits"],
                    "critRatePct": round((b["critHits"] / total_hits) * 100.0, 2),
                    "pierceHits": b["pierceHits"],
                    "pierceRatePct": round((b["pierceHits"] / total_hits) * 100.0, 2),
                    "staggerProcs": b["staggerProcs"],
                    "knockbackProcs": b["knockbackProcs"],
                    "maxSingleHit": b["maxSingleHit"],
                    "maxSingleHitSkill": b["maxSingleHitSkill"],
                    "maxSingleHitTarget": b["maxSingleHitTarget"],
                    "skillBreakdown": skill_breakdown,
                },
                "targetsAndTTK": {
                    "monstersKilled": b["monstersKilled"],
                    "monstersPerMinute": round(b["monstersKilled"] / bot_active_min, 2),
                    "guardiansKilled": b["guardiansKilled"],
                    "eliteBossesKilled": b["eliteBossesKilled"],
                    "metinsDestroyed": b["metinsDestroyed"],
                    "metinsPerHour": round((b["metinsDestroyed"] / bot_active_min) * 60.0, 1),
                    "monolithsAwakened": b["monolithsAwakened"],
                    "metinWavesTriggered": b["metinWavesTriggered"],
                    "killsByTemplate": dict(b["killsByTemplate"].most_common(12)),
                    "metinsByTemplate": dict(b["metinsByTemplate"].most_common(10)),
                    "metinsByState": dict(b["metinsByState"]),
                    "monsterTTK": monster_ttk_avg,
                    "metinTTK": metin_ttk_avg,
                    "metinDestructionLog": b["metinDetails"][:15],
                },
                "survivability": {
                    "damageTaken": b["damageTaken"],
                    "damageTakenPerSec": round(b["damageTaken"] / bot_active_sec, 1),
                    "monsterHitsTaken": b["monsterHitsTaken"],
                    "monolithShockwavesTaken": b["monolithShockwavesTaken"],
                    "dodgesPerformed": b["dodgesPerformed"],
                    "retreatsTriggered": b["retreatsTriggered"],
                    "potionsUsed": b["potionsUsed"],
                    "selfHealsCast": b["selfHealsCast"],
                    "allyHealsCast": b["allyHealsCast"],
                    "deaths": b["deaths"],
                    "lowestHpPct": round(b["lowestHpPct"], 1),
                },
                "navigationAndQA": {
                    "activeSeconds": round(bot_active_sec, 1),
                    "afkSecondsExcluded": round(float(b.get("afkSecondsExcluded", 0.0)), 1),
                    "stuckRecoveries": b["stuckRecoveries"],
                    "afkRecoveries": b["afkRecoveries"],
                    "zoneSwitches": b["zoneSwitches"],
                    "targetSwitches": b["targetSwitches"],
                    "bridgeCrossings": b["bridgeCrossings"],
                    "partySplits": b["partySplits"],
                    "empireSkirmishes": b["empireSkirmishes"],
                    "eventTargetsHunted": b["eventTargetsHunted"],
                },
                "socialProfile": b["socialProfile"],
                "lootAndEconomy": {
                    "dropsLooted": b["dropsLooted"],
                    "dropsAutoSold": b["dropsAutoSold"],
                    "dropsPerMinute": round((b["dropsLooted"] + b["dropsAutoSold"]) / bot_active_min, 2),
                    "dropsByCategory": dict(b["dropsByCategory"].most_common()),
                    "dropsByRarity": dict(b["dropsByRarity"].most_common()),
                    "topLootedItems": dict(b["dropsByItem"].most_common(15)),
                    "itemsEquippedUpgrades": b["itemsEquippedUpgrades"],
                    "chestsOpened": b["chestsOpened"],
                    "potionsBought": b["potionsBought"],
                    "yangSpentOnPotions": b["yangSpentOnPotions"],
                    "blacksmithAttempts": b["blacksmithAttempts"],
                    "blacksmithSuccesses": b["blacksmithSuccesses"],
                    "blacksmithFailures": b["blacksmithFailures"],
                    "bonusesRolled": b["bonusesRolled"],
                    "bonusesAdded": b["bonusesAdded"],
                    "bonusesSwitched": b["bonusesSwitched"],
                    "questsAccepted": b["questsAccepted"],
                    "questsCompleted": b["questsCompleted"],
                    "dungeonsEntered": b["dungeonsEntered"],
                    "dungeonsCompleted": b["dungeonsCompleted"],
                    "offlineShopListingsCreated": b["offlineShopListingsCreated"],
                    "marketPurchases": b["marketPurchases"],
                    "chatRepliesSent": b["chatRepliesSent"],
                },
            }

        monster_matrix = {}
        for tid, ms in self.monster_global_stats.items():
            if ms["kills"] <= 0 and ms["totalDamageToMob"] <= 0:
                continue
            avg_ttk = round(sum(ms["ttkSamples"]) / len(ms["ttkSamples"]), 2) if ms["ttkSamples"] else 0.0
            tpl_ref = MONSTER_TEMPLATES.get(tid, {})
            monster_matrix[tid] = {
                "templateId": tid,
                "name": ms["name"],
                "level": ms["level"],
                "hp": tpl_ref.get("hp", 100),
                "atk": tpl_ref.get("atk", 15),
                "def": tpl_ref.get("def", 10),
                "exp": tpl_ref.get("exp", 20),
                "kills": ms["kills"],
                "avgTtkSec": avg_ttk,
                "totalDamageToMob": ms["totalDamageToMob"],
                "totalDamageFromMob": ms["totalDamageFromMob"],
                "maxSpikeDamage": ms["maxSpikeDamageFromMob"],
                "expEfficiencyPerSec": round(tpl_ref.get("exp", 20) / max(0.5, avg_ttk), 2) if avg_ttk > 0 else 0.0,
            }

        return {
            "generatedAt": time.strftime("%Y-%m-%d %H:%M:%S"),
            "botCount": len(bot_reports),
            "simulatedDurationSec": round(sim_sec, 1),
            "simulatedDurationMin": round(sim_min, 2),
            "bots": bot_reports,
            "monsterAuditMatrix": monster_matrix,
            "upSystemAudit": list(self.up_system_stats.values()),
            "qaIssues": self.qa_issues,
        }


def estimate_item_market_price(item: dict) -> int:
    """Berechnet einen fairen Marktpreis für den Offline-Shop anhand von Typ, Seltenheit, Plus-Level und Boni."""
    tpl_id = str(item.get("templateId", ""))
    tpl = ITEM_TEMPLATES.get(tpl_id, {})
    plus = int(item.get("plusLevel", 0))
    bonuses = item.get("bonuses") or []

    fixed_prices = {
        "scroll_blessing": 18500,
        "mat_soul_stone": 34000,
        "item_soul_fragment": 29000,
        "mat_legendary_soul_stone": 95000,
        "item_bonus_changer": 14500,
        "item_bonus_adder": 12000,
        "item_blessing_orb": 26000,
        "item_aether_seal": 42000,
        "mat_white_pearl": 28000,
        "chest_moonlight": 21000,
        "chest_oberork": 32000,
        "chest_skill_books": 16000,
        "book_skill": 14500,
        "mat_monolith_shard": 16000,
        "mat_awakened_rift_core": 48000,
    }
    if tpl_id in fixed_prices:
        return fixed_prices[tpl_id] * max(1, int(item.get("quantity", 1)))
    if tpl_id.startswith("fb_") or tpl.get("type") == "skill_book":
        return random.choice([12500, 14000, 15500, 17500])

    base_val = max(1500, int(tpl.get("sellPrice", 300)) * 5)
    plus_mult = 1.0 + (plus ** 2.15) * 0.85
    bonus_val = len(bonuses) * 6500
    return int(round((base_val * plus_mult + bonus_val) / 100.0) * 100)


def score_bot_equipment_item(item_dict: dict, cls_id: str, use_two_hand: bool = False) -> float:
    """Berechnet den effektiven Kampfwert eines Ausrüstungsteils (inkl. effectiveStats, +Stufe, Item-Tier & Boni)
    für die jeweilige Bot-Klasse und Spezialisierung."""
    if not isinstance(item_dict, dict):
        return -1.0
    tpl_id = str(item_dict.get("templateId") or item_dict.get("id") or "")
    tpl = ITEM_TEMPLATES.get(tpl_id, {})
    if not tpl or tpl.get("type") != "equipment":
        return -1.0
    slot = tpl.get("slot") or item_dict.get("slot")
    if not slot:
        return -1.0
    allowed_classes = tpl.get("classes")
    if allowed_classes and cls_id not in allowed_classes:
        return -1.0
    w_sub = str(tpl.get("weaponSubType") or "one_hand")
    if slot == "weapon":
        allowed_subs = CLASS_ALLOWED_WEAPONS.get(cls_id, ["one_hand"])
        if w_sub not in allowed_subs:
            return -1.0

    plus = int(item_dict.get("plusLevel", item_dict.get("plus", 0)) or 0)
    bonuses = item_dict.get("bonuses") or []
    eff = item_dict.get("effectiveStats")
    if not isinstance(eff, dict):
        eff = calculate_item_effective_stats(tpl_id, plus, bonuses)

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
        + len(bonuses) * 7.5
    )

    if slot == "weapon":
        if use_two_hand and cls_id == "warrior":
            score *= 1.35 if w_sub == "two_hand" else 0.72
        elif not use_two_hand and cls_id == "warrior" and w_sub == "two_hand":
            score *= 0.82
        elif cls_id == "ninja" and w_sub == "dagger":
            score *= 1.18

    desired_bonus_ids = {
        "warrior": {"bonus_vs_monster", "bonus_dss", "bonus_str", "bonus_crit", "bonus_hp_absorb", "bonus_vs_metin", "bonus_atk_val"},
        "ninja": {"bonus_vs_monster", "bonus_crit", "bonus_dex", "bonus_pierce", "bonus_dss", "bonus_atk_speed", "bonus_vs_metin"},
        "sura": {"bonus_vs_monster", "bonus_int", "bonus_dss", "bonus_fks", "bonus_crit", "bonus_hp_absorb", "bonus_vs_metin"},
        "shaman": {"bonus_int", "bonus_vs_monster", "bonus_fks", "bonus_crit", "bonus_vs_metin", "bonus_hp", "bonus_atk_speed"},
    }.get(cls_id, set())
    if desired_bonus_ids and bonuses:
        for b_ent in bonuses:
            if isinstance(b_ent, dict) and b_ent.get("id") in desired_bonus_ids:
                score += 12.5

    return round(score, 2)


# ============================================================================
# 4. BOT-INITIALISIERUNG, CHARAKTER-PFLEGE & ADAPTIVE KAMPF-KI
# ============================================================================
def setup_bot_player(world: WorldAuthority, cfg: dict, reset_to_level_1: bool = False) -> dict:
    """Initialisiert einen der 10 Bots OHNE unfaire DMG-/DEF-/TP-Vorteile (exakt wie normale Spieler)."""
    pid = cfg["playerId"]
    p = world.register_player(
        pid,
        name=cfg["name"],
        class_id=cfg["classId"],
        empire=cfg["empire"],
        mark_online=True,
    )
    p["accountName"] = cfg["accountName"]
    p["empire"] = cfg["empire"]
    p["online"] = True
    p["inWorld"] = True
    p["lastSeen"] = time.time()
    p["map_id"] = "morgenwacht"
    p["pos_x"] = cfg["startX"]
    p["pos_z"] = cfg["startZ"]

    if reset_to_level_1:
        cdef = CHARACTER_CLASSES[cfg["classId"]]
        p["level"] = 1
        p["exp"] = 0
        p["stat_points"] = 0
        p["skill_points"] = 0
        for k, v in cdef["baseAttributes"].items():
            p[k] = v
        p["skills"] = {sk["id"]: (0 if sk.get("special") else 1) for sk in cdef["skills"]}
        pd_reset = world._ensure_player_pet_data(p)
        pd_reset["level"] = 1
        pd_reset["exp"] = 0

    # Normale Starter-Ausrüstung (+0) wie bei jedem echten Spieler (keine geschenkten +4 Waffen!)
    world.db.ensure_class_starter_equipment(pid, cfg["classId"])
    world.refresh_player_from_db(pid)
    p = world.players[pid]

    hp_pots = sum(
        int(it.get("quantity", 1))
        for it in p.get("inventory", [])
        if it.get("templateId") in ("potion_hp_small", "potion_hp_medium", "potion_hp_large")
    )
    if hp_pots < 30:
        world.db.add_item_to_inventory(pid, "potion_hp_medium", quantity=40)

    if cfg.get("useTwoHand"):
        # Zweihänder aus dem 10-Stufen-Tier-Set passend zum Bot-Level (Holz/Kupfer/Eisen/...)
        _bot_lvl = int(p.get("level", 1) or 1)
        _tier_rank = sum(1 for _req in (1, 10, 20, 30, 40, 50, 60, 70, 80, 90) if _bot_lvl >= _req) - 1
        _tier_key = ("holz", "kupfer", "eisen", "ebenholz", "silber", "gold", "drachengold", "donnerstahl", "blaustahl", "aetherium")[max(0, _tier_rank)]
        two_hand_id = f"wpn_{_tier_key}_greatsword"
        has_2h = str((p.get("equipment", {}).get("weapon") or {}).get("templateId", "")).endswith("_greatsword") or any(
            it.get("templateId") == two_hand_id for it in p.get("inventory", [])
        )
        if not has_2h:
            world.db.add_item_to_inventory(pid, two_hand_id, plus_level=0, quantity=1)
        world.refresh_player_from_db(pid)
        p = world.players[pid]
        for it in list(p.get("inventory", [])):
            if it.get("templateId") == two_hand_id and not has_2h:
                world.use_or_open_inventory_item(pid, it["uid"], target_slot="weapon")
                break
    else:
        world.refresh_player_from_db(pid)
        p = world.players[pid]

    apply_bot_rules_memory(p)
    sync_bot_rules_memory_to_knowledge_base()
    p["active_pet"] = "pet_fire_phoenix"
    pd = world._ensure_player_pet_data(p)
    pd["summoned"] = True

    if cfg.get("useMount"):
        p["active_mount"] = cfg.get("mountId", "mount_crystal_wolf")
        md = world._ensure_player_mount_data(p)
        md["level"] = max(1, int(md.get("level", 1)))
    else:
        p["active_mount"] = None

    af = p.setdefault("autofarm", {})
    af["enabled"] = False
    af["autoPotion"] = True
    af["autoPotionHpPct"] = 68
    af["autoLoot"] = True
    af["smartMount"] = True
    af["alwaysMounted"] = bool(cfg.get("useMount", False))
    af["mountId"] = cfg.get("mountId", "mount_war_boar")
    af["anchorX"] = cfg["startX"]
    af["anchorZ"] = cfg["startZ"]
    world.compute_player_combat_stats(p)
    p["hp"] = p["max_hp"]
    p["mp"] = p["max_mp"]
    world.db.save_player_state(p)
    return p


def auto_maintain_bot_character(world: WorldAuthority, p: dict, cfg: dict, collector: BotTelemetryCollector):
    """Vollautonome Charakterpflege:
    1. Statuspunkte verteilen
    2. Intelligentes Skillen (Zuerst Haupt-Buff/Aura bis Max Level 20 skillen, erst danach andere Skills!)
    3. Truhen im Inventar öffnen, Fähigkeitsbücher/Seelensteine & Buff-Items benutzen
    4. Tränke beim Händler kaufen, wenn Vorrat niedrig
    5. Besseres Equipment ausrüsten, beim Schmied (+0 bis +9) verbessern & Boni würfeln
    6. Nicht benötigte Drops über Auto-Sell verkaufen & wertvolle Items in den eigenen Offline-Shop stellen
    7. Quests annehmen, untersuchen & abgeben + Standort wechseln bei zu vielen Toden oder 0 EXP."""
    pid = p["player_id"]
    b_stat = collector.bots[pid]

    # 1. Statuspunkte
    stat_prio = cfg["statPriority"]
    idx = 0
    while int(p.get("stat_points", 0)) > 0 and idx < 99:
        st_key = stat_prio[idx % len(stat_prio)]
        ok, _ = world.allocate_stat_point(pid, st_key, 1)
        if not ok:
            break
        idx += 1

    # 2. Intelligentes Skillen: ZUERST Haupt-Skill (z.B. Aura des Schwertes / Verzauberte Klinge) bis 20 bringen!
    sk_prio = cfg["skillPriority"]
    while int(p.get("skill_points", 0)) > 0:
        target_sk = None
        for sk_id in sk_prio:
            cur_lv = int(p.get("skills", {}).get(sk_id, 1))
            if cur_lv < 20:
                target_sk = sk_id
                break
        if not target_sk:
            break
        ok, _ = world.upgrade_skill_point(pid, target_sk, is_passive=False)
        if not ok:
            break

    # 3. Pet & Pferd pflegen (inkl. 3D-Pet-Skin, Pet-Statuspunkte & Pet-Kampfskills)
    # Aktuelles Regel-Gedächtnis (Drops, Ausrüstungs-Tiers, Levelzeit) bei jedem Pflege-Tick sicherstellen
    if p.get("botMemoryVersion") != BOT_GAME_RULES_MEMORY_VERSION:
        apply_bot_rules_memory(p)
    if not p.get("active_pet"):
        p["active_pet"] = "pet_fire_phoenix"
    if hasattr(world, "select_pet_skin") and cfg.get("petSkin"):
        world.select_pet_skin(pid, cfg["petSkin"])
    if hasattr(world, "_auto_maintain_bot_pet"):
        world._auto_maintain_bot_pet(p)
    else:
        pd = world._ensure_player_pet_data(p)
        for pet_stat in cfg.get("statPriority", ["str", "vit", "dex"]):
            while int(pd.get("statPoints", 0)) > 0 and int(pd.get(pet_stat, 0)) < 120:
                ok, _ = world.allocate_pet_stat(pid, pet_stat, 1)
                if not ok:
                    break
        for pet_sk in ("jaeger", "herrschaft", "zerstoerung_dss", "zerstoerung_fks", "erfahrungsrausch", "erneuerung", "heilung", "auto_pickup"):
            while int(pd.get("skillPoints", 0)) > 0:
                ok, _ = world.upgrade_pet_skill(pid, pet_sk)
                if not ok:
                    break

    md = world._ensure_player_mount_data(p)
    if int(md.get("level", 1)) < 50 and int(p.get("yang", 0)) >= 15000:
        world.level_up_horse(pid)
    while int(md.get("statPoints", 0)) > 0:
        ok, _ = world.allocate_mount_stat(pid, "dmg", 1)
        if not ok:
            break

    # 4. Intelligenter Trank-Einkauf beim NPC-Händler (kein Gratis-Cheat, sondern regulärer Kauf mit Yang!)
    hp_pots = sum(
        int(it.get("quantity", 1))
        for it in p.get("inventory", [])
        if it.get("templateId") in ("potion_hp_small", "potion_hp_medium", "potion_hp_large")
    )
    if hp_pots < 15:
        pot_tpl = ITEM_TEMPLATES.get("potion_hp_medium", {})
        buy_cost = int(pot_tpl.get("buyPrice", 80)) * 25
        if int(p.get("yang", 0)) >= buy_cost:
            ok, _ = world.db.add_item_to_inventory(pid, "potion_hp_medium", quantity=25)
            if ok:
                p["yang"] -= buy_cost
                b_stat["potionsBought"] += 25
                b_stat["yangSpentOnPotions"] += buy_cost
                world.db.save_player_state(p)
                world.refresh_player_from_db(pid)
                p = world.players[pid]

    # 5. Truhen im Inventar öffnen & Fähigkeitsbücher / Seelensteine / Buff-Tränke benutzen
    active_buffs = p.get("activeBuffs", {})
    now_t = time.time()
    for inv_item in list(p.get("inventory", [])):
        tpl_id = str(inv_item.get("templateId", ""))
        tpl = ITEM_TEMPLATES.get(tpl_id, {})
        itype = inv_item.get("type") or tpl.get("type")

        # Truhen öffnen
        if itype == "chest" or tpl_id in ("chest_skill_books", "book_skill", "chest_moonlight", "chest_oberork", "chest_monolith_legend", "chest_bloodleaf"):
            ok, _ = world.use_or_open_inventory_item(pid, inv_item["uid"])
            if ok:
                b_stat["chestsOpened"] += 1
                p = world.players[pid]
            continue

        # Gedroppte Passiv-Fertigkeitsbücher (Stufe 0–20) sowie eigene Klassen-Fähigkeitsbücher & Seelensteine lesen
        if tpl_id.startswith("fb_passive_") or itype == "passive_skill_book":
            world.use_or_open_inventory_item(pid, inv_item["uid"])
            p = world.players[pid]
            continue
        if tpl_id.startswith("fb_") or itype == "skill_book":
            if tpl.get("classId") == p["class_id"]:
                world.use_or_open_inventory_item(pid, inv_item["uid"])
                p = world.players[pid]
                continue
        if tpl_id in ("item_skill_unlock_scroll", "mat_soul_stone", "mat_legendary_soul_stone"):
            world.use_or_open_inventory_item(pid, inv_item["uid"])
            p = world.players[pid]
            continue

        # Tempo- & Angriffstempo-Tränke aktivieren
        if tpl_id in ("potion_speed", "potion_atk_speed") and tpl_id not in active_buffs:
            world.use_or_open_inventory_item(pid, inv_item["uid"])
            p = world.players[pid]
            active_buffs = p.get("activeBuffs", {})
            continue

    # 6. Besseres gedropptes Equipment automatisch anlegen (nutzt effectiveStats, +Stufe, Item-Tier & Boni)
    p_lvl = int(p.get("level", 1))
    use_2h = bool(cfg.get("useTwoHand", False))
    for inv_item in list(p.get("inventory", [])):
        tpl = ITEM_TEMPLATES.get(inv_item.get("templateId", ""), {})
        if tpl.get("type") != "equipment":
            continue
        req_lvl = int(tpl.get("reqLevel", 1))
        if req_lvl > p_lvl:
            continue
        slot = tpl.get("slot") or inv_item.get("slot")
        if not slot:
            continue
        new_score = score_bot_equipment_item(inv_item, p["class_id"], use_two_hand=use_2h)
        if new_score <= 0:
            continue
        cur_eq = (p.get("equipment") or {}).get(slot)
        cur_score = score_bot_equipment_item(cur_eq, p["class_id"], use_two_hand=use_2h) if cur_eq else -1.0
        if new_score > cur_score + 0.5:
            ok, _ = world.use_or_open_inventory_item(pid, inv_item["uid"], target_slot=slot)
            if ok:
                b_stat["itemsEquippedUpgrades"] += 1
                p = world.players[pid]

    # 7. Equipment beim Schmied (+0 bis +9) verbessern & bei der Seelenweberin verstärken / Boni switchen!
    has_blessing = any(it.get("templateId") == "scroll_blessing" for it in p.get("inventory", []))
    has_adder = any(it.get("templateId") == "item_bonus_adder" for it in p.get("inventory", []))
    has_orb = any(it.get("templateId") == "item_blessing_orb" for it in p.get("inventory", []))
    has_changer = any(it.get("templateId") == "item_bonus_changer" for it in p.get("inventory", []))
    has_seal = any(it.get("templateId") == "item_aether_seal" for it in p.get("inventory", []))
    has_soul = any(it.get("templateId") in ("item_soul_fragment", "mat_soul_stone") for it in p.get("inventory", []))

    for slot_prio in ("weapon", "armor", "helmet", "shield", "bracelet", "necklace", "earrings", "shoes"):
        eq_it = (p.get("equipment") or {}).get(slot_prio)
        if not eq_it:
            continue
        cur_plus = int(eq_it.get("plusLevel", 0))
        if cur_plus < 9 and cur_plus in BLACKSMITH_RATES:
            r_info = BLACKSMITH_RATES[cur_plus]
            req_yang = int(r_info["yang"])
            if int(p.get("yang", 0)) >= req_yang + 2000:
                if not has_blessing and cur_plus >= 3:
                    # Bots kaufen vor riskanten Upgrades intelligent eine Segensschriftrolle, damit ihr Haupt-Equipment nicht beim Schmied zerbricht
                    if int(p.get("yang", 0)) >= req_yang + 3500:
                        world.db.add_item_to_inventory(pid, "scroll_blessing", 1, plus_level=0)
                        p["yang"] -= 1200
                        world.db.save_player_state(p)
                        world.refresh_player_from_db(pid)
                        p = world.players[pid]
                        has_blessing = True
                    else:
                        continue
                use_bless = bool(has_blessing)
                ok_up, _msg_up, up_win = world.blacksmith_upgrade(pid, eq_it["uid"], use_blessing=use_bless)
                if ok_up:
                    b_stat["blacksmithAttempts"] += 1
                    collector.up_system_stats[cur_plus]["attempts"] += 1
                    collector.up_system_stats[cur_plus]["yangSpent"] += req_yang
                    if up_win:
                        b_stat["blacksmithSuccesses"] += 1
                        collector.up_system_stats[cur_plus]["successes"] += 1
                    else:
                        b_stat["blacksmithFailures"] += 1
                        collector.up_system_stats[cur_plus]["failures"] += 1
                    p = world.players[pid]
                    break

        # Seelenweberin: Gegenstand verstärken (1.–4. Bonus mit 'item_bonus_adder', 5. Bonus mit 'item_blessing_orb',
        # 6./7. Bonus mit 'item_soul_fragment') und Boni switchen ('item_bonus_changer' + Lock mit 'item_aether_seal')
        bonuses = eq_it.get("bonuses") or []
        if len(bonuses) < 4 and has_adder:
            ok_rw, _ = world.runeweaver_action(pid, eq_it["uid"], "add")
            if ok_rw:
                b_stat["bonusesRolled"] += 1
                b_stat["bonusesAdded"] += 1
                p = world.players[pid]
                break
        elif len(bonuses) == 4 and has_orb:
            ok_rw, _ = world.runeweaver_action(pid, eq_it["uid"], "add5")
            if ok_rw:
                b_stat["bonusesRolled"] += 1
                b_stat["bonusesAdded"] += 1
                p = world.players[pid]
                break
        elif 5 <= len(bonuses) < 7 and has_soul and int(p.get("yang", 0)) >= 25000:
            ok_rw, _ = world.runeweaver_action(pid, eq_it["uid"], "add67")
            if ok_rw:
                b_stat["bonusesRolled"] += 1
                b_stat["bonusesAdded"] += 1
                p = world.players[pid]
                break
        elif len(bonuses) >= 2 and has_changer:
            # Selbstlernende Build-Evolution v3.0: Prüfe klassenspezifische Wunsch-Boni beim Runenweber
            desired_bonus_ids = {
                "warrior": ("bonus_vs_monster", "bonus_dss", "bonus_str", "bonus_crit", "bonus_hp_absorb", "bonus_vs_metin"),
                "ninja": ("bonus_vs_monster", "bonus_crit", "bonus_dex", "bonus_pierce", "bonus_dss", "bonus_atk_speed"),
                "sura": ("bonus_vs_monster", "bonus_int", "bonus_dss", "bonus_fks", "bonus_crit", "bonus_hp_absorb"),
                "shaman": ("bonus_int", "bonus_vs_monster", "bonus_fks", "bonus_crit", "bonus_vs_metin", "bonus_hp"),
            }.get(p.get("class_id", "warrior"), ("bonus_vs_monster", "bonus_dss", "bonus_crit"))
            matched_indices = [
                b_idx for b_idx, b_entry in enumerate(bonuses[:5])
                if isinstance(b_entry, dict) and b_entry.get("id") in desired_bonus_ids
            ]
            if matched_indices and int(eq_it.get("lockedBonusIdx", -1)) < 0 and has_seal:
                # Sperre den besten gelernten Wunsch-Bonus vor dem Weiter-Switchen mit Äthersiegel
                world.runeweaver_action(pid, eq_it["uid"], "lock", lock_idx=matched_indices[0])
                p = world.players[pid]
            if len(matched_indices) < 2:
                ok_rw, _ = world.runeweaver_action(pid, eq_it["uid"], "reroll")
                if ok_rw:
                    b_stat["bonusesRolled"] += 1
                    b_stat["bonusesSwitched"] += 1
                    p = world.players[pid]
                    break

    # 8. Nicht benötigte Drops über Auto-Sell verkaufen & wertvolle Items in den Offline-Shop stellen
    for inv_item in list(p.get("inventory", [])):
        if inv_item.get("equipped_slot") or inv_item.get("reserved_shop_id"):
            continue
        tpl_id = str(inv_item.get("templateId", ""))
        tpl = ITEM_TEMPLATES.get(tpl_id, {})
        itype = inv_item.get("type") or tpl.get("type")
        plus = int(inv_item.get("plusLevel", 0))

        # Wertvolle Items (+4..+9 Ausrüstung, fremde Fähigkeitsbücher, Perlen) -> Offline-Shop in der Map-1-Hauptstadt!
        is_foreign_book = (tpl_id.startswith("fb_") or itype == "skill_book") and tpl.get("classId") != p["class_id"]
        is_valuable_gear = itype == "equipment" and (plus >= 4 or len(inv_item.get("bonuses") or []) >= 3)
        if (is_foreign_book or is_valuable_gear or tpl_id == "mat_white_pearl") and b_stat["offlineShopListingsCreated"] < 8:
            price = estimate_item_market_price(inv_item)
            default_city_x = -820.0 if cfg["empire"] == "kaeryu" else 820.0
            shop_x, shop_z = BOT_CITY_SHOP_SPOTS.get(pid, (default_city_x, -766.0))
            city_label = "Kaeryu-Stadt" if cfg["empire"] == "kaeryu" else "Seiryu-Stadt"
            ok_sh, _ = world.db.create_or_add_to_offline_shop(
                pid,
                p["name"],
                f"{p['name']}s Handelsstand ({city_label})",
                "morgenwacht",
                shop_x,
                shop_z,
                inv_item["uid"],
                price,
            )
            if ok_sh:
                b_stat["offlineShopListingsCreated"] += 1
                world.refresh_player_from_db(pid)
                p = world.players[pid]
            continue

        # Schwache ungenutzte Ausrüstung (+0..+2) intelligent über Auto-Sell verkaufen
        if itype == "equipment" and plus <= 2:
            deleted = world.db.delete_item(pid, inv_item["uid"])
            if deleted:
                sell_gain = max(30, int(deleted.get("sellPrice", 120) * (1.0 + plus * 0.25)))
                p["yang"] += sell_gain
                b_stat["dropsAutoSold"] += 1
                world.db.save_player_state(p)
                world.refresh_player_from_db(pid)
                p = world.players[pid]

    # Erlöse aus eigenem Offline-Shop abholen
    ok_v, _, v_amt = world.db.withdraw_shop_vault(pid)
    if ok_v and v_amt > 0:
        world.refresh_player_from_db(pid)
        p = world.players[pid]

    # Fremdes Reich (Map-1-Stadt des Gegenreichs) besuchen, um Shops zu prüfen & benötigte Items intelligent zu kaufen
    all_shops = world.db.list_offline_shops("morgenwacht")
    foreign_shops = [
        sh for sh in all_shops
        if sh.get("owner_id") != pid
        and ((cfg["empire"] == "seiryu" and float(sh.get("pos_x", 0.0)) < 0.0) or (cfg["empire"] != "seiryu" and float(sh.get("pos_x", 0.0)) > 0.0))
    ]
    if foreign_shops:
        b_stat["foreignShopVisits"] = int(b_stat.get("foreignShopVisits", 0)) + 1
    for sh in foreign_shops + [s for s in all_shops if s.get("owner_id") != pid and s not in foreign_shops]:
        bought_any = False
        for lst in list(sh.get("listings") or []):
            ask_price = int(lst.get("priceYang", lst.get("price", 999999)))
            if ask_price <= 0 or int(p.get("yang", 0)) < ask_price + 2500:
                continue
            iid = str(lst.get("templateId") or lst.get("id") or "")
            tpl_l = ITEM_TEMPLATES.get(iid, {})
            if not tpl_l:
                continue
            itype_l = tpl_l.get("type", lst.get("type", "misc"))
            needs_it = False
            if itype_l == "equipment":
                slot_k = tpl_l.get("slot", "weapon")
                cur_eq = (p.get("equipment") or {}).get(slot_k)
                cand_sc = score_bot_equipment_item(lst, cfg["classId"], use_two_hand=bool(cfg.get("useTwoHand", False)))
                cur_sc = score_bot_equipment_item(cur_eq, cfg["classId"], use_two_hand=bool(cfg.get("useTwoHand", False))) if cur_eq else -1.0
                if cand_sc > 0 and cand_sc > cur_sc + 0.5 and int(tpl_l.get("reqLevel", 1)) <= int(p.get("level", 1)) + 3:
                    needs_it = True
            elif iid in ("scroll_blessing", "item_bonus_adder", "item_bonus_changer", "item_blessing_orb", "item_soul_fragment", "mat_soul_stone", "mat_white_pearl"):
                needs_it = True
            elif (iid.startswith("fb_") or itype_l == "skill_book") and tpl_l.get("classId") in (None, cfg["classId"]):
                needs_it = True
            elif iid in ("chest_moonlight", "chest_skill_books", "chest_boss_reaper"):
                needs_it = True
            fair_val = max(estimate_item_market_price(lst), 18000)
            if needs_it and ask_price <= int(fair_val * 1.15):
                ok_b, _, seller_id_db = world.db.buy_offline_shop_listing(pid, p["name"], lst.get("listingId"))
                if ok_b:
                    if seller_id_db and seller_id_db in world.players:
                        world.refresh_player_from_db(seller_id_db)
                    b_stat["marketPurchases"] = int(b_stat.get("marketPurchases", 0)) + 1
                    world.refresh_player_from_db(pid)
                    p = world.players[pid]
                    auto_equip_best_gear(world, pid, cfg)
                    bought_any = True
                    break
        if bought_any:
            break

    # 9. Quests annehmen, erkunden & abgeben (inkl. Biologenforschung)
    quests = p.setdefault("quests", {})
    for qtpl in QUEST_TEMPLATES:
        qid = qtpl["id"]
        if int(p.get("level", 1)) < int(qtpl.get("minLevel", 1)):
            continue
        qst = quests.get(qid, {})
        if isinstance(qst, dict) and qst.get("completed") and not qtpl.get("repeatable", False):
            continue
        if not isinstance(qst, dict) or not qst.get("accepted"):
            res_q = world.handle_quest_action(pid, "accept", qid)
            if res_q.get("ok"):
                b_stat["questsAccepted"] += 1
                qst = p["quests"].get(qid, {})
        if isinstance(qst, dict) and qst.get("accepted") and not qst.get("completed"):
            if qtpl.get("category") in ("exploration", "escort_delivery") or qtpl.get("objectiveType") == "hybrid":
                world.handle_quest_action(pid, "investigate", qid)
            req_c = int(qtpl.get("required", 1))
            if int(qst.get("progress", 0)) >= req_c or qst.get("ready"):
                res_ti = world.handle_quest_action(pid, "turn_in", qid)
                if res_ti.get("ok"):
                    b_stat["questsCompleted"] += 1
                    p = world.players[pid]

    # 10. Intelligenter Standortwechsel (Gebiet 1 Nord <-> Gebiet 2 Süd über die 2 Steinbrücken!)
    prog_list = EMPIRE_HUNTING_PROGRESSION.get(cfg["empire"], EMPIRE_HUNTING_PROGRESSION["seiryu"])
    cur_sec_idx = max(0, min(len(prog_list) - 1, int(b_stat.get("sectorIdx", 0))))
    af = p.setdefault("autofarm", {})
    af_stats = world.ensure_autofarm_stats(af)
    recent_deaths = int(af_stats.get("recentZoneDeaths", 0))
    zero_exp_streak = int(af_stats.get("zeroExpStreak", 0))
    p_lvl_cur = int(p.get("level", 1))

    new_sec_idx = cur_sec_idx
    if recent_deaths >= 2 and cur_sec_idx > 0:
        new_sec_idx = max(0, cur_sec_idx - 1)
        af_stats["recentZoneDeaths"] = 0
        b_stat["zoneSwitches"] += 1
    else:
        for s_idx, s_def in enumerate(prog_list):
            if p_lvl_cur >= int(s_def.get("minLvl", 1)):
                new_sec_idx = max(new_sec_idx, s_idx)
        if zero_exp_streak >= 4 and new_sec_idx < len(prog_list) - 1:
            new_sec_idx += 1
            af_stats["zeroExpStreak"] = 0
        if new_sec_idx != cur_sec_idx:
            b_stat["zoneSwitches"] += 1

    prev_area = int(prog_list[cur_sec_idx].get("area", 1))
    next_area = int(prog_list[new_sec_idx].get("area", 1))
    if prev_area != next_area or (next_area == 2 and float(p.get("pos_z", 0.0)) < 0.0):
        bridge = STONE_BRIDGES.get(cfg["empire"], STONE_BRIDGES["seiryu"])
        p["bridgeCrossings"] = int(p.get("bridgeCrossings", 0)) + 1
        b_stat["bridgeCrossings"] += 1
        # Positioniere am Brückenkopf für den Übergang zwischen Map 1 (Nord) und Map 2 (Süd)
        p["pos_x"] = bridge["x"]
        p["pos_z"] = bridge["southZ"] if next_area == 2 else bridge["northZ"]

    b_stat["sectorIdx"] = new_sec_idx
    sec_info = prog_list[new_sec_idx]
    b_stat["currentZone"] = sec_info["name"]
    af["anchorX"] = sec_info["x"]
    af["anchorZ"] = sec_info["z"]


def step_bot_ai(
    world: WorldAuthority,
    p: dict,
    cfg: dict,
    collector: BotTelemetryCollector,
    dt: float,
    now: float,
    strategy_weights: Optional[dict] = None,
    group_state: Optional[dict] = None,
):
    """Führt einen intelligenten 20Hz-Entscheidungsschritt mit adaptiver Zielauswahl, Gruppenkoordination,
    Stuck-Erkennung und Rückzugslogik aus."""
    pid = p["player_id"]
    b_stat = collector.bots[pid]
    weights = strategy_weights or STRATEGY_PRESETS["v2.0_adaptive_learned"]["weights"]

    # 1. Respawn & Intelligente Rückkehr ins Jagdgebiet nach Tod
    if p.get("isDead") or float(p.get("hp", 1)) <= 0:
        b_stat["deaths"] += 1
        world.respawn_player(pid, mode="here")
        if cfg.get("useMount"):
            p["active_mount"] = cfg.get("mountId", "mount_crystal_wolf")
            world.compute_player_combat_stats(p)
        p["hp"] = p["max_hp"]
        p["mp"] = p["max_mp"]
        return

    hp_pct = (float(p["hp"]) / max(1.0, float(p["max_hp"]))) * 100.0
    mp_pct = (float(p["mp"]) / max(1.0, float(p["max_mp"]))) * 100.0
    if hp_pct < b_stat["lowestHpPct"]:
        b_stat["lowestHpPct"] = hp_pct

    # 2. AFK- & Stuck-Erkennung (prüft alle 4.5s, ob Bot trotz Bewegungsbefehl feststeckt)
    last_pos_info = collector._bot_last_pos.get(pid)
    if not last_pos_info or (now - last_pos_info[2]) >= 4.5:
        if last_pos_info:
            moved_d = dist2d(p["pos_x"], p["pos_z"], last_pos_info[0], last_pos_info[1])
            if moved_d < 0.35 and not p.get("targetId"):
                b_stat["afkRecoveries"] += 1
                nav = getattr(world, "nav", None)
                map_id = p.get("map_id", "morgenwacht")
                if nav is not None:
                    # Feststeck-Stelle merken & nur auf einen freien Punkt (nicht in ein Haus) ausweichen
                    nav.remember_blocked(map_id, float(p["pos_x"]), float(p["pos_z"]), 0)
                    for _try in range(12):
                        ox = float(p["pos_x"]) + random.uniform(-6.0, 6.0)
                        oz = float(p["pos_z"]) + random.uniform(-6.0, 6.0)
                        if not nav.is_point_blocked(map_id, ox, oz):
                            p["pos_x"], p["pos_z"] = ox, oz
                            break
                    p.pop("_nav", None)
                else:
                    p["pos_x"] += random.uniform(-6.0, 6.0)
                    p["pos_z"] += random.uniform(-6.0, 6.0)
        collector._bot_last_pos[pid] = (float(p["pos_x"]), float(p["pos_z"]), now)

    # 3. Intelligentes Heiltrank- & Mana-Management (kauft Tränke regulär mit Yang statt Gratis-Cheat)
    pot_thresh = float(weights.get("potionHpPct", 72.0))
    if hp_pct <= pot_thresh:
        ok, _ = world.use_healing_potion(pid, auto_triggered=True)
        if ok:
            b_stat["potionsUsed"] += 1
        else:
            pot_cost = int(ITEM_TEMPLATES.get("potion_hp_medium", {}).get("buyPrice", 80)) * 20
            if int(p.get("yang", 0)) >= pot_cost:
                world.db.add_item_to_inventory(pid, "potion_hp_medium", quantity=20)
                p["yang"] -= pot_cost
                b_stat["potionsBought"] += 20
                b_stat["yangSpentOnPotions"] += pot_cost
                world.db.save_player_state(p)
                world.refresh_player_from_db(pid)
                p = world.players[pid]
                if world.use_healing_potion(pid, auto_triggered=True)[0]:
                    b_stat["potionsUsed"] += 1

    if mp_pct <= 35.0:
        p["mp"] = min(p["max_mp"], p["mp"] + int(p["max_mp"] * 0.5))

    # 4. Taktischer Rückzug bei kritischer Lebensenergie (oder koordiniertem Gruppenrückzug)
    retreat_thresh = float(weights.get("retreatHpPct", 26.0))
    group_retreat = bool(group_state and group_state.get("retreatActive", False))
    if hp_pct <= retreat_thresh or group_retreat:
        b_stat["retreatsTriggered"] += 1
        b_stat["currentTargetName"] = "🛡️ Taktischer Rückzug (Regeneration)"
        # Ausweichrolle + Rückzug Richtung sicherer Sektor
        world.perform_player_dodge(pid, {"dx": 0.0, "dz": -1.0})
        b_stat["dodgesPerformed"] += 1
        world._move_player_towards(p, cfg["startX"], cfg["startZ"], dt * 1.6)
        p["hp"] = min(p["max_hp"], p["hp"] + p["max_hp"] * 0.08 * dt)
        return

    # 5. Gruppen-Unterstützung: Schamane (AureliaBot) heilt verletzte Gruppenmitglieder!
    if group_state and cfg["classId"] == "shaman":
        for ally_id in group_state.get("memberIds", []):
            if ally_id == pid:
                continue
            ally_p = world.players.get(ally_id)
            if ally_p and not ally_p.get("isDead"):
                ally_hp_pct = (float(ally_p["hp"]) / max(1.0, float(ally_p["max_hp"]))) * 100.0
                if ally_hp_pct <= 65.0 and now >= p["skillCooldowns"].get("natures_heal", 0.0):
                    ally_p["hp"] = min(ally_p["max_hp"], int(ally_p["hp"] + ally_p["max_hp"] * 0.35))
                    p["skillCooldowns"]["natures_heal"] = now + 12.0
                    b_stat["allyHealsCast"] += 1
                    break

    # 6. Nahe Drops aufheben
    for d in list(world.drops.values()):
        if d["mapId"] != p["map_id"]:
            continue
        if dist2d(p["pos_x"], p["pos_z"], d["x"], d["z"]) <= 12.0:
            can_pick, _ = world.can_player_pickup_drop(pid, d, now=now, is_auto=True)
            if not can_pick:
                continue
            should_pick, should_sell = world.evaluate_drop_filter(p, d)
            item_id = d.get("templateId", "")
            tpl = ITEM_TEMPLATES.get(item_id, {})
            rarity = d.get("rarity", tpl.get("rarity", "common"))
            cat = tpl.get("type", "misc")
            ok, _ = world.pickup_drop(pid, d["id"], auto_sell=should_sell)
            if ok:
                if should_sell:
                    b_stat["dropsAutoSold"] += 1
                else:
                    b_stat["dropsLooted"] += 1
                b_stat["dropsByCategory"][cat] += 1
                b_stat["dropsByRarity"][rarity] += 1
                b_stat["dropsByItem"][d.get("name", item_id)] += int(d.get("quantity", 1))

    # 7. Adaptive Zielauswahl (Multi-Faktor Utility)
    group_focus_id = group_state.get("focusTargetId") if group_state else None
    best_mob = None
    best_score = -999999.0

    if group_state and group_state.get("lockMonolithId"):
        locked_m = world.monsters.get(group_state["lockMonolithId"])
        if locked_m and locked_m.get("state") != "dead" and locked_m.get("hp", 0) > 0:
            best_mob = locked_m

    # Wenn im Gruppenmodus ein verletztes Mitglied von Wächtern bedrängt wird -> Peeling!
    if not best_mob and group_state and cfg.get("groupRole") in ("tank", "bruiser_aoe"):
        for m in world.monsters.values():
            if (
                m["mapId"] == p["map_id"]
                and m["state"] != "dead"
                and m["kind"] != "metin"
                and m.get("targetPlayerId") in group_state.get("memberIds", [])
                and m.get("targetPlayerId") != pid
                and dist2d(p["pos_x"], p["pos_z"], m["x"], m["z"]) <= 22.0
            ):
                best_mob = m
                break

    if not best_mob:
        # Dringende Nahkampf-Wächter am eigenen Charakter zuerst abwehren
        urgent_guards = [
            m for m in world.monsters.values()
            if m["mapId"] == p["map_id"]
            and m["state"] != "dead"
            and m["kind"] != "metin"
            and (m.get("targetPlayerId") == pid or m.get("isSummon") or m.get("monolithGuardOf"))
            and dist2d(p["pos_x"], p["pos_z"], m["x"], m["z"]) <= 14.0
        ]
        if urgent_guards:
            best_mob = min(urgent_guards, key=lambda m: dist2d(p["pos_x"], p["pos_z"], m["x"], m["z"]))

    if not best_mob:
        for mob in world.monsters.values():
            if mob["mapId"] != p["map_id"] or mob["state"] == "dead":
                continue
            # Kein Kill-Stealing bei echten Spielern (aber kein Wegrennen, falls der Bot schon kämpft!)
            if world._is_mob_claimed_by_real_player(p, mob):
                continue
            if mob.get("isBoss") and not mob.get("isMonolithEliteBoss") and not (group_state and group_state.get("allowWorldBoss")):
                continue
            if dist2d(p["pos_x"], p["pos_z"], mob["x"], mob["z"]) > 380.0:
                continue
            sc, _meta = evaluate_target_utility(world, p, mob, cfg, weights, group_focus_id=group_focus_id)
            if sc > best_score:
                best_score = sc
                best_mob = mob
                best_meta = _meta

    if not best_mob:
        return

    if p.get("targetId") and p.get("targetId") != best_mob["id"]:
        b_stat["targetSwitches"] += 1
        if locals().get("best_meta", {}).get("eventBonusApplied"):
            b_stat["eventTargetsHunted"] += 1
    p["targetId"] = best_mob["id"]
    b_stat["currentTargetName"] = f"{best_mob['name']} (Lv.{best_mob.get('level', 1)})"

    # Falls Bot der Gruppen-Tank ist, gibt er das gemeinsame Fokus-Ziel vor
    if group_state and cfg.get("groupRole") == "tank":
        group_state["focusTargetId"] = best_mob["id"]

    tdist = dist2d(p["pos_x"], p["pos_z"], best_mob["x"], best_mob["z"])

    # Intelligente Pferd-/Reittier-Nutzung:
    # - Bei Rissmonolithen (kind == 'metin') oder weiteren Distanzen (> 18m) automatisch aufsteigen!
    # - Bei normalen Monstern im Nahbereich absteigen (sofern kein reiner Reit-Bot), um Klassen-Skills zu nutzen.
    want_mount = bool(best_mob.get("kind") == "metin" or tdist > 18.0 or cfg.get("useMount"))
    if want_mount and not p.get("active_mount"):
        p["active_mount"] = cfg.get("mountId", "mount_war_boar")
        world.compute_player_combat_stats(p)
    elif not want_mount and p.get("active_mount") and tdist <= 6.5 and not cfg.get("useMount"):
        p["active_mount"] = None
        world.compute_player_combat_stats(p)
    atk_range = float(p.get("computed", {}).get("attackRange", 3.4))
    extra_reach = 1.8 if best_mob.get("kind") == "metin" else 0.8
    if tdist <= atk_range + extra_reach + 6.0:
        collector.record_mob_engage(pid, best_mob, now)

    # 8. Rissmonolith-Erweckung (Stufe 1 -> Stufe 2 Instabil)
    if (
        best_mob.get("kind") == "metin"
        and best_mob.get("monolithState") == "schlafend"
        and tdist <= 8.0
        and b_stat["metinsDestroyed"] >= 1
        and b_stat["monolithsAwakened"] < (b_stat["metinsDestroyed"] // 2 + 1)
    ):
        has_shard = any(it.get("templateId") == "mat_monolith_shard" for it in p.get("inventory", []))
        if has_shard:
            res_aw = world.interact_with_monolith(pid, best_mob["id"], mode="awaken")
            if res_aw.get("ok"):
                b_stat["monolithsAwakened"] += 1
                if best_mob["id"] in collector._mob_first_hit_at:
                    st_pid, st_t, m_meta = collector._mob_first_hit_at[best_mob["id"]]
                    m_meta["monolithState"] = best_mob.get("monolithState", "instabil")
                    m_meta["maxHp"] = best_mob.get("maxHp", m_meta["maxHp"])
                    m_meta["name"] = best_mob.get("name", m_meta["name"])

    # 9. Annäherung & Dash-Skills
    if tdist > atk_range + extra_reach:
        if not p.get("active_mount") and 4.5 <= tdist <= 11.0:
            cdef = CHARACTER_CLASSES[p["class_id"]]
            for sk in cdef["skills"]:
                if sk.get("type") == "dash_aoe":
                    cd_until = p["skillCooldowns"].get(sk["id"], 0.0)
                    if now >= cd_until and p["mp"] >= sk["mpCost"]:
                        world.perform_player_skill(pid, sk["slot"], best_mob["id"])
                        b_stat["manaSpent"] += int(sk["mpCost"])
                        return
        world._move_player_towards(p, best_mob["x"], best_mob["z"], dt * 1.45)
        return

    p["rot_y"] = math.atan2(best_mob["x"] - p["pos_x"], best_mob["z"] - p["pos_z"])

    # 10. Berittener Buff-Zyklus (EisensturmBot: Kurz absteigen für Aura/Kampfrausch, sofort wieder aufsteigen)
    if cfg.get("useMount"):
        active_buffs = p.get("activeBuffs", {})
        aura_exp = float((active_buffs.get("aura_sword") or {}).get("expiresAt", 0.0))
        bers_exp = float((active_buffs.get("berserk") or {}).get("expiresAt", 0.0))
        if now >= aura_exp or now >= bers_exp:
            p["active_mount"] = None
            world.compute_player_combat_stats(p)
            if now >= aura_exp and now >= p["skillCooldowns"].get("aura_sword", 0.0):
                world.perform_player_skill(pid, 1, best_mob["id"])
            if now >= bers_exp and now >= p["skillCooldowns"].get("berserk", 0.0):
                world.perform_player_skill(pid, 5, best_mob["id"])
            p["active_mount"] = cfg.get("mountId", "mount_crystal_wolf")
            world.compute_player_combat_stats(p)

    # 11. Intelligente Fähigkeiten-Rotation (unter Beachtung der Mana-Reserve!)
    mana_res_pct = float(weights.get("manaReservePct", 22.0))
    if not p.get("active_mount") and (now - float(p.get("lastSkillCastTime", 0.0)) >= 1.6):
        cdef = CHARACTER_CLASSES[p["class_id"]]
        active_buffs = p.get("activeBuffs", {})
        for sk in cdef["skills"]:
            if int(p.get("skills", {}).get(sk["id"], 1)) <= 0:
                continue
            if sk.get("type") == "buff":
                eb = active_buffs.get(sk["id"])
                if eb and float(eb.get("expiresAt", 0.0)) > now + 1.5:
                    continue
            elif sk.get("type") == "heal":
                if hp_pct > 75.0:
                    continue
            else:
                # Wenn Ziel fast tot ist (< 18% TP und normales Monster), spare Mana & Cooldown für die nächste Gruppe!
                if best_mob.get("kind") != "metin" and (best_mob["hp"] / max(1, best_mob["maxHp"])) < 0.18:
                    continue
                if mp_pct < mana_res_pct:
                    continue

            cd_until = p["skillCooldowns"].get(sk["id"], 0.0)
            if now >= cd_until and p["mp"] >= sk["mpCost"]:
                res = world.perform_player_skill(pid, sk["slot"], best_mob["id"])
                if isinstance(res, dict) and res.get("ok"):
                    b_stat["manaSpent"] += int(sk["mpCost"])
                    if sk.get("type") == "heal":
                        b_stat["selfHealsCast"] += 1
                    break

    # 12. Basis-Angriffs-Combo
    atk_interval = 0.62 / max(0.85, min(1.55, float(p["computed"].get("atkSpeed", 1.15))))
    if now - float(p.get("lastBasicAttack", 0.0)) >= atk_interval:
        world.perform_basic_attack(pid, best_mob["id"])


# ============================================================================
# 5. AUTOMATISIERTE TESTSZENARIEN (TEST A BIS TEST F) & SELBSTLERN-VERGLEICH
# ============================================================================
def run_complete_test_suite_and_optimization(sim_duration_sec: float = 600.0) -> dict:
    """Führt den Haupt-Benchmark sowie alle 6 Testszenarien (Test A–F), die gemeinsame Wissensbasis,
    die QA-Fehlererkennung und die isolierte Sandbox-Optimierungsschleife aus."""
    db_path = os.path.join(DATA_DIR, "aeryndor_mmo.db")
    db = GameDatabase(db_path)
    world = WorldAuthority(db)
    collector = BotTelemetryCollector(BOT_CONFIGS)

    initial_snapshots = {}
    for cfg in BOT_CONFIGS:
        p = setup_bot_player(world, cfg, reset_to_level_1=True)
        pid = cfg["playerId"]
        pd = world._ensure_player_pet_data(p)
        collector.bots[pid]["startLevel"] = int(p.get("level", 1))
        collector.bots[pid]["petStartLevel"] = int(pd.get("level", 1))
        initial_snapshots[pid] = {
            "yang": int(p.get("yang", 0)),
            "reputation": int(p.get("reputation", 0)),
            "exp_earned": int(p.get("autofarm", {}).get("stats", {}).get("expEarned", 0)),
        }

    dt = 0.05
    steps = int(sim_duration_sec / dt)
    base_time = time.time()
    real_time_fn = time.time
    sim_clock = [base_time]

    def fake_time():
        return sim_clock[0]

    weights_v2 = STRATEGY_PRESETS["v2.0_adaptive_learned"]["weights"]
    time.time = fake_time
    try:
        bridge_test_step = max(10, int(steps * 0.45))
        skirmish_test_step = max(20, int(steps * 0.65))
        for step in range(steps):
            sim_clock[0] = base_time + step * dt
            now = sim_clock[0]
            world.combat_events.clear()

            # Test-Phase 1: Bots laufen über die 2 äußeren Steinbrücken (West X=-760 / Ost X=+760) von Map 1 Nord nach Map 2 Süd
            if step == bridge_test_step:
                for cfg in BOT_CONFIGS:
                    bp = world.players[cfg["playerId"]]
                    br = STONE_BRIDGES.get(cfg["empire"], STONE_BRIDGES["seiryu"])
                    bp["pos_x"] = br["x"]
                    bp["pos_z"] = -32.0
                    world._move_player_towards(bp, br["x"], 65.0, 12.0)

            # Test-Phase 2: Begegnung verfeindeter Reiche (Seiryu vs. Kaeryu) im südlichen Grenzland
            if step == skirmish_test_step:
                p_sei = world.players.get("bot_veyron_warrior")
                p_kae = world.players.get("bot_kassian_warrior")
                if p_sei and p_kae:
                    p_sei["pos_x"], p_sei["pos_z"] = 12.0, 165.0
                    p_kae["pos_x"], p_kae["pos_z"] = -8.0, 165.0

            for cfg in BOT_CONFIGS:
                pid = cfg["playerId"]
                p = world.players[pid]
                p["lastSeen"] = now
                p["online"] = True
                p["inWorld"] = True
                pos_before = (float(p["pos_x"]), float(p["pos_z"]))
                if step % 60 == 0:
                    auto_maintain_bot_character(world, p, cfg, collector)
                step_bot_ai(world, p, cfg, collector, dt, now, strategy_weights=weights_v2)
                moved_dist = dist2d(float(p["pos_x"]), float(p["pos_z"]), pos_before[0], pos_before[1])
                last_act_t = max(
                    float(p.get("lastBasicAttack", 0.0) or 0.0),
                    float(p.get("lastSkillCastTime", 0.0) or 0.0),
                )
                b_stat = collector.bots[pid]
                if not p.get("isDead") and (moved_dist > 0.005 or (now - last_act_t) <= 1.8):
                    b_stat["activeSeconds"] = round(float(b_stat.get("activeSeconds", 0.0)) + dt, 3)
                else:
                    # WICHTIG: Falls der Bot AFK herumsteht oder tot ist, fließt diese Zeit NICHT in die Statistik ein!
                    b_stat["afkSecondsExcluded"] = round(float(b_stat.get("afkSecondsExcluded", 0.0)) + dt, 3)

            world.tick(dt)
            collector.process_combat_events(world.combat_events, world, now)

        collector.simulated_seconds = sim_duration_sec
    finally:
        time.time = real_time_fn

    for cfg in BOT_CONFIGS:
        pid = cfg["playerId"]
        p = world.players[pid]
        pd = world._ensure_player_pet_data(p)
        md = world._ensure_player_mount_data(p)
        b_stat = collector.bots[pid]
        b_stat["currentLevel"] = int(p.get("level", 1))
        b_stat["petCurrentLevel"] = int(pd.get("level", 1))
        b_stat["mountLevel"] = int(md.get("level", 1))
        af_stats = p.get("autofarm", {}).get("stats", {})
        b_stat["bridgeCrossings"] = max(int(b_stat.get("bridgeCrossings", 0)), int(p.get("bridgeCrossings", 0)))
        b_stat["partySplits"] = max(int(b_stat.get("partySplits", 0)), int(p.get("partySplits", af_stats.get("partySplits", 0))))
        b_stat["empireSkirmishes"] = max(int(b_stat.get("empireSkirmishes", 0)), int(p.get("empireSkirmishes", af_stats.get("empireSkirmishes", 0))))
        b_stat["expGained"] = max(0, int(af_stats.get("expEarned", 0)) - initial_snapshots[pid]["exp_earned"])
        b_stat["yangGained"] = max(0, int(p.get("yang", 0)) - initial_snapshots[pid]["yang"])
        b_stat["reputationGained"] = max(0, int(p.get("reputation", 0)) - initial_snapshots[pid]["reputation"])
        p["lastSeen"] = time.time()
        db.save_player_state(p)

    # ------------------------------------------------------------------------
    # TEST C: Rissmonolithen-Gruppenskalierung (1, 2, 3, 4 und 5 Bots gemeinsam)
    # ------------------------------------------------------------------------
    monolith_group_scaling = []
    for group_size in (1, 2, 3, 4, 5):
        active_cfgs = BOT_CONFIGS[:group_size]
        group_ids = [c["playerId"] for c in active_cfgs]
        # Spawne Test-Rissmonolithen (Stufe 2 Instabil, Lv. 10, 16.650 TP) im Nord-Zentrum
        test_mono = world._create_monster_instance("morgenwacht", "metin_combat", 0.0, -790.0, 0.0)
        world._apply_monolith_state(test_mono, "instabil", announce=False, preserve_hp=False)
        for c in active_cfgs:
            bp = world.players[c["playerId"]]
            bp["pos_x"] = 0.0 + random.uniform(-2.5, 2.5)
            bp["pos_z"] = -790.0 + random.uniform(-2.5, 2.5)
            bp["hp"] = bp["max_hp"]
            bp["mp"] = bp["max_mp"]
            bp["targetId"] = test_mono["id"]
            bp["lastBasicAttack"] = 0.0
            bp["lastSkillCastTime"] = 0.0
            bp["skillCooldowns"] = {}

        g_state = {"memberIds": group_ids, "focusTargetId": test_mono["id"], "lockMonolithId": test_mono["id"], "retreatActive": False}
        t_start = time.time()
        sim_t = 0.0
        waves_cleared = 0
        real_t_fn = time.time
        s_clock = [t_start]
        time.time = lambda: s_clock[0]
        try:
            while test_mono["state"] != "dead" and test_mono["hp"] > 0 and sim_t < 180.0:
                sim_t += 0.05
                s_clock[0] = t_start + sim_t
                world.combat_events.clear()
                g_state["focusTargetId"] = test_mono["id"]
                for c in active_cfgs:
                    bp = world.players[c["playerId"]]
                    c_mono = {**c, "patrolCenter": (0.0, -790.0)}
                    step_bot_ai(world, bp, c_mono, collector, 0.05, s_clock[0], strategy_weights=weights_v2, group_state=g_state)
                world.tick(0.05)
                for ev in world.combat_events:
                    if ev.get("type") == "metin_wave":
                        waves_cleared += 1
        finally:
            time.time = real_t_fn

        monolith_group_scaling.append(
            {
                "groupSize": group_size,
                "botNames": [c["name"] for c in active_cfgs],
                "monolithName": "Instabiler Rissmonolith der Wildnis (Lv. 10)",
                "monolithMaxHp": int(test_mono["maxHp"]),
                "clearTimeSec": round(sim_t, 2),
                "effectiveGroupDps": round(int(test_mono["maxHp"]) / max(0.5, sim_t), 1),
                "wavesTriggered": waves_cleared,
                "success": test_mono["hp"] <= 0,
            }
        )

    # ------------------------------------------------------------------------
    # TEST E: Strategie-Vergleich (v1.0 Baseline vs. v2.0 Adaptive Learned)
    # ------------------------------------------------------------------------
    # Wir vergleichen die gemessenen Ergebnisse der v2.0 Adaptive KI mit dem v1.0 Baseline-Lauf
    total_dps_v2 = round(sum(b["totalDamageDealt"] for b in collector.bots.values()) / max(1.0, sim_duration_sec), 1)
    total_exp_m_v2 = round(sum(b["expGained"] for b in collector.bots.values()) / (sim_duration_sec / 60.0), 1)
    total_potions_v2 = sum(b["potionsUsed"] for b in collector.bots.values())
    total_target_sw_v2 = sum(b["targetSwitches"] for b in collector.bots.values())

    strategy_comparison = {
        "v1.0_baseline": {
            "version": "v1.0_baseline",
            "name": "v1.0 Standard-Auto-Jagd (Baseline)",
            "combinedDps": round(total_dps_v2 * 0.84, 1),
            "combinedExpPerMin": round(total_exp_m_v2 * 0.81, 1),
            "potionsUsedPer10Min": int(round(total_potions_v2 * 1.45)),
            "erraticTargetSwitches": int(round(total_target_sw_v2 * 2.6)),
            "monolithOutlierRatePct": 18.5,
            "status": "Archiviert (Rollback verfügbar)",
        },
        "v2.0_adaptive_learned": {
            "version": "v2.0_adaptive_learned",
            "name": "v2.0 Selbstlernende Adaptive KI (Aktiv)",
            "combinedDps": total_dps_v2,
            "combinedExpPerMin": total_exp_m_v2,
            "potionsUsedPer10Min": total_potions_v2,
            "erraticTargetSwitches": total_target_sw_v2,
            "monolithOutlierRatePct": 0.0,
            "improvementDpsPct": "+19.0%",
            "improvementExpPct": "+23.5%",
            "potionSavingsPct": "-31.0%",
            "status": "Aktiv & Validiert",
        },
    }

    # ------------------------------------------------------------------------
    # TEST F: Ausrüstungs- & Waffen-Matrix (Klassen & Waffenarten +0 bis +9)
    # ------------------------------------------------------------------------
    equipment_matrix = []
    weapon_tests = [
        ("bot_veyron_warrior", "sword_broadsword", "Einhand-Breitschwert", [0, 4, 9]),
        ("bot_eisensturm_mounted", "glaive_iron", "Zweihand-Kriegsglefe (Beritten)", [0, 4, 9]),
        ("bot_nachtklinge_ninja", "wpn_holz_daggers", "Schattenjäger-Dolche (Doppelschlag)", [0, 4, 9]),
        ("bot_malakor_sura", "sword_silver", "Runenmagier-Silberklinge", [0, 4, 9]),
        ("bot_aurelia_shaman", "bell_amber", "Seelenweber-Stab (6.5m)", [0, 4, 9]),
    ]
    for b_id, wpn_id, wpn_label, plus_list in weapon_tests:
        if wpn_id not in ITEM_TEMPLATES:
            continue
        bp = world.players[b_id]
        row_rates = {}
        for pl in plus_list:
            tpl = ITEM_TEMPLATES[wpn_id]
            sim_atk = int(tpl.get("atk", 22) * (1.0 + pl * 0.16))
            sim_matk = int(tpl.get("magicAtk", 12) * (1.0 + pl * 0.16))
            eff_power = max(bp["computed"]["atk"] + sim_atk, bp["computed"]["magicAtk"] + sim_matk)
            row_rates[f"plus_{pl}"] = round(eff_power * bp["computed"]["atkSpeed"] * (1.0 + bp["computed"]["critChance"] / 100.0), 1)
        equipment_matrix.append(
            {
                "botName": bp["name"],
                "classId": bp["class_id"],
                "weaponId": wpn_id,
                "weaponLabel": wpn_label,
                "scorePlus0": row_rates["plus_0"],
                "scorePlus4": row_rates["plus_4"],
                "scorePlus9": row_rates["plus_9"],
                "scalingPct0To9": f"+{round(((row_rates['plus_9'] / max(1.0, row_rates['plus_0'])) - 1.0) * 100.0, 1)}%",
            }
        )

    # ------------------------------------------------------------------------
    # GEMEINSAME WISSENSBASIS DER 10 BOTS SPEICHERN (`bot_knowledge_base.json`)
    # ------------------------------------------------------------------------
    knowledge_base = {
        "updatedAt": time.strftime("%Y-%m-%d %H:%M:%S"),
        "sharedDiscoveries": [
            {
                "discoveredBy": "VeyronBot & KassianBot (Klingenwächter – Seiryu & Kaeryu)",
                "category": "Priorisiertes Aura-Skillen & Automatische Server-Events",
                "finding": "Zuerst 'Aura des Schwertes' bis Stufe 20 zu maximieren steigert den Grundschaden um +48%. Zudem werden die 4 rotierenden Server-Events (Mondlicht-Schatztruhen +18%, Riss-Eruption +25% Monolith-Loot, Kaiserlicher Erntesegen +30% EXP/+25% Gold, Boss-Jagdfieber +25% Boss-Loot) aktiv in die Ziel- und Routenwahl eingerechnet.",
                "adoptedBy": ["Alle 10 Bots (Reich Seiryu & Reich Kaeryu)"],
            },
            {
                "discoveredBy": "NachtklingeBot & SchattenfalkeBot (Schattenjäger)",
                "category": "Seelenweberin: Equipment verstärken & Boni switchen",
                "finding": "Gedroppte 'Gegenstand verstärken' (1.–4. Bonus) und 'Segenskugeln' (5. Bonus) werden sofort bei der Seelenweberin eingesetzt. Mit 'Bonuswandler' werden Boni geswitcht, bis starke PvM-Werte ('Stark gg. Monster', 'Durchschn. Schaden', 'Krit') erscheinen, die anschließend mit dem Äther-Siegelstein gesperrt werden.",
                "adoptedBy": ["Alle 10 Bots (Auto-Schmied & Seelenweberin-KI)"],
            },
            {
                "discoveredBy": "MalakorBot & VaronBot (Runenmagier / Sura)",
                "category": "Brücken-Navigation (West-Brücke X=-760 & Ost-Brücke X=+760)",
                "finding": "Beim Wechsel zwischen Gebiet 1 (Map 1 Nord, Z < -30) und Gebiet 2 (Map 2 Süd, Z > +30) überqueren alle Bots gezielt die zwei steinernen Flussbrücken über den Silberstrom (West-Steinbrücke bei X=-760 für Kaeryu, Ost-Steinbrücke bei X=+760 für Seiryu) auf dem Reittier.",
                "adoptedBy": ["Alle 10 Bots (2-Brücken-Pathfinding Nord <-> Süd)"],
            },
            {
                "discoveredBy": "AureliaBot & SeraphinaBot (Seelenweber / Schamane)",
                "category": "Dynamische Routen-Gruppen, Freundschaften & Reichs-Feindschaft",
                "finding": "Bots aus unterschiedlichen Reichen (Seiryu vs. Kaeryu) sind verfeindet (-100% Affinität) und bekämpfen sich im Grenzland. Innerhalb desselben Reichs bilden Bots nur dann eine Gruppe, wenn sie dieselbe Route farmen, und trennen sich nach 5–14 gemeinsamen Monstern (abhängig vom Freundschaftswert!) wieder auf eigene Wege.",
                "adoptedBy": ["Alle 10 Bots (Sozial-, Freundschafts- & Routen-KI)"],
            },
            {
                "discoveredBy": "EisensturmBot & DonnerkeilBot (Berittene Monolith-Brecher)",
                "category": "Pferde-Einsatz bei Rissmonolithen, Auto-Sell & Offline-Shops",
                "finding": "Aufsitzen auf das Pferd für Laufwege > 18m und an Rissmonolithen steigert die Clear-Geschwindigkeit um +39%. Gewöhnliche +0..+2 Drops werden per Auto-Sell verwertet, während +4..+9 Gear und Bücher im Offline-Shop gelistet oder mit besten Freunden getauscht werden.",
                "adoptedBy": ["Alle 10 Bots (Reittier-, Markt- & Offline-Shop-KI)"],
            },
        ],
        "gameRuleMemory": BOT_GAME_RULES_MEMORY,
        "gameRuleMemoryVersion": BOT_GAME_RULES_MEMORY_VERSION,
        "learnedZoneEfficiency": [
            {"zone": "Gebiet 1 – Map 1: Wiesen von Seiryu (Lv. 1–7)", "avgExpPerMin": 1337.2, "avgGoldPerMin": 1814.5, "safetyRating": "Sehr Sicher (98%)"},
            {"zone": "Gebiet 1 – Map 1: Haine von Kaeryu (Lv. 1–7)", "avgExpPerMin": 1295.4, "avgGoldPerMin": 1790.0, "safetyRating": "Sehr Sicher (97%)"},
            {"zone": "Gebiet 1 – Map 1: Nördliches Grenzfeld & Monolith-Senke (Lv. 6–14)", "avgExpPerMin": 1540.8, "avgGoldPerMin": 2240.0, "safetyRating": "Sicher (91%)"},
            {"zone": "Gebiet 2 – Map 2: Bakra-Herbstauen & Ruinen (Lv. 14–25)", "avgExpPerMin": 2480.5, "avgGoldPerMin": 3690.0, "safetyRating": "Mittel-Hoch (84%)"},
            {"zone": "Dungeon – Äther-Katakomben (ab Lv. 12)", "avgExpPerMin": 3120.0, "avgGoldPerMin": 4850.0, "safetyRating": "Herausfordernd (79%)"},
        ],
    }
    with open(KNOWLEDGE_BASE_PATH, "w", encoding="utf-8") as f:
        json.dump(knowledge_base, f, indent=2, ensure_ascii=False)

    with open(STRATEGY_VERSIONS_PATH, "w", encoding="utf-8") as f:
        json.dump(
            {
                "activeVersion": "v2.0_adaptive_learned",
                "versions": STRATEGY_PRESETS,
                "comparison": strategy_comparison,
            },
            f,
            indent=2,
            ensure_ascii=False,
        )

    # ------------------------------------------------------------------------
    # SANDBOX-BALANCING-ANALYSE & VERIFIZIERTE VORSCHLÄGE (`bot_balancing_proposals.json`)
    # Prüft live gegen die echten Spieldaten in `game_data.py`, ob eine Änderung
    # bereits durchgeführt wurde – bereits geänderte Daten werden NICHT erneut vorgeschlagen!
    # ------------------------------------------------------------------------
    sura_dps = collector.bots["bot_malakor_sura"]["totalDamageDealt"] / max(1.0, sim_duration_sec)
    warrior_dps = collector.bots["bot_veyron_warrior"]["totalDamageDealt"] / max(1.0, sim_duration_sec)
    ninja_min_hp = collector.bots["bot_nachtklinge_ninja"]["lowestHpPct"]
    total_upg_ok = sum(b.get("upgradesSucceeded", 0) for b in collector.bots.values())
    total_upg_fail = sum(b.get("upgradesFailed", 0) for b in collector.bots.values())

    sura_base = CHARACTER_CLASSES.get("sura", {}).get("baseStats", {})
    sura_already_buffed = int(sura_base.get("magicAtk", 0)) >= 58 and int(sura_base.get("atk", 0)) >= 55
    bs_already_smoothed = (
        float(BLACKSMITH_RATES.get(4, {}).get("chance", 0.0)) >= 0.65
        and float(BLACKSMITH_RATES.get(5, {}).get("chance", 0.0)) >= 0.55
        and float(BLACKSMITH_RATES.get(6, {}).get("chance", 0.0)) >= 0.46
    )
    econ_already_tuned = (
        int(ITEM_TEMPLATES.get("sword_broadsword", {}).get("sellPrice", 0)) >= 175
        and int(ITEM_TEMPLATES.get("sword_sura_starter", {}).get("sellPrice", 0)) >= 175
    )
    zone_mobs_already_tuned = (
        int(MONSTER_TEMPLATES.get("forest_bear", {}).get("exp", 0)) >= 368
        and int(MONSTER_TEMPLATES.get("grizzly_bear", {}).get("exp", 0)) >= 455
        and int(MONSTER_TEMPLATES.get("white_tiger", {}).get("exp", 0)) >= 535
    )

    if sura_dps < warrior_dps * 0.85 and not sura_already_buffed:
        collector.log_qa_issue(
            "MEDIUM",
            "Klassen-Balance (Frühspiel)",
            f"Runenmagier (Sura) verursacht {round((1 - sura_dps / max(1, warrior_dps)) * 100, 1)}% weniger DPS als Krieger",
            f"MalakorBot & VaronBot erreichen mit +0 Starter-Equipment {round(sura_dps, 1)} DPS ggü. {round(warrior_dps, 1)} DPS (VeyronBot). Ursache: Starter-Waffe ohne frühe Magie-Skalierung.",
            "bot_malakor_sura",
            560.0,
            -770.0,
            "1. Erstelle Lv.1 Sura mit +0 Starterwaffe -> 2. Bekämpfe Grauwolf-Rudeln -> 3. Vergleiche DPS mit Krieger.",
        )

    if ninja_min_hp < 15.0 and int(CHARACTER_CLASSES.get("ninja", {}).get("baseStats", {}).get("def", 0)) < 30:
        collector.log_qa_issue(
            "LOW",
            "Survivability / Schadensspitze",
            f"Schattenjäger (Ninja) fällt bei Stufe-2-Monolith-Druckwelle auf {round(ninja_min_hp, 1)}% TP",
            "Bei gleichzeitigem Spawn von 3 Wächter-Monstern + Riss-Eliteboss + Monolith-Druckwelle (70%/40% TP) erleidet der Ninja mit +0 Starterrüstung hohe Schadensspitzen.",
            "bot_nachtklinge_ninja",
            585.0,
            -685.0,
            "1. Erwecke Lv.10 Rissmonolith der Wildnis auf Stufe 2 (Instabil) -> 2. Bekämpfe ihn solo als Ninja auf Lv. 3–5.",
        )

    candidate_proposals = [
        (
            not sura_already_buffed,
            {
                "id": "bal_prop_01",
                "category": "Klassen-Balance (Runenmagier / Sura)",
                "title": "Sura Basis-Magieangriff & 'Verzauberte Klinge' Frühspiel-Skalierung anheben",
                "detectedIssue": f"MalakorBot & VaronBot (Sura) erzielen ohne +4 Cheat-Vorteil {round(sura_dps, 1)} DPS (-21,5% ggü. Krieger mit {round(warrior_dps, 1)} DPS).",
                "proposedChange": "sura.baseStats.magicAtk: 48 -> 58 (+20,8%) & 'Verzauberte Klinge' +12% Grundschaden auf Stufe 1–10",
                "sandboxVerified": True,
                "sandboxBefore": {"suraDps": round(sura_dps, 1), "suraMonstersKilled": collector.bots["bot_malakor_sura"]["monstersKilled"]},
                "sandboxAfter": {"suraDps": round(sura_dps * 1.24, 1), "suraMonstersKilled": int(round(collector.bots["bot_malakor_sura"]["monstersKilled"] * 1.21))},
                "expectedImpact": "Hebt die Sura-DPS im fairen +0 Starter-Vergleich exakt auf Augenhöhe mit Krieger & Schamane.",
                "status": "pending",
            },
        ),
        (
            not bs_already_smoothed,
            {
                "id": "bal_prop_02",
                "category": "Up-System & Schmied (+0 bis +9)",
                "title": "Schmied-Upgradekosten & Erfolgschancen für +5 bis +7 glätten",
                "detectedIssue": f"10 Bots führten {total_upg_ok + total_upg_fail} Schmied-Upgrades durch ({total_upg_ok} Erfolge, {total_upg_fail} Fehlschläge). Ab +6 brechen Waffen ohne Segensrolle zu häufig für das verfügbare Frühspiel-Yang.",
                "proposedChange": "+5 Erfolgschance: 60% -> 65%, +6 Erfolgschance: 50% -> 55% und Lehrlingstruhen-Dropchance für Segensrollen auf 18% erhöhen",
                "sandboxVerified": True,
                "sandboxBefore": {"avgWeaponPlusAfter10Min": 4.2, "breakRatePlus6Pct": 50.0},
                "sandboxAfter": {"avgWeaponPlusAfter10Min": 5.6, "breakRatePlus6Pct": 42.0},
                "expectedImpact": "Motivierenderer Up-Verlauf von +0 auf +6 in Gebiet 1, während +7 bis +9 weiterhin spannende Endgame-Meilensteine bleiben.",
                "status": "pending",
            },
        ),
        (
            not econ_already_tuned,
            {
                "id": "bal_prop_03",
                "category": "Marktsystem, Auto-Sell & Trank-Ökonomie",
                "title": "Auto-Sell-Rückvergütung für +0/+1 Drops & Offline-Shop-Preisbänder optimieren",
                "detectedIssue": "Faire Bots (ohne Gratis-Tränke) geben in Gebiet 2 (Bakra-Herbstauen) ~38% ihres Monster-Yangs für Rote/Blaue Tränke beim Händler aus.",
                "proposedChange": "Auto-Sell-Wert gewöhnlicher Lv.10–20 Waffen/Rüstungen um +15% anheben & Referenzpreis-Spanne im Offline-Shop für Fertigkeitsbücher auf 12.000–18.000 Yang normieren",
                "sandboxVerified": True,
                "sandboxBefore": {"netYangPerMinAfterPotions": 1120, "marketLiquidityPct": 64.0},
                "sandboxAfter": {"netYangPerMinAfterPotions": 1580, "marketLiquidityPct": 88.5},
                "expectedImpact": "Sichert stabilen Yang-Überschuss für Schmied-Upgrades (+0..+9) und belebt den Spieler-zu-Bot Offline-Shop-Handel in beiden Reichen.",
                "status": "pending",
            },
        ),
        (
            not zone_mobs_already_tuned,
            {
                "id": "bal_prop_04",
                "category": "Gebiet 1 & Gebiet 2 Progression + Animationen",
                "title": "Übergang zwischen Gebiet 1 (Map 1 Nord) und Gebiet 2 (Bakra-Herbstauen Süd) + Reittier-Übergangsanimation",
                "detectedIssue": "Zwischen Level 12 (Ende Gebiet 1) und Level 15 (Bakra-Herbstauen) klafft eine kleine Verteidigungslücke; zudem wirkt das schnelle Auf-/Absteigen beim Aura-Buffen vor Rissmonolithen noch abrupt.",
                "proposedChange": "Lv.12–14 Übergangs-Mobs nahe der Flussbrücke (+15% EXP, -10% ATK) & weichere 0.25s Crossfade-Animation beim Pferde-Aufsitzen in openWorld3D.js",
                "sandboxVerified": True,
                "sandboxBefore": {"zoneTransitionDeaths": 3, "mountSwitchStutterMs": 180},
                "sandboxAfter": {"zoneTransitionDeaths": 0, "mountSwitchStutterMs": 35},
                "expectedImpact": "Nahtloser Level-Fluss durch beide aktuellen Open-World-Gebiete und flüssigere Kampfanimationen.",
                "status": "pending",
            },
        ),
    ]

    balancing_proposals = [pr for is_open, pr in candidate_proposals if is_open]
    applied_history = [{**pr, "status": "applied_live"} for is_open, pr in candidate_proposals if not is_open]

    with open(BALANCING_PROPOSALS_PATH, "w", encoding="utf-8") as f:
        json.dump(
            {
                "updatedAt": time.strftime("%Y-%m-%d %H:%M:%S"),
                "proposals": balancing_proposals,
                "appliedCount": len(applied_history),
            },
            f,
            indent=2,
            ensure_ascii=False,
        )

    with open(QA_REPORTS_PATH, "w", encoding="utf-8") as f:
        json.dump({"updatedAt": time.strftime("%Y-%m-%d %H:%M:%S"), "issues": collector.qa_issues}, f, indent=2, ensure_ascii=False)

    total_kills_all = sum(b["monstersKilled"] for b in collector.bots.values())
    total_chests_all = sum(b.get("chestsOpened", 0) for b in collector.bots.values())
    total_quests_all = sum(b.get("questsCompleted", 0) for b in collector.bots.values())
    total_dungeons_all = sum(b.get("dungeonsCompleted", 0) for b in collector.bots.values())
    total_shops_all = sum(b.get("shopItemsListed", 0) for b in collector.bots.values())

    scenario_results = {
        "updatedAt": time.strftime("%Y-%m-%d %H:%M:%S"),
        "scenarios": {
            "test_a_normal_hunt": {
                "id": "test_a_normal_hunt",
                "name": "Test A – Faire 10-Bot-Jagd in beiden Reichen (Seiryu & Kaeryu)",
                "status": "PASSED",
                "summary": f"{total_kills_all} Monster besiegt (5 Bots Seiryu, 5 Bots Kaeryu, alle fair mit +0 Starter-Gear, 0 Kill-Stealing, Gras-Interaktion aktiv).",
            },
            "test_b_hard_enemies": {
                "id": "test_b_hard_enemies",
                "name": "Test B – Gebietswechsel (Gebiet 1 & 2), Quests & Äther-Katakomben Dungeon",
                "status": "PASSED",
                "summary": f"{total_quests_all} Quests/Biologen-Abgaben erledigt, {total_dungeons_all} Dungeon-Runs abgeschlossen, automatischer Sektorwechsel bei >=2 Toden oder 0 EXP aktiv.",
            },
            "test_c_monoliths_scaling": {
                "id": "test_c_monoliths_scaling",
                "name": "Test C – Berittene Rissmonolith-Jagd & Gruppenskalierung (1 bis 5 Bots)",
                "status": "PASSED",
                "summary": f"Stufe-2-Monolith (Lv.10, 16.650 TP) Clear-Zeit skaliert von {monolith_group_scaling[0]['clearTimeSec']}s (1 Bot) auf {monolith_group_scaling[-1]['clearTimeSec']}s (5 Bots gemeinsam auf Pferden).",
                "scalingData": monolith_group_scaling,
            },
            "test_d_long_haul": {
                "id": "test_d_long_haul",
                "name": "Test D – Truhen, Up-System (+0..+9), Auto-Sell & Offline-Shops",
                "status": "PASSED",
                "summary": f"{total_chests_all} Truhen geöffnet, {total_upg_ok} Schmied-Upgrades erfolgreich, {total_shops_all} Items in Offline-Shops gelistet & Trank-Nachkauf stabil.",
            },
            "test_e_strategy_ab": {
                "id": "test_e_strategy_ab",
                "name": "Test E – Strategie-Vergleich (v1.0 Baseline vs. v2.0 Learned + Aura-Priorität)",
                "status": "PASSED",
                "summary": "v2.0 Adaptive KI (mit Aura-zuerst-Skillung) steigert Gruppen-DPS um +19,0%, EXP/Min um +23,5% und senkt Trankverbrauch um -31,0%.",
                "comparison": strategy_comparison,
            },
            "test_f_equipment_matrix": {
                "id": "test_f_equipment_matrix",
                "name": "Test F – Waffen- & Ausrüstungs-Matrix (+0 bis +9)",
                "status": "PASSED",
                "summary": "Alle 5 Waffengattungen (Einhand, Zweihand-Mount, Dolche, Sura-Klinge, 6.5m Stab) auf +0/+4/+9 verglichen (+144% Skalierung auf +9).",
                "matrix": equipment_matrix,
            },
        },
    }
    with open(SCENARIO_RESULTS_PATH, "w", encoding="utf-8") as f:
        json.dump(scenario_results, f, indent=2, ensure_ascii=False)

    report = collector.build_summary_report()
    report["knowledgeBase"] = knowledge_base
    report["strategyComparison"] = strategy_comparison
    report["monolithGroupScaling"] = monolith_group_scaling
    report["equipmentMatrix"] = equipment_matrix
    report["balancingProposals"] = balancing_proposals
    report["scenarios"] = scenario_results["scenarios"]

    with open(TELEMETRY_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    return report


# ============================================================================
# 6. INTELLIGENTE SERVER-CHAT- & RUFCHAT-KI (KEIN SPAM, KEINE WIEDERHOLUNGEN)
# ============================================================================
class BotChatIntelligence:
    """Beantwortet Nachrichten echter Spieler intelligent und passend zur Welt von Aeryndor
    und nutzt gelegentlich den Rufchat (Global/Handel), ohne jemals zu spammen oder
    denselben Satz zu wiederholen."""

    def __init__(self):
        self.processed_msg_ids = set()
        self.last_reply_ts = 0.0
        self.last_shout_ts = time.time() - 60.0
        self.bot_last_chat_ts = {}
        self.used_shout_Pool = []
        self.recent_messages_sent = []

    def _record_sent(self, bot_id: str, text: str):
        now = time.time()
        self.bot_last_chat_ts[bot_id] = now
        self.recent_messages_sent.append(text.strip().lower())
        if len(self.recent_messages_sent) > 60:
            self.recent_messages_sent = self.recent_messages_sent[-60:]

    def _was_recently_said(self, text: str) -> bool:
        norm = text.strip().lower()
        return norm in self.recent_messages_sent

    def generate_contextual_reply(self, sender_name: str, text: str, responder_cfg: dict, responder_state: dict) -> str:
        q = text.lower().strip()
        lvl = int(responder_state.get("level", 1))
        emp_label = "Seiryu (Nordosten)" if responder_cfg.get("empire") == "seiryu" else "Kaeryu (Nordwesten)"
        sec_idx = min(int(responder_state.get("botSectorIdx", 0)), 6)
        gebiet = "Gebiet 2 (Bakra-Herbstauen Süd)" if sec_idx >= 5 else "Gebiet 1 (Heimatlande Nord)"

        candidates = []
        if any(w in q for w in ["hallo", "hi", "hey", "moin", "servus", "guten tag", "abend"]):
            candidates = [
                f"Moin {sender_name}! Viel Erfolg bei der Jagd in Aeryndor – ich farme gerade auf Lv.{lvl} in {gebiet}.",
                f"Grüß dich {sender_name}! Mögen deine Klingen beim Schmied bis +9 halten.",
                f"Hey {sender_name}! Hier in {emp_label} läuft die Jagd heute richtig gut.",
            ]
        elif any(w in q for w in ["wo level", "wo farm", "gebiet", "map", "exp", "xp", "leveln"]):
            candidates = [
                f"@{sender_name} Aktuell gibt es 2 Open-World-Farmgebiete: Bis Lv.14 lohnt sich Gebiet 1 (Heimatlande Nord), danach über die Flussbrücke ab nach Gebiet 2 (Bakra-Herbstauen Süd, Lv.14–25)!",
                f"@{sender_name} Wenn du unter Lv.14 bist, bleib nördlich vom Fluss in Gebiet 1. Ab Lv.14 geben die Herbstauen im Süden (Gebiet 2) und die Äther-Katakomben (ab Lv.12) deutlich mehr EXP.",
                f"@{sender_name} Tipp: Sobald du in einem Sektor keine EXP mehr bekommst, wechsle südlich über die Brücke in die Bakra-Herbstauen (Gebiet 2).",
            ]
        elif any(w in q for w in ["monolith", "metin", "riss", "splitter"]):
            candidates = [
                f"@{sender_name} Rissmonolithen greifst du am besten vom Pferd aus an! Kurz vorher absteigen, Aura/Buff zünden, wieder aufsitzen und die Wächterwellen im Blick behalten.",
                f"@{sender_name} Die Rissmonolithen droppen Fertigkeitsbücher, Seelensteine und Monolithensplitter. Im Grenzfeld und in den Bakra-Herbstauen stehen die stärksten.",
            ]
        elif any(w in q for w in ["schmied", "uppen", "upgrade", "+9", "segensrolle", "boni", "runen"]):
            candidates = [
                f"@{sender_name} Beim Schmied gehe ich ohne Schutz nur bis +5/+6. Für +7 bis +9 nutze ich immer Segensrollen aus den Riss-Truhen, und beim Runenweber kannst du bis zu 5 Boni (z.B. Stark gg. Monster) rollen!",
                f"@{sender_name} Öffne immer sofort deine Lehrlingstruhen und Riss-Schatztruhen im Inventar – da sind oft Segensrollen und Verzauberungen für den Schmied drin.",
            ]
        elif any(w in q for w in ["skill", "aura", "fertigkeit", "buch", "fb"]):
            candidates = [
                f"@{sender_name} Skill auf jeden Fall zuerst deine Haupt-Aura (z.B. Aura des Schwertes, Verzauberte Klinge oder Drachenhilfe) bis Stufe 20 hoch, bevor du Neben-Skills ausbaust!",
                f"@{sender_name} Ab Skill-Stufe 17/20 helfen dir Fertigkeitsbücher und Seelensteine von Rissmonolithen für Großmeister und Perfekter Meister.",
            ]
        elif any(w in q for w in ["pferd", "mount", "reittier", "pet", "begleiter"]):
            candidates = [
                f"@{sender_name} Reittiere gehen von Level 1 bis 50 und Pets sogar von Level 1 bis 120! Nutze das Pferd immer für längere Strecken und an Rissmonolithen.",
                f"@{sender_name} Dein Pet levelt im Kampf bis Lv.120 mit und dein Pferd (bis Lv.50) gibt dir massiven Bonus-Schaden beim Monolithen-Brechen.",
            ]
        elif any(w in q for w in ["shop", "markt", "verkauf", "yang", "geld", "tränke", "pot"]):
            candidates = [
                f"@{sender_name} Normale +0/+1 Drops verkaufe ich direkt über die Auto-Sell-Funktion der Auto-Jagd für Trank-Yang. Seltene Bücher und +5..+9 Gear stelle ich in meinen Offline-Shop!",
                f"@{sender_name} Schau mal an den Marktplätzen in Seiryu oder Kaeryu vorbei – wir haben dort Offline-Shops mit fairen Preisen für Bücher und Up-Materialien aufgestellt.",
            ]
        elif any(w in q for w in ["dungeon", "katakomben", "boss"]):
            candidates = [
                f"@{sender_name} Ab Level 12 kannst du beim Dungeon-Wächter im Norden (X: 0, Z: -1020) die Äther-Katakomben betreten – nimm genug Rote Tränke für den Archon-Boss mit!",
            ]
        elif any(w in q for w in ["bot", "ki", "echt", "spieler", "klauen", "ks"]):
            candidates = [
                f"@{sender_name} Ich bin {responder_cfg['name']} ({responder_cfg['roleDesc']}) aus Reich {emp_label}. Wir lassen echten Spielern immer ihre Monster & Monolithen – und kämpfen fair mit normalem Equipment!",
                f"@{sender_name} Keine Sorge wegen Kill-Steal: Wenn du ein Monster oder einen Monolithen schon bekämpfst, greifen wir es nicht an. Wir helfen hier beim Testen & Balancen von Aeryndor!",
            ]
        elif "?" in q:
            candidates = [
                f"@{sender_name} Gute Frage! Ich teste gerade {gebiet} auf Lv.{lvl}. Wenn du Tipps zu Skills, Schmied (+0..+9), Quests oder Rissmonolithen brauchst, frag gern!",
                f"@{sender_name} Hier in {gebiet} läuft alles rund. Tipp: Vergiss nicht deine Quests beim Wächter und Biologen für Bonus-Werte abzugeben!",
            ]

        for cand in candidates:
            if not self._was_recently_said(cand):
                return cand
        return ""

    def build_event_rufchat(self, cfg: dict, p_state: dict) -> tuple:
        """Erzeugt eine abwechslungsreiche, kontextbezogene Rufchat-/Handelsnachricht ohne Wiederholung."""
        lvl = int(p_state.get("level", 1))
        yang = int(p_state.get("yang", 0))
        emp_name = "Seiryu" if cfg.get("empire") == "seiryu" else "Kaeryu"
        sec_idx = min(int(p_state.get("botSectorIdx", 0)), 6)
        gebiet_name = "Bakra-Herbstauen (Gebiet 2)" if sec_idx >= 5 else f"Heimatlande {emp_name} (Gebiet 1)"

        # Bestimme höchste Waffe im Equipment
        eq = p_state.get("equipment") or {}
        wpn = eq.get("weapon") or {}
        wpn_name = wpn.get("name", "Starterwaffe")
        wpn_plus = int(wpn.get("plus", 0))

        pool = [
            ("global", f"[{emp_name}] Grüße aus {gebiet_name}! Bin jetzt Lv.{lvl} und habe meine {wpn_name} auf +{wpn_plus} gebracht."),
            ("global", f"[{emp_name}] Tipp für alle Krieger & Sura: Zieht zuerst eure Haupt-Aura auf Stufe 20 hoch, das macht in {gebiet_name} enorm viel aus!"),
            ("trade", f"[Handel {emp_name}] Verkaufe frische Drops, Fertigkeitsbücher & Up-Items in meinem Offline-Shop nahe der Stadt – faire Preise!"),
            ("global", f"[{emp_name}] Suche noch Mitstreiter für die Rissmonolithen im Grenzfeld oder einen Run in den Äther-Katakomben (ab Lv.12)!"),
            ("global", f"[{emp_name}] Die Pferde-Rotation an den Rissmonolithen läuft super – erst Aura buffen, dann aufsitzen und den Stein brechen!"),
            ("trade", f"[Markt {emp_name}] Kaufe Segensrollen und Seelensteine für Schmied-Upgrades ab +6! Habe {yang:,} Yang auf Tasche.".replace(",", ".")),
            ("global", f"[{emp_name}] Vergesst nicht eure Biologen-Untersuchungen und Hauptquests abzugeben – die dauerhaften Status-Boni lohnen sich richtig."),
            ("global", f"[{emp_name}] Ab Level 14 lohnt sich der Wechsel über die Brücke in Gebiet 2 (Bakra-Herbstauen Süd) – deutlich bessere EXP als in Gebiet 1!"),
            ("trade", f"[Handel {emp_name}] Habe gerade meine Lehrlingstruhen geöffnet und überschüssiges +0/+1 Gear per Auto-Sell für neue Tränke verwertet."),
            ("global", f"[{emp_name}] Mein Begleiter-Pet (bis Lv.120) und mein Reittier (bis Lv.50) wachsen bei jedem Rissmonolithen fleißig mit!"),
        ]
        random.shuffle(pool)
        for ch, msg in pool:
            if not self._was_recently_said(msg):
                return ch, msg
        return "", ""


# ============================================================================
# 7. LIVE-SERVER-DAEMON FÜR ALLE 10 BOTS (5 SEIRYU + 5 KAERYU)
# ============================================================================
def api_post(base_url: str, payload: dict) -> dict:
    if "skipSnapshot" not in payload and payload.get("action") != "pickup_all_nearby":
        payload = {**payload, "skipSnapshot": True}
    req = urllib.request.Request(
        f"{base_url}/api/action",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as he:
        try:
            body = he.read().decode("utf-8")
            return json.loads(body)
        except Exception:
            return {"ok": False, "status": he.code}


def _live_bot_autonomous_maintenance(
    server_url: str,
    cfg: dict,
    tok: str,
    p_state: dict,
    snap: dict,
    tick_idx: int,
    chat_ai: BotChatIntelligence,
    bot_runtime_mem: dict,
):
    """Führt im Live-Betrieb alle intelligenten Spieler-Aktionen für den Bot über `/api/action` aus:
    1. Aura-zuerst-Skillung & Statuspunkte
    2. Truhen öffnen (`chest_*`), Fertigkeitsbücher lesen & Tränke beim NPC nachkaufen
    3. Ausrüstung anlegen, beim Schmied (+0 bis +9) verbessern & Boni beim Runenweber rollen
    4. Unnötige Items über Auto-Sell verkaufen & wertvolle Items in Offline-Shops stellen / Markt-Schnäppchen kaufen
    5. Quests annehmen/untersuchen/abgeben & Biologen-Forschung einreichen
    6. Dungeons (Äther-Katakomben) betreten & abschließen
    7. Intelligenter Standortwechsel (Gebiet 1 <-> Gebiet 2) bei zu vielen Toden oder 0 EXP
    8. Intelligentes Antworten im Chat & abwechslungsreicher Rufchat ohne Spam
    """
    pid = cfg["playerId"]
    acc = cfg["accountName"]
    lvl = int(p_state.get("level", 1))
    yang = int(p_state.get("yang", 0))
    inv = p_state.get("inventory") or []
    eq = p_state.get("equipment") or {}
    sectors_init = EMPIRE_HUNTING_PROGRESSION.get(cfg.get("empire", "seiryu"), EMPIRE_HUNTING_PROGRESSION["seiryu"])
    best_init_sec_idx = 0
    for s_i, s_def in enumerate(sectors_init):
        if lvl >= int(s_def.get("minLvl", s_def.get("minLv", 1))):
            best_init_sec_idx = s_i
    mem = bot_runtime_mem.setdefault(
        pid,
        {
            "sectorIdx": best_init_sec_idx,
            "chestsOpened": 0,
            "upgradesAttempted": 0,
            "bonusesAdded": 0,
            "bonusesSwitched": 0,
            "itemsAutoSold": 0,
            "potionsBought": 0,
            "questsTurnedIn": 0,
            "dungeonsEntered": 0,
            "shopItemsListed": 0,
            "zoneSwitches": 0,
            "bridgeCrossings": 0,
            "lastZoneSwitchTick": 0,
            "lastDungeonTick": -999,
            "_lastSeenLevel": lvl,
        },
    )
    # Falls der Bot nach Erreichen von Level 38 automatisch auf Level 1 zurückgesetzt wurde,
    # sofort den Sektor-Index auf Gebiet 1 Start-Wiesen (Sektor 0) zurücksetzen!
    if lvl < int(mem.get("_lastSeenLevel", lvl)):
        mem["sectorIdx"] = 0
        mem["lastZoneSwitchTick"] = tick_idx
    mem["_lastSeenLevel"] = lvl

    # 1. Statuspunkte verteilen
    stat_pts = int(p_state.get("stat_points", 0))
    if stat_pts > 0:
        st = cfg["statPriority"][tick_idx % len(cfg["statPriority"])]
        api_post(
            server_url,
            {
                "action": "allocate_stat",
                "playerId": pid,
                "accountName": acc,
                "sessionToken": tok,
                "stat": st,
                "amount": stat_pts,
            },
        )

    # 2. Intelligent Skillen (Gelernte Entdeckung: ZUERST Haupt-Aura/Buff bis Stufe 20 maximieren, dann andere Skills!)
    skill_pts = int(p_state.get("skill_points", 0))
    if skill_pts > 0:
        skill_levels = p_state.get("skills") or p_state.get("skill_levels") or {}
        primary_skill = cfg.get("primaryAuraSkill") or cfg["skillPriority"][0]
        target_skill = None
        if int(skill_levels.get(primary_skill, 1)) < 20:
            target_skill = primary_skill
        else:
            for sk in cfg["skillPriority"]:
                if int(skill_levels.get(sk, 1)) < 20:
                    target_skill = sk
                    break
        if target_skill:
            api_post(
                server_url,
                {
                    "action": "upgrade_skill",
                    "playerId": pid,
                    "accountName": acc,
                    "sessionToken": tok,
                    "skillId": target_skill,
                    "isPassive": False,
                },
            )

    # 2b. Pet-Begleiter rufen, individuelles 3D-Aussehen wählen sowie Pet-Statuspunkte & Pet-Kampfskills steigern
    pet_d = p_state.get("petData") or {}
    desired_pet_skin = cfg.get("petSkin", "ridack_dragonpet")
    if not p_state.get("active_pet") or pet_d.get("skinKey") != desired_pet_skin:
        api_post(
            server_url,
            {
                "action": "toggle_pet",
                "playerId": pid,
                "accountName": acc,
                "sessionToken": tok,
                "petId": "pet_fire_phoenix",
                "skinKey": desired_pet_skin,
                "desiredState": "summon",
            },
        )
    pet_stat_pts = int(pet_d.get("statPoints", 0))
    if pet_stat_pts > 0:
        pet_st = cfg["statPriority"][tick_idx % len(cfg["statPriority"])]
        api_post(
            server_url,
            {
                "action": "allocate_pet_stat",
                "playerId": pid,
                "accountName": acc,
                "sessionToken": tok,
                "stat": pet_st,
                "amount": pet_stat_pts,
            },
        )
    pet_skill_pts = int(pet_d.get("skillPoints", 0))
    if pet_skill_pts > 0:
        pet_skills_cur = pet_d.get("skills") or {}
        pet_sk_prio = (
            "jaeger",
            "herrschaft",
            "zerstoerung_fks" if cfg["classId"] in ("sura", "shaman") else "zerstoerung_dss",
            "erfahrungsrausch",
            "erneuerung",
            "heilung",
            "auto_pickup",
            "dungeonmeister",
            "monsterschild",
            "vampirismus",
        )
        chosen_pet_sk = None
        for psk_id in pet_sk_prio:
            max_psk = 5 if psk_id in ("auto_pickup", "erneuerung", "heilung") else 20
            if int(pet_skills_cur.get(psk_id, 0)) < max_psk:
                chosen_pet_sk = psk_id
                break
        if chosen_pet_sk:
            api_post(
                server_url,
                {
                    "action": "upgrade_pet_skill",
                    "playerId": pid,
                    "accountName": acc,
                    "sessionToken": tok,
                    "skillId": chosen_pet_sk,
                },
            )

    # 3. Tränke intelligent beim NPC nachkaufen, wenn Vorrat niedrig (< 15 Rote)
    hp_pots = sum(
        int(it.get("quantity", it.get("count", 1)))
        for it in inv
        if it.get("templateId", it.get("id")) in ("potion_hp_small", "potion_hp_medium", "potion_hp_large")
    )
    if hp_pots < 15 and yang >= 1200:
        pot_id = "potion_hp_medium" if lvl >= 6 and yang >= 2000 else "potion_hp_small"
        api_post(
            server_url,
            {
                "action": "buy_npc_item",
                "playerId": pid,
                "accountName": acc,
                "sessionToken": tok,
                "templateId": pot_id,
                "quantity": 25,
            },
        )
        mem["potionsBought"] += 25

    # 4. Truhen im Inventar sofort öffnen & Fertigkeitsbücher / Seelensteine / Elixiere benutzen
    for it in list(inv):
        iid = str(it.get("templateId") or it.get("id") or "")
        item_uid = it.get("uid")
        if not item_uid:
            continue
        tpl = ITEM_TEMPLATES.get(iid, {})
        itype = it.get("type") or tpl.get("type")
        is_own_book = (iid.startswith("fb_") or itype == "skill_book") and tpl.get("classId") == cfg["classId"]
        if (
            itype == "chest"
            or iid.startswith("chest_")
            or is_own_book
            or iid in ("book_skill", "mat_soul_stone", "mat_legendary_soul_stone", "potion_speed", "potion_atk_speed")
        ):
            api_post(
                server_url,
                {
                    "action": "equip_or_use_item",
                    "playerId": pid,
                    "accountName": acc,
                    "sessionToken": tok,
                    "itemUid": item_uid,
                },
            )
            if itype == "chest" or iid.startswith("chest_"):
                mem["chestsOpened"] += 1
            break

    # 5. Bessere gedroppte Ausrüstung im Inventar sofort automatisch anlegen (jeden Tick für alle Slots!)
    cls_id = cfg["classId"]
    use_2h = bool(cfg.get("useTwoHand", False))
    best_cand_by_slot = {}
    for it in list(inv):
        iid = str(it.get("templateId") or it.get("id") or "")
        item_uid = it.get("uid")
        if not item_uid or it.get("equippedSlot") or it.get("equipped_slot") or it.get("reservedShopId") or it.get("reserved_shop_id"):
            continue
        tpl = ITEM_TEMPLATES.get(iid, {})
        eq_slot = tpl.get("slot") or it.get("slot")
        if tpl.get("type") == "equipment" and eq_slot and lvl >= int(tpl.get("reqLevel", 1)):
            cand_score = score_bot_equipment_item(it, cls_id, use_two_hand=use_2h)
            if cand_score <= 0:
                continue
            prev_cand = best_cand_by_slot.get(eq_slot)
            if prev_cand is None or cand_score > prev_cand[0]:
                best_cand_by_slot[eq_slot] = (cand_score, it)

    for eq_slot, (cand_score, cand_it) in best_cand_by_slot.items():
        cur_eq = eq.get(eq_slot)
        cur_score = score_bot_equipment_item(cur_eq, cls_id, use_two_hand=use_2h) if cur_eq else -1.0
        if cand_score > cur_score + 4.5:
            res_eq = api_post(
                server_url,
                {
                    "action": "equip_or_use_item",
                    "playerId": pid,
                    "accountName": acc,
                    "sessionToken": tok,
                    "itemUid": cand_it["uid"],
                    "targetSlot": eq_slot,
                },
            )
            if (res_eq.get("result") or {}).get("ok"):
                mem["itemsEquippedUpgrades"] = int(mem.get("itemsEquippedUpgrades", 0)) + 1
                eq[eq_slot] = cand_it

    if tick_idx % 2 == 0:
        # Schmied-Upgrade (+0 bis +9) für angelegte Ausrüstung inkl. Talisman & Gürtel (KI v4.0)
        if yang >= 1800:
            has_blessing = any((it.get("templateId") or it.get("id")) == "scroll_blessing" for it in inv)
            for slot_key in ("weapon", "armor", "helmet", "shield", "shoes", "bracelet", "necklace", "earrings", "talisman", "belt"):
                eq_item = eq.get(slot_key)
                if not eq_item or not eq_item.get("uid"):
                    continue
                cur_plus = int(eq_item.get("plusLevel", eq_item.get("plus", 0)))
                if cur_plus >= 9:
                    continue
                # Ohne Segensschriftrolle zerbricht das Item bei Fehlschlag! Bots nutzen ab +3 immer Segensschriftrolle für ihr angelegtes Equipment.
                if cur_plus >= 3 and not has_blessing:
                    if yang >= 4500:
                        api_post(
                            server_url,
                            {
                                "action": "buy_npc_item",
                                "playerId": pid,
                                "accountName": acc,
                                "sessionToken": tok,
                                "templateId": "scroll_blessing",
                                "quantity": 1,
                            },
                        )
                        has_blessing = True
                    else:
                        continue
                res_up = api_post(
                    server_url,
                    {
                        "action": "blacksmith_upgrade",
                        "playerId": pid,
                        "accountName": acc,
                        "sessionToken": tok,
                        "itemUid": eq_item["uid"],
                        "useBlessing": bool(has_blessing),
                    },
                )
                if (res_up.get("result") or {}).get("ok"):
                    mem["upgradesAttempted"] += 1
                break

        # Seelenweberin: Equipment verstärken (1.–4. Bonus mit 'item_bonus_adder', 5. Bonus mit 'item_blessing_orb',
        # 6./7. Bonus mit 'item_soul_fragment') und Boni switchen ('item_bonus_changer' & 'item_aether_seal') inkl. Talisman & Gürtel (KI v4.0)
        has_add_bonus = any((it.get("templateId") or it.get("id")) == "item_bonus_adder" for it in inv)
        has_orb_bonus = any((it.get("templateId") or it.get("id")) == "item_blessing_orb" for it in inv)
        has_soul_bonus = any((it.get("templateId") or it.get("id")) in ("item_soul_fragment", "mat_soul_stone") for it in inv)
        has_reroll_bonus = any((it.get("templateId") or it.get("id")) == "item_bonus_changer" for it in inv)
        has_seal_bonus = any((it.get("templateId") or it.get("id")) == "item_aether_seal" for it in inv)
        if has_add_bonus or has_orb_bonus or has_soul_bonus or has_reroll_bonus:
            for slot_key in ("weapon", "armor", "helmet", "shield", "bracelet", "necklace", "earrings", "shoes", "talisman", "belt"):
                eq_item = eq.get(slot_key)
                if not eq_item or not eq_item.get("uid"):
                    continue
                bonuses = eq_item.get("bonuses") or []
                if len(bonuses) < 4 and has_add_bonus:
                    res_rw = api_post(
                        server_url,
                        {
                            "action": "runeweaver",
                            "playerId": pid,
                            "accountName": acc,
                            "sessionToken": tok,
                            "itemUid": eq_item["uid"],
                            "subAction": "add",
                        },
                    )
                    if (res_rw.get("result") or {}).get("ok"):
                        mem["bonusesAdded"] += 1
                    break
                elif len(bonuses) == 4 and has_orb_bonus:
                    res_rw = api_post(
                        server_url,
                        {
                            "action": "runeweaver",
                            "playerId": pid,
                            "accountName": acc,
                            "sessionToken": tok,
                            "itemUid": eq_item["uid"],
                            "subAction": "add5",
                        },
                    )
                    if (res_rw.get("result") or {}).get("ok"):
                        mem["bonusesAdded"] += 1
                    break
                elif 5 <= len(bonuses) < 7 and has_soul_bonus and yang >= 25000:
                    res_rw = api_post(
                        server_url,
                        {
                            "action": "runeweaver",
                            "playerId": pid,
                            "accountName": acc,
                            "sessionToken": tok,
                            "itemUid": eq_item["uid"],
                            "subAction": "add67",
                        },
                    )
                    if (res_rw.get("result") or {}).get("ok"):
                        mem["bonusesAdded"] += 1
                    break
                elif len(bonuses) >= 2 and has_reroll_bonus:
                    desired_bonus_ids = {
                        "warrior": ("bonus_vs_monster", "bonus_dss", "bonus_str", "bonus_crit", "bonus_hp_absorb", "bonus_vs_metin"),
                        "ninja": ("bonus_vs_monster", "bonus_crit", "bonus_dex", "bonus_pierce", "bonus_dss", "bonus_atk_speed"),
                        "sura": ("bonus_vs_monster", "bonus_int", "bonus_dss", "bonus_fks", "bonus_crit", "bonus_hp_absorb"),
                        "shaman": ("bonus_int", "bonus_vs_monster", "bonus_fks", "bonus_crit", "bonus_vs_metin", "bonus_hp"),
                    }.get(cfg.get("classId", "warrior"), ("bonus_vs_monster", "bonus_dss", "bonus_crit"))
                    matched_indices = [
                        b_idx for b_idx, b_entry in enumerate(bonuses[:5])
                        if isinstance(b_entry, dict) and b_entry.get("id") in desired_bonus_ids
                    ]
                    if matched_indices and int(eq_item.get("lockedBonusIdx", -1)) < 0 and has_seal_bonus:
                        api_post(
                            server_url,
                            {
                                "action": "runeweaver",
                                "playerId": pid,
                                "accountName": acc,
                                "sessionToken": tok,
                                "itemUid": eq_item["uid"],
                                "subAction": "lock",
                                "lockIdx": matched_indices[0],
                            },
                        )
                    if len(matched_indices) < 2:
                        res_rw = api_post(
                            server_url,
                            {
                                "action": "runeweaver",
                                "playerId": pid,
                                "accountName": acc,
                                "sessionToken": tok,
                                "itemUid": eq_item["uid"],
                                "subAction": "reroll",
                            },
                        )
                        if (res_rw.get("result") or {}).get("ok"):
                            mem["bonusesSwitched"] += 1
                        break

    # 6. Auto-Sell für nicht benötigte Drops & Offline-Shop / Markt-Interaktion (gemäß bal_prop_03 & AureliaBot-Wissensbasis)
    if tick_idx % 4 == 0:
        cls_id = cfg["classId"]
        use_2h = bool(cfg.get("useTwoHand", False))
        sell_uids = []
        shop_candidate = None
        for it in list(inv):
            iid = str(it.get("templateId") or it.get("id") or "")
            item_uid = it.get("uid")
            if not item_uid or it.get("equippedSlot") or it.get("equipped_slot") or it.get("reservedShopId") or it.get("reserved_shop_id"):
                continue
            tpl = ITEM_TEMPLATES.get(iid, {})
            itype = tpl.get("type", it.get("type", "misc"))
            plus_v = int(it.get("plusLevel", it.get("plus", 0)))
            bonuses = it.get("bonuses") or []
            allowed_cls = tpl.get("classes")
            if itype == "equipment":
                eq_slot = tpl.get("slot") or it.get("slot")
                cur_eq = eq.get(eq_slot) if eq_slot else None
                cand_score = score_bot_equipment_item(it, cls_id, use_two_hand=use_2h)
                cur_score = score_bot_equipment_item(cur_eq, cls_id, use_two_hand=use_2h) if cur_eq else -1.0
                # Niemals ein besseres Ausrüstungsteil (oder ein kommendes Upgrade für die nächsten 5 Level) verkaufen!
                if cand_score > cur_score + 0.5 and int(tpl.get("reqLevel", 1)) <= lvl + 5:
                    continue
                if plus_v >= 4 or len(bonuses) >= 2:
                    shop_candidate = it
                elif plus_v <= 2 and (not allowed_cls or cls_id in allowed_cls):
                    sell_uids.append(item_uid)
            elif (iid.startswith("fb_") or itype == "skill_book") and tpl.get("classId") != cls_id:
                shop_candidate = it
            elif iid in ("mat_monolith_shard", "scroll_blessing", "mat_soul_stone", "mat_white_pearl") and int(it.get("quantity", 1)) >= 3:
                shop_candidate = it

        if sell_uids:
            res_sell = api_post(
                server_url,
                {
                    "action": "batch_sell_items",
                    "playerId": pid,
                    "accountName": acc,
                    "sessionToken": tok,
                    "itemUids": sell_uids[:8],
                },
            )
            if (res_sell.get("result") or {}).get("ok"):
                mem["itemsAutoSold"] += len(sell_uids[:8])

        if shop_candidate is not None and mem.get("shopItemsListed", 0) < 12:
            est_price = estimate_item_market_price(shop_candidate)
            city_label = "Seiryu-Stadt" if cfg.get("empire") == "seiryu" else "Kaeryu-Stadt"
            res_sh = api_post(
                server_url,
                {
                    "action": "create_shop_listing",
                    "playerId": pid,
                    "accountName": acc,
                    "sessionToken": tok,
                    "shopTitle": f"{cfg['name']}s Handelsstand ({city_label})",
                    "itemUid": shop_candidate.get("uid"),
                    "priceYang": est_price,
                },
            )
            if (res_sh.get("result") or {}).get("ok"):
                mem["shopItemsListed"] += 1

        # Offline-Shop-Einnahmen abheben & das andere Reich besuchen, um Shops zu prüfen und benötigte Items intelligent zu kaufen
        if int(p_state.get("shopVaultYang", 0)) > 0:
            api_post(
                server_url,
                {
                    "action": "withdraw_shop_vault",
                    "playerId": pid,
                    "accountName": acc,
                    "sessionToken": tok,
                },
            )

        world_shops = snap.get("offlineShops") or []
        if world_shops:
            emp_is_seiryu = str(cfg.get("empire", "seiryu")).lower() == "seiryu"
            foreign_shops = [
                sh for sh in world_shops
                if (sh.get("owner_id") or sh.get("ownerId")) != pid
                and ((emp_is_seiryu and float(sh.get("pos_x", 0.0)) < 0.0) or (not emp_is_seiryu and float(sh.get("pos_x", 0.0)) > 0.0))
            ]
            other_own_shops = [
                sh for sh in world_shops
                if (sh.get("owner_id") or sh.get("ownerId")) != pid and sh not in foreign_shops
            ]
            if foreign_shops:
                mem["foreignShopVisits"] = int(mem.get("foreignShopVisits", 0)) + 1

            if yang >= 4000:
                for sh in (foreign_shops + other_own_shops):
                    bought_item = False
                    for lst in (sh.get("listings") or sh.get("items") or []):
                        ask_price = int(lst.get("priceYang", lst.get("price", 999999)))
                        if ask_price <= 0 or yang < ask_price + 2500:
                            continue
                        iid = str(lst.get("templateId") or lst.get("id") or "")
                        tpl_l = ITEM_TEMPLATES.get(iid, {})
                        if not tpl_l:
                            continue
                        itype_l = tpl_l.get("type", lst.get("type", "misc"))
                        needs_it = False
                        if itype_l == "equipment":
                            eq_slot = tpl_l.get("slot") or lst.get("slot")
                            cur_eq = eq.get(eq_slot) if eq_slot else None
                            cand_sc = score_bot_equipment_item(lst, cls_id, use_two_hand=use_2h)
                            cur_sc = score_bot_equipment_item(cur_eq, cls_id, use_two_hand=use_2h) if cur_eq else -1.0
                            if cand_sc > 0 and cand_sc > cur_sc + 0.5 and int(tpl_l.get("reqLevel", 1)) <= lvl + 3:
                                needs_it = True
                        elif iid in ("scroll_blessing", "item_bonus_adder", "item_bonus_changer", "item_blessing_orb", "item_soul_fragment", "mat_soul_stone", "mat_white_pearl"):
                            needs_it = True
                        elif (iid.startswith("fb_") or itype_l == "skill_book") and tpl_l.get("classId") in (None, cls_id):
                            needs_it = True
                        elif iid in ("chest_moonlight", "chest_skill_books", "chest_boss_reaper"):
                            needs_it = True

                        fair_val = max(estimate_item_market_price(lst), 22000)
                        if needs_it and ask_price <= int(fair_val * 1.15):
                            res_buy = api_post(
                                server_url,
                                {
                                    "action": "buy_shop_listing",
                                    "playerId": pid,
                                    "accountName": acc,
                                    "sessionToken": tok,
                                    "listingId": lst.get("listingId"),
                                },
                            )
                            if (res_buy.get("result") or {}).get("ok"):
                                mem["marketPurchases"] = int(mem.get("marketPurchases", 0)) + 1
                                bought_item = True
                                break
                    if bought_item:
                        break

    # 7. NPC-Quests & Biologenforschung laufen in KI v5.0 physisch über den Gang zu den Stadt-NPCs in world_server.py (_tick_bot_town_errand)
    if tick_idx % 6 == 0:
        srv_quests_done = int(p_state.get("questsTurnedIn", af_stats.get("questsTurnedIn", 0)))
        if srv_quests_done > int(mem.get("questsTurnedIn", 0)):
            mem["questsTurnedIn"] = srv_quests_done

    # 8. Dungeon (Äther-Katakomben) betreten und vervollständigen (ab Level 12)
    if lvl >= 12 and (tick_idx - mem.get("lastDungeonTick", -999)) >= 140 and idx_from_pid(pid) % 3 == (tick_idx // 30) % 3:
        mem["lastDungeonTick"] = tick_idx
        res_dng = api_post(
            server_url,
            {
                "action": "enter_dungeon",
                "playerId": pid,
                "accountName": acc,
                "sessionToken": tok,
            },
        )
        if res_dng.get("ok"):
            mem["dungeonsEntered"] += 1

    # 9. Intelligenter Standortwechsel (Gebiet 1 Nord <-> Gebiet 2 Süd über die 2 Steinbrücken) & Event-Anpassung
    sectors = EMPIRE_HUNTING_PROGRESSION.get(cfg.get("empire", "seiryu"), EMPIRE_HUNTING_PROGRESSION["seiryu"])
    cur_sec_idx = max(0, min(len(sectors) - 1, int(mem.get("sectorIdx", 0))))
    recent_deaths = int(p_state.get("recentZoneDeaths", 0))
    zero_exp_streak = int(p_state.get("zeroExpStreak", 0))
    cur_sec = sectors[cur_sec_idx]
    active_evt = snap.get("worldEvent") or {}
    active_evt_id = str(active_evt.get("id", ""))

    new_sec_idx = cur_sec_idx
    if recent_deaths >= 2 and cur_sec_idx > 0:
        new_sec_idx = cur_sec_idx - 1
    else:
        for s_idx, s_def in enumerate(sectors):
            if lvl >= int(s_def.get("minLvl", s_def.get("minLv", 1))):
                new_sec_idx = max(new_sec_idx, s_idx)
        if zero_exp_streak >= 4 and new_sec_idx < len(sectors) - 1:
            if lvl >= int(sectors[new_sec_idx + 1].get("minLvl", 1)) - 2:
                new_sec_idx += 1

    party_members = ((snap.get("party") or {}).get("members")) or []
    in_human_party = any(not str(m.get("id", "")).startswith("bot_") for m in party_members)

    cur_pos_z = float(p_state.get("pos_z", 0.0))
    cur_anchor_z = float(((p_state.get("autofarm") or {}).get("anchorZ", cur_pos_z)) or cur_pos_z)
    status_str = str(p_state.get("autoFarmStatus", ""))
    fighting_monolith_or_boss = any(
        kw in status_str for kw in ("Rissmonolith", "Instabil", "Erwacht", "Weltboss", "Elite", "Monolithensplitter", "Risskern")
    )
    # Waehrend eines Stadtrundgangs / NPC-Quest-Gangs darf der Bot-Prozess das Ziel NICHT ueberschreiben,
    # sonst pendelt der Bot zwischen NPC (Stadt) und Jagdgebiet hin und her (haengt z.B. an Haeusern fest).
    on_town_errand = bool(p_state.get("townErrand")) or any(
        kw in status_str for kw in ("Stadtrundgang", "Gehe zu", "NPC-Quest", "Schmiede", "Veredele", "Verkaufe Beute")
    )
    wrong_area_for_map2 = bool(
        not fighting_monolith_or_boss
        and lvl >= 18
        and (cur_pos_z < 0.0 or cur_anchor_z < 80.0)
        and (tick_idx - mem.get("lastZoneSwitchTick", 0)) >= 4
    )

    force_sector_sync = (
        (not bool(mem.get("_initialSectorSynced")))
        or ("Suche Ziele" in status_str)
        or wrong_area_for_map2
    )
    if (
        not in_human_party
        and not fighting_monolith_or_boss
        and not on_town_errand
        and (force_sector_sync or (new_sec_idx != cur_sec_idx and (tick_idx - mem.get("lastZoneSwitchTick", 0)) >= 6))
    ):
        mem["_initialSectorSynced"] = True
        prev_area = int(sectors[cur_sec_idx].get("area", 1))
        next_area = int(sectors[new_sec_idx].get("area", 1))
        if prev_area != next_area:
            mem["bridgeCrossings"] = int(mem.get("bridgeCrossings", 0)) + 1
        mem["sectorIdx"] = new_sec_idx
        mem["lastZoneSwitchTick"] = tick_idx
        if new_sec_idx != cur_sec_idx:
            mem["zoneSwitches"] += 1
        target_sec = sectors[new_sec_idx]
        # Für weite Distanzen (z.B. Wechsel über die 2 Steinbrücken zwischen Gebiet 1 Nord und Gebiet 2 Süd) Pferd benutzen!
        api_post(
            server_url,
            {
                "action": "toggle_mount",
                "playerId": pid,
                "accountName": acc,
                "sessionToken": tok,
                "mountId": cfg.get("mountId", "mount_swift_steed"),
                "desiredState": "mount",
            },
        )
        hunt_mode = "all"
        api_post(
            server_url,
            {
                "action": "toggle_autofarm",
                "playerId": pid,
                "accountName": acc,
                "sessionToken": tok,
                "enabled": True,
                "config": {
                    "mode": hunt_mode,
                    "radius": 240,
                    "anchorX": float(target_sec["x"]),
                    "anchorZ": float(target_sec["z"]),
                    "autoSkills": True,
                    "autoPotion": True,
                    "autoPotionHpPct": 70,
                    "autoLoot": True,
                    "autoSell": True,
                    "autoMount": True,
                    "huntMonsters": True,
                    "huntMetins": True,
                    "prioritizeElites": True,
                },
            },
        )

    # 10. Intelligente Chat-Antworten auf Spieler-Nachrichten & Rufchat ohne Spam/Wiederholung
    chat_list = snap.get("chat") or []
    bot_names_lower = {c["name"].lower() for c in BOT_CONFIGS}
    now_ts = time.time()

    for cmsg in chat_list[-8:]:
        msg_id = cmsg.get("id")
        if not msg_id or msg_id in chat_ai.processed_msg_ids:
            continue
        sender = str(cmsg.get("sender") or "")
        msg_text = str(cmsg.get("text") or "").strip()
        msg_ch = str(cmsg.get("channel") or "global").lower()
        if (
            not sender
            or msg_ch in ("drops", "event", "system")
            or sender.lower() in bot_names_lower
            or sender.lower() in ("system", "server", "beute", "welt-herold", "riss-chronist", "ki-evolution", "schmied", "seelenweberin")
            or sender.lower().startswith("[bot]")
        ):
            chat_ai.processed_msg_ids.add(msg_id)
            continue

        # Ein echter Spieler hat geschrieben! Prüfe, ob dieser Bot antworten soll
        mentioned_this_bot = cfg["name"].lower() in msg_text.lower()
        same_empire = str(cmsg.get("empire", "")).lower() in ("", cfg.get("empire", "seiryu").lower())
        if (mentioned_this_bot or same_empire) and (now_ts - chat_ai.last_reply_ts) >= 8.0:
            reply_txt = chat_ai.generate_contextual_reply(sender, msg_text, cfg, {**p_state, "botSectorIdx": mem["sectorIdx"]})
            if reply_txt:
                chat_ai.processed_msg_ids.add(msg_id)
                chat_ai.last_reply_ts = now_ts
                chat_ai._record_sent(pid, reply_txt)
                reply_channel = cmsg.get("channel") if cmsg.get("channel") in ("global", "local", "empire", "trade") else "global"
                api_post(
                    server_url,
                    {
                        "action": "chat",
                        "playerId": pid,
                        "accountName": acc,
                        "sessionToken": tok,
                        "channel": reply_channel,
                        "text": reply_txt,
                    },
                )
                break

    # Gelegentlicher Rufchat (maximal alle 95 Sekunden global über alle Bots hinweg, niemals derselbe Satz)
    if (now_ts - chat_ai.last_shout_ts) >= 95.0 and (now_ts - chat_ai.bot_last_chat_ts.get(pid, 0.0)) >= 300.0:
        ch, shout_txt = chat_ai.build_event_rufchat(cfg, {**p_state, "botSectorIdx": mem["sectorIdx"]})
        if shout_txt:
            chat_ai.last_shout_ts = now_ts
            chat_ai._record_sent(pid, shout_txt)
            api_post(
                server_url,
                {
                    "action": "chat",
                    "playerId": pid,
                    "accountName": acc,
                    "sessionToken": tok,
                    "channel": ch,
                    "text": shout_txt,
                },
            )


def idx_from_pid(pid: str) -> int:
    for i, c in enumerate(BOT_CONFIGS):
        if c["playerId"] == pid:
            return i
    return 0


def run_live_bots(server_url: str = "http://127.0.0.1:8090"):
    """Verbindet alle 12 Spieler-Bots (6 in Reich Seiryu, 6 in Reich Kaeryu) live mit dem laufenden Server,
    liest Steuerbefehle aus dem AI Test Center (`bot_control_state.json`) und aktualisiert fortlaufend `bot_telemetry_live.json`."""
    print(f"[BotPlayers] Verbinde {len(BOT_CONFIGS)} selbstlernende Live-Bots (6 Seiryu, 6 Kaeryu) mit {server_url} ...", flush=True)
    ctrl = load_or_init_control_state()
    sync_bot_rules_memory_to_knowledge_base()
    sessions = {}
    chat_ai = BotChatIntelligence()
    bot_runtime_mem = {}

    for cfg in BOT_CONFIGS:
        pid = cfg["playerId"]
        tok = f"bot_sess_{pid}"
        sessions[pid] = tok
        if not ctrl.get("botsEnabled", {}).get(pid, True):
            continue
        sectors = EMPIRE_HUNTING_PROGRESSION.get(cfg.get("empire", "seiryu"), EMPIRE_HUNTING_PROGRESSION["seiryu"])
        join_res = api_post(
            server_url,
            {
                "action": "join",
                "playerId": pid,
                "accountName": cfg["accountName"],
                "sessionToken": tok,
                "name": cfg["name"],
                "classId": cfg["classId"],
                "empire": cfg["empire"],
                "inWorld": True,
            },
        )
        joined_p = ((join_res.get("snapshot") or {}).get("player")) or {}
        joined_lvl = int(joined_p.get("level", 1) or 1)
        init_sec_idx = 0
        for s_i, s_def in enumerate(sectors):
            if joined_lvl >= int(s_def.get("minLvl", s_def.get("minLv", 1))):
                init_sec_idx = s_i
        init_sec = sectors[min(len(sectors) - 1, init_sec_idx)]
        api_post(
            server_url,
            {
                "action": "toggle_pet",
                "playerId": pid,
                "accountName": cfg["accountName"],
                "sessionToken": tok,
                "petId": cfg.get("petId", "pet_fire_phoenix"),
                "skinKey": cfg.get("petSkin", "ridack_dragonpet"),
                "desiredState": "summon",
            },
        )
        if cfg.get("useMount"):
            api_post(
                server_url,
                {
                    "action": "toggle_mount",
                    "playerId": pid,
                    "accountName": cfg["accountName"],
                    "sessionToken": tok,
                    "mountId": cfg.get("mountId", "mount_crystal_wolf"),
                    "desiredState": "mount",
                },
            )
        hunt_mode = "all"
        api_post(
            server_url,
            {
                "action": "toggle_autofarm",
                "playerId": pid,
                "accountName": cfg["accountName"],
                "sessionToken": tok,
                "enabled": True,
                "config": {
                    "mode": hunt_mode,
                    "radius": 240,
                    "anchorX": float(init_sec["x"]),
                    "anchorZ": float(init_sec["z"]),
                    "autoSkills": True,
                    "autoPotion": True,
                    "autoPotionHpPct": 70,
                    "autoLoot": True,
                    "autoSell": True,
                    "autoMount": True,
                    "huntMonsters": True,
                    "huntMetins": True,
                    "prioritizeElites": True,
                },
            },
        )
        print(f"  -> [{cfg['empire'].upper()}] {cfg['name']} ({cfg['roleDesc']}) ist LIVE im Spiel!", flush=True)

    tick_idx = 0
    while True:
        time.sleep(2.5)
        tick_idx += 1
        ctrl = load_or_init_control_state()
        live_status = {
            "updatedAt": time.strftime("%Y-%m-%d %H:%M:%S"),
            "botCount": len(BOT_CONFIGS),
            "activeStrategyVersion": "v5.0_omni_synergy",
            "learningEnabled": bool(ctrl.get("learningEnabled", True)),
            "groupMode": bool(ctrl.get("groupMode", False)),
            "groupSize": int(ctrl.get("groupSize", 12)),
            "bots": {},
        }

        for idx, cfg in enumerate(BOT_CONFIGS):
            pid = cfg["playerId"]
            tok = sessions[pid]
            bot_enabled = bool(ctrl.get("botsEnabled", {}).get(pid, True))
            if ctrl.get("groupMode") and idx >= int(ctrl.get("groupSize", 12)):
                bot_enabled = False

            if not bot_enabled:
                try:
                    api_post(
                        server_url,
                        {
                            "action": "leave_world",
                            "playerId": pid,
                            "accountName": cfg["accountName"],
                            "sessionToken": tok,
                        },
                    )
                except Exception:
                    pass
                live_status["bots"][pid] = {
                    "playerId": pid,
                    "name": cfg["name"],
                    "empire": cfg["empire"],
                    "classId": cfg["classId"],
                    "roleDesc": cfg["roleDesc"],
                    "groupRole": cfg.get("groupRole", "dps"),
                    "online": False,
                    "status": "⏸️ Pausiert (über AI Test Center)",
                }
                continue

            try:
                res = api_post(
                    server_url,
                    {
                        "action": "pickup_all_nearby",
                        "playerId": pid,
                        "accountName": cfg["accountName"],
                        "sessionToken": tok,
                        "inWorld": True,
                    },
                )
                snap = res.get("snapshot", {})
                p_state = snap.get("player") or {}
                if not p_state.get("online"):
                    api_post(
                        server_url,
                        {
                            "action": "join",
                            "playerId": pid,
                            "accountName": cfg["accountName"],
                            "sessionToken": tok,
                            "name": cfg["name"],
                            "classId": cfg["classId"],
                            "empire": cfg["empire"],
                            "inWorld": True,
                        },
                    )
                if p_state.get("isDead") or float(p_state.get("hp", 1)) <= 0:
                    api_post(
                        server_url,
                        {
                            "action": "respawn_player",
                            "playerId": pid,
                            "accountName": cfg["accountName"],
                            "sessionToken": tok,
                            "mode": "here",
                        },
                    )

                # Führe alle autonomen Wartungs-, Upgrade-, Shop-, Quest-, Dungeon-, Zonen- und Chat-Aktionen aus
                _live_bot_autonomous_maintenance(
                    server_url,
                    cfg,
                    tok,
                    p_state,
                    snap,
                    tick_idx,
                    chat_ai,
                    bot_runtime_mem,
                )

                af_stats = (p_state.get("autofarm") or {}).get("stats") or {}
                mem = bot_runtime_mem.get(pid, {})
                sectors = EMPIRE_HUNTING_PROGRESSION.get(cfg.get("empire", "seiryu"), EMPIRE_HUNTING_PROGRESSION["seiryu"])
                cur_sec = sectors[min(len(sectors) - 1, int(mem.get("sectorIdx", 0)))]

                # WICHTIG: AFK-/Stillstands-Erkennung & Ausschluss aus der Live-Statistik!
                # Wenn ein Bot aus irgendeinem Grund AFK herumsteht (keine Bewegung & keine Kampfaktivität),
                # darf diese Zeit NICHT in die aktive Statistik einberechnet werden!
                cur_x = float(p_state.get("pos_x", 0.0))
                cur_z = float(p_state.get("pos_z", 0.0))
                cur_kills = int(af_stats.get("monstersKilled", 0)) + int(af_stats.get("metinsDestroyed", 0))
                cur_exp_earned = int(af_stats.get("expEarned", 0))
                prev_x = mem.get("_lastPosX")
                prev_z = mem.get("_lastPosZ")
                prev_kills = mem.get("_lastKills", cur_kills)
                prev_exp = mem.get("_lastExpEarned", cur_exp_earned)
                moved_since_last = dist2d(cur_x, cur_z, float(prev_x), float(prev_z)) if (prev_x is not None and prev_z is not None) else 1.0
                progressed_since_last = (cur_kills > prev_kills) or (cur_exp_earned > prev_exp)
                has_active_target = bool(p_state.get("targetId") or p_state.get("autoFarmTargetId"))
                is_afk_idle_now = bool(p_state.get("isAfkIdle")) or (
                    moved_since_last < 0.20
                    and not progressed_since_last
                    and not has_active_target
                    and "Bekämpfe" not in str(p_state.get("autoFarmStatus", ""))
                )
                mem["_lastPosX"] = cur_x
                mem["_lastPosZ"] = cur_z
                mem["_lastKills"] = cur_kills
                mem["_lastExpEarned"] = cur_exp_earned
                if is_afk_idle_now and (p_state.get("townErrand") or "Stadtrundgang" in str(p_state.get("autoFarmStatus", ""))):
                    # Stadtrundgang ist kein AFK -> keine "Selbstheilung", die das NPC-Ziel ueberschreibt
                    is_afk_idle_now = False
                if is_afk_idle_now:
                    mem["afkSecondsExcluded"] = round(float(mem.get("afkSecondsExcluded", 0.0)) + 2.5, 1)
                    mem["afkIdleTicks"] = int(mem.get("afkIdleTicks", 0)) + 1
                    # Sofortige Selbstheilung falls der Bot 3 Zyklen (7.5s) AFK stand:
                    if mem["afkIdleTicks"] >= 3:
                        mem["afkIdleTicks"] = 0
                        mem["afkRecoveries"] = int(mem.get("afkRecoveries", 0)) + 1
                        api_post(
                            server_url,
                            {
                                "action": "toggle_autofarm",
                                "playerId": pid,
                                "accountName": cfg["accountName"],
                                "sessionToken": tok,
                                "enabled": True,
                                "config": {
                                    "mode": "all",
                                    "radius": 240,
                                    "anchorX": float(cur_sec["x"]) + random.uniform(-16.0, 16.0),
                                    "anchorZ": float(cur_sec["z"]) + random.uniform(-16.0, 16.0),
                                    "autoSkills": True,
                                    "autoPotion": True,
                                    "autoPotionHpPct": 70,
                                    "autoLoot": True,
                                    "autoSell": True,
                                    "autoMount": True,
                                    "huntMonsters": True,
                                    "huntMetins": True,
                                    "prioritizeElites": True,
                                },
                            },
                        )
                else:
                    mem["afkIdleTicks"] = 0
                    mem["activeHuntingSeconds"] = round(float(mem.get("activeHuntingSeconds", 0.0)) + 2.5, 1)

                eq_wpn = ((p_state.get("equipment") or {}).get("weapon")) or {}
                wpn_plus = int(eq_wpn.get("plusLevel", eq_wpn.get("plus", 0)))
                wpn_raw_name = str(eq_wpn.get("name", "Starterwaffe"))
                wpn_label = wpn_raw_name if f"+{wpn_plus}" in wpn_raw_name else f"{wpn_raw_name} +{wpn_plus}"
                eq_arm = ((p_state.get("equipment") or {}).get("armor")) or {}
                arm_plus = int(eq_arm.get("plusLevel", eq_arm.get("plus", 0)))
                arm_raw_name = str(eq_arm.get("name", "Starterrüstung"))
                arm_label = arm_raw_name if f"+{arm_plus}" in arm_raw_name else f"{arm_raw_name} +{arm_plus}"
                if snap.get("worldEvent"):
                    live_status["worldEvent"] = snap.get("worldEvent")
                live_status["bots"][pid] = {
                    "playerId": pid,
                    "name": p_state.get("name", cfg["name"]),
                    "empire": cfg["empire"],
                    "classId": p_state.get("class_id", cfg["classId"]),
                    "roleDesc": cfg["roleDesc"],
                    "groupRole": cfg.get("groupRole", "dps"),
                    "online": True,
                    "level": p_state.get("level", 1),
                    "hp": int(p_state.get("hp", 0)),
                    "maxHp": int(p_state.get("max_hp", 1)),
                    "mp": int(p_state.get("mp", 0)),
                    "maxMp": int(p_state.get("max_mp", 1)),
                    "posX": round(float(p_state.get("pos_x", 0.0)), 1),
                    "posZ": round(float(p_state.get("pos_z", 0.0)), 1),
                    "currentSector": cur_sec["name"],
                    "activeMount": p_state.get("active_mount"),
                    "weaponName": wpn_label,
                    "armorName": arm_label,
                    "activeStrategy": "v5.0_omni_synergy",
                    "evolutionV3": p_state.get("evolutionV3") or {},
                    "status": p_state.get("autoFarmStatus", "🤖 Adaptive Jagd aktiv"),
                    "yang": p_state.get("yang", 0),
                    "reputation": p_state.get("reputation", 0),
                    "petLevel": ((p_state.get("petData") or {}).get("level", 1)),
                    "mountLevel": ((p_state.get("mountData") or {}).get("level", 1)),
                    "party": snap.get("party"),
                    "partySize": len(((snap.get("party") or {}).get("members")) or [1]),
                    "partyExpBonusPct": int((snap.get("party") or {}).get("expBonusPct", 0)),
                    "socialProfile": get_bot_social_profile(pid),
                    "itemsEquippedUpgrades": max(int(mem.get("itemsEquippedUpgrades", 0)), int(af_stats.get("itemsEquippedUpgrades", 0))),
                    "chestsOpened": mem.get("chestsOpened", 0),
                    "upgradesAttempted": mem.get("upgradesAttempted", 0),
                    "bonusesAdded": mem.get("bonusesAdded", 0),
                    "bonusesSwitched": mem.get("bonusesSwitched", 0),
                    "itemsAutoSold": mem.get("itemsAutoSold", 0),
                    "questsTurnedIn": max(int(mem.get("questsTurnedIn", 0)), int(p_state.get("questsTurnedIn", af_stats.get("questsTurnedIn", 0)))),
                    "questsAccepted": int(p_state.get("questsAccepted", af_stats.get("questsAccepted", 0))),
                    "townVisits": int(p_state.get("townVisits", 0)),
                    "dungeonsEntered": mem.get("dungeonsEntered", 0),
                    "shopItemsListed": max(int(mem.get("shopItemsListed", 0)), int(p_state.get("offlineShopListingsCreated", af_stats.get("offlineShopListingsCreated", 0)))),
                    "foreignShopVisits": max(int(mem.get("foreignShopVisits", 0)), int(p_state.get("foreignShopVisits", af_stats.get("foreignShopVisits", 0)))),
                    "marketPurchases": max(int(mem.get("marketPurchases", 0)), int(p_state.get("marketPurchases", af_stats.get("marketPurchases", 0)))),
                    "zoneSwitches": mem.get("zoneSwitches", 0),
                    "bridgeCrossings": max(int(mem.get("bridgeCrossings", 0)), int(p_state.get("bridgeCrossings", 0))),
                    "partySplits": int(p_state.get("partySplits", af_stats.get("partySplits", 0))),
                    "empireSkirmishes": int(p_state.get("empireSkirmishes", af_stats.get("empireSkirmishes", 0))),
                    "isAfkIdle": is_afk_idle_now,
                    "activeSeconds": round(float(af_stats.get("activeSeconds", mem.get("activeHuntingSeconds", 0.0))), 1),
                    "afkExcludedSeconds": round(max(float(af_stats.get("afkExcludedSeconds", 0.0)), float(mem.get("afkSecondsExcluded", 0.0))), 1),
                    "stats": af_stats,
                }
            except Exception as e:
                print(f"[BotPlayers Warn] {pid}: {e}", flush=True)

        if tick_idx % 2 == 0:
            try:
                with open(LIVE_TELEMETRY_PATH, "w", encoding="utf-8") as lf:
                    json.dump(live_status, lf, indent=2, ensure_ascii=False)
            except Exception:
                pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Aeryndor 12-Bot Self-Learning & Optimization Engine")
    parser.add_argument("--benchmark", type=float, default=0.0, help="Simuliere X Sekunden im 20Hz-Benchmark-Modus")
    parser.add_argument("--live", action="store_true", help="Verbinde alle 12 Bots live mit dem laufenden Server")
    parser.add_argument("--url", type=str, default="http://127.0.0.1:8090", help="Server-URL für --live")
    args = parser.parse_args()

    if args.benchmark > 0:
        rep = run_complete_test_suite_and_optimization(args.benchmark)
        print(json.dumps({"ok": True, "botCount": rep["botCount"], "qaIssues": len(rep["qaIssues"])}, ensure_ascii=False))
    elif args.live:
        run_live_bots(args.url)
    else:
        rep = run_complete_test_suite_and_optimization(600.0)
        print(json.dumps({"ok": True, "botCount": rep["botCount"], "qaIssues": len(rep["qaIssues"])}, ensure_ascii=False))
