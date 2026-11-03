import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(current_dir, "src")
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from product_api.factory import create_app
from product_api.extensions import db
from product_api.models import Product, Order, OrderItem


def seed():
    app = create_app()
    with app.app_context():
        print("Recreating database tables...")
        db.drop_all()
        db.create_all()

        products_data = [
            {
                "sku": "LAPTOP-MBP-14",
                "name": "MacBook Pro 14 M3 Pro",
                "description": "Apple MacBook Pro 14 inch, M3 Pro chip, 18GB RAM, 512GB SSD",
                "price_cents": 199900,
                "qty_in_stock": 25,
            },
            {
                "sku": "LAPTOP-DELL-XPS15",
                "name": "Dell XPS 15 9530",
                "description": "Intel Core i7-13700H, 32GB RAM, 1TB SSD, RTX 4060",
                "price_cents": 184900,
                "qty_in_stock": 15,
            },
            {
                "sku": "PHONE-IP16-PRO",
                "name": "iPhone 16 Pro 256GB",
                "description": "Titanium design, A18 Pro chip, 48MP Fusion camera",
                "price_cents": 109900,
                "qty_in_stock": 40,
            },
            {
                "sku": "PHONE-S24-ULTRA",
                "name": "Samsung Galaxy S24 Ultra",
                "description": "Snapdragon 8 Gen 3, Titanium gray, 512GB Storage, S-Pen",
                "price_cents": 119900,
                "qty_in_stock": 30,
            },
            {
                "sku": "AUDIO-SONY-XM5",
                "name": "Sony WH-1000XM5 Noise-Canceling",
                "description": "Industry leading noise canceling wireless Bluetooth headphones",
                "price_cents": 39900,
                "qty_in_stock": 50,
            },
            {
                "sku": "KB-LOGI-MXMECH",
                "name": "Logitech MX Mechanical Wireless",
                "description": "Low profile mechanical keys, tactile quiet switches, backlit",
                "price_cents": 16900,
                "qty_in_stock": 35,
            },
            {
                "sku": "MOUSE-LOGI-MX3S",
                "name": "Logitech MX Master 3S",
                "description": "Quiet Clicks, 8K DPI any-surface tracking, MagSpeed scrolling",
                "price_cents": 9900,
                "qty_in_stock": 60,
            },
            {
                "sku": "MON-LG-27UP850",
                "name": "LG 27UP850-W 4K UHD Monitor",
                "description": "27 inch 4K IPS, USB-C 96W PD, HDR400, DCI-P3 95%",
                "price_cents": 44900,
                "qty_in_stock": 20,
            },
        ]

        created_products = []
        for p in products_data:
            prod = Product(**p)
            db.session.add(prod)
            created_products.append(prod)

        db.session.commit()
        print(f"Created {len(created_products)} sample products.")

        # Seed sample order
        order1 = Order(
            order_number="ORD-20261103-DEMO01",
            customer_name="Nguyen Van A",
            customer_email="nguyenvana@example.com",
            status="CONFIRMED",
            total_price_cents=(created_products[0].price_cents * 1)
            + (created_products[4].price_cents * 2),
            items=[
                OrderItem(
                    product_id=created_products[0].id,
                    quantity=1,
                    unit_price_cents=created_products[0].price_cents,
                ),
                OrderItem(
                    product_id=created_products[4].id,
                    quantity=2,
                    unit_price_cents=created_products[4].price_cents,
                ),
            ],
        )
        # Deduct seeded quantities
        created_products[0].qty_in_stock -= 1
        created_products[4].qty_in_stock -= 2

        db.session.add(order1)
        db.session.commit()
        print("Created sample order with OrderItems.")
        print("Seeding completed successfully.")


if __name__ == "__main__":
    seed()

