import base64
import pickle
from random import shuffle
import os
import glob
import json
import copy
import random

import numpy as np
import openai
from transformers import GPT2TokenizerFast

EMBEDDINGS_MODEL_ID = "openai.com:text-embedding-ada-002"
COMPLETION_MODEL_NAME = "text-davinci-003"

EXPECTED_EMBEDDING_LENGTH = {
    'openai.com:text-embedding-ada-002': 1536
}

SEPARATOR = "\n"
MAX_CONTEXT_LEN = 2048

LIBRARY_DIR = 'libraries'
SAMPLE_LIBRARIES_FILE = 'sample-import-content.pkl'

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


def get_embedding_model_name_from_id(model_id):
    return model_id.split(':')[1]


def get_embedding(text, model_id=EMBEDDINGS_MODEL_ID):
    result = openai.Embedding.create(
        model=get_embedding_model_name_from_id(model_id),
        input=text
    )
    return result["data"][0]["embedding"]


def get_similarities(query_embedding, library):
    items = sorted([
        (vector_similarity(query_embedding, item['embedding']), issue_id)
        for issue_id, item
        in library['content'].items()], reverse=True)
    return {key: value for value, key in items}


def load_default_libraries(fail_on_empty=False):
    files = glob.glob(os.path.join(LIBRARY_DIR, '*.pkl')) + \
        glob.glob(os.path.join(LIBRARY_DIR, '*.json'))
    if len(files):
        return load_multiple_libraries(files)
    if fail_on_empty:
        raise Exception('No libraries were in the default library directory.')
    return load_library(SAMPLE_LIBRARIES_FILE)


def load_libraries_in_directory(directory):
    files = glob.glob(os.path.join(directory, '*.pkl')) + \
        glob.glob(os.path.join(directory, '*.json'))
    return load_multiple_libraries(files)


def load_multiple_libraries(library_file_names):
    result = empty_library()
    for file in library_file_names:
        content = load_library(file)
        if result['embedding_model'] != content['embedding_model']:
            model = content['embedding_model']
            raise Exception(f'Embedding model {model} in {file} did not match')
        # TODO: handle key collisions; keys are only guaranteed to be unique
        # within a single library.
        result['content'].update(content['content'])
    return result


def load_data_file(file):
    filetype = os.path.splitext(file)[1].lower()
    if filetype == '.json':
        with open(file, "r") as f:
            return json.load(f)
    else:
        with open(file, "rb") as f:
            return pickle.load(f)


def load_library_from_json_blob(blob):
    raw_library = json.loads(blob)
    return _hydrate_library(raw_library)


def validate_library(library):
    if library.get('version', -1) != CURRENT_VERSION:
        raise Exception('Version invalid')
    if library.get('embedding_model', '') != EMBEDDINGS_MODEL_ID:
        raise Exception('Invalid model name')
    expected_embedding_length = EXPECTED_EMBEDDING_LENGTH.get(
        library.get('embedding_model', ''), 0)
    omit_whole_chunks, fields_to_omit, _ = keys_to_omit(library.get('omit', ''))
    if omit_whole_chunks and len(library['content']):
        raise Exception('omit configured to omit all chunks but they were present')
    for chunk_id, chunk in library['content'].items():
        for field in fields_to_omit:
            if field in chunk:
                raise Exception(f"Expected {field} to be omitted but it was included")
        if 'text' not in fields_to_omit and 'text' not in chunk:
            raise Exception(f'{chunk_id} is missing text')
        if 'embedding' not in fields_to_omit:
            if 'embedding' not in chunk:
                raise Exception(f'{chunk_id} is missing embedding')
            if len(chunk['embedding']) != expected_embedding_length:
                raise Exception(
                    f'{chunk_id} had the wrong length of embedding, expected {expected_embedding_length}')
        if 'token_count' not in chunk:
            raise Exception(f'{chunk_id} is missing token_count')
        # TODO: verify token_count is a reasonable length.
        if 'info' not in fields_to_omit:
            if 'info' not in chunk:
                raise Exception(f'{chunk_id} is missing info')
            info = chunk['info']
            if 'url' not in info:
                raise Exception(f'{chunk_id} info is missing required url')


def _convert_library_from_version_og(og_library):
    library = empty_library()
    for embedding in og_library['embeddings']:
        text, embedding, token_count, issue_id = embedding

        # Multiple embedding rows might have the same issue_id, so append a
        # counter if necessary to not overshadow any items.
        chunk_id = str(issue_id)
        count = 0
        while chunk_id in library['content']:
            chunk_id = str(issue_id) + '_' + str(count)
            count += 1

        url, image_url, title, description = og_library['issue_info'].get(
            issue_id, ('', '', '', ''))
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


def embeddings_to_arrays(library):
    for _, chunk in library['content'].items():
        if 'embedding' not in chunk:
            continue
        chunk['embedding'] = vector_from_base64(chunk['embedding'])


def arrays_to_embeddings(library):
    for _, chunk in library['content'].items():
        if 'embedding' not in chunk:
            continue
        chunk['embedding'] = base64_from_vector(chunk['embedding']).decode('ascii')


def serializable_library(library):
    result = copy.deepcopy(library)
    arrays_to_embeddings(result)
    return result


def save_library(library, filename, format=None):
    result = serializable_library(library)

    if not format:
        format = os.path.splitext(filename)[1].lower()[1:]

    if format == 'json':
        with open(filename, 'w') as f:
            json.dump(result, f, indent='\t')
    else:
        with open(filename, 'wb') as f:
            pickle.dump(result, f)


def _hydrate_library(library):
    version = library.get('version', -1)
    if version != CURRENT_VERSION:
        if version < 0:
            library = _convert_library_from_version_og(library)
        else:
            raise Exception(f'Unsupported version {version}')
    embeddings_to_arrays(library)
    validate_library(library)
    return library


def load_library(library_file):
    library = load_data_file(library_file)
    return _hydrate_library(library)


def empty_library():
    return {
        'version': CURRENT_VERSION,
        'embedding_model': EMBEDDINGS_MODEL_ID,
        'content': {}
    }


def get_token_count(text):
    tokenizer = GPT2TokenizerFast.from_pretrained("gpt2")
    return len(tokenizer.tokenize(text))


def get_context(chunk_ids, library, count=MAX_CONTEXT_LEN, count_type_is_chunk=False):
    """
    Returns a dict of chunk_id to possibly_truncated_chunk_text.

    A count of negative means 'all items'
    """
    result = {}
    context_len = 0
    counter = 0

    # TODO: Account for separator tokens, but do so without invoking a tokenizer in this method.
    for id in chunk_ids:
        if count_type_is_chunk and count >= 0 and counter >= count:
            break
        tokens = library['content'][id]['token_count']
        text = library['content'][id]['text']
        context_len += tokens
        if not count_type_is_chunk and count >= 0 and context_len > count:
            if len(result) == 0:
                result[id] = text[:(count)]
            break
        result[id] = text
        counter += 1
    return result


def get_chunks(chunk_ids, library):
    return [library['content'][chunk_id]['info'] for chunk_id in chunk_ids]


def get_context_for_library(library):
    """
    Returns an array of all text for every chunk in library
    """
    return [chunk['text'] for chunk in library['content'].values()]


def get_chunk_infos_for_library(library):
    """
    Returns all infos for all chunks in library
    """
    return [chunk['info'] for chunk in library['content'].values()]


LEGAL_SORTS = set(['similarity', 'any', 'random'])
LEGAL_COUNT_TYPES = set(['token', 'chunk'])
LEGAL_OMIT_KEYS = set(['*', '', 'similarity', 'embedding', 'info'])

def keys_to_omit(configuration=''):
    """
    Takes a configuration, either None, a single string, or a list of strings
    and returns a tuple of (omit_whole_chunk, [keys_to_omit], canonical_configuration).

    If a string is provided, it will be split on ',' to create the list.
    """
    if configuration == None:
        configuration = ''
    if isinstance(configuration, str):
        configuration = configuration.split(',')
    if len(configuration) == 0:
        configuration = ['']
    result = []
    omit_whole_chunk = False
    for item in configuration:
        if item not in LEGAL_OMIT_KEYS:
            raise Exception(f'Illegal omit key type: {item}')
        item = item.lower()
        if item == '':
            if len(configuration) != 1:
                raise Exception("If '' is provided, it must be the only item.")
            continue
        elif item == '*':
            if len(configuration) != 1:
                raise Exception("If '*' is provided, it must be the only item.")
            omit_whole_chunk = True
            continue
        else:
            result.append(item)
    if len(configuration) == 1:
        configuration = configuration[0]
    return (omit_whole_chunk, set(result), configuration)
        

def library_for_query(library, version = None, query_embedding=None, query_embedding_model=None, count=None, count_type='token', sort='similarity', sort_reversed=False, seed=None, omit='embedding'):

    # We do our own defaulting so that servers that call us can pass the result
    # of request.get() directly and if it's None, we'll use the default.
    if count_type == None:
        count_type = 'token'
    if sort == None:
        sort = 'similarity'
    if omit == None:
        omit = 'embedding'

    if version == None or version != CURRENT_VERSION:
        raise Exception(f'version must be set to {CURRENT_VERSION}')

    if query_embedding and query_embedding_model != EMBEDDINGS_MODEL_ID:
        raise Exception(f'If query_embedding is passed, query_embedding_model must be {EMBEDDINGS_MODEL_ID} but it was {query_embedding_model}')

    if sort not in LEGAL_SORTS:
        raise Exception(f'sort {sort} is not one of the legal options: {LEGAL_SORTS}')

    if count_type not in LEGAL_COUNT_TYPES:
        raise Exception(f'count_type {count_type} is not one of the legal options: {LEGAL_COUNT_TYPES}')

    result = empty_library()

    omit_whole_chunk, omit_keys, canonical_omit_configuration = keys_to_omit(omit)

    result['omit'] = canonical_omit_configuration

    similarities_dict = None
    if query_embedding:
        # TODO: support query_embedding being base64 encoded or a raw vector of
        # floats
        embedding = vector_from_base64(query_embedding)
        similarities_dict = get_similarities(embedding, library)

    # The defeault sort for 'any' or 'similarity' if there was no query set.
    chunk_ids = list(library['content'].keys())
    if sort == 'similarity' and similarities_dict:
        chunk_ids = list(similarities_dict.keys())
    if sort == 'random':
        rng = random.Random()
        rng.seed(seed)
        rng.shuffle(chunk_ids)

    if sort_reversed:
        chunk_ids.reverse()

    count_type_is_chunk = count_type == 'chunk'

    chunk_dict = get_context(chunk_ids, library, count, count_type_is_chunk=count_type_is_chunk)
    if not omit_whole_chunk:
        for chunk_id, chunk_text in chunk_dict.items():
            result['content'][chunk_id] = copy.deepcopy(library['content'][chunk_id])
            # Note: if the text was truncated then technically the embedding isn't
            # necessarily right anymore. But, like, whatever.
            result['content'][chunk_id]['text'] = chunk_text
            if similarities_dict:
                # the similarity is float32, but only float64 is JSON serializable
                result['content'][chunk_id]['similarity'] = float(similarities_dict[chunk_id])
            for key in omit_keys:
                del result['content'][chunk_id][key]
    return result


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

    # The context is a list of strings. We can't guarantee it's short enough to
    # fit because e.g. library_for_query might be the full library, so as a
    # check ensure it's short enough.
    concatenated_context = f"{context}"[:MAX_CONTEXT_LEN]
    prompt = f"Answer the question as truthfully as possible using the provided context, and if the answer is not contained within the text below, say \"I don't know.\"\n\nContext:\n{concatenated_context} \n\nQuestion:\n{query}\n\nAnswer:"
    return get_completion(prompt)


def ask(query, context_query=None, library_file=None):
    if not context_query:
        context_query = query
    library = load_library(
        library_file) if library_file else load_default_libraries()
    query_embedding = get_embedding(context_query)
    similiarities_dict = get_similarities(query_embedding, library)
    context_dict = get_context(similiarities_dict.keys(), library)

    context = list(context_dict.values())
    chunk_ids = list(context_dict.keys())

    chunks = get_chunks(chunk_ids, library)
    return get_completion_with_context(query, context), chunks
