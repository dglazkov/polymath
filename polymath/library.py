import base64
import copy
import hashlib
import json
import os
import random
import bisect
from typing import List

import numpy as np

from .access import DEFAULT_PRIVATE_ACCESS_TAG, permitted_access, host_config

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

class ChunkInfo:
    def __init__(self, chunk:'Chunk'=None, data=None):
        self._data = data if data else {}
        self._chunk = chunk
    
    @property
    def url(self):
        return self._data.get('url', '')

    @url.setter
    def url(self, value):
        if value == self.url:
            return
        self._data['url'] = value
        if self._chunk:
            self._chunk.info = self

    @property
    def image_url(self):
        return self._data.get('image_url', '')
    
    @image_url.setter
    def image_url(self, value):
        if value == self.image_url:
            return
        self._data['image_url'] = value
        if self._chunk:
            self._chunk.info = self

    @property
    def title(self):
        return self._data.get('title', '')

    @title.setter
    def title(self, value):
        if value == self.title:
            return
        self._data['title'] = value
        if self._chunk:
            self._chunk.info = self

    @property
    def description(self):
        return self._data.get('description', '')

    @description.setter
    def description(self, value):
        if value == self.description:
            return
        self._data['description'] = value
        if self._chunk:
            self._chunk.info = self

    @property
    def contents(self : 'ChunkInfo'):
        """
        Returns the contents of the whole info as a string, appropriate for
        checking equality via string comparison.
        """
        return '\n'.join([self.url, self.image_url, self.title, self.description])

    

class Chunk:
    def __init__(self, id=None, library=None, data=None):
        # data is the direct object backing store within library.content
        self._library = library
        self._data = data if data else {}
        self._id = id

        self._cached_info = None
        self._cached_embedding = None
        self._canonical_id = None
        self.validate()

    def validate(self):
        fields_to_omit = self.library.fields_to_omit if self.library else set()
        chunk_id = self.id
        embedding_model = self.library.embedding_model if self.library else ''
        expected_embedding_length = EXPECTED_EMBEDDING_LENGTH.get(embedding_model, 0) if embedding_model else None
        for field in fields_to_omit:
            if field in self._data:
                raise Exception(
                    f"Expected {field} to be omitted but it was included")
        if 'text' not in fields_to_omit and 'text' not in self._data:
            raise Exception(f'{chunk_id} is missing text')
        if 'embedding' not in fields_to_omit:
            if 'embedding' not in self._data:
                raise Exception(f'{chunk_id} is missing embedding')
            if expected_embedding_length != None:
                if len(self.embedding) != expected_embedding_length:
                    raise Exception(
                        f'{chunk_id} had the wrong length of embedding, expected {expected_embedding_length}')
        if 'token_count' not in fields_to_omit:
            if 'token_count' not in self._data:
                raise Exception(f'{chunk_id} is missing token_count')
        # TODO: verify token_count is a reasonable length.
        if 'info' not in fields_to_omit:
            if 'info' not in self._data:
                raise Exception(f'{chunk_id} is missing info')
            info = self._data['info']
            if 'url' not in info:
                raise Exception(f'{chunk_id} info is missing required url')

    def copy(self):
        """
        Returns a copy of self, but not attached to any library
        """
        data = copy.deepcopy(self._data)
        result = Chunk(id=self.id, data=data)
        return result

    def remove(self):
        if not self.library:
            return
        self.library.remove_chunk(self)

    def __str__(self):
        return self.text

    @property
    def library(self) -> 'Library':
        # There is no library setter. Call library.insert_chunk or library.remove_chunk to reparent.
        return self._library

    @property
    def id(self):
        if self._id is not None:
            return self._id
        return self.canonical_id

    @property
    def canonical_id(self):
        if self._canonical_id is None:
            self._canonical_id = canonical_id(self.text, self.info.url)
        return self._canonical_id

    @property
    def text(self):
        return self._data.get('text', '')

    @text.setter
    def text(self, value):
        if self.text == value:
            return
        self._data['text'] = value
        # canonical ID depends on text.
        self._canonical_id = None

    @property
    def token_count(self):
        return self._data.get('token_count', -1)

    @token_count.setter
    def token_count(self, value):
        self._data['token_count'] = value

    @property
    def embedding(self):
        if self._cached_embedding is None:
            raw_embedding = self._data.get('embedding', None)
            if not raw_embedding:
                return None
            self._cached_embedding = vector_from_base64(raw_embedding)
        return self._cached_embedding

    @embedding.setter
    def embedding(self, value):
        self._cached_embedding = value
        self._data['embedding'] = _base64_from_vector(value).decode('ascii')

    @property
    def similarity(self):
        return self._data.get('similarity', -1)

    @similarity.setter
    def similarity(self, value):
        self._data['similarity'] = value

    @property
    def access_tag(self):
        return self._data.get('access_tag', None)

    @access_tag.setter
    def access_tag(self, value):
        self._data['access_tag'] = value

    @property
    def info(self) -> ChunkInfo:
        if self._cached_info is None:
            self._cached_info = ChunkInfo(chunk=self, data=self._data.get('info', None))
        return self._cached_info

    @info.setter
    def info(self, value: ChunkInfo):
        self._cached_info = value
        self._data['info'] = value._data

    def strip(self):
        # Called when it should strip any values that its library has configured
        # to omit
        if not self.library:
            return
        if self.library.omit_whole_chunk:
            self.clear()
        for field_to_omit in self.library.fields_to_omit:
            if field_to_omit in self._data:
                del self._data[field_to_omit]


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

        content = self._data.get('content', {})
        self._chunks = {}
        for chunk_id, data in content.items():
            self._chunks[chunk_id] = Chunk(id=chunk_id, library=self, data=data)

        if access_tag:
            for chunk in self.chunks:
                 chunk.access_tag = access_tag
    

        self.validate()

    def validate(self):
        if self._data.get('version', -1) != CURRENT_VERSION:
            raise Exception('Version invalid')
        if self._data.get('embedding_model', '') != EMBEDDINGS_MODEL_ID:
            raise Exception('Invalid model name')
        omit_whole_chunks, _, _ = _keys_to_omit(
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
            sort_ids_set = set(sort_ids)
            content_ids_set = set(self._data['content'].keys())
            keys_in_sort_not_content = sort_ids_set - content_ids_set
            keys_in_content_not_sort = content_ids_set - sort_ids_set
            if len(keys_in_sort_not_content):
                raise Exception(f'sort.ids must contain precisely one entry for each content chunk if provided. It has extra keys {keys_in_sort_not_content}')
            if len(keys_in_content_not_sort):
                raise Exception(f'sort.ids must contain precisely one entry for each content chunk if provided. It is missing keys {keys_in_content_not_sort}')
        # no need to validate Chunks, they were already validated at creation time.

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
            sort = self._data.get('sort', {})
            ids = sort.get('ids', None)
            if ids:
                self._data['sort']['ids'] = []
            return
        for chunk in self.chunks:
            chunk.strip()

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

    def _insert_chunk_into_ids(self, chunk_id):
        # sort_ids is already in sorted order so we can do a bisect into it
        # instead of resorting after every insert, considerably faster.
        sort = self._data.get('sort', {})
        sort_ids = sort.get('ids', None)
        if sort_ids == None:
            return
        sort_type = sort.get('type', 'any')
        if sort_type == 'similarity':
            def get_similarity(chunk_id):
                chunk = self.chunk(chunk_id)
                if not chunk:
                    return -1
                # We want to revese the similarity, because bisect assumes keys
                # are sorted ascending and ours are sorted descending.
                return chunk.similarity * -1
            similarity = get_similarity(chunk_id)
            #bisect and friends only work for lists sorted in ascending order. So... 
            index = bisect.bisect_left(sort_ids, similarity, key=get_similarity)
            sort_ids.insert(index, chunk_id)
        else:
            sort_ids.append(chunk_id)

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
        elif sort_type == 'similarity':
            ids_to_sort = []
            # TODO: use a list comprehension or whatever
            for chunk_id in ids:
                chunk = self.chunk(chunk_id)
                if not chunk:
                    sort_ids_set = set(ids)
                    content_ids_set = set(self._data['content'].keys())
                    keys_in_sort_not_content = sort_ids_set - content_ids_set
                    keys_in_content_not_sort = content_ids_set - sort_ids_set
                    if len(keys_in_sort_not_content):
                        raise Exception(f'sort.ids must contain precisely one entry for each content chunk if provided. It has extra keys {keys_in_sort_not_content}')
                    if len(keys_in_content_not_sort):
                        raise Exception(f'sort.ids must contain precisely one entry for each content chunk if provided. It is missing keys {keys_in_content_not_sort}')
                    raise Exception(f'similarity sort started with a chunk that no longer exists: {chunk_id}')
                similarity = chunk.similarity
                if similarity == -1:
                    raise Exception(f'sort of similarity passed but {chunk_id} had no similarity')
                ids_to_sort.append((similarity, chunk_id))
            ids_to_sort.sort(reverse=True)
            ids = [chunk_id for (_, chunk_id) in ids_to_sort]
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

    @property
    def text(self) -> List[str]:
        return [chunk.text for chunk in self.chunks]

    @property
    def unique_infos(self: 'Library') -> List[ChunkInfo]:
        seen_infos = set()
        result = []
        for chunk in self.chunks:
            info = chunk.info
            key = info.contents
            if key in seen_infos:
                continue
            seen_infos.add(key)
            result.append(info)
        return result

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
        for chunk in other.chunks:
            self.insert_chunk(chunk.copy())

    def copy(self):
        result = Library()
        result._data = copy.deepcopy(self._data)
        result._chunks = {}
        for chunk_id, data in result._data.get('content', {}).items():
            result._chunks[chunk_id] = Chunk(id=chunk_id, library=result, data=data)
        return result

    def reset(self):
        self._data = {
            'version': CURRENT_VERSION,
            'embedding_model': EMBEDDINGS_MODEL_ID,
            'content': {}
        }
        self._chunks = {}

    def delete_all_chunks(self):
        self._data['content'] = {}
        self._chunks = {}
        if 'sort' in self._data:
            if 'ids' in self._data['sort']:
                self._data['sort']['ids'] = []

    def delete_restricted_chunks(self, access_token=None):
        """
        Deletes all chunks that are restricted, unless access_token grants access.

        Returns the number of items that were removed.
        """
        visible_access_tags = permitted_access(access_token)
        chunk_ids = list(self.chunk_ids)

        restricted_count = 0
        
        for chunk_id in chunk_ids:
            chunk = self.chunk(chunk_id)
            if chunk.access_tag == None:
                continue
            if chunk.access_tag in visible_access_tags:
                continue
        
            self.remove_chunk(chunk)
            restricted_count += 1
        
        return restricted_count

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

    def chunk(self, chunk_id) -> Chunk:
        return self._chunks.get(chunk_id, None)

    @property
    def chunks(self) -> List[Chunk]:
        """
        Returns an iterator of each chunk in order
        """
        return [self.chunk(chunk_id) for chunk_id in self.chunk_ids]

    def remove_chunk(self, chunk : Chunk):
        if not chunk:
            return
        if chunk.library != self:
            return
        chunk._library = None
        chunk_id = chunk.id
        del self._data["content"][chunk_id]
        del self._chunks[chunk_id]
        sort = self._data.get('sort', {})
        ids = sort.get('ids', None)
        if ids:
            ids.remove(chunk_id)
            # TODO: technically if this is a random sort with seed we do need a
            # resort, but in all other cases it's unnecessarily slower to sort
            # on every chunk you remove.

    def insert_chunk(self, chunk : Chunk):
        if self.omit_whole_chunk:
            return
        content = self._data['content']
        chunk_inserted = chunk.id not in content
        content[chunk.id] = chunk._data
        chunk._library = self
        self._chunks[chunk.id] = chunk
        if chunk_inserted:
            self._insert_chunk_into_ids(chunk.id)

    def serializable(self, include_access_tag=False):
        """
        Returns a dict representing the data in the library that is suitable for
        being serialized e.g. into JSON.
        """
        result = copy.deepcopy(self._data)
        for _, chunk in result['content'].items():
            if not include_access_tag and 'access_tag' in chunk:
                del chunk['access_tag']
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
            chunk = self.chunk(id).copy()
            tokens = chunk.token_count
            text = chunk.text
            context_len += tokens
            if not count_type_is_chunk and count >= 0 and context_len > count:
                if len(result.chunk_ids) == 0:
                    chunk.text = text[:(count)]
                    result.insert_chunk(chunk)
                break
            result.insert_chunk(chunk)
            counter += 1
        return result

    def save(self, filename):
        result = self.serializable()
        with open(filename, 'w') as f:
            json.dump(result, f, indent='\t')

    def _similarities(self, query_embedding):
        chunks = sorted([
            (vector_similarity(query_embedding, chunk.embedding), chunk.id)
            for chunk
            in self.chunks], reverse=True)
        return {key: value for value, key in chunks}

    def compute_similarities(self, query_embedding):
        # if we won't store the similarities anyway then don't bother.
        if self.omit_whole_chunk or 'similarities' in self.fields_to_omit:
            return
        similarities = self._similarities(query_embedding)
        for chunk_id, similarity in similarities.items():
            chunk = self.chunk(chunk_id)
            chunk.similarity = similarity

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

        result = self.copy()
        if query_embedding:
            # TODO: support query_embedding being base64 encoded or a raw vector of
            # floats
            embedding = vector_from_base64(query_embedding)
            result.compute_similarities(embedding)

        result.seed = seed
        result.sort_reversed = sort_reversed
        result.sort = sort

        count_type_is_chunk = count_type == 'chunk'
        restricted_count = result.delete_restricted_chunks(access_token)
        result = result.slice(count, count_type_is_chunk=count_type_is_chunk)
        result.count_chunks = len(result.chunk_ids)
        # Now that we know how many chunks exist we can set omit, which might
        # remove all chunks.
        result.omit = omit

        config = host_config()
        include_restricted_count = config["include_restricted_count"]
        restricted_message = config["restricted_message"]

        if include_restricted_count:
            result.count_restricted = restricted_count

        if restricted_message and restricted_count > 0:
            result.message = 'Restricted results were omitted. ' + restricted_message

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
Library.load_data_file = _load_data_file
Library.base64_from_vector = _base64_from_vector
