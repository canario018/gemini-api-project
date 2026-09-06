import sqlite3
from datetime import datetime

class BettingDatabase:
    def __init__(self, db_name="sportsbook_data.db"):
        self.db_name = db_name
        self.create_tables()

    def connect(self):
        return sqlite3.connect(self.db_name)

    def create_tables(self):
        with self.connect() as conn:
            cursor = conn.cursor()
            # Tabela unificada para armazenar as odds capturadas de qualquer casa
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS odds_market (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sportsbook TEXT,
                    event_id TEXT,
                    event_name TEXT,
                    market_name TEXT,
                    selection_name TEXT,
                    odd_value REAL,
                    captured_at TEXT
                )
            """)
            conn.commit()

    def insert_odd(self, sportsbook, event_id, event_name, market_name, selection_name, odd_value):
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO odds_market (sportsbook, event_id, event_name, market_name, selection_name, odd_value, captured_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (sportsbook, event_id, event_name, market_name, selection_name, odd_value, datetime.now().isoformat()))
            conn.commit()