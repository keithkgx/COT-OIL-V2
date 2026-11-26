# Oil Positioning Intelligence

**A free, public dashboard for understanding speculative positioning in major oil futures markets.** Built from official [CFTC Commitments of Traders (COT)](https://www.cftc.gov/MarketReports/CommitmentsofTraders/index.htm) data, updated automatically by GitHub Actions.

**[Open the interactive dashboard](https://keithkgx.github.io/COT-OIL-V2/)** · [Data & methodology](https://keithkgx.github.io/COT-OIL-V2/) (third tab) · [Market coverage research](oil-positioning-intelligence/docs/market-coverage.md) · [ICE Brent & Gasoil integration plan](oil-positioning-intelligence/docs/ice-brent-gasoil-integration.md)

> **What this is:** a historical snapshot of reportable traders' futures and options positioning. **What it is not:** live order flow, individual trader activity, or a trading signal. The displayed date is the **position date**, not necessarily the publication date.

## What can you do?

The site is organized around the questions a market analyst would ask:

1. **Where are traders positioned?** Net contracts (long − short), total open interest, net position as a share of OI, and historical net/OI percentile.
2. **How did they get there?** Switch the history chart between long, short and net contracts, net/OI, and the rolling three-year net/OI percentile.
3. **What's driving the change?** Break down the latest move in contracts by long and short holdings, then see how holdings and open interest each contributed to the net/OI change.
4. **How does participation look?** Total open interest and positions by CFTC trader group.
5. **How do related markets compare?** **Compare markets** plots historical rank against four-week net/OI change and compares shifts over matching date intervals.

Select an **as-of position date**, instrument, participant category, report basis, and historical window. The CSV on **Data & methodology** includes every observation that matches these filters.

## Current coverage

| Market | Exchange | Source | CFTC code |
| --- | --- | --- | --- |
| WTI Crude | NYMEX | CFTC Disaggregated | `067651` |
| ULSD / Heating Oil | NYMEX | CFTC Disaggregated | `022651` |
| RBOB Gasoline | NYMEX | CFTC Disaggregated | `111659` |

**Default:** Managed Money; **Futures and Options Combined** (delta-adjusted options included). Futures Only is available as an alternative, but the two report bases overlap and should **not** be added together.

**Not currently included:** main ICE Brent or ICE Low Sulphur Gasoil benchmarks. Direct ICE automation and redistribution require authorized data access. Other CFTC-reported fuel-oil-linked contracts are being assessed separately; spreads should not be presented as outright crude or fuel oil directional bets. See the [research note](oil-positioning-intelligence/docs/market-coverage.md).

## How data updates

The public site is a **static, self-contained HTML dashboard**. It uses no login, server-side analytics or live browser API requests.

- GitHub Actions is scheduled to check for new official CFTC observations daily at 06:37 and 12:37 Singapore time.
- Python computes positioning, OI-normalized measures and causal historical percentiles.
- A generated standalone HTML file is committed in [`dashboard/index.html`](oil-positioning-intelligence/dashboard/index.html) and deployed through GitHub Pages.
- A scheduled check can succeed even when there is no new position observation. The **latest position date** is shown on the site.

The pipeline and source code are available in the [project folder](oil-positioning-intelligence/). For installation, commands, tests and data definitions, see the [developer guide](oil-positioning-intelligence/README.md).

## Interpreting the numbers

- **Net position:** long − short contracts for the selected participant category.
- **Net / OI:** net position divided by all-market open interest, expressed as a percentage.
- **3Y rank:** where the selected net/OI stands relative to the contract's trailing weekly-equivalent historical readings. A high percentile does *not* imply a large position in absolute terms.
- **Change attribution:** `Δ net = Δ long − Δ short`. These are changes in reported holdings, **not observed transactions**.
- **Report-on-report:** compares with the previous published **observation**, which is not always exactly seven days prior.
- **Cross-market comparison:** contracts can differ in size, liquidity, trader mix, underlying exposure and reporting coverage. Net/OI is more comparable than raw counts, but it is not a measure of price conviction.

Sources: [CFTC COT](https://www.cftc.gov/MarketReports/CommitmentsofTraders/index.htm) · [CFTC public reporting environment](https://publicreporting.cftc.gov/stories/s/r4w3-av2u) · [explanatory notes](https://www.cftc.gov/MarketReports/CommitmentsofTraders/ExplanatoryNotes/index.htm).

## Repository layout

```text
.github/workflows/update-cot.yml                  Scheduled refresh + GitHub Pages deployment
oil-positioning-intelligence/
  src/oilcot/                                     CFTC retrieval, normalization, calculations
  templates/dashboard.html                       Dashboard source template
  data/cot_history.csv                           Historical CFTC observations
  dashboard/index.html                           Generated standalone website
  docs/market-coverage.md                        Further contracts and source research
  tests/                                         Automated checks
  README.md                                      Developer / operations guide
```

The project folder is retained for compatibility with the existing automation.

## Public-data and project disclaimer

This is an independent open-repository research dashboard, **not an official CFTC, CME, ICE or employer product**, and it is not affiliated with or endorsed by those organizations. Nothing on the site is investment advice. No proprietary desk data or API credentials should be committed to this repository.

**Contributing:** Issues and suggested improvements are welcome. This repository does not currently declare an open-source license; publishing code on GitHub does not automatically grant permission to redistribute it.
