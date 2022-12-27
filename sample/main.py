import os
import sys

#TODO: remove this ugly hack to import the ask_embeddings in the containing directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import ask_embeddings
import openai
from dotenv import load_dotenv

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

query = "Tell me about 3P"

print(ask_embeddings.ask(query))