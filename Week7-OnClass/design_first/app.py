"""
DEMO 2: DESIGN-FIRST VỚI CONNEXION (Slide 07 & Slide 08)
Viết openapi/products.yaml trước -> Connexion tự động map operationId đến handler,
tự động validate request/response và hiển thị Swagger UI.
"""

import os
import sys
import connexion

# Thêm thư mục design_first vào sys.path để Python resolve được api.products và models
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from models import db, Product

# 1. Khởi tạo Connexion App với specification_dir (Đúng Slide 08)
spec_dir = os.path.join(current_dir, "openapi")
app = connexion.FlaskApp(__name__, specification_dir=spec_dir)

# 2. Nạp API spec (Connexion đọc file yaml, tạo routes và validation)
app.add_api("products.yaml", validate_responses=True)

# 3. Cấu hình SQLite cho Flask app bên dưới
flask_app = app.app
flask_app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///design_first.db"
flask_app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(flask_app)

with flask_app.app_context():
    db.create_all()
    if not Product.query.first():
        db.session.add_all([
            Product(sku="DF-DELL-XPS", name="Dell XPS 15", price_cents=249900),
            Product(sku="DF-KEYCHRON-K2", name="Keychron K2 Mechanical Keyboard", price_cents=8900),
        ])
        db.session.commit()

if __name__ == "__main__":
    print("\n" + "=" * 65)
    print(" [DEMO 2: DESIGN-FIRST] Server dang chay tai: http://127.0.0.1:5002")
    print(" -> Swagger UI tu dong: http://127.0.0.1:5002/ui")
    print(" -> Cau hinh va route lay tu file openapi/products.yaml")
    print("=" * 65 + "\n")
    app.run(port=5002)
