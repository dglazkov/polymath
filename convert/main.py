import argparse
import os
import re

import openai
from dotenv import load_dotenv

from polymath import LIBRARY_DIR, Library, get_embedding, get_token_count

from .medium import MediumImporter
from .nakedlibrary import NakedLibraryImporter
from .substack import SubstackImporter
from .twitter import TwitterArchiveImporter

IMPORTERS = {
    'library': NakedLibraryImporter(),
    'substack': SubstackImporter(),
    'medium': MediumImporter(),
    'twitter': TwitterArchiveImporter(),
}

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")


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
parser.add_argument(
    'filename', help='The name of the input file to be processed')
parser.add_argument('--importer', help='The importer to use',
                    choices=IMPORTERS.keys(), default='library')
parser.add_argument(
    '--output', help=f'The name of the file to store in {LIBRARY_DIR}/. If not provided, will default to the input file with a new extension', default='')
parser.add_argument(
    '--base', help='The library file to base the final library on, unless overwrite is true. Defaults to --output if not specified.', default='')
parser.add_argument(
    '--max', help='The number of max lines to process. If negative, will process all.', default=-1, type=int)
parser.add_argument('--overwrite', action='store_true',
                    help='If set, will ignore any existing output and overwrite it instead of incrementally extending it')
parser.add_argument('--truncate', action='store_true',
                    help='If set, will only persist things to output from base that also had their ID in input')
for importer in IMPORTERS.values():
    if 'install_arguments' in dir(importer):
        importer.install_arguments(parser)
args = parser.parse_args()

filename = args.filename
max_lines = args.max
overwrite = args.overwrite
output_filename = args.output
base_filename = args.base
truncate = args.truncate

importer = IMPORTERS[args.importer]

if 'retrieve_arguments' in dir(importer):
    importer.retrieve_arguments(args)

if not output_filename:
    filename_without_extension = importer.output_base_filename(filename)
    output_filename = f'{filename_without_extension}.json'

full_output_filename = os.path.join(
    LIBRARY_DIR, output_filename)
if not base_filename:
    base_filename = full_output_filename

result = Library()

if not overwrite and os.path.exists(base_filename):
    print(
        f'Found {full_output_filename}, loading it as a base to incrementally extend.')
    result = Library(filename=base_filename)

print('Will process ' + ('all' if max_lines < 0 else str(max_lines)) + ' lines')

count = 0

seen_ids = {}

for id, chunk in importer.get_chunks(filename):
    seen_ids[id] = True
    if max_lines >= 0 and count >= max_lines:
        print('Reached max lines')
        break
    if result.chunk(id):
        continue
    print(f'Processing new chunk {id} ({count + 1})')
    text = strip_emoji(chunk.get('text', ''))
    if 'embedding' not in chunk:
        print(f'Fetching embedding for {id}')
        chunk['embedding'] = get_embedding(text)
    if 'token_count' not in chunk:
        print(f'Fetching token_count for {id}')
        chunk['token_count'] = get_token_count(text)
    result.set_chunk(id, chunk)
    count += 1

print(f'Loaded {count} new lines')

if truncate:
    for chunk_id in [id for id in result.chunk_ids]:
        if chunk_id in seen_ids:
            continue
        result.delete_chunk(chunk_id)

if not os.path.exists(LIBRARY_DIR):
    os.mkdir(LIBRARY_DIR)

result.save(full_output_filename)
