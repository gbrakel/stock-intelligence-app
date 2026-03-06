"""
Valuation scoring engine.
Scores how attractively a stock is valued relative to its sector.
Lower valuation = higher score (value-oriented).

Metrics and weights:
- P/E vs sector median (25%)
- Forward P/E vs sector (25%)
- PEG ratio (20%)
- EV/EBITDA vs sector (15%)
- Price-to-Sales vs sector (15%)

All metrics are inverted: cheaper = higher score.
"""

from dataclasses import dataclass
from typing import Optional

from pipeline.providers.base import ValuationData
from pipeline.utils.logging import log


@dataclass
class ValuationResult:
    score: float  # 0-100
    components: dict[str, Optional[float]]
    explanation: list[str]


def score_valuation(
    ticker: str,
    valuation: ValuationData,
    sector_valuations: dict[str, list[float]],  # metric_name -> peer values
) -> ValuationResult:
    """Score valuation attractiveness relative to sector peers."""
    components: dict[str, Optional[float]] = {}
    explanations: list[str] = []

    # --- P/E ratio (inverted) ---
    pe_score = _inverted_percentile(valuation.pe_ratio, sector_valuations.get("pe_ratio", []))
    components["pe_ratio"] = pe_score
    if valuation.pe_ratio is not None:
        if valuation.pe_ratio < 15:
            explanations.append(f"Low P/E of {valuation.pe_ratio:.1f}")
        elif valuation.pe_ratio > 40:
            explanations.append(f"High P/E of {valuation.pe_ratio:.1f}")

    # --- Forward P/E (inverted) ---
    fwd_pe_score = _inverted_percentile(valuation.forward_pe, sector_valuations.get("forward_pe", []))
    components["forward_pe"] = fwd_pe_score
    if valuation.forward_pe is not None and valuation.pe_ratio is not None:
        if valuation.forward_pe < valuation.pe_ratio * 0.85:
            explanations.append("Forward P/E suggests improving earnings outlook")

    # --- PEG ratio (inverted, <1 is attractive) ---
    peg_score = _inverted_percentile(valuation.peg_ratio, sector_valuations.get("peg_ratio", []))
    components["peg_ratio"] = peg_score
    if valuation.peg_ratio is not None:
        if valuation.peg_ratio < 1.0:
            explanations.append(f"Attractive PEG ratio of {valuation.peg_ratio:.2f}")
        elif valuation.peg_ratio > 2.5:
            explanations.append(f"High PEG ratio of {valuation.peg_ratio:.2f}")

    # --- EV/EBITDA (inverted) ---
    ev_score = _inverted_percentile(valuation.ev_ebitda, sector_valuations.get("ev_ebitda", []))
    components["ev_ebitda"] = ev_score

    # --- Price-to-Sales (inverted) ---
    ps_score = _inverted_percentile(valuation.price_to_sales, sector_valuations.get("price_to_sales", []))
    components["price_to_sales"] = ps_score

    # --- Weighted composite ---
    weights = {
        "pe_ratio": 0.25,
        "forward_pe": 0.25,
        "peg_ratio": 0.20,
        "ev_ebitda": 0.15,
        "price_to_sales": 0.15,
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
        explanations.append("Average valuation relative to sector")

    return ValuationResult(
        score=round(score, 1),
        components=components,
        explanation=explanations,
    )


def _inverted_percentile(value: Optional[float], peers: list[float]) -> Optional[float]:
    """
    Compute inverted percentile: lower value = higher score.
    Used for valuation metrics where cheap = good.
    Returns 0.0-1.0.
    """
    if value is None or value <= 0:
        return None
    if not peers:
        return 0.5

    valid_peers = [p for p in peers if p is not None and p > 0]
    if not valid_peers:
        return 0.5

    all_vals = valid_peers + [value]
    rank = sum(1 for v in all_vals if v >= value)
    return rank / len(all_vals)
