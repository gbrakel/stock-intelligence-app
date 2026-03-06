"""
Sentiment scoring engine.
Uses FinBERT (ProsusAI/finbert) for financial headline classification,
then aggregates into a 0-100 sentiment score.

FinBERT outputs per headline: positive / neutral / negative with confidence.

Aggregation (rolling windows):
- Average sentiment of recent news (40%)
- Volume of news, weighted by recency (20%)
- Ratio of positive to negative headlines (20%)
- Sentiment trend: improving or worsening (20%)
"""

import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

from pipeline.providers.base import NewsArticle
from pipeline.utils.logging import log

# Lazy-load FinBERT to avoid import overhead when not needed
_pipeline = None


def _get_finbert():
    """Lazy-load the FinBERT sentiment pipeline."""
    global _pipeline
    if _pipeline is None:
        try:
            from transformers import pipeline as hf_pipeline

            cache_dir = os.environ.get("TRANSFORMERS_CACHE", None)
            log.info("Loading FinBERT model (first run will download ~400MB)...")
            _pipeline = hf_pipeline(
                "sentiment-analysis",
                model="ProsusAI/finbert",
                tokenizer="ProsusAI/finbert",
                model_kwargs={"cache_dir": cache_dir} if cache_dir else {},
            )
            log.info("FinBERT loaded successfully")
        except ImportError:
            log.warning("transformers not installed — sentiment will use fallback")
            _pipeline = "unavailable"
        except Exception as e:
            log.error(f"Failed to load FinBERT: {e}")
            _pipeline = "unavailable"

    return _pipeline if _pipeline != "unavailable" else None


@dataclass
class SentimentResult:
    score: float  # 0-100
    components: dict[str, Optional[float]]
    explanation: list[str]
    classified_articles: list[NewsArticle]  # Articles with sentiment filled in


def classify_articles(articles: list[NewsArticle]) -> list[NewsArticle]:
    """Classify sentiment on each article using FinBERT."""
    model = _get_finbert()

    for article in articles:
        if article.sentiment is not None:
            continue  # Already classified

        if model is None:
            # Fallback: neutral classification
            article.sentiment = "neutral"
            article.sentiment_score = 0.0
            article.sentiment_confidence = 0.3
            continue

        try:
            # Truncate headline to 512 tokens (FinBERT limit)
            text = article.headline[:512]
            result = model(text)[0]

            label = result["label"].lower()
            confidence = float(result["score"])

            article.sentiment = label
            article.sentiment_confidence = round(confidence, 3)

            # Map to numeric score: positive=1.0, neutral=0.0, negative=-1.0
            if label == "positive":
                article.sentiment_score = round(confidence, 3)
            elif label == "negative":
                article.sentiment_score = round(-confidence, 3)
            else:
                article.sentiment_score = 0.0

        except Exception as e:
            log.debug(f"Sentiment classification failed for headline: {e}")
            article.sentiment = "neutral"
            article.sentiment_score = 0.0
            article.sentiment_confidence = 0.3

    return articles


def score_sentiment(
    ticker: str,
    articles: list[NewsArticle],
) -> SentimentResult:
    """
    Compute aggregated sentiment score from classified news articles.
    """
    if not articles:
        return SentimentResult(
            score=50.0,
            components={},
            explanation=["No recent news available"],
            classified_articles=[],
        )

    # Ensure articles are classified
    classified = classify_articles(articles)

    now = datetime.now()
    components: dict[str, Optional[float]] = {}
    explanations: list[str] = []

    # --- Average sentiment (recency-weighted, 7-day window) ---
    recent_7d = [a for a in classified if (now - a.published_at).days <= 7]
    recent_30d = classified  # Already filtered to ~30 days by provider

    avg_7d = _weighted_avg_sentiment(recent_7d, now)
    avg_30d = _weighted_avg_sentiment(recent_30d, now)

    # Use 7d if available, fallback to 30d
    avg_sentiment = avg_7d if recent_7d else avg_30d
    # Map from [-1, 1] to [0, 1]
    components["avg_sentiment"] = (avg_sentiment + 1) / 2 if avg_sentiment is not None else 0.5

    # --- News volume score ---
    # More recent news = more data = slightly higher confidence
    volume_score = min(len(recent_7d) / 10.0, 1.0)  # Cap at 10 articles = max
    components["news_volume"] = volume_score

    # --- Positive/negative ratio ---
    positive = sum(1 for a in recent_30d if a.sentiment == "positive")
    negative = sum(1 for a in recent_30d if a.sentiment == "negative")
    total = positive + negative
    if total > 0:
        pos_ratio = positive / total
        components["pos_neg_ratio"] = pos_ratio
        if pos_ratio > 0.7:
            explanations.append(f"{positive}/{total} recent articles are positive")
        elif pos_ratio < 0.3:
            explanations.append(f"{negative}/{total} recent articles are negative")
    else:
        components["pos_neg_ratio"] = 0.5

    # --- Sentiment trend (7d avg vs 30d avg) ---
    if avg_7d is not None and avg_30d is not None:
        trend = avg_7d - avg_30d
        # Map difference to 0-1 scale
        trend_score = max(0.0, min(1.0, 0.5 + trend * 2))
        components["sentiment_trend"] = trend_score
        if trend > 0.2:
            explanations.append("Sentiment improving over recent days")
        elif trend < -0.2:
            explanations.append("Sentiment deteriorating recently")
    else:
        components["sentiment_trend"] = 0.5

    # --- Weighted composite ---
    weights = {
        "avg_sentiment": 0.40,
        "news_volume": 0.20,
        "pos_neg_ratio": 0.20,
        "sentiment_trend": 0.20,
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
        explanations.append("Neutral news sentiment")

    return SentimentResult(
        score=round(score, 1),
        components=components,
        explanation=explanations,
        classified_articles=classified,
    )


def _weighted_avg_sentiment(
    articles: list[NewsArticle],
    now: datetime,
) -> Optional[float]:
    """Compute recency-weighted average sentiment score."""
    if not articles:
        return None

    total_weight = 0.0
    weighted_sum = 0.0

    for article in articles:
        if article.sentiment_score is None:
            continue

        # Recency weight: exponential decay, half-life of 3 days
        age_days = max((now - article.published_at).total_seconds() / 86400, 0.01)
        weight = 2.0 ** (-age_days / 3.0) * article.relevance_score

        weighted_sum += article.sentiment_score * weight
        total_weight += weight

    if total_weight == 0:
        return None
    return weighted_sum / total_weight
