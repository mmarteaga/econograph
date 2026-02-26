# Scrapy settings for Econ Thought Atlas project
#
# This configuration defines the crawling behavior for scraping economists'
# biographical metadata from Wikipedia, including name, education, influences, and more.

BOT_NAME = 'EconThoughtAtlas'

SPIDER_MODULES = ['EconThoughtAtlas.spiders']
NEWSPIDER_MODULE = 'EconThoughtAtlas.spiders'

# Identify the bot to websites
USER_AGENT = 'EconThoughtAtlas (+http://www.econschoolproject.com)'

# Obey robots.txt rules
ROBOTSTXT_OBEY = True

# Configure a delay for requests to prevent overloading Wikipedia
# DOWNLOAD_DELAY = 1.0

# Configure item pipelines
ITEM_PIPELINES = {
    'EconThoughtAtlas.pipelines.EconThoughtAtlasPipeline': 300,
}

# Enable logging for debugging
LOG_LEVEL = 'INFO'

# AutoThrottle extension for polite crawling
# AUTOTHROTTLE_ENABLED = True
# AUTOTHROTTLE_START_DELAY = 5
# AUTOTHROTTLE_MAX_DELAY = 60
# AUTOTHROTTLE_TARGET_CONCURRENCY = 1.0
# AUTOTHROTTLE_DEBUG = False