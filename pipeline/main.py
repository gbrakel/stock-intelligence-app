"""
Main pipeline orchestrator.
Runs the full daily pipeline: ingest → score → export.

Usage:
    python -m pipeline.main                     # All stocks
    python -m pipeline.main --tickers AAPL,MSFT  # Specific tickers
"""

import argparse
import json
import sys
import time
from datetime import date, datetime
from pathlib import Path

from pipeline.config import DATA_DIR, STOCK_UNIVERSE, PRICE_HISTORY_DAYS, NEWS_LOOKBACK_DAYS, MAX_NEWS_PER_STOCK
from pipeline.providers.yahoo_provider import YahooFinanceProvider
from pipeline.providers.finnhub_provider import FinnhubProvider
from pipeline.providers.news_rss_provider import GoogleNewsRSSProvider
from pipeline.providers.base import FinancialSnapshot, PriceBar, NewsArticle, ValuationData
from pipeline.engines.fundamentals import score_fundamentals
from pipeline.engines.growth_trend import score_growth_trend
from pipeline.engines.valuation import score_valuation
from pipeline.engines.sentiment import score_sentiment
from pipeline.engines.technical import score_technical
from pipeline.engines.risk import score_risk
from pipeline.engines.exit_signals import evaluate_exit_signals
from pipeline.engines.scorer import compute_composite
from pipeline.engines.explainer import generate_explanation
from pipeline.exporters.json_exporter import JSONExporter
from pipeline.utils.logging import log


def main():
    parser = argparse.ArgumentParser(description="Stock Intelligence Daily Pipeline")
    parser.add_argument("--tickers", type=str, help="Comma-separated list of tickers to process")
    args = parser.parse_args()

    # Determine stock universe
    if args.tickers:
        tickers_filter = set(t.strip().upper() for t in args.tickers.split(","))
        stocks = [s for s in STOCK_UNIVERSE if s["ticker"] in tickers_filter]
        if not stocks:
            log.error(f"No matching tickers found for: {args.tickers}")
            sys.exit(1)
    else:
        stocks = STOCK_UNIVERSE

    log.info(f"Starting pipeline for {len(stocks)} stocks")
    run_date = date.today()

    # Initialize providers
    yahoo = YahooFinanceProvider()
    finnhub = FinnhubProvider()
    google_news = GoogleNewsRSSProvider()
    exporter = JSONExporter()

    # Export stock universe
    exporter.export_stocks(stocks)

    # ------------------------------------------------------------------
    # Phase 1: Ingest data for all stocks
    # ------------------------------------------------------------------
    log.info("Phase 1: Ingesting data...")
    all_data: dict[str, dict] = {}

    # Fetch S&P 500 benchmark prices for relative momentum
    log.info("Fetching S&P 500 benchmark (SPY)...")
    benchmark_prices = yahoo.get_price_history("SPY", days=PRICE_HISTORY_DAYS)

    for stock in stocks:
        ticker = stock["ticker"]
        name = stock["name"]
        log.info(f"Ingesting {ticker} ({name})...")

        stock_data = {"stock": stock}

        try:
            # Financial data (Yahoo Finance)
            stock_data["financials"] = yahoo.get_financials(ticker)
            stock_data["valuation"] = yahoo.get_valuation(ticker)

            # Price history (Yahoo Finance)
            stock_data["prices"] = yahoo.get_price_history(ticker, days=PRICE_HISTORY_DAYS)

            # Quote
            stock_data["quote"] = yahoo.get_quote(ticker)

            # News (Finnhub + Google News RSS)
            finnhub_news = finnhub.get_news(ticker, name, days=NEWS_LOOKBACK_DAYS)
            rss_news = google_news.get_news(ticker, name, days=NEWS_LOOKBACK_DAYS)

            # Merge and deduplicate by headline similarity
            all_news = _merge_news(finnhub_news, rss_news)
            stock_data["news"] = all_news[:MAX_NEWS_PER_STOCK]

        except Exception as e:
            log.error(f"Failed to ingest {ticker}: {e}")
            stock_data.setdefault("financials", [])
            stock_data.setdefault("valuation", ValuationData())
            stock_data.setdefault("prices", [])
            stock_data.setdefault("news", [])
            stock_data.setdefault("quote", None)

        all_data[ticker] = stock_data

    # ------------------------------------------------------------------
    # Phase 2: Build sector peer data for relative scoring
    # ------------------------------------------------------------------
    log.info("Phase 2: Building sector peer data...")
    sector_peer_data = _build_sector_peer_data(all_data, stocks)

    # ------------------------------------------------------------------
    # Phase 3: Score all stocks
    # ------------------------------------------------------------------
    log.info("Phase 3: Scoring stocks...")

    # Load previous scores for delta computation
    previous_scores = _load_previous_scores()

    all_rankings: list[dict] = []
    all_latest_scores: list[dict] = []
    all_alerts: list[dict] = []
    signal_changes: list[dict] = []

    # Compute sector 3-month returns for exit signal engine
    sector_returns = _compute_sector_returns(all_data, stocks)

    for stock in stocks:
        ticker = stock["ticker"]
        sector = stock["sector"]
        data = all_data.get(ticker, {})
        log.info(f"Scoring {ticker}...")

        financials = data.get("financials", [])
        val_data = data.get("valuation", ValuationData())
        prices = data.get("prices", [])
        news = data.get("news", [])
        quote = data.get("quote")

        peer_data = sector_peer_data.get(sector, {})

        # Run scoring engines
        fund_result = score_fundamentals(ticker, financials, val_data, peer_data)
        growth_result = score_growth_trend(ticker, financials)
        val_result = score_valuation(ticker, val_data, peer_data)
        sent_result = score_sentiment(ticker, news)
        tech_result = score_technical(ticker, prices, benchmark_prices)
        risk_result = score_risk(ticker, prices, financials, sent_result.classified_articles, sector, peer_data)
        exit_result = evaluate_exit_signals(
            ticker, financials, prices, sent_result.classified_articles,
            sector_return_3m=sector_returns.get(sector, 0.0),
        )

        # Composite score
        prev_score = previous_scores.get(ticker, {}).get("composite")
        composite = compute_composite(
            fundamentals_score=fund_result.score,
            growth_trend_score=growth_result.score,
            valuation_score=val_result.score,
            sentiment_score=sent_result.score,
            technical_score=tech_result.score,
            risk_score=risk_result.overall_score,
            exit_result=exit_result,
            previous_score=prev_score,
        )

        # Explanation
        prev_signal = previous_scores.get(ticker, {}).get("signal")
        explanation = generate_explanation(
            ticker, composite, fund_result, growth_result, val_result,
            sent_result, tech_result, risk_result, exit_result, prev_signal,
        )

        # ---- Export per-stock data ----

        # Financials JSON
        exporter.export_financials(ticker, {
            "ticker": ticker,
            "quarterly": [_snapshot_to_dict(s) for s in financials if s.period_type == "quarterly"],
            "annual": [_snapshot_to_dict(s) for s in financials if s.period_type == "annual"],
            "valuation": {
                "pe_ratio": val_data.pe_ratio,
                "forward_pe": val_data.forward_pe,
                "ev_ebitda": val_data.ev_ebitda,
                "price_to_sales": val_data.price_to_sales,
                "peg_ratio": val_data.peg_ratio,
                "market_cap": val_data.market_cap,
                "enterprise_value": val_data.enterprise_value,
            },
        })

        # Prices JSON (last 2 years of daily bars)
        exporter.export_prices(ticker, [
            {"date": p.date.isoformat(), "open": p.open, "high": p.high,
             "low": p.low, "close": p.close, "volume": p.volume}
            for p in sorted(prices, key=lambda x: x.date)
        ])

        # News JSON
        exporter.export_news(ticker, [
            {"headline": a.headline, "source": a.source, "url": a.url,
             "published_at": a.published_at.isoformat(),
             "sentiment": a.sentiment, "sentiment_score": a.sentiment_score,
             "sentiment_confidence": a.sentiment_confidence,
             "relevance_score": a.relevance_score, "event_type": a.event_type}
            for a in sent_result.classified_articles
        ])

        # Risk JSON
        exporter.export_risk(ticker, {
            "ticker": ticker,
            "risk_level": risk_result.risk_level,
            "overall_risk_score": risk_result.overall_score,
            "factors": risk_result.factors,
            "risk_flags": risk_result.risk_flags,
        })

        # Score history
        score_entry = {
            "date": run_date.isoformat(),
            "composite": composite.composite_score,
            "signal": composite.signal,
            "signal_confidence": composite.signal_confidence,
            "risk_level": risk_result.risk_level,
            "scores": composite.scores,
        }
        exporter.export_score(ticker, score_entry, run_date)

        # Build ranking entry
        ranking_entry = {
            "ticker": ticker,
            "name": stock["name"],
            "sector": stock["sector"],
            "composite_score": composite.composite_score,
            "signal": composite.signal,
            "signal_confidence": composite.signal_confidence,
            "risk_level": risk_result.risk_level,
            "score_delta": composite.score_delta,
            "scores": composite.scores,
            "explanation": {
                "top_reasons": explanation.top_reasons,
                "risks": explanation.risks,
                "changes": explanation.changes,
                "exit_warnings": explanation.exit_warnings,
                "summary": explanation.summary,
            },
            "price": quote.price if quote else None,
            "price_change_pct": quote.change_percent if quote else None,
        }
        all_rankings.append(ranking_entry)

        all_latest_scores.append({
            "ticker": ticker,
            "composite_score": composite.composite_score,
            "signal": composite.signal,
            "risk_level": risk_result.risk_level,
        })

        # Collect exit alerts
        if exit_result.signal in ("reduce", "exit_watch", "exit"):
            all_alerts.append({
                "ticker": ticker,
                "signal": exit_result.signal,
                "severity": exit_result.avg_severity,
                "triggers": [t.description for t in exit_result.triggers],
                "detected_at": run_date.isoformat(),
            })

        # Detect signal changes
        if prev_signal and prev_signal != composite.signal:
            signal_changes.append({
                "ticker": ticker,
                "previous_signal": prev_signal,
                "new_signal": composite.signal,
                "date": run_date.isoformat(),
            })

    # ------------------------------------------------------------------
    # Phase 4: Export aggregated data
    # ------------------------------------------------------------------
    log.info("Phase 4: Exporting rankings and signals...")

    # Sort rankings by composite score (highest first)
    all_rankings.sort(key=lambda x: x["composite_score"], reverse=True)
    for i, r in enumerate(all_rankings):
        r["rank"] = i + 1

    exporter.export_rankings(all_rankings, run_date)
    exporter.export_latest_scores(all_latest_scores)
    exporter.export_alerts(all_alerts)
    exporter.export_signal_changes(signal_changes)

    log.info(f"Pipeline complete. {len(all_rankings)} stocks scored.")
    log.info(f"Top 5: {', '.join(r['ticker'] for r in all_rankings[:5])}")
    if all_alerts:
        log.info(f"Exit alerts: {', '.join(a['ticker'] for a in all_alerts)}")
    if signal_changes:
        log.info(f"Signal changes: {len(signal_changes)}")


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def _merge_news(finnhub_news: list[NewsArticle], rss_news: list[NewsArticle]) -> list[NewsArticle]:
    """Merge and deduplicate news from multiple sources."""
    seen: set[str] = set()
    merged: list[NewsArticle] = []

    # Finnhub first (higher reliability)
    for article in finnhub_news:
        key = article.headline.lower().strip()[:60]
        if key not in seen:
            seen.add(key)
            merged.append(article)

    for article in rss_news:
        key = article.headline.lower().strip()[:60]
        if key not in seen:
            seen.add(key)
            merged.append(article)

    # Sort by recency
    merged.sort(key=lambda a: a.published_at, reverse=True)
    return merged


def _build_sector_peer_data(
    all_data: dict[str, dict],
    stocks: list[dict],
) -> dict[str, dict[str, list[float]]]:
    """Build per-sector peer metric lists for percentile scoring."""
    sector_metrics: dict[str, dict[str, list[float]]] = {}

    for stock in stocks:
        ticker = stock["ticker"]
        sector = stock["sector"]
        data = all_data.get(ticker, {})

        if sector not in sector_metrics:
            sector_metrics[sector] = {
                "roe": [], "net_margin": [], "fcf_yield": [],
                "debt_to_equity": [], "revenue": [], "cash_debt_ratio": [],
                "roa": [], "operating_margin": [],
                "pe_ratio": [], "forward_pe": [], "peg_ratio": [],
                "ev_ebitda": [], "price_to_sales": [],
                "avg_volume": [],
            }

        financials = data.get("financials", [])
        quarterly = sorted(
            [f for f in financials if f.period_type == "quarterly"],
            key=lambda x: x.period_end, reverse=True,
        )

        if quarterly:
            latest = quarterly[0]
            _append_if(sector_metrics[sector]["roe"], latest.roe)
            _append_if(sector_metrics[sector]["net_margin"], latest.net_margin)
            _append_if(sector_metrics[sector]["operating_margin"], latest.operating_margin)
            _append_if(sector_metrics[sector]["roa"], latest.roa)
            _append_if(sector_metrics[sector]["revenue"], latest.revenue)

            if latest.total_debt and latest.total_equity and latest.total_equity > 0:
                sector_metrics[sector]["debt_to_equity"].append(latest.total_debt / latest.total_equity)

            if latest.cash_and_equivalents and latest.total_debt and latest.total_debt > 0:
                sector_metrics[sector]["cash_debt_ratio"].append(latest.cash_and_equivalents / latest.total_debt)

            val = data.get("valuation", ValuationData())
            if latest.free_cash_flow and val.market_cap and val.market_cap > 0:
                sector_metrics[sector]["fcf_yield"].append(latest.free_cash_flow / val.market_cap)

        val_data = data.get("valuation", ValuationData())
        _append_if(sector_metrics[sector]["pe_ratio"], val_data.pe_ratio)
        _append_if(sector_metrics[sector]["forward_pe"], val_data.forward_pe)
        _append_if(sector_metrics[sector]["peg_ratio"], val_data.peg_ratio)
        _append_if(sector_metrics[sector]["ev_ebitda"], val_data.ev_ebitda)
        _append_if(sector_metrics[sector]["price_to_sales"], val_data.price_to_sales)

        # Average volume from price data
        prices = data.get("prices", [])
        if prices:
            import numpy as np
            vols = [p.volume for p in prices[-20:] if p.volume > 0]
            if vols:
                sector_metrics[sector]["avg_volume"].append(float(np.mean(vols)))

    return sector_metrics


def _compute_sector_returns(all_data: dict, stocks: list[dict]) -> dict[str, float]:
    """Compute average 3-month return per sector."""
    import numpy as np

    sector_returns: dict[str, list[float]] = {}
    for stock in stocks:
        ticker = stock["ticker"]
        sector = stock["sector"]
        prices = all_data.get(ticker, {}).get("prices", [])

        if len(prices) >= 63:
            sorted_p = sorted(prices, key=lambda p: p.date)
            closes = [p.close for p in sorted_p]
            if len(closes) >= 63 and closes[-63] > 0:
                ret = (closes[-1] - closes[-63]) / closes[-63]
                sector_returns.setdefault(sector, []).append(ret)

    return {sector: float(np.mean(rets)) for sector, rets in sector_returns.items() if rets}


def _load_previous_scores() -> dict[str, dict]:
    """Load previous day's scores from data/scores/latest.json."""
    path = DATA_DIR / "scores" / "latest.json"
    if not path.exists():
        return {}

    try:
        with open(path) as f:
            data = json.load(f)
        return {s["ticker"]: s for s in data}
    except Exception:
        return {}


def _snapshot_to_dict(s: FinancialSnapshot) -> dict:
    """Convert FinancialSnapshot to JSON-serializable dict."""
    return {
        "period_end": s.period_end.isoformat() if hasattr(s.period_end, "isoformat") else str(s.period_end),
        "revenue": s.revenue,
        "net_income": s.net_income,
        "eps": s.eps,
        "gross_margin": s.gross_margin,
        "operating_margin": s.operating_margin,
        "net_margin": s.net_margin,
        "free_cash_flow": s.free_cash_flow,
        "total_debt": s.total_debt,
        "total_equity": s.total_equity,
        "cash_and_equivalents": s.cash_and_equivalents,
        "roe": s.roe,
        "roa": s.roa,
        "shares_outstanding": s.shares_outstanding,
    }


def _append_if(lst: list, val):
    """Append value to list if not None."""
    if val is not None:
        lst.append(val)


if __name__ == "__main__":
    main()
