# Nexo — Backend de coordinación médica

Backend Django para coordinar necesidades y donaciones médicas del proyecto **Nexo**.

Este incremento inicia el desarrollo operativo del **módulo KoBo**: ingesta incremental desde KoBoToolbox, webhook alternativo, mapeo idempotente y reutilización del endpoint `/api/v1/sync`.

## Reglas que respeta

- Dominio y endpoints en español.
- UUID generados en cliente o derivados de `_uuid` de KoBo.
- Idempotencia obligatoria con `idempotency_key`.
- Sin pacientes ni PII clínica innecesaria.
- Sin vendor lock-in: Django + DRF + django-q2 + KoBoToolbox.
- Autenticación requerida por defecto y permisos mínimos por rol antes de abrir la API.

## Seguridad mínima antes de abrir la API

La API aplica RBAC con los roles `admin`, `coordinador`, `campo` y `lectura`.
El healthcheck `/api/v1/salud/` es público; el resto de rutas sensibles requiere autenticación.

| Acción | admin | coordinador | campo | lectura |
|---|---:|---:|---:|---:|
| Crear necesidades | Sí | Sí | Sí | No |
| Crear donaciones | Sí | Sí | Sí | No |
| Reclamar necesidad | Sí | Sí | Limitado a su organización | No |
| Ver matching | Sí | Sí | Sí | Sí |
| Confirmar entrega | Sí | Sí | Sí | No |
| Administrar catálogos | Sí | No | No | No |

## Instalación local

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py runserver
```

## Variables KoBo

```bash
KOBO_API_URL=https://kf.kobotoolbox.org/api/v2
KOBO_TOKEN=tu_token
KOBO_ASSET_NECESIDADES=asset_uid_necesidades
KOBO_ASSET_DONACIONES=asset_uid_donaciones
```

## Catálogos iniciales obligatorios

Antes de probar la ingesta KoBo y el matching, carga los catálogos base en la base de datos y expórtalos como `media` para los formularios KoBo:

```bash
python manage.py exportar_catalogos_kobo kobo_forms/media
```

Valida que existan, como mínimo:

- Organizaciones.
- Centros de salud.
- Catálogo de ítems.
- Usuarios con rol.

Estos catálogos son parte crítica del vocabulario controlado. Sin ellos, el matching pierde calidad porque los formularios tienden a capturar texto libre y el prompt maestro exige dropdowns/catálogos para reducir errores de campo.

## Uso del módulo KoBo

### Pull manual o cron

```bash
python manage.py ingestar_kobo
python manage.py ingestar_kobo --tipo necesidad
python manage.py ingestar_kobo --tipo donacion
```

### Webhook KoBo REST Service

Configura KoBo para enviar cada submission a:

```text
POST /api/v1/kobo/webhook/necesidad
POST /api/v1/kobo/webhook/donacion
```

La ingesta usa `_uuid` como fuente de verdad: genera UUID estable para la entidad y `idempotency_key` estable para el evento. Reintentos, repull o webhook repetido no deben duplicar registros.

## Siguiente incremento sugerido

1. Completar XLSForm finales en `kobo_forms/`.
2. Agregar fixtures/seed inicial para organizaciones, centros, ítems y usuarios con rol.
3. Agregar prueba de exportación de catálogos a `kobo_forms/media`.
4. Agregar pruebas con fixtures reales de submissions.
5. Conectar fotos de confirmación en endpoint multipart separado.
