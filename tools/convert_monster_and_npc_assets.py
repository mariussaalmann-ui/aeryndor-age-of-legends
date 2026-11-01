# -*- coding: utf-8 -*-
"""
Converts Map 1 (Morgenwacht) & Map 2 (Grenzland) Monsters and Village NPCs
from C:\\Users\\Anwender\\Desktop\\Aeryndor assets\\monster into self-contained
Three.js GLB models (with merged Wait/Walk/Run/Attack/Dead skeletal animations)
and PNG textures inside public/assets/models/.
"""

import json
import os
import shutil
import struct
import subprocess
import tempfile

NOESIS_EXE = r"D:\Infinity War\Server\.Systeme & Stuff\Tools\3ds max\3ds Max 2024\3DsMax Settings\Noesis\Noesis.exe"
NOESIS_DIR = os.path.dirname(NOESIS_EXE)

ASSET_ROOT = r"C:\Users\Anwender\Desktop\Aeryndor assets\monster"
M1_MON_ROOT = os.path.join(ASSET_ROOT, "Map1", "Monsters", "Clientside")
M2_MON_ROOT = os.path.join(ASSET_ROOT, "Map2", "Monsters", "Clientside")
NPC_ROOT = os.path.join(ASSET_ROOT, "Map1", "Npc")
ORC_PACK_ROOT = r"D:\Infinity War\Server\.Systeme & Stuff\Stuff\Riddack\Ridack Orc Pack\monster"

OUT_DIR = r"d:\Aeryndor Age of Legends\public\assets\models"
OUT_MON_DIR = os.path.join(OUT_DIR, "monsters")
OUT_NPC_DIR = os.path.join(OUT_DIR, "npcs")


MONSTER_ASSETS = {
    # Map 1 (Morgenwacht) Animals & White Oath
    "pewi_stray_dog": {
        "folder": os.path.join(M1_MON_ROOT, "monster3", "pewi_stray_dog"),
        "model": "pewi_stray_dog.gr2",
        "anims": {
            "wait": "00.gr2",
            "walk": "02.gr2",
            "run": "03.gr2",
            "attack": "20.gr2",
            "dead": "31.gr2",
        },
        "textures": [
            "pewi_stray_dog_col1.dds",
            "pewi_stray_dog_col2.dds",
            "pewi_stray_dog_col3.dds",
            "pewi_stray_dog_col4.dds",
        ],
    },
    "mr_pewi_boar": {
        "folder": os.path.join(M1_MON_ROOT, "monster3", "mr_pewi_boar"),
        "model": "mr_pewi_boar.gr2",
        "anims": {
            "wait": "wait.gr2",
            "walk": "walk.gr2",
            "run": "run.gr2",
            "attack": "attack.gr2",
            "dead": "dead.gr2",
        },
        "textures": [
            "boar_col1.dds",
            "boar_col2.dds",
            "boar_col3.dds",
            "boar_col4.dds",
        ],
    },
    "pewi_bear": {
        "folder": os.path.join(M1_MON_ROOT, "monster3", "pewi_bear"),
        "model": "pewi_bear.gr2",
        "anims": {
            "wait": "wait.gr2",
            "walk": "walk.gr2",
            "run": "run.gr2",
            "attack": "attack.gr2",
            "dead": "dead.gr2",
        },
        "textures": [
            "pewi_bear_col1.dds",
            "pewi_bear_col2.dds",
            "pewi_bear_col3.dds",
            "pewi_bear_col4.dds",
            "pewi_bear_col5.dds",
        ],
    },
    "pewi_tiger": {
        "folder": os.path.join(M1_MON_ROOT, "monster3", "pewi_tiger"),
        "model": "pewi_tiger.gr2",
        "anims": {
            "wait": "wait.gr2",
            "walk": "walk.gr2",
            "run": "run.gr2",
            "attack": "attack.gr2",
            "dead": "dead.gr2",
        },
        "textures": [
            "pewi_tiger_col1.dds",
            "pewi_tiger_col2.dds",
            "pewi_tiger_col3.dds",
        ],
    },
    "bkembryo_pewi": {
        "folder": os.path.join(M1_MON_ROOT, "monster", "bkembryo_pewi"),
        "model": "bkembryo_pewi.gr2",
        "anims": {
            "wait": "wait.gr2",
            "walk": "run.gr2",
            "run": "run.gr2",
            "attack": "attack.gr2",
            "dead": "dead.gr2",
        },
        "textures": [
            "pewi_bkembryo1.dds",
            "pewi_bkembryo2.dds",
        ],
    },
    "bkseira_pewi": {
        "folder": os.path.join(M1_MON_ROOT, "monster", "bkseira_pewi"),
        "model": "bkseira_pewi.gr2",
        "anims": {
            "wait": "wait.gr2",
            "walk": "run.gr2",
            "run": "run.gr2",
            "attack": "attack.gr2",
            "dead": "dead.gr2",
        },
        "textures": [
            "bkseira_pewi1.dds",
            "bkseira_pewi2.dds",
            "bkseira_pewi3.dds",
        ],
    },
    "bktransf_pewi": {
        "folder": os.path.join(M1_MON_ROOT, "monster", "bktransf_pewi"),
        "model": "bktransf_pewi.gr2",
        "anims": {
            "wait": "wait.gr2",
            "walk": "walk.gr2",
            "run": "run.gr2",
            "attack": "attack.gr2",
            "dead": "dead.gr2",
        },
        "textures": [
            "bktransf_pewi1.dds",
            "bktransf_pewi2.dds",
        ],
    },
    "asenis_monster_m1_3": {
        "folder": os.path.join(M1_MON_ROOT, "monster", "asenis_monster_m1_3"),
        "model": "asenis_monster_m1_3.gr2",
        "anims": {
            "wait": "wait.gr2",
            "walk": "walk.gr2",
            "run": "run.gr2",
            "attack": "attack.gr2",
            "dead": "ded.gr2",
        },
        "textures": [
            "kozak.dds",
        ],
    },

    # Map 2 (Grenzland) Black Wind & Savage Clan + Boss
    "pewi_m2_xieyue": {
        "folder": os.path.join(M2_MON_ROOT, "monster3", "pewi_m2_xieyue"),
        "model": "pewi_m2_xieyue.gr2",
        "anims": {
            "wait": "wait.gr2",
            "walk": "walk.gr2",
            "run": "run.gr2",
            "attack": "attack.gr2",
            "dead": "dead.gr2",
        },
        "textures": [
            "xieyue_body_col1.dds",
            "xieyue_body_col2.dds",
            "xieyue_weapon_col1.dds",
            "xieyue_weapon_col2.dds",
        ],
    },
    "pewi_m2_dingtou": {
        "folder": os.path.join(M2_MON_ROOT, "monster3", "pewi_m2_dingtou"),
        "model": "pewi_m2_dingtou.gr2",
        "anims": {
            "wait": "00.gr2",
            "walk": "02.gr2",
            "run": "03.gr2",
            "attack": "20.gr2",
            "dead": "31.gr2",
        },
        "textures": [
            "dingtou_col1.dds",
            "dingtou_col3.dds",
            "dingtou_weapon_col1.dds",
            "dingtou_weapon_col3.dds",
        ],
    },
    "pewi_m2_bowman": {
        "folder": os.path.join(M2_MON_ROOT, "monster3", "pewi_m2_bowman"),
        "model": "pewi_m2_bowman.gr2",
        "anims": {
            "wait": "wait.gr2",
            "walk": "walk.gr2",
            "run": "run.gr2",
            "attack": "attack.gr2",
            "dead": "dead.gr2",
        },
        "textures": [
            "bowman_col1.dds",
            "bowman_col2.dds",
            "bowman_col3.dds",
        ],
    },
    "pewi_m2_kunlun": {
        "folder": os.path.join(M2_MON_ROOT, "monster3", "pewi_m2_kunlun"),
        "model": "pewi_m2_kunlun.gr2",
        "anims": {
            "wait": "wait.gr2",
            "walk": "walk.gr2",
            "run": "run.gr2",
            "attack": "attack.gr2",
            "dead": "dead.gr2",
        },
        "textures": [
            "kunlun_col1.dds",
            "kunlun_col4.dds",
            "kunlun_weapon_col1.dds",
            "kunlun_weapon_col4.dds",
        ],
    },
    "pewi_m2_ravager": {
        "folder": os.path.join(M2_MON_ROOT, "monster3", "pewi_m2_ravager"),
        "model": "pewi_m2_ravager.gr2",
        "anims": {
            "wait": "wait.gr2",
            "walk": "walk.gr2",
            "run": "run.gr2",
            "attack": "attack.gr2",
            "dead": "dead.gr2",
        },
        "textures": [
            "ravager1_col1.dds",
            "ravager1_col2.dds",
            "ravager1_col3.dds",
        ],
    },
    "pewi_m2_pangzi": {
        "folder": os.path.join(M2_MON_ROOT, "monster3", "pewi_m2_pangzi"),
        "model": "pewi_m2_pangzi.gr2",
        "anims": {
            "wait": "wait.gr2",
            "walk": "walk.gr2",
            "run": "run.gr2",
            "attack": "attack.gr2",
            "dead": "dead.gr2",
        },
        "textures": [
            "pangzi_col1.dds",
            "pangzi_col4.dds",
            "pangzi_weapon_col1.dds",
            "pangzi_weapon_col4.dds",
        ],
    },
    "pewi_m2_piratedeva": {
        "folder": os.path.join(M2_MON_ROOT, "monster3", "pewi_m2_piratedeva"),
        "model": "pewi_m2_piratedeva.gr2",
        "anims": {
            "wait": "wait.gr2",
            "walk": "walk.gr2",
            "run": "run.gr2",
            "attack": "attack.gr2",
            "dead": "dead.gr2",
        },
        "textures": [
            "piratedeva_col1.dds",
            "piratedeva_col2.dds",
            "piratedeva_col3.dds",
        ],
    },
    "pewi_m2_tuobei": {
        "folder": os.path.join(M2_MON_ROOT, "monster3", "pewi_m2_tuobei"),
        "model": "pewi_m2_tuobei.gr2",
        "anims": {
            "wait": "wait.gr2",
            "walk": "walk.gr2",
            "run": "run.gr2",
            "attack": "attack.gr2",
            "dead": "dead.gr2",
        },
        "textures": [
            "tuobei_col1.dds",
            "tuobei_col6.dds",
            "tuobei_weapon_col1.dds",
            "tuobei_weapon_col6.dds",
        ],
    },
    "pewi_m2_archbarb": {
        "folder": os.path.join(M2_MON_ROOT, "monster3", "pewi_m2_archbarb"),
        "model": "pewi_m2_archbarb.gr2",
        "anims": {
            "wait": "00.gr2",
            "walk": "03.gr2",
            "run": "03.gr2",
            "attack": "20.gr2",
            "dead": "31.gr2",
        },
        "textures": [
            "archbarb1_col1.dds",
            "archbarb2_col1.dds",
            "archbarb_weapon_col1.dds",
        ],
    },
    "pewi_m2_tongding": {
        "folder": os.path.join(M2_MON_ROOT, "monster3", "pewi_m2_tongding"),
        "model": "pewi_m2_tongding.gr2",
        "anims": {
            "wait": "wait.gr2",
            "walk": "walk.gr2",
            "run": "run.gr2",
            "attack": "attack.gr2",
            "dead": "dead.gr2",
        },
        "textures": [
            "tongding_col1.dds",
            "tongding_col3.dds",
            "tongding_weapon_col1.dds",
            "tongding_weapon_col3.dds",
        ],
    },
    "pewi_m2_jubi": {
        "folder": os.path.join(M2_MON_ROOT, "monster3", "pewi_m2_jubi"),
        "model": "pewi_m2_jubi.gr2",
        "anims": {
            "wait": "wait.gr2",
            "walk": "walk.gr2",
            "run": "run.gr2",
            "attack": "attack.gr2",
            "dead": "dead.gr2",
        },
        "textures": [
            "jubi_col1.dds",
            "jubi_col2.dds",
            "jubi_col3.dds",
        ],
    },

    # Orktal (Ridack Orc Pack: Mobs + Boss mit Wait, Run, Attack, Attack1/Skill, Knockdown, Standup, Dead)
    "ridack_moborc": {
        "folder": os.path.join(ORC_PACK_ROOT, "ridack_moborc"),
        "model": "ridack_moborc.gr2",
        "anims": {
            "wait": "00.gr2",
            "walk": "03.gr2",
            "run": "03.gr2",
            "attack": "20.gr2",
            "attack1": "20_1.gr2",
            "skill": "20_1.gr2",
            "dead": "37.gr2",
        },
        "textures": [
            ("ridack_moborc3.dds", "ridack_moborc_col3.png"),
            ("ridack_moborc.dds", "ridack_moborc_col1.png"),
            ("ridack_moborc2.dds", "ridack_moborc_col2.png"),
        ],
    },
    "ridack_moborc2": {
        "folder": os.path.join(ORC_PACK_ROOT, "ridack_moborc2"),
        "model": "ridack_moborc2.GR2",
        "anims": {
            "wait": "00.gr2",
            "walk": "03.gr2",
            "run": "03.gr2",
            "attack": "20.gr2",
            "attack1": "20_1.gr2",
            "knockdown": "55.gr2",
            "standup": "66.gr2",
            "dead": "37.gr2",
        },
        "textures": [
            ("ridack_moborc.dds", "ridack_moborc2_col1.png"),
            ("ridack_moborc2.dds", "ridack_moborc2_col2.png"),
            ("ridack_moborc3.dds", "ridack_moborc2_col3.png"),
        ],
    },
    "ridack_moborc3": {
        "folder": os.path.join(ORC_PACK_ROOT, "ridack_moborc3"),
        "model": "ridack_moborc3.GR2",
        "anims": {
            "wait": "00.gr2",
            "walk": "03.gr2",
            "run": "03.gr2",
            "attack": "20.gr2",
            "attack1": "20_1.gr2",
            "skill": "20_1.gr2",
            "knockdown": "55.gr2",
            "standup": "66.gr2",
            "dead": "37.gr2",
        },
        "textures": [
            ("ridack_moborc.dds", "ridack_moborc3_col1.png"),
            ("ridack_moborc2.dds", "ridack_moborc3_col2.png"),
            ("ridack_moborc3.dds", "ridack_moborc3_col3.png"),
        ],
    },
    "ridack_bossorc4": {
        "folder": os.path.join(ORC_PACK_ROOT, "ridack_bossorc4"),
        "model": "ridack_bossorc4.GR2",
        "anims": {
            "wait": "00.gr2",
            "walk": "03.gr2",
            "run": "03.gr2",
            "attack": "20.gr2",
            "attack1": "21.gr2",
            "skill": "21.gr2",
            "dead": "37.gr2",
        },
        "textures": [
            ("ridack_bossorc5.dds", "ridack_bossorc5.png"),
            ("ridack_bossorc4.dds", "ridack_bossorc4.png"),
            ("ridack_bossorc.dds", "ridack_bossorc.png"),
            ("ridack_bossorc2.dds", "ridack_bossorc2.png"),
            ("ridack_bossorc3.dds", "ridack_bossorc3.png"),
            ("ridack_effect.dds", "ridack_orc_effect.png"),
        ],
    },
}

NPC_ASSETS = {
    "npc_pewi_kowal": {
        "folder": os.path.join(NPC_ROOT, "npc2", "npc_pewi_kowal"),
        "model": "npc_pewi_kowal.gr2",
        "anims": {
            "wait": "wait.gr2",
            "wait1": "wait1.gr2",
            "walk": "walk.gr2",
        },
        "textures": ["kowal.dds"],
    },
    "plechi_lady_npc12": {
        "folder": os.path.join(NPC_ROOT, "npc", "plechi_lady_npc12"),
        "model": "plechi_lady_npc12.gr2",
        "anims": {
            "wait": "stay00.gr2",
            "wait1": "stay01.gr2",
        },
        "textures": ["plechito_tex.dds"],
    },
    "plechi_lord_shinsoo": {
        "folder": os.path.join(NPC_ROOT, "npc", "plechi_lord_shinsoo"),
        "model": "plechi_lord_shinsoo.gr2",
        "anims": {
            "wait": "stay00.gr2",
            "wait1": "stay01.gr2",
            "walk": "walk.gr2",
        },
        "textures": [("plechito_tex.dds", "lord_shinsoo_tex.png")],
    },
    "plechi_lord_jinno": {
        "folder": os.path.join(NPC_ROOT, "npc", "plechi_lord_jinno"),
        "model": "plechi_lord_jinno.gr2",
        "anims": {
            "wait": "stay00.gr2",
            "wait1": "stay01.gr2",
            "walk": "walk.gr2",
        },
        "textures": [
            ("plechito_tex_weapon.dds", "lord_jinno_weapon.png"),
            ("plechito_tex_body.dds", "lord_jinno_body.png"),
            ("plechito_tex_sash.dds", "lord_jinno_sash.png"),
        ],
    },
    "plechi_tribe_npc1": {
        "folder": os.path.join(NPC_ROOT, "npc", "plechi_tribe_npc1"),
        "model": "plechi_tribe_npc1.gr2",
        "anims": {
            "wait": "stay00.gr2",
            "wait1": "stay01.gr2",
            "walk": "walk.gr2",
        },
        "textures": [
            ("plechito_tex00.dds", "tribe_npc_body.png"),
            ("plechito_tex01.dds", "tribe_npc_staff.png"),
        ],
    },
    "pewi_zielarz": {
        "folder": os.path.join(NPC_ROOT, "npc2", "pewi_zielarz"),
        "model": "pewi_zielarz.gr2",
        "anims": {
            "wait": "wait.gr2",
            "wait1": "wait1.gr2",
        },
        "textures": ["zielarz.dds"],
    },
    "plechi_old_alchemist": {
        "folder": os.path.join(NPC_ROOT, "npc", "plechi_old_alchemist"),
        "model": "plechi_old_alchemist.gr2",
        "anims": {
            "wait": "stay00.gr2",
            "wait1": "stay01.gr2",
        },
        "textures": [
            ("plechito_tex00.dds", "alchemist_body.png"),
            ("plechito_tex01.dds", "alchemist_deco.png"),
        ],
    },
    "pewi_info_manager": {
        "folder": os.path.join(NPC_ROOT, "npc2", "pewi_info_manager"),
        "model": "pewi_info_manager.gr2",
        "anims": {
            "wait": "wait.gr2",
            "wait1": "wait1.gr2",
        },
        "textures": ["info_manager.dds"],
    },
    "pewi_human_aide": {
        "folder": os.path.join(NPC_ROOT, "npc2", "pewi_human_aide"),
        "model": "pewi_human_aide.gr2",
        "anims": {
            "wait": "wait.gr2",
            "wait1": "wait1.gr2",
        },
        "textures": [
            "human_aide_body.dds",
            "human_aide_face.dds",
            "human_aide_hair.dds",
        ],
    },
    "plechi_ladynpc_3": {
        "folder": os.path.join(NPC_ROOT, "npc", "plechi_ladynpc_3"),
        "model": "plechi_ladynpc_3.gr2",
        "anims": {
            "wait": "stay00.gr2",
            "wait1": "stay01.gr2",
        },
        "textures": [
            ("plechito_tex.dds", "ladynpc_3_tex.png"),
        ],
    },
    "plechi_blade_master": {
        "folder": os.path.join(NPC_ROOT, "npc", "plechi_blade_master"),
        "model": "plechi_blade_master.gr2",
        "anims": {
            "wait": "wait01.gr2",
            "wait1": "wait02.gr2",
            "walk": "walk.gr2",
        },
        "textures": [
            ("blade_master_body.tga", "blade_master_body.png"),
            ("blade_master_head.tga", "blade_master_head.png"),
            ("blade_master_wp.tga", "blade_master_wp.png"),
        ],
    },
    "plechi_guardnpc_2": {
        "folder": os.path.join(NPC_ROOT, "npc", "plechi_guardnpc_2"),
        "model": "plechi_guardnpc_2.gr2",
        "anims": {
            "wait": "stay00.gr2",
            "wait1": "stay01.gr2",
        },
        "textures": [
            ("plechito_tex.dds", "guardnpc_2_tex.png"),
        ],
    },
    "plechi_guardnpc_3": {
        "folder": os.path.join(NPC_ROOT, "npc", "plechi_guardnpc_3"),
        "model": "plechi_guardnpc_3.gr2",
        "anims": {
            "wait": "stay00.gr2",
            "wait1": "stay01.gr2",
        },
        "textures": [
            ("plechito_tex.dds", "guardnpc_3_tex.png"),
        ],
    },
    "plechi_old_warrior1": {
        "folder": os.path.join(NPC_ROOT, "npc", "plechi_old_warrior1"),
        "model": "plechi_old_warrior1.gr2",
        "anims": {
            "wait": "stay00.gr2",
            "wait1": "stay01.gr2",
        },
        "textures": [
            ("plechito_tex.dds", "old_warrior1_tex.png"),
        ],
    },
    "pewi_guan": {
        "folder": os.path.join(NPC_ROOT, "npc", "pewi_guan"),
        "model": "pewi_guan.gr2",
        "anims": {
            "wait": "wait.gr2",
            "wait1": "wait1.gr2",
        },
        "textures": [
            ("pewi_guan.dds", "pewi_guan.png"),
        ],
    },
    "pewi_tyr": {
        "folder": os.path.join(NPC_ROOT, "npc", "pewi_tyr"),
        "model": "pewi_tyr.gr2",
        "anims": {
            "wait": "wait.gr2",
            "wait1": "wait1.gr2",
        },
        "textures": [
            ("pewi_tyr.dds", "pewi_tyr.png"),
        ],
    },
    "pewi_mount_horse": {
        "folder": os.path.join(NPC_ROOT, "npc2", "pewi_mount_horse"),
        "model": "pewi_mount_horse.gr2",
        "anims": {
            "wait": "00.gr2",
            "wait1": "00_1.gr2",
            "walk": "02.gr2",
        },
        "textures": [
            ("pewi_mount_horse_col1.dds", "pewi_mount_horse_col1.png"),
            ("pewi_mount_horse_col2.dds", "pewi_mount_horse_col2.png"),
            ("pewi_mount_horse_col3.dds", "pewi_mount_horse_col3.png"),
        ],
    },
}


def run_noesis(src: str, dst: str, anim: str = None) -> bool:
    env = os.environ.copy()
    env.pop("NOESIS_ANIM_PATH", None)
    if anim and os.path.exists(anim):
        env["NOESIS_ANIM_PATH"] = anim
    if os.path.exists(dst):
        try:
            os.remove(dst)
        except Exception:
            pass
    subprocess.run(
        [NOESIS_EXE, "?cmode", src, dst],
        cwd=NOESIS_DIR,
        env=env,
        capture_output=True,
        timeout=35,
    )
    return os.path.exists(dst) and os.path.getsize(dst) > 0


def build_merged_glb(folder: str, model_file: str, anim_map: dict, dst_glb: str) -> dict:
    src_model = os.path.join(folder, model_file)
    tmp_dir = tempfile.mkdtemp(prefix="aeryndor_gr2_")
    try:
        anim_items = list(anim_map.items())
        first_name, first_file = anim_items[0]
        first_gltf = os.path.join(tmp_dir, f"{first_name}.gltf")
        first_anim_path = first_file if os.path.isabs(first_file) else os.path.join(folder, first_file)
        ok = run_noesis(src_model, first_gltf, first_anim_path)
        if not ok:
            raise RuntimeError(f"Failed to export base glTF for {src_model}")

        with open(first_gltf, "r", encoding="utf-8") as f:
            base_g = json.load(f)
        bin_uri = base_g["buffers"][0]["uri"]
        with open(os.path.join(tmp_dir, bin_uri), "rb") as fb:
            bin_data = bytearray(fb.read())

        if base_g.get("animations"):
            base_g["animations"][0]["name"] = first_name
        else:
            base_g["animations"] = []

        for clip_name, clip_file in anim_items[1:]:
            anim_path = clip_file if os.path.isabs(clip_file) else os.path.join(folder, clip_file)
            if not os.path.exists(anim_path):
                continue
            clip_gltf = os.path.join(tmp_dir, f"{clip_name}.gltf")
            if not run_noesis(src_model, clip_gltf, anim_path):
                continue
            with open(clip_gltf, "r", encoding="utf-8") as f:
                cg = json.load(f)
            if not cg.get("animations"):
                continue
            cbin_uri = cg["buffers"][0]["uri"]
            with open(os.path.join(tmp_dir, cbin_uri), "rb") as fb:
                cb = fb.read()

            anim = cg["animations"][0]
            anim["name"] = clip_name
            used_accs = sorted(
                {s["input"] for s in anim["samplers"]} | {s["output"] for s in anim["samplers"]}
            )
            used_bvs = sorted({cg["accessors"][a]["bufferView"] for a in used_accs})
            bv_map = {}
            for bv_i in used_bvs:
                obv = cg["bufferViews"][bv_i]
                while len(bin_data) % 4 != 0:
                    bin_data.append(0)
                chunk = cb[obv["byteOffset"] : obv["byteOffset"] + obv["byteLength"]]
                bv_map[bv_i] = len(base_g["bufferViews"])
                base_g["bufferViews"].append(
                    {"buffer": 0, "byteOffset": len(bin_data), "byteLength": len(chunk)}
                )
                bin_data.extend(chunk)

            acc_map = {}
            for a_i in used_accs:
                nacc = dict(cg["accessors"][a_i])
                nacc["bufferView"] = bv_map[nacc["bufferView"]]
                acc_map[a_i] = len(base_g["accessors"])
                base_g["accessors"].append(nacc)

            for s in anim["samplers"]:
                s["input"] = acc_map[s["input"]]
                s["output"] = acc_map[s["output"]]
            base_g["animations"].append(anim)

        # Fix Plechito Main_Root reflection matrix & Bip01 Pelvis bind translation offset
        nodes_list = base_g.get("nodes", [])
        main_root_indices = set()
        for idx, nd in enumerate(nodes_list):
            clean_nm = re.sub(r"^bone\d+_", "", (nd.get("name") or ""), flags=re.IGNORECASE).lower()
            if clean_nm == "main_root":
                rot = nd.get("rotation")
                if rot and sum(x * x for x in rot) < 0.9:
                    nd["scale"] = [-1.0, 1.0, 1.0]
                    nd["rotation"] = [0.70710678, 0.0, 0.0, 0.70710678]
                    main_root_indices.add(idx)

        if main_root_indices:
            bip01_idx = None
            pelvis_idx = None
            for idx, nd in enumerate(nodes_list):
                clean_nm = re.sub(r"^bone\d+_", "", (nd.get("name") or ""), flags=re.IGNORECASE)
                if clean_nm == "Bip01":
                    bip01_idx = idx
                elif clean_nm in ("Bip01 Pelvis", "Bip01_Pelvis"):
                    pelvis_idx = idx
            if bip01_idx is not None and pelvis_idx is not None:
                bt = nodes_list[bip01_idx].get("translation", [0.0, 0.0, 0.0])
                pt = nodes_list[pelvis_idx].get("translation", [0.0, 0.0, 0.0])
                if sum(abs(x) for x in bt) < 1.0 and abs(pt[1]) > 50.0:
                    nodes_list[bip01_idx]["translation"] = list(pt)
                    nodes_list[pelvis_idx]["translation"] = [0.0, 0.0, 0.0]

            for anim in base_g.get("animations", []):
                anim["channels"] = [
                    ch
                    for ch in anim.get("channels", [])
                    if ch["target"]["node"] not in main_root_indices
                ]

        # Strip embedded Ridack 3D watermark logo primitive (5866 verts / 5228 tris = 15684 indices)
        for m in base_g.get("meshes", []):
            prims = m.get("primitives", [])
            if len(prims) > 1:
                filtered_prims = []
                for p in prims:
                    pos_idx = p.get("attributes", {}).get("POSITION")
                    ind_idx = p.get("indices")
                    v_cnt = base_g["accessors"][pos_idx]["count"] if pos_idx is not None else 0
                    i_cnt = base_g["accessors"][ind_idx]["count"] if ind_idx is not None else 0
                    if v_cnt == 5866 and i_cnt == 15684:
                        continue
                    filtered_prims.append(p)
                if filtered_prims:
                    m["primitives"] = filtered_prims

        # Compute overall bounding box across all mesh primitives
        min_pt = [1e9, 1e9, 1e9]
        max_pt = [-1e9, -1e9, -1e9]
        for m in base_g.get("meshes", []):
            for p in m.get("primitives", []):
                pos_idx = p["attributes"].get("POSITION")
                if pos_idx is not None:
                    acc = base_g["accessors"][pos_idx]
                    for k in range(3):
                        min_pt[k] = min(min_pt[k], acc["min"][k])
                        max_pt[k] = max(max_pt[k], acc["max"][k])

        while len(bin_data) % 4 != 0:
            bin_data.append(0)
        base_g["buffers"] = [{"byteLength": len(bin_data)}]
        json_bytes = json.dumps(base_g, separators=(",", ":")).encode("utf-8")
        while len(json_bytes) % 4 != 0:
            json_bytes += b" "

        total_len = 12 + 8 + len(json_bytes) + 8 + len(bin_data)
        with open(dst_glb, "wb") as f:
            f.write(struct.pack("<III", 0x46546C67, 2, total_len))
            f.write(struct.pack("<II", len(json_bytes), 0x4E4F534A))
            f.write(json_bytes)
            f.write(struct.pack("<II", len(bin_data), 0x004E4942))
            f.write(bin_data)

        return {
            "meshes": len(base_g.get("meshes", [])),
            "animations": [a["name"] for a in base_g.get("animations", [])],
            "bbox_min": [round(x, 2) for x in min_pt],
            "bbox_max": [round(x, 2) for x in max_pt],
            "height_cm": round(max_pt[2] - min_pt[2], 2),
        }
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def convert_group(group_dict: dict, out_subdir: str) -> dict:
    os.makedirs(out_subdir, exist_ok=True)
    result = {}
    for asset_id, cfg in group_dict.items():
        folder = cfg["folder"]
        dst_glb = os.path.join(out_subdir, f"{asset_id}.glb")
        info = build_merged_glb(folder, cfg["model"], cfg["anims"], dst_glb)
        tex_out = []
        for tex_entry in cfg["textures"]:
            if isinstance(tex_entry, (tuple, list)):
                tex_file, base_name = tex_entry
            else:
                tex_file = tex_entry
                base_name = os.path.splitext(tex_file)[0] + ".png"
            src_tex = os.path.join(folder, tex_file)
            dst_png = os.path.join(out_subdir, base_name)
            if os.path.exists(src_tex):
                run_noesis(src_tex, dst_png)
                if os.path.exists(dst_png):
                    tex_out.append(base_name)
        info["textures"] = tex_out
        result[asset_id] = info
        print(
            f"[OK] {asset_id:22s} | height={info['height_cm']:6.1f}cm | meshes={info['meshes']} | anims={info['animations']} | tex={len(tex_out)}"
        )
    return result


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    print("=== Converting Map 1 & Map 2 Monsters ===")
    mon_res = convert_group(MONSTER_ASSETS, OUT_MON_DIR)
    print("\n=== Converting Village NPCs ===")
    npc_res = convert_group(NPC_ASSETS, OUT_NPC_DIR)
    manifest = {"monsters": mon_res, "npcs": npc_res}
    with open(os.path.join(OUT_DIR, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    print("\nSaved manifest to public/assets/models/manifest.json")


if __name__ == "__main__":
    main()
