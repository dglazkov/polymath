import os
import sys
import argparse

#TODO: remove this ugly hack to import the ask_embeddings in the containing directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import ask_embeddings
import openai
from dotenv import load_dotenv

parser = argparse.ArgumentParser()
parser.add_argument('query', help='The question to ask', default="Tell me about 3P")
parser.add_argument('context', help='The query to use to fetch the context', default='')
args = parser.parse_args()

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

query = args.query
context = args.context

print(ask_embeddings.ask(query, context))