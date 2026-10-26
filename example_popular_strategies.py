"""
Three strategies everyone swears by — run through the Verdugo gauntlet.

Each is a well-known public concept. Point it at your own OHLC data (a CSV with
columns: time, open, high, low, close) and Verdugo tells you PASS or smoke.

Spoiler from the author's own run on 6 FX pairs (15-min bars, net of cost):
all three came back HUMO. That's not a bug in the strategies — it's what honest
testing looks like. The popular stuff usually doesn't survive real cost.

    python example_popular_strategies.py your_data.csv
"""
import sys
import numpy as np
import pandas as pd
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from verdugo import Gauntlet


def bollinger_rsi_mean_reversion(df):
    """Buy when price pokes below the lower Bollinger band with RSI < 30."""
    c = df["close"]
    ma, sd = c.rolling(20).mean(), c.rolling(20).std()
    lower = ma - 2 * sd
    d = c.diff()
    up = d.clip(lower=0).ewm(alpha=1/14, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1/14, adjust=False).mean()
    rsi = 100 - 100 / (1 + up / dn.replace(0, np.nan))
    return (c < lower) & (rsi < 30)


def opening_range_breakout(df, start_h=9, start_m=30, end_h=10, cutoff_h=14):
    """Break of the first-hour range of the session (long side)."""
    t = pd.to_datetime(df["time"])
    hh, mm, day = t.dt.hour.values, t.dt.minute.values, t.dt.date.values
    hi, lo = df["high"].values, df["low"].values
    ent = np.zeros(len(df), bool)
    cur, orhi, fired = None, None, False
    for i in range(len(df)):
        if day[i] != cur:
            cur, orhi, fired = day[i], None, False
        in_or = (hh[i] == start_h and mm[i] >= start_m) or (hh[i] == end_h and mm[i] == 0)
        if in_or:
            orhi = hi[i] if orhi is None else max(orhi, hi[i])
        elif orhi is not None and not fired and end_h <= hh[i] < cutoff_h and hi[i] > orhi:
            ent[i] = True
            fired = True
    return ent


def candle_breakout_15m(df):
    """Momentum: break the previous bar's high (long side). Fires constantly."""
    return df["high"] > df["high"].shift(1)


def main(path):
    df = pd.read_csv(path)
    df.columns = [c.lower() for c in df.columns]
    if "time" not in df.columns:
        df = df.rename(columns={df.columns[0]: "time"})
    strategies = [
        ("Bollinger + RSI mean reversion", bollinger_rsi_mean_reversion, 2.0, 2.0),
        ("Opening-range breakout (ORB)", opening_range_breakout, 2.0, 2.0),
        ("15-min candle breakout", candle_breakout_15m, 1.5, 1.5),
    ]
    for name, fn, sl, tp in strategies:
        g = Gauntlet(cost_pips=1.5, pip_size=0.0001, sl_atr=sl, tp_atr=tp, max_hold_bars=16)
        res = g.run(df, fn(df), direction="long", time_col="time")
        v = res.verdict()
        s = res.summary()
        print(f"\n{name}")
        print(f"  {s['trades']} trades | win {s['win_rate']*100:.0f}% | mean {s['mean_R']:+.3f} R")
        print(f"  VERDICT: {v['verdict']} — {v['reasons'][0]}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python example_popular_strategies.py your_data.csv")
        print("CSV columns needed: time, open, high, low, close")
        sys.exit(0)
    main(sys.argv[1])
