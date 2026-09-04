# Strata Connector and Engine Plan

> This document is the authoritative packaging and convergence plan for the
> existing two-repository Strata product.

For the full plan, see the [source document](../../docs/PUBLIC_CONNECTOR_AND_ENGINE_PLAN.md).

## Summary

The Strata product consists of two repositories:

| Repository | Visibility | Responsibility |
| --- | --- | --- |
| `Strata-Connector` | Public | Blender add-on, MCP connector, contracts, reference engine, installer, docs, tests |
| `Strata-Engine` | Private | World ingestion, asset resolution, chunk planning, build workers, API, infrastructure |

The user sees **one product: Strata Toolkit**. The two repositories are an implementation boundary, not two separate applications.

## Key Principles

1. **The public Connector is independently useful** — it can be built, tested, and developed with the included reference engine.
2. **The private Engine stays private** — it never leaks code or secrets into a Connector release.
3. **The shared contract is the integration point** — versioned schemas, golden fixtures, and conformance tests.
4. **Managed builds require explicit consent** — files, hashes, intended use, and retention displayed before upload.
5. **No arbitrary code execution** — named MCP tools only, no eval/exec/shell endpoints.

See the [Architecture](ARCHITECTURE.md) and [Compatibility](COMPATIBILITY.md) documentation for implementation details.
