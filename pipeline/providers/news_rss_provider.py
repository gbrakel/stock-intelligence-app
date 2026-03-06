"""
Google News RSS provider — free, no API key, no hard rate limit.
Supplements Finnhub for broader news coverage and non-financial sources.

URL format: https://news.google.com/rss/search?q=QUERY&hl=en-US&gl=US&ceid=US:en

Limitations:
- Undocumented URL parameters, could change without notice
- Only returns ~10-20 recent articles per query
- No official API; this is RSS parsing
- Suitable for personal use at moderate request rates
"""

import time
from datetime import datetime
from typing import Optional
from email.utils import parsedate_to_datetime

import feedparser

from pipeline.providers.base import NewsArticle, NewsDataProvider
from pipeline.utils.logging import log


class GoogleNewsRSSProvider(NewsDataProvider):
    """Fetches financial news headlines via Google News RSS."""

    BASE_URL = "https://news.google.com/rss/search"

    def __init__(self, delay_sec: float = 2.0):
        self._delay = delay_sec

    def get_news(self, ticker: str, company_name: str = "", days: int = 30) -> list[NewsArticle]:
        """Fetch news articles from Google News RSS for a company."""
        articles: list[NewsArticle] = []

        # Search by both ticker and company name for broader coverage
        queries = [f"{ticker} stock"]
        if company_name:
            queries.append(f'"{company_name}"')

        seen_urls: set[str] = set()

        for query in queries:
            time.sleep(self._delay)
            feed_articles = self._fetch_feed(query, ticker)
            for article in feed_articles:
                if article.url not in seen_urls:
                    seen_urls.add(article.url)
                    articles.append(article)

        log.info(f"Google News RSS: {len(articles)} articles for {ticker}")
        return articles

    def _fetch_feed(self, query: str, ticker: str) -> list[NewsArticle]:
        """Parse a single RSS feed URL."""
        articles = []
        url = f"{self.BASE_URL}?q={query}&hl=en-US&gl=US&ceid=US:en"

        try:
            feed = feedparser.parse(url)

            if feed.bozo and not feed.entries:
                log.warning(f"Google News RSS parse error for query '{query}': {feed.bozo_exception}")
                return articles

            for entry in feed.entries:
                headline = entry.get("title", "").strip()
                if not headline:
                    continue

                # Extract source from title format "Headline - Source"
                source = "Google News"
                if " - " in headline:
                    parts = headline.rsplit(" - ", 1)
                    headline = parts[0].strip()
                    source = parts[1].strip() if len(parts) > 1 else source

                # Parse publication date
                published = self._parse_date(entry)

                link = entry.get("link", "")
                summary = entry.get("summary", "")
                # Clean HTML from summary
                if "<" in summary:
                    summary = ""

                articles.append(NewsArticle(
                    headline=headline,
                    source=source,
                    url=link,
                    published_at=published,
                    summary=summary,
                    relevance_score=0.8,  # Slightly lower than Finnhub (broader search)
                ))

        except Exception as e:
            log.error(f"Google News RSS fetch failed for '{query}': {e}")

        return articles

    def _parse_date(self, entry: dict) -> datetime:
        """Parse RSS entry date, with fallback to now."""
        published_str = entry.get("published", "")
        if published_str:
            try:
                return parsedate_to_datetime(published_str)
            except Exception:
                pass
        return datetime.now()
