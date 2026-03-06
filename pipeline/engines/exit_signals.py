"""
Exit signal engine.
Detects warning patterns and can override scoring signals downward (never upward).

Trigger rules (each scored 0-1 severity):
1. Earnings deterioration — 2+ quarters declining EPS
2. Revenue deceleration — 2+ quarters slowing YoY growth
3. Margin compression — 3+ quarters declining operating margin
4. Guidance cut — detected via news keywords
5. Debt stress — D/E increased >20% in 2 quarters
6. Sentiment collapse — 7-day avg sentiment very negative
7. Negative news cluster — 3+ negative articles in 48 hours
8. Price breakdown — below 200 SMA and declining
9. Abnormal volatility — 30-day vol > 2x 90-day vol
10. Peer underperformance — underperforms sector by >15% over 3 months
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

import numpy as np

from pipeline.providers.base import FinancialSnapshot, NewsArticle, PriceBar
from pipeline.utils.logging import log


@dataclass
class ExitTrigger:
    name: str
    severity: float  # 0.0 - 1.0
    description: str


@dataclass
class ExitSignalResult:
    signal: str  # "hold", "reduce", "exit_watch", "exit"
    triggers: list[ExitTrigger]
    avg_severity: float
    explanation: list[str]


def evaluate_exit_signals(
    ticker: str,
    financials: list[FinancialSnapshot],
    prices: list[PriceBar],
    articles: list[NewsArticle],
    sector_return_3m: float = 0.0,
) -> ExitSignalResult:
    """Run all exit signal triggers and compute override signal."""
    triggers: list[ExitTrigger] = []

    quarterly = sorted(
        [f for f in financials if f.period_type == "quarterly"],
        key=lambda x: x.period_end, reverse=True,
    )

    # --- 1. Earnings deterioration ---
    eps_vals = [q.eps for q in quarterly[:4] if q.eps is not None]
    if len(eps_vals) >= 3:
        declines = sum(1 for i in range(len(eps_vals) - 1) if eps_vals[i] < eps_vals[i + 1])
        if declines >= 2:
            triggers.append(ExitTrigger(
                name="earnings_deterioration",
                severity=0.6,
                description=f"EPS declined in {declines} of last {len(eps_vals)-1} quarters",
            ))

    # --- 2. Revenue deceleration ---
    rev_vals = [q.revenue for q in quarterly[:6] if q.revenue is not None]
    if len(rev_vals) >= 4:
        # Compute sequential growth rates
        growths = []
        for i in range(len(rev_vals) - 1):
            if rev_vals[i + 1] and rev_vals[i + 1] > 0:
                growths.append((rev_vals[i] - rev_vals[i + 1]) / abs(rev_vals[i + 1]))
        if len(growths) >= 2:
            decelerations = sum(1 for i in range(len(growths) - 1) if growths[i] < growths[i + 1])
            if decelerations >= 2:
                triggers.append(ExitTrigger(
                    name="revenue_deceleration",
                    severity=0.5,
                    description=f"Revenue growth decelerating for {decelerations} consecutive periods",
                ))

    # --- 3. Margin compression ---
    op_margins = [q.operating_margin for q in quarterly[:4] if q.operating_margin is not None]
    if len(op_margins) >= 3:
        compressions = sum(1 for i in range(len(op_margins) - 1) if op_margins[i] < op_margins[i + 1])
        if compressions >= 2:
            triggers.append(ExitTrigger(
                name="margin_compression",
                severity=0.6,
                description=f"Operating margin compressed for {compressions} consecutive quarters",
            ))

    # --- 4. Guidance cut (keyword detection in recent news) ---
    guidance_keywords = ["guidance cut", "lowers guidance", "reduced guidance", "downward revision",
                         "lowered outlook", "cuts forecast", "slashes forecast", "warns on earnings"]
    recent_news = [a for a in articles if (datetime.now() - a.published_at).days <= 14]
    for article in recent_news:
        headline_lower = article.headline.lower()
        if any(kw in headline_lower for kw in guidance_keywords):
            triggers.append(ExitTrigger(
                name="guidance_cut",
                severity=0.7,
                description=f"Guidance cut detected: '{article.headline[:80]}'",
            ))
            break  # One trigger is enough

    # --- 5. Debt stress ---
    if len(quarterly) >= 3:
        de_ratios = []
        for q in quarterly[:3]:
            if q.total_debt is not None and q.total_equity and q.total_equity > 0:
                de_ratios.append(q.total_debt / q.total_equity)
        if len(de_ratios) >= 2 and de_ratios[-1] > 0:
            increase = (de_ratios[0] - de_ratios[-1]) / de_ratios[-1]
            if increase > 0.20:
                triggers.append(ExitTrigger(
                    name="debt_stress",
                    severity=0.5,
                    description=f"Debt-to-equity increased {increase:.0%} over recent quarters",
                ))

    # --- 6. Sentiment collapse ---
    recent_7d = [a for a in articles if (datetime.now() - a.published_at).days <= 7]
    if len(recent_7d) >= 5:
        avg_sent = np.mean([a.sentiment_score for a in recent_7d if a.sentiment_score is not None])
        if avg_sent < -0.5:
            triggers.append(ExitTrigger(
                name="sentiment_collapse",
                severity=0.6,
                description=f"7-day average sentiment severely negative ({avg_sent:.2f})",
            ))

    # --- 7. Negative news cluster ---
    neg_48h = [a for a in articles
               if a.sentiment == "negative" and (datetime.now() - a.published_at).total_seconds() < 172800]
    if len(neg_48h) >= 3:
        triggers.append(ExitTrigger(
            name="negative_news_cluster",
            severity=0.5,
            description=f"{len(neg_48h)} negative articles in last 48 hours",
        ))

    # --- 8. Price breakdown ---
    sorted_prices = sorted(prices, key=lambda p: p.date)
    if len(sorted_prices) >= 200:
        closes = np.array([p.close for p in sorted_prices])
        current = closes[-1]
        sma_200 = float(np.mean(closes[-200:]))
        sma_200_prev = float(np.mean(closes[-210:-10])) if len(closes) >= 210 else sma_200

        if current < sma_200 and sma_200 < sma_200_prev:
            triggers.append(ExitTrigger(
                name="price_breakdown",
                severity=0.4,
                description=f"Price below declining 200-day SMA",
            ))

    # --- 9. Abnormal volatility ---
    if len(sorted_prices) >= 90:
        closes = np.array([p.close for p in sorted_prices])
        returns_30 = np.diff(closes[-31:]) / closes[-31:-1]
        returns_90 = np.diff(closes[-91:]) / closes[-91:-1]
        vol_30 = float(np.std(returns_30))
        vol_90 = float(np.std(returns_90))

        if vol_90 > 0 and vol_30 > 2 * vol_90:
            triggers.append(ExitTrigger(
                name="abnormal_volatility",
                severity=0.4,
                description=f"30-day volatility ({vol_30:.3f}) is {vol_30/vol_90:.1f}x the 90-day average",
            ))

    # --- 10. Peer underperformance ---
    if len(sorted_prices) >= 63:
        closes = np.array([p.close for p in sorted_prices])
        stock_return = (closes[-1] - closes[-63]) / closes[-63]
        relative = stock_return - sector_return_3m

        if relative < -0.15:
            triggers.append(ExitTrigger(
                name="peer_underperformance",
                severity=0.4,
                description=f"Underperforming sector by {abs(relative):.0%} over 3 months",
            ))

    # --- Determine signal override ---
    if not triggers:
        return ExitSignalResult(
            signal="hold",
            triggers=[],
            avg_severity=0.0,
            explanation=["No exit triggers detected"],
        )

    severities = [t.severity for t in triggers]
    avg_severity = float(np.mean(severities))
    max_severity = max(severities)

    if len(triggers) >= 4 or max_severity >= 0.8:
        signal = "exit"
    elif len(triggers) >= 2 and avg_severity >= 0.5:
        signal = "exit_watch"
    elif len(triggers) >= 1:
        signal = "reduce"
    else:
        signal = "hold"

    explanations = [f"{t.name}: {t.description}" for t in triggers]

    return ExitSignalResult(
        signal=signal,
        triggers=triggers,
        avg_severity=round(avg_severity, 2),
        explanation=explanations,
    )
