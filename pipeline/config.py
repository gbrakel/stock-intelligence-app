"""
Pipeline configuration: stock universe, scoring weights, API settings.
All values can be overridden via environment variables.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
PIPELINE_DIR = PROJECT_ROOT / "pipeline"

# ---------------------------------------------------------------------------
# API Keys
# ---------------------------------------------------------------------------
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY", "")
SEC_EDGAR_USER_AGENT = os.getenv("SEC_EDGAR_USER_AGENT", "StockIntel admin@example.com")
FMP_API_KEY = os.getenv("FMP_API_KEY", "")

# ---------------------------------------------------------------------------
# Stock Universe — curated US large-cap tickers for MVP
# ---------------------------------------------------------------------------
STOCK_UNIVERSE: list[dict] = [
    # Technology
    {"ticker": "AAPL", "name": "Apple Inc.", "sector": "Technology", "industry": "Consumer Electronics"},
    {"ticker": "MSFT", "name": "Microsoft Corp.", "sector": "Technology", "industry": "Software"},
    {"ticker": "NVDA", "name": "NVIDIA Corp.", "sector": "Technology", "industry": "Semiconductors"},
    {"ticker": "GOOGL", "name": "Alphabet Inc.", "sector": "Technology", "industry": "Internet Services"},
    {"ticker": "META", "name": "Meta Platforms Inc.", "sector": "Technology", "industry": "Social Media"},
    {"ticker": "AMZN", "name": "Amazon.com Inc.", "sector": "Technology", "industry": "E-Commerce"},
    {"ticker": "TSLA", "name": "Tesla Inc.", "sector": "Technology", "industry": "Electric Vehicles"},
    {"ticker": "AMD", "name": "Advanced Micro Devices", "sector": "Technology", "industry": "Semiconductors"},
    {"ticker": "CRM", "name": "Salesforce Inc.", "sector": "Technology", "industry": "Software"},
    {"ticker": "ORCL", "name": "Oracle Corp.", "sector": "Technology", "industry": "Software"},
    {"ticker": "ADBE", "name": "Adobe Inc.", "sector": "Technology", "industry": "Software"},
    {"ticker": "INTC", "name": "Intel Corp.", "sector": "Technology", "industry": "Semiconductors"},
    {"ticker": "AVGO", "name": "Broadcom Inc.", "sector": "Technology", "industry": "Semiconductors"},
    {"ticker": "CSCO", "name": "Cisco Systems", "sector": "Technology", "industry": "Networking"},
    {"ticker": "NOW", "name": "ServiceNow Inc.", "sector": "Technology", "industry": "Software"},

    # Healthcare
    {"ticker": "UNH", "name": "UnitedHealth Group", "sector": "Healthcare", "industry": "Health Insurance"},
    {"ticker": "JNJ", "name": "Johnson & Johnson", "sector": "Healthcare", "industry": "Pharmaceuticals"},
    {"ticker": "LLY", "name": "Eli Lilly & Co.", "sector": "Healthcare", "industry": "Pharmaceuticals"},
    {"ticker": "PFE", "name": "Pfizer Inc.", "sector": "Healthcare", "industry": "Pharmaceuticals"},
    {"ticker": "ABBV", "name": "AbbVie Inc.", "sector": "Healthcare", "industry": "Pharmaceuticals"},
    {"ticker": "MRK", "name": "Merck & Co.", "sector": "Healthcare", "industry": "Pharmaceuticals"},
    {"ticker": "TMO", "name": "Thermo Fisher Scientific", "sector": "Healthcare", "industry": "Life Sciences"},

    # Financials
    {"ticker": "JPM", "name": "JPMorgan Chase & Co.", "sector": "Financials", "industry": "Banking"},
    {"ticker": "V", "name": "Visa Inc.", "sector": "Financials", "industry": "Payments"},
    {"ticker": "MA", "name": "Mastercard Inc.", "sector": "Financials", "industry": "Payments"},
    {"ticker": "BAC", "name": "Bank of America", "sector": "Financials", "industry": "Banking"},
    {"ticker": "GS", "name": "Goldman Sachs", "sector": "Financials", "industry": "Investment Banking"},
    {"ticker": "BLK", "name": "BlackRock Inc.", "sector": "Financials", "industry": "Asset Management"},

    # Consumer
    {"ticker": "WMT", "name": "Walmart Inc.", "sector": "Consumer Staples", "industry": "Retail"},
    {"ticker": "PG", "name": "Procter & Gamble", "sector": "Consumer Staples", "industry": "Consumer Goods"},
    {"ticker": "KO", "name": "Coca-Cola Co.", "sector": "Consumer Staples", "industry": "Beverages"},
    {"ticker": "PEP", "name": "PepsiCo Inc.", "sector": "Consumer Staples", "industry": "Beverages"},
    {"ticker": "COST", "name": "Costco Wholesale", "sector": "Consumer Staples", "industry": "Retail"},
    {"ticker": "MCD", "name": "McDonald's Corp.", "sector": "Consumer Discretionary", "industry": "Restaurants"},
    {"ticker": "NKE", "name": "Nike Inc.", "sector": "Consumer Discretionary", "industry": "Apparel"},
    {"ticker": "HD", "name": "Home Depot", "sector": "Consumer Discretionary", "industry": "Home Improvement"},

    # Energy
    {"ticker": "XOM", "name": "Exxon Mobil Corp.", "sector": "Energy", "industry": "Oil & Gas"},
    {"ticker": "CVX", "name": "Chevron Corp.", "sector": "Energy", "industry": "Oil & Gas"},

    # Industrials
    {"ticker": "CAT", "name": "Caterpillar Inc.", "sector": "Industrials", "industry": "Machinery"},
    {"ticker": "BA", "name": "Boeing Co.", "sector": "Industrials", "industry": "Aerospace"},
    {"ticker": "UNP", "name": "Union Pacific Corp.", "sector": "Industrials", "industry": "Railroads"},
    {"ticker": "HON", "name": "Honeywell International", "sector": "Industrials", "industry": "Conglomerate"},
    {"ticker": "GE", "name": "GE Aerospace", "sector": "Industrials", "industry": "Aerospace"},

    # Communication / Media
    {"ticker": "DIS", "name": "Walt Disney Co.", "sector": "Communication", "industry": "Entertainment"},
    {"ticker": "NFLX", "name": "Netflix Inc.", "sector": "Communication", "industry": "Streaming"},
    {"ticker": "CMCSA", "name": "Comcast Corp.", "sector": "Communication", "industry": "Telecom"},

    # Real Estate / Utilities
    {"ticker": "NEE", "name": "NextEra Energy", "sector": "Utilities", "industry": "Renewable Energy"},
    {"ticker": "AMT", "name": "American Tower Corp.", "sector": "Real Estate", "industry": "REITs"},

    # Materials
    {"ticker": "LIN", "name": "Linde plc", "sector": "Materials", "industry": "Industrial Gases"},
    {"ticker": "APD", "name": "Air Products & Chemicals", "sector": "Materials", "industry": "Chemicals"},
]

# ---------------------------------------------------------------------------
# Scoring Weights — configurable composite formula
# ---------------------------------------------------------------------------
@dataclass
class ScoringWeights:
    fundamentals: float = 0.30
    growth_trend: float = 0.25
    valuation: float = 0.10
    sentiment: float = 0.20
    technical: float = 0.10
    risk_penalty: float = 0.15

DEFAULT_WEIGHTS = ScoringWeights()

# ---------------------------------------------------------------------------
# Signal Thresholds — composite score → signal mapping
# ---------------------------------------------------------------------------
SIGNAL_THRESHOLDS = {
    "strong_buy": 80,
    "buy": 65,
    "hold": 45,
    "reduce": 30,
    "exit_watch": 15,
    # Below 15 → exit
}

# ---------------------------------------------------------------------------
# Pipeline Settings
# ---------------------------------------------------------------------------
PRICE_HISTORY_DAYS = 730       # ~2 years of daily prices
NEWS_LOOKBACK_DAYS = 30        # Collect news from last 30 days
MAX_NEWS_PER_STOCK = 50        # Cap news articles stored per stock
FINNHUB_RATE_LIMIT_PER_MIN = 55  # Stay under 60 req/min limit
YAHOO_REQUEST_DELAY_SEC = 1.5    # Delay between yfinance calls
