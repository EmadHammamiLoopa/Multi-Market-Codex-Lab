# DEV038-A-P2 No-Result Reproduction Preflight Protocol

Status: `PROTOCOL_FROZEN_NO_REAL_CORRECTNESS_SCORING`

Date: 2026-09-03

Scientific execution commit:

`a1ac3ea806def0f38b8952295b68fab8eb18e3a1`

This preflight is operational only.

It must not calculate validation correctness, action precision, correct/false
action counts, correctness deltas, temporal null, survivor status, PnL, fees,
slippage, or forward-data metrics.

## Exact local command

```bash
cd /mnt/c/Users/emadh/Downloads/market-exp026

set +e
set +u
set +o pipefail

git fetch origin
git checkout research/dev038a-p2-execution-frozen
git reset --hard a1ac3ea806def0f38b8952295b68fab8eb18e3a1

PY=/home/emadh/.venvs/market-p10/bin/python
EXEC=a1ac3ea806def0f38b8952295b68fab8eb18e3a1

OUT=/home/emadh/Multi-Market/evidence/dev038a_p2_final_controller_correctness_v1
LOG=/home/emadh/Multi-Market/evidence/dev038a_p2_canonical_console_v1.log

R2=/home/emadh/Multi-Market/evidence/dev037_p0_r2_operationally_pruned_controller_v1/DEV037_P0_R2_OPERATIONALLY_PRUNED_CONTROLLER_RESULT.json
R2_SHA=494122f1aea64fb2a4c956d674330d9a400709656f0e116187d6fa2fefaa3336
R2_BYTES=27056

D37=/home/emadh/Multi-Market/evidence/dev037_p1_r1_four_policy_w120_correctness_v1/DEV037_P1_R1_FOUR_POLICY_W120_CORRECTNESS_RESULT.json
D37_SHA=9a9ade5fbc9e564f192786e75551277174907afad26c76a927099e7d859f0cee
D37_BYTES=236045

D38=/home/emadh/Multi-Market/evidence/dev038a_p1_joint_screen_v1/DEV038A_P1_JOINT_SCREEN_RESULT.json
D38_SHA=16292d1f730561427a4623a052441f3ab20db0a96eeefac06b6f0a0391c5e549
D38_BYTES=287084

export PYTHONPATH="$PWD/src"
export PYTHONDONTWRITEBYTECODE=1
export PYTHONUNBUFFERED=1

echo "========== DEV038-A-P2 NO-RESULT PREFLIGHT =========="

HEAD=$(git rev-parse HEAD)
DIRTY=$(git status --porcelain | wc -l)

echo "HEAD=$HEAD"
echo "DIRTY_COUNT=$DIRTY"

PREFLIGHT_OK=1

if [ "$HEAD" = "$EXEC" ]; then
  echo "HEAD_IDENTITY=PASS"
else
  echo "HEAD_IDENTITY=FAIL"
  PREFLIGHT_OK=0
fi

if [ "$DIRTY" -eq 0 ]; then
  echo "CLEAN_TREE=PASS"
else
  echo "CLEAN_TREE=FAIL"
  git status --short
  PREFLIGHT_OK=0
fi

if [ ! -e "$OUT" ]; then
  echo "P2_CANONICAL_OUTPUT_ABSENT=PASS"
else
  echo "P2_CANONICAL_OUTPUT_ABSENT=FAIL"
  PREFLIGHT_OK=0
fi

if [ ! -e "$LOG" ]; then
  echo "P2_CANONICAL_LOG_ABSENT=PASS"
else
  echo "P2_CANONICAL_LOG_ABSENT=FAIL"
  PREFLIGHT_OK=0
fi

check_parent () {
  NAME="$1"
  PATH_="$2"
  SHA_="$3"
  BYTES_="$4"

  if [ ! -f "$PATH_" ]; then
    echo "${NAME}_EXISTS=FAIL"
    PREFLIGHT_OK=0
    return
  fi

  ACT_SHA=$(sha256sum "$PATH_" | awk '{print $1}')
  ACT_BYTES=$(stat -c %s "$PATH_")

  echo "${NAME}_SHA256=$ACT_SHA"
  echo "${NAME}_BYTES=$ACT_BYTES"

  if [ "$ACT_SHA" = "$SHA_" ] && [ "$ACT_BYTES" -eq "$BYTES_" ]; then
    echo "${NAME}_IDENTITY=PASS"
  else
    echo "${NAME}_IDENTITY=FAIL"
    PREFLIGHT_OK=0
  fi
}

check_parent R2 "$R2" "$R2_SHA" "$R2_BYTES"
check_parent D37 "$D37" "$D37_SHA" "$D37_BYTES"
check_parent D38 "$D38" "$D38_SHA" "$D38_BYTES"

STAGING_COUNT=$(
  find /home/emadh/Multi-Market/evidence     -maxdepth 1     -name '.dev038a_p2_final_controller_correctness_v1.part-*'     2>/dev/null | wc -l
)

echo "STAGING_COUNT=$STAGING_COUNT"

if [ "$STAGING_COUNT" -eq 0 ]; then
  echo "NO_STAGING_RESIDUE=PASS"
else
  echo "NO_STAGING_RESIDUE=FAIL"
  PREFLIGHT_OK=0
fi

echo
echo "FILE_GUARDS_OK=$PREFLIGHT_OK"

if [ "$PREFLIGHT_OK" -ne 1 ]; then
  echo "DEV038A_P2_PREFLIGHT_NOT_RUN_FILE_GUARD_FAILURE=YES"
else

"$PY" - "$R2" "$D37" "$D38" <<'PY'
from __future__ import annotations

from collections import deque
import hashlib
import json
import sys

import numpy as np

from multimarket import dev030_direction_dataset as dd
from multimarket import dev036_c1_loader as c1loader
from multimarket import dev037_p0_r1_coverage_core as coverage
from multimarket import dev037_p0_r1_coverage_runner as r1runner

R2_PATH,D37_PATH,D38_PATH=sys.argv[1:4]

r2=json.load(open(R2_PATH,"r",encoding="utf-8"))
d37=json.load(open(D37_PATH,"r",encoding="utf-8"))
d38=json.load(open(D38_PATH,"r",encoding="utf-8"))

checks=[]

def check(name,cond,detail=""):
    cond=bool(cond)
    checks.append(cond)
    print(
        f"{name}={'PASS' if cond else 'FAIL'}"
        + (f"  {detail}" if detail else "")
    )
    return cond

print("========== FROZEN PARENT CONTRACT ==========")

check(
    "R2_STATUS",
    r2.get("status")=="DEV037_P0_R2_CONTROLLER_SELECTED",
)
check(
    "R2_SELECTED_W120",
    r2.get("selected_controller_window")==120,
)
check(
    "D37_STATUS",
    d37.get("status")=="DEV037_P1_R1_NO_CHALLENGER_SURVIVOR_RETAIN_S0",
)
check(
    "D37_ADVANCED_S0",
    d37.get("advanced_policy")==["S0"],
)
check(
    "D38_STATUS",
    d38.get("status")=="DEV038A_P1_NO_CHALLENGER_SURVIVOR_RETAIN_A0",
)
check(
    "D38_ADVANCED_A0",
    d38.get("advanced_candidate")==["A0"],
)

print()
print("========== LOAD FROZEN DEVELOPMENT LINEAGE ==========")

e=c1loader.load_c1()

day_rows=[
    len(e.per_day[d].t2.timestamps_us)
    for d in dd.HISTORICAL_DAYS
]

check(
    "SEVEN_DAYS",
    len(day_rows)==7,
)
check(
    "EVERY_DAY_1407",
    day_rows==[1407]*7,
    str(day_rows),
)
check(
    "CAMPAIGN_ROWS_9849",
    sum(day_rows)==9849,
    str(sum(day_rows)),
)

def action_sha(fid,actions):
    h=hashlib.sha256(
        f"DEV037-P1-R1-ACTION-S0-F{fid}".encode()+b"\0"
    )
    h.update(
        np.asarray(actions,dtype=np.int8).tobytes()
    )
    return h.hexdigest()

def independent_controller(scores,p_long,warm_scores,w):
    s=np.asarray(scores,dtype=np.float64)
    p=np.asarray(p_long,dtype=np.float64)
    warm=np.asarray(warm_scores,dtype=np.float64)

    buf=deque(
        warm[-int(w):].tolist(),
        maxlen=int(w),
    )

    thresholds=np.empty(len(s),dtype=np.float64)
    actions=np.zeros(len(s),dtype=np.int8)

    for i,(score,pl) in enumerate(
        zip(s.tolist(),p.tolist(),strict=True)
    ):
        ref=np.asarray(buf,dtype=np.float64)
        threshold=float(
            np.quantile(
                ref,
                0.80,
                method="higher",
            )
        )
        thresholds[i]=threshold

        if float(score)>=threshold:
            actions[i]=2 if float(pl)>=0.5 else 1

        buf.append(float(score))

    return thresholds,actions

print()
print("========== OPERATIONAL REPRODUCTION ONLY ==========")

windows=(120,360,720)
all_action_lengths=[]

for outer in dd.OUTER_FOLDS:

    z=r1runner._fold_score_streams(
        e,
        outer,
    )

    check(
        f"F{outer.fold_id}_VALIDATION_ROWS_1407",
        int(z["validation_rows"])==1407,
    )

    fold_lengths=[]

    for w in windows:

        rr=coverage.summarize(
            scores=z["validation_scores"]["S0"],
            p_long=z["validation_p_long"],
            warm_scores=z["train_scores"]["S0"],
            window=w,
        )

        parent=(
            r2["folds"][outer.fold_id-1]
              ["controllers"][str(w)]["S0"]
        )

        public=r1runner._public_result(rr)

        check(
            f"F{outer.fold_id}_W{w}_R2_PUBLIC_EXACT",
            public==parent,
        )

        independent_thresholds,independent_actions=(
            independent_controller(
                z["validation_scores"]["S0"],
                z["validation_p_long"],
                z["train_scores"]["S0"],
                w,
            )
        )

        check(
            f"F{outer.fold_id}_W{w}_THRESHOLDS_CAUSAL_EXACT",
            np.array_equal(
                np.asarray(rr.thresholds,dtype=np.float64),
                independent_thresholds,
            ),
        )

        check(
            f"F{outer.fold_id}_W{w}_ACTIONS_CAUSAL_EXACT",
            np.array_equal(
                np.asarray(rr.actions,dtype=np.int8),
                independent_actions,
            ),
        )

        check(
            f"F{outer.fold_id}_W{w}_ACTIONS_DOMAIN",
            np.all(
                np.isin(
                    np.asarray(rr.actions,dtype=np.int8),
                    (0,1,2),
                )
            ),
        )

        check(
            f"F{outer.fold_id}_W{w}_THRESHOLDS_FINITE",
            np.all(
                np.isfinite(
                    np.asarray(rr.thresholds,dtype=np.float64)
                )
            ),
        )

        fold_lengths.append(len(rr.actions))

        print(
            "OPERATIONAL",
            "FOLD=",outer.fold_id,
            "DAY=",outer.validation_day.isoformat(),
            "W=",w,
            "ACTIONS=",rr.action_count,
            "ABSTAIN=",rr.abstain_count,
            "COVERAGE=",rr.coverage,
            "LONG=",rr.long_count,
            "SHORT=",rr.short_count,
            "WARM=",rr.warm_start_count,
        )

        if w==120:
            stored=(
                d37["policy_records"]["S0"]
                   ["folds"][outer.fold_id-1]
                   ["action_sha256"]
            )
            observed=action_sha(
                outer.fold_id,
                rr.actions,
            )
            check(
                f"F{outer.fold_id}_W120_D37_ACTION_SHA_EXACT",
                observed==stored,
                observed,
            )

    check(
        f"F{outer.fold_id}_ALL_WINDOWS_SAME_ROW_COUNT",
        fold_lengths==[1407,1407,1407],
        str(fold_lengths),
    )

    all_action_lengths.extend(fold_lengths)

check(
    "ALL_12_CONTROLLER_FOLDS_1407",
    all_action_lengths==[1407]*12,
)

print()
print("========== EXPLICIT NO-RESULT GUARANTEE ==========")

print("NO_ACTION_PRECISION_CALCULATED=YES")
print("NO_CORRECT_ACTION_COUNT_CALCULATED=YES")
print("NO_FALSE_ACTION_COUNT_CALCULATED=YES")
print("NO_CORRECT_ACTION_RATE_CALCULATED=YES")
print("NO_FALSE_ACTION_RATE_CALCULATED=YES")
print("NO_ACTION_ON_NONE_FRACTION_CALCULATED=YES")
print("NO_FOLD_CORRECTNESS_DELTAS=YES")
print("NO_LOO_CORRECTNESS_DELTAS=YES")
print("NO_TEMPORAL_NULL=YES")
print("NO_SURVIVOR_CLASSIFICATION=YES")
print("NO_PNL=YES")
print("NO_FEES=YES")
print("NO_SLIPPAGE=YES")
print("NO_FORWARD_DATA_OPENED=YES")

print()
print("========== FINAL ==========")

passed=sum(checks)
failed=len(checks)-passed

print(
    "DEV038A_P2_PREFLIGHT_CHECKS_PASS=",
    passed,
)
print(
    "DEV038A_P2_PREFLIGHT_CHECKS_FAIL=",
    failed,
)

if failed==0:
    print(
        "DEV038A_P2_NO_RESULT_REPRODUCTION_PREFLIGHT=PASS"
    )
    raise SystemExit(0)

print(
    "DEV038A_P2_NO_RESULT_REPRODUCTION_PREFLIGHT=FAIL"
)
raise SystemExit(1)
PY

PY_RC=$?

echo
echo "PYTHON_PREFLIGHT_RC=$PY_RC"

echo
echo "========== FOCUSED TESTS =========="

"$PY" -m pytest -q tests/test_dev038a_p2.py
TEST_RC=$?

echo "TEST_RC=$TEST_RC"

echo
echo "========== HARNESS SMOKE =========="

"$PY" -m multimarket.dev038a_p2_harness --smoke
SMOKE_RC=$?

echo "SMOKE_RC=$SMOKE_RC"

echo
echo "========== POST PREFLIGHT =========="

echo "GIT_STATUS:"
git status --short

echo
echo "CANONICAL_OUTPUT_PRESENT:"
if [ -e "$OUT" ]; then
  echo "YES"
else
  echo "NO"
fi

echo
echo "CANONICAL_LOG_PRESENT:"
if [ -e "$LOG" ]; then
  echo "YES"
else
  echo "NO"
fi

echo
echo "STAGING_RESIDUE:"
find /home/emadh/Multi-Market/evidence   -maxdepth 1   -name '.dev038a_p2_final_controller_correctness_v1.part-*'   -print

echo
echo "DEV038A_P2_CANONICAL_NOT_STARTED=YES"
echo "DEV038A_P2_NO_CORRECTNESS_RESULT_OBSERVED=YES"

echo "DEV038A_P1_MUST_NEVER_BE_RERUN=YES"
echo "DEV038A_P0_MUST_NEVER_BE_RERUN=YES"
echo "DEV037_P1_R1_MUST_NEVER_BE_RERUN=YES"
echo "DEV037_P0_R2_MUST_NEVER_BE_RERUN=YES"
echo "DEV037_P0_R1_MUST_NEVER_BE_RERUN=YES"
echo "DEV036_C1_MUST_NEVER_BE_RERUN=YES"

echo "NO_PNL"
echo "NO_FEES"
echo "NO_SLIPPAGE"
echo "NO_FORWARD_DATA_OPENED"
echo "TERMINAL_REMAINS_OPEN=YES"

fi
```

## Pass condition

The preflight passes only if:

- file guards all pass;
- all three frozen parents reproduce exact identity;
- all four validation folds have 1407 rows;
- all 12 S0 controller/fold operational public records reproduce the frozen
  DEV037-P0-R2 artifact exactly;
- independently reconstructed causal thresholds/actions match exactly;
- all four W120 action SHA values reproduce DEV037-P1-R1 exactly;
- focused P2 tests pass;
- harness smoke passes;
- git remains clean;
- canonical P2 output/log remain absent;
- no staging residue exists.

A passing preflight still does not start DEV038-A-P2 canonical correctness.

Only after the complete preflight output is frozen and reviewed may the
single canonical run be authorized.
