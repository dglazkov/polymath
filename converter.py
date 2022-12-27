import ask_embeddings

import argparse
import json
import sys
import pickle
import os

parser = argparse.ArgumentParser()
parser.add_argument('filename', help='The name of the input file to be processed')
parser.add_argument('--max', help='The number of max lines to process. If negative, will process all.', default=-1, type=int)
args = parser.parse_args()

filename = args.filename
max_lines = args.max

with open(filename, 'r') as f:
    data = json.load(f)

chunks = data.get('chunks')

if not chunks:
    print('Data did not have chunks as expected')
    sys.exit(1)

embeddings = []
issue_info = {}

count = 0

print('Will process ' + ('all' if max_lines < 0 else str(max_lines)) + ' lines')

for chunk in chunks:
    if max_lines >= 0 and count >= max_lines:
        print('Reached max lines')
        break
    id = chunk.get('id')
    if not id:
        print('Skipping chunk missing an ID')
        continue
    print(f'Processing chunk {id}')
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

result = {
    'embeddings': embeddings,
    'issue_info': issue_info
}

base_filename, file_extension = os.path.splitext(filename)
new_filename = f'{base_filename}.pkl'

with open(new_filename, 'wb') as f:
    pickle.dump(result, f)
