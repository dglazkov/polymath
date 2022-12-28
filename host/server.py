import argparse
import os
import traceback

import openai
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request

from ask_embeddings import (get_context, get_issues,
                            get_similarities, load_library, vector_from_base64)

WANDERING_MEMORY = 60 * 60 * 2  # 2 hours, why not
WANDERING_VARIETY = 5

parser = argparse.ArgumentParser()
parser.add_argument(
    'filename', help='Relative to the root of the project, the path to the embeddings file')
parser.add_argument(
    '--port', help='Number of the port to run the server on (8080 by default).', default=8080, type=int)
args = parser.parse_args()

embeddings_filename = args.filename
port = args.port

DEFAULT_TOKEN_COUNT = 1000

app = Flask(__name__)

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")


@app.route("/api/query", methods=["POST"])
def start():
    try:
        query = request.form["query"]
        token_count = request.form.get(
            "token_count", DEFAULT_TOKEN_COUNT, type=int)
        if not query:
            return jsonify({
                "error": "Query is required"
            })
        library = load_library(embeddings_filename)
        query_embedding = vector_from_base64(query)
        similiarities = get_similarities(
            query_embedding, library["embeddings"])
        (context, issue_ids) = get_context(similiarities, token_count)
        issues = get_issues(issue_ids, library["issue_info"])
        return jsonify({
            "context": context,
            "issues": issues
        })

    except Exception as e:
        return jsonify({
            "error": f"{e}\n{traceback.print_exc()}"
        })


@app.route("/api/query", methods=["GET"])
def start_sample():
    return render_template("query.html")


if __name__ == "__main__":
    app.run(host='127.0.0.1', port=port, debug=True)
