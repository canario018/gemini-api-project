from __future__ import annotations
import json, math
from collections import defaultdict, deque
from datetime import datetime, timezone
from app.features.store import FeatureStore

class HistoricalFeaturePipeline:
    """Builds leakage-safe rolling team features from completed historical observations."""
    def __init__(self, db, window: int = 10, version: str = "hist-v1"):
        self.db=db; self.window=window; self.version=version
    @staticmethod
    def _score(metrics, key):
        v=metrics.get(key)
        try: return float(v) if v is not None else None
        except (TypeError, ValueError): return None
    def rebuild(self, observations):
        grouped=defaultdict(list)
        for row in observations:
            metrics=json.loads(row.metrics_json)
            hs=self._score(metrics,"home_score"); as_=self._score(metrics,"away_score")
            if row.home_team and row.away_team and hs is not None and as_ is not None:
                grouped[row.sport].append((row, metrics, hs, as_))
        store=FeatureStore(self.db); created=0
        for sport, games in grouped.items():
            games.sort(key=lambda x: x[0].event_start_at or x[0].observed_at)
            histories=defaultdict(lambda: {"gf":deque(maxlen=self.window),"ga":deque(maxlen=self.window)})
            for row, metrics, hs, as_ in games:
                home=row.home_team; away=row.away_team
                hf=histories[home]; af=histories[away]
                # Features are generated BEFORE current result is added: no target leakage.
                def avg(d,k): return sum(d[k])/len(d[k]) if d[k] else 0.0
                features={
                    "home_goals_for_recent":avg(hf,"gf"), "home_goals_against_recent":avg(hf,"ga"),
                    "away_goals_for_recent":avg(af,"gf"), "away_goals_against_recent":avg(af,"ga"),
                    "home_samples":len(hf["gf"]), "away_samples":len(af["gf"]),
                    "home_advantage":1.0 if row.home_team else 0.0,
                    "target_home_win":1 if hs>as_ else 0,
                    "target_draw":1 if hs==as_ else 0,
                    "target_away_win":1 if hs<as_ else 0,
                    "home_score":hs,"away_score":as_,
                }
                features["home_attack_strength"]=features["home_goals_for_recent"]
                features["away_attack_strength"]=features["away_goals_for_recent"]
                features["home_defense_strength"]=features["home_goals_against_recent"]
                features["away_defense_strength"]=features["away_goals_against_recent"]
                features["goal_diff_form"]=features["home_attack_strength"]-features["away_attack_strength"]
                q=.0
                samples=features["home_samples"]+features["away_samples"]
                quality=min(1.0,samples/(2*self.window)) if self.window else 0.0
                store.save(row.event_id,row.sport,features,self.version,quality_score=quality,source_count=1,completeness=quality,freshness_seconds=0)
                created+=1
                hf["gf"].append(hs); hf["ga"].append(as_); af["gf"].append(as_); af["ga"].append(hs)
        return created
