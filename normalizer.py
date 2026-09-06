from __future__ import annotations

import re
import unicodedata


def clean_text(value) -> str:
    if value is None:
        return ""
    return " ".join(str(value).strip().split())


def slug(value) -> str:
    text = unicodedata.normalize("NFKD", clean_text(value)).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def build_raw_key(bookmaker, event_id, market_type, home_team, away_team, selection_code, line=None) -> str:
    line_part = "none" if line is None else str(line).replace(".", "_")
    return "|".join([
        slug(bookmaker), str(event_id), slug(market_type),
        slug(home_team), slug(away_team), slug(selection_code), line_part
    ])
