# Plan de auditoría y mejora

Compartido antes de implementar. Alcance: funcionalidad existente de todas las apps;
sin pagos, API REST ni cambio de diseño. Cada corrección tendrá regresión automatizada.

## Base técnica
Registrar la ejecución original, corregir dependencias, aislar datos/correo/archivos de
pruebas y ejecutar también con PostgreSQL y Redis. Alinear Docker con Django 6.1.

## vehicles
Matriz anónimo/cliente/propietario/otro comerciante/admin/superusuario para crear,
editar, retirar y ver anuncios; catálogo activo, búsqueda, precios decimales,
paginación con filtros, 404, precio positivo, año razonable e imágenes válidas.
Retirar no equivale a vender. Mantener historial y bloquear edición de vendidos.

## core
Centralizar predicados de roles/propiedad, redirigir anónimos al login y devolver
403 a autenticados sin permisos. Probar objetos ausentes y usuarios inactivos.

## users
Registro sin escalada de rol, email normalizado/único, autenticación y logout POST,
perfil con valores iniciales, expiración y consumo único de tokens, invalidación
al cambiar email, rate limit 429 y rutas administrativas funcionales. Creación
administrativa con contraseña validada y hash; superusuario controla privilegios.

## sales
Ofertas válidas (Decimal finito, positivo, dos decimales, inferior al anunciado,
comentario <=650), duplicados por comprador, reserva/cancelación, historial aislado,
POST/CSRF, permisos admin. Mantener regla heredada: no subir oferta posterior.
Serializar por vehículo, estados explícitos, cerrar alternativas al vender y enviar
notificaciones tras commit. Probar rollback y concurrencia con PostgreSQL.

## dashboard
CRUD autorizado, listas paginadas, botones aceptar/rechazar POST con CSRF,
contraseñas seguras y protección de usuarios/marcas vinculados a historial.

## analytics
Contar detalles exitosos GET, deduplicar 24h por usuario/sesión (no IP), aislar
visitantes anónimos, tolerar caída de caché, asegurar consistencia registro/contador,
unificar métricas y permisos administrativos. Comprobar caché real y agregados.

## Criterios de aceptación
Suite original reparada sin esconder fallos, nuevas regresiones por app, migraciones
sin deriva, chequeos Django, integración PostgreSQL/Redis y reporte reproducible
con resultados y límites. No se publicará ni desplegará en producción.
