import argparse
import os
import traceback

import openai
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request

from ask_embeddings import (get_context, get_chunks,
                            get_similarities, load_library, vector_from_base64)

DEFAULT_TOKEN_COUNT = 1000

app = Flask(__name__)

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")
library_filename = os.getenv("LIBRARY_FILENAME")


@app.route("/", methods=["POST"])
def start():
    try:
        query = request.form["query"]
        token_count = request.form.get(
            "token_count", DEFAULT_TOKEN_COUNT, type=int)
        if not query:
            return jsonify({
                "error": "Query is required"
            })
        library = load_library(library_filename)
        query_embedding = vector_from_base64(query)
        similiarities = get_similarities(
            query_embedding, library)
        (context, chunk_ids) = get_context(similiarities, token_count)
        chunks = get_chunks(chunk_ids, library)
        return jsonify({
            "context": context,
            "chunks": chunks
        })

    except Exception as e:
        return jsonify({
            "error": f"{e}\n{traceback.print_exc()}"
        })


@app.route("/", methods=["GET"])
def start_sample():
    return render_template("query.html")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'filename', help='Relative to the root of the project, the path to the embeddings file')
    parser.add_argument(
        '--port', help='Number of the port to run the server on (8080 by default).', default=8080, type=int)
    args = parser.parse_args()

    library_filename = args.filename
    port = args.port

    app.run(host='127.0.0.1', port=port, debug=True)
