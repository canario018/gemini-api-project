from __future__ import annotations
import json, logging, time
from datetime import datetime, timezone
from pathlib import Path
from app.config.settings import settings
from app.database.connection import SessionLocal
from app.database.migrations import ensure_schema, backfill_canonical_fields
from app.database.connection import Base, engine
from app.monitor.engine import run_cycle
from app.alerts.telegram import TelegramSender
from app.alerts.service import run_alert_cycle

logger = logging.getLogger("MONITOR.RUNNER")

def run_forever(interval_seconds=60, max_cycles=None, run_signals=True, min_strength=40.0, bankroll=1000.0, output="data/opportunities/live_monitor_status.json", threshold_percent=0.01, threshold_absolute=0.001, run_alerts=False, alert_cooldown=300, alert_change_min_percent=1.0, alert_max_deliveries=10, alert_dry_run=False):
    ensure_schema(); Base.metadata.create_all(bind=engine)
    cycle = 0; history=[]
    while max_cycles is None or cycle < max_cycles:
        cycle += 1
        try:
            db=SessionLocal(); backfill_canonical_fields(db); db.close()
            result = run_cycle(settings, session_factory=SessionLocal, run_signals=run_signals, min_strength=min_strength, bankroll=bankroll, change_threshold_percent=threshold_percent, change_threshold_absolute=threshold_absolute)
            if run_alerts:
                adb = SessionLocal()
                try:
                    sender = TelegramSender(settings.telegram_bot_token, settings.telegram_chat_id, settings.request_timeout_seconds) if settings.telegram_bot_token and settings.telegram_chat_id else None
                    alert_result = run_alert_cycle(adb, sender, bankroll=bankroll, change_min_delta_percent=alert_change_min_percent, cooldown_seconds=alert_cooldown, max_deliveries=alert_max_deliveries, dry_run=alert_dry_run or sender is None)
                finally:
                    adb.close()
                result["alerts"] = alert_result
            history.append(result); logger.info("Cycle %s: %s", cycle, result)
            Path(output).parent.mkdir(parents=True, exist_ok=True)
            Path(output).write_text(json.dumps({"updated_at":datetime.now(timezone.utc).isoformat(),"cycle":cycle,"interval_seconds":interval_seconds,"latest":result,"history":history[-20:]}, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as exc:
            logger.exception("Cycle %s falhou: %s", cycle, exc)
        if max_cycles is None or cycle < max_cycles:
            time.sleep(max(1, interval_seconds))
    return history
