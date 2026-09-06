from datetime import datetime, timezone
import re
import requests
from app.collectors.base import BaseSportsbookCollector
from app.collectors.schemas import OddPayload
from app.normalization.normalizer import build_raw_key, clean_text
from app.normalization.canonical import parse_event_start, canonical_sport, canonical_market, canonical_selection, event_key

class BetanoCollector(BaseSportsbookCollector):
    """Adapter Betano. O endpoint deve ser validado no ambiente real; o parser
    aceita variações comuns do payload, mas não inventa campos ausentes."""
    def __init__(self, api_endpoint=None):
        default_endpoint = "https://www.betano.bet.br/api/sports/FOOT/hot/trending/leagues/10008/events"
        super().__init__(sportsbook_name="Betano", api_endpoint=api_endpoint or default_endpoint)
        self.headers = {"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36","Accept":"application/json, text/plain, */*","Referer":"https://www.betano.bet.br/"}

    def fetch_raw_data(self):
        response=requests.get(self.api_endpoint,headers=self.headers,params={"req":"s,stnf,c,mb"},timeout=10)
        self.last_http_status=response.status_code; self.last_response_bytes=len(response.content); self.last_collected_at=datetime.now(timezone.utc)
        response.raise_for_status(); return response.json()

    @staticmethod
    def _market_type(name):
        n=clean_text(name).lower()
        if any(x in n for x in ["resultado", "vencedor", "match result"]): return "MATCH_RESULT"
        if "ambas" in n and "marcam" in n or "btts" in n: return "BOTH_TEAMS_TO_SCORE"
        if "total" in n and any(x in n for x in ["gols","goals","pontos","points"]): return "TOTAL_GOALS" if any(x in n for x in ["gols","goals"]) else "TOTAL_POINTS"
        if "handicap" in n or "spread" in n: return "HANDICAP"
        if "set" in n and "vencedor" in n: return "SET_WINNER"
        return "OTHER"

    @staticmethod
    def _selection(market_type, name, participants=None):
        n=clean_text(name).lower()
        if market_type=="MATCH_RESULT":
            if any(x in n for x in ["empate","draw"]): return "DRAW"
            if participants and clean_text(participants[0].get("name","")).lower() in n: return "HOME"
            if participants and len(participants)>1 and clean_text(participants[1].get("name","")).lower() in n: return "AWAY"
            if n in {"1","home","mandante"}: return "HOME"
            if n in {"2","away","visitante"}: return "AWAY"
        if market_type in {"TOTAL_GOALS","TOTAL_POINTS"}:
            if re.search(r"\bover\b|mais",n): return "OVER"
            if re.search(r"\bunder\b|menos",n): return "UNDER"
        if market_type=="BOTH_TEAMS_TO_SCORE":
            if n in {"sim","yes"}: return "YES"
            if n in {"não","nao","no"}: return "NO"
        if market_type=="HANDICAP":
            if any(x in n for x in ["home","mandante"]): return "HOME"
            if any(x in n for x in ["away","visitante"]): return "AWAY"
        return clean_text(name)[:80] or "OTHER"

    @staticmethod
    def _line(name):
        m=re.search(r"(?:over|under|mais|menos)\s*([+-]?\d+(?:[\.,]\d+)?)",clean_text(name),re.I)
        return float(m.group(1).replace(',','.')) if m else None

    def normalize_data(self, raw_data):
        block=raw_data.get("data",{}) if isinstance(raw_data,dict) else {}
        events=block.get("events",[]) or raw_data.get("events",[]) if isinstance(raw_data,dict) else []
        records=[]; collected_at=datetime.now(timezone.utc)
        for event in events:
            if not isinstance(event,dict): continue
            eid=event.get("id")
            parts=event.get("participants") or event.get("competitors") or []
            if not eid or len(parts)<2: continue
            home=clean_text(parts[0].get("name", "Home")); away=clean_text(parts[1].get("name", "Away"))
            start=parse_event_start(event.get("startTime") or event.get("startDate") or event.get("start"))
            markets=event.get("markets",[]) or event.get("betOffers",[]) or []
            for market in markets:
                mname=clean_text(market.get("name") or market.get("marketName") or "Mercado")
                mtype=self._market_type(mname)
                selections=market.get("selections",[]) or market.get("outcomes",[]) or market.get("betOffers",[])
                for sel in selections:
                    if not isinstance(sel,dict): continue
                    price=sel.get("price",sel.get("odds",sel.get("odd")))
                    try: price=float(price)
                    except (TypeError,ValueError): continue
                    if price<=1: continue
                    sname=clean_text(sel.get("name") or sel.get("label") or "Seleção")
                    scode=self._selection(mtype,sname,parts); line=self._line(sname)
                    payload={"collected_at":collected_at,"bookmaker":"Betano","source_url":self.api_endpoint,"sport":"Futebol","league":clean_text(event.get("leagueName") or event.get("competitionName") or "Geral"),"event_id":str(eid),"event_start_at":start,"home_team":home,"away_team":away,"market_name":mname,"market_type":mtype,"selection_name":sname,"selection_code":scode,"line":line,"odd":price,"currency":"BRL","raw_key":build_raw_key("Betano",eid,mtype,home,away,scode,line)}
                    try: records.append(OddPayload.model_validate(payload).model_dump())
                    except Exception: pass
        return records
