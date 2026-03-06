import type { RiskLevel } from "@/types";

const RISK_CONFIG: Record<RiskLevel, { label: string; className: string }> = {
  low: { label: "Low", className: "text-green-400" },
  medium: { label: "Medium", className: "text-yellow-400" },
  high: { label: "High", className: "text-orange-400" },
  very_high: { label: "Very High", className: "text-red-400" },
};

export function RiskBadge({ level }: { level: RiskLevel | string }) {
  const config = RISK_CONFIG[level as RiskLevel] ?? { label: level, className: "text-gray-400" };

  return <span className={`text-xs font-medium ${config.className}`}>{config.label}</span>;
}
