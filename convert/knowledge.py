import re
import urllib.parse

from .chunker import generate_chunks

def google_url(title):
    return "https://www.google.com/search?q=" + urllib.parse.quote(title)


"""
An importer that goes through a file with simple knowledge

The format is just a piece of knowledge / information separated by some "----------" on a newline.

E.g.

Question: What is the male name for a duck?
Answer: Drake
--------------------------------------------
Dion is British and was born in Essex
--------------------------------------------
There are two forms of persistent Enterprise JavaBeans (EJB) because Oracle and IBM disagreed and both shipped

## Usage

% python3 -m convert.main --importer knowledge ~/Downloads/dions-knowledge.txt

## Future tasks

One broken piece is that there isn't a URL tagged to this as a source.
Would be great to host the content somewhere and link to it.

For now, cheating by using a Google Search URL :)
"""
class KnowledgeImporter:

    def output_base_filename(self, filename):
        return 'knowledge'

    def get_chunks(self, filename):
        # print("File: ", filename)

        with open(filename, "r") as file:
            chunks = re.split(r'\n-----[-]+\n', file.read())
            for knowledge in chunks:
                # print("Knowledge:", knowledge)

                knowledgeLines = knowledge.split('\n')

                title = knowledgeLines[0]

                info = {
                    'url': google_url(title),
                    'title': title
                }

                for chunk in generate_chunks([knowledgeLines]):
                    # print(chunk)
                    yield {
                        "text": chunk,
                        "info": info
                    }
