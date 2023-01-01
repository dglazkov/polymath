import argparse
import os
import traceback

import openai
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request
from flask_compress import Compress

from ask_embeddings import (library_for_query, load_library,
                            serializable_library, load_default_libraries)

DEFAULT_TOKEN_COUNT = 1000

app = Flask(__name__)
Compress(app)

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")
library_filename = os.getenv("LIBRARY_FILENAME")

library = load_library(
    library_filename) if library_filename else load_default_libraries(True)


@app.route("/", methods=["POST"])
def start():
    try:
        query_embedding = request.form.get("query_embedding")
        query_embedding_model = request.form.get("query_embedding_model")
        token_count = request.form.get(
            "token_count", DEFAULT_TOKEN_COUNT, type=int)
        version = request.form.get('version', -1, type=int)
        sort = request.form.get('sort')
        result = library_for_query(library, version=version, query_embedding=query_embedding,
                                    query_embedding_model=query_embedding_model, count=token_count,
                                    sort=sort)
        return jsonify(serializable_library(result))

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
        '--port', help='Number of the port to run the server on (8080 by default).', default=8080, type=int)
    args = parser.parse_args()
    app.run(host='127.0.0.1', port=args.port, debug=True)
