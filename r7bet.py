from app.collectors.sportsdata import SportsDataEventCollector

class R7BetCollector(SportsDataEventCollector):
    def __init__(self, timeout: int = 15, api_endpoint: str | None = None):
        super().__init__(sportsbook_name="R7Bet", api_endpoint=api_endpoint or "https://r7.bet.br/api/sportsbook/data/v1/sportsdata/featured/events", referer="https://r7.bet.br/", origin="https://r7.bet.br", params={"featureTag":"all","sportIDs":"1","includeMarkets":"default","take":"50","skip":"0","locale":"br-pt"}, timeout=timeout)
