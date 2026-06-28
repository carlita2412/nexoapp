# Despliegue productivo mínimo

Este documento cierra la configuración mínima antes de abrir la API de Nexo a varias organizaciones.

## 1. Variables obligatorias

Crear `/opt/nexoapp/.env` desde `.env.example` y reemplazar los valores de ejemplo:

```env
SECRET_KEY=<clave-larga-generada-en-servidor>
DEBUG=false
ALLOWED_HOSTS=nexo.tu-dominio.org
CSRF_TRUSTED_ORIGINS=https://nexo.tu-dominio.org
CORS_ALLOWED_ORIGINS=https://nexo.tu-dominio.org
SECURE_SSL_REDIRECT=true

NEXO_DB_ENGINE=postgis
DB_NAME=nexo
DB_USER=nexo
DB_PASSWORD=<clave-bd>
DB_HOST=127.0.0.1
DB_PORT=5432

STATIC_ROOT=/var/www/nexo/staticfiles
MEDIA_ROOT=/var/www/nexo/media
```

`SECRET_KEY` no debe versionarse. Generar una clave real con:

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

## 2. PostgreSQL + PostGIS

```bash
sudo apt update
sudo apt install -y postgresql postgresql-contrib postgis gdal-bin libgdal-dev libgeos-dev libproj-dev
sudo -u postgres createuser nexo
sudo -u postgres createdb nexo -O nexo
sudo -u postgres psql -d nexo -c "CREATE EXTENSION IF NOT EXISTS postgis;"
sudo -u postgres psql -c "ALTER USER nexo WITH PASSWORD '<clave-bd>';"
```

## 3. Instalar aplicación

```bash
cd /opt/nexoapp
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py check --deploy
```

Crear carpetas persistentes:

```bash
sudo mkdir -p /var/www/nexo/staticfiles /var/www/nexo/media
sudo chown -R nexo:www-data /var/www/nexo /opt/nexoapp
```

## 4. Gunicorn con systemd

Copiar `deploy/nexo.service.example` a `/etc/systemd/system/nexo.service`, ajustar `WorkingDirectory`, usuario y rutas si cambian, luego:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now nexo
sudo systemctl status nexo
```

## 5. HTTPS y reverse proxy con Caddy

Copiar `deploy/Caddyfile.example` a `/etc/caddy/Caddyfile`, reemplazar `nexo.ejemplo.org` por el dominio final, luego:

```bash
sudo systemctl reload caddy
```

Caddy termina HTTPS, sirve `/static/` y `/media/` desde almacenamiento persistente, y reenvía la API a Gunicorn en `127.0.0.1:8000`.

## 6. Verificación antes de compartir acceso

```bash
curl -I https://nexo.tu-dominio.org/api/v1/salud/
python manage.py check --deploy
python manage.py migrate --check
```

La API no debe abrirse públicamente si `DEBUG=true`, si `ALLOWED_HOSTS` contiene solo localhost/testserver, si falta PostGIS, o si `CSRF_TRUSTED_ORIGINS`/`CORS_ALLOWED_ORIGINS` no apuntan al dominio real.
