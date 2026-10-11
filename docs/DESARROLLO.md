# Guía de desarrollo

## Entorno y organización

Usar Python 3.14 y un virtualenv dedicado. `requirements.txt` fija dependencias directas, `constraints.txt` fija también transitivas y `requirements-dev.txt` añade Black/coverage. Mantener sus versiones coherentes; no actualizar toda la matriz como efecto secundario de un cambio pequeño.

La lógica de negocio compartida vive en servicios, la autorización compartida en `core` y los formularios validan la entrada. Las vistas HTML coordinan respuesta/mensajes/redirecciones; la API JWT tiene sus propios contratos. Usar `reverse()` y namespaces de rutas en vez de enlaces hardcodeados.

## Cambios comerciales

Para nuevas transiciones de ofertas/reservas, extender `sales/workflow.py` manteniendo transacción y orden de bloqueo Vehicle → Sale. Comprobar actor autorizado en la frontera y condiciones de negocio bajo bloqueo. Usar Decimal para dinero. Preservar precio original y filas históricas; no reemplazar servicios por `queryset.update()` desde vistas/admin.

Cuando se añadan restricciones, incluir migración versionada y preflight de datos históricos si corresponde. No importar modelos vivos de la app desde una RunPython: usar `apps.get_model`. Evitar correcciones destructivas silenciosas.

Los correos se programan con on_commit. Si se necesita entrega garantizada, diseñar un outbox/cola persistente; on_commit por sí solo no ofrece reintento ni entrega exactamente una vez.

## Frontend y seguridad

Mantener autoescape y evitar `safe`/mark_safe sobre contenido de usuarios. Scripts inline propios necesitan `nonce="{{ csp_nonce }}"`; no introducir onclick/onerror inline. Las escrituras usan POST y `{% csrf_token %}`. Las cookies CSRF son HttpOnly: el JavaScript debe leer el token del formulario, no de document.cookie.

No usar JWT como autenticación alternativa de las vistas HTML ni desactivar CSRF para emitir tokens. No confiar en cabeceras del cliente fuera del modo Cloudflared validado. Mantener uploads fuera del código y revisar entrega segura de media al cambiar storage.

## Validación antes de publicar

```bash
.venv/bin/pip check
.venv/bin/python manage.py check --settings=config.test_settings
.venv/bin/python manage.py makemigrations --check --dry-run --settings=config.test_settings
.venv/bin/python manage.py test --settings=config.test_settings --noinput
git diff --check
```

Añadir pruebas de comportamiento cuando el cambio lo justifique, especialmente permisos, estados, importes, fugas de datos y concurrencia. Una prueba SQLite no demuestra select_for_update; ejecutar la suite con PostgreSQL/Redis antes de publicar cambios comerciales. Ver [PRUEBAS.md](PRUEBAS.md).

Black usa línea 88 y objetivo py314, definidos en `pyproject.toml`. Coverage incluye ramas en las seis apps y exige 85%; excluye tests/migraciones. CI instala Python 3.14, PostgreSQL 17 y Redis 7, comprueba migraciones y ejecuta cobertura. El resultado local no sustituye el estado del workflow remoto.

## Git y documentación

Revisar `git status`, diff y archivos nuevos antes de stage. No incluir `.env`, claves, credenciales Cloudflared, bases, media, logs o `.test-artifacts`. Los ejemplos contienen placeholders, nunca valores reales. Describir en el commit/PR el comportamiento final, validación y límites materiales.

Actualizar README/guía correspondiente cuando cambien rutas, configuración, permisos o despliegue. Conservar los informes de auditoría como evidencia fechada, sin presentar sus cifras históricas como la suite actual. No hacer push, despliegue o acciones externas fuera del alcance autorizado por el propietario.
