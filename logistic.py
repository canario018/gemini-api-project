from __future__ import annotations
from dataclasses import dataclass
from math import exp

def sigmoid(z):
    if z < -40: return 0.0
    if z > 40: return 1.0
    return 1/(1+exp(-z))

@dataclass
class LogisticModel:
    weights: list[float]
    bias: float
    feature_names: tuple[str,...]
    learning_rate: float = .03
    l2: float = .001
    epochs: int = 800
    @classmethod
    def train(cls, X, y, feature_names, learning_rate=.03, l2=.001, epochs=800):
        X=list(X); y=list(map(int,y)); n=len(X); d=len(feature_names)
        if n == 0: raise ValueError("empty training set")
        w=[0.0]*d; b=0.0
        for _ in range(epochs):
            gw=[0.0]*d; gb=0.0
            for xi,yi in zip(X,y):
                p=sigmoid(b+sum(a*c for a,c in zip(w,xi))); e=p-yi
                gb += e
                for j,x in enumerate(xi): gw[j]+=e*x
            for j in range(d): w[j]-=learning_rate*(gw[j]/n+l2*w[j])
            b-=learning_rate*gb/n
        return cls(w,b,tuple(feature_names),learning_rate,l2,epochs)
    def predict_proba(self, x): return sigmoid(self.bias+sum(a*c for a,c in zip(self.weights,x)))
    def to_dict(self): return {"type":"logistic","weights":self.weights,"bias":self.bias,"feature_names":list(self.feature_names),"learning_rate":self.learning_rate,"l2":self.l2,"epochs":self.epochs}
