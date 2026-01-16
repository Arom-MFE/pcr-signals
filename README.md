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

