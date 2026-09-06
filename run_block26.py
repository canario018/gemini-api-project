from __future__ import annotations
import json
from collections import defaultdict
from datetime import datetime, timezone
from app.database.connection import SessionLocal
from app.database.migrations import ensure_schema
from app.data_lake.models import MarketObservationFactModel
from app.market_intelligence.advanced import Quote, detect_arbitrage, movement
from app.market_intelligence.models import MarketMovementFactModel, ArbitrageOpportunityModel

def run(limit=300000):
    ensure_schema(); db=SessionLocal()
    try:
        rows=db.query(MarketObservationFactModel).order_by(MarketObservationFactModel.observed_at.asc()).limit(limit).all()
        groups=defaultdict(list)
        for r in rows:
            groups[(r.canonical_event_id,r.market,r.line,r.bookmaker,r.selection)].append(r)
        created=arb_count=0
        for key, rs in groups.items():
            rs.sort(key=lambda x:x.observed_at); first,last=rs[0],rs[-1]
            mv=movement(first.odd,last.odd)
            obj=MarketMovementFactModel(canonical_event_id=first.canonical_event_id,bookmaker=first.bookmaker,market=first.market,selection=first.selection,line=first.line,opening_odd=first.odd,current_odd=last.odd,high_odd=max(x.odd for x in rs),low_odd=min(x.odd for x in rs),movement_percent=mv['percent'],direction=mv['direction'],implied_probability_change_pp=mv['implied_probability_change_pp'],first_observed_at=first.observed_at,last_observed_at=last.observed_at,observations=len(rs))
            db.add(obj); created+=1
        by_market=defaultdict(list)
        for r in rows: by_market[(r.canonical_event_id,r.market,r.line,r.observed_at)].append(r)
        for key, rs in by_market.items():
            result=detect_arbitrage([Quote(r.bookmaker,r.selection,r.odd,r.line,r.observed_at) for r in rs],key[1],key[2])
            if result:
                db.add(ArbitrageOpportunityModel(canonical_event_id=key[0],market=result.market,line=result.line,detected_at=datetime.now(timezone.utc).replace(tzinfo=None),inverse_sum=result.inverse_sum,margin_percent=result.margin_percent,selections_json=json.dumps(result.selections),stakes_json=json.dumps(result.stake_allocations),source_count=len({r.bookmaker for r in rs}))); arb_count+=1
        db.commit(); return {'movement_facts':created,'arbitrage_opportunities':arb_count}
    finally: db.close()
if __name__=='__main__': print(run())
