import base64
import copy
import hashlib
import json
import os
import random

import numpy as np

from .access import DEFAULT_PRIVATE_ACCESS_TAG, permitted_access, restricted_configuration

EMBEDDINGS_MODEL_ID = "openai.com:text-embedding-ada-002"

EXPECTED_EMBEDDING_LENGTH = {
    'openai.com:text-embedding-ada-002': 1536
}

MAX_CONTEXT_LEN_IN_TOKENS = 2048

CURRENT_VERSION = 0

LEGAL_SORTS = set(['similarity', 'any', 'random', 'manual'])
LEGAL_COUNT_TYPES = set(['token', 'chunk'])
LEGAL_OMIT_KEYS = set(
    ['*', '', 'similarity', 'embedding', 'token_count', 'info', 'access_tag'])


def _load_data_file(file):
    with open(file, "r") as f:
        return json.load(f)


def canonical_id_for_chunk(chunk):
    text = chunk.get('text', '')
    info = chunk.get('info', {})
    url = info.get('url', {})
    return canonical_id(text, url)


def canonical_id(chunk_text, url=''):
    """
    Returns the canonical ID for a given chunk of text.

    Today using the canonical ID as a chunk ID is a best practice, but in upcoming versions it will be required.
    """
    message = url.strip() + '\n' + chunk_text.strip()
    message_bytes = message.encode()
    hash_object = hashlib.sha256()
    hash_object.update(message_bytes)
    return hash_object.hexdigest()


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


def _base64_from_vector(vector):
    data = np.array(vector, dtype=np.float32)
    return base64.b64encode(data)


def vector_similarity(x, y):
    # np.dot returns a float32 but those aren't serializable in json. Just
    # covert to a float64 now.
    return float(np.dot(np.array(x), np.array(y)))


class Library:
    def __init__(self, data=None, blob=None, filename=None, access_tag=None):

        # The only actual data member of the class is _data. If that ever
        # changes, also change copy().

        if filename:
            data = _load_data_file(filename)
        if blob:
            data = json.loads(blob)
        if data:
            self._data = data
        else:
            self.reset()

        if access_tag == None and filename:
            next_directory_is_access_tag = False
            for directory in os.path.dirname(filename).split('/'):
                if next_directory_is_access_tag:
                    access_tag = directory
                    break
                if directory == 'access':
                    next_directory_is_access_tag = True
                else:
                    next_directory_is_access_tag = False

        if access_tag == True:
            access_tag = DEFAULT_PRIVATE_ACCESS_TAG

        for _, chunk in self._data['content'].items():
            if 'embedding' not in chunk:
                continue
            chunk['embedding'] = vector_from_base64(chunk['embedding'])

        if access_tag:
            for chunk_id in self.chunk_ids:
                self.set_chunk_field(chunk_id, access_tag=access_tag)

        self.validate()

    def validate(self):
        if self._data.get('version', -1) != CURRENT_VERSION:
            raise Exception('Version invalid')
        if self._data.get('embedding_model', '') != EMBEDDINGS_MODEL_ID:
            raise Exception('Invalid model name')
        expected_embedding_length = EXPECTED_EMBEDDING_LENGTH.get(
            self._data.get('embedding_model', ''), 0)
        omit_whole_chunks, fields_to_omit, _ = _keys_to_omit(
            self._data.get('omit', ''))
        if 'content' not in self._data:
            raise Exception('content is a required field')
        if omit_whole_chunks and len(self._data['content']):
            raise Exception(
                'omit configured to omit all chunks but they were present')
        sort = self._data.get('sort', {})
        sort_type = sort.get('type', 'any')
        sort_ids = sort.get('ids', None)
        if sort_type != 'any' and not sort_ids:
            raise Exception('sort.ids is required if sort type is not any')
        if sort_ids:
            sort_ids_dict = {key: True for key in sort_ids}
            if len(sort_ids_dict) != len(self._data['content']):
                raise Exception('sort.ids if provided must contain an entry for each content chunk')
            for chunk_id in self._data['content'].keys():
                if chunk_id not in sort_ids_dict:
                    raise Exception(f'sort.ids if provided must have an entry for each chunk_id. Missing {chunk_id}')
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
            raise TypeError(
                f'The only supported value for embedding model is {EMBEDDINGS_MODEL_ID}')
        self._data['embedding_model'] = value

    @property
    def omit(self):
        """
        Returns either a string or an array of strings all of which are legal omit keys.
        """
        if 'omit' not in self._data:
            return ''
        return self._data['omit']

    @property
    def omit_whole_chunk(self):
        omit_whole_chunk, _, _ = _keys_to_omit(self.omit)
        return omit_whole_chunk

    @property
    def fields_to_omit(self):
        _, fields_to_omit, _ = _keys_to_omit(self.omit)
        return fields_to_omit

    @omit.setter
    def omit(self, value):
        _, _, canonical_value = _keys_to_omit(value)
        if 'omit' in self._data and canonical_value == self._data['omit']:
            return
        self._data['omit'] = canonical_value
        if self.omit_whole_chunk:
            self._data['content'] = {}
            return
        for chunk_id, chunk in self.chunks:
            self.set_chunk(chunk_id, chunk)

    @property
    def seed(self):
        if 'sort' not in self._data:
            return None
        return self._data['sort'].get('seed', None)

    @seed.setter
    def seed(self, value):
        if value == self.seed:
            return
        if 'sort' not in self._data:
            self._data['sort'] = {}
        self._data['sort']['seed'] = value
        self._re_sort()

    @property
    def sort_reversed(self):
        if 'sort' not in self._data:
            return False
        return self._data['sort'].get('reversed', False)

    @sort_reversed.setter
    def sort_reversed(self, value):
        if value == self.sort_reversed:
            return
        if 'sort' not in self._data:
            self._data['sort'] = {}
        self._data['sort']['reversed'] = value
        self._re_sort()

    @property
    def sort(self):
        if 'sort' not in self._data:
            return 'any'
        return self._data['sort'].get('type', 'any')
    
    @sort.setter
    def sort(self, value):
        if value == self.sort:
            return
        if value not in LEGAL_SORTS:
            raise Exception(f'Illegal sort: {value}')
        if 'sort' not in self._data:
            self._data['sort'] = {}
        self._data['sort']['type'] = value
        if value == 'any':
            if 'ids' in self._data['sort']:
                del self._data['sort']['ids']
        else:
            if 'ids' not in self._data['sort']:
                self._data['sort']['ids'] = list(self._data['content'].keys())
        if self._data['sort']['type'] == 'any':
            del self._data['sort']['type']
        if len(self._data['sort']) == 0:
            del self._data['sort']
        self._re_sort()

    def _re_sort(self):
        """
        Called when the sort type might have changed and _data.sort.ids needs to be resorted
        """
        sort = self._data.get('sort', {})
        ids = sort.get('ids', None)
        if not ids:
            return
        sort_type = sort.get('type', 'any')
        sort_reversed = sort.get('reversed', False)
        if sort_type == 'random':
            rng = random.Random()
            rng.seed(self.seed)
            rng.shuffle(ids)
        elif sort_type == 'similiarity':
            ids_to_sort = []
            # TODO: use a list comprehension or whatever
            for chunk_id, chunk in self.chunks:
                similarity = chunk.get('similarity', None)
                if similarity == None:
                    raise Exception(f'sort of similarity passed but {chunk_id} had no similarity')
                ids_to_sort.append((similarity, chunk_id))
            ids_to_sort.sort(reverse=True)
            ids = ids_to_sort
        elif sort_type == 'manual':
            # sort type of manual we expliclity want left in the previous order.
            pass
        else:
            # effectively any, which means any order is fine.
            pass
        if sort_reversed:
            ids.reverse()
        self._data['sort']['ids'] = ids

    @property
    def _details(self):
        if 'details' not in self._data:
            return {}
        return self._data['details']

    @_details.setter
    def _details(self, value):
        self._data['details'] = value

    @property
    def counts(self):
        details = self._details
        if 'counts' not in details:
            return {}
        return details['counts']

    @counts.setter
    def counts(self, value):
        self._details = self._details
        self._details['counts'] = value

    @property
    def count_chunks(self):
        counts = self.counts
        if 'chunks' not in counts:
            return 0
        return counts['chunks']

    @count_chunks.setter
    def count_chunks(self, value):
        self._details = self._details
        self.counts = self.counts
        self.counts['chunks'] = value

    @property
    def count_restricted(self):
        counts = self.counts
        if 'restricted' not in counts:
            return 0
        return counts['restricted']

    @count_restricted.setter
    def count_restricted(self, value):
        self._details = self._details
        self.counts = self.counts
        self.counts['restricted'] = value

    @property
    def message(self):
        details = self._details
        if 'message' not in details:
            return ''
        return details['message']

    @message.setter
    def message(self, value):
        self._details = self._details
        self._details['message'] = value

    def extend(self, other: 'Library'):
        if other.embedding_model != self.embedding_model:
            raise Exception(
                'The other library had a different embedding model')
        # TODO: handle key collisions; keys are only guaranteed to be unique
        # within a single library.
        self_sort = self._data.get('sort', {})
        self_sort_type = self_sort.get('type', None)
        if self_sort_type == None:
            # We don't have a sort type, it's just implicitly 'any'. We can use
            # the one from the other library. If the other one is also 'any'
            # then this will basically be a no op.
            self.sort = other.sort
        for chunk_id, chunk in other.chunks:
            self.set_chunk(chunk_id, chunk)

    def copy(self):
        result = Library()
        result._data = copy.deepcopy(self._data)
        return result

    def reset(self):
        self._data = {
            'version': CURRENT_VERSION,
            'embedding_model': EMBEDDINGS_MODEL_ID,
            'content': {}
        }

    def delete_all_chunks(self):
        self._data['content'] = {}
        if 'sort' in self._data:
            if 'ids' in self._data['sort']:
                self._data['sort']['ids'] = []

    @property
    def chunk_ids(self):
        """
        Returns an iterator for the chunk_ids in the library in order.
        """
        sort = self._data.get('sort', {})
        ids = sort.get('ids', None)
        if not ids:
            return self._data['content'].keys()
        return ids

    def chunk(self, chunk_id):
        if chunk_id not in self._data["content"]:
            return None
        return self._data["content"][chunk_id]

    @property
    def chunks(self):
        """
        Returns an iterator of (chunk_id, chunk)
        """
        return [(chunk_id, self.chunk(chunk_id)) for chunk_id in self.chunk_ids]

    def delete_chunk(self, chunk_id):
        del self._data["content"][chunk_id]
        sort = self._data.get('sort', {})
        ids = sort.get('ids', None)
        if ids:
            ids.remove(chunk_id)
            self._re_sort()

    def _strip_chunk(self, chunk):
        if self.omit_whole_chunk:
            chunk.clear()
        for field_to_omit in self.fields_to_omit:
            if field_to_omit in chunk:
                del chunk[field_to_omit]

    def set_chunk(self, chunk_id, chunk):
        if self.omit_whole_chunk:
            return
        content = self._data['content']
        if chunk_id not in content:
            sort = self._data.get('sort', {})
            sort_ids = sort.get('ids', None)
            if sort_ids != None:
                sort_ids.append(chunk_id)
                self._re_sort()
        content[chunk_id] = chunk
        self._strip_chunk(chunk)

    def set_chunk_field(self, chunk_id, text=None, embedding=None, token_count=None, info=None, access_tag=None):
        if self.omit_whole_chunk:
            return
        chunk = self._data["content"].get(chunk_id, {})
        if text != None:
            chunk["text"] = text
        if embedding != None:
            chunk["embedding"] = embedding
        if token_count != None:
            chunk["token_count"] = token_count
        if info != None:
            chunk["info"] = info
        if access_tag != None:
            chunk["access_tag"] = access_tag
        self.set_chunk(chunk_id, chunk)

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

    def serializable(self, include_access_tag=False):
        """
        Returns a dict representing the data in the library that is suitable for
        being serialized e.g. into JSON.
        """
        result = copy.deepcopy(self._data)
        for _, chunk in result['content'].items():
            if not include_access_tag and 'access_tag' in chunk:
                del chunk['access_tag']
            if 'embedding' not in chunk:
                continue
            chunk['embedding'] = _base64_from_vector(
                chunk['embedding']).decode('ascii')
        return result

    def slice(self, count, count_type_is_chunk=False, chunk_ids=None):
        """
        Returns a new library that contains a subset of the first items of self
        up to size count.

        By default, count is of type token, meaning that the last item might be
        a subset of that chunk's content.

        If count_type_is_chunk is true, then it will return a library with up to
        that many chunks.

        A count of negative means 'all items'
        """
        result = self.copy()
        result.delete_all_chunks()
        context_len = 0
        counter = 0

        if chunk_ids == None:
            chunk_ids = list(self.chunk_ids)

        # TODO: Account for separator tokens, but do so without invoking a tokenizer in this method.
        for id in chunk_ids:
            if count_type_is_chunk and count >= 0 and counter >= count:
                break
            chunk = copy.deepcopy(self.chunk(id))
            tokens = chunk['token_count']
            text = chunk['text']
            context_len += tokens
            if not count_type_is_chunk and count >= 0 and context_len > count:
                if len(result.chunk_ids) == 0:
                    chunk['text'] = text[:(count)]
                    result.set_chunk(id, chunk)
                break
            result.set_chunk(id, chunk)
            counter += 1
        return result

    def save(self, filename):
        result = self.serializable()
        with open(filename, 'w') as f:
            json.dump(result, f, indent='\t')

    def similarities(self, query_embedding):
        items = sorted([
            (vector_similarity(query_embedding, item['embedding']), issue_id)
            for issue_id, item
            in self.chunks], reverse=True)
        return {key: value for value, key in items}

    def add_similarities(self, query_embedding):
        # if we won't store the similarities anyway then don't bother.
        if self.omit_whole_chunk or 'similarities' in self.fields_to_omit:
            return
        similarities = self.similarities(query_embedding)
        for chunk_id, similarity in similarities.items():
            self.set_chunk_field(chunk_id, similarity=similarity)

    def query(self, version=None, query_embedding=None, query_embedding_model=None, count=0, count_type='token', sort='similarity', sort_reversed=False, seed=None, omit='embedding', access_token=''):
        # We do our own defaulting so that servers that call us can pass the result
        # of request.get() directly and if it's None, we'll use the default.
        if count_type == None:
            count_type = 'token'
        if sort == None:
            sort = 'similarity'
        if omit == None:
            omit = 'embedding'

        if count == 0:
            raise Exception('count must be greater than 0')

        if version == None or version != CURRENT_VERSION:
            raise Exception(f'version must be set to {CURRENT_VERSION}')

        if query_embedding and query_embedding_model != EMBEDDINGS_MODEL_ID:
            raise Exception(
                f'If query_embedding is passed, query_embedding_model must be {EMBEDDINGS_MODEL_ID} but it was {query_embedding_model}')

        if sort not in LEGAL_SORTS:
            raise Exception(
                f'sort {sort} is not one of the legal options: {LEGAL_SORTS}')
            
        if sort == 'manual':
            raise Exception('sort of manual is not allowed in query')

        if count_type not in LEGAL_COUNT_TYPES:
            raise Exception(
                f'count_type {count_type} is not one of the legal options: {LEGAL_COUNT_TYPES}')

        result = Library()
        # TODO: when we fix #52 then we won't use this. But for now ensure that all of the items are in insertion order.
        result.sort = 'manual'

        omit_whole_chunk, _, canonical_omit_configuration = _keys_to_omit(
            omit)

        result.omit = canonical_omit_configuration

        similarities_dict = None
        if query_embedding:
            # TODO: support query_embedding being base64 encoded or a raw vector of
            # floats
            embedding = vector_from_base64(query_embedding)
            similarities_dict = self.similarities(embedding)

        # The default sort for 'any' or 'similarity' if there was no query set.
        chunk_ids = None
        if sort == 'similarity':
            if not similarities_dict:
                raise Exception('similarity sort passed without a query')
            chunk_ids = list(similarities_dict.keys())
        elif sort == 'random':
            chunk_ids = list(self.chunk_ids)
            rng = random.Random()
            rng.seed(None if not seed else seed)
            rng.shuffle(chunk_ids)
            # TODO: this is a smell; technically it's possible to have a sort of
            # random and still want embeddings. Likely we should change other
            # systems that want the random behavior to also pass the desired
            # omit behavior and not force it.
            result.omit = 'embedding,similarity'
        elif sort == 'any':
            chunk_ids = list(self.chunk_ids)

        if not chunk_ids:
            raise Exception('Invalid type of sort was specified')

        if sort_reversed:
            chunk_ids.reverse()

        count_type_is_chunk = count_type == 'chunk'

        chunk_dict = _get_context(chunk_ids, self, count,
                                  count_type_is_chunk=count_type_is_chunk)

        include_restricted_count, restricted_message = restricted_configuration()

        print(f"access_token: {access_token}")
        visible_access_tags = permitted_access(access_token)

        chunk_count = 0
        restricted_count = 0

        for chunk_id, chunk_text in chunk_dict.items():
            chunk = copy.deepcopy(self.chunk(chunk_id))
            if 'access_tag' in chunk:
                if chunk['access_tag'] not in visible_access_tags:
                    restricted_count += 1
                    continue

            chunk_count += 1

            if omit_whole_chunk:
                continue

            # Note: if the text was truncated then technically the embedding isn't
            # necessarily right anymore. But, like, whatever.
            chunk['text'] = chunk_text
            if similarities_dict:
                chunk['similarity'] = similarities_dict[chunk_id]
            result.set_chunk(chunk_id, chunk)

        result.count_chunks = chunk_count

        if include_restricted_count:
            result.count_restricted = restricted_count

        if restricted_message and restricted_count > 0:
            result.message = 'Restricted results were omitted. ' + restricted_message

        return result


def _get_context(chunk_ids, library: Library, count=MAX_CONTEXT_LEN_IN_TOKENS, count_type_is_chunk=False):
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


def _keys_to_omit(configuration=''):
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


Library.EMBEDDINGS_MODEL_ID = EMBEDDINGS_MODEL_ID
Library.CURRENT_VERSION = CURRENT_VERSION
Library.get_context = _get_context
Library.load_data_file = _load_data_file
Library.base64_from_vector = _base64_from_vector
