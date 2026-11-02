# Contributing to DataLoom

Thanks for your interest. DataLoom is intentionally small and auditable, so the
best contributions are focused bug fixes, new deterministic insight detectors,
and usability improvements.

## Development setup

Requirements: Python 3.10+, Node.js 20+.

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
source .venv/bin/activate
pip install -e "backend[dev]"

cd frontend
npm install
cd ..
```

Run the API and the Vite dev server in two terminals:

```bash
uvicorn app.main:app --app-dir backend --reload
```

```bash
cd frontend
npm run dev
```

Open <http://localhost:5173>. The Vite server proxies `/api` to port 8000.

## Tests and checks

```bash
python -m pytest backend/tests
cd frontend && npm run build
```

Please add a test for any new insight detector or query behavior. Golden-file
tests for chart payloads are welcome.

## Design rules

- The analysis engine must remain deterministic. An LLM may plan an analysis,
  but it must never execute arbitrary code or SQL.
- Every column used in SQL must be validated against the stored schema.
- User-supplied values must be passed as query parameters, never interpolated.
- New insights should include a plain-language explanation, evidence, and a
  confidence level.
- Keep the default path working without an API key or network access.

## Pull requests

- Keep changes scoped and include a short rationale.
- Update `README.md` or `README.zh-CN.md` when behavior changes.
- Add a `CHANGELOG.md` entry for user-facing changes.
- Do not commit `data/`, uploaded files, or generated Parquet files.

By contributing, you agree that your contributions are licensed under the
Apache License 2.0.

