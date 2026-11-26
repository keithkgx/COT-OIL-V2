"""Template structure checks for the trader-first public dashboard."""
from oilcot.build import ROOT


def page_source():
    return (ROOT / "templates" / "dashboard.html").read_text(encoding="utf-8")


def test_tab_order_and_single_product_story():
    page = page_source()
    assert '<button class="active" data-tab="deep">Market analysis</button>' in page
    assert '<button data-tab="overview">Compare markets</button>' in page
    assert page.index('<section id="deep"') < page.index('<section id="overview"')
    assert page.count('class="stage-number"') == 5  # four stages + comparison
    for label in ("Positioning snapshot", "Positioning history", "driving the change",
                  "Market participation & positioning context"):
        assert label in page
    assert 'id="desk-brief"' not in page  # no market-wide cards before selected product
    assert 'id="kpis"' in page
    assert 'id="commentary"' in page


def test_main_dashboard_has_auditable_metrics():
    page = page_source()
    for label in (
        "01 · Net position",
        "02 · Open interest",
        "03 · Net / open interest",
        "04 · 3Y net/OI rank",
        "id=\"positions-chart\"",
        "id=\"attribution-chart\"",
        "id=\"flows-chart\"",
        "id=\"oi-chart\"",
        "id=\"cohort-rows\"",
        "id=\"overview-chart\"",
        "id=\"overview-rows\"",
        "id=\"asof\"",
    ):
        assert label in page


def test_hidden_tab_plotly_resizing_fix():
    page = page_source()
    assert "el.closest('.page.hidden')" in page
    assert "if(active==='deep')renderDeep(s,r,selectedHistory(s))" in page
    assert "else if(active==='overview')renderOverview(s)" in page
    assert "function resizeVisibleCharts()" in page
    assert "ResizeObserver" in page
    assert "autosize:true" in page


def test_methodology_and_source_safety():
    page = page_source()
    assert "Spreading" in page
    assert "Futures + Options Combined" in page
    assert "Publication date is not available" in page
    assert "Descriptive changes in reported holdings" in page
    assert ".layout{width:100%;max-width:none" in page
    assert (ROOT / "docs" / "market-coverage.md").exists()


def test_offline_standalone_builder():
    source = (ROOT / "src" / "oilcot" / "build.py").read_text(encoding="utf-8")
    assert "get_plotlyjs" in source
    assert "output.write_text(html" in source


def test_v4_attribution_has_visible_numeric_values_and_a_durable_explanation():
    source = page_source()
    for needle in ("textposition:'outside'", "textfont:{color:'#f2f7ff',size:15",
                   'id="attribution-note"', "strong>Net change",
                   "short-side contribution", "cliponaxis:false"):
        assert needle in source, needle


def test_v4_market_comparison_uses_normalized_changes_and_source_alignment():
    source = page_source()
    for needle in ("id=\"market-change-chart\"", "id=\"cross-highlights\"",
                   "id=\"cross-asof-note\"", "change_net_oi_pp",
                   "change_28d_net_oi_pp", "common previous report date"):
        assert needle in source, needle


def test_v4_single_market_readout_and_groups():
    source = page_source()
    assert 'id="market-momentum"' in source
    assert 'id="cohort-chart"' in source
    assert "function marketRegime(" in source
    assert "function contributionStory(" in source
    # No 'All net' aggregate, which would approach zero once counterparties balance.
    assert '<option>All Trader Groups</option>' not in source
