"""Generate a local/offline interactive dashboard; embed all data and Plotly JS."""
from __future__ import annotations
import json
from pathlib import Path
from datetime import date, timedelta
from plotly.offline import get_plotlyjs
from .metrics import analyze
from .store import read_history
from .config import MARKETS
from .ice import read_ice_exports

ROOT = Path(__file__).resolve().parents[2]
HISTORY = ROOT / "data" / "cot_history.csv"


def _read_cftc_history(history_path: Path) -> list[dict]:
    records = read_history(history_path)
    markets = {m.key: m.code for m in MARKETS.values() if m.enabled and m.source == "CFTC"}
    if any(r["source"] != "CFTC" or markets.get(r["market"]) != r["contract_code"] for r in records):
        raise ValueError("CFTC history must contain only the configured CFTC markets")
    return records


def build_dashboard(history_path: Path = HISTORY, output: Path = ROOT / "dashboard" / "index.html") -> dict:
    return _render(_read_cftc_history(history_path), output)


def build_private_dashboard(ice_paths: list[Path], output: Path, history_path: Path = HISTORY) -> dict:
    output = output.resolve()
    if output.is_relative_to(ROOT.parent) or output.suffix.lower() != ".html":
        raise ValueError("Choose an .html output path outside the repository for the private dashboard")
    cftc = _read_cftc_history(history_path)
    if not cftc:
        raise ValueError("CFTC history is empty. Supply a CFTC history CSV or run the public backfill first")
    return _render(cftc + read_ice_exports(ice_paths), output, private=True)


def _render(records: list[dict], output: Path, private: bool = False) -> dict:
    processed = analyze(records)
    # Full historical canonical CSV is retained; the dashboard retains the latest
    # 5 calendar years for fast local loading, while 3Y statistics use complete history.
    if processed:
        most_recent = max(x["report_date"] for x in processed)
        cutoff = (date.fromisoformat(most_recent) - timedelta(days=365 * 5 + 4)).isoformat()
        selected = [x for x in processed if x["report_date"] >= cutoff]
    else:
        selected, most_recent = [], None
    source_dates = {}
    for row in processed:
        source, day = row["source"], row["report_date"]
        source_dates[source] = max(day, source_dates.get(source, day))
    source_dates = dict(sorted(source_dates.items()))
    available_markets = {(r["source"], r["market"]) for r in selected}
    if private and not any(source == "ICE" for source, _ in available_markets):
        raise ValueError("The supplied ICE observations are outside the dashboard’s five-year display window")
    payload = {
        "records": selected, "source_count": len(records), "last_observation": most_recent,
        "private": private, "source_dates": source_dates,
        "markets": [{"key": m.key, "label": m.label,
                     "enabled": m.enabled or (private and (m.source, m.key) in available_markets),
                     "source": m.source, "units": m.units} for m in MARKETS.values()],
    }
    data = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).replace("<", "\\u003c")
    template = (ROOT / "templates" / "dashboard.html").read_text(encoding="utf-8")
    html = template.replace("__EMBEDDED_DATA__", data).replace("/*__PLOTLY_BUNDLE__*/", get_plotlyjs())
    output.parent.mkdir(parents=True, exist_ok=True)
    if not output.exists() or output.read_text(encoding="utf-8") != html:
        output.write_text(html, encoding="utf-8")
    return {"observation_count": len(records), "dashboard_records": len(selected),
            "last_observation": most_recent, "source_dates": source_dates, "output": str(output)}
