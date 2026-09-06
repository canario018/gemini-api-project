from __future__ import annotations

import hashlib
import json
import math
import unicodedata
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from app.analytics.arbitrage import Surebet, event_identity, latest_rows
from app.database.models import OddSnapshotModel
from app.opportunities.models import SurebetAlertModel, SurebetOpportunityModel, SurebetObservationModel
from app.opportunities.temporal import movement_series, utcnow_naive


def _norm(v: str) -> str:
    return " ".join(unicodedata.normalize("NFKD", v or "").encode("ascii", "ignore").decode("ascii").lower().split())


def fingerprint(sb: Surebet) -> str:
    legs = "|".join(f"{x.bookmaker}:{x.selection_code}:{x.odd:.6f}" for x in sb.legs)
    raw = f"{sb.event_key}|{sb.market_type}|{sb.line}|{legs}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def reliability_score(sb: Surebet) -> float:
    # Score operacional, não garantia de lucro: combina margem, frescor,
    # diversidade de casas e estabilidade temporal.
    edge = min(max(sb.profit_percent, 0.0), 10.0) / 10.0 * 40.0
    freshness = max(0.0, 1.0 - min(sb.max_age_seconds, 300.0) / 300.0) * 30.0
    sync = max(0.0, 1.0 - min(sb.timestamp_spread_seconds, 120.0) / 120.0) * 15.0
    books = min(sb.bookmaker_count, 3) / 3.0 * 15.0
    return round(min(100.0, edge + freshness + sync + books), 2)


def alert_level(score: float, profit: float) -> str:
    if score >= 85 and profit >= 1.0:
        return "CRITICAL"
    if score >= 70 and profit >= 0.50:
        return "HIGH"
    if score >= 50:
        return "MEDIUM"
    return "INFO"


def movement_summary(db: Session, sb: Surebet, lookback_hours: int = 24) -> list[dict]:
    return movement_series(db, sb, lookback_hours)


def opportunity_key(sb: Surebet) -> str:
    # Identidade estável da oportunidade: evento + mercado + linha.
    # O fingerprint continua identificando a configuração exata das odds.
    return f"{sb.event_key}|{sb.market_type}|{sb.line}"


def persist_opportunities(db: Session, surebets: list[Surebet], lookback_hours: int = 24) -> tuple[int, int]:
    detected_at = utcnow_naive()
    created = updated = 0
    for sb in surebets:
        score = reliability_score(sb)
        level = alert_level(score, sb.profit_percent)
        fp = fingerprint(sb)
        op_key = opportunity_key(sb)
        movement = movement_summary(db, sb, lookback_hours)
        legs = [asdict(x) for x in sb.legs]
        for leg in legs:
            if isinstance(leg.get("collected_at"), datetime):
                leg["collected_at"] = leg["collected_at"].isoformat()
        row = db.query(SurebetOpportunityModel).filter_by(opportunity_key=op_key).first()
        payload = dict(detected_at=detected_at.isoformat(), event_key=sb.event_key,
                       home_team=sb.home_team, away_team=sb.away_team, market_type=sb.market_type,
                       line=sb.line, probability_sum=sb.probability_sum, profit_percent=sb.profit_percent,
                       reliability_score=score, alert_level=level)
        if row is None:
            row = SurebetOpportunityModel(
                detected_at=detected_at, opportunity_key=op_key, event_key=sb.event_key, home_team=sb.home_team,
                away_team=sb.away_team, sport="Futebol", market_type=sb.market_type, line=sb.line,
                probability_sum=sb.probability_sum, profit_percent=sb.profit_percent,
                reliability_score=score, max_age_seconds=sb.max_age_seconds,
                timestamp_spread_seconds=sb.timestamp_spread_seconds, bookmaker_count=sb.bookmaker_count,
                min_odd=sb.min_odd, bankroll=sb.bankroll, guaranteed_return=sb.guaranteed_return,
                guaranteed_profit=sb.guaranteed_profit, status="ACTIVE", legs_json=json.dumps(legs, ensure_ascii=False),
                movement_json=json.dumps(movement, ensure_ascii=False), alert_level=level, fingerprint=fp,
                first_seen_at=detected_at, last_seen_at=detected_at, lifetime_seconds=0, times_seen=1,
                peak_profit_percent=sb.profit_percent, trough_profit_percent=sb.profit_percent)
            db.add(row); db.flush(); created += 1
            db.add(SurebetAlertModel(created_at=detected_at, opportunity_id=row.id, fingerprint=fp,
                                     level=level, title=f"Surebet {level}: {sb.home_team} x {sb.away_team}",
                                     message=f"ROI {sb.profit_percent:.3f}% | Score {score:.1f}",
                                     payload_json=json.dumps(payload, ensure_ascii=False), delivered=1))
        else:
            row.detected_at = detected_at; row.last_seen_at = detected_at; row.times_seen = (row.times_seen or 0) + 1
            row.lifetime_seconds = max(0.0, (detected_at - (row.first_seen_at or detected_at)).total_seconds())
            row.peak_profit_percent = max(row.peak_profit_percent or sb.profit_percent, sb.profit_percent)
            row.trough_profit_percent = min(row.trough_profit_percent if row.trough_profit_percent is not None else sb.profit_percent, sb.profit_percent)
            row.probability_sum = sb.probability_sum
            row.profit_percent = sb.profit_percent; row.reliability_score = score
            row.max_age_seconds = sb.max_age_seconds; row.timestamp_spread_seconds = sb.timestamp_spread_seconds
            row.bookmaker_count = sb.bookmaker_count; row.min_odd = sb.min_odd
            row.guaranteed_return = sb.guaranteed_return; row.guaranteed_profit = sb.guaranteed_profit
            row.legs_json = json.dumps(legs, ensure_ascii=False); row.movement_json = json.dumps(movement, ensure_ascii=False)
            row.alert_level = level; row.status = "ACTIVE"; updated += 1
    # Uma linha por observação permite reconstruir a série temporal da oportunidade.
    for sb in surebets:
        db.add(SurebetObservationModel(
            opportunity_key=opportunity_key(sb), observed_at=detected_at,
            probability_sum=sb.probability_sum, profit_percent=sb.profit_percent,
            reliability_score=reliability_score(sb), fingerprint=fingerprint(sb),
            legs_json=json.dumps([asdict(x) for x in sb.legs], ensure_ascii=False, default=str),
        ))
    db.commit()
    return created, updated


def expire_old_opportunities(db: Session, max_age_seconds: int = 300) -> int:
    cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(seconds=max_age_seconds)
    rows = db.query(SurebetOpportunityModel).filter(
        SurebetOpportunityModel.status == "ACTIVE",
        SurebetOpportunityModel.detected_at < cutoff,
    ).all()
    for row in rows:
        row.status = "EXPIRED"
    db.commit()
    return len(rows)


def export_dashboard_json(db: Session, path: str, limit: int = 200) -> int:
    rows = db.query(SurebetOpportunityModel).order_by(
        SurebetOpportunityModel.reliability_score.desc(), SurebetOpportunityModel.profit_percent.desc()
    ).limit(limit).all()
    payload = []
    for r in rows:
        payload.append({
            "id": r.id, "detected_at": r.detected_at.isoformat(), "opportunity_key": r.opportunity_key,
            "first_seen_at": r.first_seen_at.isoformat() if r.first_seen_at else None,
            "last_seen_at": r.last_seen_at.isoformat() if r.last_seen_at else None,
            "lifetime_seconds": r.lifetime_seconds, "times_seen": r.times_seen,
            "peak_profit_percent": r.peak_profit_percent, "trough_profit_percent": r.trough_profit_percent, "event": f"{r.home_team} x {r.away_team}",
            "home_team": r.home_team, "away_team": r.away_team, "market_type": r.market_type, "line": r.line,
            "roi_percent": r.profit_percent, "probability_sum": r.probability_sum,
            "reliability_score": r.reliability_score, "alert_level": r.alert_level, "status": r.status,
            "max_age_seconds": r.max_age_seconds, "timestamp_spread_seconds": r.timestamp_spread_seconds,
            "bookmaker_count": r.bookmaker_count, "min_odd": r.min_odd,
            "guaranteed_return": r.guaranteed_return, "guaranteed_profit": r.guaranteed_profit,
            "legs": json.loads(r.legs_json), "movement": json.loads(r.movement_json),
        })
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return len(payload)
