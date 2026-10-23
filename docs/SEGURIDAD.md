# Seguridad — AutoTest DPRH

Resumen de todo lo implementado en materia de seguridad a lo largo
de las 9 fases, en un solo lugar (sección 22 y 25 de los requisitos).

## Autenticación

Dos esquemas de identidad completamente separados (ver también
`docs/ARQUITECTURA.md`, sección 7.1):

| | Administrador | Evaluado |
|---|---|---|
| Entidad | `Usuario` + `Rol` (RBAC) | `UsuarioTemporal` ligado a un `Candidato` |
| Login | `POST /api/auth/login` | `POST /api/portal/login` |
| Token | JWT access + refresh | JWT access único |
| Claim distintivo | `actor=admin` | `actor=evaluado` |
| Expiración | `ACCESS_TOKEN_EXPIRE_MINUTES` / `REFRESH_TOKEN_EXPIRE_MINUTES` | `min(EVALUADO_TOKEN_EXPIRE_MINUTES, expira_en)` |

Un token de un tipo nunca autentica en el esquema del otro, aunque el
`sub` (id numérico) coincida entre ambas tablas — cada dependencia de
autenticación (`get_current_usuario` / `get_evaluado_actual`) exige
su propio valor de `actor`.

## Sesiones (endurecido tras la ronda de QA)

- **Refresh tokens con rotación**: cada `POST /api/auth/refresh`
  invalida el token usado y entrega uno nuevo; reutilizar uno ya
  usado devuelve `401`.
- Cambiar la contraseña, o desactivar a un usuario, **revoca todas sus
  sesiones**.
- **Token del evaluado ligado a su sesión**: lleva un claim `sid` (el
  instante del último login). Un logout o un nuevo login invalida los
  tokens anteriores; un evaluado tiene una sola sesión vigente.
- El evaluado se revalida en **cada petición**: acceso no revocado,
  no expirado, sesión activa, y evaluado **no desactivado**.
- Un administrador no puede desactivarse ni quitarse el rol a sí
  mismo, ni dejar al sistema sin administradores activos.

## Contraseñas

- Hash con **bcrypt** (`passlib`), nunca texto plano — ni de usuarios
  administrativos ni de accesos temporales.
- Longitud mínima de 8 caracteres al crear un usuario o cambiar su
  contraseña (`UsuarioCreate`, `CambiarPasswordRequest`).
- `PUT /api/usuarios/me/password` exige conocer la contraseña actual
  para poder cambiarla — no es lo mismo que un reseteo administrativo.
- Las contraseñas temporales de evaluados se generan con `secrets`
  (aleatoriedad criptográfica) y se muestran **una sola vez**, en el
  momento de crearlas; no se pueden recuperar después.

## Accesos temporales (evaluados)

- Se rechazan si están **revocados**, **expirados**, o **bloqueados**
  tras 5 intentos fallidos consecutivos (`MAXIMO_INTENTOS_FALLIDOS`
  en `acceso_temporal_service.py`).
- Cada request al portal vuelve a validar estos tres estados —no solo
  al iniciar sesión— por si el acceso se revoca a mitad de una prueba.
- El tiempo límite de una evaluación se controla **en el servidor**
  (`_actualizar_tiempo_restante`), no confiando en el reloj del
  navegador del evaluado.

## Autorización (RBAC)

- Rutas administrativas protegidas con `require_roles("ADMINISTRADOR")`.
- El rol `EMPRESA` existe en el modelo de datos pero no tiene rutas
  propias todavía (ver `docs/ARQUITECTURA.md`).
- El evaluado nunca recibe `opciones.valor` ni `preguntas.configuracion`
  en las respuestas del portal — ahí puede vivir la clave o el peso
  de calificación de una pregunta.

## Rate limiting

`app/core/security/rate_limit.py` limita los intentos de login (10
por IP cada 60 segundos, tanto en `/api/auth/login` como en
`/api/portal/login`). Implementación en memoria, adecuada para una
sola instancia del backend; si el despliegue crece a varias instancias
detrás de un balanceador, este contador debe migrar a un almacén
compartido (p. ej. Redis) para seguir siendo efectivo.

## Manejo de errores

- Las excepciones de negocio (`AppException` y derivadas) devuelven
  el mensaje pensado para el usuario, con el código HTTP correcto.
- Cualquier excepción no prevista se captura de forma genérica
  (`app/main.py`) y responde `500` con un mensaje neutro — el detalle
  real solo se registra en el log del servidor, nunca se filtra al
  cliente.
- `/docs` y `/redoc` se deshabilitan automáticamente cuando
  `DEBUG=false` (entornos de producción).

## Cabeceras HTTP

Toda respuesta incluye `X-Content-Type-Options: nosniff`,
`X-Frame-Options: DENY` y `Referrer-Policy: same-origin`
(middleware en `app/main.py`).

## Auditoría

- `bitacora`: registra acciones administrativas relevantes (crear,
  actualizar, desactivar, asignar, calcular resultado, etc.) con el
  usuario responsable.
- `historial_login`: registra cada intento de inicio de sesión
  (exitoso o no), tanto de administradores como de evaluados.

## Datos nunca expuestos por la API

- Hashes de contraseña (`password_hash`) — nunca aparecen en ningún
  schema de salida.
- Tokens completos en logs (solo se registra la acción, no el JWT).
- Claves/pesos de calificación al evaluado (ver "Autorización").

## Pendiente para producción real

- Rate limiting distribuido (Redis) si hay más de una instancia del backend.
- Forzar HTTPS y `Secure`/`HttpOnly` en cualquier cookie si se migra
  de JWT en header a cookies.
- Rotación de `SECRET_KEY` y gestión de secretos fuera del `.env`
  (variables de entorno del orquestador, Vault, etc.).
