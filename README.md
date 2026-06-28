# Nexo — Backend de coordinación médica

Backend Django para coordinar necesidades y donaciones médicas del proyecto **Nexo**.

Este incremento inicia el desarrollo operativo del **módulo KoBo**: ingesta incremental desde KoBoToolbox, webhook alternativo, mapeo idempotente y reutilización del endpoint `/api/v1/sync`.

## Reglas que respeta

- Dominio y endpoints en español.
- UUID generados en cliente o derivados de `_uuid` de KoBo.
- Idempotencia obligatoria con `idempotency_key`.
- Sin pacientes ni PII clínica innecesaria.
- Sin vendor lock-in: Django + DRF + django-q2 + KoBoToolbox.

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
2. Exportar catálogos reales a CSV para desplegables KoBo.
3. Agregar pruebas con fixtures reales de submissions.
4. Conectar fotos de confirmación en endpoint multipart separado.
