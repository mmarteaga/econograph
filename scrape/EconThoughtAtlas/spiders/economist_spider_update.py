import scrapy
import re
from urllib.parse import unquote
import time

class EconomistSpider(scrapy.Spider):
    name = "economists_v2"
    allowed_domains = ["en.wikipedia.org"]
    start_urls = ['https://en.wikipedia.org/wiki/List_of_economists']

    def parse(self, response):
    # Focus on the <div class="div-col"> portion that has only the alphabetical list
        for link in response.css('div.div-col li a[href^="/wiki/"]::attr(href)').getall():
            url = response.urljoin(link)
            # Avoid links that are likely categories, topics, etc.
            if not any(skip in url for skip in [
            "List_of_", "Category:", "Economics", "Nobel", "School", "Index", "Template:", "File:"
        ]):
                yield scrapy.Request(url, callback=self.parse_economist)

    def parse_economist(self, response):
        data = {}
        data['url'] = response.url
        data['name'] = self.parse_name(response)
        data['born'] = self.parse_born(response)
        data['died'] = self.parse_died(response)
        data['alma_mater'] = self.parse_alma_mater(response)
        data['education'] = self.parse_education(response)
        data['influences'] = self.parse_influences(response)
        data['notable_ideas'] = self.parse_notable_ideas(response)
        data['contributions'] = self.parse_contributions(response)
        data['doctoral_advisors'] = self.parse_doctoral_advisors(response)
        data['doctoral_students'] = self.parse_doctoral_students(response)
        data['image_url'] = self.parse_image_url(response)

        yield data

    def parse_name(self, response):
        # Attempt to extract name from the infobox
        name = response.css('table.infobox.biography.vcard .fn::text').get()
        # Fallback to extracting the name from the page title
        if not name:
            name = response.css('h1#firstHeading span.mw-page-title-main::text').get()
        # Fallback to the URL if other methods fail
        if not name:
            name = response.url.split("/")[-1].replace("_", " ")
        return name

    def parse_born(self, response):
        # Extract the birth date from the infobox
        born = response.css('table.infobox.biography.vcard .bday::text').get()
        if not born:
            born_text = response.xpath('//th[contains(text(), "Born")]/following-sibling::td').xpath('string()').get()
            if born_text:
                born_match = re.search(r'\d{4}(-\d{2}-\d{2})?', born_text)
                if born_match:
                    born = born_match.group()
        return born

    def parse_died(self, response):
        # Extract the death date from the infobox
        died = response.xpath('//th[contains(text(), "Died")]/following-sibling::td//span[contains(@style, "display:none")]/text()').get()
        if not died:
            died_text = response.xpath('//th[contains(text(), "Died")]/following-sibling::td').xpath('string()').get()
            if died_text:
                died_match = re.search(r'\d{4}(-\d{2}-\d{2})?', died_text)
                if died_match:
                    died = died_match.group()
        return died

    def parse_alma_mater(self, response):
        # Extract alma mater information
        alma_mater = response.xpath('//th[contains(text(), "Alma mater")]/following-sibling::td//a/text()').extract()
        if not alma_mater:
            alma_mater = response.xpath('//th[contains(., "Alma") and contains(., "mater")]/following-sibling::td//a/text()').extract()
        return alma_mater or []  # Always return a list

    def parse_education(self, response):
        # Extract education information
        education = response.xpath('//th[contains(text(), "Education")]/following-sibling::td//a/text()').extract()
        if not education:
            education = response.xpath('//th[contains(., "Education")]/following-sibling::td//a/text()').extract()
        return education or []  # Always return a list

    def parse_influences(self, response):
        # Extract influences information
        influences = response.xpath('//th[contains(text(), "Influences")]/following-sibling::td//a/text()').extract()
        if not influences:
            influences = response.xpath('//th[contains(., "Influences")]/following-sibling::td//a/text()').extract()
        return influences or []  # Always return a list

    def parse_notable_ideas(self, response):
        # Extract notable ideas information
        notable_ideas = response.xpath('//th[contains(text(), "Notable ideas")]/following-sibling::td//a/text()').extract()
        if not notable_ideas:
            notable_ideas = response.xpath('//th[contains(., "Notable") and contains(., "idea")]/following-sibling::td//a/text()').extract()
        return notable_ideas or []

    def parse_contributions(self, response):
        # Extract contributions information
        contributions = response.xpath('//th[contains(text(), "Contributions")]/following-sibling::td//a/text()').extract()
        if not contributions:
            contributions = response.xpath('//th[contains(., "Contributions")]/following-sibling::td//a/text()').extract()
        return contributions or []

    def parse_doctoral_advisors(self, response):
        # Extract doctoral advisors information
        doctoral_advisors = response.xpath('//th[contains(text(), "Doctoral advisor")]/following-sibling::td//a/text()').extract()
        if not doctoral_advisors:
            doctoral_advisors = response.xpath('//th[contains(., "Doctoral") and contains(., "advisor")]/following-sibling::td//a/text()').extract()
        return doctoral_advisors or []

    def parse_doctoral_students(self, response):
        # Extract doctoral students information
        doctoral_students = response.xpath('//th[contains(text(), "Doctoral students")]/following-sibling::td//a/text()').extract()
        if not doctoral_students:
            doctoral_students = response.xpath('//th[contains(., "Doctoral") and contains(., "students")]/following-sibling::td//a/text()').extract()
        return doctoral_students or []

    def parse_image_url(self, response):
        # Extract the image URL
        image_url = response.css('table.infobox.biography.vcard img::attr(src)').get()
        if image_url:
            image_url = response.urljoin(image_url)
        return image_url or []

