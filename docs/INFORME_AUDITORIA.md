> Informe histórico de la auditoría funcional, anterior al refuerzo de seguridad. La suite actual tiene 174 pruebas aprobadas; consultar [SEGURIDAD.md](SEGURIDAD.md) y [README](../README.md).

# Auditoría funcional e implementación

Fecha: 11 de octubre de 2026. Base: `77a0155`, rama `main`.
Alcance: `vehicles`, `core`, `users`, `sales`, `dashboard`, `analytics` y configuración compartida.
El [plan](PLAN_MEJORAS.md) se compartió antes de implementar.

## Resultados verificados

| Ejecución | Resultado |
|---|---|
| Suite original, con dependencias faltantes instaladas | 43 pruebas aprobadas |
| 70 regresiones nuevas sobre una copia del commit original | 73 fallos de aserción y 16 errores; incluye subcasos |
| Suite final con PostgreSQL 18.6 y Redis 8.0.5 | **149 pruebas aprobadas, sin omisiones** |
| Suite final con SQLite y caché en memoria | **145 aprobadas, 4 omitidas por requerir PostgreSQL** |
| Cobertura de líneas y ramas del código de las apps | **96%** redondeado |
| Comprobaciones Django en integración | Sin incidencias ni comprobaciones silenciadas |
| Deriva de migraciones | `makemigrations --check --dry-run`: sin cambios pendientes |
| Dependencias | `pip check` y resolución local de requirements: correctas |
| Estáticos de producción | `collectstatic`, compresión y URLs del manifiesto: aprobados |
| Integridad del diff | `git diff --check`: correcto |

Entorno: Python 3.14.4, Django 6.1, coverage 7.16.2. Los números de cobertura
excluyen pruebas, fixtures de pruebas y archivos de migración; la migración se
valida mediante una prueba funcional independiente. La cobertura no acredita
experiencia visual, rendimiento bajo carga ni entrega por un proveedor SMTP real.

| Aplicación | Pruebas descubiertas | Cobertura de líneas y ramas |
|---|---:|---:|
| vehicles | 37 | 95,18% |
| core | 17 | 97,65% |
| users | 28 | 93,37% |
| sales | 39 | 95,27% |
| dashboard | 14 | 100% |
| analytics | 14 | 100% |
| Total | 149 | 96% redondeado |

El contraste de regresiones se ejecutó sobre una copia aislada del código original.
Se usó `DEBUG=True` en esa copia para evitar consultas DNS externas del validador
heredado; el código original ignora la nueva opción `EMAIL_VALIDATE_DNS`.
Los fallos de subcasos no representan 89 pruebas independientes: una misma
prueba puede recorrer varios roles, importes o rutas.

## vehicles

### Hallazgos

- La edición exigía rol administrador incluso al propietario comerciante.
- La retirada utilizaba un mixin que necesita `get_object()` sobre una vista que
  no lo implementaba: los propietarios sin rol admin recibían 403.
- Retirar marcaba `sold=True`, confundiendo retirada y venta.
- El detalle admitía anuncios inactivos para cualquier visitante.
- Los filtros ignoraban importes decimales y valores inválidos; paginar perdía los filtros.
- No se exigía precio positivo ni un año razonable.
- Las plantillas referenciaban imágenes estáticas ausentes del repositorio.
- El catálogo mostraba potencia, aceleración y velocidad inventadas para todos los vehículos.

### Mejora implementada

1. Edición y retirada para propietario o administrador; creación para comerciantes/admin.
2. Retirada lógica mediante el servicio transaccional: desactiva, libera reservas y
   cierra operaciones pendientes; conserva el vehículo y no lo declara vendido.
3. Catálogo activo y no vendido. Detalles inactivos reservados a propietario, admin
   o compradores vinculados al historial del vehículo.
4. Venta bloquea edición y republicación; modificación del precio bloqueada mientras hay reserva.
5. Filtros Decimal finitos dentro del rango admitido, formulario visible y paginación
   que conserva la consulta. Los filtros inválidos muestran error y no amplían resultados.
6. Precio mínimo 0,01; año entre 1886 y el siguiente año; imágenes válidas de hasta
   5 MB; validación de archivos nuevos sin abrir archivos históricos ausentes.
7. Índice para catálogo y restricción SQL de precio positivo.
8. Galería existente visible, reserva/cancelación con formularios POST, imagen SVG
   local de respaldo y especificaciones que proceden del modelo.
9. Administración nativa redirige creación, edición y retirada al mismo flujo;
   se desactiva el borrado masivo nativo para no saltarse las reglas comerciales.

### Pruebas

Matrices GET/POST de anónimo, cliente, propietario, otro comerciante, administrador
por rol y superusuario; publicación, propiedad inmutable, retirada sin venta,
CSRF, detalle inexistente/inactivo, vehículo vendido, filtros combinados/decimales/
NaN/infinito, paginación, precio/año/kilometraje inválidos, imagen falsa/válida/grande,
archivo guardado, imagen histórica y galería. Se comprueba que las consultas del
catálogo no crecen una por vehículo. Venta directa repetida o al propio vendedor
se rechaza. Se verifica la redirección del admin nativo.

## core

### Hallazgos

Las reglas estaban repartidas entre mixins y decoradores. Los administradores
anónimos recibían un comportamiento distinto al de otras pantallas. Faltaban
predicados reutilizables y una forma de revisar datos antes de añadir restricciones.

### Mejora implementada

- `core.permissions`: reglas comunes de admin, comerciante y propietario, con
  exclusión explícita de usuarios inactivos.
- Anónimos redirigidos al login con `next`; autenticados sin permisos reciben 403.
- Validadores compartidos de año e imagen.
- Comando `audit_data` de solo lectura para revisar duplicados, importes, estados,
  reservas, anuncios sin vendedor y años inválidos antes de migrar.
- Prueba de actualización desde migraciones originales y prueba del manifiesto estático.

### Pruebas

Reglas con usuarios reales, anónimos y `None`, usuarios inactivos, propiedad,
objeto ausente y redirecciones. La auditoría informa inconsistencias sin modificar
registros. La migración preserva una oferta histórica, detecta emails duplicados
sin distinguir mayúsculas y permite continuar tras corregir el dato duplicado.

## users

### Hallazgos

- El valor por defecto de expiración llamaba a `timedelta` sin importarlo.
- El logout permitía GET.
- Las rutas administrativas no implementaban `test_func()` y apuntaban a plantillas ausentes.
- Los campos adicionales del perfil no cargaban valores iniciales; `commit=False`
  podía crear/escribir perfiles.
- Un enlace de verificación podía verificar un email anterior al actual del usuario.
- El límite de login lanzaba la excepción antes del bloque que pretendía capturarla.
- El enlace de verificación estaba fijado a localhost.

### Mejora implementada

1. Registro atómico de usuario, perfil y token; colisiones de integridad revierten
   el registro parcial y devuelven un error de formulario.
2. Email normalizado y unicidad SQL sin distinguir mayúsculas.
3. Tokens de 24 horas y consumo único; expirados o pertenecientes a otro email no
   se validan. Cambiar el email desde el perfil elimina tokens del email anterior.
4. Logout POST; login respeta `next` local y descarta destinos externos.
5. Límite de cinco intentos por minuto, con respuesta 429 en login y registro.
6. Valores iniciales del perfil y guardado transaccional respetando `commit=False`.
7. Rutas administrativas reparadas. Solo superusuarios gestionan privilegios nativos
   `is_staff`/`is_superuser` o editan cuentas que ya tienen esos privilegios.
8. Creación administrativa con `UserCreationForm`, validación de contraseña y hash;
   el admin nativo usa `UserAdmin` de Django.
9. `SITE_URL`, DNS e integración opcional de verificación configurables.
   Las consultas HTTP usan parámetros y timeout, con mocks en pruebas.

### Pruebas

Registro válido, contraseña débil, email duplicado, intento de elevar rol, colisión
transaccional, caída SMTP, expiración/consumo/email cambiado del token, login
inactivo, redirecciones seguras, límites 429, logout, perfil propio y `commit=False`,
roles administrativos, DNS MX y proveedor externo válido/inválido/no disponible.

Se conserva la política existente: verificar email no es requisito para iniciar
sesión. Cambiar esta política necesita una decisión de producto y un flujo de reenvío.

## sales

### Hallazgos

- GET podía reservar, cancelar y decidir ofertas, saltándose la protección CSRF
  aplicable a operaciones de escritura.
- Importes inválidos como texto o NaN podían provocar excepciones.
- Una reserva anterior sin `offered_price` causaba comparaciones con `None`.
- `reserved` se guardaba aunque no estaba en las opciones del modelo.
- Aceptar ofertas distintas bloqueaba filas Sale distintas; no serializaba el vehículo.
- Aceptar dejaba alternativas pendientes; rechazar podía liberar una reserva ajena.
- Los correos se enviaban dentro de transacciones que aún podían revertirse.
- Borrar usuarios, marcas o vehículos podía borrar el historial por cascada.

### Mejora implementada

1. `sales.workflow` centraliza las transiciones con `transaction.atomic()` y bloqueo
   de Vehicle antes de tocar Sale. Incluye compras directas y cambios de anuncios.
2. Todas las operaciones HTTP de escritura exigen POST y conservan CSRF.
3. Formulario Decimal: finito, positivo, dos decimales, inferior al precio publicado;
   comentario opcional de hasta 650 caracteres.
4. Una oferta pendiente por comprador/vehículo, una reserva por vehículo y una venta
   final por vehículo mediante restricciones SQL condicionales.
5. Estado `reserved` explícito; reserva ajena no puede cancelarse y un vehículo
   reservado no acepta nuevas ofertas.
6. Aceptación cierra otras ofertas y reservas y retira el vehículo. Rechazo de una
   oferta mantiene intacta una reserva independiente.
7. Correo diferido hasta `on_commit`; fallo SMTP se registra y no revierte una
   operación ya confirmada. Rollback no envía notificaciones.
8. Relaciones comerciales protegidas frente al borrado. Historial privado y paginado,
   con precio publicado y precio ofertado diferenciados.

### Pruebas

Ofertas válidas, importes malformados, límite de comentario, múltiples compradores,
duplicados, reserva/cancelación, titularidad, reservas previas con precio nulo,
vehículo reservado/huérfano/vendido, matriz de admin, métodos HTTP y CSRF, privacidad
del historial, alternativas cerradas y preservación de reserva ajena.

También se prueban entrega al comprador/admin con backend de memoria, caída SMTP,
commit, rollback y restricciones de base de datos. Cuatro carreras reales, cada una
con conexiones independientes y barrera de sincronización, comprueban:

- Dos reservas simultáneas: un ganador.
- Dos aceptaciones simultáneas: una venta final y la otra oferta cerrada.
- Dos ofertas simultáneas del mismo comprador: una pendiente.
- Compra frente a nueva oferta: ninguna oferta pendiente después de vender.

El flujo de integración atraviesa detalle, formulario con CSRF real, oferta,
dashboard, aceptación e historial. Un comprador puede consultar su vehículo vendido;
un visitante anónimo recibe 404.

Se conserva la regla heredada que impide subir una oferta posterior. La aceptación
por admin puede cerrar una reserva existente; no se introduce cobro ni pasarela de pagos.

## dashboard

### Hallazgos

Faltaban los botones de decisión; el listado de ofertas no heredaba la plantilla
base. Crear usuarios no solicitaba contraseña segura. Los borrados podían destruir
vehículos e historial y los listados crecían sin paginación.

### Mejora implementada

- Acceso común de administrador, con login para anónimos y 403 a otros roles.
- Usuarios, marcas y ofertas paginados; consultas relacionadas agrupadas.
- Creación de usuarios con contraseña validada y hash. Privilegios nativos reservados
  a superusuarios; las cuentas privilegiadas no son editables por admin de negocio.
- Aceptar/rechazar desde formularios POST con CSRF y plantilla base.
- Borrados vinculados bloqueados con mensaje de interfaz; se indica la opción de
  desactivar usuarios. Una cuenta no puede borrarse a sí misma.

### Pruebas

Todas las rutas administrativas, roles, CRUD de marcas, nombres duplicados,
creación de usuarios, contraseña/hash, escalada de privilegios, protección de cuentas,
marca/usuario vinculados, borrado de registros sin vínculos, paginación y botones POST.

## analytics

### Hallazgos

- Los anónimos sin sesión se agrupaban por IP.
- La lectura de Redis podía fallar fuera del manejador de errores y romper el detalle.
- Contar antes de resolver la vista permitía contar solicitudes que acababan en error.
- Perder la caché permitía contar de nuevo antes de 24 horas.
- Había funciones duplicadas y variables de contexto que no coincidían con la plantilla.
- Se usaba `is_staff` en lugar del rol de negocio usado por el dashboard.

### Mejora implementada

1. Contar solo detalles GET resueltos con éxito; HEAD, POST y 404 no generan visitas.
2. Identidad por usuario o sesión anónima creada expresamente; nunca por IP.
3. Caché rápida más comprobación persistente de ventana de 24 horas. Bloqueo del
   vehículo mantiene deduplicación y contador consistentes entre trabajadores.
4. Registro y contador en la misma transacción; caché actualizada después del commit.
5. Fallos de lectura/escritura de Redis registrados sin romper el detalle, con
   deduplicación por base de datos como respaldo.
6. Vistas consolidadas, métricas alineadas con la plantilla, relaciones precargadas
   y permisos de administrador comunes.

### Pruebas

Visita inicial, repetida, expulsión de caché, ventana expirada, dos anónimos con
misma IP/sesiones distintas, cache hit, errores de caché/base de datos, GET/HEAD/POST/
404, métricas vacías/con visitas, permisos admin/staff y detalle estadístico inexistente.

## Configuración e integración

- Dependencias faltantes declaradas; versiones directas y transitivas fijadas en
  requirements/constraints. Herramientas de pruebas separadas en requirements-dev.
- Se retiran dependencias sin uso y el paquete `environ` distinto de `django-environ`.
- Docker pasa de Python 3.11 a 3.14 y declara el nombre `dockerfile` explícitamente.
- Compose incluye Redis, healthchecks y credenciales desde `.env`. Se mantiene
  PostgreSQL 15 en Compose para no cambiar la versión del volumen existente.
- `collectstatic` se ejecuta con configuración de ejecución, evitando secretos de
  producción durante la construcción. Se utiliza `STORAGES` para WhiteNoise.
- El origen CSRF fijo se reemplaza por configuración; `.env.example` corresponde
  a desarrollo local y debe adaptarse para producción.
- GitHub Actions ejecutará comprobaciones, migraciones y cobertura con PostgreSQL/Redis.
  El workflow está añadido al repositorio; no se ha ejecutado en GitHub.

Compatibilidad de Python contrastada con las [notas oficiales de Django 6.1](https://docs.djangoproject.com/en/dev/releases/6.1/).
La elección de pruebas transaccionales sigue la documentación de
[`select_for_update`](https://docs.djangoproject.com/en/dev/ref/models/querysets/#select-for-update)
y de [`on_commit`](https://docs.djangoproject.com/en/dev/topics/db/transactions/#performing-actions-after-commit).
Redis se conserva como backend de producción por los requisitos de
[incrementos atómicos de django-ratelimit](https://django-ratelimit.readthedocs.io/en/stable/installation.html).

## Migraciones y revisión de datos

Se añaden migraciones a users, vehicles y sales, conservando las originales.
Antes de aplicar unicidad/precios se comprueban los datos históricos. Si hay
inconsistencias que impiden una restricción, la migración se detiene con un mensaje
explícito; no fusiona usuarios, elimina ventas ni inventa precios.

Procedimiento para una base existente: respaldo, ejecutar `audit_data` con el código
nuevo, revisar los registros señalados, aplicar `migrate` en un entorno de validación
y después repetir las pruebas de negocio. Los datos reales del usuario no se han
migrado durante esta auditoría.

Se actualizaron dos expectativas de pruebas heredadas: retirar no significa vender,
y un comerciante autenticado sin permiso recibe 403 al aceptar una oferta.
La prueba heredada de retirada ahora usa un propietario comerciante, no administrador.

## Límites y siguientes mejoras

| Prioridad | Trabajo pendiente | Motivo |
|---|---|---|
| Antes de publicar | Validar migraciones y datos reales en staging | Solo se usaron datos sintéticos |
| Antes de publicar | Construir y probar imagen Docker y HTTPS/proxy en destino | Docker no está instalado en este entorno |
| Antes de publicar | Probar SMTP y enlaces con el dominio real | Correos locales y proveedor externo simulados |
| Alta | Outbox/cola persistente y reintentos de correo | on_commit evita envíos previos al commit, pero no garantiza entrega ante caída del proceso |
| Alta | Reenvío de verificación y decisión sobre acceso sin verificar | Se conserva la política actual de login |
| Media | Pruebas visuales de navegador y accesibilidad | Se verificaron respuestas y formularios con el cliente Django |
| Media | Medición de carga y contención del bloqueo de vehículo | Las carreras verifican invariantes, no capacidad máxima |
| Media | Gestión de galería desde formulario de comerciante | La galería existente se ve y puede administrarse desde Django admin |
| Continua | Actualizar parches y revisar constraints en CI | Versiones fijadas requieren mantenimiento deliberado |

No se realizaron commit, push ni despliegue. Los cambios y documentos quedan
locales, listos para revisión.
