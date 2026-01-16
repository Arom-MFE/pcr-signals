from __future__ import annotations

from datetime import date, datetime
from typing import Iterable, Optional, Tuple

import numpy as np
import pandas as pd

from PCR_by_expiry import (
    DEFAULT_SYMBOLS as DEFAULT_SYMBOLS_BY_EXPIRY,
    per_expiry_totals,
)

from PCR import (
    DEFAULT_SYMBOLS as DEFAULT_SYMBOLS_SNAPSHOT,
    WINDOW_SPECS,
    pcr_for_symbols_all,
    pcr_for_symbols_multiwindow,
)


def _to_num(x) -> pd.Series:
    return pd.to_numeric(x, errors="coerce")


# =========================
# Dataset 1: Per-expiry totals + signals
# =========================
def _add_dte(df: pd.DataFrame, asof: date) -> pd.DataFrame:
    out = df.copy()
    exp = pd.to_datetime(out["Expiry"], errors="coerce").dt.date
    out["DTE"] = exp.map(lambda d: (d - asof).days if d is not None else np.nan)
    out["DTE"] = _to_num(out["DTE"])
    return out


def _add_impulse_vol_over_oi(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    v = _to_num(out["Volume_PCR"])
    oi = _to_num(out["OI_PCR"])

    out["Impulse_Vol_over_OI"] = np.where(
        (oi > 0) & np.isfinite(oi) & np.isfinite(v),
        v / oi,
        np.nan,
    )
    out["Impulse_Vol_over_OI"] = _to_num(out["Impulse_Vol_over_OI"]).round(6)
    return out


def _add_event_score_oi_share_x_oi_pcr(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    tot_oi = _to_num(out["Total_OI"]).fillna(0.0)
    denom = float(tot_oi.sum())

    if denom <= 0:
        out["EventScore_OIshare_x_OI_PCR"] = np.nan
        return out

    share = tot_oi / denom
    oi_pcr = _to_num(out["OI_PCR"])
    out["EventScore_OIshare_x_OI_PCR"] = (share * oi_pcr).round(8)
    return out


def build_per_expiry_signals_dataset(
    symbols: Iterable[str],
    asof: date,
    run_ts: str,
    max_expiries: Optional[int] = None,
) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []

    for sym in list(symbols):
        df = per_expiry_totals(sym, max_expiries=max_expiries)
        df = _add_dte(df, asof=asof)
        df = _add_impulse_vol_over_oi(df)
        df = _add_event_score_oi_share_x_oi_pcr(df)

        df.insert(0, "Run_Timestamp", run_ts)
        df.insert(1, "AsOfDate", asof.isoformat())
        frames.append(df)

    out = pd.concat(frames, ignore_index=True)

    col_order = [
        "Run_Timestamp",
        "AsOfDate",
        "Symbol",
        "Expiry",
        "DTE",
        "Put_Volume",
        "Call_Volume",
        "Volume_PCR",
        "Put_OI",
        "Call_OI",
        "OI_PCR",
        "Total_OI",
        "Impulse_Vol_over_OI",
        "EventScore_OIshare_x_OI_PCR",
    ]
    col_order = [c for c in col_order if c in out.columns]
    out = out[col_order].sort_values(["Symbol", "Expiry"]).reset_index(drop=True)
    return out


# =========================
# Dataset 2: Snapshot PCR (ALL + all windows)
# =========================
def build_snapshot_dataset(
    symbols: Iterable[str],
    asof: date,
    run_ts: str,
) -> pd.DataFrame:
    df_all = pcr_for_symbols_all(symbols=symbols).copy()
    df_all["Window"] = "ALL"

    df_multi = pcr_for_symbols_multiwindow(symbols=symbols, windows=WINDOW_SPECS).copy()

    out = pd.concat([df_all, df_multi], ignore_index=True)
    out.insert(0, "Run_Timestamp", run_ts)
    out.insert(1, "AsOfDate", asof.isoformat())

    col_order = [
        "Run_Timestamp",
        "AsOfDate",
        "Symbol",
        "Window",
        "Mode",
        "Basis",
        "PCR",
        "Puts",
        "Calls",
        "Spot",
        "DTE_Min",
        "DTE_Max",
        "Strike_Pct",
        "Expiries_Inspected",
        "Expiries_Used",
    ]
    col_order = [c for c in col_order if c in out.columns]
    out = out[col_order].sort_values(["Symbol", "Window", "Basis"]).reset_index(drop=True)
    return out


# =========================
# Public API: build + export both
# =========================
def export_pcr_datasets(
    symbols: Optional[Iterable[str]] = None,
    asof: Optional[date] = None,
    max_expiries: Optional[int] = None,
    out_dir: str = ".",
    per_expiry_csv_name: Optional[str] = None,
    snapshot_csv_name: Optional[str] = None,
    snapshot_symbols: Optional[Iterable[str]] = None,
) -> Tuple[pd.DataFrame, pd.DataFrame, str, str]:
    syms = list(symbols) if symbols is not None else list(DEFAULT_SYMBOLS_BY_EXPIRY)
    snap_syms = list(snapshot_symbols) if snapshot_symbols is not None else (
        list(symbols) if symbols is not None else list(DEFAULT_SYMBOLS_SNAPSHOT)
    )

    asof_d = asof or date.today()
    run_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    df_per_expiry = build_per_expiry_signals_dataset(
        symbols=syms,
        asof=asof_d,
        run_ts=run_ts,
        max_expiries=max_expiries,
    )

    df_snapshot = build_snapshot_dataset(
        symbols=snap_syms,
        asof=asof_d,
        run_ts=run_ts,
    )

    per_expiry_name = per_expiry_csv_name or f"per_expiry_totals_with_signals__{asof_d.isoformat()}.csv"
    snapshot_name = snapshot_csv_name or f"pcr_snapshot_all_windows__{asof_d.isoformat()}.csv"

    out_dir_clean = out_dir.strip()
    if out_dir_clean in ("", "."):
        per_expiry_path = per_expiry_name
        snapshot_path = snapshot_name
    else:
        per_expiry_path = f"{out_dir_clean.rstrip('/')}/{per_expiry_name}"
        snapshot_path = f"{out_dir_clean.rstrip('/')}/{snapshot_name}"

    df_per_expiry.to_csv(per_expiry_path, index=False)
    df_snapshot.to_csv(snapshot_path, index=False)

    return df_per_expiry, df_snapshot, per_expiry_path, snapshot_path


def main() -> None:
    df1, df2, p1, p2 = export_pcr_datasets(
        symbols=None,
        asof=date.today(),
        max_expiries=None,
        out_dir=".",
    )
    print(f"Wrote: {p1} ({len(df1)} rows)")
    print(f"Wrote: {p2} ({len(df2)} rows)")


if __name__ == "__main__":
    main()
