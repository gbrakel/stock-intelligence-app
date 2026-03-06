export function DeltaIndicator({ delta }: { delta: number | null }) {
  if (delta == null) {
    return <span className="text-xs text-gray-600">—</span>;
  }

  const isPositive = delta > 0;
  const isNeutral = Math.abs(delta) < 0.5;

  if (isNeutral) {
    return <span className="text-xs text-gray-500 font-mono">0.0</span>;
  }

  return (
    <span className={`text-xs font-mono font-semibold ${isPositive ? "text-green-400" : "text-red-400"}`}>
      {isPositive ? "+" : ""}{delta.toFixed(1)}
    </span>
  );
}
