"""Generate a local/offline interactive dashboard; embed all data and Plotly JS."""
from __future__ import annotations
import json
from pathlib import Path
from datetime import datetime, timezone
from plotly.offline import get_plotlyjs
from .metrics import analyze
from .store import read_history
from .config import MARKETS

ROOT = Path(__file__).resolve().parents[2]

def build_dashboard(history_path: Path = ROOT / "data" / "cot_history.csv",
                    output: Path = ROOT / "dashboard" / "index.html") -> dict:
    records = read_history(history_path)
    processed = analyze(records)
    # Full historical canonical CSV is retained; the dashboard retains the latest
    # 5 calendar years for fast local loading, while 3Y statistics use complete history.
    if processed:
        most_recent = max(x["report_date"] for x in processed)
        cutoff = (datetime.strptime(most_recent, "%Y-%m-%d") - __import__("datetime").timedelta(days=365 * 5 + 4)).date().isoformat()
        selected = [x for x in processed if x["report_date"] >= cutoff]
    else:
        selected, most_recent = [], None
    payload = {
        "records": selected, "source_count": len(records), "last_observation": most_recent,
        "markets": [{"key": m.key, "label": m.label, "enabled": m.enabled,
                     "source": m.source, "units": m.units} for m in MARKETS.values()],
    }
    data = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).replace("<", "\\u003c")
    template = (ROOT / "templates" / "dashboard.html").read_text(encoding="utf-8")
    html = template.replace("__EMBEDDED_DATA__", data).replace("/*__PLOTLY_BUNDLE__*/", get_plotlyjs())
    output.parent.mkdir(parents=True, exist_ok=True)
    if not output.exists() or output.read_text(encoding="utf-8") != html:
        output.write_text(html, encoding="utf-8")
    return {"observation_count": len(records), "dashboard_records": len(selected), "last_observation": most_recent, "output": str(output)}
