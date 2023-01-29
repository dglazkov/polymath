import glob
import os
import re
import frontmatter

from .chunker import generate_chunks
from .markdown2text import unmark

BASE_URL = "https://preactjs.com/"
def url_from_filename(filename):
    # given /long/path/directory/file.md if index.md return /directory, else /director/file
    directory, file = os.path.split(filename)
    last = os.path.basename(os.path.normpath(directory))

    without_ext = os.path.splitext(file)[0]
    if without_ext == "index":
        without_ext = ""

    return (BASE_URL + last + "/" + without_ext)


"""
Usage: python3 -m convert.main --importer preact ~/Projects/preact-www/content/en

That is from a clone from https://github.com/preactjs/preact-www
"""
class PreactImporter:

    def output_base_filename(self, filename):
        return 'preact'

    def extract_chunks_from_markdown(self, markdownText):
        # print(markdownText)

        markdownText = re.sub(r'<docs-.*?>(.*?)</docs-.*?>', r'\1', markdownText)
        markdownText = re.sub(r'<docs-.*?>', '', markdownText)
        markdownText = re.sub(r'<div><toc></toc></div>', '', markdownText)

        text = markdownText.split("\n\n")

        return generate_chunks([text])

    def get_chunks(self, filename):
        filenames = glob.glob(f"{filename}/**/*.md", recursive=True)
        # print("Number of files:", len(filenames))
        for file in filenames:
            # print("File: ", file)

            if "/v8/" in file or "404.md" in file or "branding.md" in file or "blog.md" in file:
                continue

            page = frontmatter.load(file)

            if page.content:
                # print(url_from_filename(file))
                # print(page.content)
                # print(page.get('title'))
                # print(page.get('description'))
                # print(self.unmark(page.content))

                info = {
                    'url': url_from_filename(file),
                    'title': page.get('name'),
                }

                description = page.get('description')
                if description:
                    info["description"] = description

                count = 0
                for chunk in self.extract_chunks_from_markdown(unmark(page.content)):
                    # print(chunk)
                    yield {
                        "text": chunk,
                        "info": info
                    }
                    count += 1