from __future__ import annotations
from dataclasses import dataclass
from collections import defaultdict
import math

@dataclass(frozen=True)
class BacktestTrade:
    timestamp: object
    event_id: str
    selection: str
    probability: float
    odds: float
    outcome: int
    stake: float=1.0
    closing_odds: float|None=None

@dataclass(frozen=True)
class BacktestReport:
    trades: int
    wins: int
    turnover: float
    profit: float
    roi_percent: float
    hit_rate_percent: float
    max_drawdown: float
    sharpe: float
    avg_clv_percent: float
    brier_score: float
    log_loss: float


def _returns(trades):
    return [t.stake*(t.odds-1) if t.outcome else -t.stake for t in trades]

def _mdd(rs):
    peak=eq=dd=0.0
    for x in rs:
        eq+=x; peak=max(peak,eq); dd=max(dd,peak-eq)
    return dd

def _sharpe(rs):
    if len(rs)<2:return 0.0
    m=sum(rs)/len(rs); v=sum((x-m)**2 for x in rs)/(len(rs)-1)
    return m/math.sqrt(v) if v>0 else 0.0

def _brier(ts): return sum((t.probability-t.outcome)**2 for t in ts)/len(ts) if ts else 0.0

def _logloss(ts):
    if not ts:return 0.0
    return -sum(t.outcome*math.log(max(1e-15,min(1-1e-15,t.probability)))+(1-t.outcome)*math.log(max(1e-15,min(1-1e-15,1-t.probability))) for t in ts)/len(ts)

def _clv(t):
    if t.closing_odds is None or t.closing_odds<=1:return 0.0
    return ((1/t.closing_odds)/(1/t.odds)-1)*100

def run(trades):
    ts=sorted(list(trades),key=lambda t:t.timestamp); rs=_returns(ts); turnover=sum(t.stake for t in ts)
    return BacktestReport(len(ts),sum(t.outcome for t in ts),turnover,sum(rs),(sum(rs)/turnover*100 if turnover else 0), (sum(t.outcome for t in ts)/len(ts)*100 if ts else 0),_mdd(rs),_sharpe(rs),sum(_clv(t) for t in ts)/len(ts) if ts else 0,_brier(ts),_logloss(ts))

def walk_forward(events, train_window=500, test_window=100, min_train=50, predictor=None):
    """Chronological walk-forward. predictor(train, test_event) -> BacktestTrade|None."""
    ordered=sorted(events,key=lambda x:x.timestamp); reports=[]; start=train_window if len(ordered)>=train_window else min_train
    i=start
    while i<len(ordered):
        train=ordered[max(0,i-train_window):i]; test=ordered[i:i+test_window]
        if len(train)<min_train: break
        trades=[t for e in test if (t:=predictor(train,e)) is not None]
        reports.append({"train_start":train[0].timestamp,"train_end":train[-1].timestamp,"test_start":test[0].timestamp,"test_end":test[-1].timestamp,"report":run(trades)})
        i+=test_window
    return reports
