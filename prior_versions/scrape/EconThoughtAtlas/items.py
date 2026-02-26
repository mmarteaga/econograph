import scrapy

class EconThoughtAtlasItem(scrapy.Item):
    """
    Defines the structured data fields for economist entries scraped from Wikipedia.
    These fields correspond to metadata commonly found in infoboxes of economist biographies.
    See ref: https://docs.scrapy.org/en/latest/topics/items.html
    """
    name = scrapy.Field()
    url = scrapy.Field()
    born = scrapy.Field()
    died = scrapy.Field()
    alma_mater = scrapy.Field()
    education = scrapy.Field()
    influences = scrapy.Field()
    notable_ideas = scrapy.Field()
    contributions = scrapy.Field()
    doctoral_advisors = scrapy.Field()
    doctoral_students = scrapy.Field()
    image_url = scrapy.Field()
