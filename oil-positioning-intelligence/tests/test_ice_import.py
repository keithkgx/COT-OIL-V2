"""Synthetic fixtures for testing the offline ICE import and public build boundary."""
import csv
import json

import pytest

from oilcot.build import ROOT, build_dashboard, build_private_dashboard
from oilcot.config import GROUPS
from oilcot.ice import ICE_FIELDS, read_ice_exports
from oilcot.store import canonical


def ice_report(code, day, basis="combined"):
    return [
        dict(contract_code=code, report_date=day, basis=basis, cohort=cohort,
             long=200 + i, short=100, spreading=None, open_interest=1000)
        for i, cohort in enumerate(GROUPS)
    ]


def write_ice(path, rows):
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=ICE_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    return path


def payload(path):
    return json.loads(path.read_text(encoding="utf-8").split("\nconst DATA=", 1)[1].split(";\n", 1)[0])


def test_private_build_enables_only_imported_contracts(tmp_path):
    day = "2026-11-10"
    cftc_file = tmp_path / "cftc.csv"
    cftc_file.write_text(canonical([
        dict(report, source="CFTC", market="WTI", market_label="NYMEX WTI Crude",
             contract_code="067651", contract_units="1,000 bbl/contract")
        for report in ice_report("B", day)
    ]), encoding="utf-8")
    input_file = write_ice(tmp_path / "brent.csv", ice_report("B", "2026-11-03"))
    private_file = tmp_path / "private.html"
    public_file = tmp_path / "public.html"

    build_private_dashboard([input_file], private_file, history_path=cftc_file)
    build_dashboard(history_path=cftc_file, output=public_file)

    private = payload(private_file)
    assert private["private"] is True
    assert private["source_dates"] == {"CFTC": day, "ICE": "2026-11-03"}
    assert {m["key"]: m["enabled"] for m in private["markets"] if m["source"] == "ICE"} == {
        "BRENT": True, "GASOIL": False
    }
    brent = next(r for r in private["records"] if r["market"] == "BRENT" and r["cohort"] == "Managed Money")
    assert brent["net"] == 100
    assert brent["net_oi_pct"] == 10.0
    public = payload(public_file)
    assert {r["source"] for r in public["records"]} == {"CFTC"}
    assert {m["key"] for m in public["markets"]} == {"WTI", "ULSD", "RBOB"}


def test_public_build_rejects_ice_and_private_build_rejects_repo_output(tmp_path):
    path = write_ice(tmp_path / "ice.csv", ice_report("G", "2026-11-10", "futures"))
    history = tmp_path / "mixed.csv"
    history.write_text(canonical(read_ice_exports([path])), encoding="utf-8")
    with pytest.raises(ValueError, match="only the configured CFTC markets"):
        build_dashboard(history_path=history, output=tmp_path / "public.html")
    with pytest.raises(ValueError, match="outside the repository"):
        build_private_dashboard([path], ROOT / "dashboard" / "private.html")


def test_ice_overlaps_are_idempotent_and_conflicts_fail(tmp_path):
    rows = ice_report("B", "2026-11-10")
    first = write_ice(tmp_path / "first.csv", rows)
    second = write_ice(tmp_path / "second.csv", rows)
    assert len(read_ice_exports([first, second])) == 4
    write_ice(second, [dict(rows[0], long=999)])
    with pytest.raises(ValueError, match="conflicting values"):
        read_ice_exports([first, second])


@pytest.mark.parametrize(
    "change, message",
    [
        ({"contract_code": "BRN"}, "contract_code must be B"),
        ({"open_interest": 0}, "greater than zero"),
        ({"open_interest": 1200}, "differs between trader categories"),
        ({"long": "nan"}, "finite and nonnegative"),
    ],
)
def test_invalid_ice_export_is_rejected(tmp_path, change, message):
    rows = ice_report("G", "2026-11-10")
    rows[0].update(change)
    path = write_ice(tmp_path / "ice.csv", rows)
    with pytest.raises(ValueError, match=message):
        read_ice_exports([path])


def test_incomplete_ice_report_is_rejected(tmp_path):
    path = write_ice(tmp_path / "ice.csv", ice_report("G", "2026-11-10")[:-1])
    with pytest.raises(ValueError, match="missing trader categories"):
        read_ice_exports([path])
