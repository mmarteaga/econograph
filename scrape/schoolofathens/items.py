# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class econ_thought_atlasItem(scrapy.Item):
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
