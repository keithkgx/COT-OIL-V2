"""Normalize CFTC snapshots into explicit typed values. Missing or renamed columns raise."""
from __future__ import annotations
from datetime import date
from .config import MARKETS, COLUMNS
from .fetch import SourceError

FIELDS = ["source", "market", "market_label", "contract_code", "contract_units", "basis",
          "report_date", "cohort", "long", "short", "spreading", "open_interest"]


def _required(row: dict, keys: tuple[str, ...], field: str) -> str:
    for key in keys:
        if key in row and row[key] is not None and str(row[key]).strip():
            return str(row[key])
    raise SourceError(f"Required CFTC column missing for {field}: tried {keys}; available={list(row)[:25]}")


def _number(row: dict, keys: tuple[str, ...], field: str) -> float:
    try:
        return float(_required(row, keys, field).replace(",", ""))
    except ValueError as exc:
        raise SourceError(f"Invalid numeric value in {field}") from exc


def normalize(rows: list[dict], basis: str) -> list[dict]:
    lookup = {m.code: m for m in MARKETS.values() if m.enabled and m.source == "CFTC"}
    records = []
    seen = set()
    for raw in rows:
        code = _required(raw, ("cftc_contract_market_code",), "market code")
        if code not in lookup:
            continue
        market = lookup[code]
        date_text = _required(raw, ("report_date_as_yyyy_mm_dd",), "report date")[:10]
        try:
            iso_date = date.fromisoformat(date_text).isoformat()
        except ValueError as exc:
            raise SourceError(f"Bad CFTC report date: {date_text}") from exc
        oi = _number(raw, ("open_interest_all",), "open interest")
        if oi <= 0:
            raise SourceError(f"Impossible open interest for {market.key} on {iso_date}: {oi}")
        for cohort, cols in COLUMNS.items():
            long = _number(raw, cols["long"], f"{cohort}.long")
            short = _number(raw, cols["short"], f"{cohort}.short")
            spread = (_number(raw, cols["spread"], f"{cohort}.spreading")
                      if cols["spread"] else None)
            if min(long, short) < 0 or (spread is not None and spread < 0):
                raise SourceError("Negative CFTC long/short/spread amount")
            record = {
                "source": "CFTC", "market": market.key, "market_label": market.label,
                "contract_code": code, "contract_units": _required(raw, ("contract_units",), "contract units"),
                "basis": basis, "report_date": iso_date, "cohort": cohort,
                "long": long, "short": short, "spreading": spread, "open_interest": oi,
            }
            key = (basis, market.key, iso_date, cohort)
            if key in seen:
                raise SourceError(f"Duplicate contract-market-date row in source response: {key}")
            seen.add(key)
            records.append(record)
    if not records:
        raise SourceError("No recognized markets remained after CFTC normalization")
    return records
