import Alpine from 'alpinejs';
import Dexie from 'dexie';

const db = new Dexie('nexo_campo');
db.version(1).stores({
  outbox: 'idempotency_key, entity, estado, client_timestamp',
  datos: 'clave',
  entidades: 'id, tipo, updated_at'
});

const uuid = () => crypto.randomUUID();
const ahora = () => new Date().toISOString();

async function guardarDato(clave, valor) {
  await db.datos.put({ clave, valor });
}

async function leerDato(clave, defecto = null) {
  const fila = await db.datos.get(clave);
  return fila ? fila.valor : defecto;
}

async function api(path, opciones = {}) {
  const base = await leerDato('apiBase', location.origin);
  const token = await leerDato('token');
  const headers = { ...(opciones.headers || {}) };
  if (token) headers.Authorization = `Token ${token}`;
  if (!(opciones.body instanceof FormData)) headers['Content-Type'] = headers['Content-Type'] || 'application/json';
  const respuesta = await fetch(`${base}${path}`, { ...opciones, headers });
  if (!respuesta.ok) throw new Error(`HTTP ${respuesta.status}`);
  return respuesta.json();
}

window.nexoApp = function nexoApp() {
  return {
    token: null,
    usuario: null,
    apiBase: location.origin,
    online: navigator.onLine,
    syncMensaje: 'Sin sincronizar',
    error: '',
    login: { username: '', password: '' },
    necesidades: [],
    donaciones: [],
    asignaciones: [],
    envios: [],
    candidatos: [],
    outbox: [],
    foto: null,

    async iniciar() {
      this.token = await leerDato('token');
      this.usuario = await leerDato('usuario');
      this.apiBase = await leerDato('apiBase', location.origin);
      await this.cargarLocal();
      await this.refrescarOutbox();
      window.addEventListener('online', () => { this.online = true; this.sincronizar(); });
      window.addEventListener('offline', () => { this.online = false; this.syncMensaje = 'Modo avion: guardando local'; });
      if (this.token && this.online) await this.sincronizar();
      if ('serviceWorker' in navigator) navigator.serviceWorker.register('/sw.js');
    },

    async hacerLogin() {
      this.error = '';
      try {
        await guardarDato('apiBase', this.apiBase.replace(/\/$/, ''));
        const data = await api('/api/v1/auth/token/', { method: 'POST', body: JSON.stringify(this.login) });
        this.token = data.token;
        this.usuario = { username: data.usuario || this.login.username, rol: data.rol, organizacion: data.organizacion };
        await guardarDato('token', this.token);
        await guardarDato('usuario', this.usuario);
        await this.sincronizar();
      } catch (e) {
        this.error = 'No se pudo iniciar sesion. Verifica usuario, clave y API.';
      }
    },

    estadoClase(estado) {
      if (estado === 'superada') return 'superada';
      if (estado === 'confirmada' || estado === 'ok' || estado === 'duplicado') return 'confirmada';
      return 'tentativa';
    },

    async cargarLocal() {
      const filas = await db.entidades.toArray();
      this.necesidades = filas.filter((x) => x.tipo === 'necesidad').map((x) => x.payload);
      this.donaciones = filas.filter((x) => x.tipo === 'donacion').map((x) => x.payload);
      this.asignaciones = filas.filter((x) => x.tipo === 'asignacion').map((x) => x.payload);
      this.envios = filas.filter((x) => x.tipo === 'envio').map((x) => x.payload);
    },

    async refrescarOutbox() {
      this.outbox = await db.outbox.orderBy('client_timestamp').toArray();
    },

    async encolar(entity, payload) {
      const evento = { idempotency_key: uuid(), client_timestamp: ahora(), entity, payload, estado: 'pendiente' };
      await db.outbox.put(evento);
      if (payload.id) await db.entidades.put({ id: payload.id, tipo: entity, updated_at: evento.client_timestamp, payload: { ...payload, estado_local: 'tentativa' } });
      await this.cargarLocal();
      await this.refrescarOutbox();
      if (this.online) await this.sincronizar();
    },

    async agregarDemo(tipo) {
      const payload = tipo === 'necesidad'
        ? { id: uuid(), cantidad_solicitada: 1, nivel_triage: '2_urgente', item_nombre: 'Pendiente de catalogo' }
        : { id: uuid(), cantidad: 1, estado: 'disponible', item_nombre: 'Pendiente de catalogo' };
      await this.encolar(tipo, payload);
    },

    async prepararClaim(necesidad) {
      const payload = { id: uuid(), necesidad: necesidad.id, cantidad_asignada: 1, estado_claim: 'tentativa', claim_ts_cliente: ahora(), organizacion_responsable: this.usuario?.organizacion };
      await this.encolar('asignacion', payload);
    },

    async verMatching() {
      const necesidad = this.necesidades[0];
      if (!necesidad || !this.online) {
        this.syncMensaje = 'Matching queda pendiente hasta recuperar senal.';
        return;
      }
      this.candidatos = await api(`/api/v1/necesidades/${necesidad.id}/candidatos/`);
    },

    fotoSeleccionada(evento) {
      this.foto = evento.target.files?.[0] || null;
    },

    async crearEnvio() {
      await this.encolar('envio', { id: uuid(), estado: 'preparando', responsable: this.usuario?.username || 'campo', foto_pendiente: Boolean(this.foto) });
    },

    async sincronizar() {
      if (!this.token || !this.online) return;
      this.syncMensaje = 'Sincronizando...';
      const pendientes = await db.outbox.toArray();
      if (pendientes.length) {
        const respuesta = await api('/api/v1/sync/', { method: 'POST', body: JSON.stringify({ eventos: pendientes }) });
        const resultados = respuesta.resultados || respuesta.eventos || [];
        for (const evento of pendientes) {
          const r = resultados.find((x) => x.idempotency_key === evento.idempotency_key) || {};
          const estado = r.estado || r.resultado || 'ok';
          if (['ok', 'duplicado', 'superada'].includes(estado)) await db.outbox.delete(evento.idempotency_key);
          else await db.outbox.update(evento.idempotency_key, { estado });
        }
      }
      try {
        const cursor = await leerDato('cursorSync', '');
        const delta = await api(`/api/v1/sync/${cursor ? `?desde=${encodeURIComponent(cursor)}` : ''}`);
        for (const tipo of ['necesidades', 'donaciones', 'asignaciones', 'envios']) {
          for (const item of delta[tipo] || []) await db.entidades.put({ id: item.id, tipo: tipo.slice(0, -2), updated_at: item.updated_at, payload: item });
        }
        if (delta.cursor) await guardarDato('cursorSync', delta.cursor);
      } catch (_) {}
      await this.cargarLocal();
      await this.refrescarOutbox();
      this.syncMensaje = `Cola pendiente: ${this.outbox.length}`;
    }
  };
};

window.Alpine = Alpine;
Alpine.start();
