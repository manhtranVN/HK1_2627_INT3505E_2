import os
from flask import Flask, jsonify
from models import db
from routes.books import bp as books_bp
from routes.categories import bp as categories_bp
from routes.authors import bp as authors_bp
from seed import seed_database

def create_app(test_config=None):
    app = Flask(__name__)

    base_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(base_dir, "bookstore.db")
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["JSON_AS_ASCII"] = False

    if test_config:
        app.config.update(test_config)

    db.init_app(app)

    app.register_blueprint(books_bp, url_prefix="/api/v1/books")
    app.register_blueprint(books_bp, url_prefix="/books", name="books_direct")

    app.register_blueprint(categories_bp, url_prefix="/api/v1/categories")
    app.register_blueprint(categories_bp, url_prefix="/categories", name="categories_direct")
    app.register_blueprint(categories_bp, url_prefix="/api/v1/genres", name="genres_alias")

    app.register_blueprint(authors_bp, url_prefix="/api/v1/authors")
    app.register_blueprint(authors_bp, url_prefix="/authors", name="authors_direct")

    @app.get("/")
    def index():
        return jsonify({
            "service": "Bookstore API - Week 5: Data Modeling and Resource Design",
            "version": "1.0.0",
            "endpoints": {
                "books": "/api/v1/books",
                "categories": "/api/v1/categories",
                "authors": "/api/v1/authors"
            },
            "features": [
                "Offset Pagination (?strategy=offset&offset=0&limit=10)",
                "Cursor Pagination (?strategy=cursor&limit=10)",
                "Filter by Genre (?genre=tech)",
                "Multi-key Sorting (?sort=-price,title)",
                "JSON Schema Validation on POST",
                "Field Selection (?fields=id,title,price)"
            ]
        })

    @app.errorhandler(404)
    def handle_404(e):
        return jsonify({"error": "not_found", "message": "Resource không tồn tại"}), 404

    @app.errorhandler(405)
    def handle_405(e):
        return jsonify({"error": "method_not_allowed", "message": "Phương thức HTTP không được hỗ trợ trên URI này"}), 405

    @app.errorhandler(500)
    def handle_500(e):
        return jsonify({"error": "internal_error", "message": "Đã xảy ra lỗi nội bộ máy chủ"}), 500

    with app.app_context():
        db.create_all()
        seed_database()

    return app

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
