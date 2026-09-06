from app.collectors.altenar import AltenarCouponCollector


class OnabetCollector(AltenarCouponCollector):
    def __init__(self, timeout: int = 15):
        super().__init__(
            sportsbook_name="Onabet",
            integration="onabet",
            referer="https://onabet.com/",
            timeout=timeout,
        )
