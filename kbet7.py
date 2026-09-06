from app.collectors.generic_json import GenericSportsJsonCollector


class KBet7Collector(GenericSportsJsonCollector):
    def __init__(self, timeout: int = 15, api_endpoint: str | None = None):
        super().__init__(
            sportsbook_name="7KBet",
            api_endpoint=api_endpoint or "https://prod20350-kbet-152319626.fssb.io/api/sportscenter/carousels/events-with-items",
            referer="https://7k.bet.br/",
            origin="https://7k.bet.br",
            timeout=timeout,
        )
