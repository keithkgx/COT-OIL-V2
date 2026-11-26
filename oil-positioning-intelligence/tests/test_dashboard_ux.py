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
    assert "if(active==='deep')renderDeep(s,r,rows)" in page
    assert "else if(active==='overview')renderOverview(s,r)" in page
    assert "function resizeVisibleCharts()" in page
    assert "ResizeObserver" in page
    assert "autosize:true" in page


def test_methodology_and_source_safety():
    page = page_source()
    assert "Spreading" in page
    assert "Futures + Options Combined" in page
    assert "Publication date is not available" in page
    assert "holdings, not identified trades" in page
    assert ".layout{width:100%;max-width:none" in page
    assert (ROOT / "docs" / "market-coverage.md").exists()


def test_offline_standalone_builder():
    source = (ROOT / "src" / "oilcot" / "build.py").read_text(encoding="utf-8")
    assert "get_plotlyjs" in source
    assert "output.write_text(html" in source
