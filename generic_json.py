from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

import requests

from app.collectors.base import BaseSportsbookCollector
from app.collectors.schemas import OddPayload
from app.normalization.normalizer import build_raw_key, clean_text
from app.normalization.canonical import parse_event_start


class GenericSportsJsonCollector(BaseSportsbookCollector):
    """Adapter conservador para APIs esportivas JSON heterogêneas.

    Ele procura apenas estruturas que tenham contexto de evento + mercado + seleção
    + preço. Campos ausentes não são inventados. Quando o payload não contém odds
    identificáveis, o collector retorna lista vazia e a camada de health marca EMPTY.
    """

    def __init__(self, sportsbook_name: str, api_endpoint: str, *, referer: str, origin: str | None = None,
                 params: dict[str, Any] | None = None, timeout: int = 15):
        super().__init__(sportsbook_name, api_endpoint)
        self.timeout = timeout
        self.params = params or {}
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
            ),
            "Accept": "application/json, text/plain, */*",
            "Referer": referer,
        }
        if origin:
            self.headers["Origin"] = origin

    def fetch_raw_data(self):
        response = requests.get(
            self.api_endpoint,
            headers=self.headers,
            params=self.params,
            timeout=self.timeout,
        )
        self.last_http_status = response.status_code
        self.last_response_bytes = len(response.content)
        self.last_collected_at = datetime.now(timezone.utc)
        response.raise_for_status()
        return response.json()

    @staticmethod
    def _first(d: dict[str, Any], keys: tuple[str, ...], default=None):
        for key in keys:
            if key in d and d[key] not in (None, ""):
                return d[key]
        return default

    @staticmethod
    def _name(value) -> str:
        if isinstance(value, dict):
            return clean_text(GenericSportsJsonCollector._first(value, ("name", "displayName", "label", "title"), ""))
        return clean_text(value)

    @classmethod
    def _participants(cls, event: dict[str, Any]) -> list[str]:
        raw = cls._first(event, ("participants", "competitors", "teams", "participantsList"), [])
        if isinstance(raw, list):
            names = [cls._name(x) for x in raw]
            return [x for x in names if x]
        home = cls._name(cls._first(event, ("homeTeam", "home", "homeParticipant", "homeCompetitor"), ""))
        away = cls._name(cls._first(event, ("awayTeam", "away", "awayParticipant", "awayCompetitor"), ""))
        return [x for x in (home, away) if x]

    @classmethod
    def _event_context(cls, d: dict[str, Any], parent=None):
        event_id = cls._first(d, ("eventId", "eventID", "event_id", "fixtureId", "fixtureID", "matchId", "matchID"))
        if event_id is None and cls._first(d, ("id",)) is not None and (cls._participants(d) or cls._first(d, ("startDate", "startTime", "start", "kickoff"))):
            event_id = d.get("id")
        participants = cls._participants(d)
        if event_id is not None and len(participants) >= 2:
            return {
                "event_id": str(event_id),
                "home": participants[0],
                "away": participants[1],
                "sport": cls._name(cls._first(d, ("sport", "sportName"), "Futebol")) or "Futebol",
                "league": cls._name(cls._first(d, ("league", "leagueName", "competition", "competitionName", "championship"), "Geral")) or "Geral",
                "start": parse_event_start(cls._first(d, ("startDate", "startTime", "start", "kickoff", "eventStartTime", "date"))),
            }
        return parent

    @staticmethod
    def _looks_market(d: dict[str, Any]) -> bool:
        keys = {str(k).lower() for k in d.keys()}
        return bool(keys & {"selections", "outcomes", "betoffers", "betoffers", "odds", "items"}) and bool(
            keys & {"marketname", "market_name", "markettype", "market_type", "market", "name", "title"}
        )

    @classmethod
    def _market_context(cls, d: dict[str, Any], parent=None):
        if not cls._looks_market(d):
            return parent
        name = cls._name(cls._first(d, ("marketName", "market_name", "name", "title", "label"), "Mercado")) or "Mercado"
        market = cls._first(d, ("marketType", "market_type", "type", "typeName"), None)
        return {"name": name, "type": cls._name(market) if market else name}

    @staticmethod
    def _price(d: dict[str, Any]):
        value = GenericSportsJsonCollector._first(d, ("price", "odds", "odd", "decimalOdds", "decimalOdd", "value", "valueDecimal"))
        try:
            value = float(value)
        except (TypeError, ValueError):
            return None
        return value if value > 1.0 else None

    @staticmethod
    def _selection_name(d: dict[str, Any]) -> str:
        return clean_text(GenericSportsJsonCollector._first(
            d, ("selectionName", "outcomeName", "selection", "outcome", "label", "name", "title"), ""
        ))

    @staticmethod
    def _market_type(name: str) -> str:
        n = clean_text(name).lower()
        if any(x in n for x in ("resultado", "vencedor", "match result", "moneyline", "1x2")):
            return "MATCH_RESULT"
        if "chance dupla" in n or "double chance" in n:
            return "DOUBLE_CHANCE"
        if "empate devolve" in n or "draw no bet" in n:
            return "DRAW_NO_BET"
        if "ambas" in n and "marcam" in n or "both teams" in n or "btts" in n:
            return "BOTH_TEAMS_TO_SCORE"
        if "total" in n and any(x in n for x in ("gol", "goal")):
            return "TOTAL_GOALS"
        if "total" in n and any(x in n for x in ("ponto", "point")):
            return "TOTAL_POINTS"
        if "handicap" in n or "spread" in n:
            return "HANDICAP"
        if "set" in n and "winner" in n or "vencedor do set" in n:
            return "SET_WINNER"
        return "OTHER"

    @staticmethod
    def _selection_code(market_type: str, name: str, event_ctx: dict[str, Any] | None = None) -> str:
        n = clean_text(name).lower()
        if market_type == "MATCH_RESULT":
            if n in {"1", "home", "casa", "mandante"}:
                return "HOME"
            if n in {"x", "draw", "empate"}:
                return "DRAW"
            if n in {"2", "away", "fora", "visitante"}:
                return "AWAY"
            if event_ctx:
                if n == clean_text(event_ctx.get("home", "")).lower():
                    return "HOME"
                if n == clean_text(event_ctx.get("away", "")).lower():
                    return "AWAY"
        if market_type in {"TOTAL_GOALS", "TOTAL_POINTS"}:
            if re.search(r"\bover\b|mais", n):
                return "OVER"
            if re.search(r"\bunder\b|menos", n):
                return "UNDER"
        if market_type == "BOTH_TEAMS_TO_SCORE":
            if n in {"sim", "yes"}:
                return "YES"
            if n in {"não", "nao", "no"}:
                return "NO"
        if market_type in {"HANDICAP", "SET_WINNER"}:
            if any(x in n for x in ("home", "casa", "mandante")):
                return "HOME"
            if any(x in n for x in ("away", "fora", "visitante")):
                return "AWAY"
        return name[:80] or "OTHER"

    @staticmethod
    def _line(name: str, d: dict[str, Any]):
        direct = GenericSportsJsonCollector._first(d, ("line", "handicap", "total", "points", "threshold"))
        if direct not in (None, ""):
            try:
                return float(str(direct).replace(",", "."))
            except (TypeError, ValueError):
                pass
        match = re.search(r"(?:over|under|mais|menos)(?:\s+de)?\s*([+-]?\d+(?:[\.,]\d+)?)", name, re.I)
        if match:
            return float(match.group(1).replace(",", "."))
        return None

    def normalize_data(self, raw_data):
        records = []
        seen = set()

        def walk(node, event_ctx=None, market_ctx=None):
            if isinstance(node, list):
                for item in node:
                    walk(item, event_ctx, market_ctx)
                return
            if not isinstance(node, dict):
                return

            current_event = self._event_context(node, event_ctx)
            current_market = self._market_context(node, market_ctx)
            price = self._price(node)

            if price and current_event and current_market:
                selection_name = self._selection_name(node)
                if selection_name:
                    market_name = current_market["name"]
                    market_type = self._market_type(market_name)
                    code = self._selection_code(market_type, selection_name, current_event)
                    line = self._line(selection_name, node)
                    key = build_raw_key(self.sportsbook_name, current_event["event_id"], market_type,
                                        current_event["home"], current_event["away"], code, line)
                    if key not in seen:
                        payload = {
                            "collected_at": self.last_collected_at or datetime.now(timezone.utc),
                            "bookmaker": self.sportsbook_name,
                            "source_url": self.api_endpoint,
                            "sport": current_event["sport"],
                            "league": current_event["league"],
                            "event_id": current_event["event_id"],
                            "event_start_at": current_event["start"],
                            "home_team": current_event["home"],
                            "away_team": current_event["away"],
                            "market_name": market_name,
                            "market_type": market_type,
                            "selection_name": selection_name,
                            "selection_code": code,
                            "line": line,
                            "odd": price,
                            "currency": "BRL",
                            "raw_key": key,
                        }
                        try:
                            records.append(OddPayload.model_validate(payload).model_dump())
                            seen.add(key)
                        except Exception:
                            pass

            for value in node.values():
                if isinstance(value, (dict, list)):
                    walk(value, current_event, current_market)

        walk(raw_data)
        return records
