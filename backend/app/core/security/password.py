"""
Hashing y verificación de contraseñas.

Se usa bcrypt (a través de passlib) para todas las contraseñas del
sistema: usuarios administrativos (`Usuario.password_hash`) y
accesos temporales de evaluados (`UsuarioTemporal.password_hash`).
Las contraseñas NUNCA se almacenan ni se comparan en texto plano.
"""

from passlib.context import CryptContext

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Genera el hash seguro de una contraseña en texto plano."""
    return _pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Verifica una contraseña en texto plano contra su hash almacenado."""
    return _pwd_context.verify(password, password_hash)
