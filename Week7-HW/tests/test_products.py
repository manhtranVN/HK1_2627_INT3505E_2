import pytest


def test_index_route(client):
    """Test root endpoint returns API overview metadata."""
    res = client.get("/")
    assert res.status_code == 200
    data = res.get_json()
    assert "service" in data
    assert "endpoints" in data


def test_create_product_success(client):
    """Test successful creation of a product with valid fields."""
    payload = {
        "sku": "PROD-KB-001",
        "name": "Wireless Mechanical Keyboard",
        "description": "RGB Backlit, Red Switches",
        "price_cents": 8900,
        "qty_in_stock": 50,
    }
    response = client.post("/api/v1/products", json=payload)
    assert response.status_code == 201
    data = response.get_json()
    assert data["id"] is not None
    assert data["sku"] == "PROD-KB-001"
    assert data["name"] == "Wireless Mechanical Keyboard"
    assert data["price_cents"] == 8900
    assert data["qty_in_stock"] == 50
    assert data["archived"] is False


def test_create_product_non_json_body(client):
    """Test creating product without JSON body returns 400 Bad Request."""
    response = client.post(
        "/api/v1/products",
        data="not a json",
        content_type="text/plain",
    )
    assert response.status_code == 400
    data = response.get_json()
    assert "bad_request" in data["code"] or "bad_request" in data["error"]


def test_create_product_duplicate_sku(client):
    """Test conflict error 409 when creating product with existing SKU."""
    payload = {
        "sku": "DUP-SKU-001",
        "name": "First Product",
        "price_cents": 1000,
    }
    res1 = client.post("/api/v1/products", json=payload)
    assert res1.status_code == 201

    # Attempt duplicate SKU
    res2 = client.post("/api/v1/products", json=payload)
    assert res2.status_code == 409
    data = res2.get_json()
    assert data["code"] == "conflict" or data["error"] == "conflict"


@pytest.mark.parametrize(
    "invalid_payload,error_field",
    [
        ({"sku": "a!", "name": "Valid", "price_cents": 100}, "sku"),
        ({"sku": "VALID-SKU", "name": "", "price_cents": 100}, "name"),
        ({"sku": "VALID-SKU", "name": "   ", "price_cents": 100}, "name"),
        ({"sku": "VALID-SKU", "name": "Valid", "price_cents": -50}, "price_cents"),
        ({"sku": "VALID-SKU", "name": "Valid", "price_cents": 20_000_000}, "price_cents"),
        ({"sku": "VALID-SKU", "name": "Valid", "price_cents": 100, "qty_in_stock": -1}, "qty_in_stock"),
    ],
)
def test_create_product_validation_failure(client, invalid_payload, error_field):
    """Test input validation failure returns 422 with descriptive detail."""
    response = client.post("/api/v1/products", json=invalid_payload)
    assert response.status_code == 422
    data = response.get_json()
    assert "detail" in data
    assert error_field in data["detail"]


def test_list_products_pagination(client):
    """Test listing products with pagination parameters."""
    for i in range(1, 16):
        client.post(
            "/api/v1/products",
            json={
                "sku": f"ITEM-SKU-{i:03d}",
                "name": f"Product Item {i}",
                "price_cents": i * 1000,
                "qty_in_stock": i,
            },
        )

    # Page 1 with size 5
    res1 = client.get("/api/v1/products?page=1&size=5")
    assert res1.status_code == 200
    data1 = res1.get_json()
    assert data1["page"] == 1
    assert data1["size"] == 5
    assert data1["total"] == 15
    assert len(data1["items"]) == 5
    assert data1["items"][0]["sku"] == "ITEM-SKU-001"

    # Page 2 with size 5
    res2 = client.get("/api/v1/products?page=2&size=5")
    assert res2.status_code == 200
    data2 = res2.get_json()
    assert data2["page"] == 2
    assert len(data2["items"]) == 5
    assert data2["items"][0]["sku"] == "ITEM-SKU-006"


def test_list_products_invalid_pagination_query(client):
    """Test invalid page/size non-integer query params returns 400 Bad Request."""
    res = client.get("/api/v1/products?page=abc&size=xyz")
    assert res.status_code == 400


def test_get_product_by_id(client):
    """Test retrieving a single product by ID."""
    created = client.post(
        "/api/v1/products",
        json={"sku": "GET-BY-ID-1", "name": "Single Item", "price_cents": 5000},
    ).get_json()
    pid = created["id"]

    res = client.get(f"/api/v1/products/{pid}")
    assert res.status_code == 200
    assert res.get_json()["sku"] == "GET-BY-ID-1"

    # Non-existent ID returns 404
    res_not_found = client.get("/api/v1/products/999999")
    assert res_not_found.status_code == 404


def test_reserve_product_success_and_out_of_stock(client):
    """Test reservation decrements stock, and returns 409 when out of stock."""
    created = client.post(
        "/api/v1/products",
        json={"sku": "RESERVE-ITEM", "name": "Reserve Item", "price_cents": 2500, "qty_in_stock": 5},
    ).get_json()
    pid = created["id"]

    # Reserve 2 units
    res_reserve = client.post(f"/api/v1/products/{pid}/reserve", json={"qty": 2})
    assert res_reserve.status_code == 200
    assert res_reserve.get_json()["product"]["qty_in_stock"] == 3

    # Reserve 3 units (exhausting stock)
    res_reserve2 = client.post(f"/api/v1/products/{pid}/reserve", json={"qty": 3})
    assert res_reserve2.status_code == 200
    assert res_reserve2.get_json()["product"]["qty_in_stock"] == 0

    # Attempt to reserve 1 more unit -> Out of stock (409)
    res_fail = client.post(f"/api/v1/products/{pid}/reserve", json={"qty": 1})
    assert res_fail.status_code == 409
    data = res_fail.get_json()
    assert "out_of_stock" in data["code"] or "conflict" in data["code"]


def test_reserve_nonexistent_product(client):
    """Test reserving non-existent product returns 404."""
    res = client.post("/api/v1/products/99999/reserve", json={"qty": 1})
    assert res.status_code == 404


def test_reserve_invalid_quantity(client):
    """Test reserving zero or negative quantity returns 422."""
    created = client.post(
        "/api/v1/products",
        json={"sku": "RESERVE-INV", "name": "Valid Item", "price_cents": 1000, "qty_in_stock": 10},
    ).get_json()
    pid = created["id"]

    res_zero = client.post(f"/api/v1/products/{pid}/reserve", json={"qty": 0})
    assert res_zero.status_code == 422

    res_neg = client.post(f"/api/v1/products/{pid}/reserve", json={"qty": -5})
    assert res_neg.status_code == 422


def test_patch_product(client):
    """Test partially updating fields on an existing product."""
    created = client.post(
        "/api/v1/products",
        json={"sku": "PATCH-ORIGINAL", "name": "Original Name", "price_cents": 1000},
    ).get_json()
    pid = created["id"]

    # Partial update: price and name only
    patch_res = client.patch(
        f"/api/v1/products/{pid}",
        json={"name": "Updated Name", "price_cents": 1500},
    )
    assert patch_res.status_code == 200
    updated = patch_res.get_json()
    assert updated["name"] == "Updated Name"
    assert updated["price_cents"] == 1500
    assert updated["sku"] == "PATCH-ORIGINAL"


def test_patch_product_sku_conflict(client):
    """Test updating SKU to one that already belongs to another product returns 409."""
    client.post("/api/v1/products", json={"sku": "EXISTING-SKU-1", "name": "Prod 1", "price_cents": 1000})
    p2 = client.post("/api/v1/products", json={"sku": "EXISTING-SKU-2", "name": "Prod 2", "price_cents": 2000}).get_json()

    res = client.patch(f"/api/v1/products/{p2['id']}", json={"sku": "EXISTING-SKU-1"})
    assert res.status_code == 409


def test_patch_nonexistent_product(client):
    """Test patching non-existent product returns 404."""
    res = client.patch("/api/v1/products/99999", json={"name": "New Name"})
    assert res.status_code == 404


def test_delete_product_soft_delete(client):
    """Test soft delete sets archived=True and hides product from list and get."""
    created = client.post(
        "/api/v1/products",
        json={"sku": "DELETE-TARGET", "name": "To be deleted", "price_cents": 1000},
    ).get_json()
    pid = created["id"]

    # Perform soft delete
    del_res = client.delete(f"/api/v1/products/{pid}")
    assert del_res.status_code == 204

    # GET /api/v1/products/{id} should return 404
    get_res = client.get(f"/api/v1/products/{pid}")
    assert get_res.status_code == 404

    # Listing products should not include archived product
    list_res = client.get("/api/v1/products")
    items = list_res.get_json()["items"]
    assert all(item["id"] != pid for item in items)


def test_delete_already_deleted_product(client):
    """Test deleting already archived product returns 404."""
    created = client.post(
        "/api/v1/products",
        json={"sku": "DEL-TWICE", "name": "Twice Item", "price_cents": 1000},
    ).get_json()
    pid = created["id"]

    del1 = client.delete(f"/api/v1/products/{pid}")
    assert del1.status_code == 204

    del2 = client.delete(f"/api/v1/products/{pid}")
    assert del2.status_code == 404
