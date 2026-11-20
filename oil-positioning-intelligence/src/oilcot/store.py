"""Versionable canonical CSV store. Upsert by natural key, preserving full history."""
from __future__ import annotations
import csv
import io
from pathlib import Path
from .normalize import FIELDS
from .fetch import SourceError

KEY = ("source", "market", "basis", "report_date", "cohort")

def read_history(path: Path) -> list[dict]:
    if not path.exists() or path.stat().st_size == 0:
        return []
    with path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        if not set(FIELDS).issubset(set(reader.fieldnames or [])):
            raise SourceError("Historical CSV schema mismatch; do not overwrite without a migration")
        return list(reader)

def canonical(records: list[dict]) -> str:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=FIELDS, lineterminator="\n")
    writer.writeheader()
    def fmt(row):
        copied = dict(row)
        for c in ("long", "short", "spreading", "open_interest"):
            copied[c] = ("" if copied[c] is None or copied[c] == "" else
                         f"{float(copied[c]):.4f}".rstrip("0").rstrip("."))
        return copied
    for row in sorted(records, key=lambda r: tuple(str(r[k]) for k in KEY)):
        writer.writerow({col: fmt(row)[col] for col in FIELDS})
    return output.getvalue()

def upsert(path: Path, incoming: list[dict]) -> tuple[int,int]:
    existing = read_history(path)
    by_key = {tuple(row[c] for c in KEY): row for row in existing}
    if len(by_key) != len(existing):
        raise SourceError("Historical CSV has duplicate primary keys")
    before = canonical(existing)
    new_count, corrected_count = 0, 0
    for row in incoming:
        key = tuple(str(row[c]) for c in KEY)
        if key not in by_key:
            new_count += 1
        elif canonical([by_key[key]]) != canonical([row]):
            corrected_count += 1
        by_key[key] = row
    result = canonical(list(by_key.values()))
    if before != result or not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(result, encoding="utf-8")
        tmp.replace(path)
    return new_count, corrected_count
