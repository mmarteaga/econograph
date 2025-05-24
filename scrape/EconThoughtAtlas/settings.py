# Scrapy settings for Econ Thought Atlas project
#
# This configuration defines the crawling behavior for scraping economists'
# biographical metadata from Wikipedia, including name, education, influences, and more.

BOT_NAME = "econ_thought_atlas"

SPIDER_MODULES = ["econ_thought_atlas.spiders"]
NEWSPIDER_MODULE = "econ_thought_atlas.spiders"

# Respect robots.txt
ROBOTSTXT_OBEY = True

# Pipelines
ITEM_PIPELINES = {
    "econ_thought_atlas.pipelines.EconThoughtAtlasPipeline": 300,
}

# Custom Middlewares (currently not used, but scaffolded)
# SPIDER_MIDDLEWARES = {
#     "econ_thought_atlas.middlewares.EconThoughtAtlasSpiderMiddleware": 543,
# }
# DOWNLOADER_MIDDLEWARES = {
#     "econ_thought_atlas.middlewares.EconThoughtAtlasDownloaderMiddleware": 543,
# }
