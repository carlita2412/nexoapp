# Geodatos reales con PostGIS

Este incremento reemplaza geolocalizaciones en texto por geometrías reales de GeoDjango/PostGIS.

## Campos convertidos

| Modelo | Campo | Tipo anterior | Tipo nuevo |
|---|---|---|---|
| `CentroSalud` | `geolocalizacion` | `CharField` | `PointField(srid=4326)` |
| `Donacion` | `ubicacion_actual` | `CharField` | `PointField(srid=4326)` |
| `Envio` | `geolocalizacion_entrega` | `CharField` | `PointField(srid=4326)` |

`Donacion.ubicacion_texto` se conserva para direcciones o referencias humanas. En `Envio` se agrega `geolocalizacion_entrega_texto` para preservar valores históricos no convertibles.

## Formato API recomendado

La API serializa puntos como GeoJSON simple:

```json
{
  "type": "Point",
  "coordinates": [-66.9036, 10.4806],
  "srid": 4326
}
```

Para escritura también se aceptan:

```json
{"type": "Point", "coordinates": [-66.9036, 10.4806]}
```

```json
{"lat": 10.4806, "lon": -66.9036}
```

```json
[-66.9036, 10.4806]
```

KoBo geopoint:

```text
10.4806 -66.9036 0 5
```

## Migración de datos

La migración `0005_postgis_pointfields.py`:

1. Agrega campos `PointField` temporales.
2. Convierte texto de coordenadas válido a `Point(srid=4326)`.
3. Preserva texto no convertible en campos descriptivos cuando existe un destino seguro.
4. Elimina los campos texto originales.
5. Renombra los campos `PointField` al nombre final usado por la API.

## Implicaciones de despliegue

- Producción debe usar `NEXO_DB_ENGINE=postgis`.
- La base debe tener `CREATE EXTENSION postgis;` antes de `python manage.py migrate`.
- Para pruebas locales/CI usar `NEXO_DB_ENGINE=spatialite`, no SQLite plano.
- Instalar dependencias del sistema: `gdal-bin`, `libgdal-dev`, `libgeos-dev`, `libproj-dev` y, para SpatiaLite, `libsqlite3-mod-spatialite`.

## Uso futuro

Con `PointField` real ya queda habilitada la base para:

- mapa Leaflet con coordenadas normalizadas,
- filtros por cercanía,
- cálculo de distancia centro ↔ donación,
- priorización logística por radio o municipio.
