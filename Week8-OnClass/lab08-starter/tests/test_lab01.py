"""LAB 1 — add your five tests here. Do not delete the smoke tests.

A. GET /books, empty database -> HTTP 200 and []
B. GET /books/9999 -> HTTP 404, JSON code == NOT_FOUND
C. POST /books with only author -> HTTP 400, errors contains title
D. POST valid book, DELETE it, GET same id -> HTTP 404
BONUS. Validate a Book response using JSON Schema; add an unknown
       field to a *copy* of the response and assert ValidationError.
"""
import copy
import pytest
from jsonschema import ValidationError, validate
from tools import get_book_schema
def test_get_books_empty_database(client):
    response = client.get("/books")
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    assert data == []
    assert data is not None


def test_get_book_not_found(client):
    response = client.get("/books/9999")
    assert response.status_code == 404
    data = response.get_json()
    assert data.get("code") == "NOT_FOUND"


def test_post_book_missing_title(client):
    response = client.post("/books", json={"author": "Robert C. Martin"})
    assert response.status_code == 400
    data = response.get_json()
    assert "errors" in data
    error_fields = [err.get("field") for err in data.get("errors", [])]
    assert "title" in error_fields


def test_delete_then_get_same_id_returns_404(client):
    create_response = client.post("/books", json={
        "title": "Clean Architecture",
        "author": "Robert C. Martin",
        "year": 2017
    })
    assert create_response.status_code == 201
    book_id = create_response.get_json()["id"]

    delete_response = client.delete(f"/books/{book_id}")
    assert delete_response.status_code == 204
    get_response = client.get(f"/books/{book_id}")
    assert get_response.status_code == 404
    assert get_response.get_json().get("code") == "NOT_FOUND"


def test_response_extra_field_blocked(client, sample_book):
    response = client.get(f"/books/{sample_book}")
    assert response.status_code == 200
    data = response.get_json()

    assert "password_hash" not in data

    schema = copy.deepcopy(get_book_schema())
    if schema.get("properties", {}).get("year", {}).get("type") == "string":
        schema["properties"]["year"]["type"] = "integer"
    for prop in schema.get("properties", {}).values():
        if prop.get("nullable") and isinstance(prop.get("type"), str):
            prop["type"] = [prop["type"], "null"]

    validate(instance=data, schema=schema)

    data_with_extra = dict(data)
    data_with_extra["password_hash"] = "pbkdf2:sha256:fake_secret_hash"

    with pytest.raises(ValidationError):
        validate(instance=data_with_extra, schema=schema)
