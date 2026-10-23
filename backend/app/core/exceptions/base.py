"""Excepciones de negocio propias de AutoTest DPRH.

Estas excepciones se lanzan desde `services/` y `engine/`, y son
traducidas a respuestas HTTP apropiadas por los manejadores de
excepciones registrados en `main.py`. Así se evita mezclar
código HTTP con lógica de negocio.
"""


class AppException(Exception):
    """Excepción base de la aplicación."""

    status_code: int = 500
    detail: str = "Error interno del servidor."

    def __init__(self, detail: str | None = None):
        if detail:
            self.detail = detail
        super().__init__(self.detail)


class NotFoundError(AppException):
    status_code = 404
    detail = "Recurso no encontrado."


class ValidationError(AppException):
    status_code = 422
    detail = "Error de validación."


class UnauthorizedError(AppException):
    status_code = 401
    detail = "No autorizado."


class ForbiddenError(AppException):
    status_code = 403
    detail = "Acceso denegado."


class ConflictError(AppException):
    status_code = 409
    detail = "Conflicto con el estado actual del recurso."
