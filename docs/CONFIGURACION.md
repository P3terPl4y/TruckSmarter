# Configuración

`config/settings.py` lee `.env` en la raíz y las variables del proceso mediante django-environ. Copiar `.env.example` y sustituir los valores de ejemplo. No todas las constantes Django aceptan una variable de entorno: la tabla siguiente enumera las que el proyecto lee explícitamente.

## Variables de entorno

| Variable | Valor por defecto / requisito | Uso |
| --- | --- | --- |
| `SECRET_KEY` | Obligatoria | Firma Django; generar aleatoriamente y mantener privada |
| `DEBUG` | False | True solo en desarrollo; afecta HTTPS/cookies y DNS |
| `ALLOWED_HOSTS` | localhost,127.0.0.1 | Hosts exactos separados por comas, sin esquema |
| `DB_NAME`, `DB_USER`, `DB_PASSWORD` | Obligatorias | Credenciales PostgreSQL |
| `DB_HOST`, `DB_PORT` | localhost,5432 | Servicio PostgreSQL |
| `REDIS_URL` | redis://127.0.0.1:6379/1 | Caché y cuotas; mantener privado |
| `SITE_URL` | http://localhost:8000 | Origen para enlaces de correo |
| `CSRF_TRUSTED_ORIGINS` | Lista vacía | Orígenes con esquema separados por comas |
| `CORS_ALLOWED_ORIGINS` | Lista vacía | Orígenes exactos de API; cerrado por defecto |
| `JWT_SIGNING_KEY` | Vacía | Independiente, ≥32 bytes; vacía deshabilita API con 503 |
| `REQUESTS_PER_MINUTE` | 120 | Cuota general por IP, por ventana de minuto |
| `WRITES_PER_MINUTE` | 30 | Cuota adicional de métodos distintos de GET/HEAD/OPTIONS |
| `CLOUDFLARED_ENABLED` | False | Confiar solo en peers explícitos del túnel privado |
| `CLOUDFLARED_TRUSTED_PEERS` | Lista vacía | IP exacta de cada conector como la ve Django |
| `EMAIL_BACKEND` | django.core.mail.backends.console.EmailBackend | Consola local o SMTP en producción |
| `EMAIL_HOST`, `EMAIL_PORT` | smtp.gmail.com,587 | Transporte SMTP |
| `EMAIL_USE_TLS` | True | TLS SMTP |
| `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD` | Vacías | Credenciales SMTP |
| `DEFAULT_FROM_EMAIL` | webmaster@localhost | Remitente |
| `EMAIL_VALIDATE_DNS` | not DEBUG | Validación DNS del dominio de email |
| `EMAIL_VERIFICATION_API_KEY` | Vacía | Integración opcional Hunter; timeout/fallo tolerado |

Ejemplo local y todas las variables: [../.env.example](../.env.example). Los valores de PostgreSQL/Redis de Compose sustituyen host y URL internos; no publicar sus puertos para producción.

Generar secretos independientes, ejecutando cada comando por separado y guardando la salida únicamente en el entorno privado:

```bash
.venv/bin/python -c 'import secrets; print(secrets.token_urlsafe(64))'
.venv/bin/python -c 'import secrets; print(secrets.token_urlsafe(48))'
```

Usar el primero para SECRET_KEY y el segundo para JWT_SIGNING_KEY. Rotar cualquiera de ellos tiene consecuencias sobre sesiones/tokens; planificar la revocación.

## Constantes de código

| Configuración | Valor actual |
| --- | --- |
| Usuario | users.User |
| Idioma / zona horaria | es-es / America/Mexico_City |
| Password hasher producción | PBKDF2PasswordHasher (PBKDF2-SHA256) |
| Contraseña mínima | 8 caracteres más validadores nativos de similitud/comunes/numéricos |
| Cookies | HttpOnly; Secure con DEBUG=False; sesión Lax, CSRF Strict |
| Sesión | 3600 segundos, expire al cerrar navegador |
| HSTS producción | 31536000 s, includeSubDomains y preload |
| JWT | HS256; 300 s; issuer trucksmarter, audience trucksmarter-api |
| Límite JWT | 10 grants activos por sesión; TTL acotado entre 1 y 900 s en servicio |
| Imagen | 5 MiB por validación de campo |
| Cuerpo declarado / query | 6 MiB / 4096 caracteres |
| Formulario | 256 KiB de datos en memoria, 100 campos y 5 archivos |
| Archivo en memoria | 1 MiB antes de usar archivo temporal |
| Ventana de analytics | 86400 s |
| Redis connect/read timeout | 2 s / 2 s en settings de aplicación |
| Estáticos / media | /static/ → staticfiles; /media/ → media |

`SECURE_SSL_REDIRECT`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE` y `SECURE_PROXY_SSL_HEADER` no se leen directamente del entorno. La confianza del protocolo detrás de Cloudflared la gestiona el middleware validando al peer; no añadir confianza global en cabeceras de cualquier cliente.

El CSP permite scripts propios y nonces, CSS inline por compatibilidad, Google Fonts y Font Awesome desde los hosts definidos. Revisar CSP y templates juntos al incorporar dependencias frontend.

## Pruebas

`config.test_settings` inyecta valores aislados, SQLite en memoria, correo locmem, archivos temporales y hasher MD5 solo para fixtures. `TEST_DATABASE_URL` habilita PostgreSQL; `TEST_REDIS_URL` habilita Redis y ratelimit real. Sin Redis, los dos checks del backend se silencian solo en ese entorno. La guardia global se activa mediante overrides en las pruebas de seguridad.

No usar `config.test_settings` para servir el sitio. Ver [PRUEBAS.md](PRUEBAS.md).
