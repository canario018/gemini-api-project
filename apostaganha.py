from app.collectors.altenar import AltenarCouponCollector


class ApostaGanhaCollector(AltenarCouponCollector):
    def __init__(self):
        super().__init__(
            sportsbook_name="ApostaGanha",
            integration="apostaganha",
            referer="https://apostaganha.bet.br/",
        )
