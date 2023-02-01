import requests
from .htmlscraper import HTMLScraperImporter
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from argparse import Namespace


class SitemapImporter(HTMLScraperImporter):
    def __init__(self):
      self._debug = False

    def retrieve_arguments(self, args: Namespace):
        self._debug = args.debug

    def get_chunks(self, filename):
      # Fetch the sitemap (need to validate this is a sitemap)
      r = requests.get(filename)
      soup = BeautifulSoup(r.text, "html.parser")

      # For each URL in the sitemap, fetch the page  
      urlTags = soup.find_all("url")
      for url in urlTags:
        url = url.findNext("loc").text
        print("Fetching %s" % url)

        for chunk in super().get_chunks(url):
          yield chunk
    
    def output_base_filename(self, url):
        url_parts = urlparse(url)
        path = url_parts.path.replace('/', '-')
        return 'sitemap-%s%s' % (url_parts.hostname, path)