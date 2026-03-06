import type { FinancialPeriod } from "@/types";

function fmt(val: number | null, type: "currency" | "pct" | "number" = "currency"): string {
  if (val == null) return "\u2014";
  if (type === "pct") return `${(val * 100).toFixed(1)}%`;
  if (type === "currency") {
    if (Math.abs(val) >= 1e9) return `$${(val / 1e9).toFixed(1)}B`;
    if (Math.abs(val) >= 1e6) return `$${(val / 1e6).toFixed(0)}M`;
    return `$${val.toFixed(0)}`;
  }
  return val.toFixed(2);
}

export function FinancialTable({ periods }: { periods: FinancialPeriod[] }) {
  // Most recent first, cap at 6
  const data = periods.slice(0, 6);

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-800 text-gray-500 text-left">
            <th className="px-3 py-2 font-medium">Metric</th>
            {data.map((p) => (
              <th key={p.period_end} className="px-3 py-2 font-medium font-mono text-xs">
                {p.period_end.slice(0, 7)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="text-xs">
          <MetricRow label="Revenue" data={data} field="revenue" format="currency" />
          <MetricRow label="Net Income" data={data} field="net_income" format="currency" />
          <MetricRow label="EPS" data={data} field="eps" format="number" />
          <MetricRow label="Gross Margin" data={data} field="gross_margin" format="pct" />
          <MetricRow label="Op. Margin" data={data} field="operating_margin" format="pct" />
          <MetricRow label="Net Margin" data={data} field="net_margin" format="pct" />
          <MetricRow label="FCF" data={data} field="free_cash_flow" format="currency" />
          <MetricRow label="Total Debt" data={data} field="total_debt" format="currency" />
          <MetricRow label="ROE" data={data} field="roe" format="pct" />
        </tbody>
      </table>
    </div>
  );
}

function MetricRow({
  label,
  data,
  field,
  format,
}: {
  label: string;
  data: FinancialPeriod[];
  field: keyof FinancialPeriod;
  format: "currency" | "pct" | "number";
}) {
  return (
    <tr className="border-b border-gray-800/30">
      <td className="px-3 py-2 text-gray-400">{label}</td>
      {data.map((p, i) => {
        const val = p[field] as number | null;
        const prev = i < data.length - 1 ? (data[i + 1][field] as number | null) : null;
        const improving = val != null && prev != null && val > prev;
        const declining = val != null && prev != null && val < prev;

        return (
          <td
            key={p.period_end}
            className={`px-3 py-2 font-mono ${
              improving ? "text-green-400" : declining ? "text-red-400" : "text-gray-300"
            }`}
          >
            {fmt(val, format)}
          </td>
        );
      })}
    </tr>
  );
}
