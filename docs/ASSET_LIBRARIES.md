# Strata asset libraries

## Public Connector behavior

The Connector treats a user-supplied `.blend` library as read-only. Use
`strata_inspect_library` to inspect the selected path before a managed build;
the source file is never saved over by the Connector.

If no custom library is available, use
`strata_generate_barebones_library`. The Blender add-on creates a small legal
procedural library named `Strata_PrototypeLibrary`, with simple colored cube
prototypes for common block IDs and a `.provenance.json` sidecar. This fallback
contains no Minecraft JAR contents or third-party textures.

## Production asset authority

Texture/model precedence and Java blockstate parsing belong to the private
Engine or to an explicitly supplied, legally obtained asset pipeline. The
public reference engine does not read Minecraft JARs, texture packs, or
customer worlds and cannot claim vanilla-texture fidelity.

For a managed build, the user must review the consent summary before the
declared world and library files leave the device. The selected retention
policy is part of the build request.

## Missing assets

The managed-build request supports a missing-asset policy:

- `generate`: the Engine may generate a documented fallback and report it in
  diagnostics.
- `error`: the Engine should stop on unmapped assets and report their IDs.

The fixture client can exercise the request/response contract, but it does not
resolve real block models or textures.
