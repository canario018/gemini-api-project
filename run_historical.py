from __future__ import annotations
import argparse
from datetime import date
from app.database.migrations import ensure_schema
from app.database.connection import SessionLocal
from app.data_harvest.registry import default_providers
from app.data_harvest.collector import HistoricalCollector
from app.data_harvest.feature_pipeline import HistoricalFeaturePipeline
from app.data_harvest.persistence.repository import HistoricalRepository

def main():
    p=argparse.ArgumentParser(description="BLOCO19 historical sports data collector")
    p.add_argument("--start",required=True); p.add_argument("--end",required=True)
    p.add_argument("--providers",default="sofascore_football,fbref_football,basketball_reference,mlb_stats_api,nhl_web_api,atp_official,formula1_official")
    p.add_argument("--rebuild-features",action="store_true")
    args=p.parse_args(); ensure_schema(); db=SessionLocal(); names=set(x.strip() for x in args.providers.split(",")); providers=[x for x in default_providers() if x.name in names]
    collector=HistoricalCollector(db); results=[]
    for provider in providers: results.append(collector.run(provider,date.fromisoformat(args.start),date.fromisoformat(args.end)))
    if args.rebuild_features:
        rows=HistoricalRepository(db).list(limit=200000); print("feature_snapshots_created", HistoricalFeaturePipeline(db).rebuild(rows))
    for r in results: print(r)

if __name__ == "__main__": main()
