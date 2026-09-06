from __future__ import annotations

from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Index
from app.database.connection import Base


class SurebetOpportunityModel(Base):
    __tablename__ = "surebet_opportunities"

    id = Column(Integer, primary_key=True, autoincrement=True)
    detected_at = Column(DateTime, nullable=False, index=True)
    event_key = Column(String(500), nullable=False, index=True)
    opportunity_key = Column(String(700), nullable=False, index=True)
    home_team = Column(String(100), nullable=False)
    away_team = Column(String(100), nullable=False)
    sport = Column(String(50), nullable=False, default="Futebol")
    market_type = Column(String(50), nullable=False, index=True)
    line = Column(Float, nullable=True)
    probability_sum = Column(Float, nullable=False)
    profit_percent = Column(Float, nullable=False, index=True)
    reliability_score = Column(Float, nullable=False, index=True)
    max_age_seconds = Column(Float, nullable=False, default=0)
    timestamp_spread_seconds = Column(Float, nullable=False, default=0)
    bookmaker_count = Column(Integer, nullable=False, default=0)
    min_odd = Column(Float, nullable=False, default=0)
    bankroll = Column(Float, nullable=False, default=0)
    guaranteed_return = Column(Float, nullable=False, default=0)
    guaranteed_profit = Column(Float, nullable=False, default=0)
    status = Column(String(30), nullable=False, default="ACTIVE", index=True)
    legs_json = Column(Text, nullable=False)
    movement_json = Column(Text, nullable=False, default="[]")
    alert_level = Column(String(20), nullable=False, default="INFO")
    fingerprint = Column(String(255), nullable=False, index=True)
    first_seen_at = Column(DateTime, nullable=True, index=True)
    last_seen_at = Column(DateTime, nullable=True, index=True)
    lifetime_seconds = Column(Float, nullable=False, default=0)
    times_seen = Column(Integer, nullable=False, default=1)
    peak_profit_percent = Column(Float, nullable=False, default=0)
    trough_profit_percent = Column(Float, nullable=False, default=0)

    __table_args__ = (
        Index("idx_surebet_event_detected", "event_key", "detected_at"),
        Index("idx_surebet_status_score", "status", "reliability_score"),
        Index("idx_surebet_opportunity_key", "opportunity_key"),
    )


class SurebetObservationModel(Base):
    __tablename__ = "surebet_observations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    opportunity_key = Column(String(700), nullable=False, index=True)
    observed_at = Column(DateTime, nullable=False, index=True)
    probability_sum = Column(Float, nullable=False)
    profit_percent = Column(Float, nullable=False)
    reliability_score = Column(Float, nullable=False)
    fingerprint = Column(String(255), nullable=False)
    legs_json = Column(Text, nullable=False)

    __table_args__ = (
        Index("idx_observation_key_time", "opportunity_key", "observed_at"),
    )


class SurebetAlertModel(Base):
    __tablename__ = "surebet_alerts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime, nullable=False, index=True)
    opportunity_id = Column(Integer, nullable=True, index=True)
    fingerprint = Column(String(255), nullable=False, index=True)
    level = Column(String(20), nullable=False)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    payload_json = Column(Text, nullable=False)
    delivered = Column(Integer, nullable=False, default=1)


class BookmakerRankingModel(Base):
    __tablename__ = "bookmaker_rankings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    calculated_at = Column(DateTime, nullable=False, index=True)
    bookmaker = Column(String(80), nullable=False, index=True)
    snapshots = Column(Integer, nullable=False, default=0)
    markets_seen = Column(Integer, nullable=False, default=0)
    best_odd_count = Column(Integer, nullable=False, default=0)
    best_odd_rate = Column(Float, nullable=False, default=0)
    surebet_leg_count = Column(Integer, nullable=False, default=0)
    surebet_leg_rate = Column(Float, nullable=False, default=0)
    avg_odd = Column(Float, nullable=False, default=0)
    ranking_score = Column(Float, nullable=False, default=0, index=True)

    __table_args__ = (Index("idx_bookmaker_ranking_time", "calculated_at", "ranking_score"),)

# BLOCO 7 — temporal persistence model is imported here so Base.metadata sees it.
from app.opportunities.temporal_persistence import TemporalMarketStatModel  # noqa: E402,F401

# BLOCO 8 — signal model registration
from app.signals.models import MarketSignalModel  # noqa: E402,F401
