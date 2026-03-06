import type { Signal } from "@/types";

const SIGNAL_CONFIG: Record<Signal, { label: string; className: string }> = {
  strong_buy: { label: "Strong Buy", className: "bg-green-500/20 text-green-400 border-green-500/30" },
  buy: { label: "Buy", className: "bg-green-900/30 text-green-300 border-green-700/30" },
  hold: { label: "Hold", className: "bg-gray-700/30 text-gray-300 border-gray-600/30" },
  reduce: { label: "Reduce", className: "bg-orange-900/30 text-orange-300 border-orange-700/30" },
  exit_watch: { label: "Exit Watch", className: "bg-red-900/30 text-red-300 border-red-700/30" },
  exit: { label: "Exit", className: "bg-red-500/20 text-red-400 border-red-500/30" },
};

export function SignalBadge({ signal }: { signal: Signal | string }) {
  const config = SIGNAL_CONFIG[signal as Signal] ?? {
    label: signal,
    className: "bg-gray-700/30 text-gray-400 border-gray-600/30",
  };

  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border ${config.className}`}>
      {config.label}
    </span>
  );
}
