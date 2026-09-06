from __future__ import annotations
from abc import ABC, abstractmethod
from datetime import date
from typing import Iterable
from app.data_harvest.contracts import HistoricalObservation

class SportsStatsProvider(ABC):
    name: str
    sport: str

    @abstractmethod
    def collect(self, start: date, end: date) -> Iterable[HistoricalObservation]:
        raise NotImplementedError
