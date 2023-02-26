import urllib.parse

from overrides import override

from .base import BaseImporter, GetChunksResult

from .chunker import generate_chunks

def google_url(title):
    return "https://www.google.com/search?q=" + urllib.parse.quote(title)

def extract_groups(schema):
    groups = []

    # print(schema)
    lines = schema.split('\n')

    tripleCount = 0
    temp = []
    for line in lines:
        # print("Line:", line)
        if line == "":
            continue

        if line.startswith('"""'):
            tripleCount += 1
        
        if tripleCount == 3:
            # print('\n'.join(temp))
            groups.append('\n'.join(temp))
            # print(groups)
            temp = []
            tripleCount = 1
        
        temp.append(line)

    return groups


"""
An importer that takes in a GraphQL Schema

E.g.

------------------------------------------------------------------
\"\"\"
Units of measurement for weight.
\"\"\"
enum WeightUnit {
  ... things ...
}

\"\"\"
Marks an element of a GraphQL schema as having restricted access.
\"\"\"
directive @accessRestricted(
  \"\"\"
  Explains the reason around this restriction
  \"\"\"
  reason: String = null
) on FIELD_DEFINITION | OBJECT
------------------------------------------------------------------

## Usage

% python3 -m convert.main --importer graphqlschema ~/Downloads/graphql-schema.txt
"""
class GraphQLSchemaImporter(BaseImporter):

    @override
    def output_base_filename(self, filename) -> str:
        return 'graphql-schema'

    @override
    def get_chunks(self, filename) -> GetChunksResult:
        # print("File: ", filename)

        with open(filename, "r") as file:
            contents = file.read()
            groups = extract_groups(contents)

            info = {
                'url': google_url(groups[0]),
                'title': "Piece of GraphQL"
            }

            for chunk in generate_chunks([groups]):
                # print(chunk)
                yield {
                    "text": chunk,
                    "info": info
                }

