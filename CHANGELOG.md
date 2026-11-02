# Changelog

All notable changes to this project will be documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project uses
[Semantic Versioning](https://semver.org/).

## [0.1.0] - 2026-11-02

### Added

- CSV, TSV, and XLSX ingestion with encoding, delimiter, and type detection.
- Data profiling: missing values, duplicates, cardinality, distributions,
  outliers, and semantic column roles.
- Deterministic insight engine for trends, correlations, category concentration,
  outliers, distributions, and data-quality issues.
- Interactive exploration with bar, line, scatter, histogram, and table views.
- Natural-language questions backed by a local rule-based planner, with optional
  OpenAI-compatible LLM planning.
- Single-file HTML report export with charts, profiles, and data preview
  (ECharts loads from a CDN).
- FastAPI + DuckDB + Parquet backend, React + ECharts frontend.
- Docker image, Compose file, CI workflow, and demo dataset.

