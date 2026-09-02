# World Format Specification

MC Chunk Workflow expects a specific Blender scene structure.  
This document defines that structure so you can adapt the addon to your own world importer.

---

## Collection Hierarchy

```
Scene Collection
└── MC_Chunks_16x16x16          ← CHUNKS_PARENT_NAME
    ├── Chunk_xp000_yp000_zp000
    ├── Chunk_xp001_yp000_zp000
    ├── Chunk_xm001_yp000_zp001
    └── …
```

### Chunk collection naming

Format: `Chunk_x{sign}{X:03d}_y{sign}{Y:03d}_z{sign}{Z:03d}`

| Field | Meaning |
|---|---|
| `sign` | `p` for positive / zero, `m` for negative |
| `X`, `Y`, `Z` | Chunk coordinate (block coord ÷ 16, floored) |

Examples:

| Collection name | Chunk coords |
|---|---|
| `Chunk_xp001_yp000_zp002` | (+1, 0, +2) |
| `Chunk_xm003_yp000_zp001` | (−3, 0, +1) |

### Required chunk custom properties

Each `Chunk_*` collection must carry:

| Property | Type | Description |
|---|---|---|
| `mc_chunk_x` | int | Chunk X coordinate |
| `mc_chunk_y` | int | Chunk Y coordinate (vertical) |
| `mc_chunk_z` | int | Chunk Z coordinate |
| `mc_object_count` | int | *(optional)* cached object count for fast stats |

---

## Block Objects

Each block object inside a chunk collection must have:

| Property | Type | Description |
|---|---|---|
| `block_id` | str | Minecraft block ID e.g. `"stone"`, `"oak_log"` |
| `mc_x` | int | Minecraft world X coordinate |
| `mc_y` | int | Minecraft world Y coordinate (height) |
| `mc_z` | int | Minecraft world Z coordinate |

---

## Hero Rig

The addon looks for an armature named `A1_Steve_Rig` (configurable via  
`HERO_RIG_NAME` in `chunk_utils.py`).

The rig's world-space translation is used to determine which chunk column  
the character is standing in, enabling **Performance Mode** and **Rig Chunk**.

---

## Coordinate Mapping

One Minecraft block = one Blender metre.

Minecraft → Blender axis mapping used by the default importer:

| Minecraft | Blender |
|---|---|
| X | X |
| Y (height) | Z |
| Z | Y |

Chunk coordinates are derived from Blender-space locations:
```python
chunk_x = floor(obj.location.x / 16)
chunk_z = floor(obj.location.y / 16)  # Blender Y = Minecraft Z
```
