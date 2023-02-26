import glob
import re
import frontmatter

from argparse import ArgumentParser, Namespace
from urllib.parse import urlparse
from .chunker import generate_chunks
from .markdown2text import unmark
from overrides import override

from .base import BaseImporter, GetChunksResult

"""
Usage: python3 -m convert.main --importer markdown ~/[folder with markdown files]/ --markdown-base-url https://example.com/
"""
class MarkdownImporter(BaseImporter):

    def __init__(self):
        self._base_url = 'https://example.com/'

    def url_from_slug(self, slug):
        return self._base_url + slug

    @override
    def install_arguments(self, parser: ArgumentParser):
        """
        An opportunity to install arguments on the parser.

        Arguments should be in a new group, start with a `--{importer_name}-`
        and have a default.
        """
        markdown_group = parser.add_argument_group('markdown')
        markdown_group.add_argument('--markdown-base-url', help='The base URL that slugs will be appended to')

    @override
    def retrieve_arguments(self, args: Namespace):
        """
        An opportunity to retrieve arguments configured via install_arguments.
        """
        self._base_url = args.markdown_base_url

    @override
    def output_base_filename(self, filename) -> str:
        url = urlparse(self._base_url)
        path = url.path.replace('/', '-')
        return 'markdown-%s%s' % (url.hostname, path)

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

    @override
    def get_chunks(self, filename) -> GetChunksResult:
        filenames = glob.glob(f"{filename}/**/*.md", recursive=True) + glob.glob(f"{filename}/**/*.markdown", recursive=True)
        # print("Number of files:", len(filenames))
        for file in filenames:
            page = frontmatter.load(file)
            slug = page.get('slug')
            title = page.get('title')

            if page.content and title and slug and len(page.content) < 40000:
                # print(len(page.content))
                # print(slug)
                # print(title)
                # print(unmark(page.content))

                info = {
                    'url': self.url_from_slug(slug),
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