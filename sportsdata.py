from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from app.collectors.generic_json import GenericSportsJsonCollector
from app.collectors.schemas import OddPayload
from app.normalization.canonical import parse_event_start
from app.normalization.normalizer import build_raw_key, clean_text


class SportsDataEventCollector(GenericSportsJsonCollector):
    """Parser específico para o payload SportsData usado por R7Bet/Bet.Bet.

    A estrutura observada é: Events -> Markets -> Selections, com Highlights
    contendo eventos em Event. O parser também aceita pequenas variações de
    capitalização/campo sem recorrer a fuzzy matching.
    """

    def _first_ci(self, d: dict[str, Any], *keys, default=None):
        if not isinstance(d, dict):
            return default
        exact = {str(k): k for k in d.keys()}
        lower = {str(k).lower(): k for k in d.keys()}
        for key in keys:
            if key in d and d[key] not in (None, ""):
                return d[key]
            real = lower.get(str(key).lower())
            if real is not None and d[real] not in (None, ""):
                return d[real]
        return default

    def _events(self, raw):
        if not isinstance(raw, dict):
            return []
        events = raw.get("Events") or raw.get("events") or []
        out = list(events) if isinstance(events, list) else []
        highlights = raw.get("Highlights") or raw.get("highlights") or []
        if isinstance(highlights, list):
            for h in highlights:
                if isinstance(h, dict) and isinstance(h.get("Event"), dict):
                    out.append(h["Event"])
        return out

    def _participants(self, event):
        raw = self._first_ci(event, "Participants", "participants", default=[])
        home = away = ""
        if isinstance(raw, list):
            for p in raw:
                if not isinstance(p, dict):
                    continue
                name = clean_text(self._first_ci(p, "Name", "name", "displayName", default=""))
                role = str(self._first_ci(p, "VenueRole", "venueRole", "role", default="")).lower()
                if role == "home": home = name
                elif role == "away": away = name
            if not home and raw:
                home = clean_text(self._first_ci(raw[0], "Name", "name", default="")) if isinstance(raw[0], dict) else ""
            if not away and len(raw) > 1:
                away = clean_text(self._first_ci(raw[1], "Name", "name", default="")) if isinstance(raw[1], dict) else ""
        if not home or not away:
            text = clean_text(self._first_ci(event, "EventName", "eventName", default=""))
            parts = re.split(r"\s+vs\s+|\s+x\s+", text, maxsplit=1, flags=re.I)
            if len(parts) == 2:
                home = home or parts[0].strip()
                away = away or parts[1].strip()
        return home, away

    def _market_name(self, market):
        mt = self._first_ci(market, "MarketType", "marketType", default={})
        if isinstance(mt, dict):
            return clean_text(self._first_ci(mt, "Name", "name", default="")) or clean_text(self._first_ci(market, "Name", "name", default="Mercado"))
        return clean_text(self._first_ci(market, "Name", "name", default=mt or "Mercado"))

    def _market_type(self, market):
        mt = self._first_ci(market, "MarketType", "marketType", default={})
        mt_id = str(self._first_ci(mt, "_id", "id", default="")).upper() if isinstance(mt, dict) else ""
        name = self._market_name(market).lower()
        if mt_id.startswith("ML0") or ("resultado final" in name and "superodds" not in name): return "MATCH_RESULT"
        if mt_id == "ML1" or "resultado do 1" in name: return "FIRST_HALF_RESULT"
        if mt_id.startswith("OU") and ("gol" in name or "goal" in name): return "TOTAL_GOALS"
        if "total" in name and ("gol" in name or "goal" in name): return "TOTAL_GOALS"
        if mt_id.startswith("OU13") or "escante" in name: return "TOTAL_CORNERS"
        if mt_id.startswith("HC") or "handicap asi" in name: return "HANDICAP"
        if "ambas" in name and "marcam" in name: return "BOTH_TEAMS_TO_SCORE"
        if "primeiro gol" in name: return "FIRST_GOAL"
        if "placar correto" in name: return "CORRECT_SCORE"
        if "set" in name and "vencedor" in name: return "SET_WINNER"
        return "OTHER"

    def _price(self, selection):
        value = self._first_ci(selection, "odds", "odd", "price", "decimalOdds", "decimalOdd", "value", default=None)
        if isinstance(value, dict):
            value = self._first_ci(value, "decimal", "value", "odds", default=None)
        try:
            v = float(str(value).replace(",", "."))
            return v if v > 1 else None
        except (TypeError, ValueError):
            return None

    def _selection_name(self, selection):
        return clean_text(self._first_ci(selection, "selectionName", "SelectionName", "name", "Name", "label", "displayName", default=""))

    def _line(self, selection, market, selection_name):
        value = self._first_ci(selection, "line", "Line", "handicap", "Handicap", "total", "Total", "points", "threshold", default=None)
        if value in (None, ""):
            value = self._first_ci(market, "line", "Line", "handicap", "Handicap", "total", "Total", default=None)
        if value not in (None, ""):
            try: return float(str(value).replace(",", "."))
            except (TypeError, ValueError): pass
        m = re.search(r"(?:mais|menos|over|under)\s*(?:de)?\s*([+-]?\d+(?:[\.,]\d+)?)", selection_name, re.I)
        if m: return float(m.group(1).replace(",", "."))
        m = re.search(r"([+-]\d+(?:[\.,]\d+)?)", selection_name)
        if m and self._market_type(market) == "HANDICAP": return float(m.group(1).replace(",", "."))
        return None

    def _selection_code(self, market_type, name, home, away):
        n = clean_text(name).lower()
        if market_type in {"MATCH_RESULT", "FIRST_HALF_RESULT"}:
            if n in {"1", "home", "casa", "mandante"} or n == home.lower(): return "HOME"
            if n in {"x", "draw", "empate"}: return "DRAW"
            if n in {"2", "away", "fora", "visitante"} or n == away.lower(): return "AWAY"
        if market_type in {"TOTAL_GOALS", "TOTAL_CORNERS"}:
            if re.search(r"\b(over|mais)\b", n): return "OVER"
            if re.search(r"\b(under|menos)\b", n): return "UNDER"
        if market_type == "BOTH_TEAMS_TO_SCORE":
            if n in {"sim", "yes"}: return "YES"
            if n in {"não", "nao", "no"}: return "NO"
        if market_type == "HANDICAP":
            if any(x in n for x in (home.lower(), "home", "casa", "mandante")): return "HOME"
            if any(x in n for x in (away.lower(), "away", "fora", "visitante")): return "AWAY"
        return name[:80] or "OTHER"

    def normalize_data(self, raw_data):
        records, seen = [], set()
        for event in self._events(raw_data):
            if not isinstance(event, dict): continue
            home, away = self._participants(event)
            if not home or not away: continue
            sport = clean_text(self._first_ci(event, "SportName", "sportName", default="Futebol")) or "Futebol"
            league = clean_text(self._first_ci(event, "LeagueName", "leagueName", default="Geral")) or "Geral"
            event_id = str(self._first_ci(event, "_id", "EventId", "eventId", "id", default=""))
            start = parse_event_start(self._first_ci(event, "StartEventDate", "startEventDate", "startDate", default=None))
            markets = self._first_ci(event, "Markets", "markets", default=[])
            if not isinstance(markets, list): continue
            for market in markets:
                if not isinstance(market, dict): continue
                if self._first_ci(market, "IsSuspended", "isSuspended", default=False): continue
                market_name = self._market_name(market)
                market_type = self._market_type(market)
                selections = self._first_ci(market, "Selections", "selections", default=[])
                if not isinstance(selections, list): continue
                for selection in selections:
                    if not isinstance(selection, dict): continue
                    price = self._price(selection)
                    if price is None: continue
                    selection_name = self._selection_name(selection)
                    if not selection_name: continue
                    line = self._line(selection, market, selection_name)
                    code = self._selection_code(market_type, selection_name, home, away)
                    raw_key = build_raw_key(self.sportsbook_name, event_id, market_type, home, away, code, line)
                    if raw_key in seen: continue
                    try:
                        rec = OddPayload.model_validate({
                            "collected_at": self.last_collected_at or datetime.now(timezone.utc),
                            "bookmaker": self.sportsbook_name, "source_url": self.api_endpoint,
                            "sport": sport, "league": league, "event_id": event_id, "event_start_at": start,
                            "home_team": home, "away_team": away, "market_name": market_name,
                            "market_type": market_type, "selection_name": selection_name,
                            "selection_code": code, "line": line, "odd": price,
                            "currency": "BRL", "raw_key": raw_key,
                        }).model_dump()
                        records.append(rec); seen.add(raw_key)
                    except Exception:
                        continue
        return records
