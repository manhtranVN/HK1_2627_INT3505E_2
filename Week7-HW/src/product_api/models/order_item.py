from typing import TYPE_CHECKING
from sqlalchemy import Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..extensions import db

if TYPE_CHECKING:
    from .order import Order
    from .product import Product


class OrderItem(db.Model):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id"), nullable=False, index=True
    )
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id"), nullable=False, index=True
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price_cents: Mapped[int] = mapped_column(Integer, nullable=False)

    # Relationships
    order: Mapped["Order"] = relationship("Order", back_populates="items")
    product: Mapped["Product"] = relationship("Product", back_populates="order_items")

    @property
    def product_sku(self):
        return self.product.sku if self.product else None

    @property
    def product_name(self):
        return self.product.name if self.product else None

    @property
    def subtotal_cents(self):
        return self.quantity * self.unit_price_cents

    def to_dict(self):
        return {
            "id": self.id,
            "order_id": self.order_id,
            "product_id": self.product_id,
            "product_sku": self.product.sku if self.product else None,
            "product_name": self.product.name if self.product else None,
            "quantity": self.quantity,
            "unit_price_cents": self.unit_price_cents,
            "subtotal_cents": self.quantity * self.unit_price_cents,
        }
