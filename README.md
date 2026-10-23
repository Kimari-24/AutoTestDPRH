# AutoTest DPRH

Plataforma web para la administración y aplicación de evaluaciones
psicométricas de **DPRH**.

Este repositorio implementa el sistema por fases. **Estado actual: las
9 fases del plan están completas** (ver el roadmap al final), y la
primera ronda de QA ya está incorporada (ver
[`docs/QA_HALLAZGOS.md`](docs/QA_HALLAZGOS.md)).

## Estructura del repositorio

```
AutoTestDPRH/
├── backend/        # API REST — FastAPI + SQLAlchemy + PostgreSQL
├── frontend/        # SPA — React 19 + TypeScript + Vite + Tailwind
├── database/          # Recursos de base de datos (init scripts)
├── docker/              # Dockerfiles de backend y frontend
├── docs/                  # Documentación técnica del proyecto
├── scripts/                # Scripts de utilidad (se irán agregando)
├── .env.example              # Variables de entorno de ejemplo
├── docker-compose.yml          # Orquestación de los 3 servicios
└── README.md                     # Este archivo
```

## Stack tecnológico

| Capa       | Tecnología                                              |
|------------|-----------------------------------------------------------|
| Frontend   | React 19, TypeScript, Vite, Tailwind CSS, React Router, Axios |
| Backend    | Python, FastAPI, SQLAlchemy, Alembic, Pydantic, JWT, bcrypt |
| Base de datos | PostgreSQL 16 |
| Arquitectura | Layered Architecture (backend), Feature-based (frontend) |

## Cómo ejecutar el proyecto

Resumen del orden correcto (cada paso se explica abajo):
**1)** crear el `.env` → **2)** levantar base + backend + frontend →
**3)** las migraciones (`alembic upgrade head`) → **4)** sembrar el
primer administrador y los catálogos → **5)** entrar al panel.

### El archivo `.env`

```bash
cp .env.example .env     # en la raíz del proyecto
```

El backend lee `.env` de la **raíz** del proyecto y, si existe, también
el de `backend/` (el de `backend/` tiene prioridad). Funciona sin
importar desde qué carpeta se ejecute. Valores que conviene revisar:

- `DATABASE_URL`: el `.env.example` apunta al host `db` (el nombre del
  contenedor en Docker). **Si corres el backend directamente en tu
  máquina**, cámbialo a `localhost` (y a tu puerto si tu PostgreSQL no
  usa el `5432`), p. ej.
  `postgresql+psycopg://autotest_user:autotest_pass@localhost:5432/autotest_dprh`.
- `SECRET_KEY`: genera uno propio con
  `python3 -c "import secrets; print(secrets.token_urlsafe(64))"`.

### Opción A — Con Docker (recomendado)

Requiere Docker y Docker Compose instalados.

```bash
cp .env.example .env
docker compose up --build
```

Esto levanta tres servicios:

- `db` — PostgreSQL en el puerto `5432`
- `backend` — FastAPI en `http://localhost:8000` (docs en `/docs`).
  Al arrancar **aplica las migraciones solo** (`alembic upgrade head`).
- `frontend` — Vite dev server en `http://localhost:5173`

Después, siembra los datos iniciales (ver más abajo): la base nace
vacía, sin roles ni administrador.

### Opción B — Manual (sin Docker)

**1. Base de datos**: instalar PostgreSQL localmente y crear el usuario
   y la base indicados en `.env`.

**2. Backend**:

```bash
cd backend
python3 -m venv venv
source venv/bin/activate          # En Windows: venv\Scripts\activate
pip install -r requirements.txt
cp ../.env.example ../.env        # y ajustar DATABASE_URL a localhost
alembic upgrade head              # crea las tablas (NO es automático aquí)
uvicorn app.main:app --reload
```

**3. Frontend** (en otra terminal):

```bash
cd frontend
npm install
npm run dev
```

Frontend en `http://localhost:5173`, backend en `http://localhost:8000`.

## Verificar la instalación

1. Abrir `http://localhost:8000/api/health` — debe responder
   `{"status": "ok", ...}`; y `http://localhost:8000/api/health/db`
   confirma la conexión con PostgreSQL.
2. Abrir `http://localhost:5173` — debe mostrar la pantalla de inicio
   de sesión del panel administrativo (tras sembrar el administrador,
   ver abajo, se puede entrar).
3. Ejecutar las pruebas del backend (requieren la base con las
   migraciones aplicadas):

```bash
cd backend
pytest -v
```

Deben pasar todas (`107 passed` con esta versión).

## Primer usuario administrador (Fase 3)

Tras aplicar las migraciones (`alembic upgrade head`), la base de
datos no tiene roles ni usuarios todavía. Para poder iniciar sesión
por primera vez, ejecutar desde la raíz del proyecto:

```bash
ADMIN_EMAIL=admin@dprh.com ADMIN_PASSWORD='CambiaEsto123!' \
    python3 scripts/seed_roles.py
```

> Los scripts de `scripts/` se ejecutan desde tu máquina y necesitan
> las dependencias del backend instaladas (`pip install -r
> backend/requirements.txt`). Si usas Docker, la base es alcanzable
> en `localhost:5432`, pero tu `.env` apunta al host `db`, que solo
> existe dentro de Docker; en ese caso indica la URL al ejecutarlos:
> `DATABASE_URL=postgresql+psycopg://autotest_user:autotest_pass@localhost:5432/autotest_dprh python3 scripts/seed_roles.py`
> (lo mismo para `scripts/seed_catalogos.py`).

Esto crea los 3 roles conceptuales (`ADMINISTRADOR`, `EMPRESA`,
`EVALUADO`) y un usuario administrador inicial. Como PostgreSQL
expone el puerto `5432` también en modo Docker Compose, este mismo
comando funciona igual estando la base de datos en un contenedor:
solo se necesita el entorno virtual de `backend/` activo y que
`DATABASE_URL` (o el `.env` de la raíz) apunte a `localhost:5432`.

Luego se puede iniciar sesión:

```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"correo":"admin@dprh.com","password":"CambiaEsto123!"}'
```

## Catálogos básicos y panel administrador (Fase 4)

Además del usuario administrador, conviene sembrar los catálogos
básicos (sexo, escolaridad, estatus) antes de usar el panel:

```bash
python3 scripts/seed_catalogos.py
```

Con el backend y el frontend corriendo (ver arriba) y sesión iniciada
con el usuario administrador, el panel (`http://localhost:5173`)
permite:

- Ver el **dashboard** con tarjetas estadísticas, estado de
  evaluaciones y evaluados recientes.
- Administrar **empresas** (crear, buscar, desactivar).
- Administrar **evaluados** (crear, buscar, filtrar, desactivar) y
  ver el **expediente** de cada uno (datos personales + evaluaciones
  asignadas).

## Catálogo de evaluaciones (Fase 5)

El módulo **Evaluaciones** del panel permite construir la
**estructura** de una prueba psicométrica — sin contenido real, que
lo aporta DPRH después:

- Crear **categorías** (Inteligencia, Personalidad, etc.) y
  **evaluaciones** (nombre, código, tiempo límite, intentos).
- Activar/desactivar una evaluación.
- Crear **versiones** de una evaluación y marcar cuál está vigente.
- Agregar **preguntas** (de cualquiera de los 9 tipos soportados) con
  sus **opciones** a la versión vigente.
- Configurar un **algoritmo** de calificación (estrategia genérica,
  p. ej. "suma" o "promedio" — nunca una fórmula psicométrica real),
  con sus **factores** y **escalas**.

`scripts/seed_catalogos.py` ya siembra los 9 tipos de pregunta que
exige la sección 5 de los requisitos (opción única, opción múltiple,
verdadero/falso, escala, asociación, ordenamiento, imagen, texto,
estímulo visual).

## Motor universal de evaluaciones (Fase 6)

El motor calcula el resultado de una sesión de prueba ya completada,
usando la configuración de la Fase 5 (algoritmo, factores, escalas) —
sin ninguna fórmula psicométrica real embebida:

```bash
curl -X POST http://localhost:8000/api/resultados/sesiones/{sesion_id}/calcular \
  -H "Authorization: Bearer $ACCESS_TOKEN" -H "Content-Type: application/json" -d '{}'

curl http://localhost:8000/api/resultados/sesiones/{sesion_id} \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Las sesiones y respuestas las crea el portal del evaluado (siguiente
sección); al finalizar una sesión, el motor la califica
automáticamente.

## Portal del evaluado (Fase 7)

Flujo completo de la sección 6 de los requisitos:

1. En el panel administrativo, abre el **expediente** de un evaluado:
   - **Asignar evaluación** (elige una evaluación activa).
   - **Generar acceso temporal**: se muestra el usuario y la contraseña
     **una sola vez** (no se guardan en claro ni se pueden recuperar).
     Puedes **revocar** un acceso en cualquier momento.
2. El evaluado entra a `http://localhost:5173/portal/login` con esas
   credenciales, ve **solo sus evaluaciones**, inicia o continúa una,
   responde (con **autoguardado** y **temporizador**), y finaliza.
3. Al finalizar, el **motor** califica la sesión automáticamente
   (si la evaluación ya tiene un algoritmo activo configurado).

Reglas de seguridad del portal:

- Sesión y tokens **separados** de los del administrador: un token de
  evaluado no sirve en el panel y viceversa (claim `actor` en el JWT).
- El acceso temporal se rechaza si está **revocado**, **expirado** o
  **bloqueado** (5 intentos fallidos).
- El evaluado **nunca** recibe la clave/peso de calificación
  (`opciones.valor` y `preguntas.configuracion` se omiten de sus respuestas).
- El tiempo límite se controla **en el servidor**; al agotarse, la
  sesión pasa a `EXPIRADA` y ya no admite respuestas.

## Reportes en PDF (Fase 8)

Con una sesión ya calificada (Fase 6 o 7), el administrador descarga
su reporte:

```bash
curl "http://localhost:8000/api/reportes/sesiones/{sesion_id}/pdf" \
  -H "Authorization: Bearer $ACCESS_TOKEN" -o reporte.pdf
```

El PDF incluye datos del evaluado y su empresa, la evaluación, la
fecha, la puntuación global, una **gráfica de barras** por factor,
las interpretaciones de cada escala alcanzada — todo tomado de lo que
ya calculó el motor y configuró DPRH en el catálogo. No se redacta
ninguna interpretación ni conclusión psicométrica nueva.

## Cargar evaluaciones reales

Cada evaluación se carga como datos desde un archivo JSON, sin tocar el
motor (primer ejemplo: `database/contenido/moss.json`, la Prueba de
Moss, 30 preguntas):

```bash
python3 scripts/cargar_prueba.py database/contenido/moss.json --validar   # solo valida
python3 scripts/cargar_prueba.py database/contenido/moss.json             # carga
```

El cargador **no inventa** claves ni baremos: una evaluación cargada sin
datos de calificación se puede asignar y contestar, pero queda
`COMPLETADA` (sin calificar) hasta que DPRH aporte esos datos. Formato y
procedimiento completo: [`docs/CARGA_DE_EVALUACIONES.md`](docs/CARGA_DE_EVALUACIONES.md).

## Documentación adicional

- [`docs/ARQUITECTURA.md`](docs/ARQUITECTURA.md) — decisiones de
  arquitectura, capas del backend y frontend, y el modelo conceptual
  del motor universal de evaluaciones.
- [`docs/INSTALACION.md`](docs/INSTALACION.md) — guía detallada de
  instalación y variables de entorno.
- [`docs/SEGURIDAD.md`](docs/SEGURIDAD.md) — autenticación, RBAC,
  rate limiting, manejo de errores y todo lo demás en materia de
  seguridad, en un solo lugar.
- [`docs/TESTING.md`](docs/TESTING.md) — cómo correr las pruebas,
  organización de la suite y sus convenciones.
- [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) — checklist antes de
  desplegar a producción.
- [`docs/CARGA_DE_EVALUACIONES.md`](docs/CARGA_DE_EVALUACIONES.md) — cómo
  cargar una evaluación (formato JSON, comandos, calificación pendiente).
- [`docs/QA_HALLAZGOS.md`](docs/QA_HALLAZGOS.md) — hallazgos de la
  primera ronda de QA, su corrección y la prueba que protege cada uno.
- [`backend/README.md`](backend/README.md) — documentación específica
  del backend.

## Roadmap de fases

| Fase | Contenido |
|------|-----------|
| 1 ✅ | Fundación del proyecto (estructura, backend, frontend, conexión) |
| 2 ✅ | Base de datos: modelos SQLAlchemy y migraciones Alembic |
| 3 ✅ | Autenticación, usuarios, roles y permisos (JWT) |
| 4 ✅ | Panel administrador: dashboard, evaluados, empresas |
| 5 ✅ | Módulo de evaluaciones: preguntas, opciones, factores, escalas, algoritmos, versiones |
| 6 ✅ | Motor universal de evaluaciones psicométricas |
| 7 ✅ | Portal del evaluado: aplicación de pruebas, temporizador, sesiones |
| 8 ✅ | Resultados, gráficas y reportes (PDF) |
| 9 ✅ | Testing integral, seguridad, optimización y documentación final |

## Reglas del proyecto (resumen)

- No se inventan preguntas, claves, baremos ni algoritmos
  psicométricos reales — el sistema solo provee el motor de
  configuración; los datos oficiales los aporta DPRH.
- No se crea un motor independiente por cada prueba: existe un único
  **motor universal** configurable por datos.
- Separación estricta de capas (controller / service / repository /
  model / schema / domain), sin lógica de negocio en los endpoints
  ni en el frontend.
