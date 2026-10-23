#!/usr/bin/env python3
"""
Datos semilla mínimos para poder operar el sistema tras las migraciones.

Crea:
- Los 3 roles conceptuales del sistema: ADMINISTRADOR, EMPRESA, EVALUADO
  (aunque EMPRESA y EVALUADO no tengan flujo funcional propio todavía,
  el rol debe existir para que el modelo de datos sea consistente).
- Un usuario ADMINISTRADOR inicial, para poder iniciar sesión por
  primera vez. Las credenciales se toman de variables de entorno
  (nunca se dejan hardcodeadas) y por defecto pide que se definan.

Uso (desde la raíz del proyecto, con el entorno virtual del backend
activo y las migraciones ya aplicadas):

    ADMIN_EMAIL=admin@dprh.com ADMIN_PASSWORD='CambiaEsto123!' \\
        python3 scripts/seed_roles.py

No inventa permisos ni datos psicométricos: solo la base mínima de
seguridad para poder administrar el sistema.
"""

import os
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1] / "backend"))

from app.core.security.password import hash_password  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.models.seguridad import Rol, Usuario, UsuarioRol  # noqa: E402

ROLES = [
    ("ADMINISTRADOR", "Administrador", "Acceso completo al sistema."),
    (
        "EMPRESA",
        "Empresa",
        "Cliente de DPRH. Rol contemplado en el modelo de datos; "
        "sin flujo funcional propio todavía.",
    ),
    (
        "EVALUADO",
        "Evaluado",
        "Persona evaluada, accede mediante credenciales temporales "
        "(no usa este esquema de usuario/rol para autenticarse).",
    ),
]


def seed_roles(db) -> dict[str, Rol]:
    roles_por_codigo: dict[str, Rol] = {}
    for codigo, nombre, descripcion in ROLES:
        rol = db.query(Rol).filter(Rol.codigo == codigo).one_or_none()
        if rol is None:
            rol = Rol(codigo=codigo, nombre=nombre, descripcion=descripcion)
            db.add(rol)
            db.flush()
            print(f"  + Rol creado: {codigo}")
        else:
            print(f"  = Rol ya existía: {codigo}")
        roles_por_codigo[codigo] = rol
    return roles_por_codigo


def seed_admin(db, roles_por_codigo: dict[str, Rol]) -> None:
    correo = os.environ.get("ADMIN_EMAIL")
    password = os.environ.get("ADMIN_PASSWORD")

    if not correo or not password:
        print(
            "\nNo se definieron ADMIN_EMAIL / ADMIN_PASSWORD: se omite la "
            "creación del usuario administrador inicial.\n"
            "Ejecuta de nuevo con, por ejemplo:\n"
            "  ADMIN_EMAIL=admin@dprh.com ADMIN_PASSWORD='CambiaEsto123!' "
            "python3 scripts/seed_roles.py"
        )
        return

    existente = db.query(Usuario).filter(Usuario.correo == correo).one_or_none()
    if existente is not None:
        print(f"  = Ya existe un usuario con correo {correo}; no se crea de nuevo.")
        return

    admin = Usuario(
        nombre="Administrador",
        apellidos="DPRH",
        correo=correo,
        password_hash=hash_password(password),
        activo=True,
    )
    db.add(admin)
    db.flush()
    db.add(UsuarioRol(usuario_id=admin.id, rol_id=roles_por_codigo["ADMINISTRADOR"].id))
    print(f"  + Usuario administrador creado: {correo}")


def main() -> None:
    db = SessionLocal()
    try:
        print("Sembrando roles base...")
        roles_por_codigo = seed_roles(db)
        print("Sembrando usuario administrador inicial...")
        seed_admin(db, roles_por_codigo)
        db.commit()
        print("\nListo.")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
