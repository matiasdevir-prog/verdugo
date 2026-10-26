# Strategy library — candidates for the gauntlet

A small, growing collection of **well-known, public-concept trading strategies**,
written as clean TradingView (Pine v5) scripts. None of them is magic. That's the
point.

> The whole idea of **[Verdugo](./README.md)** is: *don't trust a strategy because
> it has a cool name and a pretty equity curve. Run it through the gauntlet* —
> net of real cost, out-of-sample, every year — and let it tell you PASS or smoke.

So treat everything here as a **candidate**, not a recommendation. Drop in your own
instrument and your own real cost, and let Verdugo give the honest verdict. The
same strategy can PASS on one market and be pure smoke on another.

## In this folder

### `DUKE_previous_day_breakout.pine`
Previous-day range breakout with a trend filter. It goes long when price breaks
**yesterday's high** (and the day opened above yesterday's close), short on the
mirror case. Stop at the recent swing, target a multiple of the risk (R). A
textbook breakout idea.

### `KAI_gap_continuation.pine`
Opening-gap continuation. At the session open, if price **gapped up** it goes long
(betting the gap keeps running), if it **gapped down** it goes short. Stop at
yesterday's close, target 2R. Low correlation with DUKE, so it's often paired for
diversification.

### `LAIRD_volatility_breakout.pine`
Volatility breakout (momentum). It brackets the session open by a fraction of
**yesterday's range** and rides whichever side breaks first. Stop back at the open,
target 2R. The classic "let the day's energy pick the direction" idea.

## More candidates (coming)

Opening-range breakout (ORB), Bollinger + RSI mean-reversion, and the news
straddle — the strategies everyone swears by. Each will land here with a Python
port so you can run it straight through Verdugo.

## How to judge one

Port the entry logic to a boolean signal, feed it to `Gauntlet.run(...)` with your
**real** cost, and read `.verdict()`. If it says `HUMO`, you just saved yourself a
blown account. If it says `PASS`, live trading is still the final judge — start
small.

*The `MDV` tag in the scripts is the author's own shorthand; the ideas themselves
are public and belong to everyone.*
