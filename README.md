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
- Seed inicial idempotente de organizaciones, catálogos, centros de salud y usuarios base.
- Pruebas de idempotencia, matching, delta sync, claim, RBAC, fotos y seed inicial.

## Stack actual

- Python 3.x
- Django 5.x
- Django REST Framework
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

> Nota: el `settings.py` actual usa SQLite por defecto para desarrollo local. Para producción pública debe configurarse PostgreSQL/PostGIS antes del despliegue final.

## Reglas implementadas

- Dominio y endpoints en español.
- UUID como PK en los modelos principales.
- Idempotencia obligatoria mediante `idempotency_key` para sync, claim y fotos.
- API sensible cerrada por autenticación, salvo healthcheck y webhook KoBo protegido opcionalmente por token.
- Permisos mínimos por rol.
- Matching sin sugerir equipos incompatibles o que requieren reparación.
- Seed inicial idempotente para operar con catálogos y organizaciones base sin texto libre.
- Fotos de entrega comprimidas a presupuesto bajo de datos y original descartado tras procesamiento.
- Sin captura de pacientes ni PII clínica innecesaria.

## Instalación local

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py seed_inicial --password-inicial 'Cambia-esta-clave-123'
python manage.py runserver
```

En Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
python manage.py migrate
python manage.py seed_inicial --password-inicial "Cambia-esta-clave-123"
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

## Seed inicial / fixtures base

El comando `seed_inicial` carga datos mínimos para que KoBo, matching y usuarios puedan operar sin depender de texto libre ni configuraciones manuales incompletas.

```bash
python manage.py seed_inicial --password-inicial 'Cambia-esta-clave-123'
```

También se puede usar variable de entorno para no dejar la clave en el historial del shell:

```bash
export NEXO_SEED_PASSWORD='Cambia-esta-clave-123'
python manage.py seed_inicial
```

En Windows PowerShell:

```powershell
$env:NEXO_SEED_PASSWORD="Cambia-esta-clave-123"
python manage.py seed_inicial
```

El seed es **idempotente**: se puede ejecutar varias veces sin duplicar registros. Usa UUID estables para organizaciones y centros, y `codigo` único para catálogos.

Datos creados:

- 5 organizaciones base: Digisalud, alianza médica, red de centros, voluntarios de campo y donantes privados.
- 10 catálogos médicos iniciales: oxígeno, monitor de signos vitales, tensiómetro, glucómetro, solución fisiológica, guantes, mascarillas, kit de curas y generador.
- 4 centros de salud iniciales con capacidades operativas: electricidad, agua, oxígeno y personal técnico.
- 4 usuarios base: `nexo_admin`, `nexo_coordinador`, `nexo_campo`, `nexo_lectura`.

Usuarios documentados:

| Usuario | Rol | Uso |
|---|---|---|
| `nexo_admin` | `admin` | Administración de organizaciones, catálogos y operación completa. |
| `nexo_coordinador` | `coordinador` | Coordinación operativa, matching, reclamos y seguimiento. |
| `nexo_campo` | `campo` | Captura y actualización en terreno. |
| `nexo_lectura` | `lectura` | Consulta de datos y matching sin escritura. |

Por seguridad, no hay contraseñas hardcodeadas en el repositorio. Si se ejecuta sin `--password-inicial` ni `NEXO_SEED_PASSWORD`, los usuarios se crean sin contraseña usable. Para asignar o reemplazar la contraseña temporal de usuarios existentes:

```bash
python manage.py seed_inicial --password-inicial 'Nueva-clave-temporal-123' --reset-passwords
```

Después del primer ingreso, cambia las contraseñas temporales desde el admin de Django o con el flujo operativo definido para producción.

Opciones útiles:

```bash
# Cargar solo organizaciones, catálogos y centros, sin usuarios
python manage.py seed_inicial --sin-usuarios

# Reaplicar seed y resetear passwords de usuarios existentes
python manage.py seed_inicial --password-inicial 'Nueva-clave-temporal-123' --reset-passwords
```

## Variables de entorno

El archivo `.env.example` define las variables usadas actualmente:

```env
DEBUG=true
ALLOWED_HOSTS=localhost,127.0.0.1,testserver

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
| `KOBO_API_URL` | Base URL de la API de KoBoToolbox. |
| `KOBO_TOKEN` | Token de API KoBo para pull incremental. |
| `KOBO_ASSET_NECESIDADES` | UID del formulario KoBo de necesidades. |
| `KOBO_ASSET_DONACIONES` | UID del formulario KoBo de donaciones. |
| `KOBO_WEBHOOK_TOKEN` | Token opcional para autorizar webhooks KoBo. |
| `KOBO_PULL_LIMIT` | Límite de submissions por consulta KoBo. |
| `NEXO_SEED_PASSWORD` | Password temporal opcional para usuarios creados por `seed_inicial`. |

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

Si `KOBO_WEBHOOK_TOKEN` tiene valor, el request debe incluirlo de una de estas formas:

```http
X-Kobo-Token: <token>
```

o bien:

```text
/api/v1/kobo/webhook/necesidad/?token=<token>
```

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
pytest coordinacion/tests/test_seed_inicial.py -q
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
- Seed inicial idempotente de organizaciones, catálogos, centros y usuarios por rol.

## Comandos útiles

```bash
# Migraciones
python manage.py makemigrations
python manage.py migrate

# Seed inicial
python manage.py seed_inicial --password-inicial 'Cambia-esta-clave-123'

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

- Configurar base de datos de producción con PostgreSQL/PostGIS.
- Mover `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS` y configuración de base de datos a variables de entorno reales.
- Validar formularios KoBo reales contra los mapeadores actuales.
- Agregar auditoría efectiva en acciones críticas.
- Revisar CORS para dominios finales de la PWA/portal.
- Configurar almacenamiento persistente de media en producción.
- Configurar HTTPS y reverse proxy para despliegue público.
