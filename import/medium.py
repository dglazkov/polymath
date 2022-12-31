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


    def extract_image_url_from_soup(self, soup : BeautifulSoup):
        img = soup.find('img', class_='graf-image')
        if not img:
            return ''
        return img.get('src')


    def extract_title_from_soup(self, soup : BeautifulSoup):
        h1 = soup.find('h1', class_='p-name')
        return h1.get_text(strip=True) if h1 else ''


    def extract_description_from_soup(self, soup: BeautifulSoup):
        section = soup.find('section', class_='p-summary')
        # TODO: if no section, then return the first paragraph of the file
        return section.get_text(strip=True) if section else ''


    def extract_slug_from_filename(self, base_filename):
        base, _ = os.path.splitext(base_filename)
        return base.split('-')[-1]


    def extract_chunks_from_soup(self, soup: BeautifulSoup):
        body = soup.find('section', class_='e-content')
        ps = body.find_all('p')
        text = [p.get_text(strip=True) for p in ps]
        return [item for item in text if len(item) > 50]


    def get_chunks(self, filename):
        filenames = glob.glob(f"{filename}/posts/*.html")
        for file in filenames:
            with open(file, 'r') as f:
                base_filename = os.path.basename(file)
                soup = BeautifulSoup(f, "html.parser")
                url = self.extract_url_from_soup(base_filename, soup)
                image_url = self.extract_image_url_from_soup(soup)
                title = self.extract_title_from_soup(soup)
                description = self.extract_description_from_soup(soup)
                slug = self.extract_slug_from_filename(base_filename)
                info = {
                    'url': url,
                    'image_url': image_url,
                    'title': title,
                    'description': description
                }
                count = 0
                for chunk in self.extract_chunks_from_soup(soup):
                    yield (f"{slug}_{count}", {
                        "text": chunk,
                        "info": info
                    })
                    count += 1
