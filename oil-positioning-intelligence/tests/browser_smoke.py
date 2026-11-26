"""Real-browser smoke test for the standalone dashboard.

Executed on GitHub PR checks using Playwright/Chromium. Deliberately uses
the already-generated local HTML so it never depends on public Pages state.
"""
import csv
from datetime import date
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from playwright.sync_api import expect, sync_playwright

from oilcot.build import build_private_dashboard
from oilcot.store import canonical, read_history
from test_ice_import import ice_report, write_ice

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "dashboard" / "index.html"
OUT = ROOT / "browser-test-output"


def check_chart(page, chart_id: str):
    locator = page.locator("#" + chart_id)
    page.wait_for_function(
        "(id) => !!document.querySelector('#'+id+' .svg-container')",
        arg=chart_id,
        timeout=30000,
    )
    page.wait_for_timeout(400)
    panel = locator.locator("xpath=ancestor::div[contains(@class, 'panel')][1]")
    plot = locator.locator(".svg-container").first
    panel_width = panel.bounding_box()["width"]
    plot_width = plot.bounding_box()["width"]
    assert panel_width > 500, (chart_id, panel_width)
    assert plot_width > panel_width * 0.80, (
        f"{chart_id} plot only {plot_width:.0f}px within {panel_width:.0f}px panel"
    )
    print(f"{chart_id}: {plot_width:.0f}px within {panel_width:.0f}px panel")


def check_filtered_export(page):
    asof = page.locator("#asof option").nth(8).get_attribute("value")
    page.locator("#asof").select_option(asof)
    page.locator("#market").select_option("RBOB")
    page.locator("#cohort").select_option("Swap Dealers")
    page.locator("#basis").select_option("futures")
    page.locator("#window").select_option("1")
    page.get_by_role("button", name="Data & methodology").click()
    expect(page.locator("#history-rows tr td").first).to_have_text(asof)
    with page.expect_download() as download:
        page.get_by_role("button", name="Download filtered CSV").click()
    file = download.value
    assert file.suggested_filename == f"cot_RBOB_Swap_Dealers_futures_asof_{asof}_1y.csv"
    with file.path().open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    assert rows and all((r["market"], r["cohort"], r["basis"]) == ("RBOB", "Swap Dealers", "futures") for r in rows)
    end = date.fromisoformat(asof)
    start = end.replace(year=end.year - 1, day=28 if (end.month, end.day) == (2, 29) else end.day)
    with (ROOT / "data" / "cot_history.csv").open(newline="", encoding="utf-8") as stream:
        expected_dates = sorted(
            r["report_date"] for r in csv.DictReader(stream)
            if (r["market"], r["cohort"], r["basis"]) == ("RBOB", "Swap Dealers", "futures")
            and start.isoformat() <= r["report_date"] <= asof
        )
    assert [r["report_date"] for r in rows] == expected_dates


def check_misaligned_comparison(page):
    page.evaluate("""() => {
        const current = DATA.last_observation;
        const index = DATA.records.findIndex(r => r.market === 'WTI' && r.basis === 'combined' &&
            r.cohort === 'Managed Money' && r.report_date === current);
        if (index < 0) throw new Error('Missing WTI fixture');
        DATA.records.splice(index, 1);
        const ulsd = DATA.records.find(r => r.market === 'ULSD' && r.basis === 'combined' &&
            r.cohort === 'Managed Money' && r.report_date === current);
        ulsd.previous_date = '2000-01-01';
        render();
    }""")
    expect(page.locator("#cross-asof-note")).to_contain_text("2 of 3 markets")
    expect(page.locator("#overview-rows tr").filter(has_text="NYMEX WTI Crude")).to_contain_text("Earlier")
    expect(page.locator("#cross-highlights .metric").nth(1)).to_have_text("Unavailable")
    assert page.locator("#market-change-chart").evaluate("(el) => el.data.map(t => t.name)") == ["Four weeks"]
    assert set(page.locator("#positioning-map").evaluate("(el) => el.data[0].text")) == {"ULSD", "RBOB"}
    page.get_by_role("button", name="Use latest shared date").click()
    expect(page.locator("#cross-asof-note")).to_contain_text("3 of 3 markets")


def check_private_ice_view(browser):
    history = read_history(ROOT / "data" / "cot_history.csv")
    dates = sorted({r["report_date"] for r in history if r["market"] == "WTI" and r["basis"] == "combined"})
    current, previous = dates[-1], dates[-2]
    with TemporaryDirectory() as work:
        folder = Path(work)
        cftc = folder / "cftc.csv"
        cftc.write_text(canonical([r for r in history if r["report_date"] >= dates[-6]]), encoding="utf-8")
        rows = [r for day in dates[-6:-1] for r in ice_report("B", day)]
        rows += [r for day in dates[-6:-2] for r in ice_report("G", day)]
        ice = write_ice(folder / "ice.csv", rows)
        report = folder / "private.html"
        build_private_dashboard([ice], report, history_path=cftc)
        page = browser.new_page(viewport={"width": 1400, "height": 900})
        errors = []
        page.on("pageerror", lambda err: errors.append(str(err)))
        page.goto(report.as_uri(), wait_until="load")
        expect(page.locator("#status-text")).to_have_text(f"CFTC position date {current} · ICE position date {previous}")
        expect(page.locator("#market option")).to_have_count(5)
        page.locator("#market").select_option("BRENT")
        expect(page.locator("#analysis-title")).to_contain_text("ICE Brent Crude")
        expect(page.locator("#asof-caption")).to_contain_text(f"BRENT latest available position date {previous}")
        page.get_by_role("button", name="Compare markets").click()
        page.locator("#pair").select_option("crude")
        expect(page.locator("#overview-rows tr")).to_have_count(2)
        expect(page.locator("#cross-asof-note")).to_contain_text("1 of 2 markets")
        page.get_by_role("button", name="Use latest shared date").click()
        expect(page.locator("#asof")).to_have_value(previous)
        expect(page.locator("#cross-asof-note")).to_contain_text("2 of 2 markets")
        assert set(page.locator("#overview-chart").evaluate("(el) => el.data.map(t => t.name)")) == {"WTI", "BRENT"}
        page.locator("#pair").select_option("distillate")
        expect(page.locator("#cross-asof-note")).to_contain_text("1 of 2 markets")
        expect(page.locator("#overview-rows tr").filter(has_text="ICE Low Sulphur Gasoil")).to_contain_text("Earlier")
        page.locator("#basis").select_option("futures")
        expect(page.locator("#cross-asof-note")).to_contain_text("No Futures Only observations for GASOIL")
        assert not errors, errors[:10]
        page.close()


def main():
    assert REPORT.exists() and REPORT.stat().st_size > 1_000_000
    OUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True, args=["--no-sandbox"],
            executable_path=os.getenv("PLAYWRIGHT_CHROMIUM_EXECUTABLE"),
        )
        page = browser.new_page(viewport={"width": 1600, "height": 950}, device_scale_factor=1)
        errors = []
        page.on("pageerror", lambda err: errors.append(str(err)))
        page.goto(REPORT.resolve().as_uri(), wait_until="load", timeout=90000)
        page.get_by_role("button", name="Market analysis").wait_for()
        check_chart(page, "positions-chart")
        check_chart(page, "flows-chart")
        check_chart(page, "attribution-chart")
        check_chart(page, "cohort-chart")
        page.locator("#market-momentum").wait_for()
        expect(page.locator("#net-oi-attribution")).to_contain_text("Holdings")
        expect(page.locator("#net-oi-attribution")).to_contain_text("Open interest")
        label = page.locator("#attribution-note strong").inner_text()
        assert "Net change" in label
        values = page.locator("#attribution-chart .bartext")
        assert values.count() >= 2, "Attribution values should be readable without hovering"
        for i in range(values.count()):
            fill = values.nth(i).evaluate("(el) => getComputedStyle(el).fill")
            assert fill in ("rgb(242, 247, 255)", "rgb(242,247,255)"), fill
        page.screenshot(path=str(OUT / "market-analysis.png"), full_page=True)
        page.locator("#history-metric").select_option("net-oi")
        assert page.locator("#positions-chart").evaluate("(el) => el.data[0].name") == "Net/OI"
        page.locator("#history-metric").select_option("rank")
        assert page.locator("#positions-chart").evaluate("(el) => el.layout.yaxis.range") == [0, 100]
        page.locator("#history-metric").select_option("contracts")
        page.get_by_role("button", name="Compare markets").click()
        check_chart(page, "overview-chart")
        check_chart(page, "market-change-chart")
        check_chart(page, "positioning-map")
        expect(page.locator("#positioning-map .xtitle")).to_have_text("Three-year net/OI percentile")
        expect(page.locator("#positioning-map .ytitle")).to_have_text("Four-week change (pp)")
        expect(page.locator("#market-filter")).to_be_hidden()
        expect(page.locator("#pair-filter")).to_be_hidden()
        page.locator("#compare-metric").select_option("net_oi_pctile_3y")
        expect(page.locator("#overview-chart .ytitle")).to_have_text("Three-year percentile")
        page.locator("#compare-metric").select_option("net_oi_pct")
        assert page.locator("#cross-highlights .cross-tile").count() == 3
        assert page.locator("#overview-rows tr").count() >= 3
        page.screenshot(path=str(OUT / "compare-markets.png"), full_page=True)
        check_misaligned_comparison(page)
        page.get_by_role("button", name="Market analysis").click()
        expect(page.locator("#market-filter")).to_be_visible()
        check_filtered_export(page)
        page.set_viewport_size({"width": 390, "height": 844})
        page.get_by_role("button", name="Market analysis").click()
        page.locator("#positions-chart .svg-container").wait_for()
        assert page.locator("body").evaluate("(el) => el.scrollWidth") <= 390
        assert not errors, errors[:10]
        check_private_ice_view(browser)
        browser.close()
    print("PASS: attribution, chart views, date alignment, filtered CSV, responsive widths and private ICE coverage")


if __name__ == "__main__":
    main()
