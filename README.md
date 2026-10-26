# Verdugo 🔪

**The honest backtest gauntlet that kills fake trading edges.**

Most trading "edges" look amazing in a backtest and die the moment real money
touches them. Verdugo exists to catch that **before** it costs you. It takes any
strategy and runs it through the three things that separate a real edge from
smoke:

1. **Real cost** — spread and commission are subtracted from *every* trade. The
   number that quietly kills most retail strategies.
2. **Out-of-sample** — it checks whether the edge still works on the newest data
   it never "saw". An edge that only works on the data you tuned it on is not an
   edge.
3. **Every year** — a strategy that wins across market regimes is real. One that
   won because of a single lucky year is a trap.

Then it gives you **one honest word: `PASS` or `HUMO`** (smoke). No equity-curve
theatre, no cherry-picked slice.

> Built by a trader who got burned by inflated numbers, and decided the fix was
> to measure everything the hard, honest way. — Matías De Virgilis

---

## Why this exists

A pretty backtest is the easiest thing in the world to produce. Add an indicator,
keep the slice where it worked, forget the spread, and you have a "90% win rate"
that evaporates in a live account. Verdugo refuses to let you fool yourself:

- It **always** subtracts cost, and shows you the exact cost at which your edge
  dies (the *break-even spread*).
- It **always** splits time into in-sample and out-of-sample.
- It treats a filter that "feels selective" with suspicion and makes you prove it
  on average — because a random filter beats the base about **half the time by
  pure luck**.

## Install

```bash
pip install -r requirements.txt     # numpy, pandas
# or, as a package:
pip install -e .
```

## Quickstart

```python
import pandas as pd
from verdugo import Gauntlet

# df: an OHLC frame (columns open/high/low/close), datetime index.
# entries: a boolean Series, True on the bar where you'd open a trade.

g = Gauntlet(
    cost_pips=2.0,     # your REAL round-trip cost. Be honest here.
    pip_size=0.0001,   # 0.01 for JPY pairs
    sl_atr=2.0,        # stop  = 2 x ATR
    tp_atr=2.0,        # target = 2 x ATR
)

res = g.run(df, entries, direction="long")

print(res.summary())            # trades, win rate, mean R, total R
print(res.out_of_sample())      # in-sample vs out-of-sample
print(res.by_year())            # mean R per year
print(res.cost_curve(pip_in_R)) # where does it die as cost rises?
print(res.verdict())            # PASS or HUMO, with the reasons
```

Everything is measured in **R** — profit in units of risk, where `1R` is the
distance to your stop. It makes strategies with different stops comparable, and
it is what actually matters for position sizing.

### Does a filter really help?

The most common self-deception in trading is "I added a filter and it got
better." Verdugo makes you prove it:

```python
cmp = g.compare(df, entries_base, entries_filtered, direction="long")
print(cmp["filter_helps"], cmp["delta_mean_R"])
```

## See it run

```bash
python demo.py
```

The demo builds synthetic data with a **real but modest** edge injected, then:

```
Trades: 350 | win rate: 60% | mean +0.173 R | total +60.6 R

OUT-OF-SAMPLE (newest 30% it never 'saw'):
  in-sample : +0.134 R        out-sample: +0.262 R      <- holds up

EVERY YEAR:
  2018..2023 all positive (one year barely, like real life)

HOW MUCH COST KILLS IT:
  at +1 pip  -> +0.173 R
  at +17 pip -> +0.035 R       <- here is where it would die

VERDICT: PASS — positive net of cost, holds out-of-sample, wins across years

FILTER TEST — a RANDOM 'filter' tried 200 times:
  looked like it 'helped' 54% of the time
  average effect: +0.004 R  (i.e. nothing)
```

That last block is the lesson: a filter that looks good **once** is usually luck.
Only one that helps **on average**, out-of-sample, net of cost, is real.

## What Verdugo is *not*

- It is **not** a strategy, and it will not give you one. It judges strategies.
- It does **not** promise profit. A `PASS` means an edge survived honest testing
  on your data — nothing more. Live trading is always the final judge.
- It is a straightforward, auditable engine, not a black box. Read `verdugo.py`; it
  is short on purpose.

## Roadmap

- Walk-forward (rolling) testing, not just one split.
- Monte-Carlo trade-order shuffling for confidence bands.
- Slippage and partial-fill models.
- A tiny CLI: `verdugo strategy.csv`.

Contributions welcome. The one rule: **nothing that makes the test more
flattering and less honest.**

## License

MIT © 2026 Matías De Virgilis.
