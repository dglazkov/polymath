from polymath.library import Library, Bit, CURRENT_VERSION, EMBEDDINGS_MODEL_ID
from polymath.ask_embeddings import (
    LIBRARY_DIR,
    get_embedding,
    get_max_tokens_for_completion_model,
    load_libraries,
    get_token_count,
    get_completion,
    get_completion_with_context,
    ask
)
from polymath.access import host_config
