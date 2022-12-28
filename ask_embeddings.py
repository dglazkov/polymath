import pickle
from random import shuffle
import os
import glob

import numpy as np
import openai
from transformers import GPT2TokenizerFast

EMBEDDINGS_MODEL_NAME = "text-embedding-ada-002"
COMPLETION_MODEL_NAME = "text-davinci-003"

SEPARATOR = "\n"
MAX_CONTEXT_LEN = 2048

def vector_similarity(x, y):
    return np.dot(np.array(x), np.array(y))


def get_embedding(text):
    result = openai.Embedding.create(
        model=EMBEDDINGS_MODEL_NAME,
        input=text
    )
    return result["data"][0]["embedding"]


def get_similarities(query_embedding, embeddings):
    return sorted([
        (vector_similarity(query_embedding, embedding), text, tokens, issue_id)
        for text, embedding, tokens, issue_id
        in embeddings], reverse=True)

EMBEDDINGS_DIR = 'out'
SAMPLE_EMBEDDINGS_FILE = 'sample-import-content.pkl'

def load_default_embeddings():
    files = glob.glob(os.path.join(EMBEDDINGS_DIR, '*.pkl'))
    if len(files):
        return load_multiple_embeddings(files)
    return load_embeddings(SAMPLE_EMBEDDINGS_FILE)

def load_multiple_embeddings(embeddings_file_names):
    embeddings = []
    issue_info = {}
    for file in embeddings_file_names:
        content = load_embeddings(file)
        embeddings.extend(content['embeddings'])
        issue_info.update(content['issue_info'])
    return {
        'embeddings': embeddings,
        'issue_info': issue_info
    }

def load_embeddings(embeddings_file):
    with open(embeddings_file, "rb") as f:
        return pickle.load(f)


def get_token_length(text):
    tokenizer = GPT2TokenizerFast.from_pretrained("gpt2")
    return len(tokenizer.tokenize(text))

def get_context(similiarities, token_count=MAX_CONTEXT_LEN):
    context = []
    context_len = 0

    tokenizer = GPT2TokenizerFast.from_pretrained("gpt2")
    separator_len = len(tokenizer.tokenize(SEPARATOR))

    issue_ids = set()

    for id, (_, text, tokens, issue_id) in enumerate(similiarities):
        context_len += tokens + separator_len
        if context_len > token_count:
            if len(context) == 0:
                context.append(text[:(token_count - separator_len)])
            break
        context.append(text)
        if id < 4:
            issue_ids.add(issue_id)
    return context, issue_ids


def get_issues(issue_ids, issue_info):
    return [issue_info[issue_id] for issue_id in issue_ids]


def get_completion(prompt):
    response = openai.Completion.create(
        model=COMPLETION_MODEL_NAME,
        prompt=prompt,
        temperature=0.7,
        max_tokens=256,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0
    )
    return response.choices[0].text.strip()


def get_completion_with_context(query, context):
    # Borrowed from https://github.com/openai/openai-cookbook/blob/838f000935d9df03e75e181cbcea2e306850794b/examples/Question_answering_using_embeddings.ipynb
    prompt = f"Answer the question as truthfully as possible using the provided context, and if the answer is not contained within the text below, say \"I don't know.\"\n\nContext:\n{context} \n\nQuestion:\n{query}\n\nAnswer:"
    return get_completion(prompt)

def ask(query, context_query = None, embeddings_file = None):
    if not context_query: context_query = query
    embeddings = load_embeddings(embeddings_file) if embeddings_file else load_default_embeddings()
    query_embedding = get_embedding(context_query)
    similiarities = get_similarities(query_embedding, embeddings["embeddings"])
    (context, issue_ids) = get_context(similiarities)

    issues = get_issues(issue_ids, embeddings["issue_info"])
    return get_completion_with_context(query, context), issues
