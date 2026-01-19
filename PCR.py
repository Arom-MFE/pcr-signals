from datetime import date, datetime
from typing import Iterable, Literal

import numpy as np
import pandas as pd
import yfinance as yf

# We explicitly distinguish between flow (volume) and positioning (open interest)
Basis = Literal["volume", "openInterest"]

BASES: list[Basis] = ["volume", "openInterest"]

# Broad index ETFs used as systemic stress proxies rather than single-name noise
DEFAULT_SYMBOLS = ["SPY", "QQQ", "DIA", "IWM", "XLF", "KRE"]

# Term-structure windows chosen to separate short-dated hedging from structural risk
WINDOW_SPECS = [
    {"name": "DTE_1_20", "dte_min": 1, "dte_max": 20, "strike_pct": 0.10},
    {"name": "DTE_21_60", "dte_min": 21, "dte_max": 60, "strike_pct": 0.10},
    {"name": "DTE_61_120", "dte_min": 61, "dte_max": 120, "strike_pct": 0.10},
]


def _parse_expiry(exp: str) -> date:
    # Explicit date parsing avoids silent timezone or locale issues
    return datetime.strptime(exp, "%Y-%m-%d").date()


def _get_spot(tk: yf.Ticker) -> float:
    # Spot price anchors strike filtering and ensures comparisons
    # are made relative to the current market level
    spot = None
    try:
        spot = tk.fast_info.get("last_price", None)
    except Exception:
        pass

    if spot is None or not np.isfinite(spot):
        try:
            spot = tk.info.get("regularMarketPrice", None)
        except Exception:
            spot = None

    if spot is None or not np.isfinite(spot):
        raise RuntimeError("Spot price unavailable")

    return float(spot)


def pcr_all_expiries_all_strikes(symbol: str, basis: Basis) -> dict:
    tk = yf.Ticker(symbol)
    expiries = list(tk.options or [])
    if not expiries:
        raise RuntimeError(f"No options for {symbol}")

    tot_puts = 0.0
    tot_calls = 0.0
    used = 0

    for exp in expiries:
        try:
            ch = tk.option_chain(exp)

            # Aggregating across all expiries captures *total market positioning*
            # rather than event-specific hedging
            tot_calls += float(ch.calls[basis].fillna(0).sum())
            tot_puts += float(ch.puts[basis].fillna(0).sum())
            used += 1
        except Exception:
            continue

    # The ratio normalizes the structural put-heavy bias in index options
    pcr = tot_puts / tot_calls if tot_calls > 0 else np.nan

    return {
        "Symbol": symbol,
        "Basis": basis,
        "Mode": "all_expiries_all_strikes",
        "Puts": int(round(tot_puts)),
        "Calls": int(round(tot_calls)),
        "PCR": round(float(pcr), 6) if np.isfinite(pcr) else None,
        "Expiries_Used": used,
    }


def pcr_windowed(
    symbol: str,
    basis: Basis,
    dte_min: int = 20,
    dte_max: int = 60,
    strike_pct: float = 0.10,
    window_name: str | None = None,
) -> dict:
    tk = yf.Ticker(symbol)
    expiries = list(tk.options or [])
    if not expiries:
        raise RuntimeError(f"No options for {symbol}")

    spot = _get_spot(tk)
    today = date.today()

    # Strike window isolates near-the-money hedging activity
    # rather than deep OTM structural positions
    strike_low = spot * (1.0 - strike_pct)
    strike_high = spot * (1.0 + strike_pct)

    tot_puts = 0.0
    tot_calls = 0.0
    inspected = 0
    used = 0

    for exp in expiries:
        try:
            dte = (_parse_expiry(exp) - today).days

            # Filtering by DTE separates short-term protection
            # from longer-horizon positioning
            if dte < dte_min or dte > dte_max:
                continue

            inspected += 1
            ch = tk.option_chain(exp)

            calls = ch.calls
            puts = ch.puts

            calls = calls[(calls["strike"] >= strike_low) & (calls["strike"] <= strike_high)]
            puts = puts[(puts["strike"] >= strike_low) & (puts["strike"] <= strike_high)]

            c = float(calls[basis].fillna(0).sum())
            p = float(puts[basis].fillna(0).sum())

            # Skip expiries with no meaningful activity
            if c + p <= 0:
                continue

            tot_calls += c
            tot_puts += p
            used += 1

        except Exception:
            continue

    # PCR here reflects *localized stress* rather than aggregate sentiment
    pcr = tot_puts / tot_calls if tot_calls > 0 else np.nan

    return {
        "Symbol": symbol,
        "Basis": basis,
        "Mode": "windowed",
        "Window": window_name or f"DTE_{dte_min}_{dte_max}",
        "Spot": round(spot, 6),
        "DTE_Min": dte_min,
        "DTE_Max": dte_max,
        "Strike_Pct": strike_pct,
        "Puts": int(round(tot_puts)),
        "Calls": int(round(tot_calls)),
        "PCR": round(float(pcr), 6) if np.isfinite(pcr) else None,
        "Expiries_Inspected": inspected,
        "Expiries_Used": used,
    }


def pcr_for_symbols_all(
    symbols: Iterable[str] = DEFAULT_SYMBOLS,
) -> pd.DataFrame:
    # Produces a cross-sectional snapshot of broad market positioning
    rows = []
    for sym in symbols:
        for b in BASES:
            rows.append(pcr_all_expiries_all_strikes(sym, b))
    return pd.DataFrame(rows)



def pcr_for_symbols_multiwindow(
    symbols: Iterable[str] = DEFAULT_SYMBOLS,
    windows: list[dict] = WINDOW_SPECS,
) -> pd.DataFrame:
    # Enables term-structure comparison of stress across maturities
    rows = []
    for w in windows:
        for sym in symbols:
            for b in BASES:
                rows.append(
                    pcr_windowed(
                        sym,
                        basis=b,
                        dte_min=int(w["dte_min"]),
                        dte_max=int(w["dte_max"]),
                        strike_pct=float(w["strike_pct"]),
                        window_name=str(w.get("name") or f"DTE_{w['dte_min']}_{w['dte_max']}"),
                    )
                )
    return pd.DataFrame(rows)


def main():
    df_all = pcr_for_symbols_all()
    df_multi = pcr_for_symbols_multiwindow()

    print("\nPCR — All Expiries / All Strikes (Volume + Open Interest)\n")
    print(df_all.to_string(index=False))

    for w in WINDOW_SPECS:
        name = w["name"]
        dte_min = w["dte_min"]
        dte_max = w["dte_max"]
        strike_pct = w["strike_pct"]

        df_w = df_multi[df_multi["Window"] == name].copy()

        print(
            f"\nPCR — {name} (DTE {dte_min}–{dte_max}, ±{int(strike_pct*100)}% Strike Window) "
            f"(Volume + Open Interest)\n"
        )
        print(df_w.to_string(index=False))


if __name__ == "__main__":
    main()