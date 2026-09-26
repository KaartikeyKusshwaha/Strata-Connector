# Privacy Policy — Strata Toolkit

**Last Updated:** September 2026

## 1. Overview
Strata Toolkit respects your privacy and adheres to a strict data-locality and explicit-consent architecture.

## 2. Local Operation
- The Strata MCP server (`strata-mcp`) and Blender add-on run locally on your system.
- Local preflight checks, library inspections, chunk streaming, and block state animations do not transmit world data or user assets over the Internet.
- Bridge authentication tokens and pairing nonces are generated locally, held in memory, and never logged or transmitted externally.

## 3. Managed Engine Builds & Consent
- Managed builds are an optional service. World data, asset libraries, and textures are **only** uploaded if you explicitly review and approve a consent prompt in the conversational interface.
- Consent summaries list every file path, SHA-256 hash, purpose, and retention policy before upload commences.
- Data retention adheres to the selected policy:
  - `delete_after_download`: Uploaded assets and generated artifacts are purged upon confirmed result download or within 24 hours.
  - `retain_7_days`: Artifacts are retained for up to 7 days for caching or re-download before automatic deletion.
- You may cancel a running build job at any time, which triggers immediate deletion of uploaded data.

## 4. Telemetry and Analytics
The open-source Strata Connector and Blender add-on do not collect telemetry, usage metrics, or error tracking data.

## 5. Security & Contact
To report security concerns or vulnerabilities, please review [SECURITY.md](SECURITY.md) or file a report via the [GitHub repository](https://github.com/KaartikeyKusshwaha/Strata-Connector).
