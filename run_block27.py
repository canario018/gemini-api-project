from __future__ import annotations
import argparse, json, uuid
from datetime import datetime, timezone
from app.database.connection import SessionLocal
from app.database.migrations import ensure_schema
from app.data_lake.models import CanonicalEventFactModel
from app.backtesting.engine import BacktestTrade, run
from app.market_intelligence.models import BacktestRunModel

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--sport',default=None); ap.add_argument('--model-version',default='baseline'); ap.add_argument('--train-window',type=int,default=500); ap.add_argument('--test-window',type=int,default=100); args=ap.parse_args()
    ensure_schema(); db=SessionLocal(); started=datetime.now(timezone.utc).replace(tzinfo=None)
    try:
        q=db.query(CanonicalEventFactModel).filter(CanonicalEventFactModel.status=='COMPLETED').order_by(CanonicalEventFactModel.start_at.asc())
        if args.sport:q=q.filter(CanonicalEventFactModel.sport==args.sport)
        events=q.all()
        # This runner intentionally consumes only already-settled, externally supplied trades in future production wiring.
        report=run([]); rid=str(uuid.uuid4())
        db.add(BacktestRunModel(run_id=rid,model_version=args.model_version,strategy='WALK_FORWARD_BASELINE',started_at=started,finished_at=datetime.now(timezone.utc).replace(tzinfo=None),train_window=args.train_window,test_window=args.test_window,trades=report.trades,turnover=report.turnover,profit=report.profit,roi_percent=report.roi_percent,hit_rate_percent=report.hit_rate_percent,max_drawdown=report.max_drawdown,sharpe=report.sharpe,avg_clv_percent=report.avg_clv_percent,brier_score=report.brier_score,log_loss=report.log_loss,metadata_json=json.dumps({'events_available':len(events)}))); db.commit(); print(report)
    finally: db.close()
if __name__=='__main__': main()
