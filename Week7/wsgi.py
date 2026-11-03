import os
import sys

# Ensure src/ directory is in Python path for flexible imports
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(current_dir, "src")
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from product_api.factory import create_app

app = create_app()

if __name__ == "__main__":
    # Ensure database tables exist in standalone dev execution
    with app.app_context():
        from product_api.extensions import db
        db.create_all()
    app.run(host="0.0.0.0", port=5000, debug=True)

