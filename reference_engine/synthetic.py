"""Synthetic data generators for the reference engine.

Produces legal, deterministic synthetic output from legal synthetic input.
No real Minecraft data, no private algorithms, no production reference profiles.
"""
from __future__ import annotations

import hashlib
import json
import os
import uuid
from typing import Dict, List


def synthetic_request_id() -> str:
    """Generates a deterministic request ID for testing."""
    return str(uuid.UUID(int=42))


def synthetic_world_hash() -> str:
    """Returns a deterministic SHA-256 hash for a synthetic world."""
    return hashlib.sha256(b"synthetic-world-v1").hexdigest()


def synthetic_chunk_descriptors(count: int = 4) -> Dict[str, dict]:
    """Generates deterministic chunk descriptors for a small synthetic world."""
    chunks = {}
    idx = 0
    for cx in range(2):
        for cz in range(2):
            key = f"{cx}:0:{cz}"
            name = f"Chunk_xp{cx:03d}_yp000_zp{cz:03d}"
            chunks[key] = {
                "name": name,
                "file": f"chunks/{name}.blend",
                "block_count": 256 * (idx + 1),
                "static_object_count": 1,
                "rig_root_count": 0,
                "bounds_minecraft": [
                    cx * 16, 0, cz * 16,
                    cx * 16 + 15, 15, cz * 16 + 15,
                ],
            }
            idx += 1
            if idx >= count:
                return chunks
    return chunks


def synthetic_manifest(
    request_id: str = "",
    engine_version: str = "2026.09.0-ref",
    chunk_count: int = 4,
) -> dict:
    """Generates a deterministic signed manifest for testing."""
    chunks = synthetic_chunk_descriptors(chunk_count)
    checksums = {}
    for chunk_data in chunks.values():
        filename = chunk_data["file"]
        checksums[filename] = hashlib.sha256(
            filename.encode("utf-8")
        ).hexdigest()
    checksums["strata-world-manifest.json"] = "will-be-computed-after-write"

    return {
        "schema_version": 1,
        "contract_version": "1.0",
        "engine_version": engine_version,
        "request_id": request_id or synthetic_request_id(),
        "input_hashes": {"world": synthetic_world_hash()},
        "chunk_size": 16,
        "coordinate_mapping": "minecraft_xyz_to_blender_xzy",
        "prototype_library": "Strata_PrototypeLibrary.blend",
        "missing_asset_policy": "generate",
        "chunks": chunks,
        "output_checksums": checksums,
        "signature": "ref-engine-synthetic-signature",
    }


def synthetic_diagnostics(
    chunk_count: int = 4,
    total_blocks: int = 2560,
) -> dict:
    """Generates deterministic diagnostics for testing."""
    return {
        "unmapped_ids": ["minecraft:custom_block_999"],
        "ignored_non_block_assets": ["minecraft:zombie", "minecraft:skeleton"],
        "generated_fallback_assets": ["minecraft:custom_block_999"],
        "chunk_count": chunk_count,
        "total_blocks": total_blocks,
        "visible_blocks": int(total_blocks * 0.6),
        "warnings": ["1 block ID not in known registry"],
        "failure_reasons": [],
    }


def write_synthetic_output(output_dir: str, request_id: str = "") -> str:
    """Writes a complete synthetic build result to disk.

    Returns the manifest path.
    """
    os.makedirs(output_dir, exist_ok=True)
    chunks_dir = os.path.join(output_dir, "chunks")
    os.makedirs(chunks_dir, exist_ok=True)

    manifest_data = synthetic_manifest(request_id=request_id)

    # Write placeholder chunk files
    for chunk_data in manifest_data["chunks"].values():
        chunk_path = os.path.join(output_dir, chunk_data["file"])
        with open(chunk_path, "wb") as f:
            f.write(b"SYNTHETIC-BLEND-" + chunk_data["name"].encode())

    # Recompute checksums for actual written files
    checksums = {}
    for chunk_data in manifest_data["chunks"].values():
        chunk_path = os.path.join(output_dir, chunk_data["file"])
        h = hashlib.sha256()
        with open(chunk_path, "rb") as f:
            h.update(f.read())
        checksums[chunk_data["file"]] = h.hexdigest()

    # Write manifest
    manifest_path = os.path.join(output_dir, "strata-world-manifest.json")
    manifest_data["output_checksums"] = checksums
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f, indent=2)

    # Add manifest's own checksum
    h = hashlib.sha256()
    with open(manifest_path, "rb") as f:
        h.update(f.read())
    checksums["strata-world-manifest.json"] = h.hexdigest()

    return manifest_path
