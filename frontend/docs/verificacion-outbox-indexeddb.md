# Verificación manual del Outbox en IndexedDB/Dexie

Esta verificación confirma que la PWA Nexo guarda acciones localmente en Dexie antes de sincronizar y que los reintentos usan la misma `idempotency_key`.

## Preparación

1. Ejecuta Django y el frontend.
2. Inicia sesión una vez con conexión para guardar el token local.
3. Abre DevTools del navegador.
4. En la pestaña **Application > IndexedDB**, ubica la base `nexo_pwa`.
5. Activa modo offline desde DevTools o desconecta la red.

## Casos de aceptación offline

### 1. Crear necesidad

1. En la PWA, entra en **Necesidad**.
2. Completa centro, item, cantidad, triage y requisitos.
3. Pulsa **Guardar local primero**.
4. Revisa `IndexedDB > nexo_pwa > outbox`.
5. Debe existir una fila con:
   - `entity: "necesidad"`
   - `estado: "pendiente"`
   - `estado_local: "abierta"`
   - `idempotency_key`
   - `client_timestamp`
   - `payload.id`
   - `creado_en`
   - `actualizado_en`
   - `intentos: 0`
   - `error: null`
   - `respuesta: null`

### 2. Crear donación

1. Entra en **Donación**.
2. Completa item, cantidad, condición y ubicación.
3. Pulsa **Guardar local primero**.
4. Debe aparecer una fila en `outbox` con:
   - `entity: "donacion"`
   - `estado: "pendiente"`
   - `estado_local` igual al estado local de la donación, normalmente `"disponible"`
   - campos completos de idempotencia, tiempo, payload, intentos, error y respuesta.

### 3. Claim offline

1. Entra en **Matching**.
2. Selecciona una necesidad y reclama una donación compatible.
3. Debe aparecer una fila en `outbox` con:
   - `entity: "asignacion_claim"`
   - `estado: "pendiente"`
   - `estado_local: "tentativa"`
   - `payload.estado_claim: "tentativa"`
   - `payload.claim_ts_cliente`

### 4. Confirmar entrega con foto pendiente

1. Entra en **Entrega**.
2. Selecciona una asignación, completa responsable, recibido por, ubicación/notas y adjunta una foto.
3. Pulsa **Guardar entrega offline**.
4. En `outbox` debe existir una fila con:
   - `entity: "envio"`
   - `estado: "pendiente"`
   - `estado_local: "entregado"`
   - `payload.estado: "entregado"`
5. En `fotos_pendientes` debe existir una fila con:
   - `envio` igual al `payload.id` del evento `envio`
   - `estado: "pendiente"`
   - `idempotency_key`
   - `blob`

## Verificación por consola

En DevTools Console ejecuta:

```js
await window.nexoDebug.verificarOutboxManual()
```

Resultado esperado:

```js
{
  total: 4,
  validos: 4,
  invalidos: 0,
  filas: [
    // cada fila debe tener valido: true y faltantes: []
  ]
}
```

También puedes inspeccionar directamente:

```js
await window.nexoDebug.db.outbox.toArray()
await window.nexoDebug.db.fotos_pendientes.toArray()
```

## Reintento y no duplicados

1. Vuelve a activar la conexión.
2. En **Cola**, pulsa **Reintentar sincronización manual**.
3. La PWA debe enviar solo eventos con `estado: "pendiente"`.
4. Si el servidor confirma `ok` o `duplicado`, el evento pasa a `estado: "sincronizado"`.
5. Si el servidor devuelve `superada`, el evento pasa a `estado: "superada"` y `estado_local: "superada"`.
6. Repite el botón de reintento: no debe crearse una nueva fila ni cambiar la `idempotency_key`; Dexie usa `outbox.&idempotency_key` y el servidor descarta duplicados.

## UI esperada

En la pestaña **Cola**, cada evento debe mostrar:

- entidad,
- estado de sincronización,
- estado local,
- `idempotency_key`,
- fecha,
- intentos,
- error o respuesta del servidor.
