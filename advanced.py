from __future__ import annotations
from dataclasses import dataclass
from collections import defaultdict
from typing import Iterable

@dataclass(frozen=True)
class Quote:
    bookmaker: str
    selection: str
    odd: float
    line: float|None = None
    observed_at: object|None = None

@dataclass(frozen=True)
class ArbitrageResult:
    market: str
    line: float|None
    inverse_sum: float
    margin_percent: float
    selections: tuple
    stake_allocations: dict


def no_vig(odds: dict[str,float]) -> dict[str,float]:
    inv={k:1.0/v for k,v in odds.items() if v and v>1}
    s=sum(inv.values())
    return {k:v/s for k,v in inv.items()} if s else {}


def overround(odds: dict[str,float]) -> float:
    return sum(1.0/v for v in odds.values() if v and v>1)-1.0


def best_prices(quotes: Iterable[Quote]):
    out={}
    for q in quotes:
        if q.odd and q.odd>1 and (q.selection not in out or q.odd>out[q.selection].odd):
            out[q.selection]=q
    return out


def detect_arbitrage(quotes: Iterable[Quote], market: str="", line=None, bankroll: float=100.0):
    best=best_prices(quotes)
    if len(best)<2: return None
    inv=sum(1.0/q.odd for q in best.values())
    if inv>=1.0: return None
    allocations={s: bankroll*(1/q.odd)/inv for s,q in best.items()}
    return ArbitrageResult(market,line,inv,(1/inv-1)*100,tuple(sorted(best)),allocations)


def stale_odds(quotes: Iterable[Quote], now, max_age_seconds: float=300):
    return [q for q in quotes if q.observed_at is not None and (now-q.observed_at).total_seconds()>max_age_seconds]


def movement(open_odd: float, current_odd: float):
    if not open_odd or not current_odd or open_odd<=1 or current_odd<=1: return {"direction":"UNKNOWN","absolute":0.0,"percent":0.0,"implied_probability_change_pp":0.0}
    pct=(current_odd/open_odd-1)*100
    direction="SHORTENING" if current_odd<open_odd else "DRIFTING" if current_odd>open_odd else "STABLE"
    return {"direction":direction,"absolute":current_odd-open_odd,"percent":pct,"implied_probability_change_pp":(1/current_odd-1/open_odd)*100}


def market_matrix(quotes: Iterable[Quote]):
    out=defaultdict(list)
    for q in quotes: out[q.selection].append(q)
    return {s: sorted(v,key=lambda q:q.odd,reverse=True) for s,v in out.items()}
