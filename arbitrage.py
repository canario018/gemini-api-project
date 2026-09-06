from __future__ import annotations

import itertools
import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Iterable

from sqlalchemy.orm import Session

from app.database.models import OddSnapshotModel


SUPPORTED_MARKETS = {
    "MATCH_RESULT": ("HOME", "DRAW", "AWAY"),
    "TOTAL_GOALS": ("OVER", "UNDER"),
    "BOTH_TEAMS_TO_SCORE": ("YES", "NO"),
}


@dataclass(frozen=True)
class ArbitrageLeg:
    bookmaker: str
    selection_code: str
    selection_name: str
    odd: float
    collected_at: datetime | None = None
    event_id: str | None = None


@dataclass(frozen=True)
class Surebet:
    event_key: str
    home_team: str
    away_team: str
    market_type: str
    line: float | None
    probability_sum: float
    profit_percent: float
    legs: tuple[ArbitrageLeg, ...]
    bankroll: float = 0.0
    guaranteed_return: float = 0.0
    guaranteed_profit: float = 0.0
    max_age_seconds: float = 0.0
    timestamp_spread_seconds: float = 0.0
    bookmaker_count: int = 0
    min_odd: float = 0.0

    @property
    def is_profitable(self) -> bool:
        return self.probability_sum < 1.0 and self.profit_percent > 0

    def stakes(self, bankroll: float | None = None) -> dict[str, float]:
        """Retorna a stake por seleção, proporcional a 1/odd."""
        total = self.bankroll if bankroll is None else float(bankroll)
        if total <= 0 or self.probability_sum <= 0:
            return {leg.selection_code: 0.0 for leg in self.legs}
        return {
            leg.selection_code: total * (1.0 / leg.odd) / self.probability_sum
            for leg in self.legs
        }


def _norm(value: str) -> str:
    text = unicodedata.normalize("NFKD", value or "").encode("ascii", "ignore").decode("ascii")
    text = text.lower()
    # Remove pontuação sem juntar palavras: "FC.Bayern" -> "fc bayern".
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _team_key(value: str) -> str:
    """Chave conservadora para comparar equipes entre bookmakers.

    Mantemos tokens do nome e removemos somente marcadores genéricos muito
    comuns. Não usamos fuzzy matching para não criar falsos positivos.
    """
    tokens = _norm(value).split()
    generic = {"fc", "futebol", "club", "clube", "sc", "ec", "esporte"}
    meaningful = [token for token in tokens if token not in generic]
    return " ".join(meaningful or tokens)


def event_identity(row: OddSnapshotModel) -> tuple:
    """Identidade canônica do evento + mercado.

    O campo persistido é criado pelo Canonical/Event Matching do BLOCO 6.
    O fallback mantém compatibilidade com bancos antigos.
    """
    canonical = getattr(row, "canonical_event_id", None)
    market = getattr(row, "canonical_market", None) or row.market_type
    line = row.line
    if canonical:
        return (canonical, market, line)
    teams = tuple(sorted((_team_key(row.home_team), _team_key(row.away_team))))
    return (_norm(row.sport), teams, market, line)


def _event_key(row: OddSnapshotModel) -> tuple:
    # Compatibilidade interna com versões anteriores do módulo.
    return event_identity(row)


def latest_rows(
    db: Session,
    lookback_hours: int = 24,
    max_age_minutes: int | None = None,
) -> list[OddSnapshotModel]:
    """Seleciona somente a cotação mais recente por evento/casa/seleção.

    O lookback limita o histórico consultado; max_age_minutes evita que uma
    odd antiga apareça como oportunidade atual.
    """
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    cutoff = now - timedelta(hours=lookback_hours)
    if max_age_minutes is not None:
        cutoff = max(cutoff, now - timedelta(minutes=max_age_minutes))

    rows = (
        db.query(OddSnapshotModel)
        .filter(OddSnapshotModel.collected_at >= cutoff)
        .order_by(OddSnapshotModel.collected_at.desc(), OddSnapshotModel.id.desc())
        .all()
    )

    latest: dict[tuple, OddSnapshotModel] = {}
    for row in rows:
        key = (event_identity(row), row.bookmaker, row.selection_code)
        if key not in latest:
            latest[key] = row
    return list(latest.values())


def best_odds(rows: Iterable[OddSnapshotModel]) -> dict[tuple, dict[str, OddSnapshotModel]]:
    """Cria a visão de melhor odd por seleção, preservando a origem."""
    result: dict[tuple, dict[str, OddSnapshotModel]] = {}
    for row in rows:
        universe = SUPPORTED_MARKETS.get(row.market_type)
        if not universe or row.selection_code not in universe or row.odd <= 1:
            continue
        event = event_identity(row)
        current = result.setdefault(event, {})
        previous = current.get(row.selection_code)
        if previous is None or row.odd > previous.odd:
            current[row.selection_code] = row
    return result


def _build_candidate(
    combo: tuple[OddSnapshotModel, ...],
    probability_sum: float,
    bankroll: float,
) -> Surebet:
    first = combo[0]
    timestamps = [r.collected_at for r in combo if r.collected_at is not None]
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    ages = [max(0.0, (now - ts).total_seconds()) for ts in timestamps]
    spread = (max(timestamps) - min(timestamps)).total_seconds() if timestamps else 0.0
    profit_percent = (1.0 / probability_sum - 1.0) * 100.0
    guaranteed_return = bankroll / probability_sum if bankroll > 0 else 0.0
    guaranteed_profit = guaranteed_return - bankroll
    legs = tuple(
        ArbitrageLeg(
            bookmaker=r.bookmaker,
            selection_code=r.selection_code,
            selection_name=r.selection_name,
            odd=r.odd,
            collected_at=r.collected_at,
            event_id=str(getattr(r, "event_id", "")) or None,
        )
        for r in combo
    )
    return Surebet(
        event_key="|".join(map(str, event_identity(first))),
        home_team=first.home_team,
        away_team=first.away_team,
        market_type=first.market_type,
        line=first.line,
        probability_sum=probability_sum,
        profit_percent=profit_percent,
        legs=legs,
        bankroll=bankroll,
        guaranteed_return=guaranteed_return,
        guaranteed_profit=guaranteed_profit,
        max_age_seconds=max(ages, default=0.0),
        timestamp_spread_seconds=spread,
        bookmaker_count=len({r.bookmaker for r in combo}),
        min_odd=min(r.odd for r in combo),
    )


def find_surebets(
    rows: Iterable[OddSnapshotModel],
    min_profit_percent: float = 0.10,
    max_outcomes: int = 3,
    max_age_seconds: int | None = 180,
    max_timestamp_spread_seconds: int | None = 30,
    distinct_bookmakers: bool = True,
    bankroll: float = 0.0,
) -> list[Surebet]:
    """Motor de arbitragem com validações de mercado e frescor.

    Regras:
    - somente mercados com universo de resultados conhecido;
    - todas as saídas precisam existir;
    - usa a melhor odd disponível por seleção;
    - opcionalmente exige uma casa diferente por perna;
    - rejeita snapshots muito antigos ou desalinhados no tempo;
    - procura a combinação de casas que minimiza Σ(1/odd).
    """
    grouped: dict[tuple, list[OddSnapshotModel]] = {}
    for row in rows:
        if row.market_type not in SUPPORTED_MARKETS:
            continue
        if row.selection_code not in SUPPORTED_MARKETS[row.market_type] or row.odd <= 1:
            continue
        grouped.setdefault(event_identity(row), []).append(row)

    results: list[Surebet] = []
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    for key, group in grouped.items():
        universe = SUPPORTED_MARKETS.get(getattr(group[0], "market_type", ""), ())
        if len(universe) > max_outcomes:
            continue

        # Primeiro elimina duplicidade temporal por casa/seleção e conserva a melhor odd.
        by_selection: dict[str, dict[str, OddSnapshotModel]] = {s: {} for s in universe}
        for row in group:
            current = by_selection[row.selection_code].get(row.bookmaker)
            if current is None or row.odd > current.odd or (
                row.odd == current.odd and row.collected_at > current.collected_at
            ):
                by_selection[row.selection_code][row.bookmaker] = row

        if any(not by_selection[s] for s in universe):
            continue

        # Todas as combinações possíveis entre casas por seleção.
        best_combo: tuple[float, tuple[OddSnapshotModel, ...]] | None = None
        for combo in itertools.product(*(list(by_selection[s].values()) for s in universe)):
            books = [r.bookmaker for r in combo]
            if distinct_bookmakers and len(set(books)) != len(books):
                continue

            timestamps = [r.collected_at for r in combo if r.collected_at is not None]
            if max_age_seconds is not None and any(
                (now - ts).total_seconds() > max_age_seconds for ts in timestamps
            ):
                continue
            if max_timestamp_spread_seconds is not None and timestamps:
                spread = (max(timestamps) - min(timestamps)).total_seconds()
                if spread > max_timestamp_spread_seconds:
                    continue

            probability_sum = sum(1.0 / r.odd for r in combo)
            if best_combo is None or probability_sum < best_combo[0]:
                best_combo = (probability_sum, combo)

        if best_combo is None:
            continue

        probability_sum, combo = best_combo
        if probability_sum >= 1.0:
            continue
        candidate = _build_candidate(combo, probability_sum, bankroll)
        if candidate.profit_percent < min_profit_percent:
            continue
        results.append(candidate)

    return sorted(
        results,
        key=lambda x: (x.profit_percent, x.min_odd, -x.max_age_seconds),
        reverse=True,
    )


def analyze_database(
    db: Session,
    lookback_hours: int = 24,
    min_profit_percent: float = 0.10,
    max_age_seconds: int | None = 180,
    max_timestamp_spread_seconds: int | None = 30,
    distinct_bookmakers: bool = True,
    bankroll: float = 0.0,
) -> list[Surebet]:
    rows = latest_rows(db, lookback_hours=lookback_hours)
    return find_surebets(
        rows,
        min_profit_percent=min_profit_percent,
        max_age_seconds=max_age_seconds,
        max_timestamp_spread_seconds=max_timestamp_spread_seconds,
        distinct_bookmakers=distinct_bookmakers,
        bankroll=bankroll,
    )
