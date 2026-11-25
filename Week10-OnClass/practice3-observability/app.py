from flask import Flask, jsonify
from prometheus_flask_exporter import PrometheusMetrics

app = Flask(__name__)
metrics = PrometheusMetrics(app)


@app.route("/orders", methods=["POST"])
def create_order():
    return jsonify({"id": 42}), 201


@app.route("/health")
def health():
    return "ok"


# http://host:8000/metrics san sang scrape
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)