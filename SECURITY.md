# Security Policy

## Reporting a vulnerability

Do not open a public issue for credentials, authorization bypasses, destructive bridge behavior, prompt injection that exposes protected data, or evidence tampering. Use the repository host's private vulnerability-reporting channel and include the affected commit, reproduction, impact, and suggested containment.

## Security boundaries

- Production Human Gates block by default. Test-only auto approval must be explicitly injected and must not be used as production authorization.
- AgentTeams and bench bridges are separate trust boundaries. Core code does not inherit their credentials or permissions.
- Bridge status checks are read-only. Apply and deletion require an exact target review; prefix-wide deletion is prohibited.
- Secrets belong in local environment or secret managers. They must not appear in source, examples, logs, RunStore, reports, or generated manifests.
- Approved G3 decisions require an external signing key and key identifier. Validation and export must receive the same key from the runtime secret manager; the decision artifact stores only the key identifier and HMAC signature.
- Sealed-holdout outcomes are inaccessible before Candidate Freeze and must not drive direct updates.
- Run conclusions are accepted only after hash and provenance verification. A summary flag alone is not evidence.

## Supported code

Security fixes target the current `main` branch. Historical Git commits and the frozen preliminary submission are retained for audit but are not active deployment artifacts.
