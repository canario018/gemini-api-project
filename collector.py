from __future__ import annotations
import json, time
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from app.data_harvest.persistence.repository import HistoricalRepository, SourceRunRepository
from app.data_harvest.contracts import HistoricalObservation

@dataclass
class CollectionResult:
    source: str; status: str; records: int; elapsed_ms: float; error: str | None = None

class HistoricalCollector:
    def __init__(self, db, raw_dir: str = "data/raw/historical"):
        self.db = db; self.raw_dir = Path(raw_dir); self.raw_dir.mkdir(parents=True, exist_ok=True)
    def run(self, provider, start: date, end: date) -> CollectionResult:
        started = time.perf_counter(); run = SourceRunRepository(self.db).start(provider.name, start.isoformat(), end.isoformat()); repo = HistoricalRepository(self.db); count = 0
        raw_path = self.raw_dir / f"{provider.name}_{start.isoformat()}_{end.isoformat()}.jsonl"
        try:
            with raw_path.open("w", encoding="utf-8") as fh:
                for obs in provider.collect(start, end):
                    repo.save(obs); fh.write(json.dumps(obs.to_dict(), ensure_ascii=False, default=str) + "\n"); count += 1
            repo.commit(); elapsed=(time.perf_counter()-started)*1000; SourceRunRepository(self.db).finish(run, "SUCCESS", count, latency_ms=elapsed)
            return CollectionResult(provider.name,"SUCCESS",count,round(elapsed,2))
        except Exception as exc:
            self.db.rollback(); elapsed=(time.perf_counter()-started)*1000; SourceRunRepository(self.db).finish(run,"FAILED",count,error=str(exc),latency_ms=elapsed)
            return CollectionResult(provider.name,"FAILED",count,round(elapsed,2),str(exc))
