import ask_embeddings

import argparse
import json
import sys
import pickle
import os

parser = argparse.ArgumentParser()
parser.add_argument('filename', help='The name of the input file to be processed')
parser.add_argument('--output', help='The name of the file to store in {OUTPUT_DIRECTORY}/. If not provided, will default to the input file with a new extension', default='')
parser.add_argument('--max', help='The number of max lines to process. If negative, will process all.', default=-1, type=int)
parser.add_argument('--overwrite', action='store_true', help='If set, will ignore any existing output and overwrite it instead of incrementally extending it')
args = parser.parse_args()

filename = args.filename
max_lines = args.max
overwrite = args.overwrite
output_filename = args.output

OUTPUT_DIRECTORY = 'out'

with open(filename, 'r') as f:
    data = json.load(f)

chunks = data.get('chunks')

if not chunks:
    print('Data did not have chunks as expected')
    sys.exit(1)

if not output_filename:
    base_filename, file_extension = os.path.splitext(filename)
    output_filename = f'{base_filename}.pkl'

full_output_filename = os.path.join(OUTPUT_DIRECTORY, output_filename)

embeddings = []
issue_info = {}

if not overwrite and os.path.exists(full_output_filename):
    print(f'Found {full_output_filename}, loading it as a base to incrementally extend.')
    with open(full_output_filename, 'rb') as f:
        existing_data = pickle.load(f)
    embeddings = existing_data['embeddings']
    issue_info = existing_data['issue_info']

count = 0
total = len(chunks) if max_lines < 0 else max_lines

print('Will process ' + ('all' if max_lines < 0 else str(max_lines)) + ' lines')

for chunk in chunks:
    if max_lines >= 0 and count >= max_lines:
        print('Reached max lines')
        break
    id = chunk.get('id')
    if not id:
        print('Skipping chunk missing an ID')
        continue
    if id in issue_info:
        continue
    print(f'Processing new chunk {id} ({count + 1}/{total})')
    text = chunk.get('text')
    if not text:
        print('Skipping a row with id ' + id + ' that was missing text')
        continue
    issue_info[id] = {}
    for property_name in ['url', 'image_url', 'title', 'description']:
        if chunk.get(property_name): issue_info[id][property_name] = chunk.get(property_name)
    embedding = ask_embeddings.get_embedding(text)
    token_length = ask_embeddings.get_token_length(text)
    embeddings.append((text, embedding, token_length, id))
    count += 1

print(f'Loaded {count} new lines')

result = {
    'embeddings': embeddings,
    'issue_info': issue_info
}

if not os.path.exists(OUTPUT_DIRECTORY):
    os.mkdir(OUTPUT_DIRECTORY)

with open(full_output_filename, 'wb') as f:
    pickle.dump(result, f)
