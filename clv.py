from __future__ import annotations

def clv_percent(entry_odd, closing_odd):
    if entry_odd<=1 or closing_odd<=1: raise ValueError('odds must be > 1')
    return (entry_odd/closing_odd-1)*100

def implied_clv_percent(entry_odd, closing_odd):
    if entry_odd<=1 or closing_odd<=1: raise ValueError('odds must be > 1')
    return ((1/closing_odd)-(1/entry_odd))*100
