"""Piezas reutilizables para los schemas de entrada."""

from __future__ import annotations

from typing import ClassVar

from pydantic import BaseModel, model_validator


class UpdateSinNulos(BaseModel):
    """Base para los schemas `*Update` (actualización parcial).

    En una actualización parcial, omitir un campo significa "no
    tocarlo" — pero enviarlo explícitamente como `null` en un campo
    OBLIGATORIO de la base de datos antes terminaba en un error 500
    (IntegrityError NOT NULL; BUG-08 de QA). Aquí se rechaza con un 422
    claro. Cada subclase declara cuáles campos no admiten null.
    """

    campos_no_nulos: ClassVar[tuple[str, ...]] = ()

    @model_validator(mode="after")
    def _rechazar_nulos_en_campos_obligatorios(self):
        for campo in self.campos_no_nulos:
            if campo in self.model_fields_set and getattr(self, campo) is None:
                raise ValueError(f"'{campo}' no puede ser null.")
        return self


def normalizar_correo(valor: str | None) -> str | None:
    """Los correos no distinguen mayúsculas: se guardan y se comparan
    siempre en minúsculas y sin espacios alrededor (BUG-14 de QA)."""
    return valor.strip().lower() if isinstance(valor, str) else valor
