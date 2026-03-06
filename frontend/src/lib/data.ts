/**
 * Data loading layer — reads static JSON files from the data/ directory.
 * In Next.js static export, these are loaded at build time.
 *
 * The data/ directory is symlinked or copied into public/ during build.
 */

import { promises as fs } from "fs";
import path from "path";
import type {
  RankingsData,
  Stock,
  StockFinancials,
  StockNews,
  StockPrices,
  StockRisk,
  StockScoreHistory,
  ExitAlert,
  SignalChange,
} from "@/types";

const DATA_DIR = path.join(process.cwd(), "..", "data");

async function readJSON<T>(filePath: string): Promise<T | null> {
  try {
    const fullPath = path.join(DATA_DIR, filePath);
    const content = await fs.readFile(fullPath, "utf-8");
    return JSON.parse(content) as T;
  } catch {
    return null;
  }
}

// ---------------------------------------------------------------------------
// Stock universe
// ---------------------------------------------------------------------------

export async function getStocks(): Promise<Stock[]> {
  return (await readJSON<Stock[]>("stocks.json")) ?? [];
}

// ---------------------------------------------------------------------------
// Rankings
// ---------------------------------------------------------------------------

export async function getLatestRankings(): Promise<RankingsData | null> {
  return readJSON<RankingsData>("rankings/latest.json");
}

export async function getRankingsByDate(date: string): Promise<RankingsData | null> {
  return readJSON<RankingsData>(`rankings/${date}.json`);
}

// ---------------------------------------------------------------------------
// Per-stock data
// ---------------------------------------------------------------------------

export async function getStockFinancials(ticker: string): Promise<StockFinancials | null> {
  return readJSON<StockFinancials>(`financials/${ticker}.json`);
}

export async function getStockPrices(ticker: string): Promise<StockPrices | null> {
  return readJSON<StockPrices>(`prices/${ticker}.json`);
}

export async function getStockNews(ticker: string): Promise<StockNews | null> {
  return readJSON<StockNews>(`news/${ticker}.json`);
}

export async function getStockRisk(ticker: string): Promise<StockRisk | null> {
  return readJSON<StockRisk>(`risk/${ticker}.json`);
}

export async function getStockScoreHistory(ticker: string): Promise<StockScoreHistory | null> {
  return readJSON<StockScoreHistory>(`scores/${ticker}.json`);
}

// ---------------------------------------------------------------------------
// Signals
// ---------------------------------------------------------------------------

export async function getExitAlerts(): Promise<ExitAlert[]> {
  return (await readJSON<ExitAlert[]>("signals/alerts.json")) ?? [];
}

export async function getSignalChanges(): Promise<SignalChange[]> {
  return (await readJSON<SignalChange[]>("signals/changes.json")) ?? [];
}

// ---------------------------------------------------------------------------
// Helpers for static generation
// ---------------------------------------------------------------------------

export async function getAllTickers(): Promise<string[]> {
  const stocks = await getStocks();
  return stocks.map((s) => s.ticker);
}
