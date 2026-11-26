"""CLI for refresh, backfill, dashboard generation and offline testing."""
from __future__ import annotations
import argparse
import csv
import json
from datetime import date, timedelta
from pathlib import Path
from .fetch import get_rows, SourceError
from .normalize import normalize
from .store import read_history, upsert
from .build import build_dashboard, build_private_dashboard, HISTORY


def refresh(data_path: Path, backfill: bool = False, basis: str = "both") -> dict:
    existing = read_history(data_path)
    requested = ["combined", "futures"] if basis == "both" else [basis]
    # Fetch ALL bases before writing; a temporary upstream failure never partially updates the store.
    additions: list[dict] = []
    counts = {}
    for name in requested:
        dates = [date.fromisoformat(r["report_date"]) for r in existing
                 if r["source"] == "CFTC" and r["basis"] == name]
        since = "2006-06-01" if backfill or not dates else (max(dates) - timedelta(days=90)).isoformat()
        raw = get_rows(name, since=since)
        normalized = normalize(raw, name)
        additions.extend(normalized)
        counts[name] = {"since": since, "raw_rows": len(raw), "position_rows": len(normalized)}
    new, corrections = upsert(data_path, additions)
    return {"new_rows": new, "revised_rows": corrections, "sources": counts}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Oil COT monitor")
    parser.add_argument("command", choices=("refresh", "backfill", "build", "build-private", "status"))
    parser.add_argument("--basis", choices=("combined", "futures", "both"), default="both")
    parser.add_argument("--data", type=Path, default=HISTORY, help="Canonical CFTC history")
    parser.add_argument("--ice-data", type=Path, action="append", help="Approved normalized ICE CSV, repeat for multiple files")
    parser.add_argument("--output", type=Path, help="Private dashboard HTML path, outside the repository")
    args = parser.parse_args(argv)
    if args.command == "build-private":
        if not args.ice_data or args.output is None:
            parser.error("build-private requires --ice-data and --output")
    elif args.ice_data or args.output is not None:
        parser.error("--ice-data and --output are only available with build-private")
    try:
        if args.command in ("refresh", "backfill"):
            result = refresh(args.data, backfill=args.command == "backfill", basis=args.basis)
            result["dashboard"] = build_dashboard(history_path=args.data)
        elif args.command == "build":
            result = build_dashboard(history_path=args.data)
        elif args.command == "build-private":
            result = build_private_dashboard(args.ice_data, args.output, history_path=args.data)
        else:
            history = read_history(args.data)
            result = {"rows": len(history), "markets": sorted(set(r["market"] for r in history)),
                      "latest_report_date": max((r["report_date"] for r in history), default=None)}
        print(json.dumps(result, indent=2))
    except (SourceError, ValueError, OSError, csv.Error) as exc:
        parser.exit(1, f"ERROR: {exc}\n")

if __name__ == "__main__":
    main()
