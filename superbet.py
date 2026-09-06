import logging
from app.collectors.base import BaseSportsbookCollector

logger = logging.getLogger(__name__)


class SuperbetCollector(BaseSportsbookCollector):
    """Placeholder seguro: só entra no pipeline quando o endpoint real estiver configurado."""
    def __init__(self, api_endpoint=None):
        if not api_endpoint:
            raise ValueError("SUPERBET_API_ENDPOINT não configurado. Não invente um endpoint.")
        super().__init__("Superbet", api_endpoint)
