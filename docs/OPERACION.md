# Instalación, despliegue y operación

## Desarrollo local

1. Instalar Python 3.14, PostgreSQL y Redis; crear un usuario/base exclusivos de la aplicación. No se automatiza aquí la administración del servidor del sistema.
2. Crear `.venv`, instalar `requirements-dev.txt`, copiar `.env.example` a `.env` y sustituir secretos/credenciales. Redis debe estar disponible incluso en desarrollo por la guardia de peticiones.
3. Ejecutar `migrate`, `createsuperuser` y `runserver` según [README](../README.md). Crear vendedores desde el panel o admin; el registro público siempre crea customer.

Para inspeccionar el entorno:

```bash
.venv/bin/pip check
.venv/bin/python manage.py check
.venv/bin/python manage.py showmigrations
```

## Base existente y migraciones

Respaldar PostgreSQL y media antes de actualizar. En una copia de staging:

```bash
.venv/bin/python manage.py audit_data
.venv/bin/python manage.py migrate --plan
.venv/bin/python manage.py migrate
```

`audit_data` es de solo lectura. Las migraciones de endurecimiento rechazan datos históricos incompatibles (emails duplicados sin distinguir mayúsculas, importes inválidos, reservas/ofertas duplicadas); no los borran ni corrigen automáticamente. Resolver esos registros con una decisión de negocio y repetir en staging antes de producción. `users/0003_jwtgrant.py` crea el almacenamiento de grants JWT. No ejecutar `makemigrations` como parte de un despliegue: las migraciones deben venir versionadas.

## Docker Compose

```bash
docker compose build
docker compose run --rm web python manage.py migrate
docker compose run --rm web python manage.py createsuperuser
docker compose up -d
docker compose logs --tail=100 web
```

`dockerfile` instala Python 3.14 y dependencias fijadas; el comando de arranque recolecta estáticos y ejecuta Gunicorn. Compose espera healthchecks de PostgreSQL/Redis. PostgreSQL 15 conserva el major del volumen original; no cambiarlo reutilizando el mismo volumen sin un procedimiento de actualización. Redis usa imagen 7-alpine. Media se monta desde `./media`; PostgreSQL usa `postgres_data`.

El puerto web se publica en `127.0.0.1:8000`, no en todas las interfaces. La imagen, los healthchecks y el montaje deben probarse con Docker en staging: Docker no estaba disponible durante la auditoría local. Nunca usar `docker compose down -v` sobre datos que se quieran conservar.

## Cloudflared

Usar el túnel existente y adaptar [deploy/cloudflared.yml.example](../deploy/cloudflared.yml.example), o configurar la ruta equivalente en el dashboard Cloudflare. No copiar credenciales del túnel al repositorio.

Para un servicio sin Docker:

```bash
.venv/bin/python manage.py collectstatic --noinput
.venv/bin/gunicorn config.wsgi:application \
  --bind 127.0.0.1:8000 --forwarded-allow-ips='' --timeout 30
```

Configurar el supervisor/systemd propio del servidor para arranque y reinicio. Enlazar al origen privado, habilitar `CLOUDFLARED_ENABLED=True` y configurar los peers exactos como explica [SEGURIDAD.md](SEGURIDAD.md). El middleware valida el origen de las cabeceras antes de restaurar IP/protocolo. En Docker la IP vista puede ser la pasarela y debe confirmarse en el entorno real.

WhiteNoise sirve los estáticos recolectados. **La ruta de media no está implementada como servidor de archivos en producción**: con DEBUG=False Django no añade las rutas de desarrollo. Antes de publicar imágenes, configurar el almacenamiento/servicio de media elegido y su ruta en Cloudflare; no asumir que WhiteNoise sirve uploads. No se ha introducido Nginx ni un servicio alternativo sin conocer esa decisión operativa.

Validar por el dominio real: login/logout, formulario CSRF, edición de perfil, publicación con imagen, reserva/oferta, panel y métricas. Confirmar Secure/HttpOnly/SameSite, CSP y HTTPS sin bucles. No habilitar caché pública indiscriminada para HTML personalizado, admin o API de tokens.

## Copias y restauración

Respaldar base PostgreSQL y directorio/almacenamiento media en una ventana coherente. Guardar además secretos y credenciales fuera de Git, con acceso restringido. Redis no sustituye una copia de los datos durables.

Ejemplo para un administrador que ya configuró libpq mediante entorno o `.pgpass` privado, sin contraseña en el comando:

```bash
pg_dump --format=custom --file=/ruta/privada/trucksmarter.dump trucksmarter
```

La ruta debe existir y estar protegida; no usar el repositorio como destino. Probar restauración en una base vacía aislada:

```bash
pg_restore --no-owner --dbname=trucksmarter_restore /ruta/privada/trucksmarter.dump
```

Copiar media al entorno restaurado y verificar rutas/contenido. Documentar retención, frecuencia y objetivos de recuperación según operación. Ni los respaldos programados ni una restauración real se han ejecutado en esta auditoría.

## Mantenimiento

Programar diariamente, con entorno y usuario del servicio:

```bash
.venv/bin/python manage.py prune_tokens
.venv/bin/python manage.py clearsessions
```

`prune_tokens` borra grants vencidos; `clearsessions` limpia sesiones caducadas. Vigilar crecimiento de VehicleView, media y logs. No existe una política automática de purga del historial comercial; no borrarlo sin decisión de negocio. Cambiar la clave JWT invalida tokens emitidos; cambiar SECRET_KEY puede invalidar sesiones y firmas.

Revisar versiones y vulnerabilidades antes de actualizar, actualizar constraints de forma controlada y ejecutar la suite PostgreSQL/Redis. El último refuerzo no incluyó un escáner CVE.

## Diagnóstico

| Síntoma | Comprobar |
| --- | --- |
| 400 DisallowedHost | ALLOWED_HOSTS con el hostname real |
| 403 CSRF | Token del formulario, cookie, origen HTTPS y CSRF_TRUSTED_ORIGINS |
| 403 Untrusted tunnel request | Modo Cloudflared, IP del peer, CF-Connecting-IP y protocolo |
| Bucle HTTPS | Middleware Cloudflared activo y peer correcto; no confiar globalmente en X-Forwarded-Proto |
| 429 general/login | Cuotas por IP, peers del túnel y Retry-After; NAT comparte cuotas |
| 503 en rutas dinámicas | Redis y tiempos de conexión; la guardia falla cerrada |
| 503 solo API JWT | JWT_SIGNING_KEY de al menos 32 bytes |
| 401 API JWT | Firma, expiración, sesión emisora, logout, contraseña o usuario inactivo |
| No llegan correos | Backend SMTP, credenciales y logs; no hay cola/reintento persistente |
| Imágenes rotas | Archivo original y entrega de media en producción |
| Migración rechazada | audit_data e inconsistencias históricas; no saltar restricciones |
| Fallos temporales por cuota | TMPDIR en un directorio de trabajo con espacio/cuota suficiente |

Los logs de la aplicación registran fallos de notificación y caché. No registrar contraseñas, tokens, cabeceras Authorization ni credenciales del túnel. `check --deploy` ayuda a revisar settings, pero no demuestra aislamiento del origen, reglas WAF ni configuración real de Cloudflare.
