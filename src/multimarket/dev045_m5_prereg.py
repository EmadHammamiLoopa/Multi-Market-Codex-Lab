from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping,Sequence
import math
import numpy as np

from multimarket.dev045_m3_policy import POLICY_IDS

AUTHORIZED_DAYS=(
    "2026-01-01",
    "2026-02-01",
    "2026-03-01",
    "2026-04-01",
    "2026-05-01",
    "2026-06-01",
    "2026-07-01",
)

PRIMARY_QUEUE_MODEL="RISK_ADVERSE"
DIAGNOSTIC_QUEUE_MODEL="LOG_PROB"

BLOCK_HOURS=4
BLOCKS_PER_DAY=6
TOTAL_BLOCKS=len(AUTHORIZED_DAYS)*BLOCKS_PER_DAY

BOOTSTRAP_REPS=20_000
BOOTSTRAP_SEED=450045
FAMILY_ALPHA=0.05

PRIMARY_ENTRY_LATENCY_MS=250
PRIMARY_RESPONSE_LATENCY_MS=250
STRESS_ENTRY_LATENCY_MS=500
STRESS_RESPONSE_LATENCY_MS=500

POSITIVE_DAYS_REQUIRED=4
POSITIVE_DAY_CONCENTRATION_MAX=0.50
PRIMARY_PF_MIN=1.0

class M5PreregError(RuntimeError):
    pass

@dataclass(frozen=True)
class FeeSchedule:
    maker_rate:float
    taker_rate:float
    source:str
    verified:bool

@dataclass(frozen=True)
class Eligibility:
    positive_net_expectancy:bool
    profit_factor_ok:bool
    positive_days_ok:bool
    concentration_ok:bool
    latency_stress_positive:bool
    integrity_ok:bool
    terminal_flat_ok:bool
    fwer_ok:bool

    @property
    def passes(self)->bool:
        return all((
            self.positive_net_expectancy,
            self.profit_factor_ok,
            self.positive_days_ok,
            self.concentration_ok,
            self.latency_stress_positive,
            self.integrity_ok,
            self.terminal_flat_ok,
            self.fwer_ok,
        ))


def validate_family()->None:
    if tuple(POLICY_IDS)!=("M01","M02","M03","M04","M05","M06","M07","M08"):
        raise M5PreregError("family_identity")
    if len(POLICY_IDS)!=8:
        raise M5PreregError("family_count")


def validate_days(days:Sequence[str])->None:
    if tuple(days)!=AUTHORIZED_DAYS:
        raise M5PreregError("authorized_days")


def validate_fee_schedule(fees:FeeSchedule)->None:
    if not fees.verified:
        raise M5PreregError("fee_schedule_unverified")
    if not fees.source or not fees.source.strip():
        raise M5PreregError("fee_source_missing")
    for name,v in (("maker_rate",fees.maker_rate),("taker_rate",fees.taker_rate)):
        x=float(v)
        if not math.isfinite(x):
            raise M5PreregError(f"nonfinite_{name}")
        # Fail closed against absurd or clearly mis-scaled fee inputs.
        if x<-0.01 or x>0.01:
            raise M5PreregError(f"out_of_range_{name}")


def _studentized_mean(x:np.ndarray)->float:
    a=np.asarray(x,dtype=np.float64)
    if a.ndim!=1 or len(a)<2 or np.any(~np.isfinite(a)):
        raise M5PreregError("studentized_input")
    sd=float(np.std(a,ddof=1))
    if sd<=0.0:
        return 0.0
    return float(np.sqrt(len(a))*np.mean(a)/sd)


def block_maxstat_test(
    block_cycle_pnl:Mapping[str,Sequence[float]],
    *,
    reps:int=BOOTSTRAP_REPS,
    seed:int=BOOTSTRAP_SEED,
)->dict:
    validate_family()
    if tuple(block_cycle_pnl.keys())!=tuple(POLICY_IDS):
        raise M5PreregError("family_identity")
    X=np.column_stack([
        np.asarray(block_cycle_pnl[c],dtype=np.float64)
        for c in POLICY_IDS
    ])
    if X.shape!=(TOTAL_BLOCKS,8) or np.any(~np.isfinite(X)):
        raise M5PreregError("block_matrix")
    if int(reps)<=0:
        raise M5PreregError("bootstrap_reps")

    obs=np.asarray([_studentized_mean(X[:,j]) for j in range(8)],dtype=np.float64)
    centered=X-np.mean(X,axis=0,keepdims=True)

    rng=np.random.default_rng(int(seed))
    maxstats=np.empty(int(reps),dtype=np.float64)
    for r in range(int(reps)):
        idx=rng.integers(0,TOTAL_BLOCKS,size=TOTAL_BLOCKS)
        Z=centered[idx]
        stats=np.asarray([_studentized_mean(Z[:,j]) for j in range(8)],dtype=np.float64)
        maxstats[r]=float(np.max(stats))

    pvals={}
    for j,cid in enumerate(POLICY_IDS):
        p=(1.0+float(np.sum(maxstats>=obs[j])))/(1.0+float(reps))
        pvals[cid]=p

    family_p=(1.0+float(np.sum(maxstats>=float(np.max(obs)))))/(1.0+float(reps))
    return {
        "policy_ids":list(POLICY_IDS),
        "observed_studentized":{cid:float(obs[j]) for j,cid in enumerate(POLICY_IDS)},
        "fwer_pvalues":pvals,
        "family_max_observed":float(np.max(obs)),
        "family_max_fwer_p":float(family_p),
        "bootstrap_reps":int(reps),
        "bootstrap_seed":int(seed),
        "block_hours":BLOCK_HOURS,
        "total_blocks":TOTAL_BLOCKS,
    }


def evaluate_eligibility(
    *,
    policy_id:str,
    primary_net_expectancy:float,
    primary_pf:float,
    positive_days:int,
    positive_day_concentration:float,
    stress_net_expectancy:float,
    execution_integrity_failures:int,
    terminal_flat:bool,
    fwer_pvalue:float,
)->Eligibility:
    if policy_id not in POLICY_IDS:
        raise M5PreregError("policy_id")
    vals=(
        primary_net_expectancy,
        primary_pf,
        positive_day_concentration,
        stress_net_expectancy,
        fwer_pvalue,
    )
    if any(not math.isfinite(float(v)) for v in vals):
        raise M5PreregError("nonfinite_metric")
    if int(positive_days)<0 or int(positive_days)>len(AUTHORIZED_DAYS):
        raise M5PreregError("positive_days")
    if not 0.0<=float(positive_day_concentration)<=1.0:
        raise M5PreregError("positive_day_concentration")
    if not 0.0<=float(fwer_pvalue)<=1.0:
        raise M5PreregError("fwer_pvalue")
    return Eligibility(
        positive_net_expectancy=float(primary_net_expectancy)>0.0,
        profit_factor_ok=float(primary_pf)>PRIMARY_PF_MIN,
        positive_days_ok=int(positive_days)>=POSITIVE_DAYS_REQUIRED,
        concentration_ok=float(positive_day_concentration)<=POSITIVE_DAY_CONCENTRATION_MAX,
        latency_stress_positive=float(stress_net_expectancy)>0.0,
        integrity_ok=int(execution_integrity_failures)==0,
        terminal_flat_ok=bool(terminal_flat),
        fwer_ok=float(fwer_pvalue)<=FAMILY_ALPHA,
    )
