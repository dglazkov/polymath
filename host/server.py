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
config = polymath.host_config()


class Endpoint:
    def __init__(self, library):
        self.library = library

    def query(self, args):
        query_embedding = args.get('query_embedding')
        query_embedding_model = args.get('query_embedding_model')
        count = args.get(
            'count', DEFAULT_TOKEN_COUNT, type=int)
        count_type = args.get('count_type')
        version = args.get('version', -1, type=int)
        sort = args.get('sort')
        sort_reversed = args.get('sort_reversed') is not None
        seed = args.get('seed')
        omit = args.get('omit')
        access_token = args.get('access_token', '')
        result = self.library.query(version=version, query_embedding=query_embedding,
                                    query_embedding_model=query_embedding_model, count=count,
                                    count_type=count_type, sort=sort, sort_reversed=sort_reversed,
                                    seed=seed, omit=omit, access_token=access_token)
        return jsonify(result.serializable())


@app.route("/", methods=["POST"])
def index():
    try:
        endpoint = Endpoint(library)
        return endpoint.query(request.form)

    except Exception as e:
        return jsonify({
            "error": f"{e}\n{traceback.format_exc()}"
        })


@app.route("/", methods=["GET"])
def render_index():
    return render_template("query.html", config=config)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--port', help='Number of the port to run the server on (8080 by default).', default=8080, type=int)
    args = parser.parse_args()
    app.run(host='127.0.0.1', port=args.port, debug=True)
