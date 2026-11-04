from flask import Blueprint, jsonify, request
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from ..extensions import db
from ..models import Product
from ..errors import Conflict, NotFound, OutOfStock, BadRequest
from ..schemas import ProductOut, ProductIn, ProductPatch, ReserveIn

products_bp = Blueprint(
    "products", __name__, url_prefix="/api/v1/products"
)


@products_bp.get("")
def list_products():
    """GET /api/v1/products - Get paginated non-archived products."""
    raw_page = request.args.get("page", 1)
    raw_size = request.args.get("size", 20)

    try:
        page = max(1, int(raw_page))
        size = min(100, max(1, int(raw_size)))
    except (ValueError, TypeError):
        raise BadRequest(message="page and size query parameters must be integers")

    base_query = select(Product).where(Product.archived.is_(False))

    rows = db.session.execute(
        base_query.order_by(Product.id)
        .offset((page - 1) * size)
        .limit(size)
    ).scalars().all()

    total = db.session.scalar(
        select(func.count())
        .select_from(Product)
        .where(Product.archived.is_(False))
    ) or 0

    return (
        jsonify(
            {
                "items": [ProductOut().dump(p) for p in rows],
                "page": page,
                "size": size,
                "total": total,
            }
        ),
        200,
    )


@products_bp.get("/<int:id>")
def get_product(id: int):
    """GET /api/v1/products/<int:id> - Get single active product."""
    product = db.session.get(Product, id)
    if not product or product.archived:
        raise NotFound(message=f"Product with id {id} not found")
    return jsonify(ProductOut().dump(product)), 200


@products_bp.post("")
def create_product():
    """POST /api/v1/products - Create a new product."""
    json_data = request.get_json(silent=True)
    if json_data is None:
        raise BadRequest(message="Request body must be a valid JSON object")

    data = ProductIn().load(json_data)
    product = Product(**data)
    db.session.add(product)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise Conflict(message=f"Product with SKU '{product.sku}' already exists")

    return jsonify(ProductOut().dump(product)), 201


@products_bp.post("/<int:id>/reserve")
def reserve_product(id: int):
    """POST /api/v1/products/<int:id>/reserve - Reserve stock for product."""
    product = db.session.get(Product, id)
    if not product or product.archived:
        raise NotFound(message=f"Product with id {id} not found")

    json_data = request.get_json(silent=True)
    if json_data is None:
        raise BadRequest(message="Request body must be a valid JSON object")

    data = ReserveIn().load(json_data)
    qty = data["qty"]

    if product.qty_in_stock < qty:
        raise OutOfStock(
            message=f"Only {product.qty_in_stock} items left in stock, requested {qty}",
            detail={
                "available": product.qty_in_stock,
                "requested": qty,
            },
        )

    product.qty_in_stock -= qty
    db.session.commit()

    return (
        jsonify(
            {
                "message": f"Successfully reserved {qty} unit(s)",
                "product": ProductOut().dump(product),
            }
        ),
        200,
    )


@products_bp.patch("/<int:id>")
def patch_product(id: int):
    """PATCH /api/v1/products/<int:id> - Partially update product attributes."""
    product = db.session.get(Product, id)
    if not product or product.archived:
        raise NotFound(message=f"Product with id {id} not found")

    json_data = request.get_json(silent=True)
    if json_data is None:
        raise BadRequest(message="Request body must be a valid JSON object")

    data = ProductPatch().load(json_data, partial=True)
    if not data:
        raise BadRequest(message="No valid fields provided for update")

    for key, value in data.items():
        setattr(product, key, value)

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise Conflict(message="SKU already exists on another product")

    return jsonify(ProductOut().dump(product)), 200


@products_bp.delete("/<int:id>")
def delete_product(id: int):
    """DELETE /api/v1/products/<int:id> - Soft delete product."""
    product = db.session.get(Product, id)
    if not product or product.archived:
        raise NotFound(message=f"Product with id {id} not found")

    product.archived = True
    db.session.commit()

    return "", 204

