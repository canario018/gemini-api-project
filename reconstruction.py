from __future__ import annotations
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Iterable

@dataclass(frozen=True)
class MarketSnapshot:
    event_id: str
    bookmaker: str
    market: str
    selection: str
    line: float | None
    odd: float
    observed_at: datetime
    event_start_at: datetime

@dataclass(frozen=True)
class TimelinePoint:
    bucket: str
    target_at: datetime
    observed_at: datetime | None
    odd: float | None
    bookmaker: str
    market: str
    selection: str
    line: float | None

@dataclass(frozen=True)
class ReconstructedMarket:
    event_id: str
    bookmaker: str
    market: str
    selection: str
    line: float | None
    event_start_at: datetime
    opening_odd: float | None
    opening_at: datetime | None
    closing_odd: float | None
    closing_at: datetime | None
    best_entry_odd: float | None
    best_entry_at: datetime | None
    min_odd: float | None
    max_odd: float | None
    observations: int
    timeline: tuple[TimelinePoint, ...]

DEFAULT_BUCKETS: tuple[tuple[str, timedelta], ...] = (
    ("T-24H", timedelta(hours=24)), ("T-12H", timedelta(hours=12)),
    ("T-6H", timedelta(hours=6)), ("T-3H", timedelta(hours=3)),
    ("T-1H", timedelta(hours=1)), ("T-30M", timedelta(minutes=30)),
    ("T-10M", timedelta(minutes=10)), ("CLOSE", timedelta(0)),
)

def _key(s: MarketSnapshot):
    return (s.event_id, s.bookmaker, s.market, s.selection, s.line)

def _nearest_at_or_before(rows, target):
    candidates = [r for r in rows if r.observed_at <= target]
    return max(candidates, key=lambda r: r.observed_at) if candidates else None

def reconstruct(rows: Iterable[MarketSnapshot], buckets=DEFAULT_BUCKETS) -> list[ReconstructedMarket]:
    groups = defaultdict(list)
    for row in rows:
        if row.odd > 1 and row.event_start_at and row.observed_at <= row.event_start_at:
            groups[_key(row)].append(row)
    out = []
    for key, group in groups.items():
        group.sort(key=lambda x: x.observed_at)
        event_id, bookmaker, market, selection, line = key
        start = group[0].event_start_at
        timeline = []
        for label, delta in buckets:
            target = start - delta
            hit = _nearest_at_or_before(group, target)
            timeline.append(TimelinePoint(label, target, hit.observed_at if hit else None, hit.odd if hit else None, bookmaker, market, selection, line))
        opening = group[0]; closing = group[-1]
        best = max(group, key=lambda x: x.odd)
        out.append(ReconstructedMarket(event_id, bookmaker, market, selection, line, start, opening.odd, opening.observed_at, closing.odd, closing.observed_at, best.odd, best.observed_at, min(x.odd for x in group), max(x.odd for x in group), len(group), tuple(timeline)))
    return out

def true_clv(entry_odd: float, closing_odd: float) -> float:
    if entry_odd <= 1 or closing_odd <= 1:
        return 0.0
    # Positive means the bettor obtained a better price than the close.
    return ((1 / closing_odd) / (1 / entry_odd) - 1.0) * 100.0

def attach_clv(reconstructed: ReconstructedMarket, entry_at: datetime | None = None) -> dict:
    entry_at = entry_at or reconstructed.best_entry_at
    return {**asdict(reconstructed), "clv_percent": true_clv(reconstructed.best_entry_odd or reconstructed.closing_odd or 0, reconstructed.closing_odd or 0) if entry_at else 0.0}
