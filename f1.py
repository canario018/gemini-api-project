from __future__ import annotations
from datetime import date, datetime, timezone, timedelta
from bs4 import BeautifulSoup
from app.data_harvest.contracts import HistoricalObservation
from app.data_harvest.providers.base import SportsStatsProvider
from app.data_harvest.providers.http import HTTPClient

class Formula1OfficialProvider(SportsStatsProvider):
    name = "formula1_official"; sport = "formula1"; BASE = "https://www.formula1.com/en/results"
    def __init__(self, timeout: float = 20.0): self.http = HTTPClient(timeout)
    def collect(self, start: date, end: date):
        # Official site exposes season result pages; table markup can change, so we preserve raw HTML.
        for year in range(start.year, end.year + 1):
            url = f"{self.BASE}/{year}/races"
            html = self.http.get_text(url)
            soup = BeautifulSoup(html, "html.parser")
            text = " ".join(soup.stripped_strings)
            yield HistoricalObservation(source=self.name, sport=self.sport, event_id=f"f1-season-{year}", observed_at=datetime.now(timezone.utc).isoformat(),
                competition="Formula 1", metrics={"season": year, "page_text_length": len(text)}, raw={"url": url, "text_excerpt": text[:10000]}, source_url=url)
