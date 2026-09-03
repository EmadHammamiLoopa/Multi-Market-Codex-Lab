# DEV043-B Pre-Execution Ranking / Null Amendment

Status:

`FROZEN_BEFORE_ANY_DEV043_B_REAL_RESULT`

Date: 2026-09-03

No real DEV043-B labels, fits, probabilities, or metrics have been opened.

## Frozen Stage-B ranking

Among Stage-B candidates that pass every frozen eligibility and joint-null gate:

1. highest minimum outer-fold balanced-accuracy lift over 0.50;
2. highest pooled balanced accuracy;
3. highest minimum leave-one-fold-out balanced accuracy;
4. highest pooled ROC AUC;
5. lowest pooled log loss;
6. lower model complexity:
   - B0_DIR_PRICE_LOGIT
   - B1_DIR_PRESSURE_LOGIT
   - B2_DIR_COMBINED_HGB
7. lexical candidate ID.

Advance exactly one.

If none qualifies:

`DEV043_B_NO_DIRECTION_SURVIVOR`

## Frozen Stage-B null statistic

The null operates on fixed OOF conditional-direction probabilities.

For each of 1999 replicates:

- draw one legal nonzero circular shift within each outer fold;
- apply the SAME fold-specific direction-label shift to B0-B2;
- do not refit models;
- pooled prediction class uses probability >=0.5 => LONG, else SHORT;
- candidate statistic = pooled balanced accuracy - 0.50;
- replicate max statistic = maximum BA lift across B0-B2.

Frozen q95:

`quantile(max_stat_null,0.95,method="higher")`

Candidate FWER:

`p_j=(1+count(max_stat_null>=observed_BA_lift_j))/2000`

Legal shifts:

- minimum circular displacement = 60 conditional-TOUCH evaluation positions;
- maximum = n_fold - 60;
- any fold with <=120 Stage-B validation rows fails closed.

No ranking or null definition may change after real Stage-B results begin.
