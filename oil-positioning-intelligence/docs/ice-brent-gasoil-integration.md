# ICE Brent and Low Sulphur Gasoil COT — integration specification

Status on 26 November 2026: **chosen as the next oil benchmarks, but not enabled for automated public redistribution**. The public dashboard links to ICE's official reporting index and contains **no fabricated ICE figures**.

## Exact target instruments

| Market | ICE Futures Europe COT code | Contract size | Economic role |
| --- | --- | --- | --- |
| Brent crude futures and options | `B` | 1,000 barrels per contract | Global seaborne crude benchmark |
| Low Sulphur Gasoil futures and options | `G` | 100 metric tonnes per contract | European diesel / middle-distillate benchmark |

These are **ICE Futures Europe Financial COT** series, not NYMEX Brent Last Day, ICE Singapore mini contracts, ICE WTI, or crack-spread legs.

Sources:
- [ICE Futures Europe COT explanatory notes](https://www.ice.com/publicdocs/futures/CoT_Notes.pdf) (codes, trader categories and futures-equivalent treatment)
- [ICE COT reports and historical CSV files](https://www.ice.com/cot-report-links)
- [ICE Commitment of Traders data product](https://developer.ice.com/fixed-income-data-services/catalog/ice-commitment-traders)
- [ICE website Terms of Use](https://www.ice.com/privacy-security-center/terms-of-use)

ICE's explanatory notes describe a combined CSV with separate records for **Futures Only** and **Futures and Options Combined**, and category definitions designed to be similar to the US CFTC Disaggregated report. The differences in exchange venue, reportability thresholds and classification practices still matter.

## Publication rights are a technical deployment gate

The ICE website Terms of Use restrict automated gathering, compilation and redistribution without appropriate authorization. A publicly downloadable report is **not equivalent to a license to systematically reproduce its historical observations on GitHub Pages**.

**Do not** copy bulk ICE records into the public GitHub CSV or HTML until permission explicitly covers this use. Authorization should address:
1. Automated download/API or bulk-file access to historical + incremental COT files.
2. Storage of a historical local database and derived metrics.
3. Display of trader-category net positions, open interest, percentiles and historical charts on a **public**, freely shareable dashboard.
4. Public distribution of historical source CSV versus derived metrics (the right may differ).
5. Required attribution, redistribution restrictions, expiry, logging, and any commercial-use limits.

If Pertamina already licenses ICE data for internal analytical use, **that does not necessarily permit republishing it publicly**. An internal-only approved export is a distinct architecture and must not silently feed this public repository.

For permission questions, use ICE market regulation contact details in the [ICE explanatory notes](https://www.ice.com/publicdocs/futures/CoT_Notes.pdf), or ICE data services through the [ICE COT product page](https://developer.ice.com/fixed-income-data-services/catalog/ice-commitment-traders).

## Ready-to-implement ingestion design — after rights approval

The current architecture already has disabled market definitions for `BRENT` (`B`) and `GASOIL` (`G`). Enable them only after all gates below have passed.

1. **Ingest** licensed ICE historical files and incremental files using the permitted transport. Keep raw source snapshots separately from normalized rows and record file checksum, source URL, retrieval time, and publication/position date when present.
2. **Normalize** to the canonical fields: `source=ICE`, `market`, `contract_code`, `contract_units`, `report_date`, `basis`, `cohort`, `long`, `short`, `spreading` and `open_interest`. Never assume ICE CSV column names without checking an actual authorized file.
3. **Validate** both Futures Only and Futures + Options Combined coverage, trader groups, non-negative OI/positions, unique keys, source-specific classification schema and product size.
4. **Backfill** at least three years (ideally the full licensed archive). Compare latest two dates with ICE's own PDF reports for Brent and Gasoil, and verify key calculations against a hand calculation.
5. **Integrate** into the common metrics engine but retain `source=ICE`. Calculate net = long − short, net/OI, changes, 1Y/3Y empirical rank. Do **not** add ICE and CFTC positions together into an "oil total".
6. **Show freshness independently**: ICE reports positions as of Tuesday and historically publish Friday London time subject to holidays. Track source-specific position dates and mismatches when comparing markets.
7. **Publish** only permitted values and derived metrics. If the license is internal-only, use a separate access-controlled dashboard; GitHub Pages is publicly accessible.
8. **Test** revision handling, missing reports, both report bases, chart/source labels and rights verification flags. If a feed fails, retain the previous verified values and display a source-staleness warning.

## Future trader-facing analysis

Once permission and backfill are confirmed, place Brent and Gasoil alongside the NYMEX contracts in the *Compare markets* page. Distinguish:
- **Crude:** NYMEX WTI versus ICE Brent (different regional benchmarks).
- **Middle distillates:** NYMEX ULSD versus ICE Gasoil (different specifications and locations).
- **Gasoline:** NYMEX RBOB (no implied substitute).
- **Relative metrics:** net/OI, report-on-report and four-week changes in net/OI percentage points, 1Y/3Y historical rank. Raw lot counts and long/short totals should always remain contract-specific.

The **default report basis remains Futures + Options Combined** in both venues, but each venue must still pass its own reconciliation.

## Current state

**No live ICE ingestion is enabled or claimed.** This document is an approved-product selection and delivery specification, not a data license or a working public ICE integration.
