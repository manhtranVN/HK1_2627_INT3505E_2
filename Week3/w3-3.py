import base64
import json
import random
from flask import Flask, jsonify, request

app = Flask(__name__)

random.seed(1)
STATUSES = ["pending", "paid", "shipped", "cancelled"]
orders = [
    {
        "id": i,
        "customer_id": random.randint(1, 5),
        "status": random.choice(STATUSES),
        "total": random.randint(10, 500) * 1000,
        "created_at": f"2026-09-{i:02d}T10:00:00Z",
    }
    for i in range(1, 31)
]
SORTABLE = {"id", "total", "created_at"}
ALL_FIELDS = set(orders[0])


def bad_request(detail):
    resp = jsonify({
        "type": "about:blank",
        "title": "Bad Request",
        "status": 400,
        "detail": detail,
        "instance": request.path,
    })
    resp.status_code = 400
    resp.content_type = "application/problem+json"
    return resp


def encode_cursor(data):
    return base64.urlsafe_b64encode(json.dumps(data).encode()).decode()


def decode_cursor(cursor):
    return json.loads(base64.urlsafe_b64decode(cursor.encode()))


@app.get("/orders")
def list_orders():
    sort = request.args.get("sort", "id")
    desc = sort.startswith("-")
    key = sort.lstrip("-")
    if key not in SORTABLE:
        return bad_request(f"Cannot sort by '{key}'. Allowed: {sorted(SORTABLE)}")

    limit = max(1, min(request.args.get("limit", 10, type=int), 100))

    items = orders
    status = request.args.get("status")
    if status:
        items = [o for o in items if o["status"] == status]
    customer_id = request.args.get("customer_id", type=int)
    if customer_id is not None:
        items = [o for o in items if o["customer_id"] == customer_id]

    items = sorted(items, key=lambda o: (o[key], o["id"]), reverse=desc)

    cursor = request.args.get("cursor")
    if cursor:
        try:
            c = decode_cursor(cursor)
            if c["sort"] != sort:
                raise ValueError("cursor belongs to another sort order")
            last = (c["value"], c["id"])
            if desc:
                items = [o for o in items if (o[key], o["id"]) < last]
            else:
                items = [o for o in items if (o[key], o["id"]) > last]
        except Exception:
            return bad_request("Invalid cursor.")

    page = items[:limit]
    next_cursor = None
    if len(items) > limit:
        last = page[-1]
        next_cursor = encode_cursor({"sort": sort, "value": last[key], "id": last["id"]})

    fields = request.args.get("fields")
    if fields:
        wanted = fields.split(",")
        unknown = set(wanted) - ALL_FIELDS
        if unknown:
            return bad_request(f"Unknown fields: {sorted(unknown)}")
        page = [{f: o[f] for f in wanted} for o in page]

    return jsonify({"data": page, "next_cursor": next_cursor})


if __name__ == "__main__":
    app.run(debug=True)