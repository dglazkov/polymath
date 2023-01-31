import glob
import os
import re
import frontmatter

from .chunker import generate_chunks
from .markdown2text import unmark

BASE_URL = "https://remix.run/docs/en/v1/"
def url_from_filename(basedir):
    # given /long/path/directory/file.md if index.md return /directory, else /director/file
    directory, file = os.path.split(basedir)
    last = os.path.basename(os.path.normpath(directory))

    without_ext = os.path.splitext(file)[0]
    if without_ext == "index":
        without_ext = ""

    return (BASE_URL + last + "/" + without_ext)


"""
Usage: python3 -m convert.main --importer remix ~/Projects/remix/docs

That is from a clone from https://github.com/remix-run/remix/tree/main/docs
"""
class RemixImporter:

    def output_base_filename(self, directory):
        return 'remix'

    def extract_chunks_from_markdown(self, markdownText):
        # print(markdownText)

        markdownText = re.sub(r'<docs-.*?>(.*?)</docs-.*?>', r'\1', markdownText)
        markdownText = re.sub(r'<docs-.*?>', '', markdownText)
        markdownText = re.sub(r'</docs-.*?>', '', markdownText)

        text = markdownText.split("\n\n")

        return generate_chunks([text])

    def get_chunks(self, directory):
        filenames = glob.glob(f"{directory}/**/*.md", recursive=True)
        # print("Number of files:", len(filenames))
        for file in filenames:
            # print("File: ", file)

            page = frontmatter.load(file)

            if page.content:
                # print(url_from_filename(file))
                # print(page.content)
                # print(page.get('title'))
                # print(page.get('description'))
                # print(self.unmark(page.content))

                info = {
                    'url': url_from_filename(file),
                    'title': page.get('title'),
                }

                description = page.get('description')
                if description:
                    info["description"] = description

                for chunk in self.extract_chunks_from_markdown(unmark(page.content)):
                    # print(chunk)
                    yield {
                        "text": chunk,
                        "info": info
                    }