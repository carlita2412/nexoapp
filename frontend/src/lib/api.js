import { guardarSesion, obtenerSesion } from './db.js';

function limpiarBase(apiBase) {
  return (apiBase || '/api/v1').replace(/\/$/, '');
}

export async function loginToken({ apiBase, username, password }) {
  const base = limpiarBase(apiBase);
  const respuesta = await fetch(`${base}/auth/token/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  });

  if (!respuesta.ok) {
    throw new Error('No se pudo iniciar sesión. Revisa usuario, clave o conexión.');
  }

  const data = await respuesta.json();
  await guardarSesion({ apiBase: base, ...data });
  return { apiBase: base, ...data };
}

export async function apiFetch(path, opciones = {}) {
  const sesion = await obtenerSesion();
  if (!sesion.token) {
    throw new Error('No hay token local. Inicia sesión al menos una vez con conexión.');
  }

  const headers = new Headers(opciones.headers || {});
  headers.set('Authorization', `Token ${sesion.token}`);
  if (!(opciones.body instanceof FormData) && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }

  const respuesta = await fetch(`${limpiarBase(sesion.apiBase)}${path}`, {
    ...opciones,
    headers,
  });

  if (!respuesta.ok) {
    const texto = await respuesta.text();
    throw new Error(texto || `Error HTTP ${respuesta.status}`);
  }

  const tipo = respuesta.headers.get('Content-Type') || '';
  return tipo.includes('application/json') ? respuesta.json() : respuesta.text();
}

export async function pushSync(eventos) {
  return apiFetch('/sync/', {
    method: 'POST',
    body: JSON.stringify({ eventos }),
  });
}

export async function pullSync(desde = null) {
  const query = desde ? `?desde=${encodeURIComponent(desde)}` : '';
  return apiFetch(`/sync/${query}`);
}

export async function obtenerCandidatos(necesidadId) {
  return apiFetch(`/necesidades/${necesidadId}/candidatos/`);
}

export async function subirFoto({ idempotencyKey, envio, blob }) {
  const form = new FormData();
  form.append('idempotency_key', idempotencyKey);
  form.append('envio', envio);
  form.append('imagen', blob, 'entrega.jpg');

  return apiFetch('/fotos/', {
    method: 'POST',
    body: form,
  });
}
