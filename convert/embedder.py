import argparse
import os

import openai
from dotenv import load_dotenv

import ask_embeddings


def add_embeddings(max_entries, library : ask_embeddings.Library):
    """
    Main entry point for the Embedder.

    Adds embeddings to the library. This happens in place by adding
    "embeddings" and "token_count" fields.
    If these fields already exist, they are not overwritten.

    Arguments:
        chunks -- polymath-formatted object (as specified in
        https://github.com/dglazkov/polymath/blob/main/format.md)
    """
    count = 0

    for id, chunk in library.chunks:
        if max_entries >= 0 and count >= max_entries:
            print("Reached max entries")
            break
        print(f"Processing new chunk {id} ({count + 1})")
        text = chunk["text"]
        if "embedding" not in chunk:
            print(f"Fetching embedding for {id}")
            chunk["embedding"] = ask_embeddings.get_embedding(text)
        if "token_count" not in chunk:
            print(f"Fetching token_count for {id}")
            chunk["token_count"] = ask_embeddings.get_token_count(text)
        library.set_chunk(id, chunk)
        count += 1


if __name__ == "__main__":
    load_dotenv()
    openai.api_key = os.getenv("OPENAI_API_KEY")

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "path", help="Path to the library to add embeddings to")
    parser.add_argument(
        "--output", help="Filename of where the output goes", required=True)
    parser.add_argument(
        "--max", help="The number of max entries to process. If negative, will process all.", default=-1, type=int)

    args = parser.parse_args()

    library = ask_embeddings.Library(filename=args.path)
    add_embeddings(args.max, library)
    print(f"Writing output to {args.output} ...")

    library.save(args.output)
    print("Done.")
