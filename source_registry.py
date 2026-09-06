from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CollectorSource:
    name: str
    bookmaker: str
    endpoint: str
    source_family: str
    configured_by_user: bool = True
    odds_schema_confirmed: bool = False


SOURCES = {
    "estrelabet": CollectorSource("estrelabet", "EstrelaBet", "https://sb2frontend-altenar2.biahosted.com/api/widget/GetCouponEvents", "ALTENAR", True, True),
    "lotogreen": CollectorSource("lotogreen", "Lotogreen", "https://sb2frontend-altenar2.biahosted.com/api/widget/GetCouponEvents", "ALTENAR", True, True),
    "multibet": CollectorSource("multibet", "Multibet", "https://sb2frontend-altenar2.biahosted.com/api/widget/GetCouponEvents", "ALTENAR", True, True),
    "apostaganha": CollectorSource("apostaganha", "ApostaGanha", "https://sb2frontend-altenar2.biahosted.com/api/widget/GetCouponEvents", "ALTENAR", True, False),
    "onabet": CollectorSource("onabet", "Onabet", "https://sb2frontend-altenar2.biahosted.com/api/widget/GetCouponEvents", "ALTENAR", True, False),
    "betano": CollectorSource("betano", "Betano", "https://www.betano.bet.br/api/sports/FOOT/hot/trending/leagues/10008/events", "BETANO", True, False),
    "r7bet": CollectorSource("r7bet", "R7Bet", "https://r7.bet.br/api/sportsbook/data/v1/sportsdata/featured/events", "SPORTSDATA", True, False),
    "betbet": CollectorSource("betbet", "Bet.Bet", "https://betpontobet.bet.br/api/sports/rogue-proxy/v1/sportsdata/events", "SPORTSDATA", True, False),
    "vbet": CollectorSource("vbet", "VBET", "https://www.vbet.bet.br/desktop/pageBuilder/sport.json", "PAGEBUILDER", True, False),
    "7kbet": CollectorSource("7kbet", "7KBet", "https://prod20350-kbet-152319626.fssb.io/api/sportscenter/carousels/events-with-items", "FSSB", True, False),
    "superbet": CollectorSource("superbet", "Superbet", "", "CONFIGURED_ENDPOINT", False, False),
    "novibet": CollectorSource("novibet", "Novibet", "", "CONFIGURED_ENDPOINT", False, False),
}
