# Aplicaciones y reglas de negocio

## Roles y permisos

| Acción | Anónimo | Usuario activo | Vendedor activo | Admin comercial / superusuario |
| --- | --- | --- | --- | --- |
| Ver catálogo disponible | Sí | Sí | Sí | Sí |
| Editar perfil propio | No | Sí | Sí | Sí |
| Crear publicación | No | No | Sí | Sí |
| Editar/retirar publicación | No | Solo si es propietario | Solo propias | Todas, salvo restricciones de estado |
| Ofertar/reservar | No | Sí, salvo vehículo propio | Sí, salvo vehículo propio | Sí, salvo vehículo propio |
| Aceptar/rechazar ofertas | No | No | No | Sí |
| Ver historial | No | Propio | Propio | Propio |
| Panel y métricas | No | No | No | Sí |

`role=admin` es un permiso comercial. No implica `is_staff` ni acceso al admin nativo `/admin/`. Un administrador comercial no puede editar cuentas staff/superuser ni asignarse esos privilegios mediante el formulario. El superusuario sí puede gestionar los campos nativos permitidos. Los usuarios inactivos no satisfacen los helpers de permisos.

## vehicles

`Brand` tiene nombre único y logo opcional. `Vehicle` almacena marca/modelo/año, precio decimal, kilometraje, transmisión, combustible, condición nuevo/usado, descripción, imagen principal, propietario y estados. `VehicleImage` contiene imágenes adicionales y una marca de imagen primaria.

El catálogo solo muestra `is_active=True, sold=False`. Los filtros son `q` (marca/modelo/descripción), `brand` (nombre parcial), `min_price`, `max_price`, con conservación de parámetros al paginar. Los importes deben ser finitos, no negativos y representables; un filtro inválido informa el error y devuelve un catálogo vacío.

El detalle admite unidades disponibles o acceso relacionado con propietario, admin o comprador del historial. Publicar requiere vendedor/admin. Editar y retirar requieren propietario/admin. Una unidad vendida no se edita ni reactiva. Una reserva impide cambiar el precio hasta cancelarla. La retirada cierra ofertas y reservas sin borrar el historial. El admin nativo de vehículos dirige estas operaciones hacia las vistas transaccionales y desactiva acciones masivas.

Precio mínimo: 0.01; año desde 1886 hasta el próximo año. La imagen principal admite JPG/JPEG/PNG/GIF y hasta 5 MiB. El formulario valida que el contenido sea imagen, no solo su extensión. Las cargas de logo/galería tienen el validador de tamaño propio; no todas comparten la misma lista de extensiones del campo principal.

## users

`User` extiende AbstractUser: email único, también sin distinguir mayúsculas, y rol customer por defecto. `Profile` guarda teléfono, dirección y datos de contacto de pago; no procesa cobros. Una señal crea el perfil al crear la cuenta.

Registro crea usuario y `EmailVerification` en una transacción, inicia sesión y programa correo tras commit. El token UUID expira en 24 horas y se consume una sola vez. El vínculo solo verifica el email actual que originó el token. Cambiarlo elimina verificaciones obsoletas. La verificación de correo **no es obligatoria para iniciar sesión** en la implementación actual.

Login respeta `next` seguro, impide redirecciones externas y dirige al admin al panel. Registro/login tienen límite de 5 POST/minuto por IP. Logout solo acepta POST. La edición de perfil conserva valores, admite commit diferido y no permite escalar rol.

`JWTGrant` guarda identificador hasheado, sesión emisora, hash de autenticación y expiración. Ver contratos y revocación en [API](API.md) y [seguridad](SEGURIDAD.md).

## sales

`Sale.amount` conserva el precio publicado al crear la operación; `offered_price` conserva la propuesta cuando existe. El historial no se recalcula al cambiar el precio del vehículo. Comprador/vendedor/vehículo tienen FK protegidas.

| Operación | Condición | Resultado |
| --- | --- | --- |
| Ofertar | Unidad activa, libre, no propia; importe positivo menor al precio; hasta 2 decimales; comentario ≤650 caracteres | `offer_pending` |
| Reofertar | Sin otra pendiente del mismo comprador; importe no mayor que su última oferta no nula | Nueva fila de oferta |
| Rechazar | Admin y oferta pendiente | `offer_rejected`, unidad continúa disponible |
| Aceptar | Admin y oferta pendiente sobre unidad disponible | `offer_accepted`, unidad vendida/inactiva; cierra alternativas |
| Reservar | Unidad activa, libre, no propia | `reserved`, vehículo vinculado al comprador |
| Cancelar reserva | Comprador titular y unidad no vendida | `cancelled`, unidad liberada |
| Completar compra | Servicio interno, unidad disponible y comprador elegible | `completed`, unidad vendida/inactiva |
| Retirar anuncio | Unidad no vendida, vista autorizada | Unidad inactiva; ofertas/reservas canceladas |

No hay endpoint público de pago o completar compra. `Vehicle.mark_as_sold()` delega al servicio transaccional interno. La aceptación de oferta ya marca la unidad vendida; no representa una confirmación bancaria. El historial es privado y paginado; las decisiones administrativas se consultan en el panel de ofertas.

## dashboard

Panel comercial protegido por el rol admin/superusuario. Gestiona usuarios, marcas y ofertas con páginas de 25 registros. Crea contraseñas mediante los formularios nativos de hashing/validación. Impide autoeliminación y protege cuentas privilegiadas frente a admins comerciales. Borrar un usuario/marca con historial protegido muestra un mensaje; se recomienda desactivar el usuario. Las decisiones de ofertas usan POST y servicios de `sales`.

## analytics

`VehicleView` registra vehículo, usuario opcional, sesión y fecha. Solo un GET exitoso de detalle contabiliza visita; no HEAD, POST o 404. Deduplicación de 24 horas por usuario autenticado o sesión anónima, con Redis y respaldo SQL. Dashboard global y estadísticas de unidad son administrativos. `Vehicle.view_count` es un acumulado, mientras `VehicleView` permite consultar periodos.

## core

Centraliza permisos (`permissions.py`, `mixins.py`), validadores (`validators.py`), guardia de peticiones y confianza Cloudflared (`security.py`). Sus comandos son `audit_data` (solo lectura) y `prune_tokens` (elimina grants vencidos). `core/testing.py` contiene fixtures compartidos con roles reales; no debe importarse desde código de producción.
