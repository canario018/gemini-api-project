from app.collectors.sportsdata import SportsDataEventCollector

class BetBetCollector(SportsDataEventCollector):
    def __init__(self, timeout: int = 15, api_endpoint: str | None = None):
        super().__init__(sportsbook_name="Bet.Bet", api_endpoint=api_endpoint or "https://betpontobet.bet.br/api/sports/rogue-proxy/v1/sportsdata/events", referer="https://betpontobet.bet.br/esportes", origin="https://betpontobet.bet.br", params={"take":"50","orderBy":"leagueOrder","includeMarkets":"default","eventType":"Fixture","sportIDs":"1"}, timeout=timeout)
