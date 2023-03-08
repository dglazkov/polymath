import glob
import os
import re
import frontmatter
from overrides import override

from .base import BaseImporter, GetChunksResult

from .chunker import generate_chunks
from .markdown2text import unmark


BASE_URL = "https://developer.chrome.com/"
def url_from_filename(filename):
    # given /long/path/directory/file.md if index.md return /directory, else /director/file
    directory, file = os.path.split(filename)
    last = os.path.basename(os.path.normpath(directory))

    without_ext = os.path.splitext(file)[0]
    if without_ext == "index":
        without_ext = ""

    return (BASE_URL + last + "/" + without_ext)


"""
Usage: python3 -m convert.main --importer developerdotchrome ~/Projects/dcc/src/site/en

That is from a clone from https://github.com/GoogleChrome/developer.chrome.com
"""
class DeveloperDotChromeImporter(BaseImporter):

    @override
    def output_base_filename(self, filename : str) -> str:
        return 'developerdotchrome'

    def extract_chunks_from_markdown(self, markdownText):
        # print(markdownText)

        markdownText = re.sub(r"{%[^%]*%}", "", markdownText)
        markdownText = re.sub(r"<img src=\"data:image\/jpeg;[^>]+>", "", markdownText)
        text = markdownText.split("\n\n")

        return generate_chunks([text])

    @override
    def get_chunks(self, filename : str) -> GetChunksResult:
        filenames = glob.glob(f"{filename}/**/*.md", recursive=True)
        # print(len(filenames))
        for file in filenames:
            # print(file)

            page = frontmatter.load(file)

            if page.content:
                # print(url_from_filename(file))
                # print(page.content)
                # print(page.get('title'))
                # print(page.get('description'))
                # print(unmark(page.content))

                info = {
                    'url': url_from_filename(file),
                    'title': page.get('title'),
                    'description': page.get('description')
                }

                count = 0
                for chunk in self.extract_chunks_from_markdown(unmark(page.content)):
                    # print(chunk)
                    yield {
                        "text": chunk,
                        "info": info
                    }
                    count += 1