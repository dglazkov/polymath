import ask_embeddings

import argparse
import json
import sys
import pickle
import os

parser = argparse.ArgumentParser()
parser.add_argument('filename', help='The name of the input file to be processed')
args = parser.parse_args()

filename = args.filename

with open(filename, 'r') as f:
    data = json.load(f)

chunks = data.get('chunks')

if not chunks:
    print('Data did not have chunks as expected')
    sys.exit(1)

embeddings = []
issue_info = {}

for chunk in chunks:
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

result = {
    'embeddings': embeddings,
    'issue_info': issue_info
}

base_filename, file_extension = os.path.splitext(filename)
new_filename = f'{base_filename}.pkl'

with open(new_filename, 'wb') as f:
    pickle.dump(result, f)
