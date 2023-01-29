import glob
import os
import re
import frontmatter

from .chunker import generate_chunks
from .markdown2text import unmark

BASE_URL = "https://polaris.shopify.com"
def url_from_filename(basedir, filename):
    # given /base/path/directory/file.md if index.md return /directory, else /director/file
    directory, file = os.path.split(filename)
    directory = re.sub(basedir, '', directory)

    # print("Basedir:", basedir)
    # print("Directory:", directory)

    without_ext = os.path.splitext(file)[0]
    if without_ext == "index":
        without_ext = ""

    return (BASE_URL + directory + "/" + without_ext)


"""
Usage: python3 -m convert.main --importer polaris ~/Projects/polaris/polaris.shopify.com/content/

That is from a clone from https://github.com/shopify/polaris
"""
class PolarisImporter:

    def output_base_filename(self, filename):
        return 'polaris'

    def extract_chunks_from_markdown(self, markdownText):
        # print(markdownText)

        markdownText = re.sub(r'<br/>', '', markdownText)
        markdownText = re.sub(r'<!--.*?-->', '', markdownText)

        text = markdownText.split("\n\n")

        return generate_chunks([text])

    def get_chunks(self, filename):
        filenames = glob.glob(f"{filename}/**/*.md", recursive=True)
        # print("Number of files:", len(filenames))
        for file in filenames:
            # print("File: ", file)

            page = frontmatter.load(file)

            if page.content:
                # print("URL:", url_from_filename(filename, file))
                # print(page.content)
                # print(page.get('title'))
                # print(page.get('description'))
                # print(self.unmark(page.content))

                info = {
                    'url': url_from_filename(filename, file)
                }

                title = page.get('title')
                if title:
                    info["title"] = title

                description = page.get('description')
                if description:
                    info["description"] = description

                keywords = page.get('keywords')
                if keywords:
                    # print("Keywords: " + ", ".join(keywords))
                    page.content += "\nKeywords: " + ', '.join([str(item) for item in keywords])

                count = 0
                for chunk in self.extract_chunks_from_markdown(unmark(page.content)):
                    # print(chunk)
                    yield {
                        "text": chunk,
                        "info": info
                    }
                    count += 1