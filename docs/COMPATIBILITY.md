# Compatibility

## Version Support Matrix

| Connector Version | Contract Version | Engine Version | Python | Blender | OS |
| --- | --- | --- | --- | --- | --- |
| 1.1.x | 1.0 | 2026.09.0+ | 3.10 – 3.13 | 4.5 LTS+ | Windows 10/11 x64 |
| 1.0.x | 1 (legacy) | 2026.09.0+ | 3.10 – 3.13 | 4.5 LTS+ | Windows 10/11 x64 |

## Contract Version Policy

The Connector and Engine communicate through a versioned contract. Contract versions follow semantic versioning:

- **Patch** (1.0.x): Compatible clarifications or optional fields.
- **Minor** (1.x.0): Backward-compatible new capability.
- **Major** (x.0.0): Removed/renamed field or changed behavior.

### Connector Behavior

- The Connector **rejects** an unsupported major version before downloading or opening any result.
- The Connector **accepts** compatible minor versions (e.g., a 1.1 manifest is accepted by a 1.0 Connector).

### Engine Behavior

- The Engine **rejects** an unsupported request major version before accepting an upload.
- The Engine consumes an exact tagged release of the public contract package.

## Engine Pinning Policy

The private Engine pins to a specific contract version tag. When the public contract is updated:

1. A new contract version is tagged in `Strata-Connector`.
2. The Engine updates its pinned version and runs contract conformance tests.
3. Both sides must pass before a paired release.

## Reference Engine

The `reference_engine/` included in this repository always supports the latest contract version. It is a protocol test fixture and does not provide production engine capabilities.
