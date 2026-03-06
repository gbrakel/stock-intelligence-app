.PHONY: setup pipeline dev frontend build clean

# Install Python dependencies
setup:
	cd pipeline && pip3 install -r requirements.txt

# Run the full daily pipeline locally
pipeline:
	cd pipeline && python3 -m pipeline.main

# Run pipeline for a subset of tickers (for testing)
pipeline-test:
	cd pipeline && python3 -m pipeline.main --tickers AAPL,MSFT,NVDA

# Start Next.js dev server
dev:
	cd frontend && npm run dev

# Build static frontend
build:
	cd frontend && npm run build

# Install frontend dependencies
frontend-setup:
	cd frontend && npm install

# Clean generated data (careful!)
clean:
	rm -rf data/rankings/*.json data/scores/*.json data/financials/*.json
	rm -rf data/prices/*.json data/news/*.json data/risk/*.json data/signals/*.json
