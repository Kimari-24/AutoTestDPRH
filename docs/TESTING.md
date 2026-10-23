# Testing — AutoTest DPRH

## Cómo ejecutar las pruebas

```bash
cd backend
pytest -v
```

Requiere PostgreSQL accesible vía `DATABASE_URL` (ver `.env`) con las
migraciones de Alembic aplicadas (`alembic upgrade head`). Todas las
pruebas son de integración real contra esa base de datos — no se usa
una base en memoria ni mocks del ORM.

## Organización de la suite

| Archivo | Cubre |
|---|---|
| `test_health.py` | Endpoints de salud (Fase 1) |
| `test_models.py` | Los 40 modelos ORM y sus relaciones (Fase 2) |
| `test_auth.py` | Login, refresh, logout, RBAC de administrador (Fase 3) |
| `test_fase4.py` | Dashboard, empresas, evaluados, expediente |
| `test_fase5.py` | Categorías, pruebas, versiones, preguntas, algoritmo/factores/escalas |
| `test_fase6.py` | Estrategias del motor (unitarias) + pipeline completo de cálculo |
| `test_fase7.py` | Accesos temporales y portal del evaluado de punta a punta |
| `test_fase8.py` | Generación y validez del reporte PDF (verificado con `pypdf`) |
| `test_seguridad.py` | Rate limiting, cabeceras de seguridad, cambio de contraseña |
| `test_cargador_prueba.py` | Cargador de evaluaciones desde JSON (incl. rollback) e integridad del archivo del Moss |
| `test_qa_regresion.py` | Regresión de los 16 hallazgos de QA (ver `docs/QA_HALLAZGOS.md`) |

## Convenciones seguidas en toda la suite

- **Datos únicos por corrida**: cada módulo genera un sufijo
  aleatorio (`uuid.uuid4().hex[:8]`) para sus correos/códigos de
  prueba, de modo que las pruebas se puedan correr repetidamente sin
  chocar entre sí ni con datos reales ya sembrados
  (`scripts/seed_roles.py`, `scripts/seed_catalogos.py`).
- **Limpieza al final de cada módulo**: los fixtures que crean datos
  (usuarios, empresas, pruebas, sesiones...) los borran en su
  `teardown`, respetando el orden de las llaves foráneas. Ejecutar
  toda la suite no debe dejar residuos: solo debe quedar el usuario
  administrador real (`admin@dprh.com`) si ya existía de antes.
- **Contenido siempre de ejemplo**: cualquier pregunta, algoritmo,
  factor o escala creada en una prueba está explícitamente comentada
  como "de ejemplo" — nunca contenido psicométrico real de ninguna de
  las 18 evaluaciones.
- **Verificación real, no superficial**: por ejemplo, el PDF de la
  Fase 8 se abre con `pypdf` y se revisa su texto, no solo su tamaño
  en bytes; el motor de la Fase 6 se prueba con aritmética verificable
  a mano, no solo "no truena".
- **`conftest.py`**: desactiva el rate limiting de login para toda la
  suite (por defecto), porque el `TestClient` hace todas sus
  peticiones desde la misma IP simulada. `test_seguridad.py` lo
  reactiva explícitamente en los dos casos donde sí interesa probarlo.

## Qué NO cubre esta suite todavía

- Pruebas de carga o concurrencia (fuera del alcance de este proyecto).
- Pruebas end-to-end de navegador para el frontend (Cypress/Playwright);
  el frontend se verifica con `tsc --noEmit` y `npm run build`, y
  manualmente contra el backend real durante el desarrollo de cada fase.
- Cobertura formal medida con `pytest-cov` (la dependencia está en
  `requirements.txt`, pero no hay un umbral mínimo configurado).

## Pruebas de regresión: se verifican contra el código anterior

Una prueba de regresión que nunca ha fallado no demuestra nada. Las de
`test_qa_regresion.py` se ejecutaron contra la versión previa a las
correcciones: fallan (detectan el bug) en el código original y pasan en
el corregido. Las pocas que pasan en ambos son controles deliberados de
comportamientos que ya funcionaban y no deben romperse.
