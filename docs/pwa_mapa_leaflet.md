# PWA Nexo Campo: mapa Leaflet + OpenStreetMap

La carpeta `pwa/` contiene la primera PWA operativa del proyecto Nexo para uso de campo. Cumple el pendiente del mapa solicitado en el prompt maestro: Leaflet + OpenStreetMap, visualización de centros, necesidades por triage, donaciones disponibles y cache limitado para reducir consumo móvil.

## Qué incluye

- **Astro 5** como shell estático ligero.
- **Tailwind** con fuentes del sistema, sin web fonts.
- **Alpine.js** para estado mínimo de interfaz.
- **Dexie/IndexedDB** para cache local de datos de API.
- **Leaflet** para el mapa operativo.
- **Workbox vía `@vite-pwa/astro`** para service worker, app shell y cache runtime.

## Datos que consume

La PWA lee la API existente:

- `GET /api/v1/centros-salud/`
- `GET /api/v1/necesidades/`
- `GET /api/v1/donaciones/`
- `GET /api/v1/catalogos/`

El token DRF se pega en la interfaz y se guarda solo en `localStorage` del dispositivo. Si la red falla, la pantalla usa la última copia guardada en IndexedDB.

## Capas del mapa

- **Centros de salud**: marcador azul, usa `CentroSalud.geolocalizacion`.
- **Necesidades abiertas/parciales**: marcador por triage sobre la coordenada del centro.
  - Crítico: rojo.
  - Urgente: naranja.
  - Importante: amarillo.
  - Rutinario: gris.
- **Donaciones disponibles**: marcador verde, usa `Donacion.ubicacion_actual` cuando existe coordenada.

## Control de datos móviles

El modo ahorro viene activo por defecto:

- zoom máximo limitado,
- `updateWhenIdle` en Leaflet para cargar tiles solo al detener el movimiento,
- `keepBuffer` reducido,
- cache Workbox `CacheFirst` para tiles de OpenStreetMap,
- límite de `120` tiles y expiración de `7` días,
- purga automática si hay presión de almacenamiento.

Esto evita precachear zonas grandes. El usuario debe navegar solo el área operativa necesaria antes de salir a campo.

## Desarrollo local

Desde la raíz del repositorio:

```bash
cd pwa
npm install
npm run dev
```

Por defecto la PWA llama a `/api/v1`. Si se sirve separada del backend:

```bash
PUBLIC_NEXO_API_BASE="https://nexo.ejemplo.org/api/v1" npm run dev
```

## Build de producción

```bash
cd pwa
npm install
PUBLIC_NEXO_API_BASE="https://nexo.ejemplo.org/api/v1" npm run build
```

El resultado queda en `pwa/dist/`. Puede publicarse con Caddy como sitio estático y proxy a Django para `/api/v1/`.

## Notas operativas

- La PWA no reemplaza KoBoCollect para captura primaria; complementa claim/matching/consulta operativa.
- El mapa es usable offline con datos ya sincronizados y tiles previamente visitados.
- Si una donación no tiene coordenada, aparece en los datos sincronizados pero no como marcador; conviene registrar `ubicacion_actual` para logística.
- No se capturan datos de pacientes ni PII clínica.
