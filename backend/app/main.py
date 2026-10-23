"""
Punto de entrada de la aplicación AutoTest DPRH (backend).

Crea la instancia de FastAPI, registra middlewares, manejadores de
excepciones y el router principal de la API.
"""

import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import api_router
from app.core.config.settings import get_settings
from app.core.exceptions.base import AppException

logger = logging.getLogger("autotest_dprh")

settings = get_settings()

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Plataforma de administración y aplicación de pruebas psicométricas para DPRH.",
    # En producción (DEBUG=false) se ocultan /docs y /redoc: no hace
    # falta exponer el mapa completo de la API a quien no la necesita.
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)

# --- CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Cabeceras de seguridad básicas (sección 22) ---
@app.middleware("http")
async def agregar_cabeceras_de_seguridad(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "same-origin"
    return response


# --- Manejo centralizado de excepciones de negocio ---
@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


# --- Manejo seguro de errores no previstos: nunca se filtra el detalle
# interno (traceback, mensaje de la excepción original) al cliente;
# solo se registra en el log del servidor (sección 22 de los requisitos).
@app.exception_handler(Exception)
async def excepcion_no_controlada_handler(request: Request, exc: Exception):
    logger.exception("Error no controlado en %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Error interno del servidor."})


# --- Registro de rutas ---
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/")
def root():
    """Ruta raíz informativa."""
    return {
        "app": settings.APP_NAME,
        "status": "running",
        "docs": "/docs",
    }
