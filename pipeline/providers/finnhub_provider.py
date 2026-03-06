"""
Finnhub provider — company news and supplementary quotes.
Free tier: 60 API calls/min, no daily cap.

Used for:
- Company news (primary news source)
- Market news
- Basic company profile
- Earnings calendar

Rate limiting: We self-throttle to 55 req/min to stay safely under 60.
"""

import time
from datetime import datetime, timedelta
from typing import Optional

import httpx

from pipeline.providers.base import NewsArticle, NewsDataProvider
from pipeline.config import FINNHUB_API_KEY, FINNHUB_RATE_LIMIT_PER_MIN
from pipeline.utils.logging import log


class FinnhubProvider(NewsDataProvider):
    """Fetches company news from Finnhub."""

    BASE_URL = "https://finnhub.io/api/v1"

    def __init__(self, api_key: str = FINNHUB_API_KEY):
        self._api_key = api_key
        self._request_count = 0
        self._window_start = time.time()

    def _throttle(self):
        """Simple rate limiter: max N requests per 60-second window."""
        self._request_count += 1
        elapsed = time.time() - self._window_start

        if elapsed < 60 and self._request_count >= FINNHUB_RATE_LIMIT_PER_MIN:
            sleep_time = 60 - elapsed + 0.5
            log.debug(f"Finnhub rate limit: sleeping {sleep_time:.1f}s")
            time.sleep(sleep_time)
            self._request_count = 0
            self._window_start = time.time()
        elif elapsed >= 60:
            self._request_count = 1
            self._window_start = time.time()

    def _get(self, endpoint: str, params: dict) -> Optional[dict | list]:
        """Make a GET request to Finnhub API."""
        self._throttle()
        params["token"] = self._api_key
        url = f"{self.BASE_URL}/{endpoint}"
        try:
            resp = httpx.get(url, params=params, timeout=15.0)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                log.warning("Finnhub rate limited. Sleeping 60s.")
                time.sleep(60)
                return self._get(endpoint, params)
            log.error(f"Finnhub HTTP error: {e}")
            return None
        except Exception as e:
            log.error(f"Finnhub request failed: {e}")
            return None

    # ------------------------------------------------------------------
    # NewsDataProvider
    # ------------------------------------------------------------------

    def get_news(self, ticker: str, company_name: str = "", days: int = 30) -> list[NewsArticle]:
        """Fetch company-specific news from Finnhub."""
        articles: list[NewsArticle] = []

        end = datetime.now()
        start = end - timedelta(days=days)

        data = self._get("company-news", {
            "symbol": ticker,
            "from": start.strftime("%Y-%m-%d"),
            "to": end.strftime("%Y-%m-%d"),
        })

        if not data or not isinstance(data, list):
            return articles

        for item in data:
            try:
                published = datetime.fromtimestamp(item.get("datetime", 0))
                headline = item.get("headline", "").strip()
                if not headline:
                    continue

                articles.append(NewsArticle(
                    headline=headline,
                    source=item.get("source", "Unknown"),
                    url=item.get("url", ""),
                    published_at=published,
                    summary=item.get("summary", ""),
                    relevance_score=1.0,  # Finnhub returns ticker-specific news
                ))
            except Exception as e:
                log.debug(f"Skipping malformed Finnhub article: {e}")
                continue

        log.info(f"Finnhub: {len(articles)} articles for {ticker}")
        return articles

    # ------------------------------------------------------------------
    # Supplementary methods
    # ------------------------------------------------------------------

    def get_earnings_calendar(self, ticker: str) -> list[dict]:
        """Fetch upcoming and recent earnings dates."""
        end = datetime.now() + timedelta(days=90)
        start = datetime.now() - timedelta(days=365)

        data = self._get("stock/earnings", {"symbol": ticker})
        if not data or not isinstance(data, list):
            return []
        return data

    def get_company_profile(self, ticker: str) -> Optional[dict]:
        """Fetch basic company profile."""
        data = self._get("stock/profile2", {"symbol": ticker})
        return data if isinstance(data, dict) else None
