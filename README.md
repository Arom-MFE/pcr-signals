# PCR Signals

A Python-based quantitative tool for computing put–call ratios (PCR) on index ETFs and analyzing where hedging pressure and downside risk concentrate across expirations and maturity buckets.

This repository provides **code-first analytical tooling** for option market diagnostics. It is not a packaged library and does not attempt to generate forecasts or trading signals. The outputs are descriptive snapshots of option market structure at the time the code is run.

---

## Overview

The core goal of this project is to decompose index option activity into:

- **Flow** (volume-based activity)
- **Positioning** (open-interest-based exposure)
- **Maturity structure** (where risk sits along the expiration curve)

These dimensions are combined into interpretable metrics that highlight:
- where hedging demand is strongest,
- where downside risk is concentrated,
- how current flow compares to existing dealer inventory.

All option data is sourced live via `yfinance`. Any CSV files included in this repository are **example outputs only**, representing a single snapshot in time.

---

## Covered Symbols and What They Represent

Default symbols used across the scripts:

- **SPY**: S&P 500 (broad US large-cap equity market)
- **QQQ**: Nasdaq-100 (US large-cap, growth/technology-heavy)
- **DIA**: Dow Jones Industrial Average (US large-cap, industrial/blue-chip tilt)
- **IWM**: Russell 2000 (US small-cap)
- **XLF**: Financials sector (banks, insurers, diversified financials)
- **KRE**: Regional banks (US regional banking industry)

These are used as liquid, widely-traded option underlyings to compare how hedging demand and positioning differ across broad market and sector exposures.

---

## Core Metrics and Formulas

### 1) Put–Call Ratio (PCR)

Two versions of PCR are computed because they represent different economic forces.

**Volume-based PCR**

PCRᵛᵒˡ = Put Volume / Call Volume

- Captures short-term, flow-driven hedging demand
- Sensitive to events, macro releases, and intraday positioning

**Open-interest-based PCR**

PCRᴼᴵ = Put Open Interest / Call Open Interest

- Captures embedded positioning and longer-horizon exposure
- Reflects risk already sitting on dealer balance sheets

These are intentionally kept separate rather than combined into a single number.

---

### 2) Flow vs Positioning Divergence 

Divergenceᵛᵒˡ⁻ᴼᴵ = PCRᵛᵒˡ − PCRᴼᴵ  

Interpretation:
- Positive values indicate new flow is more put-heavy than existing positioning
- Negative values indicate positioning is already more put-heavy than current flow

This helps distinguish **new hedging demand** from **legacy risk**.

---

### 3) Hedging Impulse

Impulseᵛᵒˡ⁄ᴼᴵ = PCRᵛᵒˡ / PCRᴼᴵ

This ratio measures how aggressive current flow is relative to the existing positioning baseline.

Interpretation:
- Values well above 1 indicate unusually strong hedging pressure
- Values near or below 1 indicate flow consistent with existing exposure

---

### 4) Event Score (Stress Concentration Proxy)

To identify expirations that matter most, the project computes:

EventScoreᵢ = (TotalOIᵢ / Σⱼ TotalOIⱼ) × PCRᴼᴵᵢ

Interpretation:
- Highlights expirations that are both large in size and heavily skewed toward puts
- Serves as a simple proxy for concentrated downside risk or event sensitivity

This metric is designed to be transparent and interpretable.

---

## Per-Expiry Analysis (Term Structure)

For each symbol, option data is aggregated **separately for each expiration date**.

Computed per expiration:
- total put volume
- total call volume
- volume-based PCR
- total put open interest
- total call open interest
- open-interest-based PCR
- total open interest
- days to expiration (DTE)

This produces a clean expiration-by-expiration view of where risk sits along the curve.

---
## Term-Structure Buckets (Non-Overlapping)

This is an **additional term-structure summary layer** on top of the full per-expiry analysis. The code still computes metrics **for every individual expiration**; the bucketed view is simply a **non-overlapping aggregation** to make the curve easier to interpret at a glance. (In other words: not everything is “grouped into buckets” and nothing is lost, this is just a second lens.)

Expirations are grouped into **non-overlapping maturity buckets** based on days to expiration:

- Short_1_20 → DTE 1–20  
- Mid_21_60 → DTE 21–60  
- Long_61_120 → DTE 61–120  

For each bucket, the following are computed:
- total put open interest
- total call open interest
- bucket-level OI PCR
- total put volume
- total call volume
- bucket-level volume PCR
- total open interest in bucket
- share of total open interest represented by the bucket

These buckets provide a clean view of how risk is distributed across near-term, medium-term, and longer-dated horizons, while the **per-expiry table remains the primary, fully granular output**.

---

## Quality Filters

To reduce noise from illiquid expirations, per-expiry signal calculations apply minimum thresholds (defaults):

- minimum call open interest: **min_call_oi = 1000**
- minimum call volume: **min_call_vol = 500**
- minimum total open interest: **min_total_oi = 10,000**

Only expirations meeting these thresholds are flagged as `Quality_OK`.


---

## Snapshot Windows (Cross-Sectional PCR)

In addition to “all expiries / all strikes,” the project computes **windowed** PCRs to isolate where hedging/positioning is concentrated on the curve.

Windows are defined by:
- **DTE window**: 1–20, 21–60, 61–120
- **Strike filter**: options within ±`strike_pct` of spot

This produces comparable cross-sectional tables across symbols for both:
- volume-based PCR (flow)
- open-interest-based PCR (positioning)

---

## Market Map vs SPY (Relative Pressure)

The snapshot report also produces a simple **relative market map vs SPY**:

- Δ Volume PCR vs SPY  
- Δ OI PCR vs SPY  
- Δ Divergence vs SPY  

Interpretation:
- Positive deltas indicate more put-heavy pressure than SPY on that dimension
- Helps identify where hedging demand or embedded downside skew is unusually concentrated relative to broad market baseline

---

## Exported Datasets

The project can export two CSV datasets for downstream analysis:

1) **Per-expiry totals with signals**  
One row per expiration per symbol, including DTE, PCRs, impulse, event score, and quality flag.

2) **Snapshot PCR across all windows**  
One row per symbol per window per basis (volume or open interest), including strike filter and DTE window metadata.

These files are **snapshots generated at runtime**, not persistent datasets.

---

## Output Schema (CSV)

### 1) Per-expiry totals with signals (`per_expiry_totals_with_signals__YYYY-MM-DD.csv`)

| Column | Meaning |
|---|---|
| Symbol | Underlying ticker (e.g., SPY) |
| Expiry | Option expiration date |
| DTE | Days to expiration |
| Put_Volume | Total put volume at expiry |
| Call_Volume | Total call volume at expiry |
| Volume_PCR | Put_Volume / Call_Volume |
| Put_OI | Total put open interest at expiry |
| Call_OI | Total call open interest at expiry |
| OI_PCR | Put_OI / Call_OI |
| Total_OI | Put_OI + Call_OI |
| Divergence_Vol_minus_OI | Volume_PCR − OI_PCR |
| Impulse_Vol_over_OI | Volume_PCR / OI_PCR |
| EventScore_OIshare_x_OI_PCR | (Total_OI / sum(Total_OI)) × OI_PCR |
| Quality_OK | Liquidity/quality threshold pass flag |

### 2) Snapshot PCR across all windows (`pcr_snapshot_all_windows__YYYY-MM-DD.csv`)

| Column | Meaning |
|---|---|
| Symbol | Underlying ticker |
| Basis | `volume` or `openInterest` |
| Window | `ALL` or a named DTE window |
| DTE_Min | Lower DTE bound (if windowed) |
| DTE_Max | Upper DTE bound (if windowed) |
| StrikePct | Strike filter around spot (e.g., 0.10 = ±10%) |
| Put | Aggregated put metric for the basis (volume or OI) |
| Call | Aggregated call metric for the basis (volume or OI) |
| PCR | Put / Call for that window + basis |
| AsOf | Snapshot date |
| RunTS | Runtime timestamp identifier |

---

## Files, Roles, and Key Functions

### `PCR.py` — PCR Engine (All expiries + windowed)
Computes PCR values in two ways:
- aggregated across **all expiries / all strikes**
- aggregated within **DTE windows** and **±strike% filters**

Key variables:
- `DEFAULT_SYMBOLS` (default ETF universe)
- `WINDOW_SPECS` (DTE windows + strike filters)
- `BASES` (`volume`, `openInterest`)

Key functions:
- `_get_spot(tk)`  
  Fetches spot price robustly (fast_info first, then fallback).
- `pcr_all_expiries_all_strikes(symbol, basis)`  
  Aggregates puts/calls across all expiries and strikes for a given basis.
- `pcr_windowed(symbol, basis, dte_min, dte_max, strike_pct, window_name)`  
  Aggregates puts/calls only for expiries in the DTE window and strikes within ±`strike_pct` of spot.
- `pcr_for_symbols_all(symbols)`  
  Runs all-expiry/all-strike PCR for each symbol for both bases.
- `pcr_for_symbols_multiwindow(symbols, windows)`  
  Runs windowed PCR across all windows, symbols, and bases.

Outputs:
- DataFrames that feed the snapshot reporting logic.

---

### `PCR_snapshot_report.py` — Snapshot Tables (Cross-Index Comparisons)
Takes the raw PCR rows produced by `PCR.py` and formats them into clean cross-sectional tables.

Key functions:
- `flow_vs_positioning_divergence(df)`  
  Pivots PCR rows to wide form (Volume vs OI) and computes divergence:
  - `Divergence_Vol_minus_OI = PCR_Volume - PCR_OpenInterest`
- `add_hedging_impulse(df_formatted)`  
  Adds:
  - `Impulse_Vol_over_OI = PCR_Volume / PCR_OpenInterest`
- `add_deltas_vs_spy(df_formatted)`  
  Adds:
  - `ΔVolume vs SPY`, `ΔOI vs SPY`, `ΔDivergence vs SPY`
- `_format_snapshot_table(title, df_raw, symbols=None)`  
  Builds a user-facing snapshot table with metadata + PCR + divergence + impulse.
- `print_snapshot_report(symbols=None)`  
  Prints snapshot table for:
  - All expiries / all strikes
  - Each window in `WINDOW_SPECS`

Outputs:
- Printed tables suitable for quick inspection and copy-paste, plus a “market map vs SPY.”

---

### `PCR_by_expiry.py` — Per-Expiry Aggregation (Raw Term Structure)
Aggregates total option activity **per expiration** for each symbol.

Key functions:
- `per_expiry_totals(symbol, max_expiries=None)`  
  For each expiry, aggregates:
  - Put_Volume, Call_Volume, Volume_PCR
  - Put_OI, Call_OI, OI_PCR
  - Total_OI
- `top_expiries_by_oi_pcr(df, top_n=5)`  
  Returns the top expiries ranked by OI-based PCR.
- `plot_pcrs_by_expiry(df, title=None)`  
  Side-by-side bar chart: Volume_PCR vs OI_PCR across expiries.
- `report_per_expiry(symbol, max_expiries=None, top_n=5, plot=True)`  
  Prints per-expiry totals + top expiries + optional plot.
- `run_reports(symbols=DEFAULT_SYMBOLS, ...)`  
  Runs per-expiry report for a list of symbols.

Outputs:
- A per-expiry DataFrame for each symbol and a basic comparison plot.

---

### `PCR_by_expiry_signals.py` — Signal Layer on Top of Per-Expiry Data
Adds DTE, quality flags, and the main “stress concentration” metrics on top of per-expiry totals.

Key functions:
- `_to_num(s)`  
  Numeric coercion helper used to keep calculations stable.
- `add_dte(df, asof=None)`  
  Adds `DTE` (days to expiration).
- `add_flow_vs_positioning(df)`  
  Adds:
  - `Divergence_Vol_minus_OI = Volume_PCR - OI_PCR`
  - `Impulse_Vol_over_OI = Volume_PCR / OI_PCR`
- `add_quality_flags(df, min_call_oi=..., min_call_vol=..., min_total_oi=...)`  
  Adds `Quality_OK` boolean to filter illiquid expiries.
- `add_event_score(df)`  
  Adds:
  - `EventScore_OIshare_x_OI_PCR = (Total_OI / sum(Total_OI)) * OI_PCR`
- `bucket_term_structure(df, buckets=[...], require_quality_ok=True)`  
  Computes non-overlapping DTE bucket aggregates and `Bucket_TotalOI_Share`.
- `enrich_per_expiry(symbol, max_expiries=None, ...)`  
  Orchestrates per-symbol pipeline:
  `per_expiry_totals → add_dte → add_flow_vs_positioning → add_quality_flags → add_event_score`
- `print_symbol_top_section(symbol, df, top_n=5, plot=True)`  
  Prints top expiries by:
  - OI_PCR
  - Impulse_Vol_over_OI
  - Divergence_Vol_minus_OI
  - EventScore_OIshare_x_OI_PCR  
  plus maturity buckets.

Outputs:
- A fully enriched per-expiry dataset per symbol plus a term-structure bucket summary.

---

### `export_pcr_datasets.py` — CSV Export (Two Datasets at Once)
Generates two clean, analysis-ready datasets and writes them to CSV.

Key functions:
- `build_per_expiry_signals_dataset(symbols, asof, run_ts, max_expiries=None)`  
  Creates a combined per-expiry dataset across symbols (one row per expiry per symbol).
- `build_snapshot_dataset(symbols, asof, run_ts)`  
  Creates combined snapshot dataset (ALL + all window specs, per symbol and basis).
- `export_pcr_datasets(symbols=None, asof=None, max_expiries=None, out_dir=".", ...)`  
  Builds both datasets and writes two CSV files.
- `main()`  
  Example runner that writes both CSV files and prints file paths + row counts.

Outputs:
- Two CSVs (schemas designed for downstream research).

---

## Example Outputs

`example_outputs/` contains example CSV outputs generated at a single point in time.

Typical files:
- `per_expiry_totals_with_signals__YYYY-MM-DD.csv`
- `pcr_snapshot_all_windows__YYYY-MM-DD.csv`

These are included to show:
- schema
- column naming
- how downstream users can ingest the data

They are not meant to be treated as a historical dataset.

---

## Data Notes

All outputs reflect market conditions **at the time the code is executed**.  
`yfinance` availability and option chain completeness depend on the upstream data source and may vary across symbols and expirations.
