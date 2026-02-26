"""
Economist Spider V3
===================
A clean implementation of the economist data scraper.

This spider crawls Wikipedia's "List of Economists" and extracts:
- Basic info: name, birth/death dates, image
- Intellectual lineage: influences
- Academic lineage: doctoral advisors and students
- Unique identifier: Wikipedia pageid

Key improvements over v2:
- Uses wikipedia library for reliable pageid extraction
- Cleaner data structure
- Better error handling
- Rate limiting to respect Wikipedia's servers
"""

import scrapy
import wikipedia
import re
import time
from datetime import datetime


class EconomistSpiderV3(scrapy.Spider):
    name = "economists_v3"
    allowed_domains = ["en.wikipedia.org"]
    start_urls = ['https://en.wikipedia.org/wiki/List_of_economists']

    # Rate limiting: sleep between requests to be respectful
    custom_settings = {
        'DOWNLOAD_DELAY': 1,  # 1 second between requests
        'CONCURRENT_REQUESTS': 1,  # Process one at a time
    }

    def __init__(self, *args, **kwargs):
        super(EconomistSpiderV3, self).__init__(*args, **kwargs)
        # Set wikipedia library language
        wikipedia.set_lang("en")
        self.processed_urls = set()  # Avoid duplicates

    def parse(self, response):
        """
        Parse the main "List of Economists" page.
        Extract links to individual economist pages.
        """
        self.log(f"Parsing list page: {response.url}")

        # Focus on the alphabetical list in div-col sections
        links = response.css('div.div-col li a[href^="/wiki/"]::attr(href)').getall()

        self.log(f"Found {len(links)} potential economist links")

        for link in links:
            url = response.urljoin(link)

            # Skip non-person pages (categories, lists, etc.)
            skip_keywords = [
                "List_of_", "Category:", "Economics", "Nobel", "School",
                "Index", "Template:", "File:", "Portal:", "Wikipedia:", "Help:"
            ]

            if any(keyword in url for keyword in skip_keywords):
                continue

            # Avoid processing the same URL twice
            if url in self.processed_urls:
                continue

            self.processed_urls.add(url)

            # Add a small delay to be respectful to Wikipedia
            time.sleep(0.5)

            yield scrapy.Request(url, callback=self.parse_economist)

    def parse_economist(self, response):
        """
        Parse an individual economist's Wikipedia page.
        Extract biographical and relationship data.
        """
        self.log(f"Parsing economist page: {response.url}")

        # Extract the economist's name from the page title
        name = self.parse_name(response)

        if not name:
            self.log(f"Warning: Could not extract name from {response.url}")
            return

        # Get Wikipedia pageid using the wikipedia library
        pageid = self.get_pageid(name, response.url)

        if not pageid:
            self.log(f"Warning: Could not get pageid for {name}")
            return

        # Build the data dictionary
        data = {
            'pageid': str(pageid),
            'name': name,
            'url': response.url,
            'born': self.parse_born(response),
            'died': self.parse_died(response),
            'influences': self.parse_influences(response),
            'doctoral_advisors': self.parse_doctoral_advisors(response),
            'doctoral_students': self.parse_doctoral_students(response),
            'img': self.parse_image_url(response),
            'school': self.parse_school(response),
            'field': self.parse_field(response),
        }

        self.log(f"Successfully extracted data for {name} (pageid: {pageid})")

        yield data

    def parse_name(self, response):
        """Extract the economist's name from the page."""
        # Try infobox first
        name = response.css('table.infobox .fn::text').get()

        # Fallback to page title
        if not name:
            name = response.css('h1#firstHeading span.mw-page-title-main::text').get()

        # Final fallback to URL
        if not name:
            name = response.url.split("/")[-1].replace("_", " ")

        return name.strip() if name else None

    def get_pageid(self, name, url):
        """
        Get Wikipedia pageid using the wikipedia library.
        This is more reliable than parsing HTML.
        """
        try:
            # Try to get the page directly by name
            page = wikipedia.page(name, auto_suggest=False)
            return page.pageid
        except wikipedia.exceptions.DisambiguationError as e:
            # Multiple pages found, try to pick the right one
            self.log(f"Disambiguation for {name}, trying first option")
            try:
                page = wikipedia.page(e.options[0], auto_suggest=False)
                return page.pageid
            except:
                pass
        except wikipedia.exceptions.PageError:
            # Page doesn't exist with this exact name, try parsing from URL
            self.log(f"PageError for {name}, extracting from URL")
            page_title = url.split("/")[-1].replace("_", " ")
            try:
                page = wikipedia.page(page_title, auto_suggest=False)
                return page.pageid
            except:
                pass
        except Exception as e:
            self.log(f"Error getting pageid for {name}: {e}")

        return None

    def parse_born(self, response):
        """
        Extract and parse birth date.
        Returns Unix timestamp (seconds since 1970, negative for BC).
        """
        # Try the .bday class first (machine-readable date)
        born = response.css('table.infobox .bday::text').get()

        if not born:
            # Try the Born row in the infobox
            born_text = response.xpath(
                '//th[contains(text(), "Born")]/following-sibling::td'
            ).xpath('string()').get()

            if born_text:
                # Extract date with regex (handles YYYY-MM-DD or just YYYY)
                match = re.search(r'(\d{4})(?:-(\d{2})-(\d{2}))?', born_text)
                if match:
                    born = match.group(0)

        # Convert to Unix timestamp
        if born:
            return self.date_to_timestamp(born)

        return None

    def parse_died(self, response):
        """
        Extract and parse death date.
        Returns Unix timestamp (seconds since 1970, negative for BC).
        """
        # Try hidden span first (machine-readable date)
        died = response.xpath(
            '//th[contains(text(), "Died")]/following-sibling::td//span[contains(@style, "display:none")]/text()'
        ).get()

        if not died:
            # Try the Died row in the infobox
            died_text = response.xpath(
                '//th[contains(text(), "Died")]/following-sibling::td'
            ).xpath('string()').get()

            if died_text:
                # Extract date with regex
                match = re.search(r'(\d{4})(?:-(\d{2})-(\d{2}))?', died_text)
                if match:
                    died = match.group(0)

        # Convert to Unix timestamp
        if died:
            return self.date_to_timestamp(died)

        return None

    def date_to_timestamp(self, date_str):
        """
        Convert date string to Unix timestamp.
        Handles formats: YYYY, YYYY-MM-DD
        """
        try:
            # Try full date format first
            if len(date_str) == 10:  # YYYY-MM-DD
                dt = datetime.strptime(date_str, '%Y-%m-%d')
            else:  # Just year
                dt = datetime.strptime(date_str, '%Y')

            # Convert to Unix timestamp (seconds since 1970)
            return int(dt.timestamp())
        except Exception as e:
            self.log(f"Error converting date {date_str}: {e}")
            return None

    def parse_influences(self, response):
        """
        Extract list of people who influenced this economist.
        Returns list of names.
        """
        influences = response.xpath(
            '//th[contains(text(), "Influences")]/following-sibling::td//a/text()'
        ).getall()

        # Clean up the names
        return [name.strip() for name in influences if name.strip()]

    def parse_doctoral_advisors(self, response):
        """
        Extract doctoral advisors.
        Returns list of names.
        """
        advisors = response.xpath(
            '//th[contains(text(), "Doctoral advisor")]/following-sibling::td//a/text()'
        ).getall()

        return [name.strip() for name in advisors if name.strip()]

    def parse_doctoral_students(self, response):
        """
        Extract doctoral students.
        Returns list of names.
        """
        students = response.xpath(
            '//th[contains(text(), "Doctoral students")]/following-sibling::td//a/text()'
        ).getall()

        return [name.strip() for name in students if name.strip()]

    def parse_image_url(self, response):
        """
        Extract the economist's image URL from the infobox.
        Returns full URL or None.
        """
        # Get the image src from the infobox
        image_url = response.css('table.infobox img::attr(src)').get()

        if image_url:
            # Convert to full URL (Wikipedia often uses protocol-relative URLs)
            if image_url.startswith('//'):
                image_url = 'https:' + image_url
            elif image_url.startswith('/'):
                image_url = response.urljoin(image_url)

        return image_url

    def parse_school(self, response):
        """
        Extract the school of thought (e.g., "Austrian School", "Keynesian", etc.)
        from the Wikipedia infobox.
        Returns a list of school names.
        """
        # Try "School" row first (most common label)
        schools = response.xpath(
            '//th[contains(text(), "School")]/following-sibling::td//a/text()'
        ).getall()

        # Also try "School tradition" which some pages use
        if not schools:
            schools = response.xpath(
                '//th[contains(text(), "school") or contains(text(), "tradition")]/following-sibling::td//a/text()'
            ).getall()

        # Clean up the names and filter out non-school items
        cleaned = []
        for school in schools:
            school = school.strip()
            if school and len(school) > 1:
                # Filter out common non-school entries
                skip_terms = ['edit', 'citation', 'verify', '[', ']']
                if not any(term in school.lower() for term in skip_terms):
                    cleaned.append(school)

        return cleaned

    def parse_field(self, response):
        """
        Extract the field/subfield of economics (e.g., "Labor economics", "Monetary economics")
        from the Wikipedia infobox.
        Returns a list of field names.
        """
        # Try "Field" row
        fields = response.xpath(
            '//th[contains(text(), "Field")]/following-sibling::td//a/text()'
        ).getall()

        # Also try "Contributions" which sometimes lists fields
        if not fields:
            fields = response.xpath(
                '//th[contains(text(), "Contribution")]/following-sibling::td//a/text()'
            ).getall()

        # Clean up and filter
        cleaned = []
        for field in fields:
            field = field.strip()
            if field and len(field) > 1:
                # Filter out common non-field entries
                skip_terms = ['edit', 'citation', 'verify', '[', ']', 'university', 'college']
                if not any(term in field.lower() for term in skip_terms):
                    cleaned.append(field)

        return cleaned
