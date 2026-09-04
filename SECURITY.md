# Security Policy

## Supported Versions

| Version | Supported |
| --- | --- |
| 1.0.x | ✅ |
| < 1.0 | ❌ |

## Reporting a Vulnerability

If you discover a security vulnerability in the Strata Connector, please report it responsibly.

**Do NOT open a public issue.** Instead:

1. Email **security@strata.dev** with a detailed description of the vulnerability.
2. Include steps to reproduce, affected versions, and any potential impact.
3. Allow up to **72 hours** for an initial response.
4. We will work with you to understand and address the issue before any public disclosure.

## Scope

The following areas are in scope for security reports:

- **MCP tool surface**: Unintended code execution, path traversal, or data leakage through MCP tools.
- **Bridge authentication**: Session token bypass, replay attacks, or token leakage.
- **Manifest validation**: Signature bypass, checksum manipulation, or path escaping in result artifacts.
- **Credential handling**: Exposure of API tokens, session tokens, or signing keys.

The following are **out of scope**:

- Issues in the private Strata Engine (report those through the managed service support channel).
- Issues in Blender itself.
- Social engineering or phishing attacks.

## Disclosure Policy

We follow coordinated disclosure. Fixes will be released as patch versions with a security advisory. Credit will be given to reporters unless they prefer to remain anonymous.
