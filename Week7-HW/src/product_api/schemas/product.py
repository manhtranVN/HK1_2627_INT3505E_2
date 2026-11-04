from marshmallow import Schema, fields, validate, validates, ValidationError


class ProductOut(Schema):
    """Schema for serializing Product output."""

    id = fields.Int(dump_only=True)
    sku = fields.Str()
    name = fields.Str()
    description = fields.Str(allow_none=True)
    price_cents = fields.Int()
    qty_in_stock = fields.Int()
    archived = fields.Bool()
    created_at = fields.Str(dump_only=True)
    updated_at = fields.Str(dump_only=True)


class ProductIn(Schema):
    """Schema for validating Product creation input."""

    sku = fields.Str(
        required=True,
        validate=[
            validate.Length(min=3, max=32),
            validate.Regexp(
                r"^[A-Z0-9-]+$",
                error="SKU must contain only uppercase letters, digits, and hyphens (3-32 chars)",
            ),
        ],
    )
    name = fields.Str(
        required=True,
        validate=validate.Length(min=1, max=255),
    )
    price_cents = fields.Int(
        required=True,
        validate=validate.Range(
            min=0, max=10_000_000, error="price_cents must be between 0 and 10,000,000"
        ),
    )
    qty_in_stock = fields.Int(
        load_default=0,
        validate=validate.Range(
            min=0, error="qty_in_stock must be non-negative"
        ),
    )
    description = fields.Str(
        load_default=None,
        allow_none=True,
        validate=validate.Length(max=2000),
    )

    @validates("name")
    def _validate_name(self, value, **kwargs):
        if not value or value.strip() == "":
            raise ValidationError("name cannot be empty or whitespace only")


class ProductPatch(Schema):
    """Schema for validating partial updates to Product."""

    sku = fields.Str(
        validate=[
            validate.Length(min=3, max=32),
            validate.Regexp(
                r"^[A-Z0-9-]+$",
                error="SKU must contain only uppercase letters, digits, and hyphens",
            ),
        ]
    )
    name = fields.Str(validate=validate.Length(min=1, max=255))
    price_cents = fields.Int(
        validate=validate.Range(min=0, max=10_000_000)
    )
    qty_in_stock = fields.Int(
        validate=validate.Range(min=0)
    )
    description = fields.Str(
        allow_none=True,
        validate=validate.Length(max=2000),
    )

    @validates("name")
    def _validate_name(self, value, **kwargs):
        if value is not None and value.strip() == "":
            raise ValidationError("name cannot be empty or whitespace only")


class ReserveIn(Schema):
    """Schema for validating reservation quantity."""

    qty = fields.Int(
        required=True,
        validate=validate.Range(
            min=1, error="qty must be a positive integer (min 1)"
        ),
    )

