# Economist Scraper and Analyzer

This part of the project scrapes biographical data on economists from Wikipedia, converts it to CSV format, and performs cleaning and analysis. The output is a structured dataset suitable for historical analysis and visualization.

Source Wikipedia: https://en.wikipedia.org/wiki/List_of_economists

---

## Project Workflow

### 1. Run the Scrapy Spider

Use the `economists_v2` Scrapy spider to collect data from Wikipedia. The spider targets the main alphabetical list of economists on the Wikipedia page `List_of_economists` and extracts biographical and academic information from individual profile pages.

The output of this step is a JSON file: `economists_v2.json`

Navigate to the Scrapy project folder (the one with the Scrapy.cfg file) in the terminal and run:

```bash
scrapy crawl economists_v2 -o economist_v2.json
```
---

### 2. Convert JSON to CSV

Open and run the Jupyter Notebook `json_csv_convert.ipynb`.

This notebook takes the raw JSON file and:

- Wraps all JSON entries in a single top-level array
- Converts nested lists (like alma mater, education, etc.) into pipe-separated strings
- Outputs a tabular CSV file named `economists_raw.csv`

---

### 3. Clean and Analyze Data

Open and run the notebook `analysis_econ.ipynb`.

This notebook:

- Loads `economists_raw.csv`
- Removes malformed or irrelevant entries
- Standardizes date formats and text casing
- Outputs the cleaned dataset to `economists_cleaned.csv`
- Optionally generates summary statistics and visualizations

---

## Folder Structure

- `scrapy_project/spiders/economist_spider.py` — Scrapy spider definition
- `scrapy_project/pipelines.py` — Pipeline for exporting JSON
- `economists_v2.json` — Raw scraped data
- `json_csv_convert.ipynb` — JSON to CSV converter
- `economists_raw.csv` — Intermediate CSV output
- `analysis_econ.ipynb` — Data cleaning and analysis
- `economists_cleaned.csv` — Final cleaned data
- `README.md` — Project overview and instructions

---

## Notes

- The spider includes logic to filter out non-person pages (e.g. categories, think tanks, list articles).
- The JSON output is designed for consistency and ease of conversion.
- All names, institutions, and relationships are pulled from structured infobox data on individual Wikipedia pages.

---
