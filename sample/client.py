import argparse
import json
import os
import sys

import openai
import urllib3

from polymath import (Library, get_completion_with_context, get_embedding,
                      get_max_tokens_for_completion_model)
from polymath.config.env import EnvConfigStore
from polymath.config.json import JSONConfigStore
from polymath.config.types import DirectoryConfig, EnvironmentConfig

config_store = JSONConfigStore()

DEFAULT_CONTEXT_TOKEN_COUNT = 1500

DEFAULT_CONFIG_FILE = config_store.default(DirectoryConfig)


def query_server(query_embedding, server, random=False, count=DEFAULT_CONTEXT_TOKEN_COUNT):
    http = urllib3.PoolManager()
    fields = {
        "version": Library.CURRENT_VERSION,
        "access_token": server_tokens.get(server, ''),
        "query_embedding_model": Library.EMBEDDINGS_MODEL_ID,
        "count": count
    }
    if random:
        fields["omit"] = "similarity,embedding"
    else:
        fields["query_embedding"] = query_embedding
    response = http.request(
        'POST', server, fields=fields).data
    obj = json.loads(response)
    if 'error' in obj:
        error = obj['error']
        raise Exception(f"Server returned an error: {error}")
    return Library(data=obj)


parser = argparse.ArgumentParser()
parser.add_argument(
    "query",
    help="The question to ask",
    default="Tell me about 3P")
parser.add_argument(
    "--dev",
    action="store_true",
    help=f"If set, will use the dev_* properties for each endpoint in config if they exist")
parser.add_argument(
    "--config",
    help=f"A path to a config file to use. If not provided it will try to use {DEFAULT_CONFIG_FILE} if it exists. Pass \"\" explicitly to proactively ignore that file even if it exists",
    default=None)
parser.add_argument(
    "--server",
    help="A server to use for querying",
    action="append")
parser.add_argument(
    "--only",
    help=f"If provided, will ignore any hosts without this name or endpoint in {DEFAULT_CONFIG_FILE}",
    action="append")
parser.add_argument(
    "--exclude",
    help=f"If provided, will ignore any hosts that have this name or endpoint in {DEFAULT_CONFIG_FILE}",
    action="append")
parser.add_argument(
    "--completion",
    help="Request completion based on the query and context",
    action=argparse.BooleanOptionalAction,
    default=True)
parser.add_argument(
    "--random", help="Ask for a random set of bits",
    action=argparse.BooleanOptionalAction,
    default=False)
parser.add_argument(
    "--verbose", help="Print out context and sources and other useful intermediate data",
    action=argparse.BooleanOptionalAction,
    default=False)
args = parser.parse_args()

config = config_store.load(DirectoryConfig, args.config)
env_config = EnvConfigStore().load(EnvironmentConfig)
openai.api_key = env_config.openai_api_key

query = args.query
server_list = args.server
dev_mode = args.dev
only = args.only
if not only:
    only = []
exclude = args.exclude
if not exclude:
    exclude = []

if not server_list:
    server_list = []

server_tokens = {}

for (server_name, server_config) in config.hosts.items():
    endpoint = server_config.endpoint
    if dev_mode and server_config.dev_endpoint:
        endpoint = server_config.dev_endpoint
    if not endpoint:
        continue
    if len(only) and endpoint not in only and server_name not in only:
        print(
            f'Excluding {server_name} because neither it nor its endpoint was included in --only')
        continue
    if len(exclude) and (endpoint in exclude or server_name in exclude):
        print(
            f'Excluding {server_name} because either it or its endpoint was included in --exclude')
        continue
    server_list.append(endpoint)
    if server_config.token is not None:
        server_tokens[endpoint] = server_config.token

if len(server_list) == 0:
    print('No hosts provided.')
    sys.exit(1)

if args.verbose:
    if args.random:
        print("Getting random bits ...")
    else:
        print(f"Getting embedding for \"{query}\" ...")

query_vector = None if args.random else Library.base64_from_vector(
    get_embedding(query))

# TODO: allow setting the answer_length (see issue #49)
answer_length = 256
# TODO: we need to allow room for the actual prompt, as well as separators
# between bits. This is a hand-tuned margin, but it should be calculated
# automatically.
context_count = get_max_tokens_for_completion_model() - 500

# We ask each endpoint for content assuming that all of its results will be
# better than any other server. We then trim down to the best content across all
# servers.
context_per_server = context_count - answer_length

combined_library = Library()

for server in server_list:
    print(f"Querying {server} ...") if args.verbose else None
    library = query_server(query_vector, server,
                           random=args.random, count=context_count)
    if library.message:
        print(f'{server} said: ' + library.message)
    combined_library.extend(library)

sliced_library = combined_library.slice(context_count)

sources = [info.url for info in sliced_library.unique_infos]
context = sliced_library.text

sources = "\n  ".join(sources)

if args.verbose:
    context_str = "\n\n".join(context)
    print(f"Context:\n{context_str}")
    print(f"\nSources:\n  {sources}")

if args.completion:
    print("Getting completion ...") if args.verbose else None
    print(
        f"\nAnswer:\n{get_completion_with_context(query, context, answer_length=answer_length)}")
    print(f"\nSources:\n  {sources}")
