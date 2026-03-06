import type { StockRisk } from "@/types";

const RISK_FACTORS = [
  { key: "volatility", label: "Volatility" },
  { key: "debt_burden", label: "Debt Burden" },
  { key: "earnings_consistency", label: "Earnings Consistency" },
  { key: "cash_burn", label: "Cash Burn" },
  { key: "sector_risk", label: "Sector Risk" },
  { key: "sentiment_stability", label: "Sentiment Stability" },
  { key: "liquidity", label: "Liquidity" },
  { key: "drawdown", label: "Drawdown" },
] as const;

function riskColor(score: number): string {
  if (score <= 25) return "bg-green-500";
  if (score <= 50) return "bg-yellow-500";
  if (score <= 75) return "bg-orange-500";
  return "bg-red-500";
}

export function RiskBreakdown({ risk }: { risk: StockRisk }) {
  return (
    <div>
      <div className="flex items-center gap-4 mb-6">
        <div className="text-center">
          <div className="text-3xl font-bold font-mono">{risk.overall_risk_score.toFixed(0)}</div>
          <div className="text-xs text-gray-500">Risk Score</div>
        </div>
        <span className={`text-sm font-medium ${
          risk.risk_level === "low" ? "text-green-400" :
          risk.risk_level === "medium" ? "text-yellow-400" :
          risk.risk_level === "high" ? "text-orange-400" :
          "text-red-400"
        }`}>
          {risk.risk_level.replace("_", " ").toUpperCase()} RISK
        </span>
      </div>

      <div className="space-y-2">
        {RISK_FACTORS.map(({ key, label }) => {
          const value = risk.factors[key as keyof typeof risk.factors] ?? 0;
          return (
            <div key={key} className="flex items-center gap-3">
              <span className="w-36 text-xs text-gray-400">{label}</span>
              <div className="flex-1 h-2 bg-gray-800 rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full ${riskColor(value)}`}
                  style={{ width: `${Math.min(value, 100)}%` }}
                />
              </div>
              <span className="w-8 text-right font-mono text-xs text-gray-500">{value.toFixed(0)}</span>
            </div>
          );
        })}
      </div>

      {risk.risk_flags.length > 0 && (
        <div className="mt-4 pt-4 border-t border-gray-800">
          <h4 className="text-xs font-medium text-gray-500 mb-2">Risk Flags</h4>
          <ul className="space-y-1 text-sm text-orange-300">
            {risk.risk_flags.map((flag, i) => (
              <li key={i}>&bull; {flag}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
