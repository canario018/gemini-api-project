from __future__ import annotations
from app.prediction.probability_engine import football_score_matrix, football_1x2_from_matrix, football_ou_from_matrix, football_btts_from_matrix

def estimate_xg(features: dict) -> tuple[float,float]:
    ha=float(features.get("home_attack_strength",1.2) or 1.2); aa=float(features.get("away_attack_strength",1.0) or 1.0)
    hd=float(features.get("home_defense_strength",1.2) or 1.2); ad=float(features.get("away_defense_strength",1.2) or 1.2)
    rest=float(features.get("rest_diff",0.0) or 0.0)
    injury_h=float(features.get("home_injury_score",0.0) or 0.0); injury_a=float(features.get("away_injury_score",0.0) or 0.0)
    home=max(.05,.65*ha+.35*(2.2/ad)+.03*rest-.15*injury_h)
    away=max(.05,.65*aa+.35*(2.0/hd)-.03*rest-.15*injury_a)
    return min(4.5,home), min(4.5,away)

def predict_football(features: dict) -> dict:
    hx,ax=estimate_xg(features); matrix=football_score_matrix(hx,ax)
    out=football_1x2_from_matrix(matrix); out.update({"OVER_2_5":football_ou_from_matrix(matrix,2.5)["OVER"],"UNDER_2_5":football_ou_from_matrix(matrix,2.5)["UNDER"],"BTTS_YES":football_btts_from_matrix(matrix)["YES"],"BTTS_NO":football_btts_from_matrix(matrix)["NO"],"home_xg":hx,"away_xg":ax})
    return out
