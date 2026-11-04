import uuid
from datetime import datetime, timezone
from flask import Blueprint, jsonify, request
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload
from ..extensions import db
from ..models import Order, OrderItem, Product
from ..errors import BadRequest, Conflict, NotFound, OutOfStock
from ..schemas import OrderCreateIn, OrderOut

orders_bp = Blueprint("orders", __name__, url_prefix="/api/v1/orders")


@orders_bp.get("")
def list_orders():
    """
    GET /api/v1/orders - Paginated list of orders with eager-loaded OrderItems and Products.
    Uses selectinload to completely eliminate N+1 query problem.
    """
    raw_page = request.args.get("page", 1)
    raw_size = request.args.get("size", 20)

    try:
        page = max(1, int(raw_page))
        size = min(100, max(1, int(raw_size)))
    except (ValueError, TypeError):
        raise BadRequest(message="page and size query parameters must be integers")

    # Eager load Order -> items and OrderItem -> product via selectinload
    stmt = (
        select(Order)
        .options(selectinload(Order.items).selectinload(OrderItem.product))
        .order_by(Order.id.desc())
        .offset((page - 1) * size)
        .limit(size)
    )

    orders = db.session.execute(stmt).scalars().all()

    total = db.session.scalar(
        select(func.count()).select_from(Order)
    ) or 0

    return (
        jsonify(
            {
                "items": [OrderOut().dump(order) for order in orders],
                "page": page,
                "size": size,
                "total": total,
            }
        ),
        200,
    )


@orders_bp.get("/<int:id>")
def get_order(id: int):
    """GET /api/v1/orders/<int:id> - Get single order with eager loaded details."""
    stmt = (
        select(Order)
        .options(selectinload(Order.items).selectinload(OrderItem.product))
        .where(Order.id == id)
    )
    order = db.session.execute(stmt).scalars().first()
    if not order:
        raise NotFound(message=f"Order with id {id} not found")

    return jsonify(OrderOut().dump(order)), 200


@orders_bp.post("")
def create_order():
    """
    POST /api/v1/orders - Place a new order linking multiple Products via OrderItems.
    Atomically checks inventory, deducts quantities, and creates order lines.
    """
    json_data = request.get_json(silent=True)
    if json_data is None:
        raise BadRequest(message="Request body must be a valid JSON object")

    data = OrderCreateIn().load(json_data)

    order_items_to_create = []
    total_cents = 0

    for item_data in data["items"]:
        product_id = item_data["product_id"]
        qty = item_data["quantity"]

        product = db.session.get(Product, product_id)
        if not product or product.archived:
            raise NotFound(
                message=f"Product with id {product_id} was not found or is no longer available"
            )

        if product.qty_in_stock < qty:
            raise OutOfStock(
                message=(
                    f"Product '{product.name}' (SKU: {product.sku}) has insufficient stock: "
                    f"{product.qty_in_stock} available, requested {qty}"
                ),
                detail={
                    "product_id": product.id,
                    "sku": product.sku,
                    "available": product.qty_in_stock,
                    "requested": qty,
                },
            )

        # Deduct inventory atomically
        product.qty_in_stock -= qty

        # Capture locked unit price
        item_total = qty * product.price_cents
        total_cents += item_total

        order_item = OrderItem(
            product_id=product.id,
            quantity=qty,
            unit_price_cents=product.price_cents,
        )
        order_items_to_create.append(order_item)

    now_tag = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    random_suffix = uuid.uuid4().hex[:6].upper()
    order_number = f"ORD-{now_tag}-{random_suffix}"

    order = Order(
        order_number=order_number,
        customer_name=data["customer_name"],
        customer_email=data["customer_email"],
        status="PENDING",
        total_price_cents=total_cents,
        items=order_items_to_create,
    )

    db.session.add(order)
    db.session.commit()

    return jsonify(OrderOut().dump(order)), 201


@orders_bp.post("/<int:id>/cancel")
def cancel_order(id: int):
    """
    POST /api/v1/orders/<int:id>/cancel - Cancel order and restore inventory.
    """
    stmt = (
        select(Order)
        .options(selectinload(Order.items).selectinload(OrderItem.product))
        .where(Order.id == id)
    )
    order = db.session.execute(stmt).scalars().first()
    if not order:
        raise NotFound(message=f"Order with id {id} not found")

    if order.status == "CANCELLED":
        raise Conflict(message="Order is already cancelled")
    if order.status == "COMPLETED":
        raise Conflict(message="Completed order cannot be cancelled")

    # Restore stock
    for item in order.items:
        if item.product:
            item.product.qty_in_stock += item.quantity

    order.status = "CANCELLED"
    db.session.commit()

    return jsonify(OrderOut().dump(order)), 200

