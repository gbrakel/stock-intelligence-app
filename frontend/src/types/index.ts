// Stock Intelligence App — TypeScript types matching pipeline JSON schemas

export type Signal = "strong_buy" | "buy" | "hold" | "reduce" | "exit_watch" | "exit";
export type RiskLevel = "low" | "medium" | "high" | "very_high";

export interface Stock {
  ticker: string;
  name: string;
  sector: string;
  industry: string;
  exchange?: string;
}

export interface ScoreBreakdown {
  fundamentals: number;
  growth_trend: number;
  valuation: number;
  sentiment: number;
  technical: number;
  risk_penalty: number;
}

export interface StockExplanation {
  top_reasons: string[];
  risks: string[];
  changes: string[];
  exit_warnings: string[];
  summary: string;
}

export interface RankedStock {
  rank: number;
  ticker: string;
  name: string;
  sector: string;
  composite_score: number;
  signal: Signal;
  signal_confidence: number;
  risk_level: RiskLevel;
  score_delta: number | null;
  scores: ScoreBreakdown;
  explanation: StockExplanation;
  price: number | null;
  price_change_pct: number | null;
}

export interface RankingsData {
  date: string;
  generated_at: string;
  rankings: RankedStock[];
}

export interface ScoreHistoryEntry {
  date: string;
  composite: number;
  signal: Signal;
  signal_confidence: number;
  risk_level: RiskLevel;
  scores: ScoreBreakdown;
}

export interface StockScoreHistory {
  ticker: string;
  history: ScoreHistoryEntry[];
}

export interface FinancialPeriod {
  period_end: string;
  revenue: number | null;
  net_income: number | null;
  eps: number | null;
  gross_margin: number | null;
  operating_margin: number | null;
  net_margin: number | null;
  free_cash_flow: number | null;
  total_debt: number | null;
  total_equity: number | null;
  cash_and_equivalents: number | null;
  roe: number | null;
  roa: number | null;
  shares_outstanding: number | null;
}

export interface StockFinancials {
  ticker: string;
  quarterly: FinancialPeriod[];
  annual: FinancialPeriod[];
  valuation: {
    pe_ratio: number | null;
    forward_pe: number | null;
    ev_ebitda: number | null;
    price_to_sales: number | null;
    peg_ratio: number | null;
    market_cap: number | null;
    enterprise_value: number | null;
  };
}

export interface PriceBar {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface StockPrices {
  ticker: string;
  prices: PriceBar[];
}

export interface NewsArticle {
  headline: string;
  source: string;
  url: string;
  published_at: string;
  sentiment: "positive" | "neutral" | "negative" | null;
  sentiment_score: number | null;
  sentiment_confidence: number | null;
  relevance_score: number;
  event_type: string | null;
}

export interface StockNews {
  ticker: string;
  articles: NewsArticle[];
}

export interface RiskFactors {
  volatility: number;
  debt_burden: number;
  earnings_consistency: number;
  cash_burn: number;
  sector_risk: number;
  sentiment_stability: number;
  liquidity: number;
  drawdown: number;
  concentration?: number;
}

export interface StockRisk {
  ticker: string;
  risk_level: RiskLevel;
  overall_risk_score: number;
  factors: RiskFactors;
  risk_flags: string[];
}

export interface ExitAlert {
  ticker: string;
  signal: string;
  severity: number;
  triggers: string[];
  detected_at: string;
}

export interface SignalChange {
  ticker: string;
  previous_signal: Signal;
  new_signal: Signal;
  date: string;
}

export interface WatchlistItem {
  ticker: string;
  addedAt: string;
  notes: string;
}
