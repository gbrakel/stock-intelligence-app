import Link from "next/link";
import { getLatestRankings, getExitAlerts, getSignalChanges } from "@/lib/data";
import { SignalBadge } from "@/components/SignalBadge";
import { RiskBadge } from "@/components/RiskBadge";
import { DeltaIndicator } from "@/components/DeltaIndicator";
import type { RankedStock } from "@/types";

export default async function DashboardPage() {
  const rankings = await getLatestRankings();
  const alerts = await getExitAlerts();
  const changes = await getSignalChanges();

  if (!rankings || !rankings.rankings.length) {
    return (
      <div className="text-center py-20 text-gray-500">
        <h1 className="text-2xl font-bold mb-4">No Data Available</h1>
        <p>Run the pipeline first: <code className="bg-gray-800 px-2 py-1 rounded">make pipeline-test</code></p>
      </div>
    );
  }

  const topStocks = rankings.rankings;
  const buySignals = topStocks.filter((s) => s.signal === "strong_buy" || s.signal === "buy");
  const warnSignals = topStocks.filter((s) => ["reduce", "exit_watch", "exit"].includes(s.signal));

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-2xl font-bold">Daily Intelligence</h1>
          <p className="text-sm text-gray-500 mt-1">
            {rankings.date} &middot; {topStocks.length} stocks scored
          </p>
        </div>
        <div className="flex gap-4 text-sm">
          <div className="text-green-400">{buySignals.length} Buy signals</div>
          {warnSignals.length > 0 && (
            <div className="text-red-400">{warnSignals.length} Warnings</div>
          )}
        </div>
      </div>

      {/* Exit alerts banner */}
      {alerts.length > 0 && (
        <div className="bg-red-950/30 border border-red-900/50 rounded-lg p-4">
          <h2 className="text-sm font-semibold text-red-400 mb-2">Active Exit Warnings</h2>
          <div className="space-y-2">
            {alerts.map((alert) => (
              <div key={alert.ticker} className="flex items-center gap-3 text-sm">
                <Link href={`/stocks/${alert.ticker}`} className="font-mono font-semibold text-white hover:text-blue-400">
                  {alert.ticker}
                </Link>
                <SignalBadge signal={alert.signal as any} />
                <span className="text-gray-400">{alert.triggers[0]}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Signal changes banner */}
      {changes.length > 0 && (
        <div className="bg-yellow-950/20 border border-yellow-900/30 rounded-lg p-4">
          <h2 className="text-sm font-semibold text-yellow-400 mb-2">Signal Changes Today</h2>
          <div className="space-y-1">
            {changes.map((c) => (
              <div key={c.ticker} className="flex items-center gap-3 text-sm">
                <Link href={`/stocks/${c.ticker}`} className="font-mono font-semibold text-white hover:text-blue-400">
                  {c.ticker}
                </Link>
                <SignalBadge signal={c.previous_signal} />
                <span className="text-gray-500">&rarr;</span>
                <SignalBadge signal={c.new_signal} />
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Rankings table */}
      <div className="bg-gray-900/50 border border-gray-800 rounded-lg overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-800 text-gray-400 text-left">
                <th className="px-4 py-3 font-medium">#</th>
                <th className="px-4 py-3 font-medium">Stock</th>
                <th className="px-4 py-3 font-medium">Score</th>
                <th className="px-4 py-3 font-medium">Signal</th>
                <th className="px-4 py-3 font-medium">Risk</th>
                <th className="px-4 py-3 font-medium">Price</th>
                <th className="px-4 py-3 font-medium">Delta</th>
                <th className="px-4 py-3 font-medium">Top Reason</th>
              </tr>
            </thead>
            <tbody>
              {topStocks.map((stock) => (
                <StockRow key={stock.ticker} stock={stock} />
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function StockRow({ stock }: { stock: RankedStock }) {
  return (
    <tr className="border-b border-gray-800/50 hover:bg-gray-800/30 transition-colors">
      <td className="px-4 py-3 text-gray-500 font-mono text-xs">{stock.rank}</td>
      <td className="px-4 py-3">
        <Link href={`/stocks/${stock.ticker}`} className="hover:text-blue-400 transition-colors">
          <div className="font-semibold">{stock.ticker}</div>
          <div className="text-xs text-gray-500">{stock.name}</div>
        </Link>
      </td>
      <td className="px-4 py-3">
        <div className="flex items-center gap-2">
          <ScoreBar score={stock.composite_score} />
          <span className="font-mono font-semibold">{stock.composite_score.toFixed(0)}</span>
        </div>
      </td>
      <td className="px-4 py-3">
        <SignalBadge signal={stock.signal} />
      </td>
      <td className="px-4 py-3">
        <RiskBadge level={stock.risk_level} />
      </td>
      <td className="px-4 py-3 font-mono">
        {stock.price != null ? (
          <div>
            <div>${stock.price.toFixed(2)}</div>
            {stock.price_change_pct != null && (
              <div className={`text-xs ${stock.price_change_pct >= 0 ? "text-green-400" : "text-red-400"}`}>
                {stock.price_change_pct >= 0 ? "+" : ""}{stock.price_change_pct.toFixed(2)}%
              </div>
            )}
          </div>
        ) : (
          <span className="text-gray-600">&mdash;</span>
        )}
      </td>
      <td className="px-4 py-3">
        <DeltaIndicator delta={stock.score_delta} />
      </td>
      <td className="px-4 py-3 text-xs text-gray-400 max-w-xs truncate">
        {stock.explanation.top_reasons[0] || "&mdash;"}
      </td>
    </tr>
  );
}

function ScoreBar({ score }: { score: number }) {
  const color =
    score >= 80 ? "bg-green-400" :
    score >= 65 ? "bg-green-600" :
    score >= 45 ? "bg-yellow-500" :
    score >= 30 ? "bg-orange-500" :
    "bg-red-500";

  return (
    <div className="w-16 h-2 bg-gray-800 rounded-full overflow-hidden">
      <div className={`h-full rounded-full ${color}`} style={{ width: `${score}%` }} />
    </div>
  );
}
