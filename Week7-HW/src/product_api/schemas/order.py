from marshmallow import Schema, fields, validate, validates, ValidationError


class OrderItemIn(Schema):
    """Schema for each item in an order placement request."""

    product_id = fields.Int(
        required=True,
        validate=validate.Range(min=1, error="product_id must be a valid positive integer"),
    )
    quantity = fields.Int(
        required=True,
        validate=validate.Range(min=1, error="quantity must be at least 1"),
    )


class OrderCreateIn(Schema):
    """Schema for creating a new Order."""

    customer_name = fields.Str(
        required=True,
        validate=validate.Length(min=1, max=255),
    )
    customer_email = fields.Email(
        required=True,
        error_messages={"invalid": "Invalid email format"},
    )
    items = fields.List(
        fields.Nested(OrderItemIn),
        required=True,
        validate=validate.Length(min=1, error="Order must contain at least 1 item"),
    )

    @validates("customer_name")
    def _validate_customer_name(self, value, **kwargs):
        if not value or value.strip() == "":
            raise ValidationError("customer_name cannot be empty or whitespace only")


class OrderItemOut(Schema):
    """Schema for serializing OrderItem response."""

    id = fields.Int(dump_only=True)
    order_id = fields.Int(dump_only=True)
    product_id = fields.Int()
    product_sku = fields.Str(dump_only=True)
    product_name = fields.Str(dump_only=True)
    quantity = fields.Int()
    unit_price_cents = fields.Int()
    subtotal_cents = fields.Int(dump_only=True)


class OrderOut(Schema):
    """Schema for serializing Order response with eager-loaded items."""

    id = fields.Int(dump_only=True)
    order_number = fields.Str()
    customer_name = fields.Str()
    customer_email = fields.Str()
    status = fields.Str()
    total_price_cents = fields.Int()
    created_at = fields.Str(dump_only=True)
    updated_at = fields.Str(dump_only=True)
    items = fields.List(fields.Nested(OrderItemOut))


class OrderStatusPatch(Schema):
    """Schema for updating order status."""

    status = fields.Str(
        required=True,
        validate=validate.OneOf(
            ["PENDING", "CONFIRMED", "CANCELLED", "COMPLETED"],
            error="Status must be one of: PENDING, CONFIRMED, CANCELLED, COMPLETED",
        ),
    )
