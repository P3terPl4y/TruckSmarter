# 🚛 TruckSmarter — Resumen Ejecutivo del Desarrollo

## 📋 Tabla de Contenidos
1. [Resumen del Proyecto](#resumen-del-proyecto)
2. [Estructura Actual del Proyecto](#estructura-actual-del-proyecto)
3. [Guía de Instalación desde Cero](#guía-de-instalación-desde-cero)
4. [Arquitectura y Aplicaciones](#arquitectura-y-aplicaciones)
5. [Pruebas de Seguridad Realizadas](#pruebas-de-seguridad-realizadas)
6. [Configuraciones Seguras para Producción](#configuraciones-seguras-para-producción)
7. [Decisiones de Diseño y Arquitectura](#decisiones-de-diseño-y-arquitectura)
8. [Lo que está Bien Hecho](#lo-que-está-bien-hecho)
9. [Áreas de Mejora y Recomendaciones](#áreas-de-mejora-y-recomendaciones)
10. [Comandos Útiles](#comandos-útiles)
11. [Errores Frecuentes y Soluciones](#errores-frecuentes-y-soluciones)
12. [Roadmap y Próximos Pasos](#roadmap-y-próximos-pasos)

---

## 📌 Resumen del Proyecto

**TruckSmarter** es una plataforma web de concesionario de vehículos desarrollada con Django. Permite a los usuarios:
- Ver un catálogo de vehículos con filtros y paginación.
- Registrarse e iniciar sesión con roles (`admin`, `seller`, `customer`).
- Hacer ofertas de compra en vehículos (sistema de negociación).
- Gestionar vehículos (crear, editar, eliminar) — solo administradores y comerciantes.
- Panel de administración personalizado para gestionar usuarios, marcas y ofertas.
- Ver métricas y estadísticas de los vehículos (analytics).

**Stack tecnológico:**
- **Backend:** Django 5.1.7, Python 3.13.3
- **Base de datos:** PostgreSQL 17.7
- **Caché:** Redis 7.x (con `django-redis`)
- **Servidor WSGI:** Gunicorn 21.2.0
- **Servidor web:** Nginx (con proxy inverso y SSL)
- **Frontend:** HTML, CSS personalizado (Ferrari‑inspired), JavaScript vanilla, Bootstrap 5 (solo para modal)
- **Envío de emails:** SMTP (Gmail) o console backend (desarrollo)
- **Rate limiting:** django-ratelimit

---

## 📁 Estructura Actual del Proyecto

```
TruckSmarter/
├── analytics/                 # Aplicación de métricas y estadísticas
│   ├── mixins.py             # TrackVehicleViewMixin (registra vistas de vehículos)
│   ├── models.py             # VehicleView (registro de visualizaciones)
│   └── urls.py, views.py
├── config/                    # Configuración principal de Django
│   ├── settings.py           # Configuración central (variables de entorno, apps, seguridad)
│   ├── urls.py               # Rutas principales
│   └── wsgi.py, asgi.py
├── core/                      # Utilidades reutilizables
│   ├── mixins.py             # AdminRequiredMixin, SellerRequiredMixin, OwnerOrAdminRequiredMixin
│   └── tests.py
├── dashboard/                 # Panel de administración personalizado
│   ├── views.py              # Gestión de usuarios, marcas, ofertas
│   ├── urls.py
│   └── templates/dashboard/
├── sales/                     # Sistema de ofertas y reservas (histórico)
│   ├── models.py             # Sale (ofertas, reservas)
│   ├── views.py              # make_offer, accept_offer, reject_offer, reserve_vehicle (histórico)
│   ├── services.py           # Envío de emails (notificaciones)
│   ├── urls.py
│   └── templates/sales/
├── users/                     # Gestión de usuarios y autenticación
│   ├── models.py             # User (AbstractUser), Profile, EmailVerification
│   ├── views.py              # register, login, profile, verify_email
│   ├── forms.py              # CustomUserCreationForm, ProfileForm, UserAdminForm
│   ├── services.py           # send_verification_email, verify_email_api
│   ├── validators.py         # validate_email_domain (validación de email)
│   ├── urls.py
│   └── templates/users/      # register.html, login.html, profile.html
├── vehicles/                  # Catálogo de vehículos
│   ├── models.py             # Brand, Vehicle, VehicleImage
│   ├── views.py              # VehicleListView, VehicleDetailView, VehicleCreateView, VehicleUpdateView, VehicleDeleteView
│   ├── forms.py              # VehicleForm, BrandForm
│   ├── urls.py
│   └── templates/vehicles/   # list.html, detail.html, form.html, confirm_delete.html
├── static/                    # Archivos estáticos (CSS, JS, imágenes)
├── templates/                 # Plantillas base
│   ├── base.html
│   ├── includes/pagination.html
│   └── emails/               # Plantillas de correos electrónicos
├── media/                     # Archivos subidos por usuarios
├── staticfiles/               # Archivos estáticos recolectados (producción)
├── docker/                    # Archivos de Docker (Dockerfile, docker-compose.yml)
├── .env                       # Variables de entorno
├── .gitignore
├── manage.py
├── requirements.txt
└── README.md
```

---

## 🚀 Guía de Instalación desde Cero

### 1. Clonar el repositorio
```bash
git clone https://github.com/P3terPl4y/TruckSmarter.git
cd TruckSmarter
```

### 2. Crear y activar entorno virtual
```bash
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows
```

### 3. Instalar dependencias
```bash
pip install -r requirements.txt
```

### 4. Configurar variables de entorno (`.env`)
```env
# Django
DEBUG=True
SECRET_KEY=tu_clave_secreta_generada_aqui
ALLOWED_HOSTS=localhost,127.0.0.1

# Database (PostgreSQL)
DB_NAME=trucksmarter
DB_USER=gowa
DB_PASSWORD=tu_contraseña
DB_HOST=localhost
DB_PORT=5432

# Email (desarrollo)
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
DEFAULT_FROM_EMAIL=TruckSmarter <noreply@trucksmarter.com>

# Producción (opcional)
# EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
# EMAIL_HOST=smtp.gmail.com
# EMAIL_PORT=587
# EMAIL_USE_TLS=True
# EMAIL_HOST_USER=tu_correo@gmail.com
# EMAIL_HOST_PASSWORD=tu_contraseña_de_aplicacion

# Seguridad (producción)
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
SECURE_PROXY_SSL_HEADER=HTTP_X_FORWARDED_PROTO,https
CSRF_TRUSTED_ORIGINS=https://tudominio.com
```

### 5. Crear base de datos (PostgreSQL)
```bash
sudo -u postgres psql
```
```sql
CREATE DATABASE trucksmarter OWNER gowa;
GRANT ALL PRIVILEGES ON DATABASE trucksmarter TO gowa;
\q
```

### 6. Aplicar migraciones
```bash
python manage.py makemigrations
python manage.py migrate
```

### 7. Crear superusuario
```bash
python manage.py createsuperuser
```

### 8. Recolectar archivos estáticos
```bash
python manage.py collectstatic --noinput
```

### 9. Ejecutar servidor de desarrollo
```bash
python manage.py runserver
```

---

## 🏗️ Arquitectura y Aplicaciones

| Aplicación | Propósito | Modelos principales |
|------------|-----------|---------------------|
| **`vehicles`** | Catálogo de vehículos, CRUD, filtros, paginación | Brand, Vehicle, VehicleImage |
| **`users`** | Gestión de usuarios, autenticación, perfiles, roles, verificación de email | User, Profile, EmailVerification |
| **`sales`** | Sistema de ofertas (negociación), historial de reservas (legado) | Sale |
| **`dashboard`** | Panel de administración personalizado (usuarios, marcas, ofertas) | - |
| **`core`** | Mixins reutilizables (permisos) | - |
| **`analytics`** | Registro y visualización de métricas de vehículos | VehicleView |

---

## 🔒 Pruebas de Seguridad Realizadas

| Prueba | Herramienta | Resultado |
|--------|-------------|-----------|
| **CSRF** | `curl` sin token / formularios | ✅ Protegido (todos los POST sin token → 403) |
| **XSS** | Inyección manual (`<script>`) | ✅ Escapado correcto (no se ejecuta) |
| **SQL Injection** | `curl` con parámetros maliciosos (`?q=' OR 1=1 --`) | ✅ ORM de Django protege |
| **Rate Limiting** | `curl` con 6 intentos fallidos en 1 minuto | ✅ Funciona (429 después de 5 intentos) |
| **Validación de email** | Registro con `test@dominioinvalido.xyz` | ✅ Bloquea dominios sin MX |
| **Headers de seguridad** | `curl -I` | ✅ X-Frame-Options: DENY, X-Content-Type-Options: nosniff, Referrer-Policy: same-origin |
| **Clickjacking** | `<iframe>` en página externa | ✅ Prevenido (X-Frame-Options: DENY) |
| **Subida de archivos** | Subir `.exe`, `.php` en `main_image` | ✅ Django ImageField rechaza no-imágenes |
| **Autorización** | Acceso a `/dashboard/` con usuario normal | ✅ 403 Forbidden |
| **Sesiones** | Cookies `sessionid` | ✅ HttpOnly, Secure en producción |

---

## 🔐 Configuraciones Seguras para Producción

### `settings.py` (bloque de seguridad)
```python
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_HSTS_SECONDS = 31536000  # 1 año
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    X_FRAME_OPTIONS = 'DENY'
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
```

### Variables de entorno para producción
```env
DEBUG=False
ALLOWED_HOSTS=tu-dominio.com,www.tu-dominio.com
SECRET_KEY=<clave_segura_generada>
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=tu_correo@gmail.com
EMAIL_HOST_PASSWORD=tu_contraseña_de_aplicacion
DEFAULT_FROM_EMAIL=TruckSmarter <tu_correo@gmail.com>
CSRF_TRUSTED_ORIGINS=https://tu-dominio.com
```

### Servidor web (Nginx)
```nginx
server {
    listen 443 ssl;
    server_name tu-dominio.com;
    
    ssl_certificate /etc/letsencrypt/live/tu-dominio.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/tu-dominio.com/privkey.pem;
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    location /static/ {
        alias /ruta/a/staticfiles/;
        expires max;
    }
    
    location /media/ {
        alias /ruta/a/media/;
        expires 1y;
    }
}
```

---

## 🧠 Decisiones de Diseño y Arquitectura

| Decisión | Razón | Alternativas |
|----------|-------|--------------|
| **Uso de CBV (Class-Based Views)** | Reutilización de código, claridad, mixins | Vistas basadas en funciones (menos escalables) |
| **Mixins de permisos** (`AdminRequiredMixin`, `SellerRequiredMixin`) | Centralización de la lógica de autorización | Decoradores `@user_passes_test` (menos reutilizables) |
| **Soft delete** en vehículos (`is_active=False`) | Mantener historial y auditoría | Eliminación física (pérdida de datos) |
| **Validación de email con `dnspython`** | Bloquear dominios inválidos (spam, correos falsos) | Validación solo de formato (menos seguro) |
| **Rate limiting con `django-ratelimit`** | Proteger contra ataques de fuerza bruta | Implementación manual (más compleja) |
| **Modo oscuro** | Mejor experiencia de usuario, tendencia moderna | Solo modo claro (menos opciones) |
| **Diseño Ferrari‑inspired** | Identidad de marca, lujo, exclusividad | Diseño genérico (menos diferenciación) |
| **Separación de `users` y `profiles`** | Extensibilidad, separación de responsabilidades | Campos extra en User (más acoplado) |
| **Panel de administración personalizado** | Control total sobre la interfaz y lógica | Django admin (menos flexible, más complejo para usuarios) |

---

## ✅ Lo que está Bien Hecho

- ✅ **Seguridad robusta:** CSRF, XSS, SQLi, rate limiting, headers de seguridad.
- ✅ **Arquitectura limpia:** Separación de aplicaciones, responsabilidades claras.
- ✅ **Documentación exhaustiva** en este documento y en el README.
- ✅ **Pruebas automatizadas:** 43 pruebas, todas pasando.
- ✅ **Modo oscuro** con persistencia en localStorage.
- ✅ **Diseño moderno** y responsivo (Ferrari‑inspired).
- ✅ **Validación de email** con verificación de MX (dominios válidos).
- ✅ **Soft delete** para preservar datos históricos.
- ✅ **Sistema de ofertas** completo con notificaciones por email.
- ✅ **Dashboard personalizado** para administradores.
- ✅ **Manejo de archivos estáticos y multimedia** con whitenoise y Nginx.
- ✅ **Gestión de roles:** Admin, Seller, Customer con permisos bien definidos.

---

## 🔄 Áreas de Mejora y Recomendaciones

| Área | Problema | Recomendación |
|------|----------|---------------|
| **Pruebas** | Cobertura moderada (~70%) | Aumentar cobertura a >90% con pruebas de integración y aceptación. |
| **Documentación** | Buen README pero falta documentación de API | Agregar Swagger/DRF para documentar endpoints. |
| **Rendimiento** | No se usan índices en la base de datos | Agregar índices en campos de búsqueda (`brand`, `price`, `created_at`). |
| **Caché** | Redis configurado pero no se usa para vistas frecuentes | Cachear vistas de catálogo y detalle para reducir carga. |
| **Asincronía** | Envío de emails síncrono | Usar Celery + Redis para tareas asíncronas (emails, notificaciones). |
| **API REST** | No hay API para integración con frontend | Implementar Django REST Framework con autenticación JWT. |
| **CI/CD** | Sin integración continua | Configurar GitHub Actions para ejecutar pruebas y deploy automático. |
| **Monitoreo** | Sin logs estructurados ni métricas | Implementar ELK Stack o Sentry para monitoreo en tiempo real. |
| **Seguridad adicional** | Sin 2FA ni verificación de dispositivos | Agregar autenticación de dos factores (2FA) para admins. |
| **Escalabilidad** | Monolítico | Considerar microservicios para aplicaciones críticas (autenticación, catálogo). |

---

## 📋 Comandos Útiles

### Gestión del proyecto
```bash
# Activar entorno virtual
source venv/bin/activate

# Ejecutar servidor de desarrollo
python manage.py runserver 4000

# Aplicar migraciones
python manage.py makemigrations
python manage.py migrate

# Recolectar archivos estáticos
python manage.py collectstatic --noinput

# Crear superusuario
python manage.py createsuperuser

# Ejecutar pruebas
python manage.py test

# Ver estado de migraciones
python manage.py showmigrations

# Shell interactiva de Django
python manage.py shell
```

### Gestión de base de datos (PostgreSQL)
```bash
# Conectar a psql
python manage.py dbshell

# Resetear base de datos (desde psql)
DROP SCHEMA public CASCADE;
CREATE SCHEMA public;
GRANT ALL ON SCHEMA public TO gowa;
\q
```

### Despliegue con Gunicorn y Nginx
```bash
# Iniciar Gunicorn
gunicorn --workers 3 --bind 127.0.0.1:8000 config.wsgi:application

# Reiniciar Nginx
sudo systemctl reload nginx

# Ver logs de Gunicorn
sudo journalctl -u trucksmarter -f

# Ver logs de Nginx
sudo tail -f /var/log/nginx/error.log
```

### Generación de `requirements.txt`
```bash
pip freeze > requirements.txt
```

---

## ⚠️ Errores Frecuentes y Soluciones

| Error | Causa | Solución |
|-------|-------|----------|
| `ModuleNotFoundError: No module named 'django'` | Entorno virtual no activado | `source venv/bin/activate` |
| `relation "users_user" does not exist` | Migraciones no aplicadas | `python manage.py migrate` |
| `CSRF cookie not set` | Petición POST sin token CSRF | Asegurar `{% csrf_token %}` en formularios |
| `dns.resolver.LifetimeTimeout` | Validación DNS falla en desarrollo | Usar validador sin DNS en `DEBUG=True` |
| `Connection reset by peer` | Error de conexión SMTP | Usar `console.EmailBackend` en desarrollo |
| `NoReverseMatch: 'purchase' not found` | URL obsoleta (reserva vs oferta) | Usar `sales:make_offer` en lugar de `sales:purchase` |
| `Vehicle matching query does not exist` | Soft delete no implementado | Usar `is_active=False` en `VehicleDeleteView` |
| `PermissionDenied` en `/create/` | Usuario sin rol `seller` o `admin` | Asignar rol correcto en el admin |

---

## 🗺️ Roadmap y Próximos Pasos

### ✅ Completado
- ✅ Sistema de autenticación con roles.
- ✅ Catálogo de vehículos con filtros y paginación.
- ✅ Sistema de ofertas (negociación).
- ✅ Dashboard de administración.
- ✅ Pruebas de seguridad.
- ✅ Modo oscuro y diseño Ferrari‑inspired.
- ✅ Validación de email con DNS.
- ✅ Soft delete de vehículos.
- ✅ Notificaciones por email para ofertas.

### 🚧 En progreso / Próximo
- 🔄 Integración con pasarela de pago (Stripe / MercadoPago).
- 🔄 Sistema de reseñas y calificaciones de vehículos.
- 🔄 Notificaciones en tiempo real (WebSockets).
- 🔄 API REST con Django REST Framework.
- 🔄 Pruebas de carga con Locust/k6.

### 💡 Futuro
- 📱 Aplicación móvil (React Native / Flutter).
- 🌐 Internacionalización (i18n).
- 🤖 Recomendación de vehículos basada en IA.
- 🧾 Generación de facturas en PDF.

---

## 📝 Notas Finales

TruckSmarter ha evolucionado de un simple catálogo a una plataforma completa de concesionario con un sistema de negociación robusto, seguridad de nivel producción y una experiencia de usuario premium. El proyecto está actualmente en fase de estabilización, con todas las pruebas pasando y listo para despliegue en producción.

**¡Gracias por acompañar este viaje de desarrollo!** 🚀
