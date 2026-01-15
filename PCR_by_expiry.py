from __future__ import annotations
from typing import Iterable, Optional

import numpy as np
import pandas as pd
import yfinance as yf
import matplotlib.pyplot as plt


# Broad index ETFs used as proxies for systemic, cross-asset stress
DEFAULT_SYMBOLS = ["SPY", "QQQ", "DIA", "IWM", "XLF", "KRE"]


def per_expiry_totals(symbol: str, max_expiries: Optional[int] = None) -> pd.DataFrame:
    tk = yf.Ticker(symbol)
    expiries = list(tk.options or [])
    if not expiries:
        raise RuntimeError(f"No option expirations for {symbol}")

    # Optional cap allows faster runs while preserving the term-structure shape
    if max_expiries is not None:
        expiries = expiries[:max_expiries]

    rows = []
    used = 0

    for exp in expiries:
        try:
            ch = tk.option_chain(exp)
            calls, puts = ch.calls, ch.puts

            # Volume captures *current hedging demand*
            # Open interest captures *persistent positioning*
            c_vol = float(calls["volume"].fillna(0).sum())
            p_vol = float(puts["volume"].fillna(0).sum())
            c_oi = float(calls["openInterest"].fillna(0).sum())
            p_oi = float(puts["openInterest"].fillna(0).sum())

            # Ratios normalize the structural put-heavy bias in index options
            vol_pcr = p_vol / c_vol if c_vol > 0 else np.nan
            oi_pcr = p_oi / c_oi if c_oi > 0 else np.nan

            rows.append(
                {
                    "Symbol": symbol,
                    "Expiry": exp,
                    "Put_Volume": int(round(p_vol)),
                    "Call_Volume": int(round(c_vol)),
                    "Volume_PCR": round(float(vol_pcr), 6) if np.isfinite(vol_pcr) else None,
                    "Put_OI": int(round(p_oi)),
                    "Call_OI": int(round(c_oi)),
                    "OI_PCR": round(float(oi_pcr), 6) if np.isfinite(oi_pcr) else None,
                    "Total_OI": int(round(p_oi + c_oi)),
                }
            )
            used += 1
        except Exception:
            # Individual expiry failures should not distort the global structure
            continue

    if not rows:
        raise RuntimeError(f"No chain data aggregated for {symbol}")

    # Sorting by expiry makes stress clustering visually and numerically obvious
    df = pd.DataFrame(rows).sort_values("Expiry").reset_index(drop=True)
    df.attrs["Expiries_Used"] = used
    df.attrs["Expiries_Requested"] = len(expiries)
    return df


def top_expiries_by_oi_pcr(df: pd.DataFrame, top_n: int = 5) -> pd.DataFrame:
    if "OI_PCR" not in df.columns:
        raise ValueError("OI_PCR column not found")

    # Focus on where *structural positioning* is most asymmetric
    out = df[df["OI_PCR"].notna()].copy()
    if out.empty:
        return out

    out = out.sort_values("OI_PCR", ascending=False).head(top_n)
    return out[
        [
            "Symbol",
            "Expiry",
            "OI_PCR",
            "Volume_PCR",
            "Put_OI",
            "Call_OI",
            "Total_OI",
            "Put_Volume",
            "Call_Volume",
        ]
    ]


def plot_pcrs_by_expiry(df: pd.DataFrame, title: Optional[str] = None) -> None:
    if "OI_PCR" not in df.columns or "Volume_PCR" not in df.columns:
        raise ValueError("Expected columns OI_PCR and Volume_PCR")

    # Visual comparison highlights flow-vs-positioning divergence at each expiry
    xlabels = df["Expiry"].astype(str).values
    oi = pd.to_numeric(df["OI_PCR"], errors="coerce").values
    vol = pd.to_numeric(df["Volume_PCR"], errors="coerce").values

    x = np.arange(len(xlabels))
    width = 0.42

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(x - width / 2, vol, width=width, alpha=0.75, label="Volume_PCR")
    ax.bar(x + width / 2, oi, width=width, alpha=0.75, label="OI_PCR")

    ax.set_xticks(x)
    ax.set_xticklabels(xlabels, rotation=45, ha="right")
    ax.set_xlabel("Expiration Date")
    ax.set_ylabel("Put/Call Ratio (PCR)")
    ax.set_title(title or f"{df['Symbol'].iloc[0]}: PCR by Expiry (Volume vs Open Interest)")

    # PCR = 1 acts as a neutral reference point for stress interpretation
    ax.axhline(1.0, linestyle="--", linewidth=1, alpha=0.6)

    ax.grid(True, linestyle="--", alpha=0.35)
    ax.legend()

    plt.tight_layout()
    plt.show()


def report_per_expiry(
    symbol: str,
    max_expiries: Optional[int] = None,
    top_n: int = 5,
    plot: bool = True,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    # Single-symbol report keeps interpretation localized before cross-asset comparison
    df = per_expiry_totals(symbol, max_expiries=max_expiries)
    top = top_expiries_by_oi_pcr(df, top_n=top_n)

    print(f"\n=== {symbol}: Per-expiry totals ===")
    print(
        df[
            [
                "Expiry",
                "Put_Volume",
                "Call_Volume",
                "Volume_PCR",
                "Put_OI",
                "Call_OI",
                "OI_PCR",
                "Total_OI",
            ]
        ].to_string(index=False)
    )

    print(f"\n{symbol}: Top {top_n} expiries by OI_PCR")
    if top.empty:
        print("(no non-null OI_PCR values)")
    else:
        print(top.to_string(index=False))

    if plot:
        plot_pcrs_by_expiry(
            df,
            title=f"{symbol}: PCR per Expiry (Volume_PCR vs OI_PCR)",
        )

    return df, top


def run_reports(
    symbols: Iterable[str] = DEFAULT_SYMBOLS,
    max_expiries: Optional[int] = None,
    top_n: int = 5,
    plot: bool = True,
) -> dict[str, dict[str, pd.DataFrame]]:
    # Running the same pipeline across indices allows direct stress comparison
    out = {}
    for sym in symbols:
        df, top = report_per_expiry(sym, max_expiries=max_expiries, top_n=top_n, plot=plot)
        out[sym] = {"per_expiry": df, "top": top}
    return out


def main():
    run_reports(
        symbols=DEFAULT_SYMBOLS,
        max_expiries=None,
        top_n=5,
        plot=True,
    )


if __name__ == "__main__":
    main()