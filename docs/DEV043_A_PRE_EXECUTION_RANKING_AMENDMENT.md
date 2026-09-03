# DEV043-A Pre-Execution Ranking Amendment

Status:

`FROZEN_BEFORE_ANY_DEV043_A_REAL_RESULT`

Date: 2026-09-03

This amendment closes one omission in the original DEV043 design:

the design defined Stage-A eligibility and required exactly one survivor to
advance, but did not specify a deterministic ranking if multiple Stage-A
candidates pass all gates.

No real DEV043-A labels, fits, probabilities, or metrics have been opened.

## Frozen Stage-A ranking

Among Stage-A candidates that pass every frozen eligibility and joint-null gate:

1. highest minimum outer-fold TOUCH AP lift over fold prevalence;
2. highest pooled TOUCH AP lift over pooled prevalence;
3. highest minimum leave-one-fold-out TOUCH AP lift;
4. highest pooled ROC AUC;
5. lowest pooled Brier score;
6. lower model complexity:
   - A0_TOUCH_PRICE_LOGIT
   - A1_TOUCH_PRESSURE_LOGIT
   - A2_TOUCH_COMBINED_HGB
7. lexical candidate ID.

Advance exactly one.

If none qualifies:

`DEV043_A_NO_TOUCH_SURVIVOR`

No ranking criterion may change after real Stage-A results begin.

## Null statistic clarification

The Stage-A temporal null operates on the fixed OOF TOUCH probabilities.

For each of 1999 replicates:

- one legal nonzero circular shift is drawn independently within each outer
  fold;
- the SAME fold-specific target shift is applied to all A0-A2 candidates;
- models are NOT refit;
- pooled shifted TOUCH average precision is calculated for each candidate;
- pooled TOUCH prevalence is unchanged by circular shifting;
- candidate statistic = shifted pooled AP minus pooled TOUCH prevalence;
- replicate max statistic = maximum AP lift across A0-A2.

Frozen q95:

`quantile(max_stat_null, 0.95, method="higher")`

Candidate FWER:

`p_j = (1 + count(max_stat_null >= observed_AP_lift_j)) / 2000`

Legal shifts:

- minimum circular displacement = 60 common evaluation positions within each
  fold;
- maximum = n_fold - 60;
- folds with <=120 valid Stage-A evaluation rows fail closed.

This clarification is part of the frozen Stage-A design.
