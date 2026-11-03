import os
import sys
from contextlib import contextmanager
import pytest
from sqlalchemy import event

# Add src to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from product_api.factory import create_app
from product_api.config import TestConfig
from product_api.extensions import db
from product_api.models import Product, Order, OrderItem


@pytest.fixture
def app():
    """Create and configure a clean Flask application instance for testing."""
    application = create_app(TestConfig)

    with application.app_context():
        db.create_all()
        yield application
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()


@pytest.fixture
def db_session(app):
    """Provides the database session fixture."""
    return db.session


class QueryCounter:
    """Helper class to monitor and count executed SQL queries."""

    def __init__(self):
        self.count = 0
        self.statements = []

    def __call__(self, conn, cursor, statement, parameters, context, executemany):
        # Exclude savepoints or schema creation queries if any
        self.count += 1
        self.statements.append(statement)


@pytest.fixture
def query_counter(app):
    """Fixture providing a context manager to count executed SQL queries."""

    @contextmanager
    def _counter():
        qc = QueryCounter()
        with app.app_context():
            engine = db.engine
            event.listen(engine, "before_cursor_execute", qc)
            try:
                yield qc
            finally:
                event.remove(engine, "before_cursor_execute", qc)

    return _counter

