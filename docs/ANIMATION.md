# Strata Block-Only Interactive Rigs & Animation

## 1. Supported Interactive Block Rigs

Strata builds unique, keyframeable armatures for interactive block entities:

1. **Chests**: Single chest, double chest, trapped chest, ender chest.
2. **Doors**: All wood and iron doors (consumes upper and lower half as one rig).
3. **Trapdoors**: All wood and iron trapdoors.
4. **Fence Gates**: All wood fence gates.
5. **Barrels & Shulker Boxes**: Opening lid motion.
6. **Pistons & Beds**: Piston extension and bed blocks.

---

## 2. Rig Root Identity & `strata_open` Driver Property

Each rig root object is named:
```text
R__<sanitized_block_id>__<mc_x>_<mc_y>_<mc_z>
```

It carries a float custom property `strata_open` in range `[0.0, 1.0]`:
- `0.0` = closed pose
- `1.0` = open pose

A scripted expression driver maps `strata_open` directly to bone rotations.

---

## 3. Operators & MCP Controls

- **Open Block Rig**: `strata.open_block_rig` / MCP `set_interactive_block_state(obj, 1.0)`
- **Close Block Rig**: `strata.close_block_rig` / MCP `set_interactive_block_state(obj, 0.0)`
- **Keyframe Open State**: `strata.insert_open_keyframe` / MCP `keyframe_interactive_block_state(obj, frame)`
