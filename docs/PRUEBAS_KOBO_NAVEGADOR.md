# Pruebas KoBo desde navegador

Esta guía permite probar el módulo KoBo usando la API navegable de Django REST Framework, sin Postman.

## 1. Preparar servidor local

```powershell
python manage.py migrate
python manage.py runserver
```

Abrir en el navegador:

```text
http://127.0.0.1:8000/api/v1/salud/
```

Debe responder `status: ok`.

## 2. Iniciar sesión en la API navegable

Crear usuario si no existe:

```powershell
python manage.py createsuperuser
```

Entrar en:

```text
http://127.0.0.1:8000/api-auth/login/
```

Iniciar sesión con el superusuario o con un usuario `admin` / `coordinador` / `campo`.

## 3. Crear datos base obligatorios

Antes de probar KoBo deben existir:

- Organización
- Centro de salud
- Catálogo / ítem

Desde navegador:

```text
http://127.0.0.1:8000/api/v1/organizaciones/
http://127.0.0.1:8000/api/v1/centros-salud/
http://127.0.0.1:8000/api/v1/catalogos/
```

Ejemplo de catálogo:

```json
{
  "codigo": "MONITOR-SV",
  "nombre": "Monitor de signos vitales",
  "categoria": "equipo_medico",
  "unidad": "unidad",
  "activo": true
}
```

Guardar los UUID generados de `organizacion`, `centro` y `catalogo`.

## 4. Probar webhook de necesidad

Abrir:

```text
http://127.0.0.1:8000/api/v1/kobo/webhook/necesidad/
```

En el formulario de DRF, enviar `POST` con JSON:

```json
{
  "_uuid": "kobo-nec-001",
  "_submission_time": "2026-06-27T12:00:00-04:00",
  "centro_id": "PEGAR_UUID_CENTRO",
  "item_codigo": "MONITOR-SV",
  "reportada_por_id": "PEGAR_UUID_ORGANIZACION",
  "cantidad_solicitada": "2",
  "nivel_triage": "1_critico",
  "requiere_electricidad": "si",
  "requiere_oxigeno": "no",
  "requiere_personal_entrenado": "si"
}
```

Resultado esperado:

```json
{
  "estado": "ok",
  "entity": "necesidad"
}
```

Verificar que se creó en:

```text
http://127.0.0.1:8000/api/v1/necesidades/
```

## 5. Probar idempotencia

Enviar el mismo JSON otra vez, con el mismo `_uuid`.

Resultado esperado:

```json
{
  "estado": "duplicado"
}
```

No debe crearse una segunda necesidad.

## 6. Probar webhook de donación

Abrir:

```text
http://127.0.0.1:8000/api/v1/kobo/webhook/donacion/
```

Enviar JSON:

```json
{
  "_uuid": "kobo-don-001",
  "_submission_time": "2026-06-27T13:00:00-04:00",
  "item_codigo": "MONITOR-SV",
  "donante_id": "PEGAR_UUID_ORGANIZACION",
  "cantidad": "3",
  "condicion": "nuevo",
  "ubicacion_texto": "Caracas"
}
```

Resultado esperado:

```json
{
  "estado": "ok",
  "entity": "donacion"
}
```

Verificar en:

```text
http://127.0.0.1:8000/api/v1/donaciones/
```

## 7. Probar pull incremental real desde KoBo

Configurar `.env` o variables de entorno:

```powershell
$env:KOBO_TOKEN="TU_TOKEN"
$env:KOBO_ASSET_NECESIDADES="ASSET_UID_NECESIDADES"
$env:KOBO_ASSET_DONACIONES="ASSET_UID_DONACIONES"
```

Ejecutar:

```powershell
python manage.py ingestar_kobo --tipo necesidad
python manage.py ingestar_kobo --tipo donacion
```

Luego refrescar en navegador:

```text
http://127.0.0.1:8000/api/v1/necesidades/
http://127.0.0.1:8000/api/v1/donaciones/
```

## 8. Errores frecuentes

### `Catálogo no existe`

El `item_codigo` del JSON no coincide con ningún `Catalogo.codigo`.

### `Centro de salud no existe`

El `centro_id` no es un UUID real de `/api/v1/centros-salud/`.

### `Organización no existe`

El `reportada_por_id` o `donante_id` no existe en `/api/v1/organizaciones/`.

### `403 Token de webhook inválido`

Si `KOBO_WEBHOOK_TOKEN` está configurado, enviar el token como query param:

```text
/api/v1/kobo/webhook/necesidad/?token=TU_TOKEN_WEBHOOK
```

O como header:

```text
X-Kobo-Token: TU_TOKEN_WEBHOOK
```
