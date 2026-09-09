from flask import Flask, jsonify, request
app = Flask(__name__)
BOOKS = [
    {"id": "book1", "t": "this is book1"},
    {"id": "book2", "t": "this is book2"},
    {"id": "book3", "t": "this is book3"},
    {"id": "book4", "t": "this is book4"},
    {"id": "book5", "t": "this is book5"}
]
@app.route("/books/<book_id>", methods = ["GET"])
def get_book(book_id):
    book = find_by_id(book_id)
    if book is None:
        return jsonify({"error": "book not found"}), 404
    return jsonify(book), 200

@app.route("/items/<int:item_id>")
def get_item(item_id):
    return jsonify({"id":item_id}), 200

def find_by_id(id):
    for book in BOOKS:
        if book["id"] == id:
            return book
    return None

@app.route("/books", methods = ["GET"])
def list_books():
    limit=int(request.args.get("limit", 20))
    q=request.args.get("q", "").strip().lower()
    items=[b for b in BOOKS if q in b["t"].lower()]
    return jsonify({"items": items}), 200

if __name__ == "__main__":
    app.run(host="127.0.0.1", port = 5000, debug = True)