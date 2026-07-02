import { guardarSesion, obtenerSesion } from './db.js';

export const API_BASE_DEFECTO = import.meta.env.PUBLIC_NEXO_API_BASE || '/api/v1';

function limpiarBase(apiBase) {
  return (apiBase || API_BASE_DEFECTO).replace(/\/$/, '');
}

function mensajeErrorLogin(error) {
  if (error instanceof TypeError) {
    return 'No se pudo conectar con la API. Revisa API base, CORS y que Django esté corriendo en http://127.0.0.1:8000.';
  }
  return error.message || 'No se pudo iniciar sesión. Revisa usuario, clave o conexión.';
}

export async function loginToken({ apiBase, username, password }) {
  const base = limpiarBase(apiBase);

  try {
    const respuesta = await fetch(`${base}/auth/token/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    });

    if (!respuesta.ok) {
      const texto = await respuesta.text();
      throw new Error(texto || 'No se pudo iniciar sesión. Revisa usuario, clave o conexión.');
    }

    const data = await respuesta.json();
    await guardarSesion({ apiBase: base, ...data });
    return { apiBase: base, ...data };
  } catch (error) {
    throw new Error(mensajeErrorLogin(error));
  }
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
