from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from app.normalization.canonical import canonical_sport, canonical_team, event_key, parse_event_start
@dataclass(frozen=True)
class EventIdentity:
    canonical_id: str
    sport: str
    home_team: str
    away_team: str
    league: str
    start_at: datetime | None
def build_event_identity(*, sport, home_team, away_team, league='', event_start_at=None):
    start=parse_event_start(event_start_at)
    return EventIdentity(event_key(sport=sport,home_team=home_team,away_team=away_team,league=league,event_start_at=start),canonical_sport(sport),canonical_team(home_team),canonical_team(away_team),league,start)
def events_match(a,b,*,max_start_diff_seconds=120):
    if canonical_sport(a.sport)!=canonical_sport(b.sport): return False
    if {canonical_team(a.home_team),canonical_team(a.away_team)} != {canonical_team(b.home_team),canonical_team(b.away_team)}: return False
    sa,sb=parse_event_start(getattr(a,'event_start_at',None)),parse_event_start(getattr(b,'event_start_at',None))
    return not(sa and sb and abs((sa-sb).total_seconds())>max_start_diff_seconds)
