from asyncio import exceptions
from flask import Flask, jsonify, request
app = Flask(__name__)
_next = 3
BOOKS = [
    {"id":1,"title":"Clean Code","author":"R. Martin","year":2008},
    {"id":2,"title":"The Pragmatic Programmer","author":"Andrew Hunt","year":1999},
]
def find(bid):
    return next((b for b in BOOKS if b["id"] == bid), None)
def is_valid_year(y):
    if y is None or isinstance(y, bool):
        return False
    try:
        val = int(y)
        return float(y) == val and val >= 1900
    except (ValueError, TypeError):
        return False    
@app.route("/books", methods=["GET"])
def list_books():
    try:
        limit = int(request.args.get("limit", 100))
    except (ValueError, TypeError):
        limit = 100
    
    q = request.args.get("q", "").strip().lower()
    sort_param = request.args.get("sort", "").strip()
    res = list(BOOKS)
    if q:
        res = [b for b in res if q in b.get("title", "").lower() or q in b.get("author", "").lower()]
    
    if sort_param == "title":
        res = sorted(res, key=lambda x: x.get("title", "").lower())
    
    return jsonify(res[:limit]), 200
@app.route("/books/<int:bid>", methods=["GET"])
def get_book(bid):
    book = find(bid)
    if not book: 
        return {"error":"not found"}, 404
    return jsonify(book), 200
@app.route("/books", methods=["POST"])
def create_book():
    global _next
    body = request.get_json(silent=True) or {}
    t, a, y = body.get("title"), body.get("author"), body.get("year")
    if not t or not a:
        return {"error":"need title+author"}, 400

    if (not is_valid_year(y)):
        return {"error":"invalid year"}, 400
        
    book = {"id":_next, "title":t, "author":a, "year": int(y)}
    _next += 1; BOOKS.append(book)
    return jsonify(book), 201, {"Location":f"/books/{book['id']}"}
@app.route("/books/<int:bid>", methods=["PUT", "DELETE"])
def modify_book(bid):
    book = find(bid)
    if not book: 
        return {"error":"not found"}, 404
    if request.method == "PUT":
        body = request.get_json(silent=True) or {}
        if "year" in body:
            if not is_valid_year(body["year"]):
                return {"error": "field 'year' must be a number >= 1900"}, 400
            body["year"] = int(body["year"])
        book.update(body)
        return jsonify(book), 200

    BOOKS.remove(book)
    return "", 204

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
