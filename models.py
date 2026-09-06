from __future__ import annotations
from sqlalchemy import Boolean, Column, DateTime, Float, Index, Integer, String, Text
from app.database.connection import Base

class AlertEventModel(Base):
    __tablename__ = "alert_events"
    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime, nullable=False, index=True)
    event_key = Column(String(900), nullable=False, index=True)
    alert_key = Column(String(1200), nullable=False, index=True)
    alert_type = Column(String(60), nullable=False, index=True)
    severity = Column(String(20), nullable=False, index=True)
    score = Column(Float, nullable=False, default=0)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    payload_json = Column(Text, nullable=False, default="{}")
    dedupe_hash = Column(String(128), nullable=False, index=True)
    status = Column(String(30), nullable=False, default="PENDING", index=True)
    suppressed_reason = Column(String(255), nullable=True)
    sent_at = Column(DateTime, nullable=True)

class AlertDeliveryModel(Base):
    __tablename__ = "alert_deliveries"
    id = Column(Integer, primary_key=True, autoincrement=True)
    alert_event_id = Column(Integer, nullable=False, index=True)
    attempted_at = Column(DateTime, nullable=False, index=True)
    channel = Column(String(40), nullable=False, default="TELEGRAM")
    status = Column(String(30), nullable=False)
    response_code = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)
    message_id = Column(String(100), nullable=True)
    __table_args__ = (Index("idx_alert_delivery_event_time", "alert_event_id", "attempted_at"),)
