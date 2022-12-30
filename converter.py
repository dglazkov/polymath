import ask_embeddings

import argparse
import json
import sys
import pickle
import os

class NakedLibraryImporter:
    def get_chunks(self, filename, existing_library, max_lines = -1):
        # Will return a dict of chunks, possibly missing embedding and token_count.
        data = ask_embeddings.load_data_file(filename)

        chunks = data.get('content')
        if not chunks:
            raise Exception('Data did not have content as expected')
        count = 0
        total = len(chunks) if max_lines < 0 else max_lines
        result = {}
        for id, chunk in chunks.items():
            if max_lines >= 0 and count >= max_lines:
                print('Reached max lines')
                break
            if id in existing_library['content']:
                continue
            print(f'Processing new chunk {id} ({count + 1}/{total})')
            text = chunk.get('text')
            if not text:
                print('Skipping a row with id ' + id + ' that was missing text')
                continue
            result['content'][id] = {
                    'text': text,
                    'info': chunk.get('info')
            }
            count += 1
        return result
    def output_base_filename(self, input_filename):
        base_filename, file_extension = os.path.splitext(input_filename)
        return base_filename

IMPORTERS = {
    'library': NakedLibraryImporter()
}

parser = argparse.ArgumentParser()
parser.add_argument('filename', help='The name of the input file to be processed')
parser.add_argument('--format', help='The format to use', choices=['pkl', 'json'], default='pkl')
parser.add_argument('--output', help=f'The name of the file to store in {ask_embeddings.LIBRARY_DIR}/. If not provided, will default to the input file with a new extension', default='')
parser.add_argument('--max', help='The number of max lines to process. If negative, will process all.', default=-1, type=int)
parser.add_argument('--overwrite', action='store_true', help='If set, will ignore any existing output and overwrite it instead of incrementally extending it')
args = parser.parse_args()

filename = args.filename
max_lines = args.max
overwrite = args.overwrite
output_filename = args.output
output_format = args.format

#TODO: allow selecting a different one via an argument.
importer = IMPORTERS['library']

if not output_filename:
    base_filename = importer.output_base_filename(filename)
    output_filename = f'{base_filename}.{output_format}'

full_output_filename = os.path.join(ask_embeddings.LIBRARY_DIR, output_filename)

result = ask_embeddings.empty_library()

if not overwrite and os.path.exists(full_output_filename):
    print(f'Found {full_output_filename}, loading it as a base to incrementally extend.')
    result = ask_embeddings.load_library(full_output_filename)

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
