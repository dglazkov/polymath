
from collections.abc import Sequence
from typing import Union, Literal

from polymath.base.dataclasses import config, empty

# First time here? Read the README.md file in this directory.

# HostConfig-related types
SourcePrefixesType = dict[str, str]
FunQueriesType = Sequence[str]
AccessTagsType = Sequence[str]


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
    library_filename: str = ''


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


@config
class RestrictedConfig:
    '''
    Restricted sub-config for host

    Used to configure how much a host should reveal about restricted bits.

    Attributes:
        count: Whether to reveal a count of how many items were restricted.
        message: The message to show to the user about how to gain access if the bits were restricted.
    '''
    count: bool = False
    message: str = ''


@config
class TokenConfig:
    '''
    Token sub-config for host

    Used to configure properties for one user's token have which access permissions

    Attributes:
        token: The secret token that will grant access
        description: Free-form text describing the user
        access_tags: a list of strings of access tags to provide acceess to. If not provided defaults to ['unpublished']
    '''
    token: str = ''
    description: str = ''
    access_tags: AccessTagsType = empty(list)


@config
class CompletionsOptionsConfig:
    '''
    The completions_options sub-config for host

    Used to configure what is sent back to the OpenAI server. See https://platform.openai.com/docs/api-reference/completions for documentation

    Attributes:
       model: The completion model to use
       prompt_template: The prompt to use
       max_tokens: the number of tokens in the response
       temperature: The temperature
       top_p: Alternate to temperature
       n: how many responses to return
       stream: Whether to stream
       logprobs: Include the probabilities
       stop: The stop string
       debug: Whether to return debug information
    '''
    model: Literal["text-davinci-003"] = "text-davinci-003"
    prompt_template: str = "Answer the question as truthfully as possible using the provided context, and if don't have the answer, say \"I don't know\" and suggest looking for this information elsewhere.\n\nContext:\n{context} \n\nQuestion:\n{query}\n\nAnswer:"
    max_tokens: int = 256
    temperature: float = 0
    top_p: float = 1
    n: int = 1
    stream: bool = False
    logprobs: Union[int, None] = None
    stop: str = "\n"
    debug: bool = False


@config(id='host')
class HostConfig:
    '''
    Host configuration

    Used to configure a host for Polymath.

    Attributes:
        endpoint: The URL where this endpoint is publicly accessible
        default_private_access_tag: Defaults to 'unpublished' if not set.
        restricted: Query page customizations for restricted access cases
        default_api_key: The default API key to use for this host
        info: Query page custom parameters
        tokens: Restricted access tokens
    '''
    endpoint: str = ''
    default_private_access_tag: str = ''
    restricted: RestrictedConfig = empty(RestrictedConfig)
    default_api_key: str = ''
    info: InfoConfig = empty(InfoConfig)
    tokens: dict[str, TokenConfig] = empty(dict)
    completions_options: CompletionsOptionsConfig = empty(CompletionsOptionsConfig)


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
    dev_endpoint: str = ''
    token: str = ''


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
