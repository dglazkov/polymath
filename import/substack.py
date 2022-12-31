import glob
import json
import os
import re
from .og import get_og_data
import urllib3
from bs4 import BeautifulSoup
from typing import Tuple


def get_issue_slug(file_name: str) -> str:
    match = re.search(r"(?<=\.)[^.]*(?=\.)", file_name)
    if match:
        return match.group()
    return None


def get_substack_name(substack_url: str) -> str:
    parsed_url = urllib3.util.parse_url(substack_url)
    host = parsed_url.host or ''
    return host.replace(".", "-")


class SubstackImporter:
    def __init__(self):
        self.substack_url = None
        self._output_base_filename = None

    def initialize(self, filename):
        config = json.load(open(f"{filename}/config.json"))
        self.substack_url = config["substack_url"]
        if not self.substack_url:
            raise ValueError("Substack URL not found in config.json")
        self._output_base_filename = config["output_base_filename"]
        if not self._output_base_filename:
            raise ValueError(
                "Output base filename not found in config.json")

    def get_issue_info(self, issue_slug: str) -> Tuple[str, str, str, str]:
        """"
        Returns issue metadata as a dict following the `info` format,
        specified in https://github.com/dglazkov/polymath/blob/main/format.md

        Because of the way Substack exports work, we have to go back
        and fetch each issue's metadata from the Substack site.

        This will cause Substack to rate limit us, so this import may
        take a long time.
        """
        url = f"{self.substack_url}/p/{issue_slug}"
        og_data = get_og_data(url)
        return {
            "url": url,
            "image_url": og_data.get("og:image"),
            "title": og_data.get("og:title"),
            "description": og_data.get("og:description")
        }

    def output_base_filename(self, _) -> str:
        return self._output_base_filename

    def get_chunks(self, filename: str):
        filenames = glob.glob(f"{filename}/posts/*.html")
        for file in filenames:
            issue_slug = get_issue_slug(file)
            issue_info = self.get_issue_info(issue_slug)
            with open(file, 'r') as file:
                soup = BeautifulSoup(file, "html.parser")
                for id, sibling in enumerate(soup.children):
                    yield (f"{issue_slug}-{id}", {
                        "text": sibling.get_text(" ", strip=True),
                        "info": issue_info
                    })
