import os
from flask import Flask, jsonify
from .config import DefaultConfig
from .extensions import db, migrate
from .logging_config import configure as configure_logging
from .errors import register_error_handlers
from .api.health import health_bp
from .api.products import products_bp
from .api.orders import orders_bp


def create_app(config=None):
    """
    Application Factory for Product and Order Management Service.
    Enables environment-based configuration, independent test fixtures,
    and resolves circular import dependencies.
    """
    cfg = config or os.environ.get("APP_CONFIG", DefaultConfig)

    app = Flask(__name__)

    if isinstance(cfg, dict):
        app.config.from_mapping(cfg)
    else:
        app.config.from_object(cfg)

    # Allow overriding configurations via APP_ prefix environment variables (12-Factor principle)
    app.config.from_prefixed_env("APP")

    # Structured JSON Logging
    configure_logging(app)

    # Initialize extensions with current application context
    from . import models  # Ensure all models are registered in SQLAlchemy metadata
    db.init_app(app)
    migrate.init_app(app, db)

    # Register centralized exception handlers
    register_error_handlers(app)

    # Register routing Blueprints
    app.register_blueprint(health_bp)
    app.register_blueprint(products_bp)
    app.register_blueprint(orders_bp)

    @app.get("/")
    def index():
        return jsonify(
            {
                "service": "Product & Order Backend API",
                "version": "1.0.0",
                "endpoints": {
                    "health_liveness": "/healthz",
                    "health_readiness": "/ready",
                    "products": "/api/v1/products",
                    "orders": "/api/v1/orders",
                },
                "docs": "/openapi.yaml",
            }
        ), 200

    return app
