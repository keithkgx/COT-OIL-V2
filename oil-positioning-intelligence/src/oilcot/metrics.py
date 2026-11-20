"""Causal positioning metrics with calendar-aware history, no future observations."""
from __future__ import annotations
from datetime import timedelta
import math
import pandas as pd

MIN_POOL = {"1y": 20, "3y": 60}


def _safe(value):
    if pd.isna(value):
        return None
    return float(value)


def _reference(group: pd.DataFrame, at: pd.Timestamp, days_ago: int, tolerance_days: int = 4):
    # Only older data are considered. Closest to the actual calendar target.
    target = at - pd.Timedelta(days=days_ago)
    subset = group[group["report_date"].lt(at)]
    if subset.empty:
        return None
    deltas = (subset["report_date"] - target).abs()
    idx = deltas.idxmin()
    if deltas.loc[idx] > pd.Timedelta(days=tolerance_days):
        return None
    return subset.loc[idx]


def _weekly_population(group: pd.DataFrame, at: pd.Timestamp, lookback: int) -> pd.DataFrame:
    # Inclusive current value; select last available observation of each calendar week
    # as seen AS OF at (no later observation can revise a historical percentile).
    lo = at - pd.DateOffset(years=lookback)
    pool = group.loc[(group["report_date"] >= lo) & (group["report_date"] <= at)].copy()
    if pool.empty:
        return pool
    # week_key is precomputed once per group in analyze().
    return pool.drop_duplicates("week_key", keep="last")


def _percentile(pool: pd.Series, current: float, minimum: int):
    v = pool.dropna()
    if len(v) < minimum or not math.isfinite(current):
        return None
    # Midrank empirical CDF; ties get average rank; percentile is 0–100.
    return round(100.0 * ((v < current).sum() + 0.5 * (v == current).sum()) / len(v), 1)


def analyze(records: list[dict]) -> list[dict]:
    if not records:
        return []
    df = pd.DataFrame.from_records(records)
    for col in ("long", "short", "spreading", "open_interest"):
        df[col] = pd.to_numeric(df[col], errors="coerce" if col == "spreading" else "raise")
    df["report_date"] = pd.to_datetime(df["report_date"], errors="raise")
    if df.duplicated(["source", "market", "basis", "report_date", "cohort"]).any():
        raise ValueError("Duplicate natural keys in history")
    df["net"] = df["long"] - df["short"]
    df["gross"] = df["long"] + df["short"]
    df["net_oi_pct"] = 100 * df["net"] / df["open_interest"]
    df["long_short_ratio"] = df["long"] / df["short"].replace(0, float("nan"))
    output = []
    keys = ["source", "market", "basis", "cohort"]
    for _, g in df.groupby(keys, sort=False):
        g = g.sort_values("report_date").reset_index(drop=True)
        # A historical level-series comparison is invalid across unit changes; segment it.
        gap = g["report_date"].diff() > pd.Timedelta(days=90)
        segment = (g["contract_units"].ne(g["contract_units"].shift()) | gap).cumsum()
        iso = g["report_date"].dt.isocalendar()
        g["week_key"] = iso.year.astype(str) + "-" + iso.week.astype(str)
        for i, r in g.iterrows():
            before = g.iloc[i - 1] if i else None
            compatible_before = before is not None and segment.iloc[i] == segment.iloc[i-1]
            week = _reference(g, r["report_date"], 7)
            month4 = _reference(g, r["report_date"], 28, tolerance_days=5)
            if week is not None and week["contract_units"] != r["contract_units"]:
                week = None
            if month4 is not None and month4["contract_units"] != r["contract_units"]:
                month4 = None
            row = {key: r[key] for key in keys}
            row.update({
                "market_label": r["market_label"], "contract_code": r["contract_code"],
                "contract_units": r["contract_units"], "report_date": r["report_date"].strftime("%Y-%m-%d"),
                "long": float(r["long"]), "short": float(r["short"]), "spreading": _safe(r["spreading"]),
                "open_interest": float(r["open_interest"]),
                "net": float(r["net"]), "gross": float(r["gross"]),
                "net_oi_pct": round(float(r["net_oi_pct"]), 3),
                "long_short_ratio": _safe(r["long_short_ratio"]),
                "previous_date": before["report_date"].strftime("%Y-%m-%d") if before is not None else None,
                "change_report": (float(r["net"] - before["net"]) if compatible_before else None),
                "change_long": (float(r["long"] - before["long"]) if compatible_before else None),
                "change_short": (float(r["short"] - before["short"]) if compatible_before else None),
                "change_oi": (float(r["open_interest"] - before["open_interest"]) if compatible_before else None),
                "change_7d": (float(r["net"] - week["net"]) if week is not None else None),
                "change_28d": (float(r["net"] - month4["net"]) if month4 is not None else None),
            })
            for period, years in (("1y", 1), ("3y", 3)):
                # Net/OI is comparable across unit re-specifications; absolute net is not.
                pool = _weekly_population(g, r["report_date"], years)
                row[f"net_oi_pctile_{period}"] = _percentile(
                    pool["net_oi_pct"], float(r["net_oi_pct"]), MIN_POOL[period])
                compatible = pool[pool.index.map(lambda k: segment.iloc[k] == segment.iloc[i])]
                row[f"net_pctile_{period}"] = _percentile(
                    compatible["net"], float(r["net"]), MIN_POOL[period])
            output.append(row)
    return sorted(output, key=lambda r: (r["market"], r["basis"], r["cohort"], r["report_date"]))
