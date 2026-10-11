# Rutas y API

## Convenciones

Las rutas HTML autentican mediante sesión Django. Los POST requieren CSRF, incluso al emitir JWT. Una visita anónima a vistas privadas suele redirigir al login; un usuario sin permiso recibe 403. Algunos objetos fuera del queryset autorizado producen 404. Las vistas comerciales pueden redirigir con mensajes de éxito/error; no son una API JSON.

`<id>` representa un entero y `<token>` un UUID. Consultar `urls.py` de cada app para los nombres usados con `reverse()`.

## HTML

| Ruta | Método | Acceso / propósito |
| --- | --- | --- |
| `/` | GET | Catálogo público; `q`, `brand`, `min_price`, `max_price`, `page` |
| `/<id>/` | GET | Detalle disponible o relación autorizada |
| `/create/` | GET, POST | Vendedor/admin; publicar |
| `/<id>/update/` | GET, POST | Propietario/admin; editar |
| `/<id>/delete/` | GET, POST | Propietario/admin; confirmar y retirar |
| `/users/register/` | GET, POST | Registro público |
| `/users/login/` | GET, POST | Login público; `next` validado |
| `/users/logout/` | POST | Cerrar sesión |
| `/users/profile/` | GET, POST | Perfil propio |
| `/users/verify/<token>/` | GET | Consumir enlace de verificación |
| `/users/admin/users/` | GET | Admin; listado alternativo de usuarios |
| `/users/admin/users/<id>/edit/` | GET, POST | Admin; edición protegida |
| `/sales/offer/<id>/` | POST | Autenticado; id de vehículo, `offered_price`, `offer_comment` |
| `/sales/reserve/<id>/` | POST | Autenticado; id de vehículo |
| `/sales/cancel-reservation/<id>/` | POST | Titular; id de vehículo |
| `/sales/history/` | GET | Historial propio, `page` |
| `/sales/accept-offer/<id>/` | POST | Admin; id de Sale |
| `/sales/reject-offer/<id>/` | POST | Admin; id de Sale |
| `/dashboard/` | GET | Admin; inicio del panel |
| `/dashboard/users/` | GET | Admin; usuarios paginados |
| `/dashboard/users/create/` | GET, POST | Admin; alta de usuario |
| `/dashboard/users/<id>/edit/` | GET, POST | Admin; edición de usuario |
| `/dashboard/users/<id>/password/` | GET, POST | Admin; cambiar contraseña con confirmación y validación; protección staff/superuser |
| `/dashboard/users/<id>/delete/` | GET, POST | Admin; confirmación y borrado protegido |
| `/dashboard/brands/` | GET | Admin; marcas paginadas |
| `/dashboard/brands/create/` | GET, POST | Admin; alta de marca |
| `/dashboard/brands/<id>/edit/` | GET, POST | Admin; edición de marca |
| `/dashboard/brands/<id>/delete/` | GET, POST | Admin; confirmación y borrado protegido |
| `/dashboard/offers/` | GET | Admin; ofertas paginadas |
| `/analytics/dashboard/` | GET | Admin; métricas globales |
| `/analytics/vehicle/<id>/` | GET | Admin; métricas de una unidad |
| `/admin/` | GET, POST según vista | Admin nativo; requiere staff y permisos Django |

Los formularios CRUD contienen sus propios campos; `VehicleForm` y los formularios de `users` son la referencia para cambios. No cambiar el esquema de un POST solo a partir de esta tabla.

## POST /users/api/token/

Requiere usuario autenticado mediante sesión y token CSRF válido. No acepta usuario/contraseña JSON ni usa Bearer para emitir otro token. No tiene refresh token. Necesita `JWT_SIGNING_KEY` independiente de al menos 32 bytes.

Respuesta 200:

```json
{"access_token":"<JWT>","token_type":"Bearer","expires_in":300}
```

Claims emitidos: `sub` (id de usuario como string), `jti` aleatorio, `iat`, `nbf`, `exp`, `iss=trucksmarter`, `aud=trucksmarter-api`, `type=access`. Firma HS256; el cliente no elige el algoritmo. No incluye contraseña, email ni rol. No guardar el token en localStorage ni logs.

| Estado | Motivo |
| --- | --- |
| 401 | No hay sesión autenticada |
| 403 | CSRF inválido/ausente o petición de túnel no confiable |
| 405 | Método distinto de POST |
| 429 | Diez tokens activos en la sesión o cuota de peticiones agotada |
| 503 | Clave ausente/inválida o Redis no disponible para la guardia |

## GET /users/api/me/

Enviar `Authorization: Bearer <JWT>`. No basta una cookie de sesión. Valida firma, algoritmo fijo, claims, vigencia, grant persistido, usuario activo, contraseña actual y sesión emisora existente/no vencida.

Respuesta 200 de ejemplo, con valores consultados en base de datos:

```json
{"id":12,"username":"comprador","role":"customer"}
```

Token ausente, alterado, revocado o vencido produce 401 y `WWW-Authenticate: Bearer`. Un método distinto de GET produce 405. Las respuestas llevan `Cache-Control` sin almacenamiento por `never_cache`.

Ejemplo con un token ya obtenido por sesión/CSRF:

```bash
curl --fail-with-body \
  -H "Authorization: Bearer $TRUCKSMARTER_ACCESS_TOKEN" \
  https://autos.example.com/users/api/me/
```

Sustituir el dominio. El token no autoriza ninguna escritura del catálogo o panel. CORS solo se habilita para estas rutas y los orígenes exactos configurados, sin credenciales de navegador.

## Rechazos globales

La guardia puede responder JSON con 400 (Content-Length inválido), 413 (tamaño declarado excesivo), 414 (query demasiado larga), 429 (cuota) o 503 (Redis no disponible). 429 por cuota incluye Retry-After; el límite de diez grants activos es independiente y puede requerir esperar a la expiración del token. HTTPS y Cloudflare pueden devolver respuestas antes de llegar a las vistas.
