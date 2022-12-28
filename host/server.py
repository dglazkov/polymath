import os
import traceback

import openai
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request

from ask_embeddings import (get_context, get_embedding, get_issues,
                                       get_similarities, load_default_embeddings)

WANDERING_MEMORY = 60 * 60 * 2  # 2 hours, why not
WANDERING_VARIETY = 5

app = Flask(__name__)

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")


@app.route("/api/query", methods=["POST"])
def start():
    try:
        query = request.form["query"]
        if not query:
            return jsonify({
                "error": "Query is required"
            })
        embeddings = load_default_embeddings()
        query_embedding = get_embedding(query)
        similiarities = get_similarities(
            query_embedding, embeddings["embeddings"])
        (context, issue_ids) = get_context(similiarities)
        issues = get_issues(issue_ids, embeddings["issue_info"])
        print(issues)
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
    app.run(host='127.0.0.1', port=8080, debug=True)
