from product_api.models import Product, Order, OrderItem
from product_api.extensions import db


def test_orders_eager_loading_prevents_n_plus_one(client, app, query_counter):
    """
    Verify that GET /api/v1/orders uses eager loading (selectinload)
    to prevent the N+1 query problem.

    Without eager loading:
      1 query to fetch N orders + N queries to fetch items + N*M queries to fetch products (1 + N + NM).
    With selectinload:
      1 count query + 1 query for orders + 1 IN query for order_items + 1 IN query for products = 4 queries total,
      COMPLETELY CONSTANT regardless of whether N is 5, 20, or 100.
    """
    with app.app_context():
        # Setup 5 distinct products
        products = []
        for i in range(1, 6):
            p = Product(
                sku=f"EAGER-P{i}",
                name=f"Eager Product {i}",
                price_cents=1000 * i,
                qty_in_stock=100,
            )
            db.session.add(p)
            products.append(p)
        db.session.commit()

        # Create 5 orders, each having 3 OrderItems linked to products
        for i in range(1, 6):
            order = Order(
                order_number=f"ORD-EAGER-{i:03d}",
                customer_name=f"Customer {i}",
                customer_email=f"customer{i}@example.com",
                status="CONFIRMED",
                total_price_cents=6000,
                items=[
                    OrderItem(product_id=products[0].id, quantity=1, unit_price_cents=1000),
                    OrderItem(product_id=products[1].id, quantity=1, unit_price_cents=2000),
                    OrderItem(product_id=products[2].id, quantity=1, unit_price_cents=3000),
                ],
            )
            db.session.add(order)
        db.session.commit()

    # Now call GET /api/v1/orders and count executed queries
    with query_counter() as qc:
        response = client.get("/api/v1/orders?page=1&size=10")

    assert response.status_code == 200
    data = response.get_json()
    assert len(data["items"]) == 5
    # Verify every item in every order has product details loaded correctly
    for o in data["items"]:
        assert len(o["items"]) == 3
        for item in o["items"]:
            assert item["product_sku"] is not None
            assert item["product_name"] is not None

    # Verify query count:
    # Query 1: SELECT count(*) FROM orders
    # Query 2: SELECT * FROM orders ORDER BY id DESC LIMIT 10
    # Query 3: SELECT * FROM order_items WHERE order_id IN (...)
    # Query 4: SELECT * FROM products WHERE id IN (...)
    # Total queries must be <= 4 (constant O(1) database roundtrips)
    assert qc.count <= 4, f"Detected potential N+1 query regression! Query count was {qc.count}"


def test_query_count_remains_constant_when_scaling(client, app, query_counter):
    """
    Verify that query count remains flat when comparing 2 orders vs 6 orders.
    This empirically confirms O(1) query complexity with respect to the number of records.
    """
    with app.app_context():
        # Setup products
        p1 = Product(sku="SCALE-P1", name="P1", price_cents=100, qty_in_stock=100)
        p2 = Product(sku="SCALE-P2", name="P2", price_cents=200, qty_in_stock=100)
        db.session.add_all([p1, p2])
        db.session.commit()

        # Seed 6 orders
        for i in range(1, 7):
            order = Order(
                order_number=f"ORD-SCALE-{i:03d}",
                customer_name=f"Scale Customer {i}",
                customer_email=f"scale{i}@example.com",
                status="CONFIRMED",
                total_price_cents=300,
                items=[
                    OrderItem(product_id=p1.id, quantity=1, unit_price_cents=100),
                    OrderItem(product_id=p2.id, quantity=1, unit_price_cents=200),
                ],
            )
            db.session.add(order)
        db.session.commit()

    # Query 2 orders
    with query_counter() as qc_small:
        res2 = client.get("/api/v1/orders?page=1&size=2")
    assert res2.status_code == 200
    assert len(res2.get_json()["items"]) == 2

    # Query 6 orders
    with query_counter() as qc_large:
        res6 = client.get("/api/v1/orders?page=1&size=6")
    assert res6.status_code == 200
    assert len(res6.get_json()["items"]) == 6

    # Both must fire the exact same number of queries (<= 4 queries)
    assert qc_small.count == qc_large.count
    assert qc_large.count <= 4
