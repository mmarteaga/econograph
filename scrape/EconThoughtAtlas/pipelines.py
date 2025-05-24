from scrapy.exporters import JsonItemExporter

class EconThoughtAtlasPipeline:
    """
    Pipeline to export scraped economist data into a UTF-8 encoded JSON file.
    The file is written incrementally as items are scraped.
    """

    def __init__(self):
        self.file = open("economists_v2.json", "wb")
        self.exporter = JsonItemExporter(self.file, encoding="utf-8", ensure_ascii=False)
        self.exporter.start_exporting()

    def close_spider(self, spider):
        self.exporter.finish_exporting()
        self.file.close()

    def process_item(self, item, spider):
        self.exporter.export_item(item)
        return item