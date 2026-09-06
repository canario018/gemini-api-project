from __future__ import annotations
from .providers import *

def default_providers():
    return [SofaScoreFootballProvider(), FBrefFootballProvider(), BasketballReferenceProvider(), MLBStatsProvider(), NHLProvider(), ATPStatsProvider(), Formula1OfficialProvider(), TheOddsAPIProvider()]
