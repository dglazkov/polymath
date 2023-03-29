import requests

from bs4 import BeautifulSoup, Tag
from urllib.parse import urlparse

from overrides import override

from .base import BaseImporter, GetChunksResult

from .chunker import generate_chunks

"""
An importer that goes through a file with simple knowledge

## Usage

% python3 -m convert.main --importer htmlscraper https://almaer.com/dion/cv/

## Future tasks

Why stop at one URL? Follow away!
"""
class HTMLScraperImporter(BaseImporter):

    @override
    def output_base_filename(self, filename) -> str:
        url_parts = urlparse(filename)
        path = url_parts.path.replace('/', '-')
        return 'html-%s%s' % (url_parts.hostname, path)
    
    @override
    def get_chunks(self, filename) -> GetChunksResult:
        r = requests.get(filename)

        soup = BeautifulSoup(r.text, "html.parser")

        info = {
            'url': filename
        }

        title_ele = soup.find("title")
        title = title_ele.text if title_ele else ''
        if title:
            info['title'] = title
        
        meta = soup.find("meta", attrs={"name": "description"})
        if meta and isinstance(meta, Tag) and "content" in meta and meta["content"]:
            info['description'] = str(meta["content"])

        body_ele = soup.find('body')
        body = body_ele.get_text() if body_ele else ''

        for chunk in generate_chunks([body.split('\n')]):
            yield {
                "text": chunk,
                "info": info
            }
