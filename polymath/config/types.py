
from collections.abc import Sequence
from dataclasses import field
from typing import Union

from polymath.base.dataclasses import config, empty

# First time here? Read the README.md file in this directory.

# For pretty much any reasonable flat property bag
PropertyBagConfigType = dict[str, Union[bool, str, int]]

# HostConfig-related types
SourcePrefixesType = dict[str, str]
FunQueriesType = Sequence[str]
InfoConfigType = dict[str, Union[str, SourcePrefixesType, FunQueriesType]]
TokensConfigType = dict[str, dict[str, str]]
HostConfigType = dict[str, Union[str, InfoConfigType, TokensConfigType]]

# EnvironmentConfig-related types
EnvironmentConfigType = dict[str, str]


@config
class EnvironmentConfig:
    openai_api_key: str
    library_filename: str = None


@config
class InfoConfig:
    headername: str = ''
    placeholder: str = ''
    fun_queries: FunQueriesType = empty(list)
    source_prefixes: SourcePrefixesType = empty(dict)


@config
class HostConfig:
    restricted: PropertyBagConfigType = empty(dict)
    default_api_key: str = ''
    info: InfoConfig = InfoConfig()
    tokens: TokensConfigType = empty(dict)
    completions_options: PropertyBagConfigType = empty(dict)
