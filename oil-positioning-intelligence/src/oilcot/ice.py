"""Read approved ICE Financial COT exports mapped to the local import format."""
from __future__ import annotations

import csv
from datetime import date
import math
from pathlib import Path

from .config import DATASETS, GROUPS, MARKETS


ICE_FIELDS = ("contract_code", "report_date", "basis", "cohort", "long", "short",
              "spreading", "open_interest")


def _position(value: str, field: str) -> float:
    try:
        amount = float(value)
    except ValueError as exc:
        raise ValueError(f"{field} must be numeric") from exc
    if not math.isfinite(amount) or amount < 0:
        raise ValueError(f"{field} must be finite and nonnegative")
    return amount


def read_ice_exports(paths: list[Path]) -> list[dict]:
    """Use supplied files only. Duplicate identical rows across files are harmless."""
    markets = {market.code: market for market in MARKETS.values() if market.source == "ICE"}
    reports: dict[tuple[str, str, str], dict[str, dict]] = {}
    for path in paths:
        with path.open(newline="", encoding="utf-8-sig") as stream:
            reader = csv.DictReader(stream, strict=True)
            missing = set(ICE_FIELDS) - set(reader.fieldnames or [])
            if missing:
                raise ValueError(f"{path.name}: missing ICE import columns: {', '.join(sorted(missing))}")
            if len(reader.fieldnames) != len(set(reader.fieldnames)):
                raise ValueError(f"{path.name}: duplicate CSV column names")
            for raw in reader:
                try:
                    if None in raw or any(raw[key] is None for key in ICE_FIELDS):
                        raise ValueError("row does not match the CSV header")
                    row = {key: raw[key].strip() for key in ICE_FIELDS}
                    market = markets.get(row["contract_code"])
                    if market is None:
                        raise ValueError("contract_code must be B (Brent) or G (Low Sulphur Gasoil)")
                    day = date.fromisoformat(row["report_date"]).isoformat()
                    basis, cohort = row["basis"], row["cohort"]
                    if basis not in DATASETS or cohort not in GROUPS:
                        raise ValueError("unrecognized report basis or trader category")
                    oi = _position(row["open_interest"], "open_interest")
                    if oi == 0:
                        raise ValueError("open_interest must be greater than zero")
                    positions = {
                        "long": _position(row["long"], "long"),
                        "short": _position(row["short"], "short"),
                        "spreading": _position(row["spreading"], "spreading") if row["spreading"] else None,
                    }
                    record = {
                        "source": "ICE", "market": market.key, "market_label": market.label,
                        "contract_code": market.code, "contract_units": market.units,
                        "report_date": day, "basis": basis, "cohort": cohort,
                        **positions, "open_interest": oi,
                    }
                    categories = reports.setdefault((market.code, day, basis), {})
                    if cohort in categories and categories[cohort] != record:
                        raise ValueError("conflicting values for the same contract, date, basis and category")
                    categories[cohort] = record
                except ValueError as exc:
                    raise ValueError(f"{path.name}, line {reader.line_num}: {exc}") from exc

    if not reports:
        raise ValueError("ICE exports contain no positioning rows")
    for (code, day, basis), categories in reports.items():
        label = f"ICE {code} {day} ({basis})"
        absent = GROUPS.keys() - categories.keys()
        if absent:
            raise ValueError(f"{label}: missing trader categories: {', '.join(sorted(absent))}")
        if len({r["open_interest"] for r in categories.values()}) != 1:
            raise ValueError(f"{label}: market open interest differs between trader categories")
    return [record for categories in reports.values() for record in categories.values()]
