"""Generate the deterministic demo dataset used by DataLoom.

Run from the repository root:
    python examples/generate_sample.py
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


def build_dataframe(rows: int = 1800, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    start = pd.Timestamp("2024-01-01")
    end = pd.Timestamp("2025-12-31")
    days = pd.date_range(start, end, freq="D")
    chosen = pd.DatetimeIndex(rng.choice(days, size=rows))
    day_index = (chosen - start).days.to_numpy()
    day_of_year = chosen.dayofyear.to_numpy()

    regions = rng.choice(
        ["华东", "华北", "华南", "西南", "东北"],
        size=rows,
        p=[0.34, 0.21, 0.20, 0.15, 0.10],
    )
    categories = rng.choice(
        ["数码", "家居", "服饰", "美妆", "食品"],
        size=rows,
        p=[0.28, 0.21, 0.20, 0.16, 0.15],
    )
    channels = rng.choice(["线上", "线下", "分销"], size=rows, p=[0.55, 0.30, 0.15])
    campaigns = rng.choice(["是", "否"], size=rows, p=[0.18, 0.82])

    region_lift = pd.Series(regions).map(
        {"华东": 1.35, "华北": 1.10, "华南": 1.18, "西南": 0.92, "东北": 0.80}
    ).to_numpy()
    category_base = pd.Series(categories).map(
        {"数码": 1150.0, "家居": 720.0, "服饰": 480.0, "美妆": 360.0, "食品": 180.0}
    ).to_numpy()
    channel_lift = pd.Series(channels).map({"线上": 1.12, "线下": 1.00, "分销": 0.82}).to_numpy()
    margin = pd.Series(categories).map(
        {"数码": 0.18, "家居": 0.24, "服饰": 0.31, "美妆": 0.36, "食品": 0.16}
    ).to_numpy()

    trend = 1 + day_index * 0.00038
    season = 1 + 0.17 * np.sin(2 * np.pi * (day_of_year / 365.25) - 1.15)
    campaign_lift = np.where(campaigns == "是", 1.14, 1.0)
    base = category_base * region_lift * channel_lift * trend * season * campaign_lift
    revenue = base * rng.lognormal(mean=0, sigma=0.24, size=rows)
    orders = rng.integers(1, 9, size=rows)
    profit = revenue * margin + rng.normal(0, revenue * 0.075, size=rows)
    unit_price = revenue / orders
    age = np.clip(rng.normal(34, 9.5, size=rows), 18, 65).round().astype(int)
    satisfaction = np.round(
        np.clip(rng.normal(4.12 - 0.24 * (channels == "分销"), 0.62, size=rows), 1, 5), 1
    )
    satisfaction[rng.random(rows) < 0.085] = np.nan
    profit[rng.random(rows) < 0.015] = np.nan
    regions = regions.astype(object)
    regions[rng.random(rows) < 0.004] = np.nan
    customer_ids = [f"C{index:05d}" for index in rng.integers(1, rows * 3, size=rows)]

    frame = pd.DataFrame(
        {
            "订单日期": pd.to_datetime(chosen).strftime("%Y-%m-%d"),
            "地区": regions,
            "品类": categories,
            "渠道": channels,
            "营销活动": campaigns,
            "销售额": np.round(revenue, 2),
            "订单数": orders,
            "利润": np.round(profit, 2),
            "客单价": np.round(unit_price, 2),
            "客户年龄": age,
            "满意度": satisfaction,
            "客户ID": customer_ids,
        }
    )
    frame = frame.sort_values("订单日期").reset_index(drop=True)
    duplicates = frame.sample(8, random_state=seed)
    frame = pd.concat([frame, duplicates], ignore_index=True)
    return frame.sort_values("订单日期").reset_index(drop=True)


def main() -> None:
    output = Path(__file__).with_name("sample_sales.csv")
    frame = build_dataframe()
    frame.to_csv(output, index=False, encoding="utf-8-sig")
    print(f"Wrote {len(frame):,} rows to {output}")


if __name__ == "__main__":
    main()

