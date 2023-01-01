import argparse
import json
import os

import openai
import urllib3
from dotenv import load_dotenv

from ask_embeddings import (base64_from_vector, get_completion_with_context,
                            get_embedding, load_library_from_json_blob,
                            get_context_for_library, get_chunk_infos_for_library,
                            CURRENT_VERSION, EMBEDDINGS_MODEL_ID)

# TODO: Make this computed from the number of servers.
CONTEXT_TOKEN_COUNT = 1500


def query_server(query_embedding, server):
    http = urllib3.PoolManager()
    response = http.request(
        'POST', server, fields={
            "version": CURRENT_VERSION,
            "query_embedding": query_embedding,
            "query_embedding_model": EMBEDDINGS_MODEL_ID,
            "count": CONTEXT_TOKEN_COUNT}).data
    obj =json.loads(response)
    if 'error' in obj:
        error = obj['error']
        raise Exception(f"Server returned an error: {error}")
    return load_library_from_json_blob(response)


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
sources = []
for server in server_list:
    print(f"Querying {server} ...")
    # for now, just combine contexts
    library = query_server(query_vector, server)
    context.extend(get_context_for_library(library))
    sources.extend([chunk["url"] for chunk in get_chunk_infos_for_library(library)])

sources = "\n  ".join(sources)

print("Getting completion ...")
print(f"\nAnswer:\n{get_completion_with_context(query, context)}")
print(f"\nSources:\n  {sources}")
