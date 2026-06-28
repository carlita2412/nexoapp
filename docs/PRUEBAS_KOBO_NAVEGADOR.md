# Pruebas KoBo desde navegador

Esta guía permite probar el módulo KoBo desde el navegador sin Postman.

Importante: escribir una URL en la barra del navegador siempre hace un `GET`. Los webhooks de KoBo solo aceptan `POST`, por eso es normal ver:

```json
{
  "detail": "Método \"GET\" no permitido."
}
```

Ese mensaje confirma que la ruta existe. Para probar el webhook desde navegador se debe enviar un `POST` usando la consola del navegador.

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

## 4. Probar webhook de necesidad con POST desde navegador

Abrir cualquier página del servidor, por ejemplo:

```text
http://127.0.0.1:8000/api/v1/salud/
```

Abrir DevTools con `F12`, ir a la pestaña **Console** y pegar este código. Cambiar `PEGAR_UUID_CENTRO` y `PEGAR_UUID_ORGANIZACION` por UUID reales.

```javascript
fetch("http://127.0.0.1:8000/api/v1/kobo/webhook/necesidad/", {
  method: "POST",
  credentials: "omit",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    _uuid: "kobo-nec-001",
    _submission_time: "2026-06-27T12:00:00-04:00",
    centro_id: "PEGAR_UUID_CENTRO",
    item_codigo: "MONITOR-SV",
    reportada_por_id: "PEGAR_UUID_ORGANIZACION",
    cantidad_solicitada: "2",
    nivel_triage: "1_critico",
    requiere_electricidad: "si",
    requiere_oxigeno: "no",
    requiere_personal_entrenado: "si"
  })
})
  .then(async (r) => ({ status: r.status, data: await r.json() }))
  .then(console.log);
```

Resultado esperado:

```json
{
  "status": 201,
  "data": {
    "estado": "ok",
    "entity": "necesidad"
  }
}
```

Verificar que se creó en:

```text
http://127.0.0.1:8000/api/v1/necesidades/
```

## 5. Probar idempotencia

Ejecutar exactamente el mismo `fetch` otra vez, con el mismo `_uuid`.

Resultado esperado:

```json
{
  "status": 200,
  "data": {
    "estado": "duplicado"
  }
}
```

No debe crearse una segunda necesidad.

## 6. Probar webhook de donación con POST desde navegador

Abrir DevTools con `F12`, ir a **Console** y pegar este código. Cambiar `PEGAR_UUID_ORGANIZACION` por un UUID real.

```javascript
fetch("http://127.0.0.1:8000/api/v1/kobo/webhook/donacion/", {
  method: "POST",
  credentials: "omit",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    _uuid: "kobo-don-001",
    _submission_time: "2026-06-27T13:00:00-04:00",
    item_codigo: "MONITOR-SV",
    donante_id: "PEGAR_UUID_ORGANIZACION",
    cantidad: "3",
    condicion: "nuevo",
    ubicacion_texto: "Caracas"
  })
})
  .then(async (r) => ({ status: r.status, data: await r.json() }))
  .then(console.log);
```

Resultado esperado:

```json
{
  "status": 201,
  "data": {
    "estado": "ok",
    "entity": "donacion"
  }
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

### `Método "GET" no permitido`

Es normal si se abrió el webhook desde la barra del navegador. El webhook existe, pero debe probarse con `POST` usando `fetch` en la consola o usando KoBo REST Service.

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

O como header dentro del `fetch`:

```javascript
headers: {
  "Content-Type": "application/json",
  "X-Kobo-Token": "TU_TOKEN_WEBHOOK"
}
```
