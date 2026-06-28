from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = "nexo-dev-secret-key-cambiar-en-produccion"

DEBUG = True

ALLOWED_HOSTS = ["localhost", "127.0.0.1", "testserver"]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

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
    },
]

WSGI_APPLICATION = "nexo_backend.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

LANGUAGE_CODE = "es-ve"
TIME_ZONE = "America/Caracas"
USE_I18N = True
USE_TZ = True
STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

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
