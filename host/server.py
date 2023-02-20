import argparse
import traceback

from flask import Flask, jsonify, render_template, request
from flask_compress import Compress
from flask_cors import CORS

from typing import Union

import polymath
from polymath.config.json import JSONConfigStore
from polymath.config.env import EnvConfigStore
from polymath.config.types import EnvironmentConfig, HostConfig

DEFAULT_TOKEN_COUNT = 1000

app = Flask(__name__)
CORS(app)
Compress(app)

env_config = EnvConfigStore().load(EnvironmentConfig)
host_config = JSONConfigStore().load(HostConfig)

library = polymath.load_libraries(env_config.library_filename, True)


class Endpoint:
    def __init__(self, library : polymath.Library):
        self.library = library

    def query(self, args: dict[str, Union[str, int]]):
        result = self.library.query(args)
        return jsonify(result.serializable())


@app.route("/", methods=["POST"])
def index():
    try:
        endpoint = Endpoint(library)
        content_type = request.headers.get('Content-Type')
        if (content_type == 'application/json'):
            json = request.json
            if not json:
                return jsonify({
                    "error": "No arguments provided"
                })
            return endpoint.query({
                'count': DEFAULT_TOKEN_COUNT,
                **json
            })
        else:
            return endpoint.query({
                'count': DEFAULT_TOKEN_COUNT,
                **request.form.to_dict()
            })

    except Exception as e:
        return jsonify({
            "error": f"{e}\n{traceback.format_exc()}"
        })


@app.route("/", methods=["GET"])
def render_index():
    return render_template("query.html", config=host_config)

@app.route('/_ah/warmup')
def warmup():
    return ('', 204)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--port', help='Number of the port to run the server on (8080 by default).', default=8080, type=int)
    args = parser.parse_args()
    app.run(host='127.0.0.1', port=args.port, debug=True)
