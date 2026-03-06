"""
JSON exporter — writes all computed data to the data/ directory
as static JSON files consumed by the Next.js frontend.
"""

import json
import os
from datetime import date, datetime
from pathlib import Path
from typing import Any

from pipeline.config import DATA_DIR
from pipeline.utils.logging import log


class JSONExporter:
    """Writes pipeline outputs to data/ as JSON files."""

    def __init__(self, data_dir: Path = DATA_DIR):
        self._dir = data_dir
        self._ensure_dirs()

    def _ensure_dirs(self):
        """Create all required subdirectories."""
        for subdir in ["rankings", "scores", "financials", "prices", "news", "risk", "signals"]:
            (self._dir / subdir).mkdir(parents=True, exist_ok=True)

    def _write(self, path: Path, data: Any):
        """Write JSON to file with consistent formatting."""
        with open(path, "w") as f:
            json.dump(data, f, indent=2, default=_json_serializer)
        log.debug(f"Wrote {path}")

    # ------------------------------------------------------------------
    # Stock universe
    # ------------------------------------------------------------------

    def export_stocks(self, stocks: list[dict]):
        """Write data/stocks.json."""
        self._write(self._dir / "stocks.json", stocks)

    # ------------------------------------------------------------------
    # Rankings
    # ------------------------------------------------------------------

    def export_rankings(self, rankings: list[dict], run_date: date):
        """Write data/rankings/latest.json and data/rankings/{date}.json."""
        payload = {
            "date": run_date.isoformat(),
            "generated_at": datetime.now().isoformat(),
            "rankings": rankings,
        }
        self._write(self._dir / "rankings" / "latest.json", payload)
        self._write(self._dir / "rankings" / f"{run_date.isoformat()}.json", payload)

    # ------------------------------------------------------------------
    # Per-stock scores (append to history)
    # ------------------------------------------------------------------

    def export_score(self, ticker: str, score_entry: dict, run_date: date):
        """Append today's score to data/scores/{ticker}.json and update latest."""
        path = self._dir / "scores" / f"{ticker}.json"
        existing = self._read_existing(path, default={"ticker": ticker, "history": []})

        # Append new entry (avoid duplicates for same date)
        existing["history"] = [
            h for h in existing["history"] if h.get("date") != run_date.isoformat()
        ]
        existing["history"].insert(0, score_entry)

        # Keep last 365 days
        existing["history"] = existing["history"][:365]

        self._write(path, existing)

    def export_latest_scores(self, all_scores: list[dict]):
        """Write data/scores/latest.json (all stocks, today's scores)."""
        self._write(self._dir / "scores" / "latest.json", all_scores)

    # ------------------------------------------------------------------
    # Financials
    # ------------------------------------------------------------------

    def export_financials(self, ticker: str, data: dict):
        """Write data/financials/{ticker}.json."""
        self._write(self._dir / "financials" / f"{ticker}.json", data)

    # ------------------------------------------------------------------
    # Prices
    # ------------------------------------------------------------------

    def export_prices(self, ticker: str, prices: list[dict]):
        """Write data/prices/{ticker}.json."""
        self._write(self._dir / "prices" / f"{ticker}.json", {
            "ticker": ticker,
            "prices": prices,
        })

    # ------------------------------------------------------------------
    # News
    # ------------------------------------------------------------------

    def export_news(self, ticker: str, articles: list[dict]):
        """Write data/news/{ticker}.json."""
        self._write(self._dir / "news" / f"{ticker}.json", {
            "ticker": ticker,
            "articles": articles,
        })

    # ------------------------------------------------------------------
    # Risk
    # ------------------------------------------------------------------

    def export_risk(self, ticker: str, risk_data: dict):
        """Write data/risk/{ticker}.json."""
        self._write(self._dir / "risk" / f"{ticker}.json", risk_data)

    # ------------------------------------------------------------------
    # Signals
    # ------------------------------------------------------------------

    def export_alerts(self, alerts: list[dict]):
        """Write data/signals/alerts.json."""
        self._write(self._dir / "signals" / "alerts.json", alerts)

    def export_signal_changes(self, changes: list[dict]):
        """Write data/signals/changes.json."""
        self._write(self._dir / "signals" / "changes.json", changes)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _read_existing(self, path: Path, default: Any = None) -> Any:
        """Read existing JSON file or return default."""
        if path.exists():
            try:
                with open(path) as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        return default if default is not None else {}


def _json_serializer(obj):
    """Custom JSON serializer for dates and datetimes."""
    if isinstance(obj, (date, datetime)):
        return obj.isoformat()
    if hasattr(obj, "__dict__"):
        return obj.__dict__
    raise TypeError(f"Type {type(obj)} not serializable")
