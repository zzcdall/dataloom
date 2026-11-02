# DataLoom backend

FastAPI service that ingests CSV/XLSX files into Parquet, profiles them with pandas,
and queries them with DuckDB.

Run from the repository root:

```bash
uvicorn app.main:app --app-dir backend --reload
```

