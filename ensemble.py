from __future__ import annotations
from dataclasses import dataclass
from app.prediction.probability_engine import clip

@dataclass(frozen=True)
class EnsembleOutput:
    probability: float
    agreement: float
    weights: dict[str,float]

class Ensemble:
    def combine(self, probabilities: dict[str,float], weights: dict[str,float] | None=None) -> EnsembleOutput:
        if not probabilities: raise ValueError("no probabilities")
        weights=weights or {k:1.0 for k in probabilities}
        usable=[(k,clip(v),max(0,float(weights.get(k,0)))) for k,v in probabilities.items()]
        denom=sum(w for _,_,w in usable)
        if denom<=0: raise ValueError("invalid weights")
        p=sum(v*w for _,v,w in usable)/denom
        vals=[v for _,v,_ in usable]
        dispersion=max(vals)-min(vals) if len(vals)>1 else 0
        return EnsembleOutput(p,max(0,min(100,100*(1-dispersion/.5))),{k:w/denom for k,_,w in usable})
