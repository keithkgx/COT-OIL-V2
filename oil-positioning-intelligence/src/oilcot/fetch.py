"""CFTC PRE Socrata data API client. Fails closed on incomplete pagination or HTTP errors."""
from __future__ import annotations
import os
import time
from datetime import date
from typing import Callable
import requests
from .config import DATASETS, MARKETS

BASE_URL = "https://publicreporting.cftc.gov/resource"

class SourceError(RuntimeError):
    """Official data retrieval failed; never silently use stale data as if current."""


def get_rows(basis: str, since: str = "2006-06-01", page_size: int = 5000,
             request_get: Callable | None = None) -> list[dict]:
    if basis not in DATASETS:
        raise ValueError(f"Unknown COT report basis: {basis}")
    date.fromisoformat(since)
    if page_size < 1 or page_size > 50000:
        raise ValueError("page_size must be between 1 and 50000")
    get = request_get or requests.get
    codes = [m.code for m in MARKETS.values() if m.enabled and m.source == "CFTC"]
    where = ("cftc_contract_market_code in (" + ",".join("'" + code + "'" for code in codes)
             + ") and report_date_as_yyyy_mm_dd >= '" + since + "T00:00:00'")
    url = f"{BASE_URL}/{DATASETS[basis]}.json"
    rows: list[dict] = []
    offset = 0
    for page in range(250):
        params = {
            "$where": where,
            "$order": "report_date_as_yyyy_mm_dd ASC, cftc_contract_market_code ASC",
            "$limit": page_size, "$offset": offset,
        }
        headers = {"User-Agent": "Oil-Positioning-Intelligence/0.1 (CFTC public data)",
                   "Accept": "application/json"}
        token = os.getenv("CFTC_APP_TOKEN")
        if token:
            headers["X-App-Token"] = token
        try:
            # Test adapters can supply a mock request_get with the same signature.
            response = get(url, params=params, headers=headers, timeout=35)
            response.raise_for_status()
            chunk = response.json()
        except (requests.RequestException, ValueError) as exc:
            raise SourceError(f"CFTC {basis} request failed (offset {offset}): {exc}") from exc
        if not isinstance(chunk, list):
            raise SourceError(f"Unexpected CFTC JSON structure for {basis} at offset {offset}")
        if chunk and any(not isinstance(item, dict) for item in chunk):
            raise SourceError("Unexpected CFTC row structure")
        rows.extend(chunk)
        if len(chunk) < page_size:
            break
        offset += len(chunk)
        time.sleep(0.15)
    else:
        raise SourceError("CFTC pagination exceeded safety limit")
    if not rows:
        raise SourceError(f"CFTC {basis} returned no matching contracts since {since}; check codes and API")
    return rows
