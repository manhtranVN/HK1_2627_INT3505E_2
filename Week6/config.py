import os
from datetime import timedelta

class Config:
    SECRET_KEY = os.environ.get("FLASK_SECRET_KEY", "prod-ready-secure-flask-secret-key-at-least-256-bits-long-random-salt")
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "social-network-jwt-secret-key-entropy-256-bits-c57d9f2a4e1b8c3d")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=15) # 900s
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)  # 2,592,000s
    JWT_ALGORITHM = "HS256"
    JWT_DECODE_ALGORITHMS = ["HS256"]
    
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    DATABASE_PATH = os.path.join(BASE_DIR, "social_network.db")
