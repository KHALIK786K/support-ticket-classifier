"""
Custom application exceptions.
"""
from __future__ import annotations


class AppException(Exception):
    """Base application exception. Carries an HTTP status, machine code, and message."""

    status_code: int = 500
    code: str = "internal_error"

    def __init__(self, message: str, *, status_code: int | None = None, code: str | None = None):
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        if code is not None:
            self.code = code
        super().__init__(message)


class ModelNotLoadedError(AppException):
    status_code = 503
    code = "model_not_loaded"


class InvalidInputError(AppException):
    status_code = 400
    code = "invalid_input"


class TrainingError(AppException):
    status_code = 500
    code = "training_failed"
