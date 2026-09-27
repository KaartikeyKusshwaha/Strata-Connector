"""Deterministic, Blender-side fallback block library generation.

The private Engine may replace this library with the user's custom asset
library. This fallback is intentionally small and legal: it creates simple
colored cubes with provenance metadata and never reads Minecraft JARs or
bundled third-party textures.
"""
from __future__ import annotations

import json
import os
import re
import uuid
from typing import Any, Iterable


DEFAULT_BLOCKS = {
    "minecraft:stone": ("Stone", (0.38, 0.40, 0.43, 1.0), 0.9),
    "minecraft:dirt": ("Dirt", (0.30, 0.16, 0.07, 1.0), 1.0),
    "minecraft:grass_block": ("Grass", (0.20, 0.48, 0.12, 1.0), 0.95),
    "minecraft:oak_planks": ("Oak Planks", (0.62, 0.38, 0.14, 1.0), 0.85),
    "minecraft:glass": ("Glass", (0.55, 0.80, 0.92, 1.0), 0.2),
    "minecraft:water": ("Water", (0.06, 0.22, 0.80, 1.0), 0.15),
}


def _safe_name(block_id: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", block_id).strip("_") or "block"


def _cube_mesh(bpy: Any, name: str) -> Any:
    mesh = bpy.data.meshes.get(name) or bpy.data.meshes.new(name)
    if not mesh.vertices:
        vertices = [
            (-0.5, -0.5, -0.5), (0.5, -0.5, -0.5),
            (0.5, 0.5, -0.5), (-0.5, 0.5, -0.5),
            (-0.5, -0.5, 0.5), (0.5, -0.5, 0.5),
            (0.5, 0.5, 0.5), (-0.5, 0.5, 0.5),
        ]
        faces = [
            (0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1),
            (1, 5, 6, 2), (2, 6, 7, 3), (4, 0, 3, 7),
        ]
        mesh.from_pydata(vertices, [], faces)
        mesh.update()
    return mesh


def generate_barebones_library(
    output_path: str,
    block_ids: Iterable[str] | None = None,
    **_kwargs: Any,
) -> dict:
    """Generate a small `.blend` library and a JSON provenance sidecar."""
    try:
        import bpy
    except ImportError:
        return {
            "status": "error",
            "error_code": "blender_required",
            "message": "Barebones library generation must run inside Blender.",
        }

    if not output_path:
        return {
            "status": "error",
            "error_code": "output_path_required",
            "message": "Provide an absolute .blend output path.",
        }
    output_path = os.path.abspath(output_path)
    if not output_path.lower().endswith(".blend"):
        return {
            "status": "error",
            "error_code": "invalid_output_path",
            "message": "Barebones library output must use a .blend extension.",
        }
    try:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        selected = list(block_ids or DEFAULT_BLOCKS.keys())
        unknown = [block_id for block_id in selected if block_id not in DEFAULT_BLOCKS]
        if unknown:
            return {
                "status": "error",
                "error_code": "unsupported_block_ids",
                "message": f"No fallback profile exists for: {', '.join(unknown)}",
            }

        library = bpy.data.collections.get("Strata_PrototypeLibrary")
        if library is None:
            library = bpy.data.collections.new("Strata_PrototypeLibrary")
            bpy.context.scene.collection.children.link(library)
        library["strata_generated"] = True
        library["strata_generator_version"] = "barebones-v1"
        library["strata_provenance"] = "procedural fallback; no Minecraft JAR or third-party texture data"

        generated_objects = []
        for block_id in selected:
            label, color, roughness = DEFAULT_BLOCKS[block_id]
            safe = _safe_name(block_id)
            mesh = _cube_mesh(bpy, f"StrataLibMesh_{safe}")
            obj = bpy.data.objects.get(f"StrataLib_{safe}")
            if obj is None:
                obj = bpy.data.objects.new(f"StrataLib_{safe}", mesh)
                library.objects.link(obj)
            elif obj.name not in library.objects:
                library.objects.link(obj)
            obj.data = mesh
            obj["strata_block_id"] = block_id
            obj["strata_display_name"] = label
            obj["strata_generated"] = True

            material = bpy.data.materials.get(f"StrataMat_{safe}")
            if material is None:
                material = bpy.data.materials.new(f"StrataMat_{safe}")
            material.use_nodes = True
            bsdf = material.node_tree.nodes.get("Principled BSDF")
            if bsdf is not None:
                bsdf.inputs["Base Color"].default_value = color
                bsdf.inputs["Roughness"].default_value = roughness
                if block_id == "minecraft:water":
                    bsdf.inputs["Metallic"].default_value = 0.0
            if len(obj.data.materials) == 0:
                obj.data.materials.append(material)
            else:
                obj.data.materials[0] = material
            generated_objects.append(obj)

        bpy.data.libraries.write(
            output_path,
            set([library]),
            path_remap="RELATIVE",
            fake_user=True,
            compress=True,
        )
        provenance_path = output_path[:-6] + ".provenance.json"
        provenance = {
            "schema_version": 1,
            "generator": "strata-barebones-v1",
            "source": "procedural fallback",
            "blender_version": list(bpy.app.version),
            "library_name": library.name,
            "block_ids": selected,
            "object_names": [obj.name for obj in generated_objects],
            "output_file": output_path,
            "operation_id": str(uuid.uuid4()),
        }
        with open(provenance_path, "w", encoding="utf-8") as f:
            json.dump(provenance, f, indent=2)
        return {
            "status": "ok",
            "message": "Generated procedural barebones block library.",
            "library_path": output_path,
            "provenance_path": provenance_path,
            "library_name": library.name,
            "object_count": len(generated_objects),
            "block_ids": selected,
            "operation_id": provenance["operation_id"],
        }
    except Exception as exc:
        return {
            "status": "error",
            "error_code": "library_generation_failed",
            "message": f"Could not generate barebones library: {exc}",
        }
