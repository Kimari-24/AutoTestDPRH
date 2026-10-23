"""
Configuración compartida de pytest.

El rate limiting de login (app/core/security/rate_limit.py) cuenta
intentos por IP, y el `TestClient` de FastAPI hace todas sus
peticiones desde la misma IP simulada. Sin este ajuste, la sola
cantidad de logins que hacen las demás suites (cada una con sus
propios fixtures de admin/evaluado) agotaría el límite y produciría
fallos que no tienen nada que ver con un error real del código.

Por eso aquí se desactiva por defecto para toda la suite, y
`tests/test_seguridad.py` lo reactiva explícitamente en los dos casos
puntuales donde sí interesa probar que el límite funciona.
"""

import pytest

from app.api.routes.auth import _limite_login
from app.api.routes.portal import _limite_login_evaluado
from app.main import app


def _sin_limite() -> None:
    return None


@pytest.fixture(autouse=True, scope="session")
def _desactivar_rate_limit_por_defecto():
    app.dependency_overrides[_limite_login] = _sin_limite
    app.dependency_overrides[_limite_login_evaluado] = _sin_limite
    yield
    app.dependency_overrides.pop(_limite_login, None)
    app.dependency_overrides.pop(_limite_login_evaluado, None)
