"""
Rate limiting básico para endpoints sensibles (login), sección 22 de
los requisitos.

Implementación en memoria (ventana deslizante por IP), suficiente
para una sola instancia del backend. Si el despliegue crece a varias
instancias detrás de un balanceador, esto debe migrar a un backend
compartido (p. ej. Redis) — lo dejamos anotado en
docs/SEGURIDAD.md — pero no se sobre-diseña aquí antes de que haga
falta.
"""

from __future__ import annotations

import time
from collections import defaultdict

from fastapi import HTTPException, Request

_intentos_por_clave: dict[str, list[float]] = defaultdict(list)


def limitar_tasa(clave_prefijo: str, maximo: int, ventana_segundos: int):
    """Fábrica de dependencias de FastAPI: permite como máximo `maximo`
    llamadas cada `ventana_segundos` por combinación (IP + `clave_prefijo`).

    Se usa en endpoints públicos de login, donde no hay un usuario
    autenticado todavía sobre el cual limitar por id.
    """

    def _dependencia(request: Request) -> None:
        ip = request.client.host if request.client else "desconocida"
        clave = f"{clave_prefijo}:{ip}"
        ahora = time.monotonic()

        intentos = _intentos_por_clave[clave]
        limite_inferior = ahora - ventana_segundos
        intentos[:] = [t for t in intentos if t > limite_inferior]

        if len(intentos) >= maximo:
            raise HTTPException(
                status_code=429,
                detail="Demasiados intentos. Espera un momento antes de volver a intentarlo.",
            )
        intentos.append(ahora)

    return _dependencia
