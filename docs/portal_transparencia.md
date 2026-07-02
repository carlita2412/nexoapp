# Portal publico de transparencia

La Fase 2 incorpora un portal estatico solo lectura para donantes y prensa en:

```text
/transparencia/
```

El portal consume endpoints publicos filtrados y no usa token.

## Endpoints publicos

```http
GET /api/v1/publico/transparencia/resumen/
GET /api/v1/publico/transparencia/donaciones/
```

## Datos publicados

### Resumen agregado

- necesidades abiertas o parciales,
- necesidades cubiertas,
- donaciones entregadas o en uso,
- donaciones dentro del pipeline publico,
- tiempo promedio de respuesta en horas,
- cobertura por estado y municipio.

### Trazabilidad por donacion

Cada donacion publica incluye:

- item,
- categoria,
- cantidad,
- unidad,
- condicion,
- estado actual,
- donante publicable,
- origen geografico cuando exista,
- destino: centro, estado, municipio y GPS si aplica,
- necesidad asociada sin datos personales,
- organizacion responsable publicable,
- pipeline:
  - registrada,
  - asignada,
  - en transito,
  - entregada,
  - en uso.

Cuando un envio entregado tiene foto comprimida lista o referencia publica, el pipeline expone `foto_url`. Cuando tiene coordenada de entrega, expone `gps`.

## Datos no publicados

La API publica evita exponer:

- contacto de organizaciones,
- contacto responsable del centro,
- responsable del envio,
- recibido por,
- notas internas,
- usuarios,
- auditoria interna,
- idempotency keys,
- datos clinicos o PII de pacientes.

Los donantes privados no verificados se muestran como `Donante privado`.

## Archivos relacionados

- `coordinacion/transparencia.py`: construye respuestas sanitizadas.
- `coordinacion/urls.py`: expone rutas publicas bajo `/api/v1/publico/transparencia/`.
- `src/pages/transparencia.astro`: portal publico estatico.

## Verificacion manual

```bash
python manage.py runserver
```

Abrir:

```text
http://127.0.0.1:8000/api/v1/publico/transparencia/resumen/
http://127.0.0.1:8000/api/v1/publico/transparencia/donaciones/
```

Luego levantar la PWA:

```bash
npm install
npm run dev
```

Abrir:

```text
http://127.0.0.1:5173/transparencia/
```
