from __future__ import annotations
from datetime import datetime

import numpy as np
import pandas as pd

from PCR import (
    DEFAULT_SYMBOLS,
    WINDOW_SPECS,
    pcr_for_symbols_all,
    pcr_for_symbols_multiwindow,
)


def flow_vs_positioning_divergence(df: pd.DataFrame) -> pd.DataFrame:
    # We require a consistent schema because this is used as a generic “snapshot” transformer
    req = {"Symbol", "Basis", "PCR"}
    missing = req - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    # Pivot turns long-form (Symbol,Basis,PCR) into a wide view so volume vs OI can be compared directly
    wide = (
        df.pivot_table(index="Symbol", columns="Basis", values="PCR", aggfunc="first")
        .reset_index()
        .rename_axis(None, axis=1)
    )

    # Divergence only makes sense if we have both flow (volume) and positioning (openInterest)
    if "volume" not in wide.columns or "openInterest" not in wide.columns:
        raise ValueError("Both 'volume' and 'openInterest' must be present in Basis")

    # Positive means flow is more put-heavy than positioning; negative means flow is “less bearish than the stack”
    wide["Divergence_Vol_minus_OI"] = wide["volume"] - wide["openInterest"]
    return wide


def add_hedging_impulse(df_formatted: pd.DataFrame) -> pd.DataFrame:
    # “Impulse” scales today’s flow signal by the embedded positioning signal
    out = df_formatted.copy()

    v = out.get("PCR_Volume")
    oi = out.get("PCR_OpenInterest")

    if v is None or oi is None:
        raise ValueError("Expected columns PCR_Volume and PCR_OpenInterest")

    v = pd.to_numeric(v, errors="coerce")
    oi = pd.to_numeric(oi, errors="coerce")

    # Ratio highlights “abnormal flow per unit of positioning” while staying dimensionless across symbols
    out["Impulse_Vol_over_OI"] = np.where(
        (oi > 0) & np.isfinite(oi) & np.isfinite(v),
        v / oi,
        np.nan,
    )

    out["Impulse_Vol_over_OI"] = pd.to_numeric(out["Impulse_Vol_over_OI"], errors="coerce").round(6)
    return out


def _format_snapshot_table(
    title: str,
    df_raw: pd.DataFrame,
    symbols: list[str] | None = None,
) -> pd.DataFrame:
    # Allows the same formatting logic to be reused for “all expiries” and each DTE/strike window
    if symbols is not None:
        df_raw = df_raw[df_raw["Symbol"].isin(symbols)].copy()

    div = flow_vs_positioning_divergence(df_raw)

    # Preserve the “window definition” so the dataset stays self-describing when exported/shared
    extra_cols = []
    for c in [
        "Window",
        "Spot",
        "DTE_Min",
        "DTE_Max",
        "Strike_Pct",
        "Expiries_Used",
        "Expiries_Inspected",
    ]:
        if c in df_raw.columns:
            extra_cols.append(c)

    # Meta columns are taken per-symbol because PCR is already aggregated for that symbol/window
    meta = (
        df_raw.drop_duplicates(subset=["Symbol"])[["Symbol"] + extra_cols]
        if extra_cols
        else df_raw.drop_duplicates(subset=["Symbol"])[["Symbol"]]
    )

    # Merge keeps both: (a) the window definition and (b) the derived divergence metrics
    out = meta.merge(div, on="Symbol", how="left")

    # Rename makes downstream usage explicit (PCR_Volume vs PCR_OpenInterest) instead of relying on “Basis”
    rename_map = {
        "volume": "PCR_Volume",
        "openInterest": "PCR_OpenInterest",
    }
    out = out.rename(columns=rename_map)

    # Add Impulse after renaming so the logic is stable regardless of upstream Basis labels
    out = add_hedging_impulse(out)

    # Standard ordering makes printed tables comparable across windows
    col_order = (
        ["Symbol"]
        + extra_cols
        + ["PCR_Volume", "PCR_OpenInterest", "Divergence_Vol_minus_OI", "Impulse_Vol_over_OI"]
    )
    col_order = [c for c in col_order if c in out.columns]
    out = out[col_order].sort_values("Symbol")

    out.attrs["title"] = title
    return out


def market_map_vs_spy(df_formatted: pd.DataFrame) -> pd.DataFrame:
    # Relative-to-SPY framing is a quick cross-asset “who is more stressed than the benchmark?” view
    req = {"Symbol", "PCR_Volume", "PCR_OpenInterest", "Divergence_Vol_minus_OI"}
    missing = req - set(df_formatted.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    spy_row = df_formatted[df_formatted["Symbol"] == "SPY"]
    if spy_row.empty:
        raise ValueError("SPY row not found in table; cannot compute market map vs SPY")

    spy_vol = float(pd.to_numeric(spy_row["PCR_Volume"].iloc[0], errors="coerce"))
    spy_oi = float(pd.to_numeric(spy_row["PCR_OpenInterest"].iloc[0], errors="coerce"))
    spy_div = float(pd.to_numeric(spy_row["Divergence_Vol_minus_OI"].iloc[0], errors="coerce"))

    t = df_formatted.copy()

    # Deltas isolate “excess put pressure” versus the broad market proxy
    t["Delta_PCR_Vol_vs_SPY"] = pd.to_numeric(t["PCR_Volume"], errors="coerce") - spy_vol
    t["Delta_PCR_OI_vs_SPY"] = pd.to_numeric(t["PCR_OpenInterest"], errors="coerce") - spy_oi
    t["Delta_Divergence_vs_SPY"] = pd.to_numeric(t["Divergence_Vol_minus_OI"], errors="coerce") - spy_div

    cols = [
        "Symbol",
        "Delta_PCR_Vol_vs_SPY",
        "Delta_PCR_OI_vs_SPY",
        "Delta_Divergence_vs_SPY",
    ]
    t = t[cols].copy()

    # Sorting by Volume delta emphasizes where the newest flow is most bearish vs SPY
    t = t[t["Symbol"] != "SPY"].sort_values("Delta_PCR_Vol_vs_SPY", ascending=False)
    t["Delta_PCR_Vol_vs_SPY"] = t["Delta_PCR_Vol_vs_SPY"].round(6)
    t["Delta_PCR_OI_vs_SPY"] = t["Delta_PCR_OI_vs_SPY"].round(6)
    t["Delta_Divergence_vs_SPY"] = t["Delta_Divergence_vs_SPY"].round(6)
    return t


def print_snapshot_report(symbols: list[str] | None = None) -> None:
    # One run prints the “global” snapshot and then the same snapshot sliced by DTE/strike windows
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    syms = symbols or DEFAULT_SYMBOLS

    df_all = pcr_for_symbols_all(symbols=syms)
    df_multi = pcr_for_symbols_multiwindow(symbols=syms)

    t_all = _format_snapshot_table(
        title="All Expiries / All Strikes",
        df_raw=df_all,
        symbols=symbols,
    )

    print(f"\nPCR Snapshot Report @ {ts}\n")

    print(f"{t_all.attrs.get('title','')}\n")
    print(t_all.to_string(index=False))

    print(f"\nMarket Map vs SPY (All Expiries / All Strikes)\n")
    print(market_map_vs_spy(t_all).to_string(index=False))

    for w in WINDOW_SPECS:
        name = str(w["name"])
        dte_min = int(w["dte_min"])
        dte_max = int(w["dte_max"])
        strike_pct = float(w["strike_pct"])

        # Window filter turns a single big dataset into a consistent family of “comparable slices”
        df_w = df_multi[df_multi["Window"] == name].copy()

        t_w = _format_snapshot_table(
            title=f"{name} (DTE {dte_min}–{dte_max}, ±{int(strike_pct*100)}% Strike Window)",
            df_raw=df_w,
            symbols=symbols,
        )

        print(f"\n{t_w.attrs.get('title','')}\n")
        print(t_w.to_string(index=False))

        print(f"\nMarket Map vs SPY ({name})\n")
        print(market_map_vs_spy(t_w).to_string(index=False))


def main():
    print_snapshot_report()


if __name__ == "__main__":
    main()
