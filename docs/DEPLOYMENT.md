# Deployment — AutoTest DPRH

## Resumen

El proyecto está pensado para desplegarse como tres piezas
independientes (ver `docker-compose.yml` en la raíz):

1. **PostgreSQL** — datos persistentes.
2. **Backend** (FastAPI/Uvicorn) — API en el puerto `8000`.
3. **Frontend** (build estático de Vite) — servido por Nginx u otro
   servidor de archivos estáticos en producción (en desarrollo, el
   propio servidor de Vite en el puerto `5173`).

## Antes de desplegar a producción

- [ ] Generar un `SECRET_KEY` largo y aleatorio (nunca el de
      `.env.example`). Por ejemplo: `python3 -c "import secrets; print(secrets.token_urlsafe(64))"`.
- [ ] Poner `APP_ENV=production` y `DEBUG=false` — esto además
      deshabilita `/docs` y `/redoc` automáticamente (ver
      `docs/SEGURIDAD.md`).
- [ ] Ajustar `BACKEND_CORS_ORIGINS` al dominio real del frontend
      (nunca `*` en producción).
- [ ] Servir el backend detrás de HTTPS (terminación TLS en un
      reverse proxy — Nginx, Traefik, el balanceador del proveedor
      cloud, etc.).
- [ ] Cambiar la contraseña del usuario administrador sembrado
      (`scripts/seed_roles.py`) apenas se tenga acceso, usando
      `PUT /api/usuarios/me/password`.
- [ ] Configurar backups periódicos de PostgreSQL.
- [ ] Si el backend corre en más de una instancia (varias réplicas
      detrás de un balanceador), migrar el rate limiting de
      `app/core/security/rate_limit.py` (en memoria, por instancia) a
      un almacén compartido como Redis — en memoria deja de ser
      efectivo si cada instancia lleva su propio conteo.

## Build de producción del frontend

```bash
cd frontend
npm install
npm run build   # genera frontend/dist/
```

Servir el contenido de `frontend/dist/` con cualquier servidor de
archivos estáticos, configurado para redirigir todas las rutas no
encontradas a `index.html` (es una SPA con React Router) y para
enviar las peticiones a `/api/*` al backend (proxy inverso).

## Migraciones en producción

```bash
cd backend
alembic upgrade head
```

Ejecutar esto como parte del pipeline de despliegue, antes de levantar
la nueva versión del backend.

## Variables de entorno

Ver `.env.example` en la raíz del proyecto y `docs/INSTALACION.md`
para el detalle de cada variable.
