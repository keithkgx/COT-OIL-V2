# Add ICE Brent and Low Sulphur Gasoil

Use the **ICE Futures Europe Financial Commitments of Traders** export for these two markets.

| Contract | COT code | Contract size | Comparison |
| --- | --- | --- | --- |
| ICE Brent Crude | `B` | 1,000 barrels | NYMEX WTI |
| ICE Low Sulphur Gasoil | `G` | 100 metric tonnes | NYMEX ULSD |

The financial report includes positions by category and separates Futures Only from Futures and Options Combined. Keep the two bases separate in the export. ICE and CFTC use similar categories, with differences in reporting thresholds and exchange coverage.

[ICE Financial COT explanatory notes](https://www.ice.com/publicdocs/futures/CoT_Notes.pdf) · [ICE COT reports](https://www.ice.com/cot-report-links) · [ICE Data Services COT product](https://developer.ice.com/fixed-income-data-services/catalog/ice-commitment-traders)

## Build a local dashboard

1. Obtain an ICE export your data agreement allows you to use for local analytics. Ask your ICE account or market-data administrator for historical and recent observations for `B` and `G`, covering the intended report bases. For three-year ranks with a full lookback, obtain at least three years of observations plus any earlier history needed for the analysis window.
2. Map the export to the CSV layout below. Save the CSV outside the Git checkout. You can supply more than one file by repeating `--ice-data`.
3. Use the Python environment from the [developer guide](../README.md). From the `oil-positioning-intelligence` folder, run the command for your operating system.

**Windows PowerShell**

```powershell
$env:PYTHONPATH = "src"
python -m oilcot.cli build-private --ice-data "C:\OilCOT\ice-cot.csv" --output "C:\OilCOT\oil-cot-private.html"
Invoke-Item "C:\OilCOT\oil-cot-private.html"
```

**macOS / Linux**

```bash
PYTHONPATH=src python -m oilcot.cli build-private --ice-data ~/OilCOT/ice-cot.csv --output ~/OilCOT/oil-cot-private.html
```

Open the resulting HTML in a browser. The **Market** dropdown lists each imported ICE contract alongside the CFTC markets. **Compare markets** adds the crude and distillate pairs when the corresponding ICE contract is available. The header shows the latest position date in each source, and the comparison can jump back to the latest position date shared by all markets in the selected view. Rankings of changes also require matching reference dates.

The local build reads the CFTC history already in the repository, unless you specify an alternative with `--data`. To update it, refresh the CFTC history, add new authorized ICE observations to your input, then rerun `build-private`. The generated HTML embeds the observations and runs offline.

## CSV layout

Use UTF-8 CSV with these column names. The importer expects this normalized layout. ICE Connect, licensed API or bulk delivery, and annual exchange files may use a different export layout.

```csv
contract_code,report_date,basis,cohort,long,short,spreading,open_interest
```

| Field | Accepted value |
| --- | --- |
| `contract_code` | `B` or `G` |
| `report_date` | Position date in `YYYY-MM-DD` format |
| `basis` | `combined` or `futures` |
| `cohort` | `Producer/Merchant`, `Swap Dealers`, `Managed Money`, or `Other Reportables` |
| `long`, `short` | Reported directional contract counts |
| `spreading` | Reported spreading contracts, or blank where unavailable or inapplicable |
| `open_interest` | Total market open interest for this contract, date and basis. Repeat the same value for all four categories. |

Include one row per trader category for each available contract, position date and basis. In a wide export, one exchange report becomes four rows by placing each category's long, short and spreading columns into the common fields. The importer accepts identical overlaps between files and reports conflicting observations so you can select the correct revision. Reconcile two recent dates against ICE's reports before relying on a new mapping.

## Public display and automation

The GitHub Pages build uses CFTC data. Before adding ICE series to the public site, obtain written confirmation that your agreement permits automated access, historical storage and public display of the specific fields and derived charts you plan to share. Ask separately about downloadable history, since those rights can differ from chart display. ICE offers API and bulk delivery under its data services. Its official COT notes also provide the Market Regulation contact for report questions.

After the approved delivery and usage are confirmed, map the licensed feed, reconcile it with source reports, and then enable the approved outputs in the public build. For current report access and terms, see [ICE COT Data Services](https://developer.ice.com/fixed-income-data-services/catalog/ice-commitment-traders), [report notes](https://www.ice.com/publicdocs/futures/CoT_Notes.pdf), and [ICE website terms](https://www.ice.com/privacy-security-center/terms-of-use).
