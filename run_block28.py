from __future__ import annotations
import argparse, json
from app.database.connection import SessionLocal
from app.database.migrations import ensure_schema
from app.data_lake.models import MarketObservationFactModel
from app.market_intelligence.reconstruction import MarketSnapshot, reconstruct, true_clv

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--sport'); ap.add_argument('--event-id'); ap.add_argument('--limit',type=int,default=200000); args=ap.parse_args()
    ensure_schema(); db=SessionLocal()
    try:
        q=db.query(MarketObservationFactModel).filter(MarketObservationFactModel.event_start_at.isnot(None), MarketObservationFactModel.odd>1).order_by(MarketObservationFactModel.observed_at.asc())
        if args.sport:q=q.filter(MarketObservationFactModel.sport==args.sport)
        if args.event_id:q=q.filter(MarketObservationFactModel.canonical_event_id==args.event_id)
        rows=q.limit(args.limit).all()
        snapshots=[MarketSnapshot(r.canonical_event_id or '',r.bookmaker,r.market,r.selection,r.line,r.odd,r.observed_at,r.event_start_at) for r in rows]
        rec=reconstruct(snapshots)
        payload=[]
        for x in rec:
            payload.append({"event_id":x.event_id,"bookmaker":x.bookmaker,"market":x.market,"selection":x.selection,"line":x.line,"opening_odd":x.opening_odd,"closing_odd":x.closing_odd,"best_entry_odd":x.best_entry_odd,"true_clv_percent":true_clv(x.best_entry_odd or x.opening_odd or 0,x.closing_odd or 0),"observations":x.observations,"timeline":[t.__dict__ for t in x.timeline]})
        print(json.dumps(payload[:1000],default=str,ensure_ascii=False,indent=2))
    finally: db.close()
if __name__=='__main__': main()
