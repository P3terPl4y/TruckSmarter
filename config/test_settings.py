"""Isolated tests; opt into PostgreSQL/Redis with TEST_DATABASE_URL/TEST_REDIS_URL."""

import os
import tempfile
import atexit
import shutil

os.environ.setdefault("SECRET_KEY", "test-only-key-never-use-in-production")
os.environ.setdefault("DB_NAME", "trucksmarter_test")
os.environ.setdefault("DB_USER", "peter")
os.environ.setdefault("DB_PASSWORD", "")

from .settings import *  # noqa: E402,F403

DEBUG = False
ALLOWED_HOSTS = ["testserver", "localhost", "127.0.0.1"]
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}
MEDIA_ROOT = tempfile.mkdtemp(prefix="trucksmarter-tests-")
atexit.register(shutil.rmtree, MEDIA_ROOT, ignore_errors=True)
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}
if os.environ.get("TEST_DATABASE_URL"):
    DATABASES = {"default": env.db("TEST_DATABASE_URL")}
CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
EMAIL_VALIDATE_DNS = False
RATELIMIT_ENABLE = False
SILENCED_SYSTEM_CHECKS = ["django_ratelimit.E003", "django_ratelimit.W001"]
if os.environ.get("TEST_REDIS_URL"):
    CACHES = {
        "default": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": os.environ["TEST_REDIS_URL"],
            "KEY_PREFIX": "trucksmarter-tests",
            "OPTIONS": {"CLIENT_CLASS": "django_redis.client.DefaultClient"},
        }
    }
    RATELIMIT_ENABLE = True
    SILENCED_SYSTEM_CHECKS = []
REQUEST_GUARD_ENABLED = False
JWT_SIGNING_KEY = "test-only-jwt-signing-key-at-least-32-bytes"
