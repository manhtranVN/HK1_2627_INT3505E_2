from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

# Module-level proxies awaiting init_app()
db = SQLAlchemy()
migrate = Migrate()

