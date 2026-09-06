from __future__ import annotations
import argparse
from app.database.connection import SessionLocal
from app.database.migrations import ensure_schema
from app.modeling.features import SportFeatureEngine

def main():
    p=argparse.ArgumentParser(description="BLOCO22 sport-specific feature engineering")
    p.add_argument("--sport",default=None); p.add_argument("--limit",type=int,default=200000); p.add_argument("--window",type=int,default=10)
    a=p.parse_args(); ensure_schema(); db=SessionLocal()
    try:
        r=SportFeatureEngine(db,a.window).build(a.sport,a.limit); print(f"BLOCO22 OK | created={r.created} skipped={r.skipped} sport={a.sport or 'all'} window={a.window}")
    finally: db.close()
if __name__=="__main__": main()
