# Arquitectura — AutoTest DPRH

## 1. Visión general

AutoTest DPRH es una plataforma web para administrar y aplicar
evaluaciones psicométricas. Se compone de tres partes:

- **Frontend** (SPA en React) — interfaz para administrador y evaluado.
- **Backend** (API REST en FastAPI) — lógica de negocio y motor de evaluación.
- **Base de datos** (PostgreSQL) — persistencia.

```
┌─────────────┐      HTTP/JSON      ┌─────────────┐      SQL      ┌──────────────┐
│  Frontend   │ ───────────────────▶│   Backend   │ ─────────────▶│  PostgreSQL  │
│  React/TS   │◀─────────────────── │   FastAPI   │◀───────────── │              │
└─────────────┘                     └─────────────┘                └──────────────┘
```

## 2. Roles conceptuales

- **ADMINISTRADOR** — acceso completo (habilitado desde Fase 3-4).
- **EVALUADO** — acceso limitado a sus propias evaluaciones (habilitado
  a partir de la Fase 7).
- **EMPRESA** — contemplado en el modelo de datos y permisos, pero
  **no se implementa funcionalmente** en esta primera versión.

## 3. Arquitectura del backend (por capas)

```
Request → Route (controller) → Service → Repository → Model (DB)
                                   ↓
                              Domain / Engine
```

- **`api/routes/`**: define endpoints HTTP, valida entrada/salida con
  schemas Pydantic. No contiene lógica de negocio.
- **`services/`**: orquesta la lógica de negocio, aplica reglas,
  invoca repositorios y al motor de evaluación cuando corresponde.
- **`repositories/`**: única capa que ejecuta queries SQLAlchemy.
- **`models/`**: entidades ORM (tablas).
- **`schemas/`**: contratos de entrada/salida de la API (nunca se
  exponen modelos de base de datos directamente).
- **`domain/`**: reglas y entidades de negocio puras, independientes
  de framework.
- **`engine/`**: el motor universal de evaluaciones psicométricas
  (Fase 6).
- **`core/`**: configuración, seguridad (JWT/hashing) y excepciones.

Esta separación sigue SOLID: cada capa tiene una única
responsabilidad y depende de abstracciones, no de implementaciones
concretas de las capas inferiores.

## 4. Arquitectura del frontend (feature-based)

```
src/
├── pages/       # Pantallas completas
├── layouts/     # Estructuras compartidas (sidebar + header, etc.)
├── routes/      # Definición de rutas y guards
├── features/    # Un módulo por dominio: auth, evaluados, empresas...
├── services/    # Clientes HTTP (Axios)
├── hooks/       # Hooks reutilizables
├── contexts/    # Estado global (auth, tema, etc.)
├── types/       # Tipos TypeScript compartidos
└── utils/       # Utilidades puras
```

Cada carpeta bajo `features/` encapsulará sus propios componentes,
hooks y llamadas a servicios relacionados con ese dominio (evaluados,
empresas, evaluaciones, resultados, etc.), evitando lógica de negocio
dispersa en componentes de UI genéricos.

## 5. El motor universal de evaluaciones psicométricas

Principio fundamental: **no existe un motor por cada prueba**
(nada de `TermanEngine`, `WonderlicEngine`, etc.). Existe un único
motor configurable por datos:

```
EVALUACIÓN → VERSIÓN → PREGUNTAS → OPCIONES → RESPUESTAS
   → ALGORITMO → FACTORES → ESCALAS → RESULTADO → REPORTE
```

Una nueva prueba psicométrica se incorpora principalmente mediante
**configuración y datos** (preguntas, opciones, algoritmo, factores,
escalas), sin modificar el núcleo del motor. El motor soporta
múltiples estrategias de cálculo (puntuación directa, por clave,
sumas, promedios, ponderaciones, percentiles, reglas condicionales),
pero **no incluye fórmulas psicométricas reales** — estas las aporta
DPRH como configuración/datos autorizados.

El motor se implementó en la **Fase 6**, en `app/engine/`:

- `estrategias.py` — funciones puras, una por estrategia genérica
  (`suma`/`puntuacion_directa`, `promedio`, `ponderacion`,
  `por_clave`, `percentil`, `regla_condicional`). Cada una recibe la
  configuración (pesos, claves, tablas de rangos) como parámetro —
  nunca la trae hardcodeada.
- `motor.py` — `MotorEvaluacion`: carga una `SesionPrueba` ya
  `COMPLETADA` junto con sus respuestas, agrupa las respuestas por
  `Factor` (usando `pregunta.configuracion["factor_codigo"]`, un dato
  de configuración de la Fase 5), ejecuta la estrategia del
  algoritmo (o la que el propio factor sobreescriba), interpreta el
  puntaje contra las `Escala` del factor, y persiste
  `Resultado` + `ResultadoFactor` + `ResultadoEscala`. Al terminar,
  deja la sesión en estatus `CALIFICADA`.

Expuesto en `POST /api/resultados/sesiones/{id}/calcular` y
`GET /api/resultados/sesiones/{id}` (Fase 6). La creación de
asignaciones/sesiones/respuestas en sí (el portal del evaluado) se
construye en la Fase 7; el motor ya queda listo para operar sobre
ellas en cuanto existan.

## 6. Modelo de datos (resumen conceptual)

```
EMPRESA → CANDIDATO → USUARIO_TEMPORAL → ASIGNACION → SESION_PRUEBA
   → RESPUESTAS → RESULTADO → RESULTADO_FACTORES / RESULTADO_ESCALAS

CATEGORIA_PRUEBA → PRUEBA → VERSION_PRUEBA → PREGUNTAS → OPCIONES
PRUEBA → ALGORITMO → FACTORES → ESCALAS
```

Grupos de tablas previstos: seguridad (usuarios, roles, permisos,
bitácora, sesiones), empresas y evaluados, catálogo de pruebas,
aplicación (asignaciones, sesiones, respuestas, resultados),
configuración, catálogos auxiliares y versionado. Se implementan
progresivamente a partir de la Fase 2, con modelos SQLAlchemy y
migraciones Alembic — no se crean tablas manualmente por SQL.

## 7. Seguridad

- Autenticación basada en JWT (access + refresh token).
- Contraseñas con hashing seguro (bcrypt) — nunca texto plano.
- Accesos temporales de evaluados con expiración automática y
  revocación.
- RBAC (roles y permisos) para proteger endpoints.
- Auditoría vía bitácora e historial de acciones/accesos.
- CORS restringido a los orígenes del frontend.


## 7.1 Autenticación de dos superficies (Fase 7)

El sistema tiene dos tipos de identidad, sin mezcla posible:

| | Administrador | Evaluado |
|---|---|---|
| Entidad | `Usuario` + roles | `UsuarioTemporal` (ligado a un `Candidato`) |
| Token | JWT access + refresh, `actor=admin` | JWT access único, `actor=evaluado` |
| Vigencia | `ACCESS_TOKEN_EXPIRE_MINUTES` | `min(EVALUADO_TOKEN_EXPIRE_MINUTES, expira_en del acceso)` |
| Dependencia | `get_current_usuario` / `require_roles` | `get_evaluado_actual` |

Ambas dependencias exigen su propio valor de `actor`, de modo que un
token de un tipo nunca autentica en el otro aunque el `sub` numérico
coincida. Además, `get_evaluado_actual` recarga el acceso temporal en
cada petición (revocado / expirado / sesión activa).

Limitaciones conocidas del portal (para fases posteriores): las
preguntas de tipo `ASOCIACION` y `ORDENAMIENTO` se muestran con el
widget genérico de opciones (sin arrastrar/ordenar), y las respuestas
de `OPCION_MULTIPLE` se guardan como ids separados por comas en
`respuestas.valor`; el motor todavía no puntúa ese formato.

## 8. Decisiones tomadas en la Fase 1

- **Tailwind CSS v4** (vía plugin `@tailwindcss/vite`) en lugar de la
  configuración clásica con `postcss.config.js`/`tailwind.config.js`
  de v3, ya que es la versión actual del paquete y simplifica la
  integración con Vite.
- **psycopg 3** (`psycopg[binary]`) como driver de PostgreSQL para
  SQLAlchemy, por ser el driver actualmente recomendado (sucesor de
  psycopg2).
- El proxy de desarrollo de Vite redirige `/api` hacia
  `http://localhost:8000`, para que el frontend pueda llamar rutas
  relativas (`/api/...`) tanto en desarrollo como en producción
  detrás de un mismo dominio/reverse proxy.

Si alguna de estas decisiones necesita cambiar, se debe evaluar el
impacto en ambas capas (frontend/backend) antes de modificarla.
