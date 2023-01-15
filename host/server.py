import argparse
import os
import traceback

import openai
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request
from flask_compress import Compress

import polymath

DEFAULT_TOKEN_COUNT = 1000

app = Flask(__name__)
Compress(app)

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")
library_filename = os.getenv("LIBRARY_FILENAME")

library = polymath.load_libraries(library_filename, True)
_, restricted_message = polymath.restricted_configuration()


@app.route("/", methods=["POST"])
def start():
    try:
        query_embedding = request.form.get("query_embedding")
        query_embedding_model = request.form.get("query_embedding_model")
        count = request.form.get(
            "count", DEFAULT_TOKEN_COUNT, type=int)
        count_type = request.form.get("count_type")
        version = request.form.get('version', -1, type=int)
        sort = request.form.get('sort')
        sort_reversed = request.form.get('sort_reversed') is not None
        seed = request.form.get('seed')
        omit = request.form.get('omit')
        access_token = request.form.get('access_token', '')
        result = library.query(version=version, query_embedding=query_embedding,
                               query_embedding_model=query_embedding_model, count=count,
                               count_type=count_type, sort=sort, sort_reversed=sort_reversed,
                               seed=seed, omit=omit, access_token=access_token)
        return jsonify(result.serializable())

    except Exception as e:
        return jsonify({
            "error": f"{e}\n{traceback.print_exc()}"
        })


@app.route("/", methods=["GET"])
def start_sample():
    return render_template("query.html", restricted_message=restricted_message)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--port', help='Number of the port to run the server on (8080 by default).', default=8080, type=int)
    args = parser.parse_args()
    app.run(host='127.0.0.1', port=args.port, debug=True)
