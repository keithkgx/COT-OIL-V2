from datetime import date, timedelta
from pathlib import Path
import csv
import pytest
from oilcot.fetch import get_rows, SourceError
from oilcot.normalize import normalize
from oilcot.store import read_history, upsert
from oilcot.metrics import analyze


def sample_raw(day="2026-11-10", long=152998, short=82414):
    return {
        "cftc_contract_market_code": "067651", "report_date_as_yyyy_mm_dd": day + "T00:00:00.000",
        "contract_units": "(CONTRACTS OF 1,000 BARRELS)", "open_interest_all": "1800000",
        "m_money_positions_long_all": str(long), "m_money_positions_short_all": str(short),
        "m_money_positions_spread": "15000", "prod_merc_positions_long": "350000",
        "prod_merc_positions_short": "500000", "swap_positions_long_all": "300000",
        "swap__positions_short_all": "250000", "swap__positions_spread_all": "32000",
        "other_rept_positions_long": "30000", "other_rept_positions_short": "25000",
        "other_rept_positions_spread": "5000",
    }


def test_live_report_arithmetic():
    m = normalize([sample_raw()], "combined")
    row = next(x for x in m if x["cohort"] == "Managed Money")
    assert row["long"] - row["short"] == 70584
    assert row["spreading"] == 15000
    assert row["basis"] == "combined"
    assert row["contract_code"] == "067651"


def test_cftc_live_api_field_names():
    """Matches the exact shortened column names observed in a real API response."""
    records = normalize([sample_raw()], "combined")
    assert len(records) == 4
    by_group = {r["cohort"]: r for r in records}
    assert by_group["Managed Money"]["spreading"] == 15000
    assert by_group["Other Reportables"]["long"] == 30000
    assert by_group["Other Reportables"]["short"] == 25000
    assert by_group["Other Reportables"]["spreading"] == 5000


def test_old_field_aliases_remain_accepted():
    raw = sample_raw()
    for field in ("m_money_positions_spread", "other_rept_positions_long",
                  "other_rept_positions_short", "other_rept_positions_spread"):
        raw[field + "_all"] = raw.pop(field)
    assert len(normalize([raw], "combined")) == 4


def test_upsert_revised_and_no_duplicates(tmp_path):
    path = tmp_path / "history.csv"
    one = normalize([sample_raw()], "combined")
    assert upsert(path, one) == (4, 0)
    assert upsert(path, one) == (0, 0)
    revision = normalize([sample_raw(long=154000)], "combined")
    assert upsert(path, revision) == (0, 1)
    assert len(read_history(path)) == 4
    assert next(x for x in read_history(path) if x["cohort"] == "Managed Money")["long"] == "154000"


def test_schema_missing_raises():
    raw = sample_raw()
    del raw["m_money_positions_short_all"]
    with pytest.raises(SourceError, match="missing"):
        normalize([raw], "combined")


def test_dates_are_calendar_aware():
    raws = [sample_raw("2026-10-27", 140000, 90000),sample_raw("2026-11-03", 150000, 85000),sample_raw("2026-11-10", 152998, 82414)]
    g = sorted([r for r in analyze(normalize(raws, "combined")) if r["cohort"] == "Managed Money"], key=lambda x:x["report_date"])
    assert g[-1]["net"] == 70584
    assert g[-1]["change_report"] == 5584
    assert g[-1]["change_long"] == 2998
    assert g[-1]["change_short"] == -2586
    assert g[-1]["change_7d"] == 5584
    assert g[-1]["change_28d"] is None
    assert g[-1]["net_oi_pctile_3y"] is None


def test_percentile_does_not_look_ahead():
    base = date(2023, 1, 3)
    rows = normalize([sample_raw((base + timedelta(days=i * 7)).isoformat(), long=120000 + i * 100, short=80000) for i in range(100)], "combined")
    all_stats = [r for r in analyze(rows) if r["cohort"] == "Managed Money"]
    half = [r for r in analyze(rows[:4 * 70]) if r["cohort"] == "Managed Money"]
    d = all_stats[69]["report_date"]
    assert next(r for r in all_stats if r["report_date"] == d)["net_oi_pctile_3y"] == next(r for r in half if r["report_date"] == d)["net_oi_pctile_3y"]
    assert all_stats[-1]["net_oi_pctile_3y"] is not None


def test_fetched_pagination_and_request_parameters():
    calls=[]
    class Response:
        def raise_for_status(self):pass
        def json(self):return [sample_raw()]
    def get(url, **kwargs):
        calls.append((url, kwargs));return Response()
    assert len(get_rows("combined", since="2026-01-01",request_get=get)) == 1
    assert "kh3c-gbw2.json" in calls[0][0]
    assert "067651" in calls[0][1]["params"]["$where"]
    assert calls[0][1]["params"]["$order"].startswith("report_date")


def test_cftc_transient_timeout_is_retried(monkeypatch):
    """The production request path retries timeouts before declaring the feed unavailable."""
    import requests
    from oilcot import fetch
    calls = []

    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return [sample_raw()]

    def sometimes_timeout(url, **kwargs):
        calls.append(kwargs)
        if len(calls) == 1:
            raise requests.Timeout("temporary CFTC gateway delay")
        return Response()

    monkeypatch.setattr(fetch.requests, "get", sometimes_timeout)
    monkeypatch.setattr(fetch.time, "sleep", lambda seconds: None)
    rows = fetch.get_rows("combined", since="2026-11-01")
    assert len(rows) == 1
    assert len(calls) == 2
    assert calls[0]["timeout"] == 60
