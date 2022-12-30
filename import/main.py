import ask_embeddings

import argparse
import json
import pickle
import os

from .nakedlibrary import NakedLibraryImporter
from .substack import SubstackImporter

IMPORTERS = {
    'library': NakedLibraryImporter(),
    'substack': SubstackImporter()
}

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

for id, chunk in importer.get_chunks(filename, result, max_lines).items():
    text = chunk.get('text', '')
    if 'embedding' not in chunk:
        chunk['embedding'] = ask_embeddings.get_embedding(text)
    if 'token_count' not in chunk:
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
