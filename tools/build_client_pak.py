# -*- coding: utf-8 -*-
"""
Builds the encrypted standalone client archive 'aeryndor_data.pak' (AERYPAK2 format)
containing 100% of the Three.js engine, shaders, UI, 3D objects, terrain, textures, and icons.
"""
import gzip
import hashlib
import json
import os
import struct
import time

SECRET = b"Aeryndor_Standalone_3D_Engine_Vault_2026_v437!#SecretKey"
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PUBLIC_DIR = os.path.join(ROOT_DIR, "public")
OUT_PAK = os.path.join(ROOT_DIR, "aeryndor_data.pak")


def make_key_table(salt: bytes) -> bytes:
    out = bytearray()
    for i in range(128):
        out.extend(hashlib.sha256(SECRET + salt + struct.pack("<I", i)).digest())
    return bytes(out)


def crypt_fast(data: bytes, kt_bytes: bytes, kt_int: int) -> bytes:
    n = len(data)
    out = bytearray(n)
    full_blocks = n // 4096
    for b in range(full_blocks):
        off = b * 4096
        chunk_int = int.from_bytes(data[off : off + 4096], "little")
        mask_byte = b & 0xFF
        if mask_byte:
            mask_int = int.from_bytes(bytes([mask_byte]) * 4096, "little")
            x = chunk_int ^ kt_int ^ mask_int
        else:
            x = chunk_int ^ kt_int
        out[off : off + 4096] = x.to_bytes(4096, "little")
    rem = n % 4096
    if rem:
        off = full_blocks * 4096
        mask_byte = full_blocks & 0xFF
        for j in range(rem):
            out[off + j] = data[off + j] ^ kt_bytes[j] ^ mask_byte
    return bytes(out)


def build_data_pak():
    t0 = time.time()
    master_salt = hashlib.sha256(SECRET + b"AERYPAK2_MASTER_SALT_2026").digest()[:16]
    kt_bytes = make_key_table(master_salt)
    kt_int = int.from_bytes(kt_bytes, "little")

    file_records = []
    for root_walk, _dirs, files in os.walk(PUBLIC_DIR):
        for fn in files:
            abs_p = os.path.join(root_walk, fn)
            rel_p = os.path.relpath(abs_p, PUBLIC_DIR).replace("\\", "/")
            file_records.append((rel_p, abs_p))

    file_records.sort(key=lambda x: x[0])

    COMPRESS_EXTS = (".js", ".css", ".html", ".json", ".bin", ".glb", ".gltf", ".svg", ".ico", ".txt")
    temp_body_path = OUT_PAK + ".body.tmp"
    index_entries = []
    curr_offset = 0

    with open(temp_body_path, "wb") as bf:
        for rel_p, abs_p in file_records:
            with open(abs_p, "rb") as rf:
                raw_bytes = rf.read()
            is_gz = 0
            if rel_p.lower().endswith(COMPRESS_EXTS) and len(raw_bytes) > 256:
                comp_bytes = gzip.compress(raw_bytes, compresslevel=6)
                if len(comp_bytes) < len(raw_bytes):
                    raw_bytes = comp_bytes
                    is_gz = 1
            enc_bytes = crypt_fast(raw_bytes, kt_bytes, kt_int)
            bf.write(enc_bytes)
            length = len(enc_bytes)
            index_entries.append({"p": rel_p, "o": curr_offset, "l": length, "z": is_gz})
            curr_offset += length

    # Serialize, GZip-compress, and encrypt the index table
    idx_json = json.dumps(index_entries, separators=(",", ":")).encode("utf-8")
    idx_gz = gzip.compress(idx_json, compresslevel=6)
    idx_enc = crypt_fast(idx_gz, kt_bytes, kt_int)

    # Write final AERYPAK2 container:
    # [8B "AERYPAK2"] [16B master_salt] [4B uint32 index_len] [idx_enc] [encrypted_files_body]
    with open(OUT_PAK, "wb") as out_f:
        out_f.write(b"AERYPAK2")
        out_f.write(master_salt)
        out_f.write(struct.pack("<I", len(idx_enc)))
        out_f.write(idx_enc)
        with open(temp_body_path, "rb") as bf:
            while True:
                chunk = bf.read(4 * 1024 * 1024)
                if not chunk:
                    break
                out_f.write(chunk)

    try:
        os.remove(temp_body_path)
    except OSError:
        pass

    dt = time.time() - t0
    size_mb = os.path.getsize(OUT_PAK) / (1024 * 1024)
    print(f"Built {OUT_PAK}: {len(index_entries)} files, {size_mb:.2f} MB in {dt:.2f}s")


if __name__ == "__main__":
    build_data_pak()
