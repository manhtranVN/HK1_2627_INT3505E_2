from flask import Flask, jsonify, request
from werkzeug.exceptions import HTTPException

app = Flask(__name__)
resources = {1: {"id": 1, "name": "Demo"}}


class ProblemError(Exception):
    def __init__(self, status, title, detail=None, type="about:blank"):
        self.status = status
        self.title = title
        self.detail = detail
        self.type = type


def problem(status, title, detail=None, type="about:blank"):
    body = {
        "type": type,
        "title": title,
        "status": status,
        "detail": detail,
        "instance": request.path,
    }
    resp = jsonify(body)
    resp.status_code = status
    resp.content_type = "application/problem+json"
    return resp


@app.errorhandler(ProblemError)
def handle_problem(e):
    return problem(e.status, e.title, e.detail, e.type)


@app.errorhandler(HTTPException)
def handle_http(e):
    return problem(e.code, e.name, e.description)

@app.errorhandler(Exception)
def handle_unexpected(e):
    app.logger.exception("Unhandled exception")
    return problem(500, "Internal Server Error", "An unexpected error occurred.")


@app.get("/resources/<int:id>")
def get_resource(id):
    if id not in resources:
        raise ProblemError(404, "Not Found", f"Resource {id} does not exist.")
    return jsonify(resources[id])


@app.get("/boom")
def boom():
    return 1 / 0  


if __name__ == "__main__":
    app.run(debug=True)