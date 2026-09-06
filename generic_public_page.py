import datetime
import logging
from bs4 import BeautifulSoup
from app.collectors.base import BaseCollector
from app.normalization.normalizer import DataNormalizer
from app.validation.validators import OddsValidator

logger = logging.getLogger(__name__)

class GenericPublicPageCollector(BaseCollector):
    def __init__(self, source_url: str, html_content: str = None):
        super().__init__(source_url, bookmaker_name="PublicBookmakerSim")
        self.html_content = html_content

    def collect(self) -> list:
        logger.info(f"Iniciando coleta na fonte: {self.source_url}")
        raw_html = self.html_content
        
        if not raw_html:
            return []

        soup = BeautifulSoup(raw_html, 'html.parser')
        matches = soup.find_all('div', class_='match-item')
        extracted_data = []
        now = datetime.datetime.utcnow()

        for match in matches:
            event_id = match.get('data-event-id', 'unknown_id')
            league = match.get('data-league', 'General League')
            sport = match.get('data-sport', 'Football')
            
            home_team = match.find('span', class_='home-team').get_text(strip=True)
            away_team = match.find('span', class_='away-team').get_text(strip=True)

            markets = match.find_all('div', class_='market-box')
            for market in markets:
                market_name = market.get('data-market-name')
                market_type = market.get('data-market-type', '1X2')

                outcomes = market.find_all('button', class_='outcome-btn')
                for outcome in outcomes:
                    sel_name = outcome.find('span', class_='sel-name').get_text(strip=True)
                    sel_code = outcome.get('data-selection-code', sel_name)
                    odd_val = float(outcome.find('span', class_='sel-odd').get_text(strip=True))
                    line_val = outcome.get('data-line')
                    line = float(line_val) if line_val else None

                    raw_key = DataNormalizer.generate_raw_key(
                        self.bookmaker_name, event_id, market_name, sel_code, line
                    )

                    record = {
                        "collected_at": now,
                        "bookmaker": self.bookmaker_name,
                        "source_url": self.source_url,
                        "sport": sport,
                        "league": league,
                        "event_id": event_id,
                        "home_team": home_team,
                        "away_team": away_team,
                        "market_name": market_name,
                        "market_type": market_type,
                        "selection_name": sel_name,
                        "selection_code": sel_code,
                        "line": line,
                        "odd": odd_val,
                        "currency": "BRL",
                        "raw_key": raw_key
                    }

                    if OddsValidator.is_valid_odds_record(record):
                        extracted_data.append(record)
                    else:
                        logger.warning(f"Registro descartado por validação estrita: {record}")

        logger.info(f"Coleta finalizada. {len(extracted_data)} odds válidas extraídas.")
        return extracted_data
