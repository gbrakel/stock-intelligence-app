import { getLatestRankings, getSignalChanges } from "@/lib/data";
import { SignalBadge } from "@/components/SignalBadge";

export default async function HistoryPage() {
  const rankings = await getLatestRankings();
  const changes = await getSignalChanges();

  return (
    <div className="space-y-8">
      <h1 className="text-2xl font-bold">Signal History</h1>

      {/* Recent signal changes */}
      <section>
        <h2 className="text-lg font-semibold text-gray-300 mb-4">Recent Signal Changes</h2>
        {changes.length === 0 ? (
          <p className="text-gray-500 text-sm">No signal changes today</p>
        ) : (
          <div className="bg-gray-900/50 border border-gray-800 rounded-lg overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-800 text-gray-400 text-left">
                  <th className="px-4 py-3 font-medium">Stock</th>
                  <th className="px-4 py-3 font-medium">Previous</th>
                  <th className="px-4 py-3 font-medium">New</th>
                  <th className="px-4 py-3 font-medium">Date</th>
                </tr>
              </thead>
              <tbody>
                {changes.map((c) => (
                  <tr key={`${c.ticker}-${c.date}`} className="border-b border-gray-800/50">
                    <td className="px-4 py-3 font-semibold">{c.ticker}</td>
                    <td className="px-4 py-3"><SignalBadge signal={c.previous_signal} /></td>
                    <td className="px-4 py-3"><SignalBadge signal={c.new_signal} /></td>
                    <td className="px-4 py-3 text-gray-500">{c.date}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* Current signals distribution */}
      {rankings && (
        <section>
          <h2 className="text-lg font-semibold text-gray-300 mb-4">Current Signal Distribution</h2>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
            {(["strong_buy", "buy", "hold", "reduce", "exit_watch", "exit"] as const).map((signal) => {
              const count = rankings.rankings.filter((r) => r.signal === signal).length;
              return (
                <div key={signal} className="bg-gray-900/50 border border-gray-800 rounded-lg p-4 text-center">
                  <div className="text-2xl font-bold font-mono">{count}</div>
                  <SignalBadge signal={signal} />
                </div>
              );
            })}
          </div>
        </section>
      )}

      {/* Score distribution */}
      {rankings && (
        <section>
          <h2 className="text-lg font-semibold text-gray-300 mb-4">Score Leaderboard</h2>
          <div className="bg-gray-900/50 border border-gray-800 rounded-lg p-6">
            <div className="space-y-2">
              {rankings.rankings.slice(0, 20).map((stock) => (
                <div key={stock.ticker} className="flex items-center gap-3">
                  <span className="w-12 text-xs text-gray-500 font-mono">#{stock.rank}</span>
                  <span className="w-16 font-semibold text-sm">{stock.ticker}</span>
                  <div className="flex-1 h-3 bg-gray-800 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full ${
                        stock.composite_score >= 65 ? "bg-green-500" :
                        stock.composite_score >= 45 ? "bg-yellow-500" :
                        "bg-red-500"
                      }`}
                      style={{ width: `${stock.composite_score}%` }}
                    />
                  </div>
                  <span className="w-10 text-right font-mono text-sm">{stock.composite_score.toFixed(0)}</span>
                  <SignalBadge signal={stock.signal} />
                </div>
              ))}
            </div>
          </div>
        </section>
      )}
    </div>
  );
}
