import argparse
import os

import openai
from dotenv import load_dotenv

from ask_embeddings import ask

parser = argparse.ArgumentParser()
parser.add_argument('query', help='The question to ask', default="Tell me about 3P")
parser.add_argument('--context', help='The query to use to fetch the context', default='')
args = parser.parse_args()

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

query = args.query
context = args.context

print(ask(query, context))