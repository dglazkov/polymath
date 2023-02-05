
from collections.abc import Sequence
from typing import Union

# HostConfig-related types
SourcePrefixesType = dict[str, str]
FunQueriesType = Sequence[str]
InfoConfigType = dict[str, Union[str, SourcePrefixesType, FunQueriesType]]
TokensConfigType = dict[str, dict[str, str]]
HostConfigType = dict[str, Union[str, InfoConfigType, TokensConfigType]]

# EnvironmentConfig-related types
EnvironmentConfigType = dict[str, str]


class EnvironmentConfig:
    def __init__(self, args: EnvironmentConfigType):
        # TODO: Throw an error if the api key is not set.
        self.openai_api_key = args.get('openai_api_key')
        self.library_filename = args.get('library_filename')


class InfoConfig:
    def __init__(self, args: InfoConfigType):
        self.headername = args.get('headername', '')
        self.placeholder = args.get('placeholder', '')
        self.fun_queries = args.get('fun_queries', [])
        self.source_prefixes = args.get('source_prefixes', {})


class HostConfig:
    def __init__(self, args: HostConfigType):
        restricted = args.get('restricted', {})
        self.include_restricted_count = restricted.get('count', False)
        self.restricted_message = restricted.get('message', '')
        self.info = InfoConfig(args.get('info', {}))
        self.tokens = args.get('tokens', {})
