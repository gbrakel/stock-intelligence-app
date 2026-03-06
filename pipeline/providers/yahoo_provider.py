"""
Yahoo Finance provider via yfinance library.
Primary source for: financial statements, price history, valuation metrics, quotes.

Limitations:
- Unofficial scraper (not a sanctioned API). Can break when Yahoo changes backend.
- No official rate limits; community-observed ~360 req/hr. We add delays to be safe.
- Fine for personal use; not for commercial products.
"""

import time
from datetime import date, datetime, timedelta
from typing import Optional

import pandas as pd
import yfinance as yf

from pipeline.providers.base import (
    FinancialDataProvider,
    FinancialSnapshot,
    PriceBar,
    PriceDataProvider,
    StockQuote,
    ValuationData,
)
from pipeline.config import YAHOO_REQUEST_DELAY_SEC
from pipeline.utils.logging import log


class YahooFinanceProvider(FinancialDataProvider, PriceDataProvider):
    """Fetches financial data and prices from Yahoo Finance."""

    def __init__(self, delay_sec: float = YAHOO_REQUEST_DELAY_SEC):
        self._delay = delay_sec

    def _throttle(self):
        time.sleep(self._delay)

    # ------------------------------------------------------------------
    # FinancialDataProvider
    # ------------------------------------------------------------------

    def get_financials(self, ticker: str) -> list[FinancialSnapshot]:
        """Fetch quarterly and annual financials from Yahoo Finance."""
        snapshots: list[FinancialSnapshot] = []
        try:
            stock = yf.Ticker(ticker)
            self._throttle()

            # Quarterly financials
            q_income = stock.quarterly_income_stmt
            q_balance = stock.quarterly_balance_sheet
            q_cashflow = stock.quarterly_cashflow

            snapshots.extend(
                self._parse_financials(q_income, q_balance, q_cashflow, "quarterly")
            )

            # Annual financials
            a_income = stock.income_stmt
            a_balance = stock.balance_sheet
            a_cashflow = stock.cashflow

            snapshots.extend(
                self._parse_financials(a_income, a_balance, a_cashflow, "annual")
            )

        except Exception as e:
            log.error(f"Yahoo financials failed for {ticker}: {e}")

        return snapshots

    def _parse_financials(
        self,
        income: pd.DataFrame,
        balance: pd.DataFrame,
        cashflow: pd.DataFrame,
        period_type: str,
    ) -> list[FinancialSnapshot]:
        """Parse yfinance DataFrames into FinancialSnapshot objects."""
        snapshots = []
        if income is None or income.empty:
            return snapshots

        for col in income.columns:
            period_end = col.date() if hasattr(col, "date") else col

            revenue = self._safe_get(income, col, "Total Revenue")
            net_income = self._safe_get(income, col, "Net Income")
            gross_profit = self._safe_get(income, col, "Gross Profit")
            operating_income = self._safe_get(income, col, "Operating Income")
            eps = self._safe_get(income, col, "Basic EPS") or self._safe_get(income, col, "Diluted EPS")

            total_debt = self._safe_get(balance, col, "Total Debt") if balance is not None else None
            total_equity = self._safe_get(balance, col, "Total Equity Gross Minority Interest") or self._safe_get(balance, col, "Stockholders Equity") if balance is not None else None
            cash = self._safe_get(balance, col, "Cash And Cash Equivalents") if balance is not None else None
            total_assets = self._safe_get(balance, col, "Total Assets") if balance is not None else None
            shares = self._safe_get(income, col, "Basic Average Shares") or self._safe_get(income, col, "Diluted Average Shares")

            fcf = None
            if cashflow is not None and not cashflow.empty and col in cashflow.columns:
                op_cf = self._safe_get(cashflow, col, "Operating Cash Flow")
                capex = self._safe_get(cashflow, col, "Capital Expenditure")
                if op_cf is not None and capex is not None:
                    fcf = op_cf + capex  # capex is typically negative

            # Compute margins
            gross_margin = (gross_profit / revenue) if revenue and gross_profit else None
            operating_margin = (operating_income / revenue) if revenue and operating_income else None
            net_margin = (net_income / revenue) if revenue and net_income else None

            # Compute returns
            roe = (net_income / total_equity) if net_income and total_equity and total_equity != 0 else None
            roa = (net_income / total_assets) if net_income and total_assets and total_assets != 0 else None

            snapshots.append(FinancialSnapshot(
                period_end=period_end,
                period_type=period_type,
                revenue=revenue,
                net_income=net_income,
                eps=eps,
                gross_margin=gross_margin,
                operating_margin=operating_margin,
                net_margin=net_margin,
                free_cash_flow=fcf,
                total_debt=total_debt,
                total_equity=total_equity,
                cash_and_equivalents=cash,
                roe=roe,
                roa=roa,
                shares_outstanding=shares,
            ))

        return snapshots

    def _safe_get(self, df: pd.DataFrame, col, row_name: str) -> Optional[float]:
        """Safely extract a value from a yfinance DataFrame."""
        if df is None or df.empty:
            return None
        if row_name not in df.index:
            return None
        if col not in df.columns:
            return None
        val = df.loc[row_name, col]
        if pd.isna(val):
            return None
        return float(val)

    def get_valuation(self, ticker: str) -> ValuationData:
        """Fetch valuation metrics from Yahoo Finance info dict."""
        try:
            stock = yf.Ticker(ticker)
            self._throttle()
            info = stock.info or {}

            return ValuationData(
                pe_ratio=info.get("trailingPE"),
                forward_pe=info.get("forwardPE"),
                ev_ebitda=info.get("enterpriseToEbitda"),
                price_to_sales=info.get("priceToSalesTrailing12Months"),
                peg_ratio=info.get("pegRatio"),
                market_cap=info.get("marketCap"),
                enterprise_value=info.get("enterpriseValue"),
            )
        except Exception as e:
            log.error(f"Yahoo valuation failed for {ticker}: {e}")
            return ValuationData()

    # ------------------------------------------------------------------
    # PriceDataProvider
    # ------------------------------------------------------------------

    def get_price_history(self, ticker: str, days: int = 730) -> list[PriceBar]:
        """Fetch daily OHLCV history."""
        bars: list[PriceBar] = []
        try:
            stock = yf.Ticker(ticker)
            self._throttle()

            end = datetime.now()
            start = end - timedelta(days=days)
            hist = stock.history(start=start.strftime("%Y-%m-%d"), end=end.strftime("%Y-%m-%d"))

            if hist is None or hist.empty:
                return bars

            for idx, row in hist.iterrows():
                bar_date = idx.date() if hasattr(idx, "date") else idx
                bars.append(PriceBar(
                    date=bar_date,
                    open=float(row.get("Open", 0)),
                    high=float(row.get("High", 0)),
                    low=float(row.get("Low", 0)),
                    close=float(row.get("Close", 0)),
                    volume=int(row.get("Volume", 0)),
                    adj_close=float(row["Close"]) if "Close" in row else None,
                ))

        except Exception as e:
            log.error(f"Yahoo price history failed for {ticker}: {e}")

        return bars

    def get_quote(self, ticker: str) -> Optional[StockQuote]:
        """Fetch latest quote."""
        try:
            stock = yf.Ticker(ticker)
            self._throttle()
            info = stock.info or {}

            price = info.get("currentPrice") or info.get("regularMarketPrice")
            if price is None:
                return None

            prev_close = info.get("previousClose") or info.get("regularMarketPreviousClose", price)
            change = price - prev_close
            change_pct = (change / prev_close * 100) if prev_close else 0

            return StockQuote(
                price=price,
                change=round(change, 2),
                change_percent=round(change_pct, 2),
                volume=info.get("volume", 0) or 0,
                timestamp=datetime.now(),
            )
        except Exception as e:
            log.error(f"Yahoo quote failed for {ticker}: {e}")
            return None
