import glob
import os
from time import sleep

import openai
from transformers import GPT2TokenizerFast

from .library import Library

COMPLETION_MODEL_NAME = "text-davinci-003"

LIBRARY_DIR = 'libraries'
SAMPLE_LIBRARIES_FILE = 'sample-content.json'


def get_max_tokens_for_completion_model(completion_model_id=COMPLETION_MODEL_NAME):
    if completion_model_id == "text-davinci-003":
        return 4000
    raise Exception(f'Unknown model id: {completion_model_id}')


def get_embedding_model_name_from_id(model_id):
    return model_id.split(':')[1]


def get_embedding(text, model_id=Library.EMBEDDINGS_MODEL_ID):
    # Occasionally, API returns an error.
    # Retry a few times before giving up.
    retry_count = 10
    result = None
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
    if result is None:
        return None
    else:
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


def get_max_answer_length(prompt, completion_model=COMPLETION_MODEL_NAME):
    max_tokens = get_max_tokens_for_completion_model(completion_model)
    prompt_length = get_token_count(prompt)
    return max_tokens - prompt_length


def get_completion(prompt, answer_length=None, completion_model=COMPLETION_MODEL_NAME):
    if answer_length is None:
        answer_length = get_max_answer_length(prompt, completion_model=completion_model)
    response = openai.Completion.create(
        model=completion_model,
        prompt=prompt,
        temperature=0.7,
        max_tokens=answer_length,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0
    )
    return response.choices[0].text.strip()


def get_completion_with_context(query, context, answer_length=None, completion_model=COMPLETION_MODEL_NAME):
    # Borrowed from https://github.com/openai/openai-cookbook/blob/838f000935d9df03e75e181cbcea2e306850794b/examples/Question_answering_using_embeddings.ipynb

    prompt = f"Answer the question as truthfully as possible using the provided context, and if the answer is not contained within the text below, say \"I don't know.\"\n\nContext:\n{context} \n\nQuestion:\n{query}\n\nAnswer:"
    return get_completion(prompt, answer_length=answer_length, completion_model=completion_model)


def ask(query, context_query=None, library_file=None, answer_length=None, completion_model=COMPLETION_MODEL_NAME):
    if not context_query:
        context_query = query
    library = load_libraries(library_file)

    query_embedding = get_embedding(context_query)
    library.compute_similarities(query_embedding)
    library.sort = 'similarity'

    context = library.text
    return get_completion_with_context(query, context, answer_length=answer_length, completion_model=completion_model), library.unique_infos
