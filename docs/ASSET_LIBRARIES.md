# Strata Asset Library Authority & Texture Precedence

## 1. Source Precedence Rules

Strata enforces strict authority order for geometry and textures:

1. **User Library Authority**: A user-supplied `.blend` library is inspected read-only and wins for every asset it declares. Source library files are **never saved over**.
2. **User Texture Packs**: `user_texture_packs` have highest texture priority.
3. **Selected Project Packs**: `selected_texture_packs` have second texture priority.
4. **Vanilla Minecraft JAR**: `minecraft_jar` supplies fallback textures and Java blockstate/model JSON data.

---

## 2. Missing-Asset Policies

Configured via `Pipeline.set_missing_asset_policy(policy)`:
- `"generate"` (default): missing assets are resolved via the own-library Java model parser.
- `"error"`: reports missing assets in `unmapped_block_ids` and stops build before building affected chunks.

---

## 3. Non-Block Asset Filtering

Character, mob, player, and item rigs (e.g. Steve, Alex, zombie, armor stand) present in a user library are ignored during world generation and logged in `ignored_non_block_assets` diagnostics so world chunks contain block assets only.
