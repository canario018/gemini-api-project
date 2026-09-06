from __future__ import annotations

import re
import unicodedata
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

GENERIC_TEAM_TOKENS = {
    'fc','sc','ec','club','clube','futebol','esporte','sports','cf','afc','ac','bc','basketball'
}

SPORT_ALIASES = {
    'futebol':'FOOTBALL','football':'FOOTBALL','soccer':'FOOTBALL',
    'basquete':'BASKETBALL','basketball':'BASKETBALL',
    'tenis':'TENNIS','tênis':'TENNIS','tennis':'TENNIS',
    'volei':'VOLLEYBALL','vôlei':'VOLLEYBALL','volleyball':'VOLLEYBALL',
    'handebol':'HANDBALL','handball':'HANDBALL',
    'hoquei':'ICE_HOCKEY','hóquei':'ICE_HOCKEY','ice hockey':'ICE_HOCKEY',
    'beisebol':'BASEBALL','baseball':'BASEBALL',
    'futsal':'FUTSAL',
}

MARKET_ALIASES = {
    'match_result': 'MATCH_RESULT', 'match result':'MATCH_RESULT', 'match winner':'MATCH_RESULT', 'vencedor do encontro':'MATCH_RESULT',
    'resultado final':'MATCH_RESULT', 'resultado final superodds':'MATCH_RESULT', '1x2':'MATCH_RESULT',
    'moneyline':'MATCH_RESULT', 'jogo':'MATCH_RESULT',
    'double_chance':'DOUBLE_CHANCE', 'double chance':'DOUBLE_CHANCE', 'chance dupla':'DOUBLE_CHANCE',
    'draw_no_bet':'DRAW_NO_BET', 'draw no bet':'DRAW_NO_BET', 'empate devolve aposta':'DRAW_NO_BET',
    'total_goals':'TOTAL_GOALS', 'total goals':'TOTAL_GOALS', 'total de gols':'TOTAL_GOALS',
    'over under':'TOTAL_POINTS', 'total pontos':'TOTAL_POINTS', 'total points':'TOTAL_POINTS',
    'ambas equipes marcam':'BOTH_TEAMS_TO_SCORE', 'both teams to score':'BOTH_TEAMS_TO_SCORE',
    'both teams to score?':'BOTH_TEAMS_TO_SCORE', 'btts':'BOTH_TEAMS_TO_SCORE',
    'handicap':'HANDICAP', 'asian handicap':'HANDICAP', 'handicap asiatico':'HANDICAP', 'handicap asiático':'HANDICAP', 'handicap asiatico':'HANDICAP',
    'handicap asiático':'HANDICAP',
    'set winner':'SET_WINNER', 'vencedor do set':'SET_WINNER',
    'first set winner':'SET_WINNER', 'vencedor 1o set':'SET_WINNER',
    'resultado do 1 tempo':'FIRST_HALF_RESULT', 'resultado do 1º tempo':'FIRST_HALF_RESULT', 'primeiro gol':'FIRST_GOAL', 'first goal':'FIRST_GOAL',
    'correct score':'CORRECT_SCORE', 'placar correto':'CORRECT_SCORE',
}

SELECTION_ALIASES = {
    'home':'HOME','casa':'HOME','mandante':'HOME','1':'HOME',
    'draw':'DRAW','empate':'DRAW','x':'DRAW',
    'away':'AWAY','fora':'AWAY','visitante':'AWAY','2':'AWAY',
    'over':'OVER','mais':'OVER','mais de':'OVER',
    'under':'UNDER','menos':'UNDER','menos de':'UNDER',
    'yes':'YES','sim':'YES','no':'NO','nao':'NO','não':'NO',
    'home_or_draw':'HOME_OR_DRAW','casa_ou_empate':'HOME_OR_DRAW',
    'home_or_away':'HOME_OR_AWAY','casa_ou_fora':'HOME_OR_AWAY',
    'draw_or_away':'DRAW_OR_AWAY','empate_ou_fora':'DRAW_OR_AWAY',
}


def _ascii(value: str) -> str:
    return unicodedata.normalize('NFKD', str(value or '')).encode('ascii','ignore').decode('ascii')


def normalize_text(value: str) -> str:
    text = _ascii(value).lower()
    text = re.sub(r'[^a-z0-9]+', ' ', text)
    return re.sub(r'\s+', ' ', text).strip()


def slug(value: str) -> str:
    return normalize_text(value).replace(' ', '-')


def canonical_sport(value: str) -> str:
    key = normalize_text(value)
    return SPORT_ALIASES.get(key, slug(key).upper() or 'UNKNOWN')


def canonical_team(value: str) -> str:
    tokens = normalize_text(value).split()
    meaningful = [t for t in tokens if t not in GENERIC_TEAM_TOKENS]
    return ' '.join(meaningful or tokens)


def canonical_market(value: str, sport: str = '') -> str:
    key = normalize_text(value)
    return MARKET_ALIASES.get(key, slug(key).upper() or 'OTHER')


def canonical_selection(value: str, code: str = '') -> str:
    code_key = normalize_text(code).replace(' ', '_')
    if code_key in SELECTION_ALIASES:
        return SELECTION_ALIASES[code_key]
    key = normalize_text(value).replace(' ', '_')
    return SELECTION_ALIASES.get(key, slug(value).upper() or 'OTHER')


def normalize_line(line) -> str:
    if line is None or str(line).strip() == '':
        return 'NONE'
    try:
        d = Decimal(str(line).replace(',', '.')).quantize(Decimal('0.01'))
        return format(d.normalize(), 'f')
    except (InvalidOperation, ValueError):
        return normalize_text(str(line))


def parse_event_start(value) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        dt = value
    else:
        text = str(value).strip().replace('Z', '+00:00')
        try:
            dt = datetime.fromisoformat(text)
        except ValueError:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).replace(tzinfo=None)


def event_key(*, sport: str, home_team: str, away_team: str, event_start_at=None, league: str = '') -> str:
    sport_key = canonical_sport(sport)
    home = canonical_team(home_team)
    away = canonical_team(away_team)
    start = parse_event_start(event_start_at)
    # Mantemos a orientação casa/fora porque HOME e AWAY têm significado
    # operacional para mercados de resultado. A liga não entra na identidade
    # para tolerar nomes de competição diferentes entre bookmakers.
    start_key = start.strftime('%Y%m%d%H%M') if start else 'NO_START'
    return '|'.join([sport_key, home, away, start_key])


def market_key(*, market_type: str, market_name: str = '', line=None, sport: str = '') -> str:
    m = canonical_market(market_type or market_name, sport)
    return '|'.join([m, normalize_line(line)])
