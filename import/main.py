import ask_embeddings

import argparse
import json
import pickle
import os
import re

from .nakedlibrary import NakedLibraryImporter
from .substack import SubstackImporter
from .medium import MediumImporter

IMPORTERS = {
    'library': NakedLibraryImporter(),
    'substack': SubstackImporter(),
    'medium': MediumImporter()
}

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


parser = argparse.ArgumentParser()
parser.add_argument('filename', help='The name of the input file to be processed')
parser.add_argument('--importer', help='The importer to use', choices=IMPORTERS.keys(), default='library')
parser.add_argument('--output-format', help='The format to use', choices=['pkl', 'json'], default='json')
parser.add_argument('--output', help=f'The name of the file to store in {ask_embeddings.LIBRARY_DIR}/. If not provided, will default to the input file with a new extension', default='')
parser.add_argument('--base', help='The library file to base the final library on, unless overwrite is true. Defaults to --output if not specified.', default='')
parser.add_argument('--max', help='The number of max lines to process. If negative, will process all.', default=-1, type=int)
parser.add_argument('--overwrite', action='store_true', help='If set, will ignore any existing output and overwrite it instead of incrementally extending it')
args = parser.parse_args()

filename = args.filename
max_lines = args.max
overwrite = args.overwrite
output_filename = args.output
base_filename = args.base
output_format = args.output_format

importer = IMPORTERS[args.importer]

if not output_filename:
    filename_without_extension = importer.output_base_filename(filename)
    output_filename = f'{filename_without_extension}.{output_format}'

full_output_filename = os.path.join(ask_embeddings.LIBRARY_DIR, output_filename)
if not base_filename:
    base_filename = full_output_filename

result = ask_embeddings.empty_library()

if not overwrite and os.path.exists(base_filename):
    print(f'Found {full_output_filename}, loading it as a base to incrementally extend.')
    result = ask_embeddings.load_library(base_filename)

print('Will process ' + ('all' if max_lines < 0 else str(max_lines)) + ' lines')

count = 0

for id, chunk in importer.get_chunks(filename):
    if max_lines >= 0 and count >= max_lines:
        print('Reached max lines')
        break
    if id in result['content']:
        continue
    print(f'Processing new chunk {id} ({count + 1})')
    text = strip_emoji(chunk.get('text', ''))
    if 'embedding' not in chunk:
        print(f'Fetching embedding for {id}')
        chunk['embedding'] = ask_embeddings.base64_from_vector(ask_embeddings.get_embedding(text)).decode("ascii") 
    if 'token_count' not in chunk:
        print(f'Fetching token_count for {id}')
        chunk['token_count'] = ask_embeddings.get_token_count(text)
    result['content'][id] = chunk
    count += 1

print(f'Loaded {count} new lines')

if not os.path.exists(ask_embeddings.LIBRARY_DIR):
    os.mkdir(ask_embeddings.LIBRARY_DIR)

if output_format == 'json':
    with open(full_output_filename, 'w') as f:
        json.dump(result, f, indent='\t')
else:
    with open(full_output_filename, 'wb') as f:
        pickle.dump(result, f)
