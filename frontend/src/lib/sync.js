import { db, guardarAjuste, guardarDeltas, obtenerAjuste, resumenCola } from './db.js';
import { pullSync, pushSync, subirFoto } from './api.js';

const ESTADOS_SERVIDOR_OK = new Set(['ok', 'duplicado']);
const EVENTO_SYNC_CAMBIO = 'nexo-sync-cambio';
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

function ahoraIso() {
  return new Date().toISOString();
}

function avisarCambioSync() {
  if (typeof window !== 'undefined') {
    window.dispatchEvent(new CustomEvent(EVENTO_SYNC_CAMBIO));
  }
}

async function guardarEstadoSync({ estadoActual, intento = false, ok = false, error = null } = {}) {
  const ahora = ahoraIso();

  await db.transaction('rw', db.ajustes, async () => {
    if (intento) await guardarAjuste('ultimoIntentoSync', ahora);
    if (estadoActual) await guardarAjuste('estadoSyncActual', estadoActual);
    if (ok) await guardarAjuste('ultimoSyncOk', ahora);
    await guardarAjuste('ultimoErrorSync', error);
  });

  avisarCambioSync();
}

function resumenErroresFotos(errores = []) {
  if (!errores.length) return null;
  const primero = errores[0];
  const extra = errores.length > 1 ? ` (+${errores.length - 1} mas)` : '';
  return `Fotos pendientes: ${primero}${extra}`;
}

async function estadoPorCola(error = null) {
  if (error) return 'error';
  const resumen = await resumenCola();
  return resumen.pendientes > 0 || resumen.fotos > 0 ? 'pendiente' : 'al_dia';
}

function estadoLocalInicial(entity, payload, extra = {}) {
  if (extra.estado_local) return extra.estado_local;
  if (payload?.estado_claim) return payload.estado_claim;
  if (payload?.estado) return payload.estado;
  if (entity === 'asignacion_claim') return 'tentativa';
  return 'pendiente';
}

function normalizarEvento(entity, payload, extra = {}) {
  const ahora = ahoraIso();
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
  const estadoActual = await estadoPorCola();
  await guardarEstadoSync({ estadoActual });
  return evento;
}

function estadoSincronizacion(estadoServidor) {
  if (ESTADOS_SERVIDOR_OK.has(estadoServidor)) return 'sincronizado';
  if (estadoServidor === 'superada') return 'superada';
  return 'conflicto';
}

function estadoClaimResultado(resultado, evento) {
  if (resultado.estado === 'superada') return 'superada';
  if (resultado.estado_claim) return resultado.estado_claim;
  if (resultado.payload?.estado_claim) return resultado.payload.estado_claim;
  if (resultado.registro?.estado_claim) return resultado.registro.estado_claim;
  if (ESTADOS_SERVIDOR_OK.has(resultado.estado)) return 'confirmada';
  return evento.payload?.estado_claim || evento.estado_local || 'tentativa';
}

function estadoLocalResultado(resultado, evento) {
  if (evento.entity === 'asignacion_claim') return estadoClaimResultado(resultado, evento);
  if (resultado.estado === 'superada') return 'superada';
  if (ESTADOS_SERVIDOR_OK.has(resultado.estado)) {
    return resultado.payload?.estado || resultado.registro?.estado || evento.payload?.estado || evento.estado_local;
  }
  return resultado.estado || 'conflicto';
}

function registroAsignacionResultado(resultado, evento, ahora) {
  if (evento.entity !== 'asignacion_claim') return null;

  const registroServidor = resultado.registro || resultado.payload || {};
  const estadoClaim = estadoClaimResultado(resultado, evento);

  return {
    ...evento.payload,
    ...registroServidor,
    id: registroServidor.id || evento.payload.id,
    idempotency_key: evento.idempotency_key,
    estado_claim: estadoClaim,
    updated_at: registroServidor.updated_at || ahora,
    actualizado_en: ahora,
    respuesta_sync: resultado,
  };
}

export async function sincronizarOutbox() {
  await guardarEstadoSync({ estadoActual: 'sincronizando', intento: true, error: null });

  const pendientes = await db.outbox.where('estado').equals('pendiente').sortBy('creado_en');

  try {
    let respuesta = { resultados: [] };

    if (pendientes.length) {
      const eventos = pendientes.map(({ idempotency_key, client_timestamp, entity, payload }) => ({
        idempotency_key,
        client_timestamp,
        entity,
        payload,
      }));

      respuesta = await pushSync(eventos);
      const resultados = respuesta.resultados || [];
      const ahora = ahoraIso();

      await db.transaction('rw', db.outbox, db.asignaciones, async () => {
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

          const asignacion = registroAsignacionResultado(resultado, evento, ahora);
          if (asignacion) await db.asignaciones.put(asignacion);
        }
      });
    }

    const fotos = await subirFotosPendientes();
    const errorFotos = resumenErroresFotos(fotos.errores);
    const estadoActual = await estadoPorCola(errorFotos);
    await guardarEstadoSync({ estadoActual, ok: !errorFotos, error: errorFotos });

    return { ...respuesta, fotos };
  } catch (error) {
    const ahora = ahoraIso();
    await db.transaction('rw', db.outbox, async () => {
      for (const evento of pendientes) {
        await db.outbox.update(evento.idempotency_key, {
          intentos: (evento.intentos || 0) + 1,
          error: error.message,
          actualizado_en: ahora,
        });
      }
    });
    await guardarEstadoSync({ estadoActual: 'error', error: error.message });
    throw error;
  }
}

export async function sincronizarDeltas() {
  await guardarEstadoSync({ estadoActual: 'sincronizando', intento: true, error: null });

  try {
    const desde = await obtenerAjuste('cursorSync', null);
    const respuesta = await pullSync(desde);
    await guardarDeltas(respuesta.deltas || {});
    if (respuesta.cursor) await guardarAjuste('cursorSync', respuesta.cursor);
    const estadoActual = await estadoPorCola();
    await guardarEstadoSync({ estadoActual, ok: true, error: null });
    return respuesta;
  } catch (error) {
    await guardarEstadoSync({ estadoActual: 'error', error: error.message });
    throw error;
  }
}

export async function sincronizarTodo() {
  await guardarEstadoSync({ estadoActual: 'sincronizando', intento: true, error: null });

  try {
    const push = await sincronizarOutbox();
    const pull = await sincronizarDeltas();
    const errorFotos = resumenErroresFotos(push.fotos?.errores || []);
    const estadoActual = await estadoPorCola(errorFotos);
    await guardarEstadoSync({ estadoActual, ok: !errorFotos, error: errorFotos });
    return { push, pull };
  } catch (error) {
    await guardarEstadoSync({ estadoActual: 'error', error: error.message });
    throw error;
  }
}

export async function guardarFotoPendiente({ idempotencyKey, envio, blob }) {
  if (!blob) return null;
  const ahora = ahoraIso();
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
  const estadoActual = await estadoPorCola();
  await guardarEstadoSync({ estadoActual });
  return idempotencyKey;
}

export async function subirFotosPendientes() {
  const pendientes = await db.fotos_pendientes.where('estado').equals('pendiente').toArray();
  const resultados = [];
  const errores = [];

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
        actualizado_en: ahoraIso(),
      });
      resultados.push(resultado);
    } catch (error) {
      errores.push(error.message);
      await db.fotos_pendientes.update(foto.idempotency_key, {
        error: error.message,
        actualizado_en: ahoraIso(),
      });
    }
  }

  return { resultados, errores };
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
