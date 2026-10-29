"""Lỗi nghiệp vụ dùng chung.

Endpoint không tự gắn mã HTTP cho từng nhánh; service ném lỗi nghiệp vụ và
``main.py`` ánh xạ chúng sang status code tương ứng qua exception handler.
"""

from fastapi import status


class ServiceError(Exception):
    """Cha chung của mọi lỗi nghiệp vụ có thể trả về cho client."""

    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


class InvalidInputError(ServiceError):
    status_code = status.HTTP_400_BAD_REQUEST


class UnauthorizedError(ServiceError):
    status_code = status.HTTP_401_UNAUTHORIZED


class ForbiddenError(ServiceError):
    status_code = status.HTTP_403_FORBIDDEN


class NotFoundError(ServiceError):
    status_code = status.HTTP_404_NOT_FOUND


class ConflictError(ServiceError):
    status_code = status.HTTP_409_CONFLICT


class PayloadTooLargeError(ServiceError):
    status_code = status.HTTP_413_CONTENT_TOO_LARGE
