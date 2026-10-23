# Hallazgos de la primera ronda de QA

Trazabilidad de cada hallazgo del reporte de QA: qué se corrigió y qué
prueba lo protege. Las pruebas están en
`backend/tests/test_qa_regresion.py` (30 pruebas) y se verificaron
**contra el código anterior**: 25 fallan sobre el código original (es
decir, detectan el bug de verdad) y 5 pasan en ambos (controles de
comportamientos que ya funcionaban y deben seguir funcionando).

| # | Severidad | Hallazgo | Corrección | Dónde |
|---|---|---|---|---|
| 01 | **Crítica** | `por_clave` nunca acertaba con claves numéricas: el motor convertía el valor de la opción `"1"` a `1.0` y comparaba `"1.0"` contra `"1"`. Toda calificación con claves numéricas salía en 0. | Si la respuesta es numérica, la comparación es numérica; si es texto, se compara como texto. Además `"nan"`/`"inf"` ya no se tratan como número. | `engine/estrategias.py`, `engine/motor.py` |
| 02 | Alta | Un evaluado desactivado podía iniciar sesión y seguir operando. | Se valida que el evaluado esté activo al iniciar sesión **y en cada petición** del portal. | `services/acceso_temporal_service.py` |
| 03 | Alta | La `fecha_limite` de una asignación no se respetaba. | Pasada la fecha no se puede iniciar (la asignación pasa a `EXPIRADA`); `mis-evaluaciones` deja de ofrecerla como iniciable. | `services/portal_evaluado_service.py` |
| 04 | Alta | Cambiar la contraseña no cerraba las sesiones abiertas. | Se revocan todas las sesiones (refresh tokens) del usuario al cambiarla. Al desactivar a un usuario también. | `services/usuario_service.py` |
| 05 | Media | El refresh token no rotaba: el mismo valía 7 días y podía reutilizarse. | Cada refresh invalida el token usado y entrega uno nuevo. El frontend se ajustó (ver nota abajo). | `services/auth_service.py`, `frontend/src/contexts/AuthContext.tsx` |
| 06 | Media | El token de un evaluado seguía sirviendo tras un nuevo login. | El token lleva un claim `sid` (la "generación" de la sesión = instante del último login). Un login nuevo o un logout invalida los tokens anteriores. Sin cambios de esquema. | `core/security/jwt.py`, `services/acceso_temporal_service.py`, `api/dependencies/evaluado_auth.py` |
| 07 | Media | `skip` negativo producía un 500. | `skip >= 0`. | `api/routes/*` |
| 08 | Media | `null` explícito en campos obligatorios de un `PUT` producía un 500. | Respuesta `422` clara, con una base reutilizable (`UpdateSinNulos`). Omitir el campo sigue siendo válido. | `schemas/base.py` y schemas `*Update` |
| 09 | Media | Un administrador podía desactivarse a sí mismo o quitarse su propio rol y dejar el sistema sin administradores. | No puede desactivarse ni quitarse el rol a sí mismo; tampoco se puede desactivar ni quitar el rol al único administrador activo. | `services/usuario_service.py` |
| 10 | Media | Se asignaban evaluaciones a evaluados desactivados y evaluaciones desactivadas. | `409` en ambos casos. | `services/asignacion_service.py` |
| 11 | Media | Se podía asignar e iniciar una evaluación sin versión vigente / sin preguntas, y se consumía el intento. | Al asignar se exige versión vigente (`422`); al iniciar se exige que tenga preguntas (`409`) **sin consumir el intento**. | `services/asignacion_service.py`, `services/portal_evaluado_service.py` |
| 12 | Media | `tipo_calculo` aceptaba cualquier texto; el error aparecía hasta que un evaluado terminaba su prueba. | Se valida contra las estrategias que el motor soporta, también la sobreescritura por factor. Si aun así una sesión no se puede calificar al finalizar, queda registrado en el log. | `schemas/algoritmo.py`, `services/portal_evaluado_service.py` |
| 13 | Baja | `limit` sin tope. | `1 <= limit <= 200`. | `api/routes/*` |
| 14 | Baja | Los correos distinguían mayúsculas (se podían crear duplicados y el login fallaba con otra capitalización). | Los correos se guardan y comparan en minúsculas; las búsquedas son insensibles a mayúsculas también para datos ya guardados. | `schemas/base.py`, `repositories/*` |
| 15 | Baja | Fechas imposibles: nacimiento en el futuro, `fecha_limite` en el pasado. | `422`. | `schemas/candidato.py`, `schemas/acceso_temporal.py` |
| 16 | Baja | Escalas con `valor_min > valor_max`. | `422` al crear y al actualizar (incluso cuando solo se envía uno de los dos valores). | `schemas/algoritmo.py`, `services/algoritmo_service.py` |

## Hallazgos de documentación / instalación

- El README mandaba crear el `.env` en la raíz, pero el backend solo
  leía el de la carpeta desde la que se ejecutaba → ahora lee el de la
  raíz y el de `backend/` (este último con prioridad).
- Ninguna guía mencionaba `alembic upgrade head` ni la siembra de
  datos iniciales → agregado a `README.md` e `INSTALACION.md`; el
  contenedor de Docker además aplica las migraciones solo al arrancar.
- El README conservaba texto de la Fase 1 (estado actual, "tarjeta de
  conexión" que ya no existe, conteo de pruebas) → actualizado.

## Decisiones que conviene conocer

- **BUG-03** bloquea *empezar* una evaluación vencida. Una sesión que
  ya estaba en proceso antes de la fecha límite se puede seguir
  contestando (la limita su propio tiempo máximo). Si el negocio
  prefiere cortar también las sesiones en curso, es un cambio pequeño.
- **BUG-05**: la rotación es "deslizante" (cada refresh extiende la
  sesión 7 días más). No se implementó detección de reutilización
  (revocar todo si se presenta un token ya usado), porque con varias
  pestañas abiertas puede cerrar sesiones legítimas.
- **BUG-06**: un evaluado tiene **una** sesión vigente a la vez; abrir
  el portal en otro navegador cierra la anterior.
- Los resultados ya calculados con `por_clave` antes de esta
  corrección salieron en 0 y **no se recalculan solos**: hay que
  recalcularlos con `POST /api/resultados/sesiones/{id}/calcular`
  enviando `{"forzar_recalculo": true}`.

## Pendiente / fuera de esta ronda

- Advertencias de `oxlint` en el frontend: el QA reportó 7; ahora son 6 (una
  desapareció al refactorizar `AuthContext`). Todas son avisos de estilo
  `react/set-state-in-effect` (el patrón "cargar datos al montar la
  pantalla"), 0 errores. No se tocaron a propósito: arreglarlas implica
  reescribir la carga de datos de 6 pantallas sin poder probarlas en un
  navegador, y no son un defecto funcional.
- Rate limiting detrás de un proxy inverso: se limita por la IP que ve
  el backend; con un proxy habría que confiar en `X-Forwarded-For`.
- Un servidor aislado de pruebas de `DEBUG=false` (`/docs` oculto) no
  tiene prueba automática propia.
