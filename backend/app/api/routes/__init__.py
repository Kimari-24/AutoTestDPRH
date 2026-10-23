"""Registro central de routers de la API."""

from fastapi import APIRouter

from app.api.routes import (
    auth,
    dashboard,
    empresas,
    evaluaciones,
    evaluados,
    health,
    portal,
    reportes,
    resultados,
    usuarios,
)

api_router = APIRouter()

api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(usuarios.router)
api_router.include_router(dashboard.router)
api_router.include_router(empresas.router)
api_router.include_router(evaluados.router)
api_router.include_router(evaluaciones.router)
api_router.include_router(resultados.router)
api_router.include_router(portal.router)
api_router.include_router(reportes.router)

# Fase 9: testing integral, seguridad, optimizacion y documentacion final.
# api_router.include_router(configuracion.router)
