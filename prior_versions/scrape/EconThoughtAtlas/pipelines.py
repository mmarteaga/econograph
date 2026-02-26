import json

class EconThoughtAtlasPipeline:
    """
    Pipeline to export scraped economist data into a UTF-8 encoded JSON file.
    The file is written incrementally as items are scraped.
    """
    def __init__(self):
        self.items = []

    def process_item(self, item, spider):
        self.items.append(dict(item))
        return item

    def close_spider(self, spider):
        with open("economists_v2.json", "w", encoding="utf-8") as f:
            json.dump(self.items, f, ensure_ascii=False, indent=2)