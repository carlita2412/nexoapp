# Nexo — Backend de coordinación médica

Backend Django + Django REST Framework para coordinar **necesidades ↔ donaciones médicas** entre organizaciones, centros de salud y equipos de campo.

El objetivo del sistema es reducir la descoordinación en la respuesta humanitaria: registrar necesidades, registrar donaciones, sugerir matches compatibles, reclamar necesidades de forma controlada, confirmar entregas y mantener sincronización idempotente para clientes offline.

## Estado actual del repositorio

Este repositorio contiene el backend operativo de la API `v1` de Nexo. Actualmente incluye:

- Modelo de datos principal: organizaciones, centros de salud, catálogos, necesidades, donaciones, asignaciones, envíos, fotos, usuarios, eventos sincronizados y cursor KoBo.
- API REST versionada en `/api/v1/`.
- Autenticación por token para clientes de campo/PWA.
- RBAC mínimo por rol antes de abrir acceso a varias organizaciones.
- Endpoint de sincronización offline-first con `idempotency_key`.
- Pull por deltas para clientes offline.
- Motor de matching entre necesidades y donaciones compatibles.
- Claim de necesidades con control transaccional e idempotencia.
- Ingesta incremental desde KoBoToolbox por comando de Django.
- Webhook alternativo para KoBoToolbox.
- Endpoint multipart para fotos de confirmación de entrega.
- Compresión asíncrona de fotos con `django-q2`.
- Configuración productiva por `.env` para PostgreSQL/PostGIS, CORS/CSRF, media persistente, staticfiles, Gunicorn y Caddy.
- Pruebas de idempotencia, matching, delta sync, claim, RBAC y fotos.

## Stack actual

- Python 3.x
- Django 5.x
- Django REST Framework
- PostgreSQL/PostGIS en producción
- Token Authentication de DRF
- django-filter
- django-cors-headers
- django-q2
- Pillow
- qrcode
- gunicorn
- whitenoise
- pytest + pytest-django
- ruff + black

> Producción usa `django.contrib.gis.db.backends.postgis`. Para pruebas locales/CI puede usarse `NEXO_DB_ENGINE=spatialite` o `NEXO_DB_ENGINE=sqlite` cuando aplique.

## Reglas implementadas

- Dominio y endpoints en español.
- UUID como PK en los modelos principales.
- Idempotencia obligatoria mediante `idempotency_key` para sync, claim y fotos.
- API sensible cerrada por autenticación, salvo healthcheck y webhook KoBo protegido opcionalmente por token.
- Permisos mínimos por rol.
- Matching sin sugerir equipos incompatibles o que requieren reparación.
- Fotos de entrega comprimidas a presupuesto bajo de datos y original descartado tras procesamiento.
- Sin captura de pacientes ni PII clínica innecesaria.
- Configuración sensible fuera del código mediante `.env`.

## Instalación local

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py runserver
```

En Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
python manage.py migrate
python manage.py runserver
```

API local:

```text
http://127.0.0.1:8000/api/v1/
```

Admin Django:

```text
http://127.0.0.1:8000/admin/
```

## Variables de entorno

El archivo `.env.example` define las variables necesarias para desarrollo y producción:

```env
SECRET_KEY=change-me
DEBUG=false
ALLOWED_HOSTS=nexo.ejemplo.org,localhost,127.0.0.1,testserver
CSRF_TRUSTED_ORIGINS=https://nexo.ejemplo.org
CORS_ALLOWED_ORIGINS=https://nexo.ejemplo.org
SECURE_SSL_REDIRECT=true

NEXO_DB_ENGINE=postgis
DB_NAME=nexo
DB_USER=nexo
DB_PASSWORD=change-me
DB_HOST=127.0.0.1
DB_PORT=5432

STATIC_ROOT=/var/www/nexo/staticfiles
MEDIA_ROOT=/var/www/nexo/media

KOBO_API_URL=https://kf.kobotoolbox.org/api/v2
KOBO_TOKEN=
KOBO_ASSET_NECESIDADES=
KOBO_ASSET_DONACIONES=
KOBO_WEBHOOK_TOKEN=
KOBO_PULL_LIMIT=500
```

Variables relevantes:

| Variable | Uso |
|---|---|
| `SECRET_KEY` | Clave privada de Django. Obligatoria y nunca debe versionarse con valor real. |
| `DEBUG` | Debe ser `false` en producción. |
| `ALLOWED_HOSTS` | Dominios/IP autorizados para servir la API. |
| `CSRF_TRUSTED_ORIGINS` | Orígenes HTTPS confiables para CSRF. |
| `CORS_ALLOWED_ORIGINS` | Orígenes permitidos para la PWA/portal. |
| `SECURE_SSL_REDIRECT` | Fuerza HTTPS cuando el reverse proxy ya está activo. |
| `NEXO_DB_ENGINE` | `postgis` en producción; `spatialite`/`sqlite` para pruebas locales controladas. |
| `DB_NAME`/`DB_USER`/`DB_PASSWORD`/`DB_HOST`/`DB_PORT` | Credenciales PostgreSQL/PostGIS. |
| `STATIC_ROOT` | Carpeta persistente para `collectstatic`. |
| `MEDIA_ROOT` | Carpeta persistente para fotos comprimidas y media. |
| `KOBO_API_URL` | Base URL de la API de KoBoToolbox. |
| `KOBO_TOKEN` | Token de API KoBo para pull incremental. |
| `KOBO_ASSET_NECESIDADES` | UID del formulario KoBo de necesidades. |
| `KOBO_ASSET_DONACIONES` | UID del formulario KoBo de donaciones. |
| `KOBO_WEBHOOK_TOKEN` | Token opcional para autorizar webhooks KoBo. |
| `KOBO_PULL_LIMIT` | Límite de submissions por consulta KoBo. |

## Despliegue productivo mínimo

La guía operativa vive en [`docs/produccion.md`](docs/produccion.md). Incluye:

- creación de `.env` real,
- instalación PostgreSQL + PostGIS,
- migraciones,
- `collectstatic`,
- `python manage.py check --deploy`,
- servicio systemd para Gunicorn,
- Caddy como HTTPS/reverse proxy,
- verificación de `/api/v1/salud/`.

Plantillas incluidas:

- [`deploy/nexo.service.example`](deploy/nexo.service.example)
- [`deploy/Caddyfile.example`](deploy/Caddyfile.example)

## Seguridad y roles

La API aplica RBAC con cuatro roles:

- `admin`
- `coordinador`
- `campo`
- `lectura`

El endpoint `/api/v1/salud/` es público. Las demás rutas operativas requieren autenticación, salvo el webhook KoBo, que acepta llamadas externas y puede protegerse con `KOBO_WEBHOOK_TOKEN`.

| Acción | admin | coordinador | campo | lectura |
|---|---:|---:|---:|---:|
| Crear necesidades | Sí | Sí | Sí | No |
| Crear donaciones | Sí | Sí | Sí | No |
| Reclamar necesidad | Sí | Sí | Limitado a su organización | No |
| Ver matching | Sí | Sí | Sí | Sí |
| Confirmar entrega / crear envío | Sí | Sí | Sí | No |
| Subir foto de entrega | Sí | Sí | Sí | No |
| Administrar organizaciones | Sí | No | No | No |
| Administrar catálogos | Sí | No | No | No |
| Pull sync | Sí | Sí | Sí | Sí |
| Push sync | Sí | Sí | Sí | No |

## Autenticación por token

Obtener token:

```http
POST /api/v1/auth/token/
Content-Type: application/json

{
  "username": "usuario",
  "password": "clave"
}
```

Respuesta esperada:

```json
{
  "token": "...",
  "usuario": "usuario",
  "rol": "campo",
  "organizacion": "uuid-de-organizacion"
}
```

Usar token:

```http
Authorization: Token <token>
```

## Endpoints principales

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/api/v1/salud/` | Healthcheck público. |
| `POST` | `/api/v1/auth/token/` | Login por token. |
| `GET/POST` | `/api/v1/organizaciones/` | Organizaciones de la alianza. Escritura solo `admin`. |
| `GET/POST` | `/api/v1/catalogos/` | Catálogo controlado de ítems. Escritura solo `admin`. |
| `GET/POST` | `/api/v1/centros-salud/` | Centros de salud y capacidades operativas. |
| `GET/POST` | `/api/v1/necesidades/` | Necesidades médicas. |
| `GET` | `/api/v1/necesidades/<uuid>/candidatos/` | Donaciones compatibles para una necesidad. |
| `POST` | `/api/v1/necesidades/<uuid>/claim/` | Reclamar una necesidad. |
| `GET/POST` | `/api/v1/donaciones/` | Donaciones disponibles. |
| `GET/POST` | `/api/v1/asignaciones/` | Asignaciones. Escritura manual solo coordinación/admin. |
| `GET/POST` | `/api/v1/envios/` | Envíos y confirmación logística. |
| `GET/POST` | `/api/v1/fotos/` | Fotos multipart de confirmación. |
| `GET/POST` | `/api/v1/sync/` | Pull por deltas y push de outbox. |
| `POST` | `/api/v1/kobo/webhook/<necesidad|donacion>/` | Webhook KoBo. |

## Sincronización offline-first

### Push de outbox

```http
POST /api/v1/sync/
Authorization: Token <token>
Content-Type: application/json

{
  "eventos": [
    {
      "idempotency_key": "uuid-evento",
      "client_timestamp": "2026-06-28T10:00:00Z",
      "entity": "necesidad",
      "payload": {
        "id": "uuid-entidad",
        "centro": "uuid-centro",
        "item": "uuid-catalogo",
        "cantidad_solicitada": 5,
        "nivel_triage": "2_urgente",
        "reportada_por": "uuid-organizacion"
      }
    }
  ]
}
```

Estados posibles por evento:

- `ok`: procesado.
- `duplicado`: el `idempotency_key` ya fue procesado.
- `conflicto`: entidad no soportada, payload inválido, falta de `id`, versión vieja, etc.

Entidades soportadas por sync:

- `organizacion`
- `catalogo`
- `centro_salud`
- `necesidad`
- `donacion`
- `asignacion`
- `envio`

### Pull por deltas

```http
GET /api/v1/sync/?desde=<cursor>
Authorization: Token <token>
```

Devuelve solo registros con `updated_at` posterior al cursor. Sin `desde`, devuelve el estado sincronizable completo.

## Matching

El matching devuelve donaciones compatibles para una necesidad. Valida:

- La necesidad debe estar `abierta` o `parcial`.
- La donación debe estar `disponible`.
- El ítem de la donación debe coincidir con el ítem solicitado.
- La donación no debe requerir reparación.
- El centro debe cumplir los requisitos operativos de la necesidad: electricidad, oxígeno, agua y personal técnico entrenado.

Endpoint:

```http
GET /api/v1/necesidades/<uuid>/candidatos/
Authorization: Token <token>
```

## Claim de necesidades

Endpoint:

```http
POST /api/v1/necesidades/<uuid>/claim/
Authorization: Token <token>
Content-Type: application/json

{
  "donacion_id": "uuid-donacion",
  "cantidad_asignada": 1,
  "organizacion_responsable_id": "uuid-organizacion",
  "idempotency_key": "uuid-opcional"
}
```

Reglas actuales:

- Usa transacción y `select_for_update` sobre necesidad y donación.
- No permite reclamar necesidades cerradas o cubiertas.
- No permite reclamar donaciones no disponibles.
- No permite sobre-asignar más de lo pendiente.
- No permite asignar más de la cantidad disponible en la donación.
- Si el claim cubre todo, la necesidad pasa a `cubierta`.
- Si cubre parcialmente, pasa a `parcial`.
- Si la donación se agota, pasa a `asignada`.
- Con el mismo `idempotency_key`, el reintento devuelve la misma asignación sin duplicar cobertura.
- `campo` solo puede reclamar para su propia organización.

## Fotos de confirmación de entrega

Subida multipart:

```http
POST /api/v1/fotos/
Authorization: Token <token>
Content-Type: multipart/form-data

idempotency_key=<uuid>
envio=<uuid-envio>
imagen=<archivo>
```

Comportamiento:

- Devuelve `202 Accepted` al recibir una foto nueva.
- Devuelve `200 OK` si se reintenta con el mismo `idempotency_key`.
- Rechaza subidas mayores a `FOTO_MAX_SUBIDA_BYTES`.
- Encola procesamiento con `django-q2`.
- Comprime la imagen a `FOTO_OBJETIVO_BYTES`.
- Guarda la imagen comprimida.
- Actualiza `Envio.foto_confirmacion_ref`.
- Borra el archivo original tras comprimirlo.

Para procesar tareas en producción/desarrollo:

```bash
python manage.py qcluster
```

## KoBoToolbox

### Pull incremental

```bash
python manage.py ingestar_kobo
python manage.py ingestar_kobo --tipo necesidad
python manage.py ingestar_kobo --tipo donacion
```

El servicio:

- Consulta KoBo usando `KOBO_TOKEN`.
- Lee los assets definidos en `KOBO_ASSET_NECESIDADES` y `KOBO_ASSET_DONACIONES`.
- Usa `KoboCursor` para guardar el último `_submission_time` y `_uuid`.
- Mapea cada submission a un evento compatible con `/sync`.
- Reutiliza la idempotencia del motor sync.

### Webhook KoBo

Configura KoBo REST Service para enviar submissions a:

```text
POST /api/v1/kobo/webhook/necesidad/
POST /api/v1/kobo/webhook/donacion/
```

Si `KOBO_WEBHOOK_TOKEN` tiene valor, el request debe incluirlo con `X-Kobo-Token: <token>` o `?token=<token>`.

## Modelos principales

| Modelo | Uso |
|---|---|
| `Organizacion` | Participantes de la alianza. |
| `Catalogo` | Vocabulario controlado de ítems. |
| `CentroSalud` | Centros receptores y sus capacidades operativas. |
| `Necesidad` | Solicitudes de equipos/insumos con triage y requisitos. |
| `Donacion` | Recursos disponibles para asignar. |
| `Asignacion` | Resultado del claim entre necesidad y donación. |
| `Envio` | Logística y confirmación de entrega. |
| `Foto` | Evidencia comprimida de entrega. |
| `EventoSincronizado` | Registro de `idempotency_key` procesados. |
| `RegistroAuditoria` | Base para auditoría. |
| `KoboCursor` | Cursor incremental por formulario KoBo. |
| `Usuario` | Usuario autenticado con rol y organización. |

## Pruebas

Ejecutar toda la suite:

```bash
pytest -q
```

Ejecutar grupos específicos:

```bash
pytest coordinacion/tests/test_permisos.py -q
pytest coordinacion/tests/test_idempotencia.py -q
pytest coordinacion/tests/test_arbitraje_claim.py -q
pytest coordinacion/tests/test_sync_delta.py -q
pytest coordinacion/tests/test_fotos.py -q
```

Coberturas funcionales existentes:

- RBAC mínimo por rol.
- Healthcheck público y rutas sensibles autenticadas.
- Login por token.
- Idempotencia de `/sync`.
- Conflictos por versión vieja.
- Pull por delta.
- Matching por compatibilidad operativa.
- Claim parcial, total, duplicado y no sobre-asignado.
- Subida de fotos, compresión, idempotencia y permisos.

## Comandos útiles

```bash
# Migraciones
python manage.py makemigrations
python manage.py migrate

# Staticfiles
python manage.py collectstatic --noinput

# Validación de despliegue
python manage.py check --deploy

# Servidor local
python manage.py runserver

# Worker de tareas async
python manage.py qcluster

# Ingesta KoBo
python manage.py ingestar_kobo
python manage.py ingestar_kobo --tipo necesidad
python manage.py ingestar_kobo --tipo donacion

# Tests
pytest -q
```

## Pendientes recomendados antes del despliegue público

- Cargar seed/fixtures iniciales de organizaciones, centros, catálogos y usuarios.
- Validar formularios KoBo reales contra los mapeadores actuales.
- Agregar auditoría efectiva en acciones críticas.
- Reemplazar dominios de ejemplo por el dominio final en `.env`, Caddy, CSRF y CORS.
