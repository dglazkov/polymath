import glob
import os
import re
import frontmatter

from .chunker import generate_chunks
from .markdown2text import unmark

BASE_URL = "https://developer.mozilla.org/en-US/docs/"
def url_from_slug(slug):
    return BASE_URL + slug

"""
Usage: python3 -m convert.main --importer mdn ~/Projects/mdn-content/files/en-us/

That is from a clone from https://github.com/mdn/content
"""
class MDNImporter:

    def output_base_filename(self, filename):
        return 'mdn'

    def extract_chunks_from_markdown(self, markdownText):
        # print(markdownText)

        # markdownText = re.sub(r'{{\s+domxref\("[^\"]*",\s+"([^\"]*)"\)\s*}}', r'\1', markdownText)
        # markdownText = re.sub(r'{{\s+HTMLElement\("([^\"]*)"\)\s*}}', r'\1', markdownText)

        markdownText = re.sub(r'{{\s*\w+\(\"(.*?)\"\s*,\s*\"(.*?)\"\)\s*}}', r'\1', markdownText)
        markdownText = re.sub(r'{{\s*\w+\(\"(.*?)\"\)\s*}}', r'\1', markdownText)

        markdownText = re.sub(r"{%[^%]*%}", "", markdownText)
        markdownText = re.sub(r'{{(.*)(\"[^\"]*\")}}', r'\2', markdownText)

        markdownText = re.sub(r'{{.*?}}', '', markdownText)
        markdownText = re.sub(r'<section.*?>.*</section>', '', markdownText)
        
        text = markdownText.split("\n\n")

        return generate_chunks([text])

    def get_chunks(self, filename):
        filenames = glob.glob(f"{filename}/web/**/*.md", recursive=True) + glob.glob(f"{filename}/glossary/**/*.md", recursive=True)
        # print("Number of files:", len(filenames))
        for file in filenames:
            # print(file)

            page = frontmatter.load(file)
            slug = page.get('slug')
            title = page.get('title')

            if page.content and title and slug and len(page.content) < 40000:
                # print(len(page.content))
                # print(slug)
                # print(title)
                # print(unmark(page.content))

                info = {
                    'url': url_from_slug(slug),
                    'title': title
                }

                count = 0
                for chunk in self.extract_chunks_from_markdown(unmark(page.content)):
                    # print(chunk)
                    yield {
                        "text": chunk,
                        "info": info
                    }
                    count += 1