# PCR Signals

## Overview

This repository contains Python code for computing and analyzing **Put–Call Ratios (PCR)** on U.S. index options, with the goal of identifying **where risk and hedging pressure concentrate across expirations and maturities**.

This is **executable analysis code**, not a packaged Python library. Scripts are intended to be run directly, producing console output and optional **point-in-time CSV snapshots**. 

All CSV files generated represent **single-moment market snapshots**. They are included only to document output structure and are not intended to be reused as datasets.

---

## Repository Structure
pcr-signals/ ├── PCR.py # Core PCR computations (all expiries/maturity windows) ├── PCR_by_expiry.py # Per-expiry aggregation and visualization ├── PCR_by_expiry_signals.py # Derived per-expiry signals and impulse metrics ├── PCR_snapshot_report.py # Console-based cross-sectional snapshot report ├── export_pcr_datasets.py # Utility to export snapshots to CSV ├── example_outputs/ # Example CSVs generated at a single point in time └── README.md # Documentation and metric definitions
---
---

## What the Code Computes

The analysis separates option market information into two dimensions:

* **Flow**: Captured by volume-based PCR, representing current hedging demand.
* **Positioning**: Captured by open-interest-based PCR, representing embedded positioning.

By comparing these measures across expirations, maturity windows, and index ETFs, the code highlights **stress concentration, hedging impulses, and positioning asymmetries** along the option surface.



---

## Core Metrics and Formulas

### 1. Put–Call Ratio (PCR)

**Volume-based PCR**

$$\text{Volume\_PCR} = \frac{\text{Put Volume}}{\text{Call Volume}}$$

Measures short-term **flow-driven hedging demand**.

**Open-Interest-based PCR**

$$\text{OI\_PCR} = \frac{\text{Put Open Interest}}{\text{Call Open Interest}}$$

Measures **embedded positioning** and longer-term risk exposure.

---

### 2. Flow vs Positioning Divergence

$$\text{Divergence}_{\text{Vol-OI}} = \text{Volume\_PCR} - \text{OI\_PCR}$$

* **Positive**: Flow is more bearish than existing positioning.
* **Negative**: Positioning is already more bearish than current flow.

This isolates **new hedging pressure versus existing inventory**.

---

### 3. Hedging Impulse

$$\text{Impulse}_{\text{Vol/OI}} = \begin{cases} \frac{\text{Volume\_PCR}}{\text{OI\_PCR}}, & \text{if } \text{OI\_PCR} > 0 \\ \text{NaN}, & \text{otherwise} \end{cases}$$

Highlights **sudden hedging demand relative to embedded positioning**.

---

### 4. Days to Expiration (DTE)

$$\text{DTE} = \text{Expiration Date} - \text{As-Of Date}$$

Transforms calendar expirations into a **tradable maturity axis**, enabling term-structure analysis and clustering.

---

### 5. Event-Style Stress Score (OI-Weighted PCR)

$$\text{EventScore}_i = \left( \frac{\text{Total OI}_i}{\sum_j \text{Total OI}_j} \right) \times \text{OI\_PCR}_i$$

Where:
* $i$ indexes specific expirations.
* The first term represents the **OI Share**, weighting the PCR by concentration.

This highlights **expirations where large positioning coincides with skewed put–call ratios**, acting as a proxy for expiration-level stress.

---

### 6. Term-Structure Buckets

Expirations are grouped by DTE into maturity buckets (e.g., Short, Mid, Long). For each bucket, the code computes:
* Total Put and Call Volume / Open Interest.
* Volume- and OI-based PCR.
* Bucket share of total Open Interest.

This reveals **where along the maturity curve risk and hedging pressure concentrate**.

---

## Script Descriptions

### `PCR.py`
**Core computation layer:**
* Calculates PCR across all expiries and all strikes.
* Calculates PCR across configurable DTE and strike windows (e.g., $\pm10\%$).
* Provides the base logic for Volume and Open Interest extraction.

### `PCR_by_expiry.py`
**Per-expiry aggregation:**
* Aggregates volume and open interest by specific expiration dates.
* Computes per-expiry PCRs.
* Provides optional visualization of the PCR term structure.

### `PCR_by_expiry_signals.py`
**Signal construction layer:**
* Calculates DTE for all rows.
* Computes **Divergence** and **Hedging Impulse**.
* Calculates **OI-weighted Event Stress Scores**.
* Generates term-structure bucket summaries.

### `PCR_snapshot_report.py`
**Console-based diagnostic:**
* Cross-sectional PCR comparisons across indices (SPY, QQQ, IWM, etc.).
* Flow vs. Positioning contrasts.
* Relative differences compared to SPY.

### `export_pcr_datasets.py`
**CSV export utility:**
* Exports per-expiry totals with derived signals.
* Exports PCR snapshots across all defined maturity windows.
* Files are timestamped to emphasize point-in-time generation.

---

## Example Outputs

The `example_outputs/` directory contains CSV files generated at a specific moment in time. They exist solely to document output schemas and illustrate what running the code produces.

They are **not historical datasets**.

---

## Running the Code

Ensure you have the dependencies installed. Run the scripts directly from the terminal:

```bash
python PCR.py
python PCR_by_expiry.py
python PCR_snapshot_report.py
python export_pcr_datasets.py
