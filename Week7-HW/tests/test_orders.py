def test_create_order_success(client):
    """Test successful order creation linking multiple products with inventory deduction."""
    p1 = client.post(
        "/api/v1/products",
        json={"sku": "ORD-P1", "name": "Mechanical Keyboard", "price_cents": 10000, "qty_in_stock": 10},
    ).get_json()

    p2 = client.post(
        "/api/v1/products",
        json={"sku": "ORD-P2", "name": "Gaming Mouse", "price_cents": 5000, "qty_in_stock": 20},
    ).get_json()

    order_payload = {
        "customer_name": "Tran Van B",
        "customer_email": "tranvanb@example.com",
        "items": [
            {"product_id": p1["id"], "quantity": 2},
            {"product_id": p2["id"], "quantity": 3},
        ],
    }

    res = client.post("/api/v1/orders", json=order_payload)
    assert res.status_code == 201
    order_data = res.get_json()
    assert order_data["id"] is not None
    assert order_data["order_number"].startswith("ORD-")
    assert order_data["customer_name"] == "Tran Van B"
    assert order_data["customer_email"] == "tranvanb@example.com"
    assert order_data["status"] == "PENDING"
    # Total calculation: (2 * 10000) + (3 * 5000) = 20000 + 15000 = 35000
    assert order_data["total_price_cents"] == 35000
    assert len(order_data["items"]) == 2

    # Verify inventory was decremented
    p1_updated = client.get(f"/api/v1/products/{p1['id']}").get_json()
    assert p1_updated["qty_in_stock"] == 8

    p2_updated = client.get(f"/api/v1/products/{p2['id']}").get_json()
    assert p2_updated["qty_in_stock"] == 17


def test_create_order_insufficient_stock(client):
    """Test order creation fails with 409 when product stock is insufficient."""
    p = client.post(
        "/api/v1/products",
        json={"sku": "ORD-LOW-STOCK", "name": "Rare Item", "price_cents": 20000, "qty_in_stock": 2},
    ).get_json()

    order_payload = {
        "customer_name": "Le Van C",
        "customer_email": "levanc@example.com",
        "items": [{"product_id": p["id"], "quantity": 5}],
    }

    res = client.post("/api/v1/orders", json=order_payload)
    assert res.status_code == 409
    data = res.get_json()
    assert "out_of_stock" in data["code"] or "conflict" in data["code"]

    # Verify stock remained untouched
    p_check = client.get(f"/api/v1/products/{p['id']}").get_json()
    assert p_check["qty_in_stock"] == 2


def test_create_order_validation_failures(client):
    """Test validation errors for empty items, invalid email, or blank customer name."""
    p = client.post("/api/v1/products", json={"sku": "VALID-P1", "name": "Item", "price_cents": 1000, "qty_in_stock": 5}).get_json()

    # Empty items list -> 422
    res_no_items = client.post(
        "/api/v1/orders",
        json={"customer_name": "User", "customer_email": "user@example.com", "items": []},
    )
    assert res_no_items.status_code == 422

    # Invalid email -> 422
    res_bad_email = client.post(
        "/api/v1/orders",
        json={"customer_name": "User", "customer_email": "invalid-email-format", "items": [{"product_id": p["id"], "quantity": 1}]},
    )
    assert res_bad_email.status_code == 422

    # Blank customer name -> 422
    res_blank_name = client.post(
        "/api/v1/orders",
        json={"customer_name": "   ", "customer_email": "user@example.com", "items": [{"product_id": p["id"], "quantity": 1}]},
    )
    assert res_blank_name.status_code == 422


def test_create_order_nonexistent_product(client):
    """Test order creation with non-existent product ID returns 404."""
    order_payload = {
        "customer_name": "Test Customer",
        "customer_email": "test@example.com",
        "items": [{"product_id": 999999, "quantity": 1}],
    }
    res = client.post("/api/v1/orders", json=order_payload)
    assert res.status_code == 404


def test_get_order_by_id(client):
    """Test retrieving single order by ID with details."""
    p = client.post("/api/v1/products", json={"sku": "GET-ORD-P", "name": "Item", "price_cents": 2000, "qty_in_stock": 10}).get_json()
    order = client.post(
        "/api/v1/orders",
        json={"customer_name": "Alice", "customer_email": "alice@example.com", "items": [{"product_id": p["id"], "quantity": 2}]},
    ).get_json()

    res = client.get(f"/api/v1/orders/{order['id']}")
    assert res.status_code == 200
    data = res.get_json()
    assert data["id"] == order["id"]
    assert len(data["items"]) == 1
    assert data["items"][0]["product_sku"] == "GET-ORD-P"

    # Non-existent ID returns 404
    res_nf = client.get("/api/v1/orders/999999")
    assert res_nf.status_code == 404


def test_list_orders_pagination(client):
    """Test paginated retrieval of orders."""
    p = client.post("/api/v1/products", json={"sku": "LIST-ORD-P", "name": "Item", "price_cents": 1000, "qty_in_stock": 100}).get_json()
    for i in range(1, 8):
        client.post(
            "/api/v1/orders",
            json={"customer_name": f"Customer {i}", "customer_email": f"cust{i}@example.com", "items": [{"product_id": p["id"], "quantity": 1}]},
        )

    res = client.get("/api/v1/orders?page=1&size=3")
    assert res.status_code == 200
    data = res.get_json()
    assert data["page"] == 1
    assert data["size"] == 3
    assert data["total"] == 7
    assert len(data["items"]) == 3


def test_cancel_order_restores_inventory(client):
    """Test cancelling an order restores the reserved product stock."""
    p = client.post(
        "/api/v1/products",
        json={"sku": "CANCEL-STOCK-P1", "name": "Stock Test Item", "price_cents": 5000, "qty_in_stock": 10},
    ).get_json()

    order = client.post(
        "/api/v1/orders",
        json={
            "customer_name": "Hoang Van D",
            "customer_email": "hoangd@example.com",
            "items": [{"product_id": p["id"], "quantity": 4}],
        },
    ).get_json()

    # Stock should be 6
    assert client.get(f"/api/v1/products/{p['id']}").get_json()["qty_in_stock"] == 6

    # Cancel order
    cancel_res = client.post(f"/api/v1/orders/{order['id']}/cancel")
    assert cancel_res.status_code == 200
    assert cancel_res.get_json()["status"] == "CANCELLED"

    # Stock restored back to 10
    assert client.get(f"/api/v1/products/{p['id']}").get_json()["qty_in_stock"] == 10

    # Cancelling again returns 409 Conflict
    re_cancel = client.post(f"/api/v1/orders/{order['id']}/cancel")
    assert re_cancel.status_code == 409
