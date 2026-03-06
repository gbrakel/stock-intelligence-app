"""
Technical / momentum scoring engine.
Scores price-based momentum and trend signals.

Metrics and weights:
- Price vs 50-day SMA (20%)
- Price vs 200-day SMA (20%)
- 50/200 SMA crossover direction (15%)
- RSI zone (15%)
- 3-month price momentum vs S&P 500 (20%)
- Volume trend (10%)
"""

from dataclasses import dataclass
from typing import Optional

import numpy as np

from pipeline.providers.base import PriceBar
from pipeline.utils.logging import log


@dataclass
class TechnicalResult:
    score: float  # 0-100
    components: dict[str, Optional[float]]
    explanation: list[str]
    indicators: dict[str, Optional[float]]  # Raw indicator values (SMA, RSI, etc.)


def score_technical(
    ticker: str,
    prices: list[PriceBar],
    benchmark_prices: list[PriceBar] = None,  # S&P 500 for relative momentum
) -> TechnicalResult:
    """Score technical momentum from price history."""
    if len(prices) < 50:
        return TechnicalResult(
            score=50.0, components={}, explanation=["Insufficient price history"],
            indicators={},
        )

    # Sort chronologically (oldest first)
    prices_sorted = sorted(prices, key=lambda p: p.date)
    closes = np.array([p.close for p in prices_sorted])
    volumes = np.array([p.volume for p in prices_sorted])

    components: dict[str, Optional[float]] = {}
    explanations: list[str] = []
    indicators: dict[str, Optional[float]] = {}

    current_price = closes[-1]

    # --- SMA calculations ---
    sma_50 = float(np.mean(closes[-50:])) if len(closes) >= 50 else None
    sma_200 = float(np.mean(closes[-200:])) if len(closes) >= 200 else None
    indicators["sma_50"] = round(sma_50, 2) if sma_50 else None
    indicators["sma_200"] = round(sma_200, 2) if sma_200 else None
    indicators["current_price"] = round(current_price, 2)

    # --- Price vs 50-day SMA ---
    if sma_50:
        pct_above_50 = (current_price - sma_50) / sma_50
        # Map to 0-1: +10% above → ~0.85, -10% below → ~0.15
        score_50 = max(0.0, min(1.0, 0.5 + pct_above_50 * 5))
        components["price_vs_sma50"] = score_50
        if pct_above_50 > 0.05:
            explanations.append(f"Trading {pct_above_50:.0%} above 50-day SMA")
        elif pct_above_50 < -0.05:
            explanations.append(f"Trading {abs(pct_above_50):.0%} below 50-day SMA")

    # --- Price vs 200-day SMA ---
    if sma_200:
        pct_above_200 = (current_price - sma_200) / sma_200
        score_200 = max(0.0, min(1.0, 0.5 + pct_above_200 * 3))
        components["price_vs_sma200"] = score_200
        if pct_above_200 < -0.10:
            explanations.append(f"Trading {abs(pct_above_200):.0%} below 200-day SMA")

    # --- Golden/Death Cross ---
    if sma_50 and sma_200:
        cross_score = 0.7 if sma_50 > sma_200 else 0.3
        components["sma_crossover"] = cross_score
        if sma_50 > sma_200:
            # Check if this is recent (was it a cross in last 20 days?)
            prev_sma50 = float(np.mean(closes[-70:-20])) if len(closes) >= 70 else None
            prev_sma200 = float(np.mean(closes[-220:-20])) if len(closes) >= 220 else None
            if prev_sma50 and prev_sma200 and prev_sma50 < prev_sma200:
                explanations.append("Recent golden cross (50 SMA crossed above 200 SMA)")
                components["sma_crossover"] = 0.85
        else:
            explanations.append("50-day SMA below 200-day SMA (bearish structure)")

    # --- RSI (14-period) ---
    rsi = _compute_rsi(closes, period=14)
    indicators["rsi_14"] = round(rsi, 1) if rsi else None
    if rsi is not None:
        # RSI 30-70 is neutral (0.5), extremes penalized
        if 40 <= rsi <= 60:
            rsi_score = 0.5
        elif rsi > 70:
            rsi_score = max(0.1, 1.0 - (rsi - 70) / 30)
            explanations.append(f"RSI at {rsi:.0f} (overbought zone)")
        elif rsi < 30:
            rsi_score = min(0.9, rsi / 30)
            explanations.append(f"RSI at {rsi:.0f} (oversold zone)")
        else:
            rsi_score = 0.3 + (rsi - 30) / 40 * 0.4
        components["rsi"] = rsi_score

    # --- 3-month relative momentum vs benchmark ---
    if len(closes) >= 63:  # ~3 months of trading days
        stock_return = (closes[-1] - closes[-63]) / closes[-63]
        indicators["return_3m"] = round(stock_return, 4)

        benchmark_return = 0.0
        if benchmark_prices and len(benchmark_prices) >= 63:
            bench_sorted = sorted(benchmark_prices, key=lambda p: p.date)
            bench_closes = [p.close for p in bench_sorted]
            if len(bench_closes) >= 63:
                benchmark_return = (bench_closes[-1] - bench_closes[-63]) / bench_closes[-63]

        relative_return = stock_return - benchmark_return
        indicators["relative_return_3m"] = round(relative_return, 4)

        # Map relative return to 0-1
        momentum_score = max(0.0, min(1.0, 0.5 + relative_return * 3))
        components["relative_momentum"] = momentum_score

        if relative_return > 0.10:
            explanations.append(f"Outperforming benchmark by {relative_return:.0%} over 3 months")
        elif relative_return < -0.10:
            explanations.append(f"Underperforming benchmark by {abs(relative_return):.0%} over 3 months")

    # --- Volume trend ---
    if len(volumes) >= 20:
        avg_vol_recent = float(np.mean(volumes[-10:]))
        avg_vol_prior = float(np.mean(volumes[-20:-10]))
        if avg_vol_prior > 0:
            vol_change = (avg_vol_recent - avg_vol_prior) / avg_vol_prior
            vol_score = max(0.0, min(1.0, 0.5 + vol_change))
            components["volume_trend"] = vol_score
            if vol_change > 0.5:
                explanations.append("Volume increasing significantly")

    # --- Weighted composite ---
    weights = {
        "price_vs_sma50": 0.20,
        "price_vs_sma200": 0.20,
        "sma_crossover": 0.15,
        "rsi": 0.15,
        "relative_momentum": 0.20,
        "volume_trend": 0.10,
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
        explanations.append("Neutral technical setup")

    return TechnicalResult(
        score=round(score, 1),
        components=components,
        explanation=explanations,
        indicators=indicators,
    )


def _compute_rsi(closes: np.ndarray, period: int = 14) -> Optional[float]:
    """Compute RSI (Relative Strength Index)."""
    if len(closes) < period + 1:
        return None

    deltas = np.diff(closes[-(period + 1):])
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)

    avg_gain = np.mean(gains)
    avg_loss = np.mean(losses)

    if avg_loss == 0:
        return 100.0

    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))
