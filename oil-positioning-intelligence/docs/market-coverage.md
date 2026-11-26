# Oil COT market coverage — research and decisions

_Last researched: 26 November 2026. These are candidate instruments, **not** additional live dashboard markets._

## How to choose a useful new series

For a public positioning dashboard, a contract should (1) measure a distinct economic exposure; (2) provide publicly verifiable Disaggregated COT data for the desired report basis; (3) have enough continuous observations and meaningful open interest for the proposed percentiles; and (4) permit the intended automated retrieval and public distribution.

**Do not combine contracts solely because their names contain "oil".** A physical crude contract, a fuel-oil outright, a refinery crack, and a fuel-oil basis spread answer different market questions.

## Existing dashboard markets

| Instrument | CFTC market code | Included? | Why |
| --- | --- | --- | --- |
| NYMEX WTI Physical | `067651` | Yes | Liquid US crude benchmark |
| NYMEX NY Harbor ULSD / historically Heating Oil | `022651` | Yes | US middle-distillate proxy; check historical product-definition breaks |
| NYMEX RBOB Gasoline | `111659` | Yes | US gasoline positioning |

The default report basis is **Disaggregated Futures and Options Combined**. Futures Only is available as an alternative and must not be added to Combined.

## Candidate additions — ranked by analytical usefulness

| Candidate | Source / identifier | What it represents | Decision |
| --- | --- | --- | --- |
| **ICE Brent** | ICE Futures Europe COT, Brent `B` | Main international crude benchmark; distinct from NYMEX Brent Last Day | **High priority**, but only after verifying automated-use and public redistribution rights |
| **ICE Low Sulphur Gasoil** | ICE Futures Europe COT, Gasoil `G` | European middle-distillate benchmark, useful against ULSD | **High priority**, same rights and data-integration gate |
| **USGC HSFO (Platts)** | CFTC `02141B`, ICE Futures Energy Division | Gulf Coast high-sulfur fuel oil-related contract | **Next CFTC candidate for controlled backfill**; not a Singapore HSFO/VLSFO series |
| **Fuel Oil 3% USGC / 3.5% FOB Rotterdam** | CFTC `02141C` | Cross-regional high-sulfur fuel-oil **basis spread** | Separate spread category only, not part of outright oil-positioning totals |
| **USGC HSFO / Brent 1st Line** | CFTC `02141R` | Fuel oil versus crude **relative-value exposure** | Separate spread category only |
| **ICE Dubai 1st Line** | ICE Europe COT reporting | Related Dubai exposures reported in an aggregation, not just outright Dubai | Defer until constituents, economic interpretation and permissions are validated |
| **NYMEX Brent Last Day** | CFTC, separate US-listed contract | Smaller contract linked to Brent; **not** the ICE Brent benchmark | Exclude from main crude view to avoid misleading proxy comparison |
| **ICE WTI** | CFTC and/or ICE reporting | Another venue's WTI exposure | Don't sum with NYMEX WTI without confirming contract scope and overlap |

CFTC report references (codes and instrument names):
- [CFTC current Disaggregated Petroleum Combined report](https://www.cftc.gov/dea/options/petroleum_sof.htm)
- [CFTC current Disaggregated Petroleum Futures Only report](https://www.cftc.gov/dea/futures/petroleum_sf.htm)
- [CFTC historical files](https://www.cftc.gov/MarketReports/CommitmentsofTraders/HistoricalCompressed/index.htm)

ICE references:
- [ICE COT historical file index](https://www.ice.com/cot-report-links)
- [ICE Futures Europe COT Report Center](https://www.ice.com/report/122)
- [ICE COT enterprise data product](https://developer.ice.com/fixed-income-data-services/catalog/ice-commitment-traders)
- [ICE website terms](https://www.ice.com/privacy-security-center/terms-of-use)
- [ICE 2023 announcement on Dubai aggregated contracts](https://www.ice.com/publicdocs/circulars/23175.pdf)

**ICE access note:** A publicly visible ICE report or CSV does not by itself establish permission to automate extraction or publish a derivative feed. Confirm contractual conditions before any live ICE-backed public dashboard integration.

## CME / QuikStrike versus CFTC

[CME QuikStrike's Commitment of Traders tool](https://www.cmegroup.com/tools-information/quikstrike/commitment-of-traders.html) visualizes **CFTC** COT disclosures. It is useful for checking charts and definitions, but isn't an independent set of positions to add to the CFTC records. Treat it as a secondary cross-check, not a parallel source to be summed.

## Implementation gates before enabling another instrument

1. Confirm its exact source/exchange and stable contract code from official publications.
2. Programmatically query **both Combined and Futures Only** records using the existing CFTC schema adapter (if CFTC-reported).
3. Backfill sufficient history to compute the 1Y/3Y percentiles causally; a 90-day refresh is **not** a substitute for a historical backfill.
4. Reconcile at least two observed reporting dates against the CFTC's published contract report, including the open-interest units and trader groups.
5. Inspect historical series breaks, code/name changes, and potential contract definition changes.
6. Flag outright versus basis spread exposure explicitly. Do not mix spread positions into a sum of outright directional positions.
7. Only then turn the market on in `src/oilcot/config.py`, document the coverage, and rerun the full historical backfill and validation.
8. For non-CFTC data sources, verify permitted retrieval, storage and redistribution before publication.

For fuel-oil desk work, the USGC HSFO series could provide **supplementary positioning context**, but should never be presented as direct evidence of Singapore bunker demand or the Singapore 380cst/VLSFO market.
