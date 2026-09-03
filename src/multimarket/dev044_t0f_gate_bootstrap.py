from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

import math
import numpy as np

from . import dev044_t0_strategy_contract as contract

EXPERIMENT_ID="DEV044-T0F"
DESIGN_VERSION="viability-gates-block-maxstat-v1"

PRIMARY_COST_BPS_RT=10.0
STRESS_COST_BPS_RT=16.0
ENTRY_LATENCY_MS=250
RESPONSE_LATENCY_MS=250
LATENCY_STRESS_MS=500

BLOCK_HOURS=4
BLOCKS_PER_DAY=6
DAYS=4
TOTAL_BLOCKS=24
BOOTSTRAP_REPS=20_000
BOOTSTRAP_SEED=440044

MECHANICAL_MIN_ACTIVE_POOLED=100
MECHANICAL_MIN_ACTIVE_EACH_DAY=1

MIN_ACCEPTED_TRADES_POOLED=40
MIN_ACCEPTED_TRADES_EACH_DAY=5
MIN_ACCEPTED_LONG=10
MIN_ACCEPTED_SHORT=10

MIN_PRIMARY_NET_EXPECTANCY_BPS=0.0
MIN_PRIMARY_PROFIT_FACTOR=1.10
MIN_POSITIVE_DAYS=3
MAX_POSITIVE_DAY_CONCENTRATION=0.60
MAX_DRAWDOWN_BPS=320.0
MIN_STRESS_NET_EXPECTANCY_BPS=0.0
MIN_LATENCY_STRESS_NET_EXPECTANCY_BPS=0.0

FAMILY_ALPHA=0.05

RANK_KEYS=(
    "min_loo_primary_net_expectancy_bps",
    "median_daily_primary_net_bps",
    "pooled_primary_net_expectancy_bps",
    "stress_cost_net_expectancy_bps",
    "primary_profit_factor",
    "negative_max_drawdown_bps",
    "negative_positive_day_concentration",
    "accepted_trades",
    "candidate_id",
)

class T0FGateError(RuntimeError):
    pass

@dataclass(frozen=True)
class MechanicalSupport:
    candidate_id:str
    active_pooled:int
    active_by_day:tuple[int,int,int,int]

@dataclass(frozen=True)
class EconomicMetrics:
    candidate_id:str
    execution_integrity_failures:int
    accepted_trades:int
    accepted_by_day:tuple[int,int,int,int]
    accepted_long:int
    accepted_short:int
    pooled_primary_net_expectancy_bps:float
    primary_profit_factor:float
    positive_days:int
    loo_primary_net_expectancy_bps:tuple[float,float,float,float]
    positive_day_concentration:float
    max_drawdown_bps:float
    stress_cost_net_expectancy_bps:float
    latency_stress_net_expectancy_bps:float
    median_daily_primary_net_bps:float

def validate_candidate_id(candidate_id:str)->None:
    if candidate_id not in contract.CANDIDATE_IDS:
        raise T0FGateError(f"candidate_id:{candidate_id}")

def mechanical_eligible(x:MechanicalSupport)->bool:
    validate_candidate_id(x.candidate_id)
    if x.active_pooled<0 or len(x.active_by_day)!=4 or any(v<0 for v in x.active_by_day):
        raise T0FGateError("mechanical_support")
    if x.active_pooled!=sum(x.active_by_day):
        raise T0FGateError("mechanical_support_sum")
    return (
        x.active_pooled>=MECHANICAL_MIN_ACTIVE_POOLED
        and min(x.active_by_day)>=MECHANICAL_MIN_ACTIVE_EACH_DAY
    )

def _finite(x:float)->bool:
    return math.isfinite(float(x))

def economic_gate_results(x:EconomicMetrics)->dict[str,bool]:
    validate_candidate_id(x.candidate_id)
    if len(x.accepted_by_day)!=4 or len(x.loo_primary_net_expectancy_bps)!=4:
        raise T0FGateError("economic_shape")
    vals=(
        x.pooled_primary_net_expectancy_bps,
        x.primary_profit_factor,
        *x.loo_primary_net_expectancy_bps,
        x.positive_day_concentration,
        x.max_drawdown_bps,
        x.stress_cost_net_expectancy_bps,
        x.latency_stress_net_expectancy_bps,
        x.median_daily_primary_net_bps,
    )
    if any(not _finite(v) for v in vals):
        raise T0FGateError("economic_nonfinite")
    if any(v<0 for v in x.accepted_by_day):
        raise T0FGateError("accepted_by_day")
    if x.accepted_trades!=sum(x.accepted_by_day):
        raise T0FGateError("accepted_sum")
    if x.accepted_long<0 or x.accepted_short<0:
        raise T0FGateError("side_counts")
    if x.accepted_long+x.accepted_short!=x.accepted_trades:
        raise T0FGateError("side_sum")
    if not (0.0<=x.positive_day_concentration<=1.0):
        raise T0FGateError("concentration")
    if x.max_drawdown_bps<0:
        raise T0FGateError("drawdown")
    return {
        "execution_integrity":x.execution_integrity_failures==0,
        "accepted_trades_pooled":x.accepted_trades>=MIN_ACCEPTED_TRADES_POOLED,
        "accepted_trades_each_day":min(x.accepted_by_day)>=MIN_ACCEPTED_TRADES_EACH_DAY,
        "accepted_long":x.accepted_long>=MIN_ACCEPTED_LONG,
        "accepted_short":x.accepted_short>=MIN_ACCEPTED_SHORT,
        "primary_net_positive":x.pooled_primary_net_expectancy_bps>MIN_PRIMARY_NET_EXPECTANCY_BPS,
        "primary_profit_factor":x.primary_profit_factor>=MIN_PRIMARY_PROFIT_FACTOR,
        "positive_days":x.positive_days>=MIN_POSITIVE_DAYS,
        "all_loo_positive":min(x.loo_primary_net_expectancy_bps)>0.0,
        "positive_day_concentration":x.positive_day_concentration<=MAX_POSITIVE_DAY_CONCENTRATION,
        "max_drawdown":x.max_drawdown_bps<=MAX_DRAWDOWN_BPS,
        "stress_cost_positive":x.stress_cost_net_expectancy_bps>MIN_STRESS_NET_EXPECTANCY_BPS,
        "latency_stress_positive":x.latency_stress_net_expectancy_bps>MIN_LATENCY_STRESS_NET_EXPECTANCY_BPS,
    }

def economic_eligible(x:EconomicMetrics)->bool:
    return all(economic_gate_results(x).values())

def ranking_tuple(x:EconomicMetrics):
    validate_candidate_id(x.candidate_id)
    return (
        min(x.loo_primary_net_expectancy_bps),
        x.median_daily_primary_net_bps,
        x.pooled_primary_net_expectancy_bps,
        x.stress_cost_net_expectancy_bps,
        x.primary_profit_factor,
        -x.max_drawdown_bps,
        -x.positive_day_concentration,
        x.accepted_trades,
        # lexical candidate ID is the final deterministic tie-breaker;
        # callers sort descending on the numeric prefix and ascending on ID.
        x.candidate_id,
    )

def _studentized_mean(x:np.ndarray)->float:
    a=np.asarray(x,dtype=np.float64)
    if a.ndim!=1 or len(a)<2 or np.any(~np.isfinite(a)):
        raise T0FGateError("studentized_input")
    sd=float(np.std(a,ddof=1))
    if sd<=0.0:
        return 0.0
    return float(np.sqrt(len(a))*np.mean(a)/sd)

def block_maxstat_test(
    block_pnl:Mapping[str,Sequence[float]],
    *,
    reps:int=BOOTSTRAP_REPS,
    seed:int=BOOTSTRAP_SEED,
)->dict:
    # All 32 candidates remain in the multiplicity family, including those
    # that are mechanically/economically ineligible.
    if tuple(block_pnl.keys())!=contract.CANDIDATE_IDS:
        raise T0FGateError("family_identity")
    X=np.column_stack([
        np.asarray(block_pnl[c],dtype=np.float64)
        for c in contract.CANDIDATE_IDS
    ])
    if X.shape!=(TOTAL_BLOCKS,32) or np.any(~np.isfinite(X)):
        raise T0FGateError("block_matrix")
    if reps<=0:
        raise T0FGateError("bootstrap_reps")

    obs=np.asarray([_studentized_mean(X[:,j]) for j in range(32)],dtype=np.float64)
    centered=X-np.mean(X,axis=0,keepdims=True)

    rng=np.random.default_rng(int(seed))
    maxstats=np.empty(int(reps),dtype=np.float64)

    for r in range(int(reps)):
        idx=rng.integers(0,TOTAL_BLOCKS,size=TOTAL_BLOCKS)
        Z=centered[idx]
        stats=np.asarray([_studentized_mean(Z[:,j]) for j in range(32)],dtype=np.float64)
        maxstats[r]=float(np.max(stats))

    pvals={}
    for j,cid in enumerate(contract.CANDIDATE_IDS):
        p=(1.0+float(np.sum(maxstats>=obs[j])))/(1.0+float(reps))
        pvals[cid]=p

    family_p=(1.0+float(np.sum(maxstats>=float(np.max(obs)))))/(1.0+float(reps))

    return {
        "candidate_ids":list(contract.CANDIDATE_IDS),
        "observed_studentized":{cid:float(obs[j]) for j,cid in enumerate(contract.CANDIDATE_IDS)},
        "fwer_pvalues":pvals,
        "family_max_observed":float(np.max(obs)),
        "family_max_fwer_p":float(family_p),
        "bootstrap_reps":int(reps),
        "bootstrap_seed":int(seed),
        "block_hours":BLOCK_HOURS,
        "total_blocks":TOTAL_BLOCKS,
    }

def candidate_passes_family_control(candidate_id:str,result:Mapping)->bool:
    validate_candidate_id(candidate_id)
    p=float(result["fwer_pvalues"][candidate_id])
    return p<=FAMILY_ALPHA
