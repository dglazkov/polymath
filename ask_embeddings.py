import base64
from random import shuffle
import os
import glob
import json
import copy
import random
from time import sleep

import numpy as np
import openai
from transformers import GPT2TokenizerFast

EMBEDDINGS_MODEL_ID = "openai.com:text-embedding-ada-002"
COMPLETION_MODEL_NAME = "text-davinci-003"

EXPECTED_EMBEDDING_LENGTH = {
    'openai.com:text-embedding-ada-002': 1536
}

SEPARATOR = "\n"
MAX_CONTEXT_LEN_IN_TOKENS = 2048

LIBRARY_DIR = 'libraries'
SAMPLE_LIBRARIES_FILE = 'sample-content.json'

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
    # Occasionally, API returns an error.
    # Retry a few times before giving up.
    retry_count = 10
    while retry_count > 0:
        try:
            result = openai.Embedding.create(
                model=get_embedding_model_name_from_id(model_id),
                input=text
            )
            break
        except Exception as e:
            print(f'openai.Embedding.create error: {e}')
            print("Retrying in 20 seconds ...")
            sleep(20)
            retry_count -= 1
    return result["data"][0]["embedding"]


def load_default_libraries(fail_on_empty=False):
    files = glob.glob(os.path.join(LIBRARY_DIR, '**/*.json'), recursive=True)
    if len(files):
        return load_multiple_libraries(files)
    if fail_on_empty:
        raise Exception('No libraries were in the default library directory.')
    return load_library(SAMPLE_LIBRARIES_FILE)


def load_libraries_in_directory(directory):
    files = glob.glob(os.path.join(directory, '**/*.json'), recursive=True)
    return load_multiple_libraries(files)


def load_data_file(file):
    with open(file, "r") as f:
        return json.load(f)


class Library:
    def __init__(self, data=None, blob=None, filename=None):
        if filename:
            data = load_data_file(filename)
        if blob:
            data = json.loads(blob)
        if data:
            self._data = data
        else:
            self.reset()

        for _, chunk in self._data['content'].items():
            if 'embedding' not in chunk:
                continue
            chunk['embedding'] = vector_from_base64(chunk['embedding'])

        self.validate()

    def validate(self):
        if self._data.get('version', -1) != CURRENT_VERSION:
            raise Exception('Version invalid')
        if self._data.get('embedding_model', '') != EMBEDDINGS_MODEL_ID:
            raise Exception('Invalid model name')
        expected_embedding_length = EXPECTED_EMBEDDING_LENGTH.get(
            self._data.get('embedding_model', ''), 0)
        omit_whole_chunks, fields_to_omit, _ = keys_to_omit(
            self._data.get('omit', ''))
        if omit_whole_chunks and len(self._data['content']):
            raise Exception(
                'omit configured to omit all chunks but they were present')
        for chunk_id, chunk in self._data['content'].items():
            for field in fields_to_omit:
                if field in chunk:
                    raise Exception(
                        f"Expected {field} to be omitted but it was included")
            if 'text' not in fields_to_omit and 'text' not in chunk:
                raise Exception(f'{chunk_id} is missing text')
            if 'embedding' not in fields_to_omit:
                if 'embedding' not in chunk:
                    raise Exception(f'{chunk_id} is missing embedding')
                if len(chunk['embedding']) != expected_embedding_length:
                    raise Exception(
                        f'{chunk_id} had the wrong length of embedding, expected {expected_embedding_length}')
            if 'token_count' not in fields_to_omit:
                if 'token_count' not in chunk:
                    raise Exception(f'{chunk_id} is missing token_count')
            # TODO: verify token_count is a reasonable length.
            if 'info' not in fields_to_omit:
                if 'info' not in chunk:
                    raise Exception(f'{chunk_id} is missing info')
                info = chunk['info']
                if 'url' not in info:
                    raise Exception(f'{chunk_id} info is missing required url')

    @property
    def data(self):
        # TODO: audit all use of this and move them to other getters/setters
        return self._data

    @property
    def version(self):
        return self._data['version']

    @version.setter
    def version(self, value):
        if not isinstance(value, int):
            raise TypeError('Version must be an integer')
        self._data['version'] = value

    @property
    def embedding_model(self):
        return self._data['embedding_model']

    @embedding_model.setter
    def embedding_model(self, value):
        if value != EMBEDDINGS_MODEL_ID:
            raise TypeError(f'The only supported value for embedding model is {EMBEDDINGS_MODEL_ID}')
        self._data['embedding_model'] = value

    @property
    def omit(self):
        """
        Returns either a string or an array of strings all of which are legal omit keys.
        """
        return self._data['omit']

    @omit.setter
    def omit(self, value):
        _, _, canonical_value = keys_to_omit(value)
        self._data['omit'] = canonical_value

    def extend(self, other : 'Library'):
        if other.embedding_model != self.embedding_model:
            raise Exception('The other library had a different embedding model')
        # TODO: handle key collisions; keys are only guaranteed to be unique
        # within a single library.
        self._data['content'].update(other._data['content'])

    def reset(self):
        self._data = {
            'version': CURRENT_VERSION,
            'embedding_model': EMBEDDINGS_MODEL_ID,
            'content': {}
        }

    @property
    def chunk_ids(self):
        """
        Returns an iterator for the chunk_ids in the library in order.
        """
        return self._data["content"].keys()

    def chunk(self, chunk_id):
        return self._data["content"][chunk_id]

    @property
    def chunks(self):
        """
        Returns an iterator of (chunk_id, chunk)
        """
        return self._data["content"].items()

    def delete_chunk(self, chunk_id):
        del self._data["content"][chunk_id]

    def set_chunk(self, chunk_id, chunk):
        self._data["content"][chunk_id] = chunk

    def set_chunk_field(self, chunk_id, text=None, embedding=None, token_count=None, info = None):
        if chunk_id not in self._data["content"]:
            self._data["content"][chunk_id] = {}
        chunk = self._data["content"][chunk_id]
        if text != None:
            chunk["text"] = text
        if embedding != None:
            chunk["embedding"] = embedding
        if token_count != None:
            chunk["token_count"] = token_count
        if info != None:
            chunk["info"] = info
    
    def delete_chunk_field(self, chunk_id, fields=None):
        if isinstance(fields, str):
            fields = [fields]
        if chunk_id not in self._data["content"]:
            return
        chunk = self._data["content"][chunk_id]
        for field in fields:
            del chunk[field]
        if len(chunk) == 0:
            self.delete_chunk(chunk_id)

    def serializable(self):
        """
        Returns a dict representing the data in the library that is suitable for
        being serialized e.g. into JSON.
        """
        result = copy.deepcopy(self._data)
        for _, chunk in result['content'].items():
            if 'embedding' not in chunk:
                continue
            chunk['embedding'] = base64_from_vector(
                chunk['embedding']).decode('ascii')
        return result
    
    def save(self, filename):
        result = self.serializable()
        with open(filename, 'w') as f:
            json.dump(result, f, indent='\t')


def get_similarities(query_embedding, library : Library):
    items = sorted([
        (vector_similarity(query_embedding, item['embedding']), issue_id)
        for issue_id, item
        in library.chunks], reverse=True)
    return {key: value for value, key in items}


def load_library(library_file) -> Library:
    return Library(filename=library_file)


def load_multiple_libraries(library_file_names) -> Library:
    result = Library()
    for file in library_file_names:
        library = Library(filename =file)
        result.extend(library)
    return result

def get_token_count(text):
    tokenizer = GPT2TokenizerFast.from_pretrained("gpt2")
    return len(tokenizer.tokenize(text))


def get_context(chunk_ids, library : Library, count=MAX_CONTEXT_LEN_IN_TOKENS, count_type_is_chunk=False):
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
        chunk = library.chunk(id)
        tokens = chunk['token_count']
        text = chunk['text']
        context_len += tokens
        if not count_type_is_chunk and count >= 0 and context_len > count:
            if len(result) == 0:
                result[id] = text[:(count)]
            break
        result[id] = text
        counter += 1
    return result


def get_context_for_library(library : Library):
    """
    Returns an array of all text for every chunk in library
    """
    return [chunk['text'] for (_, chunk) in library.chunks]


def get_chunk_infos_for_library(library : Library):
    """
    Returns all infos for all chunks in library
    """
    return [chunk['info'] for (_, chunk) in library.chunks]


LEGAL_SORTS = set(['similarity', 'any', 'random'])
LEGAL_COUNT_TYPES = set(['token', 'chunk'])
LEGAL_OMIT_KEYS = set(
    ['*', '', 'similarity', 'embedding', 'token_count', 'info'])


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
                raise Exception(
                    "If '*' is provided, it must be the only item.")
            omit_whole_chunk = True
            continue
        else:
            result.append(item)
    if len(configuration) == 1:
        configuration = configuration[0]
    return (omit_whole_chunk, set(result), configuration)


def library_for_query(library : Library, version=None, query_embedding=None, query_embedding_model=None, count=None, count_type='token', sort='similarity', sort_reversed=False, seed=None, omit='embedding'):

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
        raise Exception(
            f'If query_embedding is passed, query_embedding_model must be {EMBEDDINGS_MODEL_ID} but it was {query_embedding_model}')

    if sort not in LEGAL_SORTS:
        raise Exception(
            f'sort {sort} is not one of the legal options: {LEGAL_SORTS}')

    if count_type not in LEGAL_COUNT_TYPES:
        raise Exception(
            f'count_type {count_type} is not one of the legal options: {LEGAL_COUNT_TYPES}')

    result = Library()

    omit_whole_chunk, omit_keys, canonical_omit_configuration = keys_to_omit(
        omit)

    result.omit = canonical_omit_configuration

    similarities_dict = None
    if query_embedding:
        # TODO: support query_embedding being base64 encoded or a raw vector of
        # floats
        embedding = vector_from_base64(query_embedding)
        similarities_dict = get_similarities(embedding, library)

    # The defeault sort for 'any' or 'similarity' if there was no query set.
    chunk_ids = result.chunk_ids
    if sort == 'similarity' and similarities_dict:
        chunk_ids = list(similarities_dict.keys())
    if sort == 'random':
        rng = random.Random()
        rng.seed(seed)
        rng.shuffle(chunk_ids)

    if sort_reversed:
        chunk_ids.reverse()

    count_type_is_chunk = count_type == 'chunk'

    chunk_dict = get_context(chunk_ids, library, count,
                             count_type_is_chunk=count_type_is_chunk)
    if not omit_whole_chunk:
        for chunk_id, chunk_text in chunk_dict.items():
            chunk = copy.deepcopy(library.chunk(chunk_id))
            # Note: if the text was truncated then technically the embedding isn't
            # necessarily right anymore. But, like, whatever.
            chunk['text'] = chunk_text
            if similarities_dict:
                # the similarity is float32, but only float64 is JSON serializable
                chunk['similarity'] = float(
                    similarities_dict[chunk_id])
            for key in omit_keys:
                del chunk[key]
            result.set_chunk(chunk_id, chunk)
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

    prompt = f"Answer the question as truthfully as possible using the provided context, and if the answer is not contained within the text below, say \"I don't know.\"\n\nContext:\n{context} \n\nQuestion:\n{query}\n\nAnswer:"
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

    infos = [library.chunk(chunk_id)['info'] for chunk_id in chunk_ids]
    return get_completion_with_context(query, context), infos
