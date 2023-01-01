import glob
import json
import re
from .og import get_og_data
import urllib3
from bs4 import BeautifulSoup
from typing import Tuple
from argparse import (ArgumentParser, Namespace)

HEADERS = ["h1", "h2", "h3", "h4", "h5", "h6"]
LISTS = ["ul", "ol"]


def get_issue_slug(file_name: str) -> str:
    match = re.search(r"(?<=\.)[^.]*(?=\.)", file_name)
    if match:
        return match.group()
    return None


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


def get_text(node):
    return node.get_text(" ", strip=True)


def get_sections(filename: str, exclude: list):
    with open(filename, 'r') as file:
        soup = BeautifulSoup(file, "html.parser")
        section_content = []
        for sibling in soup.children:
            if sibling.name in LISTS:
                section_content.extend([get_text(item) for item in sibling.children])
            else:
                text = get_text(sibling)
                if not text:
                    continue
                skip = any(item in text for item in exclude)
                if sibling.name in HEADERS:
                    if section_content:
                        yield section_content
                    section_content = [ text ] if not skip else []
                else:
                    if not skip:
                        section_content.append(text)
        if section_content:
            yield section_content


def get_pages(path: str, config: dict):
    """
    Main entry point for the Substack importer.

    Returns a dict of pages. The key is a unique identifier of a page
    and the value is of the following structure structure:
        "sections": list of sections, each section is a list of strings,
        represnting a text chunk
        "info": dict of issue metadata, following the `info` format
        as specified in https://github.com/dglazkov/polymath/blob/main/format.md

    Arguments:
        path {str} -- Path to the directory containing the Substack export
        config {dict} -- Config file from the Substack export

    Format of the config file:
    {
        "substack_url": url of the Substack site,
        "exclude": [
            list of strings to exclude from the import. 
            Each string is a substring of the text to exclude from the import. 
        ]
    }
    """
    page_filenames = glob.glob(f"{path}/posts/*.html")
    result = {}
    for page_filename in page_filenames:
        print(f"Processing \"{page_filename}\"")
        issue_slug = get_issue_slug(page_filename)
        issue_info = get_issue_info(config["substack_url"], issue_slug)
        result[f"{issue_slug}"] = {
            "sections": list(get_sections(page_filename, config["exclude"])),
            "info": issue_info
        }
    return result

if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument(
        "path", help="Path to the directory containing the Substack export")
    parser.add_argument(
        '--output', help='Filename of where the output goes"', required=True)
    args = parser.parse_args()

    config = json.load(open(f"{args.path}/config.json"))

    pages = get_pages(args.path, config)
    print(f"Writing output to {args.output} ...")
    json.dump(pages, open(args.output, "w"), indent="\t")
    print("Done.")
