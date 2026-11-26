"""Real-browser smoke test for the standalone dashboard.

Executed on GitHub PR checks using Playwright/Chromium. Deliberately uses
the already-generated local HTML so it never depends on public Pages state.
"""
import csv
from datetime import date
import os
from pathlib import Path
from playwright.sync_api import expect, sync_playwright

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
        expect(page.locator("#market-filter")).to_be_hidden()
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
        browser.close()
    print("PASS: attribution, historical chart views, comparison dates, filtered CSV and responsive widths")


if __name__ == "__main__":
    main()
