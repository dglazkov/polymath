import glob
import json
import re
from .og import get_og_data
import urllib3
from bs4 import BeautifulSoup
from typing import Tuple
from argparse import (ArgumentParser, Namespace)

HEADERS = ["h1", "h2", "h3", "h4", "h5", "h6"]

def get_issue_slug(file_name: str) -> str:
    match = re.search(r"(?<=\.)[^.]*(?=\.)", file_name)
    if match:
        return match.group()
    return None


def get_substack_name(substack_url: str) -> str:
    parsed_url = urllib3.util.parse_url(substack_url)
    host = parsed_url.host or ''
    return host.replace(".", "-")


def get_issue_info(substack_url, issue_slug: str) -> Tuple[str, str, str, str]:
    """"
    Returns issue metadata as a dict following the `info` format,
    specified in https://github.com/dglazkov/polymath/blob/main/format.md

    Because of the way Substack exports work, we have to go back
    and fetch each issue's metadata from the Substack site.

    This will cause Substack to rate limit us, so this import may
    take a long time.
    """
    url = f"{substack_url}/p/{issue_slug}"
    og_data = get_og_data(url)
    return {
        "url": url,
        "image_url": og_data.get("og:image"),
        "title": og_data.get("og:title"),
        "description": og_data.get("og:description")
    }


class SubstackImporter:
    def __init__(self):
        self._substack_url = None

    def install_arguments(self, parser: ArgumentParser):
        """
        An opportunity to install arguments on the parser.

        Arguments should be in a new group, start with a `--{importer_name}-`
        and have a default.
        """
        substack_group = parser.add_argument_group('substack')
        substack_group.add_argument(
            '--substack-url', help='If importer type is substack, this url is required. Example: https://read.fluxcollective.org', default='')

    def retrieve_arguments(self, args: Namespace):
        """
        An opportunity to retrieve arguments configured via install_arguments.
        """
        self._substack_url = args.substack_url
        if not self._substack_url:
            raise Exception('--substack-url is required')

    def output_base_filename(self, _) -> str:
        return self._substack_url.replace('https://', '').replace('http://', '').replace('.', '_')

    def get_chunks(self, filename: str):
        filenames = glob.glob(f"{filename}/posts/*.html")
        for file in filenames:
            issue_slug = get_issue_slug(file)
            issue_info = get_issue_info(self._substack_url, issue_slug)
            with open(file, 'r') as file:
                soup = BeautifulSoup(file, "html.parser")
                for id, sibling in enumerate(soup.children):
                    yield (f"{issue_slug}-{id}", {
                        "text": sibling.get_text(" ", strip=True),
                        "info": issue_info
                    })


def get_sections(filename: str, exclude: list):
    with open(filename, 'r') as file:
        soup = BeautifulSoup(file, "html.parser")
        section_content = []
        for sibling in soup.children:
            text = sibling.get_text(" ", strip=True)
            if any(item in text for item in exclude):
                continue
            if sibling.name in HEADERS:
                if section_content:
                    yield "\n".join(section_content)
                section_content = []
            section_content.append(text)
        if section_content:
            yield "\n".join(section_content)


def get_pages(filename: str, config: dict):
    page_filenames = glob.glob(f"{filename}/posts/*.html")
    for id, page_filename in enumerate(page_filenames):
        print(f"Processing \"{page_filename}\"")
        issue_slug = get_issue_slug(page_filename)
        issue_info = get_issue_info(config["substack_url"], issue_slug)
        yield (f"{issue_slug}", {
            "text": list(get_sections(page_filename, config["exclude"])),
            "page_info": issue_info
        })


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument(
        "path", help="Path to the directory containing the Substack export")
    parser.add_argument(
        '--output', help='Filename of where the output goes"', required=True)
    args = parser.parse_args()

    config = json.load(open(f"{args.path}/config.json"))

    pages = list(get_pages(args.path, config))
    json.dump(pages, open(args.output, "w"), indent="\t")
