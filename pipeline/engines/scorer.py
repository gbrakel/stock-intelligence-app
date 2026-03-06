"""
Composite scorer.
Combines all individual engine scores into a single composite score,
maps to a signal (strong_buy → exit), and applies exit signal overrides.
"""

from dataclasses import dataclass
from typing import Optional

from pipeline.config import DEFAULT_WEIGHTS, SIGNAL_THRESHOLDS, ScoringWeights
from pipeline.engines.exit_signals import ExitSignalResult
from pipeline.utils.logging import log


@dataclass
class CompositeScore:
    composite_score: float  # Final weighted score 0-100
    signal: str  # strong_buy, buy, hold, reduce, exit_watch, exit
    signal_confidence: float  # 0.0-1.0
    scores: dict[str, float]  # Individual engine scores
    exit_override: Optional[str]  # Original signal before exit override, if changed
    score_delta: Optional[float]  # Change vs previous day


def compute_composite(
    fundamentals_score: float,
    growth_trend_score: float,
    valuation_score: float,
    sentiment_score: float,
    technical_score: float,
    risk_score: float,
    exit_result: ExitSignalResult,
    previous_score: Optional[float] = None,
    weights: ScoringWeights = DEFAULT_WEIGHTS,
) -> CompositeScore:
    """
    Compute the final composite score and signal.

    Formula:
    Final = (W_f × Fund) + (W_g × Growth) + (W_v × Val)
          + (W_s × Sent) + (W_t × Tech) - (W_r × Risk)
    """
    scores = {
        "fundamentals": round(fundamentals_score, 1),
        "growth_trend": round(growth_trend_score, 1),
        "valuation": round(valuation_score, 1),
        "sentiment": round(sentiment_score, 1),
        "technical": round(technical_score, 1),
        "risk_penalty": round(risk_score, 1),
    }

    composite = (
        weights.fundamentals * fundamentals_score
        + weights.growth_trend * growth_trend_score
        + weights.valuation * valuation_score
        + weights.sentiment * sentiment_score
        + weights.technical * technical_score
        - weights.risk_penalty * risk_score
    )

    # Clamp to 0-100
    composite = max(0.0, min(100.0, composite))

    # Map composite score to signal
    signal = _score_to_signal(composite)

    # Apply exit override (can only push signal downward)
    exit_override = None
    if exit_result.signal != "hold":
        signal_rank = _signal_rank(signal)
        exit_rank = _signal_rank(exit_result.signal)
        if exit_rank < signal_rank:
            exit_override = signal
            signal = exit_result.signal

    # Confidence: higher when score is far from threshold boundaries
    confidence = _compute_confidence(composite, signal)

    # Delta vs previous day
    delta = round(composite - previous_score, 1) if previous_score is not None else None

    return CompositeScore(
        composite_score=round(composite, 1),
        signal=signal,
        signal_confidence=round(confidence, 2),
        scores=scores,
        exit_override=exit_override,
        score_delta=delta,
    )


def _score_to_signal(score: float) -> str:
    """Map composite score to signal string."""
    if score >= SIGNAL_THRESHOLDS["strong_buy"]:
        return "strong_buy"
    elif score >= SIGNAL_THRESHOLDS["buy"]:
        return "buy"
    elif score >= SIGNAL_THRESHOLDS["hold"]:
        return "hold"
    elif score >= SIGNAL_THRESHOLDS["reduce"]:
        return "reduce"
    elif score >= SIGNAL_THRESHOLDS["exit_watch"]:
        return "exit_watch"
    else:
        return "exit"


def _signal_rank(signal: str) -> int:
    """Rank signals from most bullish (6) to most bearish (1)."""
    ranks = {
        "strong_buy": 6,
        "buy": 5,
        "hold": 4,
        "reduce": 3,
        "exit_watch": 2,
        "exit": 1,
    }
    return ranks.get(signal, 4)


def _compute_confidence(score: float, signal: str) -> float:
    """
    Compute confidence based on how far the score is from the nearest threshold.
    Higher distance from boundary = higher confidence.
    """
    thresholds = sorted(SIGNAL_THRESHOLDS.values())

    min_distance = 100.0
    for threshold in thresholds:
        dist = abs(score - threshold)
        if dist < min_distance:
            min_distance = dist

    # Also check distance from 0 and 100
    min_distance = min(min_distance, score, 100 - score)

    # Map distance to confidence: 0 distance → 0.5, 15+ distance → 0.95
    confidence = 0.5 + min(min_distance / 30.0, 0.45)
    return confidence
