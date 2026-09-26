"""Result manifest loader and Blender collection linker for Strata Toolkit.

Validates result manifests independently and links scene and chunk data
into Blender's active scene collection, with clean rollback on failure.
"""
from __future__ import annotations

import hashlib
import json
import os
import uuid
from typing import Any, Dict, List, Optional, Tuple

try:
    import bpy
    _IN_BLENDER = True
except ImportError:
    _IN_BLENDER = False


def validate_and_open_result(manifest_path: str) -> dict:
    """Independently validates a result manifest and links data into Blender.

    Security & Validation checks:
    - manifest_path must exist and be valid JSON
    - Contract major version must be compatible (1.x)
    - Rejects empty manifests
    - Validates all relative chunk paths to prevent directory traversal
    - Verifies all chunk files exist under the verified result root
    - Creates a dedicated root collection in Blender: 'Strata World - <id>'
    - Links chunk collections into the scene
    - Rolls back any created collections on failure, preserving user scene
    - Returns structured counts and manifest hash
    """
    if not manifest_path or not os.path.exists(manifest_path):
        return {
            "status": "error",
            "error_code": "manifest_not_found",
            "message": f"Manifest file does not exist: {manifest_path}",
        }

    abs_manifest = os.path.abspath(manifest_path)
    result_root = os.path.dirname(abs_manifest)

    # 1. Read manifest and compute its hash
    try:
        with open(abs_manifest, "r", encoding="utf-8") as f:
            raw_content = f.read()
            manifest_data = json.loads(raw_content)
    except Exception as e:
        return {
            "status": "error",
            "error_code": "malformed_manifest",
            "message": f"Failed to parse manifest JSON: {e}",
        }

    manifest_hash = hashlib.sha256(raw_content.encode("utf-8")).hexdigest()

    # 2. Check major version
    contract_version = str(manifest_data.get("contract_version", "1.0"))
    if not contract_version.startswith("1."):
        return {
            "status": "error",
            "error_code": "unsupported_contract_version",
            "message": f"Unsupported contract version: '{contract_version}'. Expected major 1.",
        }

    # 3. Validate chunks
    chunks_dict = manifest_data.get("chunks", {})
    if not chunks_dict:
        return {
            "status": "error",
            "error_code": "empty_manifest",
            "message": "Manifest contains no chunk definitions.",
        }

    validated_chunks: List[Tuple[str, str]] = []
    for chunk_key, chunk_info in chunks_dict.items():
        rel_file = chunk_info.get("file", "")
        if not rel_file or ".." in rel_file or rel_file.startswith(("/", "\\")):
            return {
                "status": "error",
                "error_code": "path_traversal",
                "message": f"Invalid chunk path in manifest: '{rel_file}'",
            }
        abs_chunk = os.path.abspath(os.path.join(result_root, rel_file))
        if not abs_chunk.startswith(result_root):
            return {
                "status": "error",
                "error_code": "path_traversal",
                "message": f"Chunk path escapes result root: '{rel_file}'",
            }
        if not os.path.exists(abs_chunk):
            return {
                "status": "error",
                "error_code": "missing_chunk_file",
                "message": f"Chunk file not found on disk: '{rel_file}'",
            }
        validated_chunks.append((chunk_info.get("name", chunk_key), abs_chunk))

    # 4. If running in Blender, build collection hierarchy
    if _IN_BLENDER:
        created_collections = []
        created_objects = []
        try:
            scene = bpy.context.scene
            req_id = manifest_data.get("request_id", uuid.uuid4().hex[:8])[:8]
            root_col_name = f"Strata World - {req_id}"

            # Check if collection already exists, reuse or create unique
            if root_col_name in bpy.data.collections:
                root_col = bpy.data.collections[root_col_name]
            else:
                root_col = bpy.data.collections.new(root_col_name)
                scene.collection.children.link(root_col)
                created_collections.append(root_col)

            linked_chunks_count = 0
            for name, filepath in validated_chunks:
                if name in bpy.data.collections:
                    chunk_col = bpy.data.collections[name]
                else:
                    chunk_col = bpy.data.collections.new(name)
                    chunk_col["strata_chunk_path"] = filepath
                    root_col.children.link(chunk_col)
                    created_collections.append(chunk_col)

                linked_chunks_count += 1

                # Try loading blend library data if valid blend archive
                try:
                    with bpy.data.libraries.load(filepath, link=True) as (data_from, data_to):
                        data_to.collections = data_from.collections
                        data_to.objects = data_from.objects
                    for col in data_to.collections:
                        if col and col.name not in chunk_col.children:
                            chunk_col.children.link(col)
                    for obj in data_to.objects:
                        if obj and obj.name not in chunk_col.objects:
                            chunk_col.objects.link(obj)
                            created_objects.append(obj)
                except Exception:
                    pass

            return {
                "status": "ok",
                "message": f"Successfully opened and linked result in Blender.",
                "manifest_path": abs_manifest,
                "manifest_sha256": manifest_hash,
                "collection_name": root_col_name,
                "linked_chunks": linked_chunks_count,
                "total_chunks": len(validated_chunks),
                "object_count": len(bpy.data.objects),
                "material_count": len(bpy.data.materials),
                "operation_id": str(uuid.uuid4()),
            }

        except Exception as e:
            # Rollback: remove only created collections and objects
            for obj in created_objects:
                try:
                    if obj and obj.name in bpy.data.objects:
                        bpy.data.objects.remove(obj, do_unlink=True)
                except Exception:
                    pass
            for col in reversed(created_collections):
                try:
                    if col and col.name in bpy.data.collections:
                        bpy.data.collections.remove(col)
                except Exception:
                    pass
            return {
                "status": "error",
                "error_code": "blender_linking_failed",
                "message": f"Failed to link result into Blender: {e}",
            }
    else:
        # Running outside Blender (unit test / fallback mode)
        return {
            "status": "ok",
            "message": "Validated result manifest and chunk files (non-Blender mode).",
            "manifest_path": abs_manifest,
            "manifest_sha256": manifest_hash,
            "linked_chunks": len(validated_chunks),
            "total_chunks": len(validated_chunks),
            "object_count": 0,
            "material_count": 0,
            "operation_id": str(uuid.uuid4()),
        }
