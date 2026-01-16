# PCR Signals

## Overview

This repository contains Python code for computing and analyzing **put–call ratios (PCR)** on U.S. index options, with a focus on identifying **where risk and hedging pressure concentrate across option expirations and maturities**.

The project is designed as **executable analysis code**, not as a packaged Python library.  
Users run the scripts directly, inspect console output, and optionally export **point-in-time CSV snapshots**.

All CSV files produced by this code represent **single-moment snapshots** of the options market at runtime.  
They are included only to document output structure and should not be treated as reusable datasets.

---

## What This Code Computes

The code separates options market information into two distinct dimensions:

1. **Flow**
   - Measured using **volume-based put–call ratios**
   - Reflects *current hedging demand*

2. **Positioning**
   - Measured using **open-interest-based put–call ratios**
   - Reflects *embedded, longer-term positioning*

By comparing these measures across:
- expiration dates,
- maturity windows (DTE buckets),
- and index ETFs,

the code highlights **where stress, hedging demand, and positioning are concentrated** along the option surface.

---

## Repository Structure
pcr-signals/
│
├── PCR.py
│ Core PCR computations across all expiries and maturity windows
│
├── PCR_by_expiry.py
│ Per-expiry aggregation and visualization
│
├── PCR_by_expiry_signals.py
│ Derived per-expiry signals and metrics
│
├── PCR_snapshot_report.py
│ Console-based cross-sectional snapshot report
│
├── export_pcr_datasets.py
│ Exports snapshot CSV outputs
│
├── example_outputs/
│ Example CSVs generated at a single point in time
│
└── README.md


---

## Core Metrics and Formulas

This section documents **every calculated quantity**, its formula, and where it is implemented.

---

### 1. Put–Call Ratio (PCR)

#### Volume-based PCR

\[
\text{Volume\_PCR} = \frac{\text{Put Volume}}{\text{Call Volume}}
\]

- Measures *current flow* and short-term hedging demand.
- Implemented in:
  - `PCR.py`
  - `PCR_by_expiry.py`

---

#### Open-Interest-based PCR

\[
\text{OI\_PCR} = \frac{\text{Put Open Interest}}{\text{Call Open Interest}}
\]

- Measures *embedded positioning*.
- Implemented in:
  - `PCR.py`
  - `PCR_by_expiry.py`

---

### 2. Divergence Between Flow and Positioning

\[
\text{Divergence}_{\text{Vol−OI}} = \text{Volume\_PCR} - \text{OI\_PCR}
\]

- Positive values indicate flow is more bearish than positioning.
- Negative values indicate positioning is already bearish relative to flow.
- Implemented in:
  - `PCR_by_expiry_signals.py`
  - `PCR_snapshot_report.py`

---

### 3. Hedging Impulse (Flow Over Positioning)

\[
\text{Impulse}_{\text{Vol/OI}} =
\begin{cases}
\frac{\text{Volume\_PCR}}{\text{OI\_PCR}}, & \text{if } \text{OI\_PCR} > 0 \\
\text{NaN}, & \text{otherwise}
\end{cases}
\]

- Highlights **short-term hedging surges** relative to existing positioning.
- Implemented in:
  - `PCR_by_expiry_signals.py`
  - `PCR_snapshot_report.py`

---

### 4. Days to Expiration (DTE)

\[
\text{DTE} = (\text{Expiration Date} - \text{As-Of Date})
\]

- Converts calendar expirations into a tradable maturity axis.
- Used for term-structure analysis and clustering.
- Implemented in:
  - `PCR_by_expiry_signals.py`

---

### 5. Event-Style Stress Score (OI-Weighted PCR)

\[
\text{EventScore}_{i} =
\left(
\frac{\text{Total OI}_{i}}{\sum_j \text{Total OI}_{j}}
\right)
\times \text{OI\_PCR}_{i}
\]

Where:
- \(i\) indexes expirations
- the OI share weights PCR by concentration

This metric highlights **where large positioning coincides with skewed put–call ratios**, acting as a proxy for expiration-level stress.

- Implemented in:
  - `PCR_by_expiry_signals.py`

---

### 6. Term-Structure Buckets

Expirations are grouped by DTE into predefined maturity buckets (e.g. short, mid, long).

For each bucket:
- total put/call volume
- total put/call open interest
- PCRs
- open-interest share

This reveals **where along the maturity curve risk is concentrated**.

- Implemented in:
  - `PCR_by_expiry_signals.py`

---

## Script-Level Description

### `PCR.py`

Core computation layer.

- Computes PCR across:
  - all expiries / all strikes
  - DTE and strike-filtered windows
- Supports both volume and open interest
- Defines maturity window specifications

No interpretation or ranking logic is included.

---

### `PCR_by_expiry.py`

Expiration-level aggregation.

For each expiration:
- sums put and call volume
- sums put and call open interest
- computes PCRs
- optionally plots PCR term structure

---

### `PCR_by_expiry_signals.py`

Derived per-expiry metrics.

Adds:
- DTE
- flow vs positioning divergence
- hedging impulse
- OI-weighted stress scores
- term-structure bucket summaries

---

### `PCR_snapshot_report.py`

Console-based snapshot diagnostics.

- Cross-sectional PCR comparison
- SPY-relative differences
- Flow vs positioning comparison
- Windowed maturity analysis

Designed for **inspection**, not storage.

---

### `export_pcr_datasets.py`

Snapshot CSV export utility.

Produces:
1. Per-expiry totals with derived signals
2. PCR snapshots across all maturity windows

Files are timestamped to emphasize **point-in-time generation**.

---

## Example Outputs

The `example_outputs/` directory contains CSV files generated at a specific moment in time.

They exist to:
- document output schemas
- illustrate column meanings
- show what running the code produces

They are **not historical datasets** and are not intended for reuse.

---

## Running the Code

Typical usage:

```bash
python PCR.py
python PCR_snapshot_report.py
python PCR_by_expiry.py
python export_pcr_datasets.py

