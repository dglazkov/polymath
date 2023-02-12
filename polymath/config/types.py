
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
    '''
    General environment configuration

    Used for configuring the environment in which this Polymath instance is running.

    Attributes:
        openai_api_key: The OpenAI API key to use
        library_filename: The filename of the Polymath library to use
    '''
    openai_api_key: str
    library_filename: str = None


@config
class InfoConfig:
    '''
    Query page custom parameters

    Used to customize the Polymath query page.

    Attributes:
        headername: A prefix that goes in front of the Polymath title page
        placeholder: A placeholder for the query input field
        fun_queries: A list of fun queries to display when the user clicks the "magic" icon
        source_prefixes: A dictionary of prefixes to use for each source URL 
    '''
    headername: str = ''
    placeholder: str = ''
    fun_queries: FunQueriesType = empty(list)
    source_prefixes: SourcePrefixesType = empty(dict)


@config(id='host')
class HostConfig:
    '''
    Host configuration

    Used to configure a host for Polymath.

    Attributes:
        default_private_access_tag: Defaults to 'unpublished' if not set.
        restricted: Query page customizations for restricted access cases
        default_api_key: The default API key to use for this host
        info: Query page custom parameters
        tokens: Restricted access tokens
    '''
    default_private_access_tag: str = ''
    restricted: PropertyBagConfigType = empty(dict)
    default_api_key: str = ''
    info: InfoConfig = InfoConfig()
    tokens: TokensConfigType = empty(dict)
    completions_options: PropertyBagConfigType = empty(dict)


@config
class EndpointConfig:
    '''
    Directory endpoint configuration

    Attributes:
        endpoint: Hostname[:port] of the endpoint
        dev_endpoint: Hostname[:port] of the endpoint used when run in '--dev` mode
        token: Token to use when accessing the endpoint
    '''
    endpoint: str
    dev_endpoint: str = None
    token: str = None


@config(id='directory')
class DirectoryConfig:
    '''
    Directory configuration

    Used to configure the directory of Polymath instances.

    Attributes:
        hosts: A dictionary of endpoints to configure. 
               The key is the friendly name of the endpoint.
               The value is the endpoint configuration.
    '''
    hosts: dict[str, EndpointConfig] = empty(dict)
