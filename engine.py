from __future__ import annotations
import json, logging, time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from sqlalchemy.orm import Session
from app.collectors.registry import build_collectors
from app.database.repositories import OddsRepository
from app.database.models import OddSnapshotModel
from app.monitor.models import MonitorRunModel, CollectorHealthModel, MarketChangeModel
from app.signals.engine import build_market_signals
from app.intelligence_center import rank_signals, build_intelligence_center, export_intelligence_center
from app.signals.persistence import persist_signals, export_signals_json
from app.intelligence_persistence import persist_ranking
from app.value.engine import analyze_database as analyze_value_database
from app.value.persistence import persist_value_opportunities
from app.diagnostics.quality import assess_records

logger = logging.getLogger("MONITOR")

def utcnow_naive(): return datetime.now(timezone.utc).replace(tzinfo=None)

def _key(r):
    event = getattr(r, "canonical_event_id", None) or f"{r.sport}|{r.home_team}|{r.away_team}|{r.event_start_at}"
    market = getattr(r, "canonical_market", None) or r.market_type
    selection = getattr(r, "canonical_selection", None) or r.selection_code
    return f"{event}|{market}|{r.line}|{r.bookmaker}|{selection}"

def _dict_key(r):
    event = r.get("canonical_event_id") or f"{r.get('sport')}|{r.get('home_team')}|{r.get('away_team')}|{r.get('event_start_at')}"
    market = r.get("canonical_market") or r.get("market_type")
    selection = r.get("canonical_selection") or r.get("selection_code")
    return f"{event}|{market}|{r.get('line')}|{r.get('bookmaker')}|{selection}"

def collect_once(settings):
    collectors = build_collectors(settings)
    started = time.perf_counter()
    results = []
    with ThreadPoolExecutor(max_workers=max(1, len(collectors))) as executor:
        futures = {executor.submit(_collect_one, c): c for c in collectors}
        for future in as_completed(futures):
            results.append(future.result())
    elapsed = (time.perf_counter() - started) * 1000
    return collectors, results, elapsed

def _collect_one(collector):
    t0 = time.perf_counter()
    try:
        raw = collector.fetch_raw_data()
        records = collector.normalize_data(raw)
        return {"name": collector.sportsbook_name, "records": records, "raw": raw, "error": None, "latency_ms": (time.perf_counter()-t0)*1000, "collector": collector}
    except Exception as exc:
        logger.exception("Collector %s falhou", collector.sportsbook_name)
        return {"name": collector.sportsbook_name, "records": [], "raw": None, "error": exc, "latency_ms": (time.perf_counter()-t0)*1000, "collector": collector}

def detect_changes(db: Session, records: list[dict], *, threshold_percent: float = 0.01, threshold_absolute: float = 0.001, lookback_minutes: int = 15, detected_at: datetime | None = None):
    """Detecta somente mudanças relevantes contra o último snapshot anterior da mesma chave.
    A chave usa o mesmo evento/mercado/seleção canônicos do sistema; nenhuma execução de aposta ocorre.
    """
    now = detected_at or utcnow_naive()
    cutoff = now.timestamp() - lookback_minutes * 60
    candidates = db.query(OddSnapshotModel).filter(OddSnapshotModel.collected_at >= datetime.fromtimestamp(cutoff, tz=timezone.utc).replace(tzinfo=None)).order_by(OddSnapshotModel.collected_at.desc(), OddSnapshotModel.id.desc()).all()
    latest = {}
    for row in candidates:
        key = _key(row)
        if key not in latest: latest[key] = row
    changes = []
    for r in records:
        k = _dict_key(r)
        prev = latest.get(k)
        current = float(r["odd"])
        previous = float(prev.odd) if prev else None
        if previous is None:
            ctype = "NEW"
            delta = 0.0; pct = 0.0; direction = "NEW"
        else:
            delta = current - previous
            pct = (delta / previous * 100.0) if previous else 0.0
            if abs(delta) < threshold_absolute and abs(pct) < threshold_percent:
                continue
            direction = "UP" if delta > 0 else "DOWN"
            ctype = "ODD_CHANGE"
        change = {
            "detected_at": now.isoformat(), "change_key": k,
            "event_key": r.get("canonical_event_id") or k.split("|", 1)[0],
            "canonical_event_id": r.get("canonical_event_id"), "bookmaker": r.get("bookmaker"),
            "market_type": r.get("canonical_market") or r.get("market_type"), "line": r.get("line"),
            "selection_code": r.get("canonical_selection") or r.get("selection_code"),
            "previous_odd": previous, "current_odd": current, "delta": delta,
            "delta_percent": pct, "direction": direction, "change_type": ctype,
            "event_start_at": str(r.get("event_start_at")) if r.get("event_start_at") else None,
        }
        changes.append(change)
    return changes

def persist_changes(db: Session, changes: list[dict]):
    for c in changes:
        db.add(MarketChangeModel(detected_at=datetime.fromisoformat(c["detected_at"]), change_key=c["change_key"], event_key=c["event_key"], canonical_event_id=c.get("canonical_event_id"), bookmaker=c["bookmaker"], market_type=c["market_type"], line=c.get("line"), selection_code=c["selection_code"], previous_odd=c.get("previous_odd"), current_odd=c["current_odd"], delta=c["delta"], delta_percent=c["delta_percent"], direction=c["direction"], change_type=c["change_type"], payload_json=json.dumps(c, ensure_ascii=False)))
    db.commit(); return len(changes)

def run_cycle(settings, *, session_factory=None, run_signals=True, min_strength=40.0, bankroll=1000.0, change_threshold_percent=0.01, change_threshold_absolute=0.001):
    started_at = utcnow_naive(); run = MonitorRunModel(started_at=started_at, status="RUNNING")
    db = None
    try:
        collectors, results, _ = collect_once(settings)
        normalized = [r for x in results for r in x["records"]]
        errors = [x for x in results if x["error"] is not None]
        if session_factory is None:
            from app.database.connection import SessionLocal
            session_factory = SessionLocal
        db = session_factory()
        run.collectors_count = len(collectors); run.records_normalized = len(normalized); run.error_count = len(errors)
        db.add(run); db.commit(); db.refresh(run)
        for x in results:
            q = assess_records(x["records"])
            db.add(CollectorHealthModel(run_id=run.id, checked_at=started_at, bookmaker=x["name"], status="ERROR" if x["error"] else ("EMPTY" if len(x["records"]) == 0 else "OK"), latency_ms=x["latency_ms"], records_count=len(x["records"]), http_status=getattr(x.get("collector"), "last_http_status", None), response_bytes=getattr(x.get("collector"), "last_response_bytes", None), unique_events=q["unique_events"], duplicate_rate_percent=q["duplicate_rate_percent"], missing_start_percent=q["missing_start_percent"], supported_market_percent=q["supported_market_percent"], quality_score=q["quality_score"], error_type=type(x["error"]).__name__ if x["error"] else None, error_message=str(x["error"]) if x["error"] else None))
        db.commit()
        # Detecta contra o estado anterior ao ciclo. Só depois persiste os novos snapshots.
        changes = detect_changes(db, normalized, threshold_percent=change_threshold_percent, threshold_absolute=change_threshold_absolute, detected_at=started_at)
        persisted_changes = persist_changes(db, changes)
        repo = OddsRepository(db, settings.idempotency_window_seconds)
        saved = sum(1 for r in normalized if repo.save_snapshot(r))
        signal_count = ranking_count = value_count = 0
        if run_signals:
            signals = build_market_signals(db, windows=(24,48,72,96,120), min_strength=min_strength, bankroll=bankroll)
            persist_signals(db, signals)
            export_signals_json(signals)
            ranked = rank_signals(signals, top_n=len(signals))
            persist_ranking(db, ranked)
            export_intelligence_center(build_intelligence_center(signals, top_n=50))
            signal_count, ranking_count = len(signals), len(ranked)
        values = analyze_value_database(db, lookback_hours=24, min_ev_percent=3.0, min_edge_percent=1.0, min_bookmakers=2, max_age_seconds=300)
        value_count = persist_value_opportunities(db, values) if values else 0
        run.snapshots_saved = saved; run.changes_detected = persisted_changes; run.signals_count = signal_count; run.rankings_count = ranking_count; run.value_opportunities_count = value_count
        run.status = "PARTIAL" if errors else "OK"; run.finished_at = utcnow_naive(); run.duration_seconds = (run.finished_at-started_at).total_seconds(); run.message = "; ".join(f'{x["name"]}: {x["error"]}' for x in errors)[:4000] if errors else "Cycle completed"
        db.commit()
        return {"run_id": run.id, "status": run.status, "collectors": len(collectors), "normalized": len(normalized), "saved": saved, "changes": persisted_changes, "signals": signal_count, "rankings": ranking_count, "value_opportunities": value_count, "errors": len(errors)}
    except Exception as exc:
        if db is not None:
            db.rollback(); run.status="ERROR"; run.finished_at=utcnow_naive(); run.duration_seconds=(run.finished_at-started_at).total_seconds(); run.message=str(exc)[:4000]; db.add(run); db.commit()
        raise
    finally:
        if db is not None: db.close()
