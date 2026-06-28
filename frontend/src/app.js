import Alpine from 'alpinejs';
import { Workbox } from 'workbox-window';
import { db, cerrarSesionLocal, obtenerSesion, resumenCola } from './lib/db.js';
import { loginToken, obtenerCandidatos } from './lib/api.js';
import { comprimirFoto } from './lib/foto.js';
import {
  encolarEvento,
  guardarFotoPendiente,
  sincronizarDeltas,
  sincronizarTodo,
  uuid,
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
    apiBase: '/api/v1',
    token: null,
    usuario: null,
    rol: null,
    organizacion: null,
  },
  login: {
    apiBase: '/api/v1',
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
    this.login.apiBase = this.sesion.apiBase || '/api/v1';
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

    this.resumen = resumen;
    this.cola = cola;
    this.fotos = fotos;
    this.catalogos = catalogos;
    this.centros = centros;
    this.organizaciones = organizaciones;
    this.necesidades = necesidades;
    this.donaciones = donaciones;
    this.asignaciones = asignaciones;
    this.envios = envios;

    if (!this.formNecesidad.centro && centros[0]) this.formNecesidad.centro = centros[0].id;
    if (!this.formNecesidad.item && catalogos[0]) this.formNecesidad.item = catalogos[0].id;
    if (!this.formDonacion.item && catalogos[0]) this.formDonacion.item = catalogos[0].id;
    if (!this.formMatching.necesidad && necesidades[0]) this.formMatching.necesidad = necesidades[0].id;
    if (!this.formEntrega.asignacion && asignaciones[0]) this.formEntrega.asignacion = asignaciones[0].id;
  },

  nombreCatalogo(id) {
    return this.catalogos.find((item) => item.id === id)?.nombre || id;
  },

  nombreCentro(id) {
    return this.centros.find((centro) => centro.id === id)?.nombre || id;
  },

  nombreOrg(id) {
    return this.organizaciones.find((org) => org.id === id)?.nombre || id;
  },

  async sincronizarSilencioso() {
    try {
      await sincronizarTodo();
      await this.cargarLocal();
    } catch (_) {
      await this.cargarLocal();
    }
  },

  async sincronizarManual() {
    this.error = '';
    this.mensaje = '';
    try {
      await sincronizarTodo();
      await this.cargarLocal();
      this.mensaje = 'Sincronización completada.';
    } catch (error) {
      this.error = `No se pudo sincronizar ahora: ${error.message}`;
      await this.cargarLocal();
    }
  },

  async descargarDeltas() {
    this.error = '';
    try {
      await sincronizarDeltas();
      await this.cargarLocal();
      this.mensaje = 'Datos actualizados para trabajo offline.';
    } catch (error) {
      this.error = error.message;
    }
  },

  async crearNecesidad() {
    this.error = '';
    const id = uuid();
    const payload = {
      id,
      centro: this.formNecesidad.centro,
      item: this.formNecesidad.item,
      cantidad_solicitada: entero(this.formNecesidad.cantidad_solicitada, 1),
      cantidad_cubierta: 0,
      nivel_triage: this.formNecesidad.nivel_triage,
      requisitos_operacion: {
        requiere_electricidad: Boolean(this.formNecesidad.requiere_electricidad),
        requiere_oxigeno: Boolean(this.formNecesidad.requiere_oxigeno),
        requiere_personal_entrenado: Boolean(this.formNecesidad.requiere_personal_entrenado),
      },
      estado: 'abierta',
      reportada_por: this.sesion.organizacion,
    };

    if (!payload.centro || !payload.item || !payload.reportada_por) {
      this.error = 'Faltan centro, item u organización del usuario.';
      return;
    }

    await encolarEvento('necesidad', payload);
    await db.necesidades.put({ ...payload, version: 1, created_at: ahoraIso(), updated_at: ahoraIso() });
    this.mensaje = 'Necesidad guardada localmente y agregada a la cola.';
    this.formMatching.necesidad = id;
    await this.cargarLocal();
  },

  async crearDonacion() {
    this.error = '';
    const id = uuid();
    const payload = {
      id,
      donante: this.sesion.organizacion,
      item: this.formDonacion.item,
      cantidad: entero(this.formDonacion.cantidad, 1),
      condicion: this.formDonacion.condicion,
      vencimiento: null,
      certificacion: '',
      ubicacion_actual: null,
      ubicacion_texto: this.formDonacion.ubicacion_texto,
      estado: this.formDonacion.estado,
    };

    if (!payload.donante || !payload.item) {
      this.error = 'Faltan item u organización donante.';
      return;
    }

    await encolarEvento('donacion', payload);
    await db.donaciones.put({ ...payload, version: 1, created_at: ahoraIso(), updated_at: ahoraIso() });
    this.mensaje = 'Donación guardada localmente y agregada a la cola.';
    await this.cargarLocal();
  },

  candidatosOffline(necesidad) {
    if (!necesidad) return [];
    return this.donaciones
      .filter((donacion) => donacion.item === necesidad.item)
      .filter((donacion) => ['disponible', 'registrada'].includes(donacion.estado))
      .map((donacion) => ({
        id: donacion.id,
        item: this.nombreCatalogo(donacion.item),
        donante: this.nombreOrg(donacion.donante),
        cantidad_disponible: donacion.cantidad,
        condicion: donacion.condicion,
        ubicacion_texto: donacion.ubicacion_texto || 'Sin ubicación',
        compatible: donacion.condicion !== 'requiere_reparacion',
        motivo: donacion.condicion === 'requiere_reparacion'
          ? 'Requiere reparación antes de asignar.'
          : 'Coincide por catálogo local. Validación final en servidor al sincronizar.',
        puntaje: donacion.condicion === 'nuevo' ? 90 : 70,
      }));
  },

  async buscarCandidatos() {
    this.error = '';
    const necesidad = this.necesidades.find((n) => n.id === this.formMatching.necesidad);
    if (!necesidad) {
      this.error = 'Selecciona una necesidad.';
      return;
    }

    if (this.online && !this.cola.some((e) => e.payload?.id === necesidad.id && e.estado === 'pendiente')) {
      try {
        const data = await obtenerCandidatos(necesidad.id);
        this.candidatos = data.candidatos || [];
        return;
      } catch (_) {
        // Si falla la red, cae a matching local.
      }
    }

    this.candidatos = this.candidatosOffline(necesidad);
  },

  async reclamar(donacionId) {
    const necesidad = this.necesidades.find((n) => n.id === this.formMatching.necesidad);
    const donacion = this.donaciones.find((d) => d.id === donacionId) || this.candidatos.find((d) => d.id === donacionId);
    if (!necesidad || !donacion) {
      this.error = 'No se pudo identificar necesidad o donación.';
      return;
    }

    const pendiente = Math.max(1, entero(necesidad.cantidad_solicitada, 1) - entero(necesidad.cantidad_cubierta, 0));
    const disponible = entero(donacion.cantidad || donacion.cantidad_disponible, 1);
    const cantidad = Math.min(pendiente, disponible);

    await encolarEvento('claim_necesidad', {
      necesidad: necesidad.id,
      donacion: donacionId,
      cantidad_asignada: cantidad,
      organizacion_responsable: this.sesion.organizacion,
    });

    this.mensaje = 'Claim guardado en outbox. El servidor lo arbitrará al sincronizar.';
    await this.cargarLocal();
  },

  seleccionarFoto(evento) {
    this.formEntrega.foto = evento.target.files?.[0] || null;
  },

  async confirmarEntrega() {
    this.error = '';
    const id = uuid();
    const payload = {
      id,
      asignacion: this.formEntrega.asignacion,
      estado: 'entregado',
      responsable: this.formEntrega.responsable,
      foto_confirmacion_ref: '',
      geolocalizacion_entrega: null,
      geolocalizacion_entrega_texto: this.formEntrega.geolocalizacion_entrega_texto,
      timestamp_entrega: ahoraIso(),
      recibido_por: this.formEntrega.recibido_por,
      notas: this.formEntrega.notas,
    };

    if (!payload.asignacion || !payload.responsable) {
      this.error = 'Selecciona asignación e indica responsable.';
      return;
    }

    await encolarEvento('envio', payload);
    await db.envios.put({ ...payload, version: 1, created_at: ahoraIso(), updated_at: ahoraIso() });

    if (this.formEntrega.foto) {
      const blob = await comprimirFoto(this.formEntrega.foto);
      await guardarFotoPendiente({
        idempotencyKey: uuid(),
        envio: id,
        blob,
      });
    }

    this.mensaje = 'Entrega guardada localmente. La foto queda en cola separada.';
    this.formEntrega.responsable = '';
    this.formEntrega.recibido_por = '';
    this.formEntrega.notas = '';
    this.formEntrega.geolocalizacion_entrega_texto = '';
    this.formEntrega.foto = null;
    await this.cargarLocal();
  },
}));

window.Alpine = Alpine;
Alpine.start();
