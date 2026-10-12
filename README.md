# TruckSmarter

Plataforma Django para publicar vehículos, negociar ofertas, reservar unidades y consultar métricas. El sitio usa sesiones y formularios HTML; dispone además de una API JWT pequeña para identificar al usuario.

Estado verificado el 11/10/2026: **186 pruebas aprobadas con PostgreSQL y Redis**, incluidas **25 de seguridad y 12 del cambio de contraseñas del panel**, con **96% de cobertura de líneas y ramas redondeada**. Estos resultados corresponden al código local; no certifican un despliegue de producción.

Sitio desplegado: **[catalog-macmanix.duohnson.com](https://catalog-macmanix.duohnson.com/)**, mediante Cloudflared hacia el puerto 8800.

## Documentación

| Guía | Contenido |
| --- | --- |
| [Arquitectura](docs/ARQUITECTURA.md) | Estructura, relaciones, transacciones y decisiones técnicas |
| [Aplicaciones y negocio](docs/APLICACIONES.md) | Responsabilidades, permisos y flujos de las seis apps |
| [Rutas y API](docs/API.md) | Endpoints HTML, JWT, contratos y errores |
| [Configuración](docs/CONFIGURACION.md) | Variables de entorno y límites configurados en código |
| [Despliegue actual en 8800](docs/DESPLIEGUE_8800.md) | Servicios Macmanix, logo, estado DNS y mantenimiento |
| [Operación y Cloudflared](docs/OPERACION.md) | Instalación, Docker, despliegue, respaldos y diagnóstico |
| [Pruebas](docs/PRUEBAS.md) | Suite rápida, PostgreSQL/Redis y cobertura |
| [Seguridad](docs/SEGURIDAD.md) | Cookies, CSRF, CORS, CSP, JWT y protección contra abuso |
| [Desarrollo](docs/DESARROLLO.md) | Convenciones, validación y cambios seguros |
| [SSH y GitHub](docs/SSH_GITHUB.md) | Clave dedicada, acceso y publicación |
| [Plan aplicado](docs/PLAN_MEJORAS.md) | Plan de la auditoría funcional original |
| [Informe funcional](docs/INFORME_AUDITORIA.md) | Resultados históricos anteriores al refuerzo de seguridad |

## Inicio rápido

Requisitos: Python 3.14, PostgreSQL y Redis. Las versiones Python están fijadas en `requirements.txt` y `constraints.txt`. Compose conserva PostgreSQL 15 para respetar la versión del volumen original; la validación local se ejecutó con PostgreSQL 18.6 y Redis 8.0.5. CI configura PostgreSQL 17 y Redis 7; no se ha ejecutado aquí el workflow remoto.

```bash
git clone https://github.com/P3terPl4y/TruckSmarter.git
cd TruckSmarter
python3.14 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
cp .env.example .env
```

Editar `.env`: generar `SECRET_KEY`, establecer las credenciales PostgreSQL y `REDIS_URL`. El ejemplo usa desarrollo local y correo de consola. No usar sus valores de ejemplo en producción.

```bash
.venv/bin/python manage.py migrate
.venv/bin/python manage.py createsuperuser
.venv/bin/python manage.py runserver
```

Abrir `http://127.0.0.1:8000/`. Para un despliegue existente, ejecutar primero el respaldo y `audit_data` descritos en [operación](docs/OPERACION.md).

## Componentes

| Componente | Función |
| --- | --- |
| `vehicles` | Catálogo, marcas, imágenes y publicaciones |
| `users` | Cuentas, perfiles, verificación de correo, sesiones y JWT |
| `sales` | Ofertas, reservas, historial y transiciones transaccionales |
| `dashboard` | Administración comercial de usuarios, marcas y ofertas |
| `analytics` | Visitas únicas por usuario/sesión y métricas administrativas |
| `core` | Permisos, validadores, middleware de seguridad y comandos operativos |
| `config` | Settings, rutas principales y entradas WSGI/ASGI |
| `templates`, `static` | HTML compartido, correos, CSS, JavaScript y fallback de imágenes |
| `deploy` | Ejemplo de configuración Cloudflared |

## Comprobaciones

```bash
.venv/bin/python manage.py check --settings=config.test_settings
.venv/bin/python manage.py makemigrations --check --dry-run --settings=config.test_settings
.venv/bin/python manage.py test --settings=config.test_settings --noinput
```

SQLite omite los cuatro casos que requieren bloqueo real de PostgreSQL. Para demostrar las garantías de concurrencia y rate limiting, seguir [PRUEBAS.md](docs/PRUEBAS.md) con PostgreSQL y Redis exclusivos de pruebas.

## Producción

El acceso público previsto es **Cloudflare Tunnel → Cloudflared → Gunicorn → Django**, con el origen privado. El middleware solo confía en cabeceras del túnel desde peers explícitos. No se utiliza Nginx. WhiteNoise sirve estáticos; Django entrega las imágenes públicas de vehicles y brands en /media/, incluso con DEBUG=False, sin Nginx.

JWT permanece deshabilitado hasta configurar una clave independiente válida. Las contraseñas usan PBKDF2-SHA256 con sal; SHA-256 es una función hash, no cifrado. No subir `.env`, credenciales del túnel, claves privadas, respaldos ni archivos de usuarios a Git.
