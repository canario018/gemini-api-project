from __future__ import annotations
from collections import defaultdict, deque
import json, math
from dataclasses import dataclass
from datetime import datetime
from sqlalchemy import select
from app.data_lake.models import CanonicalEventFactModel, TeamEventStatFactModel

ALIASES = {
    "xg": ("xg","expected_goals","expected_goals_for"), "xga": ("xga","expected_goals_against"),
    "shots": ("shots","total_shots"), "shots_on_target": ("shots_on_target","sot"),
    "corners": ("corners","corner_kicks"), "cards": ("cards","yellow_cards","total_cards"),
    "possession": ("possession","possession_pct"), "pace": ("pace",), "ortg": ("ortg","offensive_rating"),
    "drtg": ("drtg","defensive_rating"), "efg": ("efg","efg_pct"), "tsp": ("ts_pct","ts","true_shooting_pct"),
    "turnovers": ("turnovers","tov"), "rebounds": ("rebounds","total_rebounds"),
    "hold_pct": ("hold_pct","service_hold_pct","hold"), "break_pct": ("break_pct","return_games_won_pct","break"),
    "serve_pts_pct": ("serve_points_won_pct","serve_pts_pct"), "return_pts_pct": ("return_points_won_pct","return_pts_pct"),
}

@dataclass
class FeatureBuildResult:
    created: int
    skipped: int


def _metric(metrics, name):
    for k in ALIASES.get(name, (name,)):
        v = metrics.get(k)
        if isinstance(v, (int,float)) and math.isfinite(float(v)): return float(v)
    return None

def _mean(q): return sum(q)/len(q) if q else 0.0

def _ewma(q, decay=.85):
    if not q: return 0.0
    w=[decay**i for i in range(len(q)-1,-1,-1)]
    return sum(x*y for x,y in zip(q,w))/sum(w)

def sport_features(sport, history, context=None):
    context=context or {}; out={}
    for side, h in history.items():
        for key in h:
            if key in {"gf","ga","xg","xga","shots","shots_on_target","corners","cards","pace","ortg","drtg","efg","tsp","turnovers","rebounds","hold_pct","break_pct","serve_pts_pct","return_pts_pct"}:
                out[f"{side}_{key}_recent"]=_ewma(h[key])
        out[f"{side}_sample_count"]=len(h["gf"])
        if sport=="basketball":
            out[f"{side}_net_rating_recent"]=out.get(f"{side}_ortg_recent",0)-out.get(f"{side}_drtg_recent",0)
        if sport=="tennis":
            out[f"{side}_serve_return_strength"]=(out.get(f"{side}_hold_pct_recent",0)+out.get(f"{side}_break_pct_recent",0))/2
    if sport=="football":
        out["attack_diff"]=out.get("home_xg_recent",0)-out.get("away_xg_recent",0)
        out["defense_diff"]=out.get("away_xga_recent",0)-out.get("home_xga_recent",0)
        out["shots_diff"]=out.get("home_shots_recent",0)-out.get("away_shots_recent",0)
    elif sport=="basketball":
        out["net_rating_diff"]=out.get("home_net_rating_recent",0)-out.get("away_net_rating_recent",0)
        out["pace_avg"]=(out.get("home_pace_recent",0)+out.get("away_pace_recent",0))/2
        out["efg_diff"]=out.get("home_efg_recent",0)-out.get("away_efg_recent",0)
    elif sport=="tennis":
        out["serve_return_diff"]=out.get("home_serve_return_strength",0)-out.get("away_serve_return_strength",0)
    for k,v in context.items():
        if isinstance(v,(int,float)) and math.isfinite(float(v)): out[k]=float(v)
    return out

class SportFeatureEngine:
    """Builds point-in-time sport-aware team features. Current event is added only after features are written."""
    VERSION="sport-specific-v1"
    def __init__(self, db, window=10): self.db,self.window=db,window
    def build(self, sport=None, limit=200000):
        from app.data_lake.models import FeatureVectorModel
        q=select(CanonicalEventFactModel).order_by(CanonicalEventFactModel.start_at.asc()).limit(limit)
        if sport: q=q.where(CanonicalEventFactModel.sport==sport)
        events=self.db.execute(q).scalars().all()
        facts=self.db.execute(select(TeamEventStatFactModel).order_by(TeamEventStatFactModel.event_start_at.asc())).scalars().all()
        by={(r.canonical_event_id,r.canonical_team_id):r for r in facts}
        hist=defaultdict(lambda: defaultdict(lambda: deque(maxlen=self.window)))
        created=0; skipped=0
        for e in events:
            if not e.start_at or not e.canonical_home_team_id or not e.canonical_away_team_id: skipped+=1; continue
            h,a=e.canonical_home_team_id,e.canonical_away_team_id
            histories={"home":hist[h],"away":hist[a]}
            f=sport_features((e.sport or "").lower(), histories)
            labels=None
            if e.home_score is not None and e.away_score is not None:
                labels={"home_score":e.home_score,"away_score":e.away_score,"home_win":int(e.home_score>e.away_score),"draw":int(e.home_score==e.away_score),"away_win":int(e.home_score<e.away_score)}
            for tid,side in ((h,"home"),(a,"away")):
                row=self.db.query(FeatureVectorModel).filter_by(entity_type="team",entity_id=tid,canonical_event_id=e.canonical_event_id,feature_set=f"{e.sport}_pre_match",feature_version=self.VERSION,as_of=e.start_at).one_or_none()
                if row is None:
                    row=FeatureVectorModel(entity_type="team",entity_id=tid,canonical_event_id=e.canonical_event_id,sport=e.sport,feature_set=f"{e.sport}_pre_match",feature_version=self.VERSION,as_of=e.start_at); self.db.add(row); created+=1
                row.features_json=json.dumps({k:v for k,v in f.items() if k.startswith(side+"_") or not k.startswith(("home_","away_"))},sort_keys=True)
                row.labels_json=json.dumps(labels,sort_keys=True) if labels else None
                row.sample_count=len(hist[tid]["gf"]); row.source_count=e.source_count; row.completeness=min(1,row.sample_count/max(1,self.window)); row.quality_score=.5*float(e.quality_score)+.5*row.completeness; row.leakage_safe=True
            for tid,side,opp in ((h,"home",a),(a,"away",h)):
                hs,as_=e.home_score,e.away_score
                if hs is not None and as_ is not None:
                    hist[tid]["gf"].append(float(hs if side=="home" else as_)); hist[tid]["ga"].append(float(as_ if side=="home" else hs))
                fact=by.get((e.canonical_event_id,tid))
                if fact:
                    try: m=json.loads(fact.metrics_json or "{}")
                    except Exception: m={}
                    for key in ("xg","xga","shots","shots_on_target","corners","cards","pace","ortg","drtg","efg","tsp","turnovers","rebounds","hold_pct","break_pct","serve_pts_pct","return_pts_pct"):
                        v=_metric(m,key)
                        if v is not None: hist[tid][key].append(v)
        self.db.commit(); return FeatureBuildResult(created,skipped)
