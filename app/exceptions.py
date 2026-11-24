"""app/exceptions.py
Errores de dominio y mapeo de violaciones UNIQUE.
"""
from __future__ import annotations

UNIQUE_CONSTRAINTS: dict[str, str] = {
    "uq_users_email": "Email already registered",
    "uq_users_username": "Username already taken",
    "uq_categories_name": "Category name already exists",
    "uq_categories_slug": "Category slug already exists",
    "uq_tags_name": "Tag name already exists",
    "uq_tags_slug": "Tag slug already exists",
}


class PulseError(Exception):
    """Error de dominio con código HTTP."""

    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


# El error de dominio para el 415
class UnsupportedMediaTypeError(PulseError):
    """415: el archivo no es de un tipo que aceptamos (o dice ser algo que no es)."""

    # El código que viaja en el JSON de error
    error_code = "UNSUPPORTED_MEDIA_TYPE"

    def __init__(self, detail: str) -> None:
        super().__init__(415, detail)


# El error de dominio para el 413
class FileTooLargeError(PulseError):
    """413: el archivo pasa del tamaño máximo."""

    # El código que viaja en el JSON de error
    error_code = "FILE_TOO_LARGE"

    def __init__(self, detail: str) -> None:
        super().__init__(413, detail)


class NotFoundError(PulseError):
    """404 de dominio con un mensaje legible para entidad e id."""

    def __init__(self, entity: str, entity_id: object) -> None:
        super().__init__(404, f"{entity} {entity_id} no existe")


def raise_duplicate(message: str) -> PulseError:
    """Traduce el mensaje de IntegrityError a un 409 legible."""
    for fragment, detail in UNIQUE_CONSTRAINTS.items():
        if fragment in message:
            return PulseError(409, detail)
    return PulseError(409, "Resource already exists")
