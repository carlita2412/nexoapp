import os
from pathlib import Path

import environ
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def _agregar_dll_dir_windows(ruta: str | None) -> None:
    if os.name != "nt" or not ruta:
        return

    ruta_path = Path(ruta)
    if ruta_path.is_file():
        ruta_path = ruta_path.parent

    if ruta_path.exists():
        os.add_dll_directory(str(ruta_path))


if os.name == "nt":
    QGIS_BIN_PATH = os.environ.get("QGIS_BIN_PATH")
    GDAL_LIBRARY_PATH = os.environ.get("GDAL_LIBRARY_PATH")
    GEOS_LIBRARY_PATH = os.environ.get("GEOS_LIBRARY_PATH")

    _agregar_dll_dir_windows(QGIS_BIN_PATH)
    _agregar_dll_dir_windows(GDAL_LIBRARY_PATH)
    _agregar_dll_dir_windows(GEOS_LIBRARY_PATH)

env = environ.Env(
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, []),
    CSRF_TRUSTED_ORIGINS=(list, []),
    CORS_ALLOWED_ORIGINS=(list, []),
    DB_NAME=(str, "nexo"),
    DB_USER=(str, "nexo"),
    DB_PASSWORD=(str, ""),
    DB_HOST=(str, "localhost"),
    DB_PORT=(str, "5432"),
    NEXO_DB_ENGINE=(str, "postgis"),
)
env.read_env(BASE_DIR / ".env")

GDAL_LIBRARY_PATH = env("GDAL_LIBRARY_PATH", default=None)
GEOS_LIBRARY_PATH = env("GEOS_LIBRARY_PATH", default=None)

SECRET_KEY = env("SECRET_KEY")
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env("ALLOWED_HOSTS")
CSRF_TRUSTED_ORIGINS = env("CSRF_TRUSTED_ORIGINS", default=[])
CORS_ALLOWED_ORIGINS = env("CORS_ALLOWED_ORIGINS", default=[])

if DEBUG:
    origenes_desarrollo = [
        "http://localhost:4321",
        "http://127.0.0.1:4321",
    ]
    for origen in origenes_desarrollo:
        if origen not in CORS_ALLOWED_ORIGINS:
            CORS_ALLOWED_ORIGINS.append(origen)
        if origen not in CSRF_TRUSTED_ORIGINS:
            CSRF_TRUSTED_ORIGINS.append(origen)

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=not DEBUG)
SESSION_COOKIE_SECURE = env.bool("SESSION_COOKIE_SECURE", default=not DEBUG)
CSRF_COOKIE_SECURE = env.bool("CSRF_COOKIE_SECURE", default=not DEBUG)

SECURE_HSTS_SECONDS = env.int("SECURE_HSTS_SECONDS", default=0 if DEBUG else 31536000)
SECURE_HSTS_INCLUDE_SUBDOMAINS = env.bool(
    "SECURE_HSTS_INCLUDE_SUBDOMAINS",
    default=False,
)
SECURE_HSTS_PRELOAD = env.bool("SECURE_HSTS_PRELOAD", default=False)

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.gis",
    "rest_framework",
    "rest_framework.authtoken",
    "django_filters",
    "corsheaders",
    "django_q",
    "coordinacion",
]

AUTH_USER_MODEL = "coordinacion.Usuario"

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "nexo_backend.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    }
]

WSGI_APPLICATION = "nexo_backend.wsgi.application"

NEXO_DB_ENGINE = env("NEXO_DB_ENGINE").lower()

if NEXO_DB_ENGINE == "spatialite":
    DATABASES = {
        "default": {
            "ENGINE": "django.contrib.gis.db.backends.spatialite",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }
    SPATIALITE_LIBRARY_PATH = env("SPATIALITE_LIBRARY_PATH", default="")
elif NEXO_DB_ENGINE == "sqlite":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.contrib.gis.db.backends.postgis",
            "NAME": env("DB_NAME"),
            "USER": env("DB_USER"),
            "PASSWORD": env("DB_PASSWORD"),
            "HOST": env("DB_HOST"),
            "PORT": env("DB_PORT"),
        }
    }

LANGUAGE_CODE = "es-ve"
TIME_ZONE = "America/Caracas"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = env.path("STATIC_ROOT", default=BASE_DIR / "staticfiles")
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
LOGIN_REDIRECT_URL = "/api/v1/"
LOGOUT_REDIRECT_URL = "/api-auth/login/"

MEDIA_URL = "media/"
MEDIA_ROOT = env.path("MEDIA_ROOT", default=BASE_DIR / "media")

FOTO_OBJETIVO_BYTES = 100_000
FOTO_MAX_SUBIDA_BYTES = 5 * 1024 * 1024

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.TokenAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "coordinacion.permisos.PermisoPorRol",
    ],
}

Q_CLUSTER = {
    "name": "nexo",
    "workers": 2,
    "timeout": 90,
    "retry": 120,
    "queue_limit": 50,
    "bulk": 10,
    "orm": "default",
}

KOBO_API_URL = env("KOBO_API_URL", default="https://kf.kobotoolbox.org/api/v2").rstrip("/")
KOBO_TOKEN = env("KOBO_TOKEN", default="")
KOBO_ASSET_NECESIDADES = env("KOBO_ASSET_NECESIDADES", default="")
KOBO_ASSET_DONACIONES = env("KOBO_ASSET_DONACIONES", default="")
KOBO_WEBHOOK_TOKEN = env("KOBO_WEBHOOK_TOKEN", default="")
KOBO_PULL_LIMIT = env.int("KOBO_PULL_LIMIT", default=500)
