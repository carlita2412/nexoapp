# KoBoToolbox: validación de formularios reales Nexo

Este documento cierra el pendiente operativo de validar los formularios KoBo reales contra los mapeadores actuales antes del despliegue público.

## 1. Objetivo

Validar que los assets reales de KoBo para **necesidades** y **donaciones** producen submissions compatibles con Nexo:

- nombres exactos de campos,
- coordenadas/geopoint,
- catálogos CSV,
- asset UID configurado,
- webhook con token,
- mapeo idempotente hacia `/api/v1/sync/`.

## 2. Variables `.env`

Configura en el backend:

```env
KOBO_API_URL=https://kf.kobotoolbox.org/api/v2
KOBO_TOKEN=token-api-kobo
KOBO_ASSET_NECESIDADES=uid-del-asset-necesidades
KOBO_ASSET_DONACIONES=uid-del-asset-donaciones
KOBO_WEBHOOK_TOKEN=token-largo-aleatorio-para-webhook
KOBO_PULL_LIMIT=500
```

`KOBO_WEBHOOK_TOKEN` debe ser distinto al `KOBO_TOKEN`. Es el secreto compartido entre KoBo REST Service y Nexo.

## 3. Contrato de campos aceptado

### Necesidades

| Campo esperado | Aliases aceptados | Requerido | Uso |
|---|---|---:|---|
| `_uuid` | `uuid`, `submission_uuid` | Sí | Base de UUID estable e idempotency key. |
| `_submission_time` | `submission_time` | No | Timestamp cliente. |
| `centro_id` | `centro_salud_id`, `centro` | Sí | UUID del centro exportado en CSV. |
| `item_codigo` | `codigo_item`, `item` | Sí | Código del catálogo exportado en CSV. |
| `cantidad_solicitada` | `cantidad` | Sí | Entero mayor a cero. |
| `nivel_triage` | `triage` | Sí | `1_critico`, `2_urgente`, `3_importante`, `4_rutinario`. |
| `reportada_por_id` | `organizacion_id`, `reportada_por` | Condicional | UUID de organización. |
| `reportada_por_nombre` | `organizacion_nombre`, `nombre_organizacion` | Condicional | Alternativa si no se usa UUID. |
| `requiere_electricidad` | — | No | Booleano. |
| `requiere_oxigeno` | — | No | Booleano. |
| `requiere_personal_entrenado` | `requiere_personal_tecnico` | No | Booleano. |
| `requiere_insumos` | — | No | Booleano. |

Debe existir `reportada_por_id` **o** `reportada_por_nombre`.

### Donaciones

| Campo esperado | Aliases aceptados | Requerido | Uso |
|---|---|---:|---|
| `_uuid` | `uuid`, `submission_uuid` | Sí | Base de UUID estable e idempotency key. |
| `_submission_time` | `submission_time` | No | Timestamp cliente. |
| `item_codigo` | `codigo_item`, `item` | Sí | Código del catálogo exportado en CSV. |
| `cantidad` | — | Sí | Entero mayor a cero. |
| `condicion` | — | No | `nuevo`, `usado_funcional`, `requiere_reparacion`, `requiere_calibracion`. |
| `donante_id` | `organizacion_id`, `donante` | Condicional | UUID de organización donante. |
| `donante_nombre` | `organizacion_nombre`, `nombre_organizacion` | Condicional | Alternativa si no se usa UUID. |
| `ubicacion_actual` | `geopoint`, `geolocalizacion` | Sí | Geopoint KoBo `lat lon alt accuracy`. |
| `ubicacion_texto` | `direccion` | No | Referencia textual. |
| `vencimiento` | `fecha_vencimiento` | No | Fecha para insumos/medicamentos. |
| `certificacion` | — | No | Texto libre corto de certificación. |

Debe existir `donante_id` **o** `donante_nombre`.

## 4. Catálogos CSV

Antes de validar formularios reales, exporta/carga los CSV usados por los selects de KoBo:

```bash
python manage.py exportar_catalogos_kobo kobo_forms/media
```

Validaciones mínimas:

- El CSV de centros debe exponer `centro_id` con UUID real de `CentroSalud`.
- El CSV de catálogos debe exponer `item_codigo` con `Catalogo.codigo`.
- El CSV de organizaciones debe exponer UUID de organización para `reportada_por_id` o `donante_id`.
- Los nombres visibles pueden cambiar, pero los valores enviados por KoBo deben ser UUID/código exacto.

Si KoBo envía un código que no existe en `Catalogo.codigo`, Nexo rechaza la submission con `Catálogo no existe`.

## 5. Validar assets reales sin guardar datos

Con `.env` configurado y al menos una submission real en cada asset:

```bash
python manage.py validar_kobo_assets --tipo necesidad --limite 5
python manage.py validar_kobo_assets --tipo donacion --limite 5
```

O ambos:

```bash
python manage.py validar_kobo_assets --tipo todos --limite 5
```

Este comando descarga submissions reales desde KoBo y ejecuta los mapeadores, pero **no guarda** necesidades ni donaciones. Si falla, revisa:

- nombre exacto del campo en XLSForm,
- valor enviado por los selects,
- catálogo CSV cargado como media del formulario,
- formato de geopoint,
- asset UID en `.env`.

## 6. Validar coordenadas

KoBo debe enviar geopoint con formato:

```text
lat lon alt accuracy
```

Ejemplo válido:

```text
10.5000 -66.9167 0 5
```

Nexo lo convierte a PointField SRID 4326 usando longitud/latitud internamente. Una coordenada vacía o no parseable en donaciones se rechaza porque el mapa y la logística dependen de ella.

## 7. Configurar webhook REST Service en KoBo

En cada asset real de KoBo:

1. Abrir el formulario en KoBoToolbox.
2. Ir a **Settings**.
3. Entrar en **REST Services**.
4. Agregar servicio REST.
5. Para necesidades usar:

```text
https://TU_DOMINIO/api/v1/kobo/webhook/necesidad/
```

6. Para donaciones usar:

```text
https://TU_DOMINIO/api/v1/kobo/webhook/donacion/
```

7. Configurar método `POST` y payload JSON.
8. Enviar el token de una de estas dos formas:

Header recomendado:

```text
X-Kobo-Token: valor-de-KOBO_WEBHOOK_TOKEN
```

Alternativa si KoBo no permite header personalizado:

```text
https://TU_DOMINIO/api/v1/kobo/webhook/donacion/?token=valor-de-KOBO_WEBHOOK_TOKEN
```

## 8. Probar webhook con token

Prueba token inválido:

```bash
curl -X POST https://TU_DOMINIO/api/v1/kobo/webhook/donacion/ \
  -H 'Content-Type: application/json' \
  -H 'X-Kobo-Token: incorrecto' \
  -d '{}'
```

Debe responder `403` con `Token de webhook inválido.`

Prueba token válido con una submission mínima de donación:

```bash
curl -X POST https://TU_DOMINIO/api/v1/kobo/webhook/donacion/ \
  -H 'Content-Type: application/json' \
  -H 'X-Kobo-Token: valor-de-KOBO_WEBHOOK_TOKEN' \
  -d '{
    "_uuid": "prueba-donacion-001",
    "_submission_time": "2026-06-28T14:40:00Z",
    "item_codigo": "MONITOR_SIGNOS",
    "cantidad": "1",
    "condicion": "nuevo",
    "donante_nombre": "Donante prueba",
    "geopoint": "10.5000 -66.9167 0 5",
    "ubicacion_texto": "Caracas"
  }'
```

Debe responder `201` si es nueva o `200` si ya fue procesada por idempotencia.

## 9. Validar ingesta incremental real

Una vez que los mapeadores pasan con `validar_kobo_assets`:

```bash
python manage.py ingestar_kobo --tipo necesidad
python manage.py ingestar_kobo --tipo donacion
```

Reejecuta el comando para confirmar idempotencia: no debe duplicar registros.

## 10. Checklist de cierre

- [ ] Asset real de necesidades validado con `validar_kobo_assets --tipo necesidad`.
- [ ] Asset real de donaciones validado con `validar_kobo_assets --tipo donacion`.
- [ ] Campos exactos del XLSForm coinciden con el contrato de este documento.
- [ ] Selects usan valores CSV correctos (`centro_id`, `item_codigo`, organización).
- [ ] Geopoint de donaciones llega como `lat lon alt accuracy`.
- [ ] Webhook rechaza token inválido.
- [ ] Webhook acepta token válido.
- [ ] Reingesta incremental no duplica por idempotencia.
