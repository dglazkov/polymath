import argparse
import json
import os

import openai
import urllib3
from dotenv import load_dotenv

from polymath import (Library, get_completion_with_context, get_embedding)

# TODO: Make this computed from the number of servers.
CONTEXT_TOKEN_COUNT = 1500

DEFAULT_CONFIG_FILE = "directory.SECRET.json"


def query_server(query_embedding, server, random=False):
    http = urllib3.PoolManager()
    fields = {
        "version": Library.CURRENT_VERSION,
        "access_token": server_tokens.get(server, ''),
        "query_embedding_model": Library.EMBEDDINGS_MODEL_ID,
        "count": CONTEXT_TOKEN_COUNT
    }
    if random:
        fields["sort"] = "random"
        fields["omit"] = "similarity,embedding"
    else:
        fields["query_embedding"] = query_embedding
        fields["sort"] = "similarity"
    response = http.request(
        'POST', server, fields=fields).data
    obj = json.loads(response)
    if 'error' in obj:
        error = obj['error']
        raise Exception(f"Server returned an error: {error}")
    return Library(data=obj)


parser = argparse.ArgumentParser()
parser.add_argument("query", help="The question to ask",
                    default="Tell me about 3P")
parser.add_argument("--dev", action="store_true",
                    help=f"If set, will use the dev_* properties for each endpoint in config if they exist")
parser.add_argument(
    "--config", help=f"A path to a config file to use. If not provided it will try to use {DEFAULT_CONFIG_FILE} if it exists. Pass \"\" explicitly to proactively ignore that file even if it exists", default=None)
parser.add_argument("--server", help="A server to use for querying",
                    action="append"),
parser.add_argument("--only", help=f"If provided, will ignore any hosts without this name or endpoint in {DEFAULT_CONFIG_FILE}", action="append")
parser.add_argument("--exclude", help=f"If provided, will ignore any hosts that have this name or endpoint in {DEFAULT_CONFIG_FILE}", action="append")
parser.add_argument("--completion", help="Request completion based on the query and context",
                    action=argparse.BooleanOptionalAction, default=True)
parser.add_argument("--random", help="Ask for a random set of chunks",
                    action=argparse.BooleanOptionalAction, default=False)
parser.add_argument("--verbose", help="Print out context and sources and other useful intermediate data",
                    action=argparse.BooleanOptionalAction, default=False)
args = parser.parse_args()

config = {}

config_file = args.config
complain_for_missing_config = True
if config_file == None:
    config_file = DEFAULT_CONFIG_FILE
    complain_for_missing_config = False

if config_file:
    if os.path.exists(config_file):
        print(f'Using config {config_file}')
        with open(config_file, 'r') as f:
            config = json.load(f)
    else:
        if complain_for_missing_config:
            print(f'{config_file} was not found.')

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

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

if 'hosts' in config:
    for (server_name, server_config) in config['hosts'].items():
        endpoint = server_config.get('endpoint', '')
        if dev_mode and 'dev_endpoint' in server_config:
            endpoint = server_config['dev_endpoint']
        if not endpoint:
            continue
        if len(only) and endpoint not in only and server_name not in only:
            print(f'Excluding {server_name} because neither it nor its endpoint was included in --only')
            continue
        if len(exclude) and (endpoint in exclude or server_name in exclude):
            print(f'Excluding {server_name} because either it or its endpoint was included in --exclude')
            continue
        server_list.append(endpoint)
        server_tokens[endpoint] = server_config.get('token', '')

if len(server_list) == 0:
    print('No hosts provided.')

if args.verbose:
    if args.random:
        print("Getting random chunks ...")
    else:
        print(f"Getting embedding for \"{query}\" ...")

query_vector = None if args.random else Library.base64_from_vector(
    get_embedding(query))

context = []
sources = []
for server in server_list:
    print(f"Querying {server} ...") if args.verbose else None
    # for now, just combine contexts
    library = query_server(query_vector, server, random=args.random)
    if library.message:
        print(f'{server} said: ' + library.message)
    context.extend(library.text)
    sources.extend([info.url for info in library.unique_infos])

sources = "\n  ".join(sources)

if args.verbose:
    context_str = "\n\n".join(context)
    print(f"Context:\n{context_str}")
    print(f"\nSources:\n  {sources}")

if args.completion:
    print("Getting completion ...") if args.verbose else None
    print(f"\nAnswer:\n{get_completion_with_context(query, context)}")
    print(f"\nSources:\n  {sources}")
