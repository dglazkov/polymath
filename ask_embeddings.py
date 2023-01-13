import glob
import os
from time import sleep

import openai
from transformers import GPT2TokenizerFast

from library import Library

COMPLETION_MODEL_NAME = "text-davinci-003"

LIBRARY_DIR = 'libraries'
SAMPLE_LIBRARIES_FILE = 'sample-content.json'


def get_embedding_model_name_from_id(model_id):
    return model_id.split(':')[1]


def get_embedding(text, model_id=Library.EMBEDDINGS_MODEL_ID):
    # Occasionally, API returns an error.
    # Retry a few times before giving up.
    retry_count = 10
    while retry_count > 0:
        try:
            result = openai.Embedding.create(
                model=get_embedding_model_name_from_id(model_id),
                input=text
            )
            break
        except Exception as e:
            print(f'openai.Embedding.create error: {e}')
            print("Retrying in 20 seconds ...")
            sleep(20)
            retry_count -= 1
    return result["data"][0]["embedding"]


def load_default_libraries(fail_on_empty=False) -> Library:
    files = glob.glob(os.path.join(LIBRARY_DIR, '**/*.json'), recursive=True)
    if len(files):
        return load_multiple_libraries(files)
    if fail_on_empty:
        raise Exception('No libraries were in the default library directory.')
    return Library(filename=SAMPLE_LIBRARIES_FILE)


def load_libraries_in_directory(directory) -> Library:
    files = glob.glob(os.path.join(directory, '**/*.json'), recursive=True)
    return load_multiple_libraries(files)


def load_libraries(file=None, fail_on_empty=False) -> Library:
    if file:
        return Library(filename=file)
    return load_default_libraries(fail_on_empty)


def load_multiple_libraries(library_file_names) -> Library:
    result = Library()
    for file in library_file_names:
        library = Library(filename=file)
        result.extend(library)
    return result


def get_token_count(text):
    tokenizer = GPT2TokenizerFast.from_pretrained("gpt2")
    return len(tokenizer.tokenize(text))


def get_context_for_library(library: Library):
    """
    Returns an array of all text for every chunk in library
    """
    return [chunk['text'] for (_, chunk) in library.chunks]


def get_chunk_infos_for_library(library: Library):
    """
    Returns all infos for all chunks in library
    """
    infos = []
    if "similarity" in library.fields_to_omit:
        infos = [(_, chunk['info']) for (_, chunk) in library.chunks]
    else:
        infos = [(chunk["similarity"], chunk['info'])
                 for (_, chunk) in library.chunks]
        infos.sort(reverse=True)
    unique_infos = []
    urls = []
    for _, info in infos:
        url = info["url"]
        if url not in urls:
            unique_infos.append(info)
            urls.append(info["url"])
    return unique_infos


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


def ask(query, context_query=None, library_file=None):
    if not context_query:
        context_query = query
    library = load_libraries(library_file)

    query_embedding = get_embedding(context_query)
    similiarities_dict = library.similarities(query_embedding)
    context_dict = Library.get_context(similiarities_dict.keys(), library)

    context = list(context_dict.values())
    chunk_ids = list(context_dict.keys())

    infos = [library.chunk(chunk_id)['info'] for chunk_id in chunk_ids]
    return get_completion_with_context(query, context), infos
