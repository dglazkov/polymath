import base64
import pickle
from random import shuffle
import os
import glob
import json

import numpy as np
import openai
from transformers import GPT2TokenizerFast

EMBEDDINGS_MODEL_NAME = "text-embedding-ada-002"
COMPLETION_MODEL_NAME = "text-davinci-003"

SEPARATOR = "\n"
MAX_CONTEXT_LEN = 2048

LIBRARY_DIR = 'out'
SAMPLE_LIBARRIES_FILE = 'sample-import-content.pkl'

CURRENT_VERSION = 0

# In JS, the argument can be produced with with:
# ```
# btoa(String.fromCharCode(...(new Uint8Array(new Float32Array(data).buffer))));
# ```
# where `data` is an array of floats


def vector_from_base64(str):
    return np.frombuffer(base64.b64decode(str), dtype=np.float32)

# In JS, the argument can be produced with with:
# ```
# new Float32Array(new Uint8Array([...atob(encoded_data)].map(c => c.charCodeAt(0))).buffer);
# ```
# where `encoded_data` is a base64 string


def base64_from_vector(vector):
    data = np.array(vector, dtype=np.float32)
    return base64.b64encode(data)


def vector_similarity(x, y):
    return np.dot(np.array(x), np.array(y))


def get_embedding(text):
    result = openai.Embedding.create(
        model=EMBEDDINGS_MODEL_NAME,
        input=text
    )
    return result["data"][0]["embedding"]


def get_similarities(query_embedding, library):
    return sorted([
        (vector_similarity(query_embedding, item['embedding']), item['text'], item['token_count'], issue_id)
        for issue_id, item
        in library['content'].items()], reverse=True)


def load_default_libraries():
    files = glob.glob(os.path.join(LIBRARY_DIR, '*.pkl')) + glob.glob(os.path.join(LIBRARY_DIR, '*.json'))
    if len(files):
        return load_multiple_libraries(files)
    return load_library(SAMPLE_LIBARRIES_FILE)


def load_multiple_libraries(library_file_names):
    result = empty_library()
    for file in library_file_names:
        content = load_library(file)
        if result['embedding_model'] != content['embedding_model']:
            model = content['embedding_model']
            raise Exception(f'Embedding model {model} in {file} did not match')
        #TODO: handle key collisions; keys are only guaranteed to be unique
        #within a single library.
        result['content'].update(content['content'])
    return result


def _load_raw_library(library_file):
    filetype = os.path.splitext(library_file)[1].lower()
    if filetype == '.json':
        with open(library_file, "r") as f:
            return json.load(f)  
    else:
        with open(library_file, "rb") as f:
            return pickle.load(f)


def validate_library(library):
    if library.get('version', -1) != CURRENT_VERSION:
        raise Exception('Version invalid')
    if library.get('embedding_model', '') != EMBEDDINGS_MODEL_NAME:
        raise Exception('Invalid model name')
    for chunk_id, chunk in library['content'].items():
        if 'text' not in chunk:
            raise Exception(f'{chunk_id} is missing text')
        if 'embedding' not in chunk:
            raise Exception(f'{chunk_id} is missing embedding')
        #TODO: test the embedding length is the expected number of floats.
        if 'token_count' not in chunk:
            raise Exception(f'{chunk_id} is missing token_count')
        if chunk['token_count'] != get_token_length(chunk['text']):
            raise Exception(f'{chunk_id} has the incorrect token_count')
        if 'info' not in chunk:
            raise Exception(f'{chunk_id} is missing info')
        info = chunk['info']
        if 'url' not in info:
            raise Exception(f'{chunk_id} info is missing required url')


def _convert_library_from_version_og(og_library):
    library = empty_library()
    for embedding in og_library['embeddings']:
        text, embedding, token_count, issue_id = embedding

        #Multiple embedding rows might have the same issue_id, so append a
        #counter if necessary to not overshadow any items.
        chunk_id = issue_id
        count = 0
        while chunk_id in library['content']:
            chunk_id = issue_id + '_' + str(count)
            count += 1

        url, image_url, title, description = og_library['issue_info'].get(issue_id, ('', '', '', ''))
        library['content'][chunk_id] = {
            'text': text,
            'embedding': embedding,
            'token_count': token_count,
            'info': {
                'url': url,
                'image_url': image_url,
                'title': title,
                'description': description
            }
        }
    return library


def load_library(library_file):
    library = _load_raw_library(library_file)
    if library.get('version', -1) == -1:
        library = _convert_library_from_version_og(library)
    validate_library(library)
    return library


def empty_library():
    return {
        'version': CURRENT_VERSION,
        'embedding_model': 'text-embedding-ada-002',
        'content': {}
    }


def get_token_length(text):
    tokenizer = GPT2TokenizerFast.from_pretrained("gpt2")
    return len(tokenizer.tokenize(text))


def get_context(similiarities, token_count=MAX_CONTEXT_LEN):
    context = []
    context_len = 0

    tokenizer = GPT2TokenizerFast.from_pretrained("gpt2")
    separator_len = len(tokenizer.tokenize(SEPARATOR))

    issue_ids = set()

    for id, (_, text, tokens, issue_id) in enumerate(similiarities):
        context_len += tokens + separator_len
        if context_len > token_count:
            if len(context) == 0:
                context.append(text[:(token_count - separator_len)])
            break
        context.append(text)
        if id < 4:
            issue_ids.add(issue_id)
    return context, issue_ids


def get_issues(issue_ids, library):
    return [library[issue_id]['info'] for issue_id in issue_ids]


def get_completion(prompt):
    response = openai.Completion.create(
        model=COMPLETION_MODEL_NAME,
        prompt=prompt,
        temperature=0.7,
        max_tokens=256,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0
    )
    return response.choices[0].text.strip()


def get_completion_with_context(query, context):
    # Borrowed from https://github.com/openai/openai-cookbook/blob/838f000935d9df03e75e181cbcea2e306850794b/examples/Question_answering_using_embeddings.ipynb
    prompt = f"Answer the question as truthfully as possible using the provided context, and if the answer is not contained within the text below, say \"I don't know.\"\n\nContext:\n{context} \n\nQuestion:\n{query}\n\nAnswer:"
    return get_completion(prompt)


def ask(query, context_query=None, library_file=None):
    if not context_query:
        context_query = query
    library = load_library(
        library_file) if library_file else load_default_libraries()
    query_embedding = get_embedding(context_query)
    similiarities = get_similarities(query_embedding, library)
    (context, issue_ids) = get_context(similiarities)

    issues = get_issues(issue_ids, library)
    return get_completion_with_context(query, context), issues
