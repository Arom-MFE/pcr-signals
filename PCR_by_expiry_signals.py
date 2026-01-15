from __future__ import annotations
from datetime import date, datetime
from typing import Optional, Iterable

import numpy as np
import pandas as pd

from PCR_by_expiry import (
    DEFAULT_SYMBOLS,
    per_expiry_totals,
    top_expiries_by_oi_pcr,
    plot_pcrs_by_expiry,
)


def _to_num(s: pd.Series) -> pd.Series:
    # Keep arithmetic predictable when upstream data has None/strings/NaN
    return pd.to_numeric(s, errors="coerce")


def add_dte(df: pd.DataFrame, asof: Optional[date] = None) -> pd.DataFrame:
    # DTE turns “calendar dates” into a tradable axis (term-structure stress clustering)
    out = df.copy()
    d0 = asof or date.today()
    exp = pd.to_datetime(out["Expiry"], errors="coerce").dt.date
    out["DTE"] = exp.map(lambda x: (x - d0).days if x is not None else np.nan)
    out["DTE"] = pd.to_numeric(out["DTE"], errors="coerce")
    return out


def add_flow_vs_positioning(df: pd.DataFrame) -> pd.DataFrame:
    # Volume_PCR approximates *today’s flow*; OI_PCR approximates *embedded positioning*
    # Comparing them isolates “new hedging demand” vs “existing dealer inventory pressure”
    out = df.copy()
    v = _to_num(out["Volume_PCR"])
    oi = _to_num(out["OI_PCR"])

    # Positive divergence means flow is more put-heavy than the existing position stack
    out["Divergence_Vol_minus_OI"] = (v - oi).round(6)

    # Impulse scales flow by positioning to highlight “abnormal activity per unit inventory”
    out["Impulse_Vol_over_OI"] = np.where(
        (oi > 0) & np.isfinite(oi) & np.isfinite(v),
        (v / oi),
        np.nan,
    )
    out["Impulse_Vol_over_OI"] = _to_num(out["Impulse_Vol_over_OI"]).round(6)
    return out


def add_quality_flags(
    df: pd.DataFrame,
    min_call_oi: int = 1000,
    min_call_vol: int = 500,
    min_total_oi: int = 10_000,
) -> pd.DataFrame:
    # Filters prevent “signal” from being dominated by thin expiries (micro-liquidity noise)
    out = df.copy()
    call_oi = _to_num(out["Call_OI"])
    call_vol = _to_num(out["Call_Volume"])
    tot_oi = _to_num(out["Total_OI"])

    ok = (call_oi >= min_call_oi) & (call_vol >= min_call_vol) & (tot_oi >= min_total_oi)
    out["Quality_OK"] = ok.fillna(False)
    return out


def top_by_metric(
    df: pd.DataFrame,
    metric: str,
    top_n: int = 5,
    descending: bool = True,
    require_quality_ok: bool = True,
) -> pd.DataFrame:
    # Ranking is a practical way to turn a term structure into “where do I look first?”
    if metric not in df.columns:
        raise ValueError(f"Metric '{metric}' not found")

    t = df.copy()
    if require_quality_ok and "Quality_OK" in t.columns:
        t = t[t["Quality_OK"] == True].copy()

    t[metric] = _to_num(t[metric])
    t = t[t[metric].notna()].copy()
    if t.empty:
        return t

    t = t.sort_values(metric, ascending=not descending).head(top_n)
    cols = [
        "Symbol",
        "Expiry",
        "DTE",
        "Volume_PCR",
        "OI_PCR",
        "Divergence_Vol_minus_OI",
        "Impulse_Vol_over_OI",
        "EventScore_OIshare_x_OI_PCR",
        "Put_OI",
        "Call_OI",
        "Total_OI",
        "Put_Volume",
        "Call_Volume",
        "Quality_OK",
    ]
    cols = [c for c in cols if c in t.columns]
    return t[cols]


def compute_concentration_metrics(df: pd.DataFrame, top_k: int = 3) -> dict:
    # Concentration captures whether stress is “everywhere” or localized into a few expiries
    t = df.copy()
    total_oi = _to_num(t["Total_OI"]).fillna(0.0)
    sum_total_oi = float(total_oi.sum())

    if sum_total_oi <= 0:
        return {
            "Sum_Total_OI": 0,
            f"Top{top_k}_TotalOIShare": np.nan,
        }

    share = total_oi / sum_total_oi
    top_share = float(share.sort_values(ascending=False).head(top_k).sum())

    return {
        "Sum_Total_OI": int(round(sum_total_oi)),
        f"Top{top_k}_TotalOIShare": round(top_share, 6),
    }


def add_event_score(df: pd.DataFrame) -> pd.DataFrame:
    # “Stress” is not just high PCR; it matters where the OI mass is concentrated
    # This score weights OI_PCR by the expiry’s share of total OI
    out = df.copy()
    tot_oi = _to_num(out["Total_OI"]).fillna(0.0)
    denom = float(tot_oi.sum())
    if denom <= 0:
        out["EventScore_OIshare_x_OI_PCR"] = np.nan
        return out

    oi_pcr = _to_num(out["OI_PCR"])
    share = tot_oi / denom
    out["EventScore_OIshare_x_OI_PCR"] = (share * oi_pcr).round(8)
    return out


def bucket_term_structure(
    df: pd.DataFrame,
    buckets: list[tuple[str, int, int]] = [
        ("Short_1_20", 1, 20),
        ("Mid_21_60", 21, 60),
        ("Long_61_120", 61, 120),
    ],
    require_quality_ok: bool = True,
) -> pd.DataFrame:
    # Buckets compress many expiries into interpretable regimes (front, mid, back)
    # Ranges are non-overlapping to avoid double-counting the same expiry
    t = df.copy()
    if require_quality_ok and "Quality_OK" in t.columns:
        t = t[t["Quality_OK"] == True].copy()

    t["DTE"] = _to_num(t["DTE"])
    t["Put_OI"] = _to_num(t["Put_OI"])
    t["Call_OI"] = _to_num(t["Call_OI"])
    t["Put_Volume"] = _to_num(t["Put_Volume"])
    t["Call_Volume"] = _to_num(t["Call_Volume"])
    t["Total_OI"] = _to_num(t["Total_OI"]).fillna(0.0)

    # Bucket share makes the term-structure comparable across symbols with different OI scales
    denom_total_oi = float(t["Total_OI"].sum())

    rows = []
    for name, lo, hi in buckets:
        w = t[(t["DTE"] >= lo) & (t["DTE"] <= hi)].copy()

        put_oi = float(w["Put_OI"].sum())
        call_oi = float(w["Call_OI"].sum())
        put_vol = float(w["Put_Volume"].sum())
        call_vol = float(w["Call_Volume"].sum())
        total_oi = float(w["Total_OI"].sum())

        oi_pcr = put_oi / call_oi if call_oi > 0 else np.nan
        vol_pcr = put_vol / call_vol if call_vol > 0 else np.nan
        oi_share = (total_oi / denom_total_oi) if denom_total_oi > 0 else np.nan

        rows.append(
            {
                "Bucket": name,
                "DTE_Min": lo,
                "DTE_Max": hi,
                "Sum_Put_OI": int(round(put_oi)),
                "Sum_Call_OI": int(round(call_oi)),
                "Bucket_OI_PCR": round(float(oi_pcr), 6) if np.isfinite(oi_pcr) else None,
                "Sum_Put_Volume": int(round(put_vol)),
                "Sum_Call_Volume": int(round(call_vol)),
                "Bucket_Volume_PCR": round(float(vol_pcr), 6) if np.isfinite(vol_pcr) else None,
                "Bucket_TotalOI": int(round(total_oi)),
                "Bucket_TotalOI_Share": round(float(oi_share), 6) if np.isfinite(oi_share) else None,
            }
        )

    out = pd.DataFrame(rows)
    out["Bucket_OI_PCR"] = _to_num(out["Bucket_OI_PCR"])
    out["Bucket_Volume_PCR"] = _to_num(out["Bucket_Volume_PCR"])
    out["Bucket_TotalOI_Share"] = _to_num(out["Bucket_TotalOI_Share"])
    return out


def enrich_per_expiry(
    symbol: str,
    max_expiries: Optional[int] = None,
    min_call_oi: int = 1000,
    min_call_vol: int = 500,
    min_total_oi: int = 10_000,
) -> pd.DataFrame:
    # One pipeline that turns raw chains into a “readable stress surface” by expiry
    df = per_expiry_totals(symbol, max_expiries=max_expiries)
    df = add_dte(df)
    df = add_flow_vs_positioning(df)
    df = add_quality_flags(
        df,
        min_call_oi=min_call_oi,
        min_call_vol=min_call_vol,
        min_total_oi=min_total_oi,
    )
    df = add_event_score(df)
    return df


def _per_expiry_table(df: pd.DataFrame) -> pd.DataFrame:
    # Keep the printed table consistent across symbols for easy side-by-side comparison
    cols_main = [
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
        "Divergence_Vol_minus_OI",
        "Impulse_Vol_over_OI",
        "EventScore_OIshare_x_OI_PCR",
        "Quality_OK",
    ]
    cols_main = [c for c in cols_main if c in df.columns]
    return df[cols_main].copy()


def print_symbol_top_section(
    symbol: str,
    df: pd.DataFrame,
    top_n: int = 5,
    plot: bool = True,
) -> None:
    # Top sections answer: “where is the stress concentrated right now?”
    print(f"\n=== {symbol}: Top {top_n} expiries by OI_PCR (with signals) ===")
    top_oi = top_expiries_by_oi_pcr(df, top_n=top_n)
    if top_oi.empty:
        print("(no non-null OI_PCR values)")
    else:
        top_oi = top_oi.merge(
            df[
                [
                    "Expiry",
                    "DTE",
                    "Divergence_Vol_minus_OI",
                    "Impulse_Vol_over_OI",
                    "EventScore_OIshare_x_OI_PCR",
                    "Quality_OK",
                ]
            ],
            on="Expiry",
            how="left",
        )
        print(top_oi.to_string(index=False))

    print(f"\n{symbol}: Top {top_n} by Hedging Impulse (Impulse_Vol_over_OI)")
    t_imp = top_by_metric(df, "Impulse_Vol_over_OI", top_n=top_n, descending=True, require_quality_ok=True)
    print(t_imp.to_string(index=False) if not t_imp.empty else "(no qualifying rows)")

    print(f"\n{symbol}: Top {top_n} by Divergence (Divergence_Vol_minus_OI)")
    t_div = top_by_metric(df, "Divergence_Vol_minus_OI", top_n=top_n, descending=True, require_quality_ok=True)
    print(t_div.to_string(index=False) if not t_div.empty else "(no qualifying rows)")

    print(f"\n{symbol}: Top {top_n} by Stress Concentration proxy (EventScore_OIshare_x_OI_PCR)")
    t_evt = top_by_metric(df, "EventScore_OIshare_x_OI_PCR", top_n=top_n, descending=True, require_quality_ok=True)
    print(t_evt.to_string(index=False) if not t_evt.empty else "(no qualifying rows)")

    conc = compute_concentration_metrics(df, top_k=3)
    print(f"\n{symbol}: Concentration Summary")
    for k, v in conc.items():
        print(f"{k}: {v}")

    print(f"\n{symbol}: Term-Structure Buckets (quality-filtered)")
    buckets = bucket_term_structure(df, require_quality_ok=True)
    print(buckets.to_string(index=False))

    if plot:
        # Plot makes “flow vs positioning” divergence obvious at a glance by expiry
        plot_pcrs_by_expiry(df, title=f"{symbol}: PCR per Expiry (Volume_PCR vs OI_PCR)")


def main(
    symbols: Iterable[str] = DEFAULT_SYMBOLS,
    max_expiries: Optional[int] = None,
    top_n: int = 5,
    plot: bool = True,
) -> None:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    symbols = list(symbols)

    all_tables: dict[str, pd.DataFrame] = {}

    print(f"\nPCR by Expiry Signals Report @ {ts}\n")

    for sym in symbols:
        # First pass: print “top stress” sections per symbol (fast to scan)
        df = enrich_per_expiry(sym, max_expiries=max_expiries)
        all_tables[sym] = df
        print_symbol_top_section(sym, df, top_n=top_n, plot=plot)

    print("\n\n==============================")
    print("PER-EXPIRY TOTALS (WITH SIGNALS) — ALL SYMBOLS")
    print("==============================\n")

    for sym in symbols:
        # Second pass: print full tables only after readers have a mental map of the highlights
        df = all_tables[sym]
        print(f"\n=== {sym}: Per-expiry totals (with signals) ===")
        print(_per_expiry_table(df).to_string(index=False))


if __name__ == "__main__":
    main(
        symbols=DEFAULT_SYMBOLS,
        max_expiries=None,
        top_n=5,
        plot=True,
    )
