import os
import environ
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

if os.name == "nt":
    QGIS_BIN_PATH = os.environ.get("QGIS_BIN_PATH")

    if QGIS_BIN_PATH and os.path.exists(QGIS_BIN_PATH):
        os.add_dll_directory(QGIS_BIN_PATH)

    GDAL_LIBRARY_PATH = os.environ.get("GDAL_LIBRARY_PATH")
    GEOS_LIBRARY_PATH = os.environ.get("GEOS_LIBRARY_PATH")
    
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
import os


if NEXO_DB_ENGINE == "spatialite":
    DATABASES = {
        "default": {
            "ENGINE": "django.contrib.gis.db.backends.spatialite",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }
    SPATIALITE_LIBRARY_PATH = env("SPATIALITE_LIBRARY_PATH", default="")
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
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Redirección posterior al login/logout de la API navegable de DRF.
LOGIN_REDIRECT_URL = "/api/v1/"
LOGOUT_REDIRECT_URL = "/api-auth/login/"

# --- Almacenamiento de fotos de entrega ---
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

# Presupuesto y límites de fotos (§2). El cliente comprime antes de subir; el
# servidor re-comprime para garantizar el objetivo.
FOTO_OBJETIVO_BYTES = 100_000          # foto de entrega < 100 KB
FOTO_MAX_SUBIDA_BYTES = 5 * 1024 * 1024  # rechazo defensivo de subidas enormes

REST_FRAMEWORK = {
    # En campo el cliente offline usa Token (cabecera Authorization: Token <key>);
    # Session habilita la API navegable y el admin durante desarrollo.
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.TokenAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    # Por defecto, ninguna ruta es anónima: cada vista decide su política de rol.
    # PermisoPorRol = lectura para cualquier autenticado, escritura solo admin.
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

# --- KoBoToolbox ---
KOBO_API_URL = env("KOBO_API_URL", default="https://kf.kobotoolbox.org/api/v2").rstrip("/")
KOBO_TOKEN = env("KOBO_TOKEN", default="")
KOBO_ASSET_NECESIDADES = env("KOBO_ASSET_NECESIDADES", default="")
KOBO_ASSET_DONACIONES = env("KOBO_ASSET_DONACIONES", default="")
KOBO_WEBHOOK_TOKEN = env("KOBO_WEBHOOK_TOKEN", default="")
KOBO_PULL_LIMIT = env.int("KOBO_PULL_LIMIT", default=500)

SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=not DEBUG)
SESSION_COOKIE_SECURE = env.bool("SESSION_COOKIE_SECURE", default=not DEBUG)
CSRF_COOKIE_SECURE = env.bool("CSRF_COOKIE_SECURE", default=not DEBUG)

SECURE_HSTS_SECONDS = env.int("SECURE_HSTS_SECONDS", default=0 if DEBUG else 31536000)
SECURE_HSTS_INCLUDE_SUBDOMAINS = env.bool(
    "SECURE_HSTS_INCLUDE_SUBDOMAINS",
    default=False,
)
SECURE_HSTS_PRELOAD = env.bool("SECURE_HSTS_PRELOAD", default=False)