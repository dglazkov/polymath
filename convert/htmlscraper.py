import requests

from bs4 import BeautifulSoup
from urllib.parse import urlparse

from .chunker import generate_chunks

"""
An importer that goes through a file with simple knowledge

## Usage

% python3 -m convert.main --importer htmlscraper https://almaer.com/dion/cv/

## Future tasks

Why stop at one URL? Follow away!
"""
class HTMLScraperImporter:

    def output_base_filename(self, url):
        url_parts = urlparse(url)
        path = url_parts.path.replace('/', '-')
        return 'html-%s%s' % (url_parts.hostname, path)
       
    def get_chunks(self, url):
        r = requests.get(url)

        soup = BeautifulSoup(r.text, "html.parser")

        info = {
            'url': url
        }

        title = soup.find("title").text
        if title:
            info['title'] = title
        
        meta = soup.find("meta", attrs={"name": "description"})
        if meta and meta["content"]:
            info['description'] = meta["content"]

        body = soup.find('body').get_text()

        for chunk in generate_chunks([body.split('\n')]):
            yield {
                "text": chunk,
                "info": info
            }
