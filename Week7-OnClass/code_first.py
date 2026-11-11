"""
DEMO 1: CODE-FIRST VỚI FLASK-SMOREST (Slide 06 & Slide 09)
Viết handler và Marshmallow Schema trước -> OpenAPI 3.0 tự sinh sau từ code.
"""

from flask import Flask
from flask.views import MethodView
from flask_smorest import Api, Blueprint, abort
from flask_sqlalchemy import SQLAlchemy
from marshmallow import Schema, fields

# 1. Khởi tạo App & Cấu hình Swagger UI
app = Flask(__name__)
app.config["API_TITLE"] = "Product API (Code-First)"
app.config["API_VERSION"] = "v1"
app.config["OPENAPI_VERSION"] = "3.0.3"
app.config["OPENAPI_URL_PREFIX"] = "/"
app.config["OPENAPI_SWAGGER_UI_PATH"] = "/swagger-ui"
app.config["OPENAPI_SWAGGER_UI_URL"] = "https://cdn.jsdelivr.net/npm/swagger-ui-dist/"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///code_first.db"

db = SQLAlchemy(app)

# 2. Khai báo Model Database
class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sku = db.Column(db.String(32), unique=True, nullable=False)
    name = db.Column(db.String(255), nullable=False)
    price_cents = db.Column(db.Integer, nullable=False)

# 3. Định nghĩa Schemas (Marshmallow)
class ProductSchema(Schema):
    id = fields.Int(dump_only=True)
    sku = fields.Str()
    name = fields.Str()
    price_cents = fields.Int()

class ProductInSchema(Schema):
    sku = fields.Str(required=True)
    name = fields.Str(required=True)
    price_cents = fields.Int(required=True)

# 4. Viết Resource với MethodView (Đúng mẫu Slide 09)
blp = Blueprint("products", __name__, url_prefix="/products")

class ProductList(MethodView):
    @blp.arguments(ProductInSchema)  # Tự động validate POST body
    @blp.response(201, ProductSchema)
    def post(self, data):
        p = Product(**data)
        db.session.add(p)
        db.session.commit()
        return p

    @blp.response(200, ProductSchema(many=True))
    def get(self):
        return db.session.execute(db.select(Product)).scalars().all()

# Đăng ký route
blp.add_url_rule("", view_func=ProductList.as_view("product_list"))

api = Api(app)
api.register_blueprint(blp)

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        # Seed thử 2 sản phẩm mẫu
        if not Product.query.first():
            db.session.add_all([
                Product(sku="CF-MBP14", name="MacBook Pro 14", price_cents=199900),
                Product(sku="CF-MX3S", name="Logitech MX Master 3S", price_cents=9900),
            ])
            db.session.commit()

    print("\n" + "=" * 65)
    print(" [DEMO 1: CODE-FIRST] Đang chạy tại http://127.0.0.1:5001")
    print(" -> Swagger UI tự sinh từ code: http://127.0.0.1:5001/swagger-ui")
    print(" -> OpenAPI Spec tự sinh:       http://127.0.0.1:5001/openapi.json")
    print("=" * 65 + "\n")
    app.run(port=5001, debug=True)

