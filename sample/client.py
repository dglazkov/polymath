import argparse
import json
import os

import openai
import urllib3
from dotenv import load_dotenv

from ask_embeddings import (base64_from_vector, get_completion_with_context,
                            get_embedding)

# TODO: Make this computed from the number of servers.
CONTEXT_TOKEN_COUNT = 1500


def query_server(query, server):
    http = urllib3.PoolManager()
    response = http.request(
        'POST', f"{server}/api/query", fields={
            "query": query,
            "token_count": CONTEXT_TOKEN_COUNT}).data
    return json.loads(response)


parser = argparse.ArgumentParser()
parser.add_argument("query", help="The question to ask",
                    default="Tell me about 3P")
parser.add_argument("--server", help="A server to use for querying",
                    action="append", required=True),
args = parser.parse_args()

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

query = args.query
server_list = args.server

print(f"Getting embedding for \"{query}\" ...")
query_vector = base64_from_vector(get_embedding(query))

context = []
for server in server_list:
    print(f"Querying {server} ...")
    # for now, just combine contexts
    context.extend(query_server(query_vector, server)["context"])

print("Getting completion ...")
print(get_completion_with_context(query, context))
