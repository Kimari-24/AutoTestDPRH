"""
Paquete de modelos ORM.

Este modulo importa explicitamente todas las clases de modelo para
que `Base.metadata` (usada por Alembic para autogenerar migraciones)
las conozca todas, sin depender de que otro modulo las importe antes.
"""

from app.models.catalogos import (  # noqa: F401
    Escolaridad,
    EstatusCandidato,
    EstatusPrueba,
    Sexo,
    TipoEscala,
    TipoFactor,
    TipoPregunta,
)
from app.models.empresa import Empresa  # noqa: F401
from app.models.seguridad import (  # noqa: F401
    Bitacora,
    HistorialAccion,
    HistorialLogin,
    Permiso,
    Rol,
    RolPermiso,
    Sesion,
    TokenRecuperacion,
    Usuario,
    UsuarioRol,
)
from app.models.candidato import Candidato, UsuarioTemporal  # noqa: F401
from app.models.catalogo_prueba import (  # noqa: F401
    Algoritmo,
    CategoriaPrueba,
    Escala,
    Factor,
    Opcion,
    Pregunta,
    Prueba,
)
from app.models.versionado import (  # noqa: F401
    VersionAlgoritmo,
    VersionPregunta,
    VersionPrueba,
)
from app.models.aplicacion import (  # noqa: F401
    Asignacion,
    Respuesta,
    Resultado,
    ResultadoEscala,
    ResultadoFactor,
    SesionPrueba,
)
from app.models.configuracion import Configuracion, Parametro  # noqa: F401
from app.models.sistema import LogError, Notificacion  # noqa: F401

__all__ = [
    "Escolaridad",
    "EstatusCandidato",
    "EstatusPrueba",
    "Sexo",
    "TipoEscala",
    "TipoFactor",
    "TipoPregunta",
    "Empresa",
    "Bitacora",
    "HistorialAccion",
    "HistorialLogin",
    "Permiso",
    "Rol",
    "RolPermiso",
    "Sesion",
    "TokenRecuperacion",
    "Usuario",
    "UsuarioRol",
    "Candidato",
    "UsuarioTemporal",
    "Algoritmo",
    "CategoriaPrueba",
    "Escala",
    "Factor",
    "Opcion",
    "Pregunta",
    "Prueba",
    "VersionAlgoritmo",
    "VersionPregunta",
    "VersionPrueba",
    "Asignacion",
    "Respuesta",
    "Resultado",
    "ResultadoEscala",
    "ResultadoFactor",
    "SesionPrueba",
    "Configuracion",
    "Parametro",
    "LogError",
    "Notificacion",
]
