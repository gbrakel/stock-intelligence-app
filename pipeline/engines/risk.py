"""
Risk scoring engine.
Assigns a risk profile (Low / Medium / High / Very High) to each stock.

Factors and weights:
- Volatility (15%) — annualized 30-day std dev
- Debt burden (15%) — D/E ratio percentile
- Earnings inconsistency (15%) — coefficient of variation of EPS
- Cash burn (10%) — negative FCF quarters / total
- Sector risk (10%) — sector average drawdown
- Sentiment stability (10%) — std dev of sentiment scores
- Liquidity (10%) — inverse of avg daily dollar volume
- Drawdown (10%) — max peak-to-trough in 12 months
- Concentration (5%) — sector default (data rarely available)
"""

from dataclasses import dataclass
from typing import Optional

import numpy as np

from pipeline.providers.base import FinancialSnapshot, NewsArticle, PriceBar
from pipeline.utils.logging import log

# Sector default risk scores (based on typical sector volatility)
SECTOR_RISK_DEFAULTS = {
    "Technology": 55,
    "Healthcare": 50,
    "Financials": 50,
    "Consumer Staples": 25,
    "Consumer Discretionary": 45,
    "Energy": 60,
    "Industrials": 40,
    "Communication": 45,
    "Utilities": 20,
    "Real Estate": 35,
    "Materials": 45,
}


@dataclass
class RiskResult:
    overall_score: float  # 0-100 (higher = riskier)
    risk_level: str  # "low", "medium", "high", "very_high"
    factors: dict[str, float]  # Individual factor scores
    risk_flags: list[str]  # Human-readable risk warnings


def score_risk(
    ticker: str,
    prices: list[PriceBar],
    financials: list[FinancialSnapshot],
    articles: list[NewsArticle],
    sector: str,
    peer_data: dict[str, list[float]] = None,
) -> RiskResult:
    """Compute overall risk score for a stock."""
    factors: dict[str, float] = {}
    flags: list[str] = []

    if peer_data is None:
        peer_data = {}

    # --- Volatility ---
    vol_score = _score_volatility(prices)
    factors["volatility"] = vol_score
    if vol_score > 70:
        flags.append(f"High volatility (annualized)")

    # --- Debt burden ---
    debt_score = _score_debt(financials, peer_data.get("debt_to_equity", []))
    factors["debt_burden"] = debt_score
    if debt_score > 70:
        flags.append("Elevated debt-to-equity ratio")

    # --- Earnings inconsistency ---
    earnings_score = _score_earnings_consistency(financials)
    factors["earnings_consistency"] = earnings_score
    if earnings_score > 70:
        flags.append("Inconsistent earnings across recent quarters")

    # --- Cash burn ---
    burn_score = _score_cash_burn(financials)
    factors["cash_burn"] = burn_score
    if burn_score > 60:
        flags.append("Frequent negative free cash flow")

    # --- Sector risk ---
    sector_score = float(SECTOR_RISK_DEFAULTS.get(sector, 45))
    factors["sector_risk"] = sector_score

    # --- Sentiment stability ---
    sent_score = _score_sentiment_stability(articles)
    factors["sentiment_stability"] = sent_score
    if sent_score > 70:
        flags.append("Highly volatile news sentiment")

    # --- Liquidity ---
    liq_score = _score_liquidity(prices, peer_data.get("avg_volume", []))
    factors["liquidity"] = liq_score
    if liq_score > 70:
        flags.append("Low relative trading volume")

    # --- Max drawdown ---
    dd_score = _score_drawdown(prices)
    factors["drawdown"] = dd_score
    if dd_score > 70:
        flags.append(f"Significant drawdown in last 12 months")

    # --- Concentration (default) ---
    factors["concentration"] = 40.0  # Default — would need revenue breakdown data

    # --- Weighted composite ---
    weights = {
        "volatility": 0.15,
        "debt_burden": 0.15,
        "earnings_consistency": 0.15,
        "cash_burn": 0.10,
        "sector_risk": 0.10,
        "sentiment_stability": 0.10,
        "liquidity": 0.10,
        "drawdown": 0.10,
        "concentration": 0.05,
    }

    overall = sum(factors.get(k, 50) * w for k, w in weights.items())
    overall = max(0.0, min(100.0, overall))

    # Map to risk level
    if overall <= 25:
        level = "low"
    elif overall <= 50:
        level = "medium"
    elif overall <= 75:
        level = "high"
    else:
        level = "very_high"

    return RiskResult(
        overall_score=round(overall, 1),
        risk_level=level,
        factors={k: round(v, 1) for k, v in factors.items()},
        risk_flags=flags,
    )


def _score_volatility(prices: list[PriceBar]) -> float:
    """Annualized 30-day volatility → 0-100 risk score."""
    if len(prices) < 30:
        return 50.0

    sorted_prices = sorted(prices, key=lambda p: p.date)
    closes = np.array([p.close for p in sorted_prices[-31:]])
    if len(closes) < 2:
        return 50.0

    returns = np.diff(closes) / closes[:-1]
    daily_vol = float(np.std(returns))
    annual_vol = daily_vol * np.sqrt(252)

    # Map: 0% vol → 0, 20% → 33, 40% → 66, 60%+ → 100
    return min(100.0, annual_vol * 166.0)


def _score_debt(financials: list[FinancialSnapshot], peer_de: list[float]) -> float:
    """Debt-to-equity ratio → risk score."""
    quarterly = sorted(
        [f for f in financials if f.period_type == "quarterly"],
        key=lambda x: x.period_end, reverse=True,
    )
    if not quarterly:
        return 50.0

    latest = quarterly[0]
    if latest.total_debt is None or latest.total_equity is None or latest.total_equity <= 0:
        return 50.0

    de = latest.total_debt / latest.total_equity

    # Higher D/E = higher risk
    if de < 0.3:
        return 15.0
    elif de < 0.7:
        return 30.0
    elif de < 1.5:
        return 50.0
    elif de < 3.0:
        return 75.0
    else:
        return 90.0


def _score_earnings_consistency(financials: list[FinancialSnapshot]) -> float:
    """Coefficient of variation of EPS over recent quarters → risk score."""
    quarterly = sorted(
        [f for f in financials if f.period_type == "quarterly"],
        key=lambda x: x.period_end, reverse=True,
    )
    eps_values = [q.eps for q in quarterly[:8] if q.eps is not None]
    if len(eps_values) < 3:
        return 50.0

    arr = np.array(eps_values)
    mean_eps = float(np.mean(arr))
    if abs(mean_eps) < 0.01:
        return 70.0  # Near-zero earnings = risky

    cv = float(np.std(arr) / abs(mean_eps))
    # Map CV to risk: 0 → low risk, 1+ → high risk
    return min(100.0, cv * 60.0)


def _score_cash_burn(financials: list[FinancialSnapshot]) -> float:
    """Proportion of negative FCF quarters → risk score."""
    quarterly = [f for f in financials if f.period_type == "quarterly" and f.free_cash_flow is not None]
    if not quarterly:
        return 50.0

    negative_count = sum(1 for q in quarterly if q.free_cash_flow < 0)
    ratio = negative_count / len(quarterly)
    return min(100.0, ratio * 120.0)


def _score_sentiment_stability(articles: list[NewsArticle]) -> float:
    """Std dev of sentiment scores → risk (more volatile = riskier)."""
    scores = [a.sentiment_score for a in articles if a.sentiment_score is not None]
    if len(scores) < 3:
        return 40.0

    std = float(np.std(scores))
    # Map: 0 std → 0 risk, 0.8 std → 80 risk
    return min(100.0, std * 100.0)


def _score_liquidity(prices: list[PriceBar], peer_volumes: list[float]) -> float:
    """Low volume relative to peers → higher risk."""
    if len(prices) < 20:
        return 50.0

    sorted_prices = sorted(prices, key=lambda p: p.date)
    recent_vols = [p.volume for p in sorted_prices[-20:]]
    avg_vol = float(np.mean(recent_vols))

    if not peer_volumes:
        # Absolute scale: <1M avg vol = risky for large-caps
        if avg_vol > 10_000_000:
            return 10.0
        elif avg_vol > 2_000_000:
            return 25.0
        elif avg_vol > 500_000:
            return 50.0
        else:
            return 75.0

    # Percentile among peers (lower = riskier)
    rank = sum(1 for v in peer_volumes if v <= avg_vol)
    pctile = rank / (len(peer_volumes) + 1)
    return max(0.0, (1 - pctile) * 100)


def _score_drawdown(prices: list[PriceBar]) -> float:
    """Max drawdown in last 12 months → risk score."""
    sorted_prices = sorted(prices, key=lambda p: p.date)
    # Last ~252 trading days
    recent = sorted_prices[-252:]
    if len(recent) < 20:
        return 50.0

    closes = np.array([p.close for p in recent])
    peak = np.maximum.accumulate(closes)
    drawdowns = (closes - peak) / peak
    max_dd = float(np.min(drawdowns))  # Most negative value

    # Map: 0% dd → 0 risk, -20% → 50, -40% → 80, -60%+ → 100
    return min(100.0, abs(max_dd) * 200.0)
