from __future__ import annotations
from datetime import date, datetime, timezone
from bs4 import BeautifulSoup, Comment
from app.data_harvest.contracts import HistoricalObservation
from app.data_harvest.providers.base import SportsStatsProvider
from app.data_harvest.providers.http import HTTPClient

class FBrefFootballProvider(SportsStatsProvider):
    name = "fbref_football"; sport = "football"; BASE = "https://fbref.com/en/comps"
    COMPETITIONS = {"premier_league": 9, "brasileirao": 24, "la_liga": 12, "serie_a_italy": 11, "bundesliga": 20}
    def __init__(self, timeout: float = 20.0): self.http = HTTPClient(timeout)
    def collect(self, start: date, end: date):
        for label, comp_id in self.COMPETITIONS.items():
            for season in range(start.year, end.year + 1):
                url = f"{self.BASE}/{comp_id}/{season}/{season}-{season+1 if comp_id not in {24} else season}-Standard-Stats"
                try: html = self.http.get_text(url)
                except Exception: continue
                soup = BeautifulSoup(html, "html.parser"); tables = list(soup.find_all("table"))
                for c in soup.find_all(string=lambda x: isinstance(x, Comment)):
                    if "stats_standard" in str(c): tables.extend(BeautifulSoup(str(c), "html.parser").find_all("table"))
                for table in tables[:4]:
                    for row in table.find_all("tr"):
                        cells = [x.get_text(" ", strip=True) for x in row.find_all(["th", "td"])]
                        if len(cells) < 5: continue
                        yield HistoricalObservation(source=self.name, sport=self.sport, event_id=f"fbref-{label}-{season}-{hash(tuple(cells))}", observed_at=datetime.now(timezone.utc).isoformat(), competition=label, team_id=cells[0], metrics={"row": cells}, raw={"season": season, "row": cells}, source_url=url)
