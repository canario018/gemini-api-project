from __future__ import annotations
from datetime import date, datetime, timezone
from bs4 import BeautifulSoup, Comment
from app.data_harvest.contracts import HistoricalObservation
from app.data_harvest.providers.base import SportsStatsProvider
from app.data_harvest.providers.http import HTTPClient

class BasketballReferenceProvider(SportsStatsProvider):
    name = "basketball_reference"; sport = "basketball"; BASE = "https://www.basketball-reference.com"
    def __init__(self, league: str = "NBA", timeout: float = 20.0): self.league = league; self.http = HTTPClient(timeout)
    def collect(self, start: date, end: date):
        for year in range(start.year, end.year + 1):
            url = f"{self.BASE}/leagues/{self.league}_{year}_advanced.html"
            html = self.http.get_text(url); soup = BeautifulSoup(html, "html.parser")
            # Preserve a compact extraction of advanced-stat rows. Comments often contain tables.
            tables = list(soup.find_all("table"))
            for c in soup.find_all(string=lambda x: isinstance(x, Comment)):
                if "advanced" in str(c).lower():
                    cs = BeautifulSoup(str(c), "html.parser"); tables.extend(cs.find_all("table"))
            count = 0
            for table in tables[:3]:
                for row in table.find_all("tr"):
                    cells = [x.get_text(" ", strip=True) for x in row.find_all(["th", "td"])]
                    if len(cells) < 4: continue
                    yield HistoricalObservation(source=self.name, sport=self.sport, event_id=f"basketball-ref-{year}-{count}", observed_at=datetime.now(timezone.utc).isoformat(), competition=self.league,
                        team_id=cells[0], metrics={"row": cells}, raw={"season": year, "row": cells}, source_url=url); count += 1
