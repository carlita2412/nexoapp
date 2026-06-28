import { db, guardarAjuste, guardarDeltas, obtenerAjuste } from './db.js';
import { pullSync, pushSync, subirFoto } from './api.js';

export function uuid() {
  if (crypto?.randomUUID) return crypto.randomUUID();
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === 'x' ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

export async function encolarEvento(entity, payload, extra = {}) {
  const ahora = new Date().toISOString();
  const idempotencyKey = extra.idempotency_key || uuid();
  const evento = {
    idempotency_key: idempotencyKey,
    client_timestamp: ahora,
    entity,
    payload,
  };

  await db.outbox.put({
    ...evento,
    estado: 'pendiente',
    intentos: 0,
    respuesta: null,
    error: null,
    creado_en: ahora,
    actualizado_en: ahora,
  });

  return evento;
}

function estadoLocal(estadoServidor) {
  if (estadoServidor === 'ok' || estadoServidor === 'duplicado') return 'sincronizado';
  if (estadoServidor === 'superada') return 'superada';
  return 'conflicto';
}

export async function sincronizarOutbox() {
  const pendientes = await db.outbox.where('estado').equals('pendiente').sortBy('creado_en');
  if (!pendientes.length) return { resultados: [] };

  const eventos = pendientes.map(({ idempotency_key, client_timestamp, entity, payload }) => ({
    idempotency_key,
    client_timestamp,
    entity,
    payload,
  }));

  try {
    const respuesta = await pushSync(eventos);
    const resultados = respuesta.resultados || [];
    const ahora = new Date().toISOString();

    await db.transaction('rw', db.outbox, async () => {
      for (const resultado of resultados) {
        await db.outbox.update(resultado.idempotency_key, {
          estado: estadoLocal(resultado.estado),
          respuesta: resultado,
          error: null,
          actualizado_en: ahora,
        });
      }
    });

    await subirFotosPendientes();
    return respuesta;
  } catch (error) {
    const ahora = new Date().toISOString();
    await db.transaction('rw', db.outbox, async () => {
      for (const evento of pendientes) {
        await db.outbox.update(evento.idempotency_key, {
          intentos: (evento.intentos || 0) + 1,
          error: error.message,
          actualizado_en: ahora,
        });
      }
    });
    throw error;
  }
}

export async function sincronizarDeltas() {
  const desde = await obtenerAjuste('cursorSync', null);
  const respuesta = await pullSync(desde);
  await guardarDeltas(respuesta.deltas || {});
  if (respuesta.cursor) await guardarAjuste('cursorSync', respuesta.cursor);
  return respuesta;
}

export async function sincronizarTodo() {
  const push = await sincronizarOutbox();
  const pull = await sincronizarDeltas();
  return { push, pull };
}

export async function guardarFotoPendiente({ idempotencyKey, envio, blob }) {
  if (!blob) return null;
  await db.fotos_pendientes.put({
    idempotency_key: idempotencyKey,
    envio,
    blob,
    estado: 'pendiente',
    error: null,
    creado_en: new Date().toISOString(),
  });
  return idempotencyKey;
}

export async function subirFotosPendientes() {
  const pendientes = await db.fotos_pendientes.where('estado').equals('pendiente').toArray();
  const resultados = [];

  for (const foto of pendientes) {
    const envio = await db.envios.get(foto.envio);
    const eventoEnvio = await db.outbox
      .where('entity')
      .equals('envio')
      .filter((evento) => evento.payload?.id === foto.envio)
      .first();

    const envioSincronizado = envio || eventoEnvio?.estado === 'sincronizado';
    if (!envioSincronizado) continue;

    try {
      const resultado = await subirFoto({
        idempotencyKey: foto.idempotency_key,
        envio: foto.envio,
        blob: foto.blob,
      });
      await db.fotos_pendientes.update(foto.idempotency_key, {
        estado: 'sincronizado',
        respuesta: resultado,
        error: null,
      });
      resultados.push(resultado);
    } catch (error) {
      await db.fotos_pendientes.update(foto.idempotency_key, {
        error: error.message,
      });
    }
  }

  return resultados;
}
