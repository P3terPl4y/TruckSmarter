# Reproducir las pruebas

## Instalación

Usar Python 3.14 y un entorno virtual dedicado:

```bash
python3.14 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/pip check
```

Las versiones transitivas están fijadas en `constraints.txt`. Las pruebas no
necesitan `.env`, SMTP real ni credenciales de proveedores externos.

## Suite rápida

```bash
.venv/bin/python manage.py check --settings=config.test_settings
.venv/bin/python manage.py makemigrations --check --dry-run --settings=config.test_settings
.venv/bin/python manage.py test --settings=config.test_settings --noinput
```

Resultado funcional previo al refuerzo: 149 casos, 145 aprobados y 4 omitidos.
La suite de seguridad actual añadió 25 casos: todos pasaron también en SQLite.
No se ha repetido aquí una ejecución conjunta SQLite de los 174 casos. SQLite no demuestra
las garantías de bloqueo de PostgreSQL. En este modo rate limiting se desactiva
por defecto y se activa en los casos específicos; dos comprobaciones del backend
de caché se silencian únicamente en esta configuración de pruebas local.

Para ejecutar una aplicación:

```bash
.venv/bin/python manage.py test vehicles --settings=config.test_settings --verbosity=2
.venv/bin/python manage.py test users --settings=config.test_settings --verbosity=2
.venv/bin/python manage.py test sales --settings=config.test_settings --verbosity=2
.venv/bin/python manage.py test dashboard --settings=config.test_settings --verbosity=2
.venv/bin/python manage.py test analytics --settings=config.test_settings --verbosity=2
.venv/bin/python manage.py test core --settings=config.test_settings --verbosity=2
```

## PostgreSQL y Redis

Usar una base PostgreSQL de pruebas y un usuario con permiso para crear su base
`test_...`. Usar una base Redis exclusiva para pruebas: la suite limpia esa caché.
Los endpoints siguientes corresponden a los servicios aislados empleados en la
auditoría; se pueden sustituir por los de otro entorno de pruebas.

```bash
export TEST_DATABASE_URL=postgresql://peter@127.0.0.1:55440/trucksmarter_audit
export TEST_REDIS_URL=redis://127.0.0.1:56380/0
.venv/bin/coverage run manage.py test --settings=config.test_settings --noinput
.venv/bin/coverage report
```

Resultado actual verificado: 186 aprobados (25 de seguridad y 12 de administración de contraseñas), sin omisiones ni comprobaciones silenciadas;
96% de cobertura redondeada, incluyendo ramas. El umbral configurado es 85%.
Las migraciones y las pruebas se ejecutan sobre una base temporal creada y borrada
por Django. Nunca usar credenciales ni caché de producción para estos comandos.

Los cuatro casos de carrera están en `sales/test_transactions.py` y usan hilos con
conexiones independientes. No se sustituye el bloqueo SQL por un mock.

## Temporales

Si `/tmp` tiene una cuota pequeña, usar un directorio de trabajo temporal:

```bash
mkdir -p .test-artifacts
export TMPDIR="$PWD/.test-artifacts"
```

Las imágenes y la colección de estáticos se guardan en directorios temporales y
se limpian al finalizar. `.test-artifacts` está excluido de Git y Docker.

## Evidencia local de esta ejecución

En `.test-artifacts/` quedaron `final-postgres.txt`, `final-sqlite.txt`,
`coverage.txt` y `coverage.json` de la auditoría funcional. El refuerzo actual dejó
`security-postgres.txt`, `security-sqlite.txt` y `security-coverage.txt`. Son artefactos generados, no fuentes.
El resumen permanente se encuentra en [INFORME_AUDITORIA.md](INFORME_AUDITORIA.md).

## Configurar desarrollo y Docker

Para ejecutar la aplicación, copiar `.env.example` a `.env`, sustituir la clave y
configurar PostgreSQL/Redis. El ejemplo usa DEBUG y correo de consola para desarrollo.

Con Docker disponible:

```bash
docker compose build
docker compose run --rm web python manage.py migrate
docker compose run --rm web python manage.py createsuperuser
docker compose up -d
```

La construcción de la imagen no se ejecutó en esta máquina. Compose utiliza el
Dockerfile `dockerfile` y espera que PostgreSQL/Redis estén saludables. Para
producción configurar DEBUG=False, hosts, origen CSRF, SITE_URL, HTTPS/proxy y SMTP.

## Base de datos existente

Con la configuración de la base a revisar, hacer un respaldo y ejecutar antes de migrar:

```bash
.venv/bin/python manage.py audit_data
.venv/bin/python manage.py migrate --plan
```

`audit_data` no escribe datos. Si informa inconsistencias, revisar los registros
antes de aplicar restricciones; las migraciones incluyen comprobaciones que
impiden aceptar duplicados o importes inválidos. Validar primero en staging.

## Contraseñas del panel y compatibilidad de recarga

`dashboard/test_passwords.py` añade 12 casos para permisos, validación, CSRF, revocación, sesión propia y enlaces compatibles con procesos que aún no tengan la ruta nueva. La suite completa más reciente aprobó **186 casos con PostgreSQL/Redis y 96% de cobertura redondeada**. El panel aislado aprobó 26 casos.

La primera repetición encontró falta de cuota en el PostgreSQL de pruebas ubicado en `/tmp`, no un fallo de la base real. La validación final usó un PostgreSQL temporal separado en `.test-artifacts/password-postgres-data`, puerto 55442, con base `trucksmarter_password_tests` y el Redis exclusivo de pruebas en 56380. La instancia PostgreSQL temporal se detuvo al finalizar. Evidencias: `password-postgres-home.txt`, `password-dashboard.txt` y `password-coverage.txt` dentro de `.test-artifacts`.
