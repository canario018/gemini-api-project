from app.collectors.generic_json import GenericSportsJsonCollector


class VBetCollector(GenericSportsJsonCollector):
    def __init__(self, timeout: int = 15, api_endpoint: str | None = None):
        super().__init__(
            sportsbook_name="VBET",
            api_endpoint=api_endpoint or "https://www.vbet.bet.br/desktop/pageBuilder/sport.json",
            referer="https://www.vbet.bet.br/pb/pre-match",
            origin="https://www.vbet.bet.br",
            params={"v": "1788553109976"},
            timeout=timeout,
        )
