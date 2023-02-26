from bs4 import BeautifulSoup
from .chunker import generate_chunks

import wpparser

from overrides import override

from .base import BaseImporter, GetChunksResult

"""
An importer that goes through your downloaded WordPress archive.

[How to get your archive](https://wordpress.com/support/export/)

## Usage

% python3 -m convert.main --importer wordpress ~/Downloads/exports/dionalmaer.WordPress.2023-01-14.xml
"""
class WordPressArchiveImporter(BaseImporter):

    @override
    def output_base_filename(self, filename) -> str:
        return 'wordpress'

    @override
    def get_chunks(self, filename) -> GetChunksResult:
        # print(filename)

        data = wpparser.parse(filename)

        for post in data['posts']:
            # print(post)

            info = {
                'url': post['link'],
            }

            title = post['title']
            if title:
                info['title'] = title

            description = post['description']
            if description:
                info['description'] = description

            content = post['content']
            if content:
                extraTags = ""
                tags = post['tags']
                if tags and isinstance(tags, list):
                    readable_tags = [tag.replace('-', ' ') for tag in tags]
                    extraTags = ', '.join(readable_tags)
                    content += "\n" + extraTags                

                soup = BeautifulSoup(post['content'], 'html.parser')
                ps = soup.find_all('p')
                text = [p.get_text(' ', strip=True) for p in ps]

                for chunk in generate_chunks([text]):
                    yield {
                        "text": chunk,
                        "info": info
                    }
