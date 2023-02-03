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
from .upgrade import upgrade_library_data

EMBEDDINGS_MODEL_ID = "openai.com:text-embedding-ada-002"

EXPECTED_EMBEDDING_LENGTH = {
    'openai.com:text-embedding-ada-002': 1536
}

MAX_CONTEXT_LEN_IN_TOKENS = 2048

# CURRENT_VERSION should be upped every time there is a change that breaks
# backwards-compatibility in the library format.
#
# When updating it, add an item to upgrade.py:_UPGRADERS whose key is one lower
# than the new CURRENT_VERSION.
#
# Old libraries will continue to work, just being upgraded every time they are
# loaded. When a new version is released, ping the discord and remind everyone
# to run `python3 -m convert.upgrade` to upgrade all of their libraries.
CURRENT_VERSION = 1

LEGAL_SORTS = set(['similarity', 'any', 'random', 'manual'])
LEGAL_COUNT_TYPES = set(['token', 'bit'])
LEGAL_OMIT_KEYS = set(
    ['*', '', 'similarity', 'embedding', 'token_count', 'info', 'access_tag'])


def _load_data_file(file):
    with open(file, "r") as f:
        return json.load(f)


def canonical_id(bit_text, url=''):
    """
    Returns the canonical ID for a given bit of text.
    """
    message = url.strip() + '\n' + bit_text.strip()
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


class BitInfo:
    def __init__(self, bit: 'Bit' = None, data=None):
        self._data = data if data else {}
        self._bit = bit

    @property
    def url(self):
        return self._data.get('url', '')

    @url.setter
    def url(self, value):
        if value == self.url:
            return
        self._data['url'] = value
        if self._bit:
            self._bit.info = self

    @property
    def image_url(self):
        return self._data.get('image_url', '')

    @image_url.setter
    def image_url(self, value):
        if value == self.image_url:
            return
        self._data['image_url'] = value
        if self._bit:
            self._bit.info = self

    @property
    def title(self):
        return self._data.get('title', '')

    @title.setter
    def title(self, value):
        if value == self.title:
            return
        self._data['title'] = value
        if self._bit:
            self._bit.info = self

    @property
    def description(self):
        return self._data.get('description', '')

    @description.setter
    def description(self, value):
        if value == self.description:
            return
        self._data['description'] = value
        if self._bit:
            self._bit.info = self

    @property
    def contents(self: 'BitInfo'):
        """
        Returns the contents of the whole info as a string, appropriate for
        checking equality via string comparison.
        """
        return '\n'.join([self.url or '', self.image_url or '', self.title or '', self.description or ''])

    def toJSON(self):
        return self._data


class Bit:
    def __init__(self, library=None, data=None):
        self._cached_info = None
        self._cached_embedding = None
        self._canonical_id = None

        # data is the direct object backing store within library.content
        self._data = data if data else {}
        self._set_library(library)

    def validate(self):
        if not self.library:
            # We can't validate without knowing our library, which tells us which fields to omit.
            return
        fields_to_omit = self.library.fields_to_omit if self.library else set()
        bit_id = self.id
        embedding_model = self.library.embedding_model if self.library else ''
        expected_embedding_length = EXPECTED_EMBEDDING_LENGTH.get(
            embedding_model, 0) if embedding_model else None
        for field in fields_to_omit:
            if field in self._data:
                raise Exception(
                    f"Expected {field} to be omitted but it was included")
        if 'text' not in fields_to_omit and 'text' not in self._data:
            raise Exception(f'{bit_id} is missing text')
        if 'embedding' not in fields_to_omit:
            if 'embedding' not in self._data:
                raise Exception(f'{bit_id} is missing embedding')
            if expected_embedding_length != None:
                if len(self.embedding) != expected_embedding_length:
                    raise Exception(
                        f'{bit_id} had the wrong length of embedding, expected {expected_embedding_length}')
        if 'token_count' not in fields_to_omit:
            if 'token_count' not in self._data:
                raise Exception(f'{bit_id} is missing token_count')
        # TODO: verify token_count is a reasonable length.
        if 'info' not in fields_to_omit:
            if 'info' not in self._data:
                raise Exception(f'{bit_id} is missing info')
            info = self._data['info']
            if 'url' not in info:
                raise Exception(f'{bit_id} info is missing required url')

    def copy(self):
        """
        Returns a copy of self, but not attached to any library
        """
        data = copy.deepcopy(self._data)
        result = Bit(data=data)
        return result

    def remove(self):
        if not self.library:
            return
        self.library.remove_bit(self)

    def __str__(self):
        return self.text

    @property
    def library(self) -> 'Library':
        # There is no exposed library setter. Call library.insert_bit or library.remove_bit to reparent.
        return self._library

    def _set_library(self, library: 'Library'):
        # _set_library should only be called by a library in insert_bit or in our constructor.
        self._library = library
        self.validate()

    @property
    def id(self):
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
    def info(self) -> BitInfo:
        if self._cached_info is None:
            self._cached_info = BitInfo(
                bit=self, data=self._data.get('info', None))
        return self._cached_info

    @info.setter
    def info(self, value: BitInfo):
        self._cached_info = value
        self._data['info'] = value._data

    def strip(self):
        # Called when it should strip any values that its library has configured
        # to omit
        if not self.library:
            return
        if self.library.omit_whole_bit:
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

        self._upgraded = upgrade_library_data(self._data)

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

        content = self._data.get('bits', [])
        self._bits = {}
        # _bits_in_order is an inflated bit in the same order as the underlying data.
        self._bits_in_order = []
        for bit_data in content:
            bit = Bit(library=self, data=bit_data)
            bit_id = bit.id
            self._bits[bit_id] = bit
            self._bits_in_order.append(bit)

        if access_tag:
            for bit in self.bits:
                bit.access_tag = access_tag

        self.validate()

    @property
    def upgraded(self):
        return self._upgraded

    def validate(self):
        if self._data.get('version', -1) != CURRENT_VERSION:
            raise Exception('Version invalid')
        if self._data.get('embedding_model', '') != EMBEDDINGS_MODEL_ID:
            raise Exception('Invalid model name')
        omit_whole_bits, _, _ = _keys_to_omit(
            self._data.get('omit', ''))
        if 'bits' not in self._data:
            raise Exception('bits is a required field')
        if omit_whole_bits and len(self._data['bits']):
            raise Exception(
                'omit configured to omit all bits but they were present')
        # no need to validate bits, they were already validated at creation time.

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
    def omit_whole_bit(self):
        omit_whole_bit, _, _ = _keys_to_omit(self.omit)
        return omit_whole_bit

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
        if self.omit_whole_bit:
            self._data['bits'] = []
            self._bits_in_order = []
            self._bits = {}
        for bit in self.bits:
            bit.strip()

    @property
    def seed(self):
        return self._data.get('seed', None)

    @seed.setter
    def seed(self, value):
        if value == self.seed:
            return
        self._data['seed'] = value
        if not value:
            del self._data['seed']
        self._re_sort()

    @property
    def sort_reversed(self):
        return self._data.get('reversed', False)

    @sort_reversed.setter
    def sort_reversed(self, value):
        if value == self.sort_reversed:
            return
        self._data['reversed'] = value
        if not value:
            del self._data['reversed']
        self._re_sort()

    @property
    def sort(self):
        return self._data.get('sort', 'any')

    @sort.setter
    def sort(self, value):
        if value == self.sort:
            return
        if value not in LEGAL_SORTS:
            raise Exception(f'Illegal sort: {value}')
        self._data['sort'] = value
        if self._data['sort'] == 'any':
            del self._data['sort']
        self._re_sort()

    def _insert_bit_in_order(self, bit):
        # bits is already in sorted order so we can do a bisect into it
        # instead of resorting after every insert, considerably faster.
        sort_type = self._data.get('sort', 'any')
        bits = self._data['bits']
        bits_in_order = self._bits_in_order
        if sort_type == 'similarity':
            # TODO: handle sort_reversed correctly. This assumes a descending
            # sort by similarity.
            def get_similarity(bit):
                if not bit:
                    return -1
                # We want to revese the similarity, because bisect assumes keys
                # are sorted ascending and ours are sorted descending.
                return bit.similarity * -1
            similarity = get_similarity(bit)
            # bisect and friends only work for lists sorted in ascending order. So...
            index = bisect.bisect_left(
                bits_in_order, similarity, key=get_similarity)
            bits_in_order.insert(index, bit)
            bits.insert(index, bit._data)
        else:
            bits_in_order.append(bit)
            bits.append(bit._data)
        self._assert_bits_synced('_insert_bit_in_order')

    def _re_sort(self):
        """
        Called when the sort type might have changed and _data.sort.ids needs to be resorted
        """
        sort_type = self._data.get('sort', 'any')
        sort_reversed = self._data.get('reversed', False)
        # We'll operate on bits_in_order and then replicate that order in
        # self._data['bits]
        bits_in_order = self._bits_in_order
        if sort_type == 'random':
            rng = random.Random()
            rng.seed(self.seed)
            rng.shuffle(bits_in_order)
        elif sort_type == 'similarity':
            def get_similarity(bit):
                similarity = bit.similarity
                if similarity == -1:
                    bit_id = bit.id
                    raise Exception(
                        f'sort of similarity passed but {bit_id} had no similarity')
                return similarity
            bits_in_order.sort(reverse=True, key=get_similarity)
        elif sort_type == 'manual':
            # sort type of manual we expliclity want left in the previous order.
            pass
        else:
            # effectively any, which means any order is fine.
            pass
        if sort_reversed:
            bits_in_order.reverse()
        # replicate the final order of bits_in_order in bits.
        bits = self._data['bits']
        # Operate on the existing list in place to maintain object equality
        bits.clear()
        for bit in bits_in_order:
            bits.append(bit._data)
        self._assert_bits_synced('_re_sort')

    def _assert_bits_synced(self, callsite=''):
        # Throws if the invariant that self._data[bits] and self._bits and
        # self._bits_in_order is not met. A useful check internally for
        # anything that modifies bits to verify everything is correct and find
        # mistakes in logic faster.
        bits_cache_len = len(self._bits)
        bits_len = len(self._data['bits'])
        bits_in_order_len = len(self._bits_in_order)
        if bits_cache_len != bits_len:
            raise Exception('bits_cache_len != bits_len ' +
                            str(bits_cache_len) + ' ' + str(bits_len) + ' ' + callsite)
        if bits_cache_len != bits_in_order_len:
            raise Exception('bits_cache_len != bits_in_order_len ' +
                            str(bits_cache_len) + ' ' + str(bits_in_order_len) + ' ' + callsite)
        if bits_in_order_len != bits_len:
            raise Exception('bits_in_order_len != bits_len ' +
                            str(bits_in_order_len) + ' ' + str(bits_len) + ' ' + callsite)

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
    def count_bits(self):
        counts = self.counts
        if 'bits' not in counts:
            return 0
        return counts['bits']

    @count_bits.setter
    def count_bits(self, value):
        self._details = self._details
        self.counts = self.counts
        self.counts['bits'] = value

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
        return [bit.text for bit in self.bits]

    @property
    def unique_infos(self: 'Library') -> List[BitInfo]:
        seen_infos = set()
        result = []
        for bit in self.bits:
            info = bit.info
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
        self_sort_type = self._data.get('sort', None)
        if self_sort_type == None:
            # We don't have a sort type, it's just implicitly 'any'. We can use
            # the one from the other library. If the other one is also 'any'
            # then this will basically be a no op.
            self.sort = other.sort
        self_omit = self._data.get('omit')
        if not self_omit:
            # We don't have an omit type, so just absorb the omit type from the
            # other. If it also doesn't have an omit type this will be a no-op.
            self.omit = other.omit
        for bit in other.bits:
            self.insert_bit(bit.copy())

    def copy(self):
        result = Library()
        result._data = copy.deepcopy(self._data)
        result._bits = {}
        result._bits_in_order = []
        for data in result._data.get('bits', []):
            bit = Bit(library=result, data=data)
            result._bits[bit.id] = bit
            result._bits_in_order.append(bit)
        return result

    def reset(self):
        self._data = {
            'version': CURRENT_VERSION,
            'embedding_model': EMBEDDINGS_MODEL_ID,
            'bits': []
        }
        self._bits = {}
        self._bits_in_order = []

    def delete_all_bits(self):
        self._data['bits'] = []
        self._bits = {}
        self._bits_in_order = []

    def delete_restricted_bits(self, access_token=None):
        """
        Deletes all bits that are restricted, unless access_token grants access.

        Returns the number of items that were removed.
        """
        visible_access_tags = permitted_access(access_token)

        restricted_count = 0

        for bit in self.bits:
            if bit.access_tag == None:
                continue
            if bit.access_tag in visible_access_tags:
                continue

            self.remove_bit(bit)
            restricted_count += 1

        return restricted_count

    def bit(self, bit_id) -> Bit:
        return self._bits.get(bit_id, None)

    @property
    def bits(self) -> List[Bit]:
        """
        Returns an iterator of each bit in order
        """
        return [bit for bit in self._bits_in_order]

    def remove_bit(self, bit: Bit):
        if not bit:
            return
        if bit.library != self:
            return
        bit._set_library(None)
        bit_id = bit.id
        index = 0
        for other_bit in self._bits_in_order:
            if bit is other_bit:
                break
            index = index + 1
        if index >= len(self._bits_in_order):
            raise Exception('Bit was not found')
        self._bits_in_order.pop(index)
        self._data['bits'].pop(index)
        del self._bits[bit_id]
        # TODO: technically if this is a random sort with seed we do need a
        # resort, but in all other cases it's unnecessarily slower to sort
        # on every bit you remove.

    def insert_bit(self, bit: Bit):
        if bit.library == self:
            return
        if self.omit_whole_bit:
            return
        if bit.id in self._bits:
            # This is an effectively duplicate bit, which can happen in rare
            # cases where there is the same text in a given url.
            return
        bit._set_library(self)
        self._bits[bit.id] = bit
        self._insert_bit_in_order(bit)

    def serializable(self, include_access_tag=False):
        """
        Returns a dict representing the data in the library that is suitable for
        being serialized e.g. into JSON.
        """
        result = copy.deepcopy(self._data)
        for bit in result['bits']:
            if not include_access_tag and 'access_tag' in bit:
                del bit['access_tag']
        return result

    def slice(self, count, count_type_is_bit=False):
        """
        Returns a new library that contains a subset of the first items of self
        up to size count.

        By default, count is of type token, meaning that the last item might be
        a subset of that bit's content.

        If count_type_is_bit is true, then it will return a library with up to
        that many bits.

        A count of negative means 'all items'
        """
        result = self.copy()
        result.delete_all_bits()
        context_len = 0
        counter = 0

        # TODO: Account for separator tokens, but do so without invoking a tokenizer in this method.
        for original_bit in self.bits:
            if count_type_is_bit and count >= 0 and counter >= count:
                break
            bit = original_bit.copy()
            tokens = bit.token_count
            text = bit.text
            context_len += tokens
            if not count_type_is_bit and count >= 0 and context_len > count:
                if len(result.bits) == 0:
                    bit.text = text[:(count)]
                    result.insert_bit(bit)
                break
            result.insert_bit(bit)
            counter += 1
        return result

    def save(self, filename):
        result = self.serializable()
        with open(filename, 'w') as f:
            json.dump(result, f, indent='\t')

    def _similarities(self, query_embedding):
        bits = sorted([
            (vector_similarity(query_embedding, bit.embedding), bit.id)
            for bit
            in self.bits], reverse=True)
        return {key: value for value, key in bits}

    def compute_similarities(self, query_embedding):
        # if we won't store the similarities anyway then don't bother.
        if self.omit_whole_bit or 'similarities' in self.fields_to_omit:
            return
        similarities = self._similarities(query_embedding)
        for bit_id, similarity in similarities.items():
            bit = self.bit(bit_id)
            bit.similarity = similarity

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

        if version == None or version < CURRENT_VERSION:
            # We expect hosts to potentially lag in updating. We want to ensure
            # the format they spit out is understood by the client (lower
            # versions can be upgraded seamlessly). So as long as our current
            # version is less than or equal to the client's version everything
            # should work.
            raise Exception(f'version must be at least {CURRENT_VERSION}')

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
            if type(query_embedding) == str:
                embedding = vector_from_base64(query_embedding)
            else: # assuming it's a list of vectors now
                embedding = query_embedding
            result.compute_similarities(embedding)

        result.seed = seed
        result.sort_reversed = sort_reversed
        result.sort = sort

        count_type_is_bit = count_type == 'bit'
        restricted_count = result.delete_restricted_bits(access_token)
        result = result.slice(count, count_type_is_bit=count_type_is_bit)
        result.count_bits = len(result.bits)
        # Now that we know how many bits exist we can set omit, which might
        # remove all bits.
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
    and returns a tuple of (omit_whole_bit, [keys_to_omit], canonical_configuration).

    If a string is provided, it will be split on ',' to create the list.
    """
    if configuration == None:
        configuration = ''
    if isinstance(configuration, str):
        configuration = configuration.split(',')
    if len(configuration) == 0:
        configuration = ['']
    result = []
    omit_whole_bit = False
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
            omit_whole_bit = True
            continue
        else:
            result.append(item)
    if len(configuration) == 1:
        configuration = configuration[0]
    return (omit_whole_bit, set(result), configuration)


Library.EMBEDDINGS_MODEL_ID = EMBEDDINGS_MODEL_ID
Library.CURRENT_VERSION = CURRENT_VERSION
Library.load_data_file = _load_data_file
Library.base64_from_vector = _base64_from_vector
