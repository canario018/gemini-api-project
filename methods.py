from __future__ import annotations
from math import log, exp
from app.prediction.probability_engine import clip

class PlattCalibrator:
    def __init__(self,a=1.0,b=0.0): self.a=a; self.b=b
    def fit(self, probabilities, outcomes, epochs=500, lr=.05):
        xs=[log(clip(p)/(1-clip(p))) for p in probabilities]; ys=list(map(int,outcomes)); a=self.a; b=self.b
        for _ in range(epochs):
            ga=gb=0.0
            for x,y in zip(xs,ys):
                z=a*x+b; p=1/(1+exp(-max(-40,min(40,z)))); e=p-y; ga+=e*x; gb+=e
            n=max(1,len(xs)); a-=lr*ga/n; b-=lr*gb/n
        self.a,self.b=a,b; return self
    def transform(self,p):
        z=self.a*log(clip(p)/(1-clip(p)))+self.b
        return 1/(1+exp(-max(-40,min(40,z))))

class IsotonicCalibrator:
    """Simple pool-adjacent-violators calibrator for binary probabilities."""
    def __init__(self): self.points=[]
    def fit(self, probabilities, outcomes):
        pairs=sorted((float(p),int(y)) for p,y in zip(probabilities,outcomes)); blocks=[]
        for p,y in pairs:
            blocks.append([p,p,1,y])
            while len(blocks)>=2 and blocks[-2][3]/blocks[-2][2] > blocks[-1][3]/blocks[-1][2]:
                a=blocks.pop(); b=blocks.pop(); blocks.append([b[0],a[1],b[2]+a[2],b[3]+a[3]])
        self.points=[(b[0],b[1],b[3]/b[2]) for b in blocks]; return self
    def transform(self,p):
        if not self.points: return clip(p)
        p=float(p)
        for lo,hi,v in self.points:
            if lo <= p <= hi: return v
        return self.points[0][2] if p < self.points[0][0] else self.points[-1][2]
