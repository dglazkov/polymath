import argparse
import json
import os

import openai
import urllib3
from dotenv import load_dotenv

import ask_embeddings

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

context = []
for server in server_list:
    print(f"Querying {server} ...")
    # for now, just combine contexts
    context.extend(query_server(query, server)["context"])

print(ask_embeddings.get_completion_with_context(query, context))
