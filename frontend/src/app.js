import Alpine from 'alpinejs';
import { Workbox } from 'workbox-window';
import { db, cerrarSesionLocal, obtenerSesion, resumenCola } from './lib/db.js';
import { API_BASE_DEFECTO, loginToken, obtenerCandidatos } from './lib/api.js';
import { comprimirFoto } from './lib/foto.js';
import {
  encolarEvento,
  guardarFotoPendiente,
  sincronizarDeltas,
  sincronizarTodo,
  uuid,
  verificarOutboxManual,
} from './lib/sync.js';

const ahoraIso = () => new Date().toISOString();
const entero = (valor, defecto = 0) => Number.parseInt(valor || defecto, 10);

async function registrarServiceWorker() {
  if ('serviceWorker' in navigator) {
    const wb = new Workbox('/sw.js');
    wb.register();
  }
}

function estadoConexion() {
  return navigator.onLine ? 'en_linea' : 'offline';
}

Alpine.data('nexoApp', () => ({
  listo: false,
  online: navigator.onLine,
  pestaña: 'cola',
  mensaje: '',
  error: '',
  sesion: {
    apiBase: API_BASE_DEFECTO,
    token: null,
    usuario: null,
    rol: null,
    organizacion: null,
  },
  login: {
    apiBase: API_BASE_DEFECTO,
    username: '',
    password: '',
  },
  resumen: { pendientes: 0, sincronizados: 0, conflicto: 0, superada: 0, fotos: 0 },
  cola: [],
  fotos: [],
  catalogos: [],
  centros: [],
  organizaciones: [],
  necesidades: [],
  donaciones: [],
  asignaciones: [],
  envios: [],
  candidatos: [],
  formNecesidad: {
    centro: '',
    item: '',
    cantidad_solicitada: 1,
    nivel_triage: '2_urgente',
    requiere_electricidad: false,
    requiere_oxigeno: false,
    requiere_personal_entrenado: false,
  },
  formDonacion: {
    item: '',
    cantidad: 1,
    condicion: 'nuevo',
    ubicacion_texto: '',
    estado: 'disponible',
  },
  formMatching: {
    necesidad: '',
  },
  formEntrega: {
    asignacion: '',
    responsable: '',
    recibido_por: '',
    notas: '',
    geolocalizacion_entrega_texto: '',
    foto: null,
  },

  async init() {
    this.online = navigator.onLine;
    window.addEventListener('online', async () => {
      this.online = true;
      await this.sincronizarSilencioso();
    });
    window.addEventListener('offline', () => {
      this.online = false;
    });

    await registrarServiceWorker();
    this.sesion = await obtenerSesion();
    this.login.apiBase = this.sesion.apiBase || API_BASE_DEFECTO;
    await this.cargarLocal();
    this.listo = true;

    if (this.sesion.token && this.online) {
      await this.sincronizarSilencioso();
    }
  },

  get autenticado() {
    return Boolean(this.sesion.token);
  },

  get estadoConexionTexto() {
    return estadoConexion() === 'en_linea' ? 'En línea' : 'Modo avión / sin señal';
  },

  async iniciarSesion() {
    this.error = '';
    this.mensaje = '';
    try {
      const sesion = await loginToken(this.login);
      this.sesion = sesion;
      this.mensaje = 'Sesión guardada. La PWA ya puede operar offline.';
      await this.sincronizarSilencioso();
    } catch (error) {
      this.error = error.message;
    }
  },

  async cerrarSesion() {
    await cerrarSesionLocal();
    this.sesion = await obtenerSesion();
    this.mensaje = 'Sesión local cerrada.';
  },

  async cargarLocal() {
    const [
      resumen,
      cola,
      fotos,
      catalogos,
      centros,
      organizaciones,
      necesidades,
      donaciones,
      asignaciones,
      envios,
    ] = await Promise.all([
      resumenCola(),
      db.outbox.orderBy('creado_en').reverse().toArray(),
      db.fotos_pendientes.orderBy('creado_en').reverse().toArray(),
      db.catalogos.orderBy('nombre').toArray(),
      db.centros_salud.orderBy('nombre').toArray(),
      db.organizaciones.orderBy('nombre').toArray(),
      db.necesidades.orderBy('updated_at').reverse().toArray(),
      db.donaciones.orderBy('updated_at').reverse().toArray(),
      db.asignaciones.orderBy('updated_at').reverse().toArray(),
      db.envios.orderBy('updated_at').reverse().toArray(),
    ]);

    Object.assign(this, {
      resumen,
      cola,
      fotos,
      catalogos,
      centros,
      organizaciones,
      necesidades,
      donaciones,
      asignaciones,
      envios,
    });
  },

  nombreCatalogo(id) {
    return this.catalogos.find((item) => item.id === id)?.nombre || id;
  },

  fechaEvento(evento) {
    return evento.creado_en || evento.client_timestamp || '';
  },

  detalleEvento(evento) {
    if (evento.error) return evento.error;
    if (!evento.respuesta) return 'Pendiente de sincronizar.';
    if (evento.respuesta.mensaje) return evento.respuesta.mensaje;
    return JSON.stringify(evento.respuesta);
  },

  async refrescar() {
    await this.cargarLocal();
  },

  async crearNecesidad() {
    const id = uuid();
    const payload = {
      id,
      centro: this.formNecesidad.centro,
      item: this.formNecesidad.item,
      cantidad_solicitada: entero(this.formNecesidad.cantidad_solicitada, 1),
      nivel_triage: this.formNecesidad.nivel_triage,
      requisitos_operacion: {
        requiere_electricidad: this.formNecesidad.requiere_electricidad,
        requiere_oxigeno: this.formNecesidad.requiere_oxigeno,
        requiere_personal_entrenado: this.formNecesidad.requiere_personal_entrenado,
      },
      estado: 'abierta',
      reportada_por: this.sesion.organizacion,
      created_at: ahoraIso(),
      updated_at: ahoraIso(),
    };

    await db.necesidades.put(payload);
    await encolarEvento('necesidad', payload, { estado_local: 'abierta' });
    this.mensaje = 'Necesidad guardada localmente.';
    await this.refrescar();
  },

  async crearDonacion() {
    const id = uuid();
    const payload = {
      id,
      donante: this.sesion.organizacion,
      item: this.formDonacion.item,
      cantidad: entero(this.formDonacion.cantidad, 1),
      condicion: this.formDonacion.condicion,
      ubicacion_texto: this.formDonacion.ubicacion_texto,
      estado: this.formDonacion.estado,
      created_at: ahoraIso(),
      updated_at: ahoraIso(),
    };

    await db.donaciones.put(payload);
    await encolarEvento('donacion', payload, { estado_local: payload.estado });
    this.mensaje = 'Donación guardada localmente.';
    await this.refrescar();
  },

  async buscarCandidatos() {
    this.error = '';
    try {
      this.candidatos = await obtenerCandidatos(this.formMatching.necesidad);
    } catch (error) {
      this.error = error.message;
    }
  },

  async reclamar(donacion) {
    const id = uuid();
    const payload = {
      id,
      necesidad: this.formMatching.necesidad,
      donacion,
      cantidad_asignada: 1,
      organizacion_responsable: this.sesion.organizacion,
      estado_claim: 'tentativa',
      claim_ts_cliente: ahoraIso(),
      estado_logistico: 'pendiente',
      created_at: ahoraIso(),
      updated_at: ahoraIso(),
    };
    const evento = await encolarEvento('asignacion_claim', payload, { estado_local: 'tentativa' });
    await db.asignaciones.put({ ...payload, idempotency_key: evento.idempotency_key });
    this.mensaje = 'Claim tentativo guardado. Se arbitrará al sincronizar.';
    await this.refrescar();
  },

  seleccionarFoto(event) {
    this.formEntrega.foto = event.target.files?.[0] || null;
  },

  async confirmarEntrega() {
    const id = uuid();
    const payload = {
      id,
      asignacion: this.formEntrega.asignacion,
      estado: 'entregado',
      responsable: this.formEntrega.responsable,
      recibido_por: this.formEntrega.recibido_por,
      notas: this.formEntrega.notas,
      geolocalizacion_entrega_texto: this.formEntrega.geolocalizacion_entrega_texto,
      timestamp_entrega: ahoraIso(),
      created_at: ahoraIso(),
      updated_at: ahoraIso(),
    };

    await db.envios.put(payload);
    await encolarEvento('envio', payload, { estado_local: 'entregado' });

    if (this.formEntrega.foto) {
      const blob = await comprimirFoto(this.formEntrega.foto);
      await guardarFotoPendiente({ idempotencyKey: uuid(), envio: id, blob });
    }

    this.mensaje = 'Entrega y foto guardadas localmente.';
    await this.refrescar();
  },

  async descargarDeltas() {
    this.error = '';
    try {
      await sincronizarDeltas();
      this.mensaje = 'Deltas descargados.';
      await this.refrescar();
    } catch (error) {
      this.error = error.message;
    }
  },

  async sincronizarManual() {
    this.error = '';
    try {
      await sincronizarTodo();
      this.mensaje = 'Cola sincronizada.';
      await this.refrescar();
    } catch (error) {
      this.error = error.message;
    }
  },

  async reintentarSincronizacionManual() {
    this.error = '';
    try {
      await sincronizarTodo();
      this.mensaje = 'Reintento manual completado.';
      await this.refrescar();
    } catch (error) {
      this.error = error.message;
      await this.refrescar();
    }
  },

  async sincronizarSilencioso() {
    try {
      await sincronizarTodo();
      await this.refrescar();
    } catch (_) {
      // La PWA sigue usable offline si falla la red o el backend.
    }
  },
}));

window.Alpine = Alpine;
window.nexoDebug = { db, sincronizarTodo, verificarOutboxManual };
Alpine.start();
