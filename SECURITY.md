# Security

## Supported versions

DataLoom is pre-1.0. Security fixes are applied to the latest release on `main`.

## Reporting a vulnerability

Please do not open a public issue for a vulnerability. Use GitHub's private
security advisory flow ("Security" → "Report a vulnerability") or contact the
maintainer listed in the repository profile. Include reproduction steps and the
affected version.

## Threat model

DataLoom is designed as a local-first, single-user tool. It does not ship with
authentication or multi-tenant isolation. Do not expose it directly to the public
internet without putting it behind an authenticated reverse proxy.

Key safeguards in the current design:

- Uploaded tables are treated as untrusted data. Column identifiers are matched
  against the stored profile and quoted; filter values are parameterized.
- The optional LLM planner only receives column metadata and the user's
  question. It returns a typed `AnalysisSpec`, which is validated before
  execution.
- The LLM never receives raw rows, and generated SQL is never executed.
- File names are display-only; stored files use server-generated UUIDs.
- Upload size is capped (100 MB by default) and file extensions are restricted.

## Data handling

By default all data stays in the local `data/` directory. If an LLM is
configured, only metadata and the question are sent to the configured
OpenAI-compatible endpoint. Review that provider's retention policy before
enabling it.

