import glob
import os
from bs4 import BeautifulSoup


class MediumImporter:
    def output_base_filename(self, filename):
        profile_path = f"{filename}/profile/profile.html"
        with open(profile_path, "r") as f:
            soup = BeautifulSoup(f, "html.parser")
            ele = soup.find('a', class_='u-url')
            username = ele.get_text(strip=True)
            return username.replace('@','')


    def extract_url_from_soup(self, base_filename : str, soup : BeautifulSoup):
        if (base_filename.startswith('draft_')):
            footer = soup.find('footer')
            ele = footer.find('a')
        else:
            ele = soup.find('a', class_='p-canonical')
        return ele.get('href')


    def get_chunks(self, filename):
        filenames = glob.glob(f"{filename}/posts/*.html")
        for file in filenames:
            with open(file, 'r') as f:
                base_filename = os.path.basename(file)
                soup = BeautifulSoup(f, "html.parser")
                url = self.extract_url_from_soup(base_filename, soup)
                print(url)
        print('Actual importing not yet implemented')
