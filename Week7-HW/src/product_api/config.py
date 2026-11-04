import os


class DefaultConfig:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-not-for-prod")
    JSON_SORT_KEYS = False
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DB_URL", "sqlite:///product_api.db"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 1800,
    }
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")


class TestConfig(DefaultConfig):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    LOG_LEVEL = "WARNING"
    # In-memory SQLite does not require connection pooling options
    SQLALCHEMY_ENGINE_OPTIONS = {}


class ProductionConfig(DefaultConfig):
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "WARNING")
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_size": int(os.environ.get("DB_POOL_SIZE", 10)),
        "max_overflow": int(os.environ.get("DB_MAX_OVERFLOW", 20)),
        "pool_recycle": 1800,
        "pool_pre_ping": True,
    }

