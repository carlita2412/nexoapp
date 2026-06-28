# Nexo Campo PWA

PWA ligera para operación de campo con mapa Leaflet + OpenStreetMap.

## Funciones

- Ver centros de salud georreferenciados.
- Ver necesidades abiertas/parciales por triage.
- Ver donaciones disponibles con coordenada.
- Guardar última data de API en IndexedDB con Dexie.
- Cachear app shell y tiles con Workbox.
- Limitar consumo móvil con modo ahorro activo por defecto.

## Desarrollo

```bash
npm install
npm run dev
```

Variables opcionales:

```bash
PUBLIC_NEXO_API_BASE="http://127.0.0.1:8000/api/v1"
PUBLIC_NEXO_TILE_HOST="https://tile.openstreetmap.org"
```

## Producción

```bash
npm run build
```

Publicar `dist/` como sitio estático y dejar `/api/v1/` apuntando al backend Django.
