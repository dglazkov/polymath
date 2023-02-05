
import json
import os
from collections.abc import Sequence
from typing import Union

SourcePrefixesType = dict[str, str]
FunQueriesType = Sequence[str]
InfoConfigType = dict[str, Union[str, SourcePrefixesType, FunQueriesType]]
TokensConfigType = dict[str, dict[str, str]]
HostConfigType = dict[str, Union[str, InfoConfigType, TokensConfigType]]
ConfigTypes = HostConfigType


class InfoConfig:
    def __init__(self, args: InfoConfigType):
        self.headername = args.get('headername', '')
        self.placeholder = args.get('placeholder', '')
        self.fun_queries = args.get('fun_queries', [])
        self.source_prefixes = args.get('source_prefixes', {})


class HostConfig:
    def __init__(self, args: HostConfigType):
        restricted = args.get('restricted', {})
        self.include_restructed_count = restricted.get('count', False)
        self.restricted_message = restricted.get('message', '')
        self.info = InfoConfig(args.get('info', {}))
        self.tokens = args.get('tokens', {})


class JSONConfigStore:
    def __init__(self):
        self._cache = {}

    def load(self, filename: str) -> ConfigTypes:
        if filename in self._cache:
            return self._cache[filename]
        if not os.path.exists(filename):
            return {}
        with open(filename, 'r') as f:
            result = json.load(f)
        self._cache[filename] = result
        return result


class JSONConfigLoader:
    def __init__(self):
        self._config_store = JSONConfigStore()

    def load_host_config(self, filename: str = None) -> HostConfig:
        if filename is None:
            filename = 'host.SECRET.json'
        config = self._config_store.load(filename)
        return HostConfig(config)


JSON = JSONConfigLoader()
