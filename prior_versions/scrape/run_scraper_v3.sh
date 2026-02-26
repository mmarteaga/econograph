#!/bin/bash

# Econograph V3 Scraper Runner
# ============================
# This script runs the economist spider and saves output to economists_v3.json

echo "Starting Economist Spider V3..."
echo "This will take some time due to rate limiting (respectful to Wikipedia)"
echo ""

cd EconThoughtAtlas

# Run the spider and save to economists_v3.json
scrapy crawl economists_v3 -o ../economists_v3.json

echo ""
echo "Scraping complete! Output saved to: scrape/economists_v3.json"
echo ""
echo "Next steps:"
echo "  1. Review the data: cat scrape/economists_v3.json | jq . | less"
echo "  2. Run stage 2: python3 build_graph/transform_v3.py scrape/economists_v3.json"
