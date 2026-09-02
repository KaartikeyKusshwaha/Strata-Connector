# Strata 3D Chunks & LRU Paging Architecture

## 1. Overview & Naming Convention

Strata implements A1-compatible 3-dimensional `16 x 16 x 16` chunking matching `A1.blend`.

Chunk collections follow the A1 naming convention:
```text
Chunk_x<p|m><cx>_y<p|m><cy>_z<p|m><cz>
```
- Positive coordinates use `p` (e.g. `xp001`).
- Negative coordinates use `m` (e.g. `ym002`).
- Each magnitude is zero-padded to at least **3 digits**.

### Examples:
- `(0, 0, 0)` $\rightarrow$ `Chunk_xp000_yp000_zp000`
- `(1, -2, 3)` $\rightarrow$ `Chunk_xp001_ym002_zp003`
- `(-15, 0, 120)` $\rightarrow$ `Chunk_xm015_yp000_zp120`

---

## 2. Directory Layout & World Manifest

Imports write an external scene directory structure rather than a single monolithic file:

```text
<output-directory>/
  World.blend
  strata-world-manifest.json
  Strata_PrototypeLibrary.blend
  chunks/
    Chunk_xp000_yp000_zp000.blend
    Chunk_xp000_yp000_zp001.blend
    ...
```

`strata-world-manifest.json` tracks chunk boundaries and files:
```json
{
  "schema_version": 1,
  "chunk_size": 16,
  "coordinate_mapping": "minecraft_xyz_to_blender_xzy",
  "prototype_library": "Strata_PrototypeLibrary.blend",
  "missing_asset_policy": "generate",
  "chunks": {
    "0:0:0": {
      "name": "Chunk_xp000_yp000_zp000",
      "file": "chunks/Chunk_xp000_yp000_zp000.blend",
      "block_count": 256,
      "static_object_count": 256,
      "rig_root_count": 0,
      "bounds_minecraft": [0, 0, 0, 15, 15, 15]
    }
  }
}
```

---

## 3. LRU Edit-Time Streaming

The master file maintains a Least Recently Used set of loaded chunk collections:
- Default Working Set: `radius_x = 1, radius_y = 1, radius_z = 1` ($\rightarrow$ 27 chunks max).
- Moving the active camera or selection unloads oldest unpinned chunks outside the working radius and purges local orphaned datablocks.
- Pinned chunks (`strata_pinned = True`) are excluded from LRU eviction.
