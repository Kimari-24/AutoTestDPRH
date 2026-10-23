# Guía de instalación — AutoTest DPRH

## Requisitos previos

| Herramienta | Versión mínima | Notas |
|-------------|----------------|-------|
| Python      | 3.12           | Backend |
| Node.js     | 20             | Frontend |
| PostgreSQL  | 16             | O usar el contenedor de Docker Compose |
| Docker + Docker Compose | (opcional pero recomendado) | Para levantar todo con un solo comando |

## 1. Clonar y configurar variables de entorno

```bash
cp .env.example .env
```

Editar `.env` y ajustar, como mínimo:

- `SECRET_KEY`: generar un valor aleatorio largo (nunca usar el de
  ejemplo en un ambiente real).
- `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`: credenciales de
  la base de datos.
- `DATABASE_URL`: debe coincidir con las credenciales anteriores.
  - Con Docker Compose, el host es `db` (nombre del servicio).
  - En instalación manual, normalmente `localhost`.

### Variables de entorno explicadas

| Variable | Descripción |
|----------|-------------|
| `APP_NAME` | Nombre de la aplicación, usado en respuestas de la API. |
| `APP_ENV` | `development`, `staging` o `production`. |
| `DEBUG` | Habilita detalles adicionales de error (desactivar en producción). |
| `DATABASE_URL` | Cadena de conexión SQLAlchemy hacia PostgreSQL. Host `db` dentro de Docker; `localhost` (y tu puerto) si el backend corre en tu máquina. |
| `SECRET_KEY` | Clave usada para firmar los JWT. Debe mantenerse secreta. |
| `JWT_ALGORITHM` | Algoritmo de firma de los tokens (por defecto `HS256`). |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Vigencia del token de acceso. |
| `REFRESH_TOKEN_EXPIRE_MINUTES` | Vigencia del token de refresco. |
| `EVALUADO_TOKEN_EXPIRE_MINUTES` | Vigencia máxima del token de un evaluado en el portal (nunca excede la expiración de su acceso temporal). |
| `BACKEND_CORS_ORIGINS` | Orígenes permitidos para CORS, separados por comas. |
| `VITE_API_BASE_URL` | Base URL que usa el frontend para llamar a la API. |

## 2. Instalación con Docker Compose (recomendado)

```bash
docker compose up --build
```

El contenedor del backend aplica las migraciones solo al arrancar
(`alembic upgrade head`). La base queda con las tablas pero **sin
datos**: sigue la sección 4 para sembrar el administrador y los
catálogos.

Servicios y puertos:

- PostgreSQL → `localhost:5432`
- Backend (FastAPI) → `localhost:8000` (Swagger en `/docs`)
- Frontend (Vite) → `localhost:5173`

Para detener:

```bash
docker compose down
```

Para detener y borrar también los datos de la base de datos:

```bash
docker compose down -v
```

## 3. Instalación manual (sin Docker)

### 3.1 Base de datos

Instalar PostgreSQL 16 localmente y crear la base de datos y el
usuario indicados en `.env`, por ejemplo:

```sql
CREATE USER autotest_user WITH PASSWORD 'autotest_pass';
CREATE DATABASE autotest_dprh OWNER autotest_user;
```

Ajustar `DATABASE_URL` en `.env` para apuntar a `localhost`.

### 3.2 Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head           # crea las tablas (aquí NO es automático)
uvicorn app.main:app --reload
```

El backend lee el `.env` de la raíz del proyecto (y, si existe, el de
`backend/`, que tiene prioridad), sin importar desde qué carpeta se
ejecute.

Verificar en `http://localhost:8000/api/health` (y `/api/health/db`
para confirmar la conexión con PostgreSQL).

### 3.3 Frontend

```bash
cd frontend
npm install
npm run dev
```

Verificar en `http://localhost:5173` — debe mostrar la pantalla de
verificación de conexión con el backend.

## 4. Datos iniciales (obligatorio la primera vez)

Con las migraciones aplicadas, la base está vacía. Desde la raíz del
proyecto, con las dependencias del backend instaladas:

```bash
ADMIN_EMAIL=admin@dprh.com ADMIN_PASSWORD='CambiaEsto123!' python3 scripts/seed_roles.py
python3 scripts/seed_catalogos.py
```

Si usas Docker, tu `.env` apunta al host `db` (que solo existe dentro
de Docker); pasa la URL con `localhost` al ejecutar los scripts:

```bash
DATABASE_URL=postgresql+psycopg://autotest_user:autotest_pass@localhost:5432/autotest_dprh \
ADMIN_EMAIL=admin@dprh.com ADMIN_PASSWORD='CambiaEsto123!' python3 scripts/seed_roles.py
```

Después ya puedes iniciar sesión en `http://localhost:5173` con ese
administrador (y cambiar la contraseña con `PUT /api/usuarios/me/password`).

## 5. Ejecutar pruebas

```bash
cd backend
pytest -v
```

## 6. Problemas comunes

- **El frontend muestra "No se pudo conectar con el backend"**:
  confirmar que el backend está corriendo en el puerto `8000` y que
  no hay otro proceso ocupando ese puerto.
- **Error de conexión a PostgreSQL**: revisar que `DATABASE_URL` en
  `.env` tenga el host correcto (`db` con Docker, `localhost` en
  instalación manual) y que las credenciales coincidan con las de la
  base de datos creada.
- **Cambios en variables de entorno no se reflejan**: reiniciar el
  proceso de `uvicorn`/`npm run dev`, o los contenedores
  (`docker compose restart`).
