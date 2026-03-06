import Link from "next/link";
import {
  getStocks,
  getLatestRankings,
  getStockFinancials,
  getStockPrices,
  getStockNews,
  getStockRisk,
  getStockScoreHistory,
} from "@/lib/data";
import { SignalBadge } from "@/components/SignalBadge";
import { RiskBadge } from "@/components/RiskBadge";
import { DeltaIndicator } from "@/components/DeltaIndicator";
import { ScoreBreakdownChart } from "@/components/ScoreBreakdownChart";
import { NewsTimeline } from "@/components/NewsTimeline";
import { RiskBreakdown } from "@/components/RiskBreakdown";
import { FinancialTable } from "@/components/FinancialTable";

// Generate static paths for all tickers
export async function generateStaticParams() {
  const stocks = await getStocks();
  return stocks.map((s) => ({ ticker: s.ticker }));
}

export default async function StockDetailPage({ params }: { params: Promise<{ ticker: string }> }) {
  const { ticker } = await params;
  const upperTicker = ticker.toUpperCase();

  const [rankings, financials, prices, news, risk, scoreHistory] = await Promise.all([
    getLatestRankings(),
    getStockFinancials(upperTicker),
    getStockPrices(upperTicker),
    getStockNews(upperTicker),
    getStockRisk(upperTicker),
    getStockScoreHistory(upperTicker),
  ]);

  const stock = rankings?.rankings.find((r) => r.ticker === upperTicker);

  if (!stock) {
    return (
      <div className="text-center py-20">
        <h1 className="text-xl font-bold text-gray-400">Stock not found: {upperTicker}</h1>
        <Link href="/" className="text-blue-400 hover:underline mt-4 inline-block">Back to Dashboard</Link>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-3xl font-bold">{stock.ticker}</h1>
            <SignalBadge signal={stock.signal} />
            <RiskBadge level={stock.risk_level} />
          </div>
          <p className="text-gray-400 mt-1">{stock.name} &middot; {stock.sector}</p>
        </div>
        <div className="text-right">
          {stock.price != null && (
            <div>
              <div className="text-2xl font-mono font-bold">${stock.price.toFixed(2)}</div>
              {stock.price_change_pct != null && (
                <div className={`text-sm ${stock.price_change_pct >= 0 ? "text-green-400" : "text-red-400"}`}>
                  {stock.price_change_pct >= 0 ? "+" : ""}{stock.price_change_pct.toFixed(2)}%
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Summary card */}
      <div className="bg-gray-900/50 border border-gray-800 rounded-lg p-6">
        <p className="text-gray-300">{stock.explanation.summary}</p>
        <div className="flex items-center gap-4 mt-4">
          <div className="text-center">
            <div className="text-3xl font-bold font-mono">{stock.composite_score.toFixed(0)}</div>
            <div className="text-xs text-gray-500">Score</div>
          </div>
          <DeltaIndicator delta={stock.score_delta} />
          <div className="text-xs text-gray-500">
            Confidence: {(stock.signal_confidence * 100).toFixed(0)}%
          </div>
        </div>
      </div>

      {/* Exit warnings */}
      {stock.explanation.exit_warnings.length > 0 && (
        <div className="bg-red-950/30 border border-red-900/50 rounded-lg p-4">
          <h3 className="text-sm font-semibold text-red-400 mb-2">Exit Warnings</h3>
          <ul className="space-y-1 text-sm text-gray-300">
            {stock.explanation.exit_warnings.map((w, i) => (
              <li key={i}>&bull; {w}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Score breakdown */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-gray-900/50 border border-gray-800 rounded-lg p-6">
          <h3 className="text-sm font-semibold text-gray-400 mb-4">Score Breakdown</h3>
          <ScoreBreakdownChart scores={stock.scores} />
        </div>

        <div className="bg-gray-900/50 border border-gray-800 rounded-lg p-6">
          <h3 className="text-sm font-semibold text-gray-400 mb-4">Top Reasons</h3>
          <ul className="space-y-2 text-sm">
            {stock.explanation.top_reasons.map((reason, i) => (
              <li key={i} className="text-gray-300">{reason}</li>
            ))}
          </ul>
          <h3 className="text-sm font-semibold text-gray-400 mt-6 mb-2">Key Risks</h3>
          <ul className="space-y-2 text-sm">
            {stock.explanation.risks.map((risk, i) => (
              <li key={i} className="text-gray-400">{risk}</li>
            ))}
          </ul>
        </div>
      </div>

      {/* Risk breakdown */}
      {risk && (
        <div className="bg-gray-900/50 border border-gray-800 rounded-lg p-6">
          <h3 className="text-sm font-semibold text-gray-400 mb-4">Risk Assessment</h3>
          <RiskBreakdown risk={risk} />
        </div>
      )}

      {/* Financials */}
      {financials && financials.quarterly.length > 0 && (
        <div className="bg-gray-900/50 border border-gray-800 rounded-lg p-6">
          <h3 className="text-sm font-semibold text-gray-400 mb-4">Quarterly Financials</h3>
          <FinancialTable periods={financials.quarterly.slice(0, 8)} />
        </div>
      )}

      {/* Valuation metrics */}
      {financials?.valuation && (
        <div className="bg-gray-900/50 border border-gray-800 rounded-lg p-6">
          <h3 className="text-sm font-semibold text-gray-400 mb-4">Valuation</h3>
          <div className="grid grid-cols-2 sm:grid-cols-5 gap-4">
            <ValMetric label="P/E" value={financials.valuation.pe_ratio} />
            <ValMetric label="Fwd P/E" value={financials.valuation.forward_pe} />
            <ValMetric label="EV/EBITDA" value={financials.valuation.ev_ebitda} />
            <ValMetric label="P/S" value={financials.valuation.price_to_sales} />
            <ValMetric label="PEG" value={financials.valuation.peg_ratio} />
          </div>
        </div>
      )}

      {/* News timeline */}
      {news && news.articles.length > 0 && (
        <div className="bg-gray-900/50 border border-gray-800 rounded-lg p-6">
          <h3 className="text-sm font-semibold text-gray-400 mb-4">
            Recent News ({news.articles.length} articles)
          </h3>
          <NewsTimeline articles={news.articles.slice(0, 20)} />
        </div>
      )}

      {/* Changes vs yesterday */}
      {stock.explanation.changes.length > 0 && (
        <div className="bg-gray-900/50 border border-gray-800 rounded-lg p-6">
          <h3 className="text-sm font-semibold text-gray-400 mb-4">Changes vs Yesterday</h3>
          <ul className="space-y-1 text-sm text-gray-300">
            {stock.explanation.changes.map((c, i) => (
              <li key={i}>&bull; {c}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

function ValMetric({ label, value }: { label: string; value: number | null }) {
  return (
    <div>
      <div className="text-xs text-gray-500">{label}</div>
      <div className="font-mono font-semibold">
        {value != null ? value.toFixed(1) : "\u2014"}
      </div>
    </div>
  );
}
