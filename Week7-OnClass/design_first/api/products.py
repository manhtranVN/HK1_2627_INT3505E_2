"""
Handler logic theo đúng Slide 08:
Các hàm python độc lập được OpenAPI spec trỏ tới qua `operationId`.
"""

import connexion
from models import db, Product

def list_products():
    """Operation: api.products.list_products"""
    products = Product.query.all()
    return [p.to_dict() for p in products], 200

def create_product(body=None):
    """Operation: api.products.create_product"""
    if body is None:
        body = connexion.request.get_json()
    product = Product(
        sku=body["sku"],
        name=body["name"],
        price_cents=body["price_cents"],
    )
    db.session.add(product)
    db.session.commit()
    return product.to_dict(), 201

def get_product(id):
    """Operation: api.products.get_product"""
    product = Product.query.get(id)
    if not product:
        return {"detail": f"Không tìm thấy sản phẩm có id={id}"}, 404
    return product.to_dict(), 200

