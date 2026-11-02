# Publishing checklist

This guide is for the first public release of `zzcdall/dataloom`.

## 1. Pick and verify the name

DataLoom is a working name. Before publishing, check:

- GitHub organization and repository availability
- npm package name (`dataloom-frontend` is only local; the product name matters)
- PyPI project name (`dataloom`)
- `dataloom.dev` / `dataloom.app` / `dataloom.io` domain availability
- A trademark search in your target market

If the name is taken, keep the code and change only the brand strings:

- `frontend/public/favicon.svg`
- `frontend/src/components/Logo.tsx`
- `frontend/index.html`
- `backend/app/main.py` (`title`)
- `backend/pyproject.toml`
- both README files
- `docker-compose.yml` and the Docker image name

## 2. Replace placeholders

```bash
# From the repository root
grep -R "your-handle" -n .   # should return nothing
```

Update:

- `README.md` and `README.zh-CN.md` clone URL
- `backend/pyproject.toml` project URLs
- `docs/PUBLISHING.md` if you want a different workflow

## 3. Final local verification

```bash
python -m pytest backend/tests
cd frontend && npm run build
cd ..
docker compose up --build
```

Check <http://localhost:8000>:

- upload a CSV
- load the demo dataset
- open each tab
- export the HTML report
- delete a dataset

Make sure `git status` does not include `data/`, `*.parquet`, `*.db`, or uploads.

## 4. Create the repository

```bash
git init
git add .
git commit -m "feat: initial DataLoom release"
git branch -M main
git remote add origin https://github.com/zzcdall/dataloom.git
git push -u origin main
```

Repository description suggestion (≤ 120 chars):

> Upload CSV/Excel, get an auditable automated analysis report in seconds. Local-first, DuckDB + React, deterministic insights.

Topics:

`data-analysis`, `data-visualization`, `duckdb`, `fastapi`, `react`, `echarts`,
`csv`, `excel`, `dashboard`, `self-hosted`, `local-first`, `ai-analytics`

Enable:

- Issues
- Discussions (optional, useful for "show your data" threads)
- Private vulnerability reporting
- Dependabot alerts

Upload `docs/social-preview.png` as the social preview (1280×640). Regenerate it
after UI changes with `python scripts/make_social_preview.py`.

## 5. Tag v0.1.0

```bash
git tag -a v0.1.0 -m "DataLoom v0.1.0"
git push origin v0.1.0
```

Create a GitHub Release from the tag and paste the `0.1.0` section of
`CHANGELOG.md`. Attach a screenshot and the HTML report generated from
`examples/sample_sales.csv`.

Optional: publish a container image to GHCR.

```bash
docker build -t ghcr.io/zzcdall/dataloom:0.1.0 .
echo $GITHUB_TOKEN | docker login ghcr.io -u zzcdall --password-stdin
docker push ghcr.io/zzcdall/dataloom:0.1.0
```

## 6. Launch sequence

Do not launch cold. A small, real feedback loop is more valuable than a big
announcement.

1. Ask 5–10 people to run their own CSV/XLSX through it. Watch where they get
   stuck; fix the top three issues.
2. Record a 30–60 second screen capture: upload → insight cards → explore →
   export.
3. Publish a demo page (or a Docker one-liner) with a synthetic dataset only.
   Never upload a real customer dataset to a public demo.
4. Post to Show HN on Tuesday–Thursday morning US Eastern time. Lead with the
   local-first/auditable angle, not "AI".
5. Cross-post: `r/dataengineering`, `r/selfhosted`, `r/opensource`, V2EX, 知乎,
   小红书, and 即刻. Adapt the copy; do not paste the same post everywhere.
6. Reply to every issue quickly for the first two weeks.

Avoid asking for stars. Ask for specific feedback: "What did it get wrong on
your data?"

## 7. What to measure

- Time from upload to first useful insight (target: < 60 seconds)
- Percentage of uploads that produce at least one non-overview insight
- Export rate (a proxy for "this was useful")
- Repeat usage within 7 days
- Top failing file shapes (encodings, merged cells, multi-sheet workbooks)

## 8. Known limitations to state honestly

- Single-user, no auth
- First worksheet only for XLSX
- Browser upload limit of 100 MB by default
- Correlation is not causation; the insight engine says so explicitly
- LLM planning is optional and never trusted with raw data or SQL execution

