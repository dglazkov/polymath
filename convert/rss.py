import glob
import os

import feedparser

from argparse import ArgumentParser, Namespace

from bs4 import BeautifulSoup
from urllib.parse import urlparse

from .chunker import generate_chunks

class RSSImporter:

    def output_base_filename(self, filename):
        url = urlparse(filename)
        path = url.path.replace('/', '-')
        return 'rss-%s%s' % (url.hostname, path)
       
    def get_chunks(self, filename):
        feed = feedparser.parse(filename)

        for entry in feed.entries:
            title = entry.title
            content = entry.content[0] # hacking
            url = entry.link
            info = {
                'url': url,
                'title': title
            }

            text = content.value
            
            if content.type == 'text/html':
                soup = BeautifulSoup(content.value, "html.parser")
                ps = soup.find_all('p')
                text = [p.get_text(" ", strip=True) for p in ps]

            for chunk in generate_chunks([text]):
                yield {
                    "text": chunk,
                    "info": info
                }
