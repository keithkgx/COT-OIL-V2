"""Real-browser smoke test: visible Plotly tabs must fill their panels on first load.

Executed on GitHub PR checks using Playwright/Chromium. Deliberately uses
the already-generated local HTML so it never depends on public Pages state.
"""
from pathlib import Path
from playwright.sync_api import sync_playwright

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


def main():
    assert REPORT.exists() and REPORT.stat().st_size > 1_000_000
    OUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
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
        label = page.locator("#attribution-note strong").inner_text()
        assert "Net change" in label
        values = page.locator("#attribution-chart .bartext")
        assert values.count() >= 2, "Attribution values should be readable without hovering"
        for i in range(values.count()):
            fill = values.nth(i).evaluate("(el) => getComputedStyle(el).fill")
            assert fill in ("rgb(242, 247, 255)", "rgb(242,247,255)"), fill
        page.screenshot(path=str(OUT / "market-analysis.png"), full_page=True)
        page.get_by_role("button", name="Compare markets").click()
        check_chart(page, "overview-chart")
        check_chart(page, "market-change-chart")
        assert page.locator("#cross-highlights .cross-tile").count() == 3
        assert page.locator("#overview-rows tr").count() >= 3
        page.screenshot(path=str(OUT / "compare-markets.png"), full_page=True)
        page.get_by_role("button", name="Market analysis").click()
        page.set_viewport_size({"width": 1200, "height": 900})
        check_chart(page, "positions-chart")
        assert not errors, errors[:10]
        browser.close()
    print("PASS: visible attribution labels, cross-market analytics and chart widths at two viewport sizes")


if __name__ == "__main__":
    main()
