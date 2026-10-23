# Base de datos — AutoTest DPRH

Esta carpeta no contiene la base de datos en sí (eso vive en el volumen
Docker `dprh_postgres_data`), sino recursos relacionados:

- `init/`: scripts SQL que Postgres ejecuta automáticamente la
  primera vez que se crea el contenedor (extensiones, datos semilla
  mínimos, etc.). Vacío por ahora; se usará a partir de la Fase 2.

El esquema real de tablas se gestionará con **Alembic**
(`backend/migrations/`), no con scripts SQL manuales, para mantener
un historial versionado y reproducible.
