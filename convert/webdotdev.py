import glob
import os
import re
import frontmatter

from io import StringIO
from markdown import Markdown
from argparse import ArgumentParser, Namespace
from .chunker import generate_chunks

def unmark_element(element, stream=None):
    if stream is None:
        stream = StringIO()
    if element.text:
        stream.write(element.text)
    for sub in element:
        unmark_element(sub, stream)
    if element.tail:
        stream.write(element.tail)
    return stream.getvalue()

def unmark(text):
    return __md.convert(text)

# patching Markdown
Markdown.output_formats["plain"] = unmark_element
__md = Markdown(output_format="plain")
__md.stripTopLevelTags = False

BASE_URL = "http://web.dev/"
def url_from_filename(filename):
    # given /long/path/directory/file.md if index.md return /directory, else /director/file
    directory, file = os.path.split(filename)
    last = os.path.basename(os.path.normpath(directory))

    without_ext = os.path.splitext(file)[0]
    if without_ext == "index":
        without_ext = ""

    return (BASE_URL + last + "/" + without_ext)


"""
pass in the filename that's the root directory of English content:

~/Projects/web.dev/src/site/content/en

"""
class WebDotDevImporter:

    def __init__(self):
        self.unmark = unmark

    def output_base_filename(self, filename):
        return 'webdotdev'

    def extract_chunks_from_markdown(self, markdownText):
        # print(markdownText)

        markdownText = re.sub(r"{%[^%]*%}", "", markdownText)
        text = markdownText.split("\n\n")

        return generate_chunks([text])

    def get_chunks(self, filename):
        filenames = glob.glob(f"{filename}/**/*.md", recursive=True)
        print(len(filenames))
        for file in filenames:
            # print(file)

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
                    'description': page.get('description')
                }

                count = 0
                for chunk in self.extract_chunks_from_markdown(self.unmark(page.content)):
                    # print(chunk)
                    yield {
                        "text": chunk,
                        "info": info
                    }
                    count += 1