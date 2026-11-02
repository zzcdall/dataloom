"""Delete every dataset from a running local DataLoom instance.

This is a development helper. It is intentionally explicit and does not touch
files outside the API's own storage.

Usage:
    python scripts/reset_dev_data.py http://127.0.0.1:8000
"""

from __future__ import annotations

import sys

import requests


def main() -> None:
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"
    datasets = requests.get(f"{base_url}/api/datasets", timeout=30).json()
    for dataset in datasets:
        response = requests.delete(f"{base_url}/api/datasets/{dataset['id']}", timeout=30)
        response.raise_for_status()
        print(f"deleted {dataset['id']} {dataset['name']}")
    print(f"Deleted {len(datasets)} dataset(s).")


if __name__ == "__main__":
    main()

