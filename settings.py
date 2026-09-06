from __future__ import annotations

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
DATA_DIR.mkdir(exist_ok=True)
RAW_DIR.mkdir(exist_ok=True)


class Settings(BaseSettings):
    database_url: str = f"sqlite:///{DATA_DIR / 'betting.db'}"
    log_level: str = "INFO"
    idempotency_window_seconds: int = 60
    request_timeout_seconds: int = 15
    collectors: str = "estrelabet,lotogreen,multibet"
    save_raw_json: bool = True
    raw_data_dir: str = str(RAW_DIR)
    analysis_lookback_hours: int = 24
    analysis_min_profit_percent: float = 0.10
    bankroll: float = 1000.0
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    betano_api_endpoint: str = ""
    superbet_api_endpoint: str = ""
    novibet_api_endpoint: str = ""
    r7bet_api_endpoint: str = ""
    betbet_api_endpoint: str = ""
    vbet_api_endpoint: str = ""
    kbet7_api_endpoint: str = ""

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
