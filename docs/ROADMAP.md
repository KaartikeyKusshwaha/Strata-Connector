# Strata Roadmap

This document outlines the future development path for the Strata project. (Note: These are planned features, not currently implemented).

## v0.2 — World Format Expansion
- **Litematica schematic reader**: Upgrading the current stub to a full implementation for reading Litematica files.
- **Java 1.21 region format updates**: Supporting the latest Minecraft block states and NBT structures.
- **Biome-aware block resolution**: Dynamically assigning block variants (e.g., grass color) based on biome data.

## v0.3 — Export Targets
- **Unreal Engine render target**: Adding a USD export pipeline stage to seamlessly move worlds into Unreal Engine.
- **glTF export**: Support for exporting chunks to web viewers and lightweight applications.
- **Per-chunk LOD system**: Generating Level of Detail meshes for distant chunks to optimize massive renders.

## v0.4 — Animation
- **Timeline-driven chunk activation**: Animating the appearance of chunks over time (e.g., building a world block-by-block).
- **Water/lava simulation pipeline stage**: Automatically converting static fluid blocks into animated, flowing meshes or fluid sims.
- **Mob animation rigs**: Auto-importing and rigging standard Minecraft mobs with base animations.

## v0.5 — SDK Maturity
- **PyPI distribution**: Publishing the SDK (`pip install strata-mc`) for easier inclusion in other Python projects.
- **Plugin marketplace / registry**: A centralized list of community-built World Readers and Geometry Backends.
- **Web-based block map editor**: A visual tool for editing `block_map.json` without writing raw JSON.
- **Config file**: Centralizing pipeline settings in a `strata.toml` file.

## v1.0 — Beyond Minecraft
- **Generic voxel world reader interface**: Abstracting the reader to support any voxel format.
- **Support other game world formats**: Teardown, Minetest, etc.
- **Studio-grade batch pipeline**: Headless farm rendering and massive distributed chunk processing.
- **Documentation site**: Moving from Markdown files to a fully hosted, searchable Sphinx or MkDocs site.

---
Contributions welcome — see `CONTRIBUTING.md`
