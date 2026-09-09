from flask import Flask, jsonify
app = Flask(__name__)
ORDERS = {
    "order1":{"id":"order1", "status":"paid"},
    "order2":{"id":"order2", "status":"pending"},
    "order3":{"id":"order3", "status":"shipped"},
    "order4":{"id":"order4", "status":"delivered"},
}

@app.route("/orders/<order_id>", methods=["DELETE"])
def delete_order(order_id):
    order = ORDERS.get(order_id)
    if order is None:
        return {"error": "not found"}, 404
    if order["status"] in ("shipped", "delivered"):
        return {"error": "cannot delete"}, 409
    ORDERS.pop(order_id, None)
    return "", 204

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
