# Stock Intelligence

Daily stock scoring, risk assessment, and signal intelligence platform.
Personal use research tool — not financial advice.

## Architecture

```
GitHub Actions (daily cron 6:30PM ET)
  → Python pipeline (ingest → score → export JSON)
    → Static Next.js site (reads JSON, deployed to GitHub Pages)
```

Zero hosting cost. No database server.

## Quick Start

### 1. Set up environment

```bash
cp .env.example .env
# Edit .env and add your FINNHUB_API_KEY (free at https://finnhub.io)
```

### 2. Install dependencies

```bash
# Python pipeline
cd pipeline && pip3 install -r requirements.txt

# Frontend
cd ../frontend && npm install
```

### 3. Run the pipeline (test with 3 stocks)

```bash
make pipeline-test
```

This fetches data for AAPL, MSFT, NVDA and writes JSON files to `data/`.

### 4. Start the frontend

```bash
make dev
```

Open http://localhost:3000

### 5. Run full pipeline (all 50 stocks)

```bash
make pipeline
```

Takes ~15-20 minutes (rate-limited API calls).
First run downloads FinBERT model (~400MB).

## GitHub Actions

The daily pipeline runs automatically via `.github/workflows/daily-pipeline.yml`:
- Triggers weekdays at 6:30PM ET (after US market close)
- Fetches data, scores all stocks, exports JSON
- Commits data files and deploys static site

Set these secrets in your repo (Settings → Secrets):
- `FINNHUB_API_KEY` — Get free at https://finnhub.io

## Data Sources

| Source | Data | Cost |
|--------|------|------|
| Finnhub | Company news, quotes | Free (60 req/min) |
| yfinance | Financials, prices, valuations | Free (unofficial) |
| Google News RSS | News headlines | Free |
| FinBERT | Sentiment classification | Free (local model) |

## Scoring Formula

```
Score = 0.30×Fundamentals + 0.25×Growth + 0.10×Valuation
      + 0.20×Sentiment + 0.10×Technical - 0.15×Risk
```

Signals: Strong Buy (≥80) → Buy (≥65) → Hold (≥45) → Reduce (≥30) → Exit Watch (≥15) → Exit (<15)

## Project Structure

```
pipeline/           Python pipeline (data ingestion + scoring)
  providers/        Data source abstractions (Yahoo, Finnhub, RSS)
  engines/          Scoring engines (fundamentals, growth, valuation, etc.)
  exporters/        JSON file writer
  main.py           Pipeline orchestrator

frontend/           Next.js static site
  src/app/          Pages (Dashboard, Stock Detail, Watchlist, History)
  src/components/   UI components

data/               Generated JSON (committed to repo, read by frontend)
```

## Disclaimer

This is a research tool for informational purposes only. Not financial advice.
Past performance does not guarantee future results. All signals are probabilistic
estimates with inherent uncertainty.
