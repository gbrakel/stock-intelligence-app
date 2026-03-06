"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { SignalBadge } from "@/components/SignalBadge";
import { RiskBadge } from "@/components/RiskBadge";
import type { WatchlistItem, RankedStock, RankingsData } from "@/types";

export default function WatchlistPage() {
  const [watchlist, setWatchlist] = useState<WatchlistItem[]>([]);
  const [rankings, setRankings] = useState<RankingsData | null>(null);
  const [newTicker, setNewTicker] = useState("");

  useEffect(() => {
    // Load watchlist from localStorage
    const stored = localStorage.getItem("stock-intel-watchlist");
    if (stored) {
      setWatchlist(JSON.parse(stored));
    }
    // Load latest rankings
    fetch("/data/rankings/latest.json")
      .then((r) => r.ok ? r.json() : null)
      .then(setRankings)
      .catch(() => {});
  }, []);

  const saveWatchlist = (items: WatchlistItem[]) => {
    setWatchlist(items);
    localStorage.setItem("stock-intel-watchlist", JSON.stringify(items));
  };

  const addToWatchlist = () => {
    const ticker = newTicker.trim().toUpperCase();
    if (!ticker || watchlist.some((w) => w.ticker === ticker)) return;

    saveWatchlist([...watchlist, { ticker, addedAt: new Date().toISOString(), notes: "" }]);
    setNewTicker("");
  };

  const removeFromWatchlist = (ticker: string) => {
    saveWatchlist(watchlist.filter((w) => w.ticker !== ticker));
  };

  const getRanking = (ticker: string): RankedStock | undefined =>
    rankings?.rankings.find((r) => r.ticker === ticker);

  return (
    <div className="space-y-6">
      <div className="flex items-end justify-between">
        <h1 className="text-2xl font-bold">Watchlist</h1>
        <div className="flex gap-2">
          <input
            type="text"
            placeholder="Add ticker..."
            value={newTicker}
            onChange={(e) => setNewTicker(e.target.value.toUpperCase())}
            onKeyDown={(e) => e.key === "Enter" && addToWatchlist()}
            className="bg-gray-800 border border-gray-700 rounded px-3 py-1.5 text-sm w-32 focus:outline-none focus:border-blue-500"
          />
          <button
            onClick={addToWatchlist}
            className="bg-blue-600 hover:bg-blue-700 text-white px-3 py-1.5 rounded text-sm transition-colors"
          >
            Add
          </button>
        </div>
      </div>

      {watchlist.length === 0 ? (
        <div className="text-center py-16 text-gray-500">
          <p className="text-lg mb-2">Your watchlist is empty</p>
          <p className="text-sm">Add tickers above or click the star on any stock page</p>
        </div>
      ) : (
        <div className="bg-gray-900/50 border border-gray-800 rounded-lg overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-800 text-gray-400 text-left">
                <th className="px-4 py-3 font-medium">Stock</th>
                <th className="px-4 py-3 font-medium">Score</th>
                <th className="px-4 py-3 font-medium">Signal</th>
                <th className="px-4 py-3 font-medium">Risk</th>
                <th className="px-4 py-3 font-medium">Price</th>
                <th className="px-4 py-3 font-medium">Added</th>
                <th className="px-4 py-3 font-medium"></th>
              </tr>
            </thead>
            <tbody>
              {watchlist.map((item) => {
                const rank = getRanking(item.ticker);
                return (
                  <tr key={item.ticker} className="border-b border-gray-800/50 hover:bg-gray-800/30">
                    <td className="px-4 py-3">
                      <Link href={`/stocks/${item.ticker}`} className="font-semibold hover:text-blue-400">
                        {item.ticker}
                      </Link>
                    </td>
                    <td className="px-4 py-3 font-mono">
                      {rank ? rank.composite_score.toFixed(0) : "\u2014"}
                    </td>
                    <td className="px-4 py-3">
                      {rank ? <SignalBadge signal={rank.signal} /> : <span className="text-gray-600">\u2014</span>}
                    </td>
                    <td className="px-4 py-3">
                      {rank ? <RiskBadge level={rank.risk_level} /> : <span className="text-gray-600">\u2014</span>}
                    </td>
                    <td className="px-4 py-3 font-mono">
                      {rank?.price != null ? `$${rank.price.toFixed(2)}` : "\u2014"}
                    </td>
                    <td className="px-4 py-3 text-xs text-gray-500">
                      {new Date(item.addedAt).toLocaleDateString()}
                    </td>
                    <td className="px-4 py-3">
                      <button
                        onClick={() => removeFromWatchlist(item.ticker)}
                        className="text-gray-500 hover:text-red-400 text-xs transition-colors"
                      >
                        Remove
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
