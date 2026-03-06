"""
Growth trend scoring engine.
Detects whether a company is improving or deteriorating over time
by analyzing quarter-over-quarter and year-over-year trends.

Metrics and weights:
- QoQ revenue growth acceleration (20%)
- YoY revenue growth (20%)
- EPS growth trend (3-quarter direction) (20%)
- Margin expansion (operating + net) (15%)
- FCF growth (15%)
- Earnings surprise (10%) — placeholder, requires analyst estimates
"""

from dataclasses import dataclass
from typing import Optional

from pipeline.providers.base import FinancialSnapshot
from pipeline.utils.logging import log


@dataclass
class GrowthTrendResult:
    score: float  # 0-100
    components: dict[str, Optional[float]]
    explanation: list[str]


def score_growth_trend(
    ticker: str,
    financials: list[FinancialSnapshot],
) -> GrowthTrendResult:
    """Score growth trends from quarterly financial data."""
    quarterly = sorted(
        [f for f in financials if f.period_type == "quarterly"],
        key=lambda x: x.period_end,
        reverse=True,
    )

    if len(quarterly) < 2:
        return GrowthTrendResult(score=50.0, components={}, explanation=["Insufficient quarterly data"])

    explanations: list[str] = []
    components: dict[str, Optional[float]] = {}

    # --- QoQ Revenue Growth Acceleration ---
    qoq_accel = _compute_acceleration([q.revenue for q in quarterly[:4]])
    components["qoq_revenue_acceleration"] = _normalize_growth(qoq_accel)
    if qoq_accel is not None:
        if qoq_accel > 0:
            explanations.append("Revenue growth is accelerating QoQ")
        elif qoq_accel < -0.05:
            explanations.append("Revenue growth is decelerating QoQ")

    # --- YoY Revenue Growth ---
    yoy_rev = _yoy_growth([q.revenue for q in quarterly[:8]])
    components["yoy_revenue_growth"] = _normalize_growth(yoy_rev)
    if yoy_rev is not None:
        if yoy_rev > 0.20:
            explanations.append(f"Strong YoY revenue growth of {yoy_rev:.0%}")
        elif yoy_rev < 0:
            explanations.append(f"YoY revenue declined {yoy_rev:.0%}")

    # --- EPS Trend (direction over last 3 quarters) ---
    eps_values = [q.eps for q in quarterly[:4] if q.eps is not None]
    eps_trend = _compute_trend_direction(eps_values)
    components["eps_trend"] = eps_trend
    if eps_trend is not None:
        if eps_trend > 0.6:
            explanations.append("EPS trending upward over recent quarters")
        elif eps_trend < 0.4:
            explanations.append("EPS trending downward over recent quarters")

    # --- Margin Expansion ---
    op_margins = [q.operating_margin for q in quarterly[:4] if q.operating_margin is not None]
    net_margins = [q.net_margin for q in quarterly[:4] if q.net_margin is not None]

    margin_trend = _compute_margin_trend(op_margins, net_margins)
    components["margin_expansion"] = margin_trend
    if margin_trend is not None:
        if margin_trend > 0.6:
            explanations.append("Margins expanding")
        elif margin_trend < 0.4:
            explanations.append("Margins compressing")

    # --- FCF Growth ---
    fcf_values = [q.free_cash_flow for q in quarterly[:4] if q.free_cash_flow is not None]
    fcf_trend = _compute_trend_direction(fcf_values)
    components["fcf_growth"] = fcf_trend
    if fcf_trend is not None and fcf_trend > 0.6:
        explanations.append("Free cash flow improving")

    # --- Earnings Surprise (placeholder) ---
    # This would require analyst consensus estimates from a paid source
    components["earnings_surprise"] = 0.5  # Neutral default

    # --- Weighted composite ---
    weights = {
        "qoq_revenue_acceleration": 0.20,
        "yoy_revenue_growth": 0.20,
        "eps_trend": 0.20,
        "margin_expansion": 0.15,
        "fcf_growth": 0.15,
        "earnings_surprise": 0.10,
    }

    total_weight = 0.0
    weighted_sum = 0.0
    for metric, weight in weights.items():
        val = components.get(metric)
        if val is not None:
            weighted_sum += val * weight
            total_weight += weight

    score = (weighted_sum / total_weight * 100) if total_weight > 0 else 50.0
    score = max(0.0, min(100.0, score))

    if not explanations:
        explanations.append("Stable growth trends")

    return GrowthTrendResult(
        score=round(score, 1),
        components=components,
        explanation=explanations,
    )


def _compute_acceleration(values: list[Optional[float]]) -> Optional[float]:
    """
    Compute growth acceleration from a list of values (most recent first).
    Returns the change in growth rate between the two most recent periods.
    """
    clean = [v for v in values if v is not None and v != 0]
    if len(clean) < 3:
        return None

    # Growth rates
    growth_recent = (clean[0] - clean[1]) / abs(clean[1])
    growth_prior = (clean[1] - clean[2]) / abs(clean[2])

    return growth_recent - growth_prior


def _yoy_growth(values: list[Optional[float]]) -> Optional[float]:
    """
    Compute year-over-year growth.
    Expects 8 quarters (most recent first): compares Q0 vs Q4.
    """
    clean = [v for v in values if v is not None]
    if len(clean) < 5:
        return None

    current = clean[0]
    year_ago = clean[4] if len(clean) > 4 else clean[-1]

    if year_ago == 0:
        return None
    return (current - year_ago) / abs(year_ago)


def _compute_trend_direction(values: list[float]) -> Optional[float]:
    """
    Score the direction of a series (most recent first).
    Returns 0.0 (consistently declining) to 1.0 (consistently improving).
    Values are reversed to chronological order for analysis.
    """
    if len(values) < 2:
        return None

    # Reverse to chronological
    chronological = list(reversed(values))
    ups = sum(1 for i in range(1, len(chronological)) if chronological[i] > chronological[i - 1])
    total = len(chronological) - 1

    return ups / total if total > 0 else 0.5


def _compute_margin_trend(op_margins: list[float], net_margins: list[float]) -> Optional[float]:
    """Combined margin trend from operating and net margins."""
    scores = []
    if len(op_margins) >= 2:
        scores.append(_compute_trend_direction(op_margins))
    if len(net_margins) >= 2:
        scores.append(_compute_trend_direction(net_margins))

    valid = [s for s in scores if s is not None]
    if not valid:
        return None
    return sum(valid) / len(valid)


def _normalize_growth(value: Optional[float]) -> Optional[float]:
    """Normalize a growth rate to 0.0-1.0 scale using sigmoid-like mapping."""
    if value is None:
        return None
    # Sigmoid mapping: 0% → 0.5, +50% → ~0.85, -50% → ~0.15
    import math
    return 1.0 / (1.0 + math.exp(-5 * value))
