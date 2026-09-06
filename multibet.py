from app.collectors.altenar import AltenarCouponCollector


class MultibetCollector(AltenarCouponCollector):
    def __init__(self, timeout: int = 15):
        super().__init__(
            sportsbook_name="Multibet",
            integration="multibet.br",
            referer="https://multi.bet.br/",
            timeout=timeout,
        )
