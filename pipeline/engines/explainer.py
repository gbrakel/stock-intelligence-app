"""
Explainer engine.
Generates plain-language explanations for each stock's recommendation.
Combines insights from all scoring engines into a structured explanation.
"""

from dataclasses import dataclass

from pipeline.engines.scorer import CompositeScore
from pipeline.engines.fundamentals import FundamentalsResult
from pipeline.engines.growth_trend import GrowthTrendResult
from pipeline.engines.valuation import ValuationResult
from pipeline.engines.sentiment import SentimentResult
from pipeline.engines.technical import TechnicalResult
from pipeline.engines.risk import RiskResult
from pipeline.engines.exit_signals import ExitSignalResult


@dataclass
class Explanation:
    top_reasons: list[str]
    risks: list[str]
    changes: list[str]  # What changed vs yesterday
    exit_warnings: list[str]
    summary: str


def generate_explanation(
    ticker: str,
    composite: CompositeScore,
    fundamentals: FundamentalsResult,
    growth: GrowthTrendResult,
    valuation: ValuationResult,
    sentiment: SentimentResult,
    technical: TechnicalResult,
    risk: RiskResult,
    exit_result: ExitSignalResult,
    previous_signal: str = None,
) -> Explanation:
    """Generate a structured explanation for a stock's recommendation."""

    # --- Top reasons (from highest-scoring engines) ---
    top_reasons: list[str] = []

    # Collect all engine explanations with their scores
    engine_explanations = [
        (composite.scores.get("fundamentals", 50), "Fundamentals", fundamentals.explanation),
        (composite.scores.get("growth_trend", 50), "Growth", growth.explanation),
        (composite.scores.get("valuation", 50), "Valuation", valuation.explanation),
        (composite.scores.get("sentiment", 50), "Sentiment", sentiment.explanation),
        (composite.scores.get("technical", 50), "Technical", technical.explanation),
    ]

    # Sort by score (highest first) and take top contributing factors
    engine_explanations.sort(key=lambda x: x[0], reverse=True)

    for score, category, explanations in engine_explanations:
        if score >= 60 and explanations:
            # This engine contributed positively
            top_reasons.append(f"[{category}] {explanations[0]}")
            if len(top_reasons) >= 3:
                break

    if not top_reasons:
        top_reasons.append("Average performance across all dimensions")

    # --- Risks ---
    risks = risk.risk_flags.copy()
    # Add low-scoring engine concerns
    for score, category, explanations in engine_explanations:
        if score < 40 and explanations:
            risks.append(f"[{category}] {explanations[0]}")

    if not risks:
        risks.append("No significant risk flags detected")

    # --- Changes vs yesterday ---
    changes: list[str] = []
    if composite.score_delta is not None:
        direction = "improved" if composite.score_delta > 0 else "declined"
        changes.append(f"Composite score {direction} by {abs(composite.score_delta):.1f} points")

    if previous_signal and previous_signal != composite.signal:
        changes.append(f"Signal changed from {_format_signal(previous_signal)} to {_format_signal(composite.signal)}")

    if composite.exit_override:
        changes.append(f"Signal overridden from {_format_signal(composite.exit_override)} due to exit triggers")

    if not changes:
        changes.append("No significant changes from previous day")

    # --- Exit warnings ---
    exit_warnings = exit_result.explanation if exit_result.signal != "hold" else []

    # --- Summary sentence ---
    summary = _generate_summary(ticker, composite, risk)

    return Explanation(
        top_reasons=top_reasons,
        risks=risks,
        changes=changes,
        exit_warnings=exit_warnings,
        summary=summary,
    )


def _generate_summary(ticker: str, composite: CompositeScore, risk: RiskResult) -> str:
    """Generate a one-line summary."""
    signal_label = _format_signal(composite.signal)
    risk_label = risk.risk_level.replace("_", " ").title()

    if composite.signal in ("strong_buy", "buy"):
        return (
            f"{ticker} scores {composite.composite_score:.0f}/100 with a {signal_label} signal. "
            f"Risk level: {risk_label}. "
            f"Confidence: {composite.signal_confidence:.0%}."
        )
    elif composite.signal == "hold":
        return (
            f"{ticker} scores {composite.composite_score:.0f}/100 — currently a Hold. "
            f"Risk level: {risk_label}."
        )
    else:
        return (
            f"{ticker} scores {composite.composite_score:.0f}/100 with a {signal_label} signal. "
            f"Risk level: {risk_label}. Review position carefully."
        )


def _format_signal(signal: str) -> str:
    """Format signal for display."""
    return signal.replace("_", " ").title()
