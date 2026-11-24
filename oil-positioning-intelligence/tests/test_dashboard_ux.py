"""Smoke tests for the trader-facing dashboard controls and explanatory semantics."""
from pathlib import Path

from oilcot.build import ROOT


def test_asof_selection_and_cross_market_brief_exist():
    page = (ROOT / "templates" / "dashboard.html").read_text(encoding="utf-8")
    for snippet in (
        'id="asof"',
        'id="asof-caption"',
        'id="desk-brief"',
        "function deskBrief(",
        "function atMarket(",
        "r.report_date<=s.asof",
        "windowRows(rows,years,asof)",
        'id="overview-rows"',
        '4W change',
        '1Y rank',
        '3Y rank',
    ):
        assert snippet in page, snippet


def test_deep_dive_explicitly_disclaims_trades():
    page = (ROOT / "templates" / "dashboard.html").read_text(encoding="utf-8")
    assert 'id="flows-chart"' in page
    assert 'id="cohort-rows"' in page
    assert "not identified transactions" in page
    assert "Non-reportable positions are not in this version" in page


def test_private_offline_architecture_still_intact():
    source = (ROOT / "src" / "oilcot" / "build.py").read_text(encoding="utf-8")
    assert "get_plotlyjs" in source
    assert "output.write_text(html" in source
    assert (ROOT / "templates" / "dashboard.html").is_file()
