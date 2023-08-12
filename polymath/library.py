import base64
import bisect
import copy
import hashlib
import json
import os
import random
from typing import List, Union, Final, cast

import numpy as np

from numpy.typing import NDArray

from .access import DEFAULT_PRIVATE_ACCESS_TAG, HOST_CONFIG, permitted_access
from .upgrade import upgrade_library_data
from .types import BitData, BitInfoData, LibraryData, LibraryDetailsCountsData, LibraryDetailsData

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


def canonical_id(bit_text: str, url: str = '') -> str:
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


def vector_from_base64(str: str) -> NDArray[np.float32]:
    return np.frombuffer(base64.b64decode(str), dtype=np.float32)


def vector_similarity(x: NDArray[np.float32], y: NDArray[np.float32]) -> float:
    # np.dot returns a float32 but those aren't serializable in json. Just
    # covert to a float64 now.
    return float(np.dot(np.array(x), np.array(y)))


class BitInfo:
    def __init__(self, bit: Union['Bit', None] = None, data: Union[BitInfoData, None] = None):
        self._data = data if data else {}
        self._bit = bit

    @property
    def url(self) -> str:
        return str(self._data.get('url', ''))

    @url.setter
    def url(self, value: str):
        if value == self.url:
            return
        self._data['url'] = value
        if self._bit:
            self._bit.info = self

    @property
    def image_url(self) -> str:
        return str(self._data.get('image_url', ''))

    @image_url.setter
    def image_url(self, value: str):
        if value == self.image_url:
            return
        self._data['image_url'] = value
        if self._bit:
            self._bit.info = self

    @property
    def title(self) -> str:
        return str(self._data.get('title', ''))

    @title.setter
    def title(self, value: str):
        if value == self.title:
            return
        self._data['title'] = value
        if self._bit:
            self._bit.info = self

    @property
    def description(self) -> str:
        return str(self._data.get('description', ''))

    @description.setter
    def description(self, value: str):
        if value == self.description:
            return
        self._data['description'] = value
        if self._bit:
            self._bit.info = self

    @property
    def contents(self: 'BitInfo') -> str:
        """
        Returns the contents of the whole info as a string, appropriate for
        checking equality via string comparison.
        """
        return '\n'.join([self.url or '', self.image_url or '', self.title or '', self.description or ''])

    def toJSON(self):
        return self._data


class Bit:
    def __init__(self, library: Union['Library', None] = None, data: Union[BitData, None] = None):
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
        fields_to_omit = cast(
            set[str], self.library.fields_to_omit if self.library else set())
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
                if self.embedding is not None and len(self.embedding) != expected_embedding_length:
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
            if type(info) is not dict:
                raise Exception('info is not dict')
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

    def __str__(self) -> str:
        return self.text

    @property
    def library(self) -> Union['Library', None]:
        # There is no exposed library setter. Call library.insert_bit or library.remove_bit to reparent.
        return self._library

    def _set_library(self, library: Union['Library', None]):
        # _set_library should only be called by a library in insert_bit or in our constructor.
        self._library = library
        self.validate()

    @property
    def id(self) -> str:
        if self._canonical_id is None:
            self._canonical_id = canonical_id(self.text, self.info.url)
        return self._canonical_id

    @property
    def text(self) -> str:
        return str(self._data.get('text', ''))

    @text.setter
    def text(self, value: str):
        if self.text == value:
            return
        self._data['text'] = value
        # canonical ID depends on text.
        self._canonical_id = None

    @property
    def token_count(self) -> int:
        result = self._data.get('token_count', -1)
        if not isinstance(result, int):
            raise Exception('token_count not int as expected')
        return result

    @token_count.setter
    def token_count(self, value: int):
        self._data['token_count'] = value

    @property
    def embedding(self) -> Union[NDArray[np.float32], None]:
        if self._cached_embedding is None:
            raw_embedding = self._data.get('embedding', None)
            if not raw_embedding:
                return None
            if not isinstance(raw_embedding, str):
                return None
            self._cached_embedding = vector_from_base64(raw_embedding)
        return self._cached_embedding

    @embedding.setter
    def embedding(self, value: Union[NDArray[np.float32], None]):
        self._cached_embedding = value
        self._data['embedding'] = Library.base64_from_vector(
            value).decode('ascii')

    @property
    def similarity(self) -> float:
        result = self._data.get('similarity', -1)
        if not isinstance(result, float):
            raise Exception('similarity not float as expected')
        return result

    @similarity.setter
    def similarity(self, value: float):
        self._data['similarity'] = value

    @property
    def access_tag(self) -> Union[str, None]:
        result = self._data.get('access_tag', None)
        if result is None:
            return result
        return str(result)

    @access_tag.setter
    def access_tag(self, value: Union[str, None]):
        self._data['access_tag'] = value

    @property
    def info(self) -> BitInfo:
        if self._cached_info is None:
            info_data = self._data.get('info', None)
            if info_data is not None and not isinstance(info_data, dict):
                raise Exception('info not dict as expected')
            self._cached_info = BitInfo(
                bit=self, data=info_data)
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
            self._data = {}
        for field_to_omit in self.library.fields_to_omit:
            if field_to_omit in self._data:
                del self._data[field_to_omit]


class Library:

    EMBEDDINGS_MODEL_ID: Final[str] = EMBEDDINGS_MODEL_ID
    CURRENT_VERSION: Final[int] = CURRENT_VERSION

    def __init__(self, data: Union[LibraryData, None] = None, blob: Union[str, None] = None, filename: Union[str, None] = None, access_tag: Union[str, bool, None] = None):

        # The only actual data member of the class is _data. If that ever
        # changes, also change copy().

        if filename:
            data = Library.load_data_file(filename)
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
        assert isinstance(content, list)
        self._bits = cast(dict[str, Bit], {})
        # _bits_in_order is an inflated bit in the same order as the underlying data.
        self._bits_in_order = cast(list[Bit], [])
        for bit_data in content:
            assert isinstance(bit_data, dict)
            bit = Bit(library=self, data=bit_data)
            bit_id = bit.id
            self._bits[bit_id] = bit
            self._bits_in_order.append(bit)

        if access_tag:
            for bit in self.bits:
                bit.access_tag = access_tag

        self.validate()

    @classmethod
    def load_data_file(cls, file: str) -> LibraryData:
        with open(file, "r") as f:
            return json.load(f)

    # In JS, the argument can be produced with with:
    # ```
    # new Float32Array(new Uint8Array([...atob(encoded_data)].map(c => c.charCodeAt(0))).buffer);
    # ```
    # where `encoded_data` is a base64 string

    @classmethod
    def base64_from_vector(cls, vector: Union[NDArray[np.float32], List[float], None]):
        if not vector:
            raise Exception('Vector was none')
        data = np.array(vector, dtype=np.float32)
        return base64.b64encode(data.tobytes())

    @property
    def upgraded(self) -> bool:
        return self._upgraded

    def validate(self):
        if self._data.get('version', -1) != CURRENT_VERSION:
            raise Exception('Version invalid')
        if self._data.get('embedding_model', '') != EMBEDDINGS_MODEL_ID:
            raise Exception('Invalid model name')
        raw_omit = self._data.get('omit', '')
        if not isinstance(raw_omit, str):
            raise Exception('omit not str as expected')
        omit_whole_bits, _, _ = _keys_to_omit(raw_omit)
        if 'bits' not in self._data:
            raise Exception('bits is a required field')
        raw_bits = self._data['bits']
        if not isinstance(raw_bits, list):
            raise Exception('bits not list as expected')
        if omit_whole_bits and len(raw_bits):
            raise Exception(
                'omit configured to omit all bits but they were present')
        # no need to validate bits, they were already validated at creation time.

    @property
    def version(self) -> int:
        result = self._data['version']
        assert isinstance(result, int)
        return result

    @version.setter
    def version(self, value: int):
        self._data['version'] = value

    @property
    def embedding_model(self) -> str:
        result = self._data['embedding_model']
        assert isinstance(result, str)
        return result

    @embedding_model.setter
    def embedding_model(self, value: str):
        if value != EMBEDDINGS_MODEL_ID:
            raise TypeError(
                f'The only supported value for embedding model is {EMBEDDINGS_MODEL_ID}')
        self._data['embedding_model'] = value

    @property
    def omit(self) -> str:
        """
        Returns either a string or an array of strings all of which are legal omit keys.
        """
        result = self._data.get('omit', '')
        assert isinstance(result, str)
        return result

    @property
    def omit_whole_bit(self) -> bool:
        omit_whole_bit, _, _ = _keys_to_omit(self.omit)
        return omit_whole_bit

    @property
    def fields_to_omit(self) -> set[str]:
        _, fields_to_omit, _ = _keys_to_omit(self.omit)
        return fields_to_omit

    @omit.setter
    def omit(self, value: str):
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
    def sort(self) -> str:
        result = self._data.get('sort', 'any')
        assert isinstance(result, str)
        return result

    @sort.setter
    def sort(self, value: str):
        if value == self.sort:
            return
        if value not in LEGAL_SORTS:
            raise Exception(f'Illegal sort: {value}')
        self._data['sort'] = value
        if self._data['sort'] == 'any':
            del self._data['sort']
        self._re_sort()

    def _insert_bit_in_order(self, bit: Bit):
        # bits is already in sorted order so we can do a bisect into it
        # instead of resorting after every insert, considerably faster.
        sort_type = self._data.get('sort', 'any')
        bits = self._data['bits']
        bits = cast(list[BitData], bits)
        bits_in_order = self._bits_in_order
        if sort_type == 'similarity':
            # NOTE: if sort_reversed is ever supported, then bisect_left will
            # not be sufficient.
            def get_similarity(bit: Bit) -> float:
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
        # We'll operate on bits_in_order and then replicate that order in
        # self._data['bits]
        bits_in_order = self._bits_in_order
        if sort_type == 'random':
            rng = random.Random()
            rng.shuffle(bits_in_order)
        elif sort_type == 'similarity':
            def get_similarity(bit: Bit) -> float:
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
        # replicate the final order of bits_in_order in bits.
        bits = cast(list[BitData], self._data['bits'])
        # Operate on the existing list in place to maintain object equality
        bits.clear()
        for bit in bits_in_order:
            bits.append(bit._data)
        self._assert_bits_synced('_re_sort')

    def _assert_bits_synced(self, callsite: str = ''):
        # Throws if the invariant that self._data[bits] and self._bits and
        # self._bits_in_order is not met. A useful check internally for
        # anything that modifies bits to verify everything is correct and find
        # mistakes in logic faster.
        bits_cache_len = len(self._bits)
        bits_len = len(cast(list[BitData], self._data['bits']))
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
    def _details(self) -> LibraryDetailsData:
        result = self._data.get('details', {})
        assert isinstance(result, dict)
        return result

    @_details.setter
    def _details(self, value: LibraryDetailsData):
        self._data['details'] = value

    @property
    def counts(self) -> LibraryDetailsCountsData:
        details = self._details
        if 'counts' not in details:
            return {}
        result = details['counts']
        assert isinstance(result, dict)
        return result

    @counts.setter
    def counts(self, value: LibraryDetailsCountsData):
        self._details = self._details
        self._details['counts'] = value

    @property
    def count_bits(self) -> int:
        counts = self.counts
        if 'bits' not in counts:
            return 0
        return counts['bits']

    @count_bits.setter
    def count_bits(self, value: int):
        self._details = self._details
        self.counts = self.counts
        self.counts['bits'] = value

    @property
    def count_restricted(self) -> int:
        counts = self.counts
        if 'restricted' not in counts:
            return 0
        return counts['restricted']

    @count_restricted.setter
    def count_restricted(self, value: int):
        self._details = self._details
        self.counts = self.counts
        self.counts['restricted'] = value

    @property
    def message(self) -> str:
        details = self._details
        result = details.get('message', '')
        assert isinstance(result, str)
        return result

    @message.setter
    def message(self, value: str):
        self._details = self._details
        self._details['message'] = value

    @property
    def text(self) -> List[str]:
        return [bit.text for bit in self.bits]

    @property
    def unique_infos(self: 'Library') -> List[BitInfo]:
        seen_infos = cast(set[str], set())
        result = cast(list[BitInfo], [])
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
        result._bits = cast(dict[str, Bit], {})
        result._bits_in_order = cast(list[Bit], [])
        raw_bits = cast(list[BitData], result._data.get('bits', []))
        for data in raw_bits:
            bit = Bit(library=result, data=data)
            result._bits[bit.id] = bit
            result._bits_in_order.append(bit)
        return result

    def reset(self):
        self._data = cast(LibraryData, {
            'version': CURRENT_VERSION,
            'embedding_model': EMBEDDINGS_MODEL_ID,
            'bits': []
        })
        self._bits = {}
        self._bits_in_order = []

    def delete_all_bits(self):
        self._data['bits'] = []
        self._bits = {}
        self._bits_in_order = []

    def delete_restricted_bits(self, access_token: Union[str, None] = None):
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

    def bit(self, bit_id: str) -> Union[Bit, None]:
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
        cast(list[BitData], self._data['bits']).pop(index)
        del self._bits[bit_id]

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

    def serializable(self, include_access_tag: bool = False):
        """
        Returns a dict representing the data in the library that is suitable for
        being serialized e.g. into JSON.
        """
        result = copy.deepcopy(self._data)
        for bit in cast(list[BitData], result['bits']):
            if not include_access_tag and 'access_tag' in bit:
                del bit['access_tag']
        return result

    def slice(self, count: int, count_type_is_bit: bool = False) -> 'Library':
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

    def save(self, filename: str):
        result = self.serializable()
        with open(filename, 'w') as f:
            json.dump(result, f, indent='\t')

    def _similarities(self, query_embedding: NDArray[np.float32]):
        bits = sorted([
            (vector_similarity(query_embedding, bit.embedding), bit.id)
            for bit
            in self.bits
            if bit.embedding is not None], reverse=True)
        return {key: value for value, key in bits}

    def compute_similarities(self, query_embedding: Union[NDArray[np.float32], None]):
        # if we won't store the similarities anyway then don't bother.
        if self.omit_whole_bit or 'similarities' in self.fields_to_omit or query_embedding is None:
            return
        similarities = self._similarities(query_embedding)
        for bit_id, similarity in similarities.items():
            bit = self.bit(bit_id)
            if not bit:
                continue
            bit.similarity = similarity

    @classmethod
    def _validate_query_arguments(cls, args: dict[str, Union[str, int]]):
        version = int(args.get('version', -1))
        raw_query_embedding = args.get('query_embedding')
        query_embedding_model = str(args.get('query_embedding_model'))
        count = int(args.get('count', 0))
        count_type = args.get('count_type', 'token')
        omit = args.get('omit', 'embedding')
        access_token = args.get('access_token', '')

        if count == 0:
            raise Exception('count must be greater than 0')

        if version < CURRENT_VERSION:
            # We expect hosts to potentially lag in updating. We want to ensure
            # the format they spit out is understood by the client (lower
            # versions can be upgraded seamlessly). So as long as our current
            # version is less than or equal to the client's version everything
            # should work.
            raise Exception(f'version must be at least {CURRENT_VERSION}')

        if query_embedding_model != EMBEDDINGS_MODEL_ID:
            raise Exception(
                f'Embedding model was {query_embedding_model} but expected {EMBEDDINGS_MODEL_ID}')

        query_embedding = None
        if raw_query_embedding:
            if type(raw_query_embedding) is not str:
                # TODO: allow accepting a query_embedding argument that is already NDArray[np.float32]
                raise Exception('query_embedding must be str')
            query_embedding = vector_from_base64(raw_query_embedding)
        else:
            embedding_length = EXPECTED_EMBEDDING_LENGTH[query_embedding_model]
            query_embedding = np.random.rand(
                embedding_length).astype(np.float32)

        if count_type not in LEGAL_COUNT_TYPES:
            raise Exception(
                f'count_type {count_type} is not one of the legal options: {LEGAL_COUNT_TYPES}')

        return (query_embedding, {
            'count': count,
            'count_type': count_type,
            'omit': omit,
            'access_token': access_token
        })

    def _produce_query_result(self, target, query_embedding: NDArray[np.float32]):
        target.compute_similarities(query_embedding)
        target.sort = 'similarity'

    def _remove_restricted_bits(self, count: int, omit: str, count_type: str, access_token: Union[str, None]):
        count_type_is_bit = count_type == 'bit'
        restricted_count = self.delete_restricted_bits(access_token)
        result = self.slice(count, count_type_is_bit=count_type_is_bit)
        result.count_bits = len(result.bits)
        # Now that we know how many bits exist we can set omit, which might
        # remove all bits.
        result.omit = omit

        if HOST_CONFIG.restricted.count:
            result.count_restricted = restricted_count

        restricted_message = HOST_CONFIG.restricted.message

        if restricted_message and restricted_count > 0:
            result.message = 'Restricted results were omitted. ' + restricted_message
        return result

    def query(self, args: dict[str, Union[str, int]]):
        query_embedding, access_args = self._validate_query_arguments(args)
        result = self.copy()
        self._produce_query_result(result, query_embedding)
        return result._remove_restricted_bits(**access_args)


def _keys_to_omit(configuration='') -> tuple[bool, set[str], Union[str, list[str]]]:
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
