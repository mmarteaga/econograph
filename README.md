# About the Econonetwork
#### Last updated: May 2025

## Why?

Economists, like any other discipline, do not produce ideas in a vacuum. Their contributions build upon and influence one another, forming a complex and evolving web of intellectual history. The goal of this project is to uncover and visualize those interconnections—academic lineage, intellectual influence, and institutional affiliations—using structured data scraped from Wikipedia.

Inspired by projects that have done similar work in philosophy, this effort brings the tools of data scraping, transformation, and network analysis to the history of economic thought. While some similar projects exist, they often focus on either manual curation or simple lists. Here, we aim to automate the data collection process at scale and create a reusable foundation for further historical, institutional, or theoretical investigations into the economics profession.


## How?

### Data Collection

We begin by scraping Wikipedia’s [List of Economists](https://en.wikipedia.org/wiki/List_of_economists), which alphabetically indexes notable figures with individual articles. For each economist, we navigate to their page and extract structured information from the infobox and relevant HTML elements.

This is done using a custom Scrapy spider (`economists_v2`) with extraction logic tailored to the common patterns found in Wikipedia biographies.

### (Optional) Building the Graph of Economists

From the cleaned data, one can construct a directed graph where:

- Nodes = individual economists
- Edges = relationships such as “influenced by” or “doctoral advisor of”

This can be extended by:
- Applying PageRank or other centrality metrics
- Visualizing the network using a force-directed graph (e.g., with D3.js)

## Disclaimer

This project is subject to a number of limitations:
- It is based solely on the English-language Wikipedia and its editorial choices
- Some economists do not have structured or complete infobox data
- Influence relationships are often incomplete or ambiguous
- The scraper relies on heuristic parsing and may introduce noise

Despite these caveats, the resulting dataset offers a compelling and scalable lens into the development of economic ideas and the scholars behind them. Use with curiosity—and caution.

## References & Credit
This project uses
* [Wikipedia](https://www.wikipedia.org/) as its data source</li>
* [scrapy](https://scrapy.org/) for scraping</li>
* [networkx](https://networkx.github.io/) for calculating centrality scores</li>
* [d3.js](https://d3js.org/) for rendering the force-directed graph and axis</li>
* [materialize](https://materializecss.com/) for some UI elements</li>
