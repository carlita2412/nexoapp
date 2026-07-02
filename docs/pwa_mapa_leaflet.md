# PWA — Mapa Leaflet con tiles cacheados

Este incremento agrega y documenta la vista `/mapa/` de la PWA de campo para operar con bajo consumo de datos y soporte offline.

## Qué muestra

- Centros de salud con `geolocalizacion`.
- Necesidades abiertas o parciales, ubicadas sobre su centro y diferenciadas por `nivel_triage`:
  - `1_critico`
  - `2_urgente`
  - `3_importante`
  - `4_rutinario`
- Donaciones en estado `disponible` con `ubicacion_actual`.
- Envíos/entregas con `geolocalizacion_entrega`.

## Endpoints usados

La vista lee datos autenticados desde:

- `GET /api/v1/centros-salud/`
- `GET /api/v1/necesidades/`
- `GET /api/v1/donaciones/`
- `GET /api/v1/envios/`
- `GET /api/v1/asignaciones/`
- `GET /api/v1/catalogos/`
- `GET /api/v1/organizaciones/`

El token se toma de `localStorage` usando cualquiera de estas claves, para mantener compatibilidad con el login existente o próximo de la PWA:

- `nexo_token`
- `token`
- `auth_token`
- `nexo_auth.token`

## Offline y ahorro de datos

- Los datos operativos del mapa se guardan en IndexedDB con Dexie, en la base `nexo_campo`, tabla `mapa`.
- Si no hay señal, la vista muestra la última copia local disponible.
- La actualización de datos es manual con el botón **Actualizar datos**, para evitar sincronizaciones pesadas involuntarias en datos móviles.
- Leaflet usa `detectRetina: false`, `updateWhenIdle: true` y `keepBuffer: 1` para limitar descarga de tiles.
- El mapa limita `maxZoom` y `maxNativeZoom` a `15`.

## Cache de tiles

`astro.config.mjs` agrega una regla Workbox `CacheFirst` para `https://tile.openstreetmap.org/{z}/{x}/{y}.png` solo cuando `z <= 15`.

La caché se llama `nexo-osm-tiles-z15` y usa:

- `maxEntries: 450`
- `maxAgeSeconds: 30 días`
- `purgeOnQuotaError: true`

Esto permite precargar/usar zonas consultadas previamente sin permitir que el cache de mapa crezca sin control.

## Desarrollo local

Desde la raíz del repositorio:

```bash
npm install
npm run dev
```

## Build de producción

```bash
npm install
npm run build
```

El resultado queda en `dist/`. Puede publicarse con Caddy como sitio estático y proxy a Django para `/api/v1/`.

## Verificación manual

1. Entrar a `/mapa/` con sesión válida.
2. Tocar **Actualizar datos**.
3. Navegar la zona operativa hasta zoom 15 para poblar tiles.
4. Activar modo avión.
5. Recargar `/mapa/` y confirmar que aparecen datos locales y tiles previamente visitados.
6. Volver a tener señal y tocar **Actualizar datos** para refrescar.

## Notas operativas

- La PWA no reemplaza KoBoCollect para captura primaria; complementa claim/matching/consulta operativa.
- El mapa es usable offline con datos ya sincronizados y tiles previamente visitados.
- Si una donación o entrega no tiene coordenada, aparece en los datos sincronizados pero no como marcador; conviene registrar `ubicacion_actual` y `geolocalizacion_entrega` para logística.
- No se capturan datos de pacientes ni PII clínica.
