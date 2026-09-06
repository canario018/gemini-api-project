from __future__ import annotations

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class OddPayload(BaseModel):
    collected_at: datetime
    bookmaker: str = Field(..., min_length=1)
    source_url: str = Field(..., min_length=1)
    sport: str = Field(..., min_length=1)
    league: str = Field(..., min_length=1)
    event_id: str = Field(..., min_length=1)
    event_start_at: Optional[datetime] = None
    home_team: str = Field(..., min_length=1)
    away_team: str = Field(..., min_length=1)
    market_name: str = Field(..., min_length=1)
    market_type: str = Field(..., min_length=1)
    selection_name: str = Field(..., min_length=1)
    selection_code: str = Field(..., min_length=1)
    line: Optional[float] = None
    odd: float = Field(..., gt=1.0)
    currency: str = "BRL"
    raw_key: str = Field(..., min_length=1)

    @field_validator("odd")
    @classmethod
    def validate_odd(cls, v: float) -> float:
        if v <= 1.0:
            raise ValueError("A odd deve ser estritamente maior que 1.0")
        return v
