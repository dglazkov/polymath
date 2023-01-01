import argparse
import json

from cleantext import clean

MIN_CHUNK_SIZE = 50
MAX_CHUNK_SIZE = 500

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


def create_chunks(sections):
    count = 0
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
                    count += 1
                    yield (count, chunk)
                    buffer = []
                    buffer_size = 0
                continue
            # If just right, yield it
            count += 1
            yield (count, "\n".join(buffer))
            buffer = []
            buffer_size = 0
        # Yield the last buffer
        if buffer:
            count += 1
            yield (count, "\n".join(buffer))
            buffer = []
            buffer_size = 0


def generate_chunks(pages):
    for page_id, page in pages.items():
        sections = page["sections"]
        print(f"Processing {page['info']['url']} with {len(sections)} sections ...")
        for chunk_id, chunk in create_chunks(sections):
            yield (
                f"{page_id}-{chunk_id}",
                {
                    "text": chunk,
                    "info": page["info"]
                }
            )

def get_chunks(pages):
    """
    Main entry point for the Chunker.

    Chunks pages into strings that are well-sized for embeddings.

    Returns polymath-formatted object (as specified in
    https://github.com/dglazkov/polymath/blob/main/format.md)

    Arguments:
        pages -- Object that is an output of one of the importers.
    """
    content = {}
    for id, chunk in generate_chunks(pages):
        content[id] = chunk
    return {
        "version": 0,
        "embedding_model": 'openai.com:text-embedding-ada-002',
        "omit": 'embedding,token_count,similarity',
        "content": content
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "path", help="Path to the file containing page sections")
    parser.add_argument(
        '--output', help='Filename of where the output goes"', required=True)
    args = parser.parse_args()
  
    pages = json.load(open(args.path, 'r'))
    chunks = get_chunks(pages)
    print(f"Writing output to {args.output} ...")
    json.dump(chunks, open(args.output, "w"), indent="\t")
    print("Done.")
