"use client";

import type { ScoreBreakdown } from "@/types";

const DIMENSIONS = [
  { key: "fundamentals", label: "Fundamentals", color: "bg-blue-500" },
  { key: "growth_trend", label: "Growth", color: "bg-green-500" },
  { key: "valuation", label: "Valuation", color: "bg-purple-500" },
  { key: "sentiment", label: "Sentiment", color: "bg-yellow-500" },
  { key: "technical", label: "Technical", color: "bg-cyan-500" },
  { key: "risk_penalty", label: "Risk Penalty", color: "bg-red-500" },
] as const;

export function ScoreBreakdownChart({ scores }: { scores: ScoreBreakdown }) {
  return (
    <div className="space-y-3">
      {DIMENSIONS.map(({ key, label, color }) => {
        const value = scores[key as keyof ScoreBreakdown];
        const isRisk = key === "risk_penalty";
        return (
          <div key={key} className="flex items-center gap-3">
            <span className="w-28 text-xs text-gray-400">{label}</span>
            <div className="flex-1 h-3 bg-gray-800 rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full ${color} transition-all duration-500`}
                style={{ width: `${Math.min(value, 100)}%` }}
              />
            </div>
            <span className={`w-10 text-right font-mono text-sm ${isRisk ? "text-red-400" : "text-gray-300"}`}>
              {isRisk ? `-${value.toFixed(0)}` : value.toFixed(0)}
            </span>
          </div>
        );
      })}
    </div>
  );
}
