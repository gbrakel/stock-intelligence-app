"""
Base interfaces for all data providers.
Every data source implements one or more of these abstract classes,
making providers swappable without changing engine logic.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional


# ---------------------------------------------------------------------------
# Data containers returned by providers
# ---------------------------------------------------------------------------

@dataclass
class FinancialSnapshot:
    """One period (quarter or year) of financial data for a company."""
    period_end: date
    period_type: str  # "quarterly" or "annual"
    revenue: Optional[float] = None
    net_income: Optional[float] = None
    eps: Optional[float] = None
    gross_margin: Optional[float] = None
    operating_margin: Optional[float] = None
    net_margin: Optional[float] = None
    free_cash_flow: Optional[float] = None
    total_debt: Optional[float] = None
    total_equity: Optional[float] = None
    cash_and_equivalents: Optional[float] = None
    roe: Optional[float] = None
    roa: Optional[float] = None
    shares_outstanding: Optional[float] = None


@dataclass
class ValuationData:
    """Current valuation metrics for a stock."""
    pe_ratio: Optional[float] = None
    forward_pe: Optional[float] = None
    ev_ebitda: Optional[float] = None
    price_to_sales: Optional[float] = None
    peg_ratio: Optional[float] = None
    market_cap: Optional[float] = None
    enterprise_value: Optional[float] = None


@dataclass
class PriceBar:
    """Single OHLCV price bar."""
    date: date
    open: float
    high: float
    low: float
    close: float
    volume: int
    adj_close: Optional[float] = None


@dataclass
class NewsArticle:
    """A single news article with optional sentiment (filled by sentiment engine)."""
    headline: str
    source: str
    url: str
    published_at: datetime
    summary: str = ""
    sentiment: Optional[str] = None       # "positive", "neutral", "negative"
    sentiment_score: Optional[float] = None  # -1.0 to 1.0
    sentiment_confidence: Optional[float] = None  # 0.0 to 1.0
    relevance_score: float = 1.0
    event_type: Optional[str] = None      # "earnings", "partnership", "lawsuit", etc.


@dataclass
class StockQuote:
    """Real-time (or delayed) quote snapshot."""
    price: float
    change: float
    change_percent: float
    volume: int
    timestamp: datetime


# ---------------------------------------------------------------------------
# Provider ABC
# ---------------------------------------------------------------------------

class FinancialDataProvider(ABC):
    """Provides fundamental financial data (income statement, balance sheet, etc.)."""

    @abstractmethod
    def get_financials(self, ticker: str) -> list[FinancialSnapshot]:
        """Return quarterly + annual financial snapshots."""
        ...

    @abstractmethod
    def get_valuation(self, ticker: str) -> ValuationData:
        """Return current valuation metrics."""
        ...


class PriceDataProvider(ABC):
    """Provides historical and current price data."""

    @abstractmethod
    def get_price_history(self, ticker: str, days: int = 730) -> list[PriceBar]:
        """Return daily OHLCV bars for the last N days."""
        ...

    @abstractmethod
    def get_quote(self, ticker: str) -> Optional[StockQuote]:
        """Return the latest quote."""
        ...


class NewsDataProvider(ABC):
    """Provides news articles for a given stock."""

    @abstractmethod
    def get_news(self, ticker: str, company_name: str, days: int = 30) -> list[NewsArticle]:
        """Return recent news articles."""
        ...
