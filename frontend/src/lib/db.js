import Dexie from 'dexie';

export const db = new Dexie('nexo_pwa');

db.version(1).stores({
  ajustes: '&clave',
  outbox: '&idempotency_key, estado, entity, creado_en, actualizado_en',
  organizaciones: '&id, nombre, updated_at',
  catalogos: '&id, codigo, nombre, categoria, updated_at',
  centros_salud: '&id, nombre, estado, municipio, updated_at',
  necesidades: '&id, estado, item, centro, updated_at',
  donaciones: '&id, estado, item, updated_at',
  asignaciones: '&id, necesidad, donacion, estado_claim, estado_logistico, updated_at',
  envios: '&id, asignacion, estado, updated_at',
  fotos_pendientes: '&idempotency_key, envio, estado, creado_en',
});

export async function obtenerAjuste(clave, defecto = null) {
  const fila = await db.ajustes.get(clave);
  return fila ? fila.valor : defecto;
}

export async function guardarAjuste(clave, valor) {
  await db.ajustes.put({ clave, valor });
  return valor;
}

export async function obtenerSesion() {
  return {
    apiBase: await obtenerAjuste('apiBase', '/api/v1'),
    token: await obtenerAjuste('token'),
    usuario: await obtenerAjuste('usuario'),
    rol: await obtenerAjuste('rol'),
    organizacion: await obtenerAjuste('organizacion'),
  };
}

export async function guardarSesion({ apiBase, token, usuario, rol, organizacion }) {
  await db.transaction('rw', db.ajustes, async () => {
    await guardarAjuste('apiBase', apiBase || '/api/v1');
    await guardarAjuste('token', token);
    await guardarAjuste('usuario', usuario);
    await guardarAjuste('rol', rol);
    await guardarAjuste('organizacion', organizacion);
  });
}

export async function cerrarSesionLocal() {
  await db.transaction('rw', db.ajustes, async () => {
    await db.ajustes.delete('token');
    await db.ajustes.delete('usuario');
    await db.ajustes.delete('rol');
    await db.ajustes.delete('organizacion');
  });
}

export async function guardarDeltas(deltas = {}) {
  const tablas = {
    organizaciones: db.organizaciones,
    catalogos: db.catalogos,
    centros_salud: db.centros_salud,
    necesidades: db.necesidades,
    donaciones: db.donaciones,
    asignaciones: db.asignaciones,
    envios: db.envios,
  };

  await db.transaction('rw', Object.values(tablas), async () => {
    for (const [nombre, registros] of Object.entries(deltas)) {
      const tabla = tablas[nombre];
      if (!tabla || !Array.isArray(registros)) continue;
      await tabla.bulkPut(registros);
    }
  });
}

export async function resumenCola() {
  const pendientes = await db.outbox.where('estado').equals('pendiente').count();
  const sincronizados = await db.outbox.where('estado').equals('sincronizado').count();
  const conflicto = await db.outbox.where('estado').equals('conflicto').count();
  const superada = await db.outbox.where('estado').equals('superada').count();
  const fotos = await db.fotos_pendientes.where('estado').equals('pendiente').count();
  return { pendientes, sincronizados, conflicto, superada, fotos };
}
