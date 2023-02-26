import os
import re
import urllib.parse

from .chunker import generate_chunks

from overrides import override

from .base import BaseImporter, GetChunksResult

def google_url(title):
    return "https://www.google.com/search?q=" + urllib.parse.quote(title)


"""
An importer that goes through a file with simple knowledge

The format is just a piece of knowledge / information separated by some "----------" on a newline.

E.g.

```
Question: What is the male name for a duck?
Answer: Drake
--------------------------------------------
Dion is British and was born in Essex
--------------------------------------------
There are two forms of persistent Enterprise JavaBeans (EJB) because Oracle and IBM disagreed and both shipped
```

You can also add metadata before the knowledge to setup the info. They are all optional.

E.g.

```
title: Hydrogen uses Remix!
description: Hydrogen uses Remix for the best online store development

Question: What is the best way to build an online store with Remix?

Answer: We recommend Hydrogen, Shopify's solution that uses the Remix you love at it's core, and then gives you all of the commerce helpers you need.
----------
url: https://remix.run/blog/remixing-react-router

Question: How is Remix related to React Router?

Answer: They are from the same team and they work great together!
```

## Usage

% python3 -m convert.main --importer knowledge ~/Downloads/dions-knowledge.txt

## Future tasks

One broken piece is that there isn't a URL tagged to this as a source.
Would be great to host the content somewhere and link to it.

For now, cheating by using a Google Search URL :)
"""
class KnowledgeImporter(BaseImporter):

    @override
    def output_base_filename(self, filename) -> str:
        file_without_ext = os.path.splitext(os.path.basename(filename))[0]
        return 'knowledge-' + file_without_ext

    @override
    def get_chunks(self, filename) ->  GetChunksResult:
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

                cleanKnowledge = []
                for line in knowledgeLines:
                    if line.startswith("url:"):
                        info["url"] = re.sub(r"url:\s*", "", line)
                    elif line.startswith("title:"):
                        info["title"] = re.sub(r"title:\s*", "", line)
                    elif line.startswith("description:"):
                        info["description"] = re.sub(r"description:\s*", "", line)
                    elif not line.strip():
                        continue
                    else:
                        cleanKnowledge.append(line)

                # print("Knowledge Lines:", cleanKnowledge)
                # print("Info: ", info)
                for chunk in generate_chunks([cleanKnowledge]):
                    # print(chunk)
                    yield {
                        "text": chunk,
                        "info": info
                    }
