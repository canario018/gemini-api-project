from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Any

@dataclass(frozen=True)
class HistoricalObservation:
    source: str
    sport: str
    event_id: str
    observed_at: str
    event_start_at: str | None = None
    competition: str | None = None
    home_team: str | None = None
    away_team: str | None = None
    team_id: str | None = None
    player_id: str | None = None
    metrics: dict[str, Any] = field(default_factory=dict)
    raw: dict[str, Any] = field(default_factory=dict)
    source_url: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
