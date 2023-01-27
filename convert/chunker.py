import argparse
import json

from cleantext import clean

MIN_CHUNK_SIZE = 500
MAX_CHUNK_SIZE = 1500

# The idea of a chunker is to take in a list of text strings and
# chunk it into another list of text strings, where each string is
# more interesting for the embedding model.

# For example, a very short string has too little information for
# the embedding model to be useful: it contains very little context.
# On the other hand, a very long string has a lot more context, but
# it also uses up the token prompt space, which means that it will
# either dominate the prompt or be cut off.

# Chunker operates with the presumption that there is a goldielocks
# space: a string that is just the right size for the embedding model.

# The goldielocks space is a band between two sizes:
# "too small" and "too big".

GOLDIELOCKS = {
    "min": MAX_CHUNK_SIZE - MIN_CHUNK_SIZE,
    "max": MAX_CHUNK_SIZE + MIN_CHUNK_SIZE
}

# Whenever chunker takes in a string, it will evaluate it against
# the goldielocks space. If it is too small, it will accumulate
# it into a buffer. If it is too big, it will split it up into
# smaller strings. If it is just right, it will yield it.

# When a string is split up, occasionally, the remaining leftover
# of the split will be kind of "meh": too small for its own chunk.
# In that case, it will be appended to the previous chunk.
MEH_SIZE = GOLDIELOCKS["min"] / 2

# TODO: Make this logic use GPT-2 tokenizer rather than character lengths.


def get_clean_text(text: str):
    return clean(text,
                 no_urls=True,
                 lower=False,
                 no_emoji=True)


def make_chunky_sentences(text: str):
    result = []
    while len(text) > MAX_CHUNK_SIZE:
        split_index = text[:MAX_CHUNK_SIZE].rfind(".")
        if split_index == -1:
            result.append(text)
            break
        result.append(text[:split_index + 1])
        text = text[split_index + 1:].strip(" ")
    if len(result) > 0 and len(text) < MEH_SIZE:
        result[-1] += text
    else:
        result.append(text)
    return result


def generate_chunks(sections):
    """
    Main entry point for the Chunker.

    Chunks a page into strings that are well-sized for embeddings.

    Returns chunks that can be used as output of the Importer.get_chunks

    Arguments:
        sections -- list of sections, each section is a list of strings,
            representing a text chunk

    """
    buffer = []
    buffer_size = 0
    for section in sections:
        for line in section:
            text = get_clean_text(line)
            # Skip empty lines.
            if not text:
                continue
            text_size = len(text)
            buffer.append(text)
            buffer_size += text_size
            # If too small, continue accumulating
            if (buffer_size) < GOLDIELOCKS["min"]:
                continue
            # If too large, split up in multiple chunks
            if (buffer_size) > GOLDIELOCKS["max"]:
                chunks = make_chunky_sentences("\n".join(buffer))
                for chunk in chunks:
                    yield chunk
                    buffer = []
                    buffer_size = 0
                continue
            # If just right, yield it
            yield "\n".join(buffer)
            buffer = []
            buffer_size = 0
        # Yield the last buffer
        if buffer:
            yield "\n".join(buffer)
            buffer = []
            buffer_size = 0

