
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


