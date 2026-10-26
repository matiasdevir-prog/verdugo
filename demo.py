"""
Verdugo demo — runs on synthetic data, no downloads, no secrets.

It shows the two lessons Verdugo exists to teach:
  1) A real edge survives real cost and out-of-sample... until the cost gets
     high enough. Verdugo shows you exactly where it dies.
  2) A "filter" that feels smart usually adds nothing. Verdugo proves it with
     a plain A/B, instead of a nice-looking chart.

Run:  python examples/demo.py
"""
import numpy as np
import pandas as pd

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from verdugo import Gauntlet

rng = np.random.default_rng(7)

# ---- build ~8 years of daily FX-like prices with a REAL post-dip rebound edge
N = 2000
dates = pd.date_range("2018-01-01", periods=N, freq="D")
ret = rng.normal(0, 0.005, N)                 # base noise (dominant, so the edge is only a tilt)

# 1st pass: locate dips on a provisional path
prov = 1.10 + np.cumsum(ret)
ma = pd.Series(prov).rolling(20).mean()
sd = pd.Series(prov).rolling(20).std()
dip = ((pd.Series(prov) < ma - 1.5 * sd).fillna(False)).values

# inject a REAL but modest rebound after each dip: a tilt, not a guarantee
push = [0.0009, 0.0006, 0.0004]
for i in range(N - len(push) - 1):
    if dip[i]:
        for k, p in enumerate(push):
            ret[i + 1 + k] += p

# now build a consistent OHLC frame from the final returns
close = 1.10 + np.cumsum(ret)
df = pd.DataFrame(index=dates)
df["close"] = close
df["open"] = pd.Series(close, index=dates).shift(1).fillna(close[0]).values
wick = np.abs(rng.normal(0, 0.0012, N))
df["high"] = np.maximum(df["open"], df["close"]) + wick
df["low"] = np.minimum(df["open"], df["close"]) - wick

entries = dip  # go long on the dip

g = Gauntlet(cost_pips=1.0, pip_size=0.0001, sl_atr=1.5, tp_atr=1.5, max_hold_bars=8)
res = g.run(df, entries, direction="long")

print("=" * 60)
print("VERDUGO — honest gauntlet demo")
print("=" * 60)
s = res.summary()
print(f"\nTrades: {s['trades']} | win rate: {s['win_rate']*100:.0f}% | "
      f"mean {s['mean_R']:+.3f} R | total {s['total_R']:+.1f} R")

oos = res.out_of_sample()
print(f"\nOUT-OF-SAMPLE (newest 30% it never 'saw'):")
print(f"  in-sample : {oos['in_mean_R']:+.3f} R ({oos['in_n']} trades)")
print(f"  out-sample: {oos['oos_mean_R']:+.3f} R ({oos['oos_n']} trades)")

print("\nEVERY YEAR:")
print(res.by_year().round(3).to_string())

# median risk, to express an extra pip of cost in R
med_atr = float(np.nanmedian(__import__("verdugo").atr(df.rename(columns=str.lower))))
pip_in_R = 0.0001 / (2.0 * med_atr)
print("\nHOW MUCH COST KILLS IT:")
print(res.cost_curve(pip_in_R).round(3).to_string(index=False))

v = res.verdict()
print("\n" + "-" * 60)
print(f"VERDICT: {v['verdict']}")
for r in v["reasons"]:
    print(f"  - {r}")

# ---- A/B: does a 'smart' random filter help? Try it 200 times. ----
print("\n" + "-" * 60)
print("FILTER TEST — a RANDOM 'filter' (keep half the signals), tried 200 times:")
deltas = []
for _ in range(200):
    f = entries & (rng.random(N) > 0.5)
    deltas.append(g.compare(df, entries, f, direction="long")["delta_mean_R"])
deltas = np.array(deltas)
print(f"  looked like it 'helped' {(deltas > 0).mean()*100:.0f}% of the time")
print(f"  average effect: {deltas.mean():+.4f} R  (i.e. nothing)")
print("\nLesson: a filter that looks good ONCE is usually luck — about half the")
print("time pure noise 'beats' the base. Only a filter that helps on AVERAGE,")
print("out-of-sample, net of cost, is real. That is the whole point of Verdugo.")
