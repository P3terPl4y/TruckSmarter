# TruckSmarter - Plataforma de Compra y Venta de Vehículos

## 📋 Descripción

TruckSmarter es una plataforma web desarrollada con Django que permite a usuarios publicar, gestionar y comprar vehículos. Incluye un sistema de roles (Cliente, Comerciante, Administrador) y un flujo completo de compra con notificaciones por email.

## 🚀 Tecnologías

- **Backend:** Django 6.1, Python 3.13+
- **Base de datos:** PostgreSQL (producción), SQLite (desarrollo)
- **Frontend:** Bootstrap 5, CSS personalizado, JavaScript vanilla
- **Servidor:** Whitenoise para archivos estáticos
- **Variables de entorno:** django-environ

## ✨ Características

- **Catálogo de vehículos** con paginación y filtros
- **Sistema de roles:** Cliente, Comerciante, Administrador
- **Publicación de vehículos** (solo comerciantes y administradores)
- **Sistema de compras** con transacciones atómicas
- **Notificaciones por email** al comprador y vendedor
- **Panel de perfil** con edición de datos personales
- **Modo oscuro** con persistencia local
- **Diseño responsive** y moderno

## 📦 Requisitos

- Python 3.13 o superior
- PostgreSQL 15+ (o SQLite para desarrollo)
- pip (gestor de paquetes de Python)

## 🔧 Instalación

### 1. Clonar el repositorio

```bash
git clone https://github.com/P3terPl4y/TruckSmarter.git
cd TruckSmarter
