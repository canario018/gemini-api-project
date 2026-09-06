from __future__ import annotations
from datetime import date, datetime, timezone
from bs4 import BeautifulSoup
from app.data_harvest.contracts import HistoricalObservation
from app.data_harvest.providers.base import SportsStatsProvider
from app.data_harvest.providers.http import HTTPClient

class ATPStatsProvider(SportsStatsProvider):
    name = "atp_official"; sport = "tennis"; BASE = "https://www.atptour.com/en/stats/stats-home"
    def __init__(self, timeout: float = 20.0): self.http = HTTPClient(timeout)
    def collect(self, start: date, end: date):
        html = self.http.get_text(self.BASE); soup = BeautifulSoup(html, "html.parser")
        links = [a.get("href") for a in soup.find_all("a") if a.get("href") and "stats" in a.get("href")]
        yield HistoricalObservation(source=self.name, sport=self.sport, event_id=f"atp-stats-{start.isoformat()}-{end.isoformat()}", observed_at=datetime.now(timezone.utc).isoformat(),
            competition="ATP", metrics={"stats_link_count": len(links)}, raw={"links": links[:200]}, source_url=self.BASE)
