# Macmanix en el puerto 8800 — 11/10/2026

## Estado

La aplicación se ejecuta con Gunicorn en **127.0.0.1:8800**, DEBUG=False y las protecciones de producción. El logo original `static/Macmanix.jpg` aparece en la esquina superior izquierda de la cabecera, enlaza al inicio y conserva su proporción en escritorio y móvil. El título del navegador usa Macmanix.

Se reutilizó la ruta ya existente en `/etc/cloudflared/config.yml`:

```text
catalog.macmanix.duohnson.com → http://localhost:8800
```

No se modificó el túnel ni las rutas de otras aplicaciones. Durante la comprobación el hostname no resolvía por DNS, de modo que **no se confirmó acceso público HTTPS**. El origen sí respondió 200 en catálogo, login y logo usando las cabeceras del peer de túnel confiable. El paso pendiente es comprobar/publicar el registro DNS de ese hostname en Cloudflare y la cobertura de su certificado; la ruta local del túnel por sí sola no prueba que exista DNS público.

El origen rechaza peticiones que no vengan del peer confiable con las cabeceras válidas; abrir directamente `http://localhost:8800` en un navegador no representa la entrada pública prevista. No desactivar esa protección para resolver un problema DNS.

## Servicios separados

| Servicio del usuario | Recurso |
| --- | --- |
| macmanix-web.service | Gunicorn, 2 workers, 127.0.0.1:8800 |
| macmanix-postgresql.service | PostgreSQL 18, 127.0.0.1:55441 |
| macmanix-redis.service | Redis, 127.0.0.1:56381 |

Los tres servicios se instalaron en `~/.config/systemd/user/`, se habilitaron y estaban activos. El usuario tiene `Linger=yes`, por lo que su gestor puede arrancarlos sin una sesión interactiva. Los ejemplos exactos están en [deploy/systemd](../deploy/systemd); incluyen rutas específicas de esta máquina y requieren adaptar paths/versiones en otro host. PostgreSQL y Redis deben estar inicializados antes de habilitar las unidades en una instalación nueva.

No se reutilizaron la base de pruebas, Redis de pruebas ni los servicios de otras aplicaciones. La base `trucksmarter` se creó vacía, con todas las migraciones y un rol de aplicación sin privilegios de superusuario. No se importaron vehículos ni usuarios ficticios, ni se creó una cuenta administrativa con contraseña predeterminada.

PostgreSQL usa autenticación SCRAM por TCP y peer por socket Unix privado. Redis tiene contraseña y solo escucha en loopback. Las claves Django/JWT y credenciales de servicios se generaron aleatoriamente y permanecen en `.env` (600) y `.runtime` (700), excluidos de Git/Docker. No copiar estos datos a documentación ni commits.

## Operación

```bash
systemctl --user status macmanix-web macmanix-postgresql macmanix-redis
systemctl --user restart macmanix-web
journalctl --user -u macmanix-web -n 100 --no-pager
```

Los logs HTTP y Gunicorn están en `.runtime/access.log` y `.runtime/web.log`; datos PostgreSQL en `.runtime/postgres`, datos Redis en `.runtime/redis`, configuración Redis privada en `.runtime/redis.conf`. Respaldar la base y media; `.runtime` no es una copia de seguridad.

Para actualizar código/estáticos, desde `/home/peter/TruckSmarter` y con el entorno privado configurado:

```bash
TMPDIR="$PWD/.runtime/tmp" .venv/bin/python manage.py audit_data
TMPDIR="$PWD/.runtime/tmp" .venv/bin/python manage.py migrate --noinput
TMPDIR="$PWD/.runtime/tmp" .venv/bin/python manage.py collectstatic --noinput
TMPDIR="$PWD/.runtime/tmp" .venv/bin/python manage.py check --deploy --fail-level WARNING
systemctl --user restart macmanix-web
```

Para crear la primera cuenta administrativa, usar el asistente sin guardar contraseñas en comandos o historial:

```bash
.venv/bin/python manage.py createsuperuser
```

El correo está configurado con backend de consola porque no se proporcionaron credenciales SMTP. Configurar SMTP antes de ofrecer verificación por correo a usuarios reales. La entrega de media en producción sigue siendo una decisión pendiente descrita en [OPERACION.md](OPERACION.md); el logo es un estático y se sirve correctamente mediante WhiteNoise.

## Validación

- Migraciones de la base nueva aplicadas y collectstatic completado.
- `check --deploy --fail-level WARNING`: sin hallazgos en la configuración efectiva.
- Siete pruebas de assets/cookies/CSRF/CORS/XSS/SQL/PBKDF2 aprobadas tras aislar `CLOUDFLARED_ENABLED=False` en settings de pruebas. La configuración privada del despliegue no debe activar la restricción de peer dentro del test client.
- Origen: catálogo/login/logo 200, CSP presente, cookie CSRF Secure/HttpOnly y bytes del logo iguales al original.
- Vista previa de HTML renderizado comprobada en Firefox; no constituye una prueba de acceso por Cloudflare. Capturas en `.test-artifacts`, fuera de Git.
- Suite completa repetida con PostgreSQL/Redis de pruebas: **174 aprobadas**, sin omisiones ni checks silenciados. Evidencia local en `.test-artifacts/logo-postgres.txt`.
- DNS público: pendiente; no se ha declarado el dominio accesible.
