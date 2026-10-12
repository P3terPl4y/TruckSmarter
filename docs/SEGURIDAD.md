# Refuerzo y pruebas de seguridad — 11/10/2026

## Cambios aplicados

- **Cookies:** sesión y CSRF HttpOnly, Secure con DEBUG=False, SameSite Lax/Strict respectivamente; sesión de una hora y cierre de navegador. HTTPS obligatorio y HSTS en producción.
- **CSRF:** middleware activo en todos los formularios y en la emisión de JWT. Logout mediante POST. CORS no concede exenciones CSRF.
- **CORS:** cerrado por defecto. `CORS_ALLOWED_ORIGINS` admite una lista exacta, limitada a `/users/api/`, sin credenciales de navegador.
- **XSS:** autoescape de Django, Content Security Policy obligatoria, nonce aleatorio por respuesta para los scripts inline propios, sin manejadores JavaScript inline. Objetos y framing bloqueados, base y destino de formularios restringidos. Se mantiene `style-src 'unsafe-inline'` para el CSS existente; no se permite en `script-src`. El admin usa los mecanismos CSP nativos de Django 6.1.
- **SQL injection:** consultas mediante ORM y validación de filtros. Las pruebas envían cargas maliciosas al catálogo y al login y comprueban que no autentican ni dañan la tabla. No se ha añadido un filtro de palabras SQL que pueda bloquear texto legítimo.
- **Abuso:** contadores Redis atómicos por IP, 120 peticiones/minuto y 30 escrituras/minuto; respuesta 429 y Retry-After. El login/registro mantienen además su límite de 5/minuto. Las ventanas fijas pueden permitir una ráfaga al cambiar de minuto. Si Redis falla, las rutas dinámicas devuelven 503. Límite declarado del cuerpo 6 MiB, query 4096 caracteres, campos 100, archivos 5 y memoria de datos de formulario 256 KiB.
- **JWT:** POST `/users/api/token/` requiere sesión y CSRF. GET `/users/api/me/` requiere Bearer, sin fallback a cookies. HS256 fijo, clave independiente de al menos 32 bytes, issuer/audience y claims obligatorios, vida de 5 minutos. No hay refresh token. Hasta 10 tokens activos por sesión, serializados por bloqueo del usuario. La base guarda SHA-256 del identificador aleatorio, nunca el token completo. La consulta valida usuario activo, contraseña y existencia de la sesión: logout, eliminación de sesión o cambio de contraseña revocan el acceso. El rol se lee de la base, no del JWT. Respuestas sin caché.
- **SHA-256:** las contraseñas se guardan con PBKDF2-SHA256 y sal aleatoria. SHA-256 y HS256 no cifran datos; el JWT es legible y debe viajar por HTTPS. No se han presentado estos mecanismos como cifrado reversible de datos personales o bancarios.

## Cloudflared, sin Nginx

El ejemplo está en `deploy/cloudflared.yml.example`; no reemplaza el túnel existente ni sus credenciales. El puerto Docker se publica únicamente en `127.0.0.1`. Para ejecución sin Docker, enlazar Gunicorn a `127.0.0.1:8000` y usar `--forwarded-allow-ips=''` para que la validación de cabeceras quede a cargo del middleware.

Con el origen privado y accesible exclusivamente por Cloudflared:

```dotenv
DEBUG=False
ALLOWED_HOSTS=autos.example.com
SITE_URL=https://autos.example.com
CSRF_TRUSTED_ORIGINS=https://autos.example.com
CLOUDFLARED_ENABLED=True
CLOUDFLARED_TRUSTED_PEERS=127.0.0.1,::1
CORS_ALLOWED_ORIGINS=
```

Sustituir el dominio por el real. `CLOUDFLARED_TRUSTED_PEERS` contiene las IP exactas de los conectores tal como las ve Django, no las de los visitantes. En Docker la dirección del peer puede ser la pasarela del bridge: comprobarla y configurar únicamente la dirección necesaria, sin confiar en una red completa. No habilitar este modo con un puerto accesible directamente desde Internet ni compartido con emisores no confiables.

El middleware se ejecuta antes de SecurityMiddleware, acepta `CF-Connecting-IP` y `X-Forwarded-Proto` únicamente desde esos peers, valida IP/protocolo y rechaza los demás. Evita bucles de redirección HTTPS y aplica tanto los límites generales como los de login a la IP del visitante. `X-Forwarded-For` no se utiliza. Con el modo deshabilitado todas esas cabeceras se ignoran.

Cloudflare recomienda `CF-Connecting-IP` para restaurar la IP del visitante y describe el protocolo original en `X-Forwarded-Proto`: [cabeceras oficiales](https://developers.cloudflare.com/fundamentals/reference/http-headers/). El túnel dirige el hostname hacia el servicio privado: [configuración oficial](https://developers.cloudflare.com/tunnel/features/locally-managed-tunnels/configuration-file/).

Los límites de Django actúan después de recibir la conexión; no sustituyen la protección de red frente a DoS volumétrico o conexiones lentas. Revisar en Cloudflare las reglas WAF y de rate limiting del hostname, especialmente login, registro y emisión de tokens, y bloquear bypass directo al origen. La disponibilidad de reglas depende del plan. No se han modificado reglas de la cuenta Cloudflare, ejecutado carga sobre el dominio ni validado un túnel real durante esta auditoría. WhiteNoise entrega estáticos y la vista catalog_image entrega exclusivamente imágenes raster públicas de vehicles/brands, con DEBUG=False, GET/HEAD, contención de rutas y nosniff.

## Activación y mantenimiento

1. Instalar `requirements.txt` y aplicar las migraciones, incluida `users/0003_jwtgrant.py`, después del procedimiento habitual de respaldo.
2. Generar una clave independiente: `python -c 'import secrets; print(secrets.token_urlsafe(48))'`; guardarla como `JWT_SIGNING_KEY` en el entorno privado. Sin clave válida la API de tokens devuelve 503. No guardar tokens en localStorage ni registrar Authorization.
3. Configurar hostname, HTTPS y los peers del túnel como arriba. Mantener Redis privado y disponible. Ajustar límites según tráfico legítimo; usuarios que comparten una IP también comparten cuota.
4. Programar diariamente `python manage.py prune_tokens` y `python manage.py clearsessions`. Cambiar la clave JWT invalida los tokens existentes.
5. Probar un login, CSRF, subida de imagen y navegación por el túnel tras desplegar. Se ha probado la lógica del middleware de Cloudflared localmente; el origen real no ha sido desplegado ni modificado.

## Resultados

- Suite completa PostgreSQL/Redis: **174 pruebas aprobadas**, sin skips ni checks silenciados.
- Suite de seguridad SQLite: **25 pruebas aprobadas**; se silencian únicamente los checks de ratelimit/LocMem del entorno de pruebas.
- Cobertura global de líneas y ramas: **96% redondeada**.
- `makemigrations --check --dry-run`, `pip check`, sintaxis/formato y `git diff --check`: aprobados.
- `check --deploy --fail-level WARNING`: sin hallazgos usando settings aislados con HTTPS, cookies Secure y clave efímera fuerte; no se ha certificado la configuración del servidor real.
- Evidencias locales: `.test-artifacts/security-postgres.txt`, `security-sqlite.txt`, `security-coverage.txt`. Los errores SMTP/Redis simulados que aparecen en logs pertenecen a pruebas de resiliencia.

## Validación reproducible

Suite local con PostgreSQL y Redis aislados, sin correo externo ni datos de producción:

```bash
TMPDIR="$PWD/.test-artifacts" \
TEST_DATABASE_URL=postgresql://peter@127.0.0.1:55440/trucksmarter_audit \
TEST_REDIS_URL=redis://127.0.0.1:56380/0 \
.venv/bin/coverage run --data-file=.test-artifacts/security.coverage \
manage.py test --settings=config.test_settings --noinput
.venv/bin/coverage report --data-file=.test-artifacts/security.coverage
```

Los nuevos casos están en `core/test_security.py`: cookies reales de login HTTPS, CSRF ausente/incorrecto/origen ajeno, CORS permitido/denegado, escape XSS y CSP, cargas SQL, PBKDF2 con sales diferentes, abuso e IP falsificada, caída de caché, tamaños inválidos, JWT alterado/sin firma/caducado/con claims incorrectos, revocación, caducidad y limpieza de grants, límite de emisión, y aislamiento de clientes y cabeceras detrás de Cloudflared.

Las pruebas normales usan MD5 únicamente para acelerar sus fixtures; la prueba criptográfica activa PBKDF2-SHA256 explícitamente y producción configura exclusivamente ese hasher. Esto no es un pentest exhaustivo ni una medición de capacidad. No se ha ejecutado un escáner de dependencias CVE ni un navegador para evaluar visualmente CSP.

## Cambio de contraseñas en el panel

`/dashboard/users/<id>/password/` permite a administradores autorizados establecer una contraseña con confirmación mediante SetPasswordForm. Conserva los validadores y hashing nativos, protege CSRF, evita caché de respuestas y marca los campos de contraseña como sensibles para los informes de errores. La operación bloquea la fila y vuelve a comprobar la protección de staff/superusuarios antes de guardar. Los campos adicionales enviados no pueden cambiar privilegios. La sesión propia se mantiene si el actor cambia su contraseña; las sesiones previas de otros dispositivos y los JWT dejan de autenticar con el hash anterior.

Doce pruebas nuevas en `dashboard/test_passwords.py` cubren permisos GET/POST, cuentas protegidas, confirmación/fortaleza, hashing, campos ajenos, CSRF, enlaces, objeto inexistente, sesión propia y revocación de sesión/JWT. Incluyen una regresión que mantiene el listado y la edición accesibles cuando un proceso aún no ha cargado la ruta nueva. Ninguna contraseña operativa ni prueba modifica la cuenta real del administrador durante la validación.

Validación posterior de esta ampliación: **186 pruebas aprobadas con PostgreSQL/Redis**, sin omisiones ni checks silenciados, y **96% de cobertura de líneas y ramas redondeada**. El apartado de resultados anterior conserva la ejecución del refuerzo inicial de 174 casos. Los errores Django de producción se envían ahora al logger de consola del servicio, con stack trace y sin volcar cuerpos de formularios.
