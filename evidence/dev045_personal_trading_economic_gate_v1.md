# DEV045 — PERSONAL_TRADING_ECONOMIC_GATE_V1

Status: **FROZEN BEFORE 112-REPLAY PNL**

Parent: `caffbfb8bb0a979299a497456ed50e1d3b32f3ac`

## Objective

This is a personal, profit-seeking trading project. The governing decision
criterion is therefore **realistic tradable profitability with capital
protection**, not publication-style statistical perfection.

Technical success of the data/execution pipeline increases confidence that
future economic results are trustworthy. It does **not** prove in advance that
an economic edge exists.

Every valid prior success from EXP024 and earlier/later work remains usable in
the role it actually demonstrated. Every failure remains preserved as a
constraint, exclusion, or lesson. Predictive success is not automatically a
profitable strategy, and execution-infrastructure success is not automatically
an economic edge.

## Primary veto gates — realistic base case

The realistic base case must pass the following trading-critical conditions:

- net expectancy is positive after realistic trading costs;
- Profit Factor is above 1;
- execution integrity is complete;
- there is no future leakage;
- fees, slippage, latency, queue position, and fills are realistically modeled;
- drawdown remains within the frozen personal risk limit;
- inventory and terminal-state safety are valid.

Failure in one of these primary economic/integrity/risk gates is **not** a
near-pass merely because other gates passed.

## Adverse conditions

Adverse conditions are robustness evidence. Profit is allowed to deteriorate,
but the strategy must not exhibit an unacceptable collapse relative to the
risk envelope.

## Extreme stress

Extreme stress is a survival/containment test, not a requirement for continued
profitability under implausibly severe assumptions. Loss may occur, but it
must be bounded and the risk controls must work.

## Statistical and concentration evidence

The following remain fully reported and preserved:

- FWER p-value;
- number of positive days;
- profit concentration;
- extreme-stress net PnL.

However, none of these is by itself an automatic veto on a realistically
profitable and safely executable strategy. They determine **confidence and
capital sizing**.

For example, `p = 0.06` instead of `0.05` does not automatically invalidate an
otherwise profitable, cost-realistic, execution-valid strategy. It lowers
confidence and therefore raises the burden of fresh validation and lowers the
capital allowed initially.

## Three separate decision dimensions

The final result must report separately:

1. **Profitability** — is there positive edge after realistic costs?
2. **Robustness** — does the edge remain acceptable when conditions worsen?
3. **Confidence** — how strong is the evidence, and therefore how much capital
   can reasonably be risked?

## Path to live capital

An M6 historical PASS does not directly authorize meaningful live capital.
The required sequence is:

1. fresh replication;
2. untouched forward validation;
3. paper/shadow execution;
4. very small real capital;
5. measure real fills, slippage, and operational behavior;
6. gradual capital scaling only if the live evidence confirms the edge.

## Governing principle

> Every valid prior success is reused in the role it proved, every failure is
> learned from, and the final trading test is realistic and as strict as
> needed to protect capital — not artificially harder than reality. The goal
> is a genuine edge that is profitable, robust, and tradable with our own
> money.

## Closed surfaces

This contract changes interpretation only. It does not authorize the 112
replays yet, policy execution, historical PnL, Feb-Jul raw opening or
conversion, August/September+ access, network acquisition, Railway, or live
trading.
