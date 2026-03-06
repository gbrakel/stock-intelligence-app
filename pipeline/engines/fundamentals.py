"""
Fundamentals scoring engine.
Scores a stock 0-100 based on financial health metrics,
ranked relative to sector peers (percentile-based).

Metrics and weights:
- ROE (15%) — higher = better
- Net margin (15%) — higher = better
- FCF yield (15%) — positive & growing = strong
- Debt-to-equity (15%) — lower = better (inverted)
- Revenue stability (10%) — larger, more stable = better
- Cash/debt ratio (10%) — higher = better
- ROA (10%) — higher = better
- Operating margin (10%) — higher = better
"""

from dataclasses import dataclass
from typing import Optional

import numpy as np

from pipeline.providers.base import FinancialSnapshot, ValuationData
from pipeline.utils.logging import log


@dataclass
class FundamentalsResult:
    score: float  # 0-100
    components: dict[str, Optional[float]]  # Individual metric scores
    explanation: list[str]  # Human-readable reasons


def score_fundamentals(
    ticker: str,
    financials: list[FinancialSnapshot],
    valuation: ValuationData,
    sector_data: dict[str, list[float]],  # metric_name -> list of peer values
) -> FundamentalsResult:
    """
    Compute fundamentals score for a single stock.

    `sector_data` maps metric names to lists of values from sector peers,
    used to compute percentile ranks.
    """
    # Use most recent quarterly data
    quarterly = [f for f in financials if f.period_type == "quarterly"]
    quarterly.sort(key=lambda x: x.period_end, reverse=True)

    if not quarterly:
        return FundamentalsResult(score=50.0, components={}, explanation=["No financial data available"])

    latest = quarterly[0]
    explanations: list[str] = []
    components: dict[str, Optional[float]] = {}

    # --- ROE ---
    roe_score = _percentile_score(latest.roe, sector_data.get("roe", []))
    components["roe"] = roe_score
    if latest.roe is not None:
        if latest.roe > 0.20:
            explanations.append(f"Strong ROE of {latest.roe:.1%}")
        elif latest.roe < 0:
            explanations.append(f"Negative ROE of {latest.roe:.1%}")

    # --- Net margin ---
    net_margin_score = _percentile_score(latest.net_margin, sector_data.get("net_margin", []))
    components["net_margin"] = net_margin_score
    if latest.net_margin is not None and latest.net_margin > 0.15:
        explanations.append(f"Healthy net margin of {latest.net_margin:.1%}")

    # --- FCF yield ---
    fcf_yield = None
    if latest.free_cash_flow is not None and valuation.market_cap and valuation.market_cap > 0:
        fcf_yield = latest.free_cash_flow / valuation.market_cap
    fcf_score = _percentile_score(fcf_yield, sector_data.get("fcf_yield", []))
    components["fcf_yield"] = fcf_score
    if fcf_yield is not None and fcf_yield > 0.05:
        explanations.append(f"Strong FCF yield of {fcf_yield:.1%}")
    elif latest.free_cash_flow is not None and latest.free_cash_flow < 0:
        explanations.append("Negative free cash flow")

    # --- Debt-to-equity (inverted: lower = better) ---
    de_ratio = None
    if latest.total_debt is not None and latest.total_equity and latest.total_equity > 0:
        de_ratio = latest.total_debt / latest.total_equity
    de_score = _percentile_score_inverted(de_ratio, sector_data.get("debt_to_equity", []))
    components["debt_to_equity"] = de_score
    if de_ratio is not None and de_ratio > 2.0:
        explanations.append(f"High debt-to-equity ratio of {de_ratio:.2f}")
    elif de_ratio is not None and de_ratio < 0.5:
        explanations.append(f"Low debt-to-equity ratio of {de_ratio:.2f}")

    # --- Revenue stability (use most recent revenue magnitude) ---
    rev_score = _percentile_score(latest.revenue, sector_data.get("revenue", []))
    components["revenue"] = rev_score

    # --- Cash/debt ratio ---
    cash_debt = None
    if latest.cash_and_equivalents is not None and latest.total_debt and latest.total_debt > 0:
        cash_debt = latest.cash_and_equivalents / latest.total_debt
    cash_score = _percentile_score(cash_debt, sector_data.get("cash_debt_ratio", []))
    components["cash_debt_ratio"] = cash_score
    if cash_debt is not None and cash_debt > 1.0:
        explanations.append("Cash exceeds total debt")

    # --- ROA ---
    roa_score = _percentile_score(latest.roa, sector_data.get("roa", []))
    components["roa"] = roa_score

    # --- Operating margin ---
    op_margin_score = _percentile_score(latest.operating_margin, sector_data.get("operating_margin", []))
    components["operating_margin"] = op_margin_score
    if latest.operating_margin is not None and latest.operating_margin > 0.20:
        explanations.append(f"Strong operating margin of {latest.operating_margin:.1%}")

    # --- Weighted composite ---
    weights = {
        "roe": 0.15,
        "net_margin": 0.15,
        "fcf_yield": 0.15,
        "debt_to_equity": 0.15,
        "revenue": 0.10,
        "cash_debt_ratio": 0.10,
        "roa": 0.10,
        "operating_margin": 0.10,
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
        explanations.append("Average fundamental metrics")

    return FundamentalsResult(
        score=round(score, 1),
        components=components,
        explanation=explanations,
    )


def _percentile_score(value: Optional[float], peers: list[float]) -> Optional[float]:
    """Compute percentile rank of value among peers (0.0 to 1.0). Higher = better."""
    if value is None:
        return None
    if not peers:
        # No peer data — normalize to 0.5 (neutral)
        return 0.5

    all_vals = peers + [value]
    all_vals = [v for v in all_vals if v is not None]
    if len(all_vals) < 2:
        return 0.5

    rank = sum(1 for v in all_vals if v <= value)
    return rank / len(all_vals)


def _percentile_score_inverted(value: Optional[float], peers: list[float]) -> Optional[float]:
    """Inverted percentile: lower value = higher score."""
    if value is None:
        return None
    if not peers:
        return 0.5

    all_vals = peers + [value]
    all_vals = [v for v in all_vals if v is not None]
    if len(all_vals) < 2:
        return 0.5

    rank = sum(1 for v in all_vals if v >= value)
    return rank / len(all_vals)
