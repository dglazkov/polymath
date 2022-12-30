import glob
import os
from bs4 import BeautifulSoup


class MediumImporter:
    def get_filenames(self, path: str) -> list:
        return glob.glob(f"{path}/posts/*.html")

    def output_base_filename(self, filename):
        profile_path = f"{filename}/profile/profile.html"
        with open(profile_path, "r") as f:
            soup = BeautifulSoup(f, "html.parser")
            ele = soup.find('a', class_='u-url')
            username = ele.get_text(strip=True)
            return username.replace('@','')

    def get_chunks(self, filename):
        #TODO: implement
        print('This importer is not yet implemented')
        raise StopIteration
