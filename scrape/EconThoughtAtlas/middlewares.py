from scrapy import signals

class EconThoughtAtlasSpiderMiddleware:
    """
    Middleware for spider-level events and data transformation.
    Currently acts as a passthrough; customize as needed.
    """
    @classmethod
    def from_crawler(cls, crawler):
        # This method is used by Scrapy to create your spiders.
        s = cls()
        crawler.signals.connect(s.spider_opened, signal=signals.spider_opened)
        return s

    def process_spider_input(self, response, spider):
        # Called for each response that goes through the spider middleware.
        return None

    def process_spider_output(self, response, result, spider):
        # Called with the results returned from the Spider.
        for i in result:
            yield i

    def process_spider_exception(self, response, exception, spider):
        # Called when an exception is raised during spider processing.
        pass

    def spider_opened(self, spider):
        spider.logger.info('Spider opened: %s' % spider.name)


class EconSchoolDownloaderMiddleware:
    @classmethod
    def from_crawler(cls, crawler):
        # This method is used by Scrapy to create your spiders.
        s = cls()
        crawler.signals.connect(s.spider_opened, signal=signals.spider_opened)
        return s

    def process_request(self, request, spider):
        # Called for each request before it reaches the downloader.
        return None

    def process_response(self, request, response, spider):
        # Called with the response returned from the downloader.
        return response

    def process_exception(self, request, exception, spider):
        # Called when an exception is raised during downloading.
        pass

    def spider_opened(self, spider):
        spider.logger.info('Spider opened: %s' % spider.name)