import glob
import json
import os
import re
from .og import get_og_data
import urllib3
from bs4 import BeautifulSoup
from typing import Tuple

SUBSTACK_URL = os.environ.get("SUBSTACK_URL", '')

def get_issue_slug(file_name: str) -> str:
    match = re.search(r"(?<=\.)[^.]*(?=\.)", file_name)
    if match:
        return match.group()
    return None


def get_substack_name(substack_url: str) -> str:
    parsed_url = urllib3.util.parse_url(substack_url)
    host = parsed_url.host or ''
    return host.replace(".", "-")


def strip_emoji(text: str) -> str:
    """
    Removes all emojis from a string."""
    emoji_pattern = re.compile("["
                               u"\U0001F600-\U0001F64F"  # emoticons
                               u"\U0001F300-\U0001F5FF"  # symbols & pictographs
                               u"\U0001F680-\U0001F6FF"  # transport & map symbols
                               u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
                               "]+", flags=re.UNICODE)
    return emoji_pattern.sub(r'', text)


class SubstackImporter:
    def __init__(self, substack_url: str = SUBSTACK_URL):
        self.substack_url = substack_url
        self.substack_name = get_substack_name(substack_url)

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

    def get_filenames(self, path: str) -> list:
        return glob.glob(f"{path}/posts/*.html")

    def output_base_filename(self, _):
        return self.substack_name

    def get_chunks(self, filename, existing_library, max_lines=-1):
        issue_slug = get_issue_slug(filename)
        issue_info = self.get_issue_info(issue_slug)
        result = {}
        with open(filename, 'r') as file:
            soup = BeautifulSoup(file, "html.parser")
            for id, sibling in enumerate(soup.children):
                result["content"][f"{issue_slug}-{id}"] = {
                    "text": strip_emoji(sibling.get_text(" ", strip=True)),
                    "info": issue_info
                }
        return result
