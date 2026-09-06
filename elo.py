from __future__ import annotations
from dataclasses import dataclass
from math import pow

@dataclass
class EloModel:
    rating_home: float = 1500.0
    rating_away: float = 1500.0
    k: float = 20.0
    home_advantage: float = 60.0
    def probability(self, home_rating: float | None=None, away_rating: float | None=None) -> float:
        h=home_rating if home_rating is not None else self.rating_home
        a=away_rating if away_rating is not None else self.rating_away
        return 1/(1+pow(10, -((h+self.home_advantage)-a)/400))
    @staticmethod
    def update(home: float, away: float, result: float, k=20, home_advantage=60):
        p=1/(1+pow(10,-((home+home_advantage)-away)/400)); d=k*(result-p)
        return home+d, away-d
