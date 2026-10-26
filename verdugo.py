"""
Verdugo — the honest backtest gauntlet.

One idea: most trading "edges" look great in a laboratory and die in real life.
Verdugo puts a strategy through the three things that kill fakes:
  1) real cost (spread/commission) subtracted from every trade,
  2) out-of-sample: does it still work on data it never saw,
  3) every year: does it win across regimes, or was it one lucky slice.

It returns ONE honest verdict: PASS or HUMO (smoke).

Author: Matías De Virgilis.  License: MIT.
"""
from __future__ import annotations
import numpy as np
import pandas as pd


def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Wilder ATR on an OHLC frame."""
    pc = df["close"].shift(1)
    tr = pd.concat(
        [df["high"] - df["low"], (df["high"] - pc).abs(), (df["low"] - pc).abs()],
        axis=1,
    ).max(axis=1)
    return tr.ewm(alpha=1.0 / period, adjust=False).mean()


class Result:
    """Per-trade results of one run, plus the honest tests on top of them."""

    def __init__(self, trades: pd.DataFrame, cost_pips: float):
        # trades: columns = ['time', 'R'] ; R is profit in units of risk (1R = the stop)
        self.trades = trades.reset_index(drop=True)
        self.cost_pips = cost_pips

    # ---- basic honest summary ------------------------------------------------
    def summary(self) -> dict:
        R = self.trades["R"].values
        return {
            "trades": int(len(R)),
            "win_rate": float((R > 0).mean()) if len(R) else float("nan"),
            "mean_R": float(R.mean()) if len(R) else float("nan"),
            "total_R": float(R.sum()) if len(R) else 0.0,
        }

    # ---- test 1: out of sample ----------------------------------------------
    def out_of_sample(self, split: float = 0.3) -> dict:
        """Chronological split: oldest (1-split) vs newest `split`."""
        n = len(self.trades)
        k = int(n * (1 - split))
        inn = self.trades["R"].values[:k]
        oos = self.trades["R"].values[k:]
        f = lambda a: (float(a.mean()) if len(a) else float("nan"),
                       float((a > 0).mean()) if len(a) else float("nan"), int(len(a)))
        im, iw, ina = f(inn)
        om, ow, ona = f(oos)
        return {"in_mean_R": im, "in_win": iw, "in_n": ina,
                "oos_mean_R": om, "oos_win": ow, "oos_n": ona}

    # ---- test 2: every year --------------------------------------------------
    def by_year(self) -> pd.DataFrame:
        t = self.trades.copy()
        t["year"] = pd.to_datetime(t["time"]).dt.year
        g = t.groupby("year")["R"].agg(["count", "mean", lambda s: (s > 0).mean()])
        g.columns = ["trades", "mean_R", "win_rate"]
        return g

    # ---- test 3: how much cost kills it -------------------------------------
    def cost_curve(self, pip_value_in_R: float, steps=(0, 1, 2, 4, 8, 16)) -> pd.DataFrame:
        """Mean R if the real cost were X extra pips. Shows the break-even cost."""
        base = self.trades["R"].values
        rows = []
        for extra in steps:
            adj = base - extra * pip_value_in_R
            rows.append((self.cost_pips + extra, float(adj.mean()), float((adj > 0).mean())))
        return pd.DataFrame(rows, columns=["cost_pips", "mean_R", "win_rate"])

    # ---- the verdict ---------------------------------------------------------
    def verdict(self, min_trades=40) -> dict:
        s = self.summary()
        oos = self.out_of_sample()
        yr = self.by_year()
        reasons = []
        ok = True
        if s["trades"] < min_trades:
            ok = False
            reasons.append(f"too few trades ({s['trades']}<{min_trades}): not enough evidence")
        if not (s["mean_R"] > 0):
            ok = False
            reasons.append(f"loses money net of cost (mean {s['mean_R']:+.3f} R)")
        if not (oos["oos_mean_R"] > 0):
            ok = False
            reasons.append(f"dies out-of-sample (oos mean {oos['oos_mean_R']:+.3f} R)")
        pos_years = (yr["mean_R"] > 0).mean() if len(yr) else 0.0
        if pos_years < 0.6:
            ok = False
            reasons.append(f"only {pos_years*100:.0f}% of years positive (one lucky slice)")
        if ok:
            reasons.append("positive net of cost, holds out-of-sample, wins across years")
        return {"verdict": "PASS" if ok else "HUMO",
                "mean_R": s["mean_R"], "oos_mean_R": oos["oos_mean_R"],
                "pos_years_frac": float(pos_years), "trades": s["trades"],
                "reasons": reasons}


class Gauntlet:
    """
    Run a strategy through the honest gauntlet.

    Parameters
    ----------
    cost_pips : round-trip real cost per trade, in pips (spread + commission).
                This is the number that kills fakes. Be honest with it.
    pip_size  : price value of one pip (0.0001 for most FX, 0.01 for JPY pairs).
    sl_atr, tp_atr : stop and target as multiples of ATR.
    atr_period, max_hold_bars : engine settings.
    """

    def __init__(self, cost_pips: float = 1.0, pip_size: float = 0.0001,
                 sl_atr: float = 2.0, tp_atr: float = 2.0,
                 atr_period: int = 14, max_hold_bars: int = 40):
        self.cost_pips = float(cost_pips)
        self.pip_size = float(pip_size)
        self.sl_atr = float(sl_atr)
        self.tp_atr = float(tp_atr)
        self.atr_period = int(atr_period)
        self.max_hold_bars = int(max_hold_bars)

    def run(self, df: pd.DataFrame, entries, direction: str = "long",
            time_col: str | None = None) -> Result:
        """
        df      : OHLC frame with columns open/high/low/close (case-insensitive).
        entries : boolean Series/array aligned to df; True where a trade opens
                  at that bar's close.
        direction : 'long' or 'short'.
        """
        d = df.rename(columns=str.lower).reset_index()
        if time_col is None:
            time_col = "index" if "index" in d.columns else d.columns[0]
        hi, lo, cl = d["high"].values, d["low"].values, d["close"].values
        a = atr(d, self.atr_period).values
        ent = np.asarray(entries, dtype=bool)
        if len(ent) != len(d):
            raise ValueError("entries must align with df (same length)")
        cost = self.cost_pips * self.pip_size
        long = direction == "long"
        out_t, out_R = [], []
        n = len(d)
        for i in range(n - 1):
            if not ent[i] or np.isnan(a[i]) or a[i] <= 0:
                continue
            e = cl[i]
            risk = self.sl_atr * a[i]
            if long:
                sl, tp = e - risk, e + self.tp_atr * a[i]
            else:
                sl, tp = e + risk, e - self.tp_atr * a[i]
            pnl = None
            for j in range(i + 1, min(i + 1 + self.max_hold_bars, n)):
                if long:
                    if lo[j] <= sl: pnl = sl - e; break
                    if hi[j] >= tp: pnl = tp - e; break
                else:
                    if hi[j] >= sl: pnl = e - sl; break
                    if lo[j] <= tp: pnl = e - tp; break
            if pnl is None:
                last = cl[min(i + self.max_hold_bars, n - 1)]
                pnl = (last - e) if long else (e - last)
            pnl -= cost
            out_t.append(d[time_col].iloc[i])
            out_R.append(pnl / risk)
        return Result(pd.DataFrame({"time": out_t, "R": out_R}), self.cost_pips)

    def compare(self, df, entries_base, entries_filtered, direction="long",
                time_col=None) -> dict:
        """
        A/B a filter: does `entries_filtered` (a subset of signals) actually beat
        `entries_base`? This is what exposes a filter that only *feels* smart.
        """
        base = self.run(df, entries_base, direction, time_col).summary()
        filt = self.run(df, entries_filtered, direction, time_col).summary()
        helps = filt["mean_R"] > base["mean_R"] + 1e-9
        return {"base": base, "filtered": filt,
                "filter_helps": bool(helps),
                "delta_mean_R": filt["mean_R"] - base["mean_R"]}


__version__ = "0.1.0"
__author__ = "Matías De Virgilis"
__all__ = ["Gauntlet", "Result", "atr"]
