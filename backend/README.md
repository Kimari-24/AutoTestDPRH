# AutoTest DPRH — Backend

API REST construida con **FastAPI**, **SQLAlchemy** y **PostgreSQL**,
siguiendo una arquitectura por capas (Layered Architecture).

## Estructura

```
backend/
├── app/
│   ├── api/
│   │   ├── dependencies/   # Dependencias de FastAPI (auth, permisos, etc. — Fase 3+)
│   │   ├── middleware/     # Middlewares personalizados (Fase 3+)
│   │   └── routes/         # Endpoints agrupados por módulo
│   ├── core/
│   │   ├── config/         # Settings (variables de entorno)
│   │   ├── security/       # JWT, hashing de contraseñas (Fase 3+)
│   │   └── exceptions/     # Excepciones de negocio y su manejo HTTP
│   ├── models/              # Modelos ORM (SQLAlchemy) — Fase 2+
│   ├── schemas/             # Schemas Pydantic de entrada/salida — Fase 2+
│   ├── repositories/        # Acceso a datos (queries) — Fase 2+
│   ├── services/            # Lógica de negocio — Fase 2+
│   ├── domain/               # Entidades y reglas de dominio puras
│   ├── engine/                # Motor universal de evaluaciones psicométricas — Fase 6
│   ├── db/                    # Conexión y sesión de base de datos
│   └── main.py                 # Punto de entrada de la aplicación
├── migrations/                  # Migraciones Alembic
├── tests/                        # Pruebas (pytest)
└── requirements.txt
```

## Requisitos

- Python 3.12+
- PostgreSQL 16 (o usar el `docker-compose.yml` de la raíz)

## Instalación local (sin Docker)

```bash
cd backend
python3 -m venv venv
source venv/bin/activate        # En Windows: venv\Scripts\activate
pip install -r requirements.txt
cp ../.env.example ../.env      # Ajustar valores si es necesario
```

## Ejecutar el servidor de desarrollo

```bash
uvicorn app.main:app --reload
```

La API quedará disponible en `http://localhost:8000`, con documentación
interactiva en `http://localhost:8000/docs` (Swagger) y
`http://localhost:8000/redoc` (ReDoc).

## Endpoints de la Fase 1

- `GET /` — información general de la app.
- `GET /api/health` — estado del backend.
- `GET /api/health/db` — estado de la conexión a PostgreSQL (requiere
  que la base de datos esté corriendo).

## Endpoints de la Fase 3 (autenticación y usuarios)

Autenticación (públicos, excepto `/me`):

- `POST /api/auth/login` — `{correo, password}` → par de tokens JWT.
- `POST /api/auth/refresh` — `{refresh_token}` → nuevo access token.
- `POST /api/auth/logout` — `{refresh_token}` → revoca la sesión (204).
- `GET /api/auth/me` — requiere `Authorization: Bearer <access_token>`.

Usuarios administrativos (requieren rol `ADMINISTRADOR`):

- `GET /api/usuarios` — lista paginada.
- `GET /api/usuarios/{id}` — detalle.
- `POST /api/usuarios` — crear (con `roles: ["ADMINISTRADOR"]`, etc.).
- `PUT /api/usuarios/{id}` — actualizar datos o roles.
- `DELETE /api/usuarios/{id}` — desactivar (baja lógica, nunca borra).
- `PUT /api/usuarios/me/password` — el propio usuario cambia su
  contraseña (requiere la actual; Fase 9).

`POST /api/auth/login` y `POST /api/portal/login` tienen rate
limiting (10 intentos por IP cada 60s — ver `docs/SEGURIDAD.md`).

Antes de poder usar `/api/auth/login`, hay que sembrar el primer rol
y usuario con `scripts/seed_roles.py` (ver README raíz del proyecto).

## Endpoints de la Fase 4 (dashboard, empresas, evaluados)

Todos requieren rol `ADMINISTRADOR`:

- `GET /api/dashboard/resumen` — tarjetas estadísticas y evaluados recientes.
- `GET /api/empresas`, `GET /api/empresas/{id}`, `POST /api/empresas`,
  `PUT /api/empresas/{id}`, `DELETE /api/empresas/{id}` (baja lógica).
- `GET /api/evaluados` (con `buscar`, `empresa_id`, `estatus_candidato_id`,
  `solo_activos`), `GET /api/evaluados/{id}`,
  `GET /api/evaluados/{id}/expediente`, `POST /api/evaluados`,
  `PUT /api/evaluados/{id}`, `DELETE /api/evaluados/{id}`.

Antes de crear evaluados con sexo/escolaridad/estatus, sembrar los
catálogos con `scripts/seed_catalogos.py`.

## Endpoints de la Fase 5 (catálogo de evaluaciones)

Todos requieren rol `ADMINISTRADOR`. Ninguno crea contenido
psicométrico real — solo la estructura genérica:

- `GET/POST /api/evaluaciones/categorias`
- `GET/POST /api/evaluaciones`, `GET/PUT /api/evaluaciones/{id}`,
  `POST /api/evaluaciones/{id}/activar`, `DELETE /api/evaluaciones/{id}` (desactivar)
- `GET/POST /api/evaluaciones/{id}/versiones`,
  `POST /api/evaluaciones/{id}/versiones/{version_id}/activar`
- `GET/POST /api/evaluaciones/versiones/{version_id}/preguntas`,
  `PUT/DELETE /api/evaluaciones/preguntas/{id}` (DELETE desactiva)
- `POST /api/evaluaciones/preguntas/{id}/opciones`,
  `PUT/DELETE /api/evaluaciones/opciones/{id}` (DELETE es físico, solo si
  la opción no tiene respuestas de evaluados asociadas)
- `GET/POST /api/evaluaciones/{id}/algoritmos`,
  `PUT /api/evaluaciones/algoritmos/{id}`
- `POST /api/evaluaciones/algoritmos/{id}/factores`,
  `PUT/DELETE /api/evaluaciones/factores/{id}`
- `POST /api/evaluaciones/factores/{id}/escalas`,
  `PUT/DELETE /api/evaluaciones/escalas/{id}`

`scripts/seed_catalogos.py` siembra los 9 tipos de pregunta que exige
la sección 5 de los requisitos.

## Endpoints de la Fase 6 (motor de resultados)

Requieren rol `ADMINISTRADOR`. Operan sobre una `SesionPrueba` que ya
esté en estatus `COMPLETADA` (la creación de sesiones llega en la
Fase 7):

- `POST /api/resultados/sesiones/{sesion_prueba_id}/calcular` —
  `{"forzar_recalculo": bool}` (opcional) → ejecuta `app/engine/motor.py`
  y persiste `Resultado` + `ResultadoFactor` + `ResultadoEscala`.
  Deja la sesión en `CALIFICADA`.
- `GET /api/resultados/sesiones/{sesion_prueba_id}` — consulta el
  resultado ya calculado.

El motor (`app/engine/`) no contiene fórmulas psicométricas reales:
ejecuta la estrategia (`tipo_calculo`) y la configuración que trae el
`Algoritmo`/`Factor` de la Fase 5.

## Endpoints de la Fase 7 (accesos temporales y portal del evaluado)

Administración (rol `ADMINISTRADOR`), bajo `/api/evaluados`:

- `POST /{id}/accesos-temporales` — crea usuario + contraseña temporales
  (la contraseña en claro solo se devuelve en esta respuesta).
- `GET /{id}/accesos-temporales` — lista (sin contraseñas).
- `POST /accesos-temporales/{acceso_id}/revocar`
- `POST /{id}/asignaciones`, `GET /{id}/asignaciones`

Portal del evaluado (token propio, `actor=evaluado`), bajo `/api/portal`:

- `POST /login`, `POST /logout`
- `GET /mis-evaluaciones`
- `POST /evaluaciones/{asignacion_id}/iniciar` — inicia o retoma la sesión
- `GET /sesiones/{id}/preguntas` — sin `valor` de opciones ni `configuracion`
- `PUT /sesiones/{id}/preguntas/{pregunta_id}/respuesta` — autoguardado
- `GET /sesiones/{id}/progreso`
- `POST /sesiones/{id}/finalizar` — cierra y dispara el motor

## Endpoints de la Fase 8 (reportes PDF)

Requiere rol `ADMINISTRADOR`:

- `GET /api/reportes/sesiones/{sesion_prueba_id}/pdf` — descarga el
  reporte de una sesión ya calificada (usa `POST
  /api/resultados/sesiones/{id}/calcular` primero si aún no existe
  resultado; responde 409 si todavía no hay uno).

El renderizado vive en `app/reportes/pdf_reporte.py` (reportlab +
matplotlib para la gráfica de barras por factor) y recibe solo datos
ya calculados/configurados — nunca redacta contenido psicométrico.

## Ejecutar pruebas

```bash
pytest -v
```

## Migraciones (Alembic)

Ya existen los 40 modelos del sistema (Fase 2). Para aplicar el
esquema a una base de datos nueva:

```bash
alembic upgrade head
```

Para crear una nueva migración tras modificar modelos:

```bash
alembic revision --autogenerate -m "descripcion del cambio"
alembic upgrade head
```

## Datos semilla

Los scripts de datos semilla viven en `scripts/` en la raíz del
proyecto (no dentro de `backend/`), para poder ejecutarse igual
apuntando a una base de datos local o a la de Docker Compose. Cargan
catálogos estructurales mínimos — **sin contenido psicométrico
real**:

```bash
# desde la raíz del proyecto
ADMIN_EMAIL=admin@dprh.com ADMIN_PASSWORD='CambiaEsto123!' python3 scripts/seed_roles.py
python3 scripts/seed_catalogos.py
```

## Convenciones

- No colocar lógica de negocio en `api/routes/` (controllers): debe
  vivir en `services/`.
- `repositories/` es la única capa que habla directamente con
  SQLAlchemy/la base de datos.
- Las excepciones de negocio heredan de `AppException`
  (`core/exceptions/base.py`) y se traducen automáticamente a
  respuestas HTTP en `main.py`.
