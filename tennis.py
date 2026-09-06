from __future__ import annotations
import math

def sigmoid(x): return 1/(1+math.exp(-max(-30,min(30,x))))

def predict(features):
    diff=float(features.get("serve_return_diff",0)); rest=float(features.get("rest_diff",0)); surface=float(features.get("surface_edge",0)); z=.06*diff+.02*rest+.04*surface
    p=sigmoid(z); return {"HOME":p,"AWAY":1-p,"model":"serve-return-tennis-v1"}
