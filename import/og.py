from time import sleep
import urllib3
from bs4 import BeautifulSoup

def request_data(url):
    http = urllib3.PoolManager()
    html = http.request('GET', url).data
    soup = BeautifulSoup(html, "html.parser")
    og_data = {}
    for meta in soup.find_all("meta"):
        if "property" in meta.attrs and meta.attrs["property"].startswith("og:"):
            og_data[meta.attrs["property"]] = meta.attrs["content"]
    return og_data

def get_og_data(url):
    while True:
        og_data = request_data(url)
        if og_data:
            break
        print("Got empty response. Retrying in 20 seconds ...")
        sleep(20)
    return og_data

if __name__ == "__main__":
    og_data = get_og_data(
        "https://whatdimitrilearned.substack.com/p/2022-11-14")
    print(og_data)
