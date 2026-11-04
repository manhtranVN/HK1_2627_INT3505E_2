from flask import jsonify
from werkzeug.exceptions import HTTPException
from marshmallow.exceptions import ValidationError


class ApiError(Exception):
    """Base class for all application-level business errors."""

    status_code = 500
    code = "internal_error"

    def __init__(self, code=None, message="", status=None, detail=None):
        super().__init__(message)
        if code:
            self.code = code
        if status:
            self.status_code = status
        self.message = message
        self.detail = detail if detail is not None else message


class BadRequest(ApiError):
    status_code = 400
    code = "bad_request"


class NotFound(ApiError):
    status_code = 404
    code = "not_found"


class Conflict(ApiError):
    status_code = 409
    code = "conflict"


class OutOfStock(ApiError):
    status_code = 409
    code = "out_of_stock"


class UnprocessableEntity(ApiError):
    status_code = 422
    code = "validation_error"


def register_error_handlers(app):
    """Register application-wide JSON error handlers."""

    @app.errorhandler(ApiError)
    def _on_api_error(err):
        return (
            jsonify(
                {
                    "code": err.code,
                    "error": err.code,
                    "message": err.message,
                    "detail": err.detail,
                }
            ),
            err.status_code,
        )

    @app.errorhandler(ValidationError)
    def _on_validation_error(err):
        return (
            jsonify(
                {
                    "code": "validation_error",
                    "error": "validation_error",
                    "message": "Input validation failed",
                    "detail": err.messages,
                }
            ),
            422,
        )

    @app.errorhandler(HTTPException)
    def _on_http_exception(err):
        code_str = err.name.lower().replace(" ", "_")
        return (
            jsonify(
                {
                    "code": code_str,
                    "error": code_str,
                    "message": err.description,
                    "detail": err.description,
                }
            ),
            err.code,
        )

    @app.errorhandler(Exception)
    def _on_unhandled_exception(err):
        app.logger.exception("unhandled_exception")
        return (
            jsonify(
                {
                    "code": "internal_error",
                    "error": "internal_error",
                    "message": "An internal server error occurred",
                    "detail": "An internal server error occurred",
                }
            ),
            500,
        )

