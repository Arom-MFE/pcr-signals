# PCR Signals

## Overview

This repository contains Python code for computing and analyzing **put–call ratios (PCR)** on U.S. index options, with the goal of identifying **where risk and hedging pressure concentrate across expirations and maturities**.

This is **executable analysis code**, not a packaged Python library.  
Scripts are intended to be run directly, producing console output and optional **point-in-time CSV snapshots**.

All CSV files generated represent **single-moment market snapshots**. They are included only to document output structure and are not intended to be reused as datasets.

---

## Repository Structure

Single-purpose scripts for PCR computation, per-expiry analysis, signal construction, snapshot reporting, and CSV export, plus an `example_outputs/` folder containing one-time generated snapshots.

---

## What the Code Computes

The analysis separates option market information into two dimensions:

- **Flow**  
  Captured by volume-based PCR, representing current hedging demand.

- **Positioning**  
  Captured by open-interest-based PCR, representing embedded positioning.

By comparing these measures across expirations, maturity windows, and index ETFs, the code highlights **stress concentration, hedging impulses, and positioning asymmetries** along the option surface.

---

## Core Metrics and Formulas

This section documents every computed quantity, its mathematical definition, and its interpretation.

---

### 1. Put–Call Ratio (PCR)

#### Volume-based PCR

$$
\text{Volume\_PCR} = \frac{\text{Put Volume}}{\text{Call Volume}}
$$

Measures short-term **flow-driven hedging demand**.

---

#### Open-Interest-based PCR

$$
\text{OI\_PCR} = \frac{\text{Put Open Interest}}{\text{Call Open Interest}}
$$

Measures **embedded positioning** and longer-term risk exposure.

---

### 2. Flow vs Positioning Divergence

$$
\text{Divergence}_{\text{Vol−OI}} = \text{Volume\_PCR} - \text{OI\_PCR}
$$

- Positive: flow is more bearish than positioning  
- Negative: positioning is already more bearish than current flow  

This isolates **new hedging pressure versus existing inventory**.

---

### 3. Hedging Impulse

$$
\text{Impulse}_{\text{Vol/OI}} =
\begin{cases}
\frac{\text{Volume\_PCR}}{\text{OI\_PCR}}, & \text{if } \text{OI\_PCR} > 0 \\
\text{NaN}, & \text{otherwise}
\end{cases}
$$

Highlights **sudden hedging demand relative to embedded positioning**.

---

### 4. Days to Expiration (DTE)

$$
\text{DTE} = \text{Expiration Date} - \text{As-Of Date}
$$

Transforms calendar expirations into a **tradable maturity axis**, enabling term-structure analysis and clustering.

---

### 5. Event-Style Stress Score (OI-Weighted PCR)

$$
\text{EventScore}_i =
\left(
\frac{\text{Total OI}_i}{\sum_j \text{Total OI}_j}
\right)
\times \text{OI\_PCR}_i
$$

Where:
- $i$ indexes expirations
- OI share weights PCR by concentration

This highlights **expirations where large positioning coincides with skewed put–call ratios**, acting as a proxy for expiration-level stress.

---

### 6. Term-Structure Buckets

Expirations are grouped by DTE into maturity buckets (e.g. short, mid, long).  
For each bucket, the code computes:

- Total put and call volume  
- Total put and call open interest  
- Volume- and OI-based PCR  
- Share of total open interest  

This reveals **where along the maturity curve risk and hedging pressure concentrate**.

---

## Script Descriptions

### `PCR.py`

Core computation layer:
- PCR across all expiries and all strikes
- PCR across configurable DTE and strike windows
- Volume and open-interest bases only  
No ranking or interpretation logic is included.

---

### `PCR_by_expiry.py`

Per-expiry aggregation:
- Aggregates volume and open interest by expiration
- Computes per-expiry PCRs
- Optional visualization of PCR term structure

---

### `PCR_by_expiry_signals.py`

Signal construction layer:
- Adds DTE
- Computes divergence and hedging impulse
- Computes OI-weighted event stress scores
- Builds term-structure bucket summaries

---

### `PCR_snapshot_report.py`

Console-based diagnostic snapshot:
- Cross-sectional PCR comparison
- Flow vs positioning contrasts
- SPY-relative differences
- Windowed maturity summaries  
Designed for inspection, not storage.

---

### `export_pcr_datasets.py`

CSV export utility:
- Per-expiry totals with derived signals
- PCR snapshots across all maturity windows  
Files are timestamped to emphasize **point-in-time generation**.

---

## Example Outputs

The `example_outputs/` directory contains CSV files generated at a specific moment in time.  
They exist solely to document output schemas and illustrate what running the code produces.

They are **not historical datasets**.

---

## Running the Code

Typical usage:

```bash
python PCR.py
python PCR_by_expiry.py
python PCR_snapshot_report.py
python export_pcr_datasets.py
