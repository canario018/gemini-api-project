from __future__ import annotations
from app.normalization.canonical import canonical_selection, market_key
def canonical_market_id(row):
    return market_key(market_type=getattr(row,'market_type',''),market_name=getattr(row,'market_name',''),line=getattr(row,'line',None),sport=getattr(row,'sport',''))
def canonical_selection_id(row):
    return canonical_selection(getattr(row,'selection_name',''),getattr(row,'selection_code',''))
def markets_match(a,b): return canonical_market_id(a)==canonical_market_id(b)
