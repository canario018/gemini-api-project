from __future__ import annotations
import math

def sigmoid(x): return 1/(1+math.exp(-max(-30,min(30,x))))

def predict(features):
    net=float(features.get("net_rating_diff",0)); efg=float(features.get("efg_diff",0)); pace=float(features.get("pace_avg",0)); rest=float(features.get("rest_diff",0)); injury=float(features.get("injury_diff",0))
    z=.16*net+.035*efg+.025*rest-.08*injury
    p_home=sigmoid(z); p_away=1-p_home
    base_total=210+2.0*pace if pace else 210.0
    return {"HOME":p_home,"AWAY":p_away,"projected_total":max(120,min(300,base_total)),"model":"rating-basketball-v1"}
