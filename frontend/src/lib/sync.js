import { db, guardarAjuste, guardarDeltas, obtenerAjuste } from './db.js';
import { pullSync, pushSync, subirFoto } from './api.js';

const ESTADOS_SERVIDOR_OK = new Set(['ok', 'duplicado']);
const CAMPOS_EVENTO_REQUERIDOS = [
  'idempotency_key',
  'client_timestamp',
  'entity',
  'payload',
  'estado',
  'estado_local',
  'creado_en',
  'actualizado_en',
  'intentos',
  'error',
  'respuesta',
];

export function uuid() {
  if (globalThis.crypto?.randomUUID) return globalThis.crypto.randomUUID();
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === 'x' ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

function estadoLocalInicial(entity, payload, extra = {}) {
  if (extra.estado_local) return extra.estado_local;
  if (payload?.estado_claim) return payload.estado_claim;
  if (payload?.estado) return payload.estado;
  if (entity === 'asignacion_claim') return 'tentativa';
  return 'pendiente';
}

function normalizarEvento(entity, payload, extra = {}) {
  const ahora = new Date().toISOString();
  const eventoBase = typeof entity === 'object' && entity !== null ? entity : { entity, payload, ...extra };
  const eventoPayload = eventoBase.payload;
  const eventoEntity = eventoBase.entity;

  if (!eventoEntity) throw new Error('El evento de outbox requiere entity.');
  if (!eventoPayload || typeof eventoPayload !== 'object') {
    throw new Error(`El evento ${eventoEntity} requiere payload objeto.`);
  }

  return {
    idempotency_key: eventoBase.idempotency_key || uuid(),
    client_timestamp: eventoBase.client_timestamp || ahora,
    entity: eventoEntity,
    payload: eventoPayload,
    estado: eventoBase.estado || 'pendiente',
    estado_local: estadoLocalInicial(eventoEntity, eventoPayload, eventoBase),
    intentos: eventoBase.intentos ?? 0,
    respuesta: eventoBase.respuesta ?? null,
    error: eventoBase.error ?? null,
    creado_en: eventoBase.creado_en || ahora,
    actualizado_en: eventoBase.actualizado_en || ahora,
  };
}

export async function encolarEvento(entity, payload, extra = {}) {
  const evento = normalizarEvento(entity, payload, extra);
  await db.outbox.put(evento);
  return evento;
}

function estadoSincronizacion(estadoServidor) {
  if (ESTADOS_SERVIDOR_OK.has(estadoServidor)) return 'sincronizado';
  if (estadoServidor === 'superada') return 'superada';
  return 'conflicto';
}

function estadoLocalResultado(resultado, evento) {
  if (resultado.estado === 'superada') return 'superada';
  if (ESTADOS_SERVIDOR_OK.has(resultado.estado)) {
    if (evento.entity === 'asignacion_claim') {
      return resultado.estado_claim || resultado.payload?.estado_claim || resultado.registro?.estado_claim || 'confirmada';
    }
    return resultado.payload?.estado || resultado.registro?.estado || evento.payload?.estado || evento.estado_local;
  }
  return resultado.estado || 'conflicto';
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
        const evento = pendientes.find((item) => item.idempotency_key === resultado.idempotency_key);
        if (!evento) continue;

        await db.outbox.update(resultado.idempotency_key, {
          estado: estadoSincronizacion(resultado.estado),
          estado_local: estadoLocalResultado(resultado, evento),
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
  const ahora = new Date().toISOString();
  await db.fotos_pendientes.put({
    idempotency_key: idempotencyKey,
    envio,
    blob,
    estado: 'pendiente',
    respuesta: null,
    error: null,
    creado_en: ahora,
    actualizado_en: ahora,
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

    const envioSincronizado = eventoEnvio ? eventoEnvio.estado === 'sincronizado' : Boolean(envio);
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
        actualizado_en: new Date().toISOString(),
      });
      resultados.push(resultado);
    } catch (error) {
      await db.fotos_pendientes.update(foto.idempotency_key, {
        error: error.message,
        actualizado_en: new Date().toISOString(),
      });
    }
  }

  return resultados;
}

export async function verificarOutboxManual() {
  const eventos = await db.outbox.toArray();
  const filas = eventos.map((evento) => {
    const faltantes = CAMPOS_EVENTO_REQUERIDOS.filter((campo) => !(campo in evento));
    return {
      idempotency_key: evento.idempotency_key,
      entity: evento.entity,
      estado: evento.estado,
      estado_local: evento.estado_local,
      creado_en: evento.creado_en,
      valido: faltantes.length === 0 && Boolean(evento.payload),
      faltantes,
    };
  });

  return {
    total: filas.length,
    validos: filas.filter((fila) => fila.valido).length,
    invalidos: filas.filter((fila) => !fila.valido).length,
    filas,
  };
}
