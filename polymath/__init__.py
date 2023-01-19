from polymath.library import Library, CURRENT_VERSION, EMBEDDINGS_MODEL_ID
from polymath.ask_embeddings import (
    LIBRARY_DIR,
    get_embedding,
    load_libraries,
    get_token_count,
    get_context_for_library,  # TODO: factor this into Library
    get_chunk_infos_for_library,  # TODO: factor this into Library
    get_completion,
    get_completion_with_context,
    ask
)
from polymath.access import restricted_configuration
