import "leaflet/dist/leaflet.css";
import L from "leaflet";
import Alpine from "alpinejs";
import { Workbox } from "workbox-window";
import {
  cargarDatosMapa,
  guardarToken,
  limpiarCacheLocal,
  obtenerToken
} from "./api";

const TILE_HOST = __NEXO_TILE_HOST__;
const MAPA_CENTRO_INICIAL = [8.2, -66.2];
const ZOOM_INICIAL = 6;
const ZOOM_MAXIMO = 13;
const ZOOM_MINIMO = 5;

const etiquetasTriage = {
  "1_critico": "1 - Critico",
  "2_urgente": "2 - Urgente",
  "3_importante": "3 - Importante",
  "4_rutinario": "4 - Rutinario"
};

function puntoValido(punto) {
  if (!punto) return null;
  if (Array.isArray(punto) && punto.length >= 2) {
    return { lon: Number(punto[0]), lat: Number(punto[1]) };
  }
  if (Array.isArray(punto?.coordinates) && punto.coordinates.length >= 2) {
    return { lon: Number(punto.coordinates[0]), lat: Number(punto.coordinates[1]) };
  }
  if (punto.lat !== undefined && (punto.lon !== undefined || punto.lng !== undefined)) {
    return { lon: Number(punto.lon ?? punto.lng), lat: Number(punto.lat) };
  }
  return null;
}

function esCoordenadaUsable(punto) {
  return (
    punto &&
    Number.isFinite(punto.lat) &&
    Number.isFinite(punto.lon) &&
    Math.abs(punto.lat) <= 90 &&
    Math.abs(punto.lon) <= 180
  );
}

function textoCatalogo(catalogos, id) {
  return catalogos.find((item) => item.id === id)?.nombre ?? id ?? "Sin item";
}

function textoCentro(centros, id) {
  return centros.find((centro) => centro.id === id)?.nombre ?? "Centro no sincronizado";
}

function markerHtml(clase) {
  return `<span class="nexo-marker ${clase}" aria-hidden="true"></span>`;
}

function icono(clase) {
  return L.divIcon({
    className: "",
    html: markerHtml(clase),
    iconSize: [24, 24],
    iconAnchor: [12, 12],
    popupAnchor: [0, -10]
  });
}

function popupCentro(centro) {
  return `
    <h3>${centro.nombre}</h3>
    <p><strong>Tipo:</strong> ${centro.tipo}</p>
    <p><strong>Estado:</strong> ${centro.estado_operativo}</p>
    <p><strong>Ubicacion:</strong> ${centro.municipio}, ${centro.estado}</p>
    <p><strong>Capacidades:</strong> ${[
      centro.tiene_electricidad ? "electricidad" : null,
      centro.tiene_agua ? "agua" : null,
      centro.tiene_oxigeno ? "oxigeno" : null,
      centro.tiene_personal_tecnico ? "personal tecnico" : null
    ].filter(Boolean).join(", ") || "sin capacidades registradas"}</p>
  `;
}

function popupNecesidad(necesidad, centros, catalogos) {
  return `
    <h3>${textoCatalogo(catalogos, necesidad.item)}</h3>
    <p><strong>Triage:</strong> ${etiquetasTriage[necesidad.nivel_triage] ?? necesidad.nivel_triage}</p>
    <p><strong>Centro:</strong> ${textoCentro(centros, necesidad.centro)}</p>
    <p><strong>Solicitado:</strong> ${necesidad.cantidad_solicitada}</p>
    <p><strong>Cubierto:</strong> ${necesidad.cantidad_cubierta}</p>
    <p><strong>Estado:</strong> ${necesidad.estado}</p>
  `;
}

function popupDonacion(donacion, catalogos) {
  return `
    <h3>${textoCatalogo(catalogos, donacion.item)}</h3>
    <p><strong>Cantidad:</strong> ${donacion.cantidad}</p>
    <p><strong>Condicion:</strong> ${donacion.condicion}</p>
    <p><strong>Estado:</strong> ${donacion.estado}</p>
    <p><strong>Ubicacion:</strong> ${donacion.ubicacion_texto || "coordenada registrada"}</p>
  `;
}

function crearCapaTiles(modoAhorro) {
  return L.tileLayer(`${TILE_HOST}/{z}/{x}/{y}.png`, {
    maxZoom: modoAhorro ? 11 : ZOOM_MAXIMO,
    minZoom: ZOOM_MINIMO,
    updateWhenIdle: true,
    keepBuffer: modoAhorro ? 1 : 2,
    crossOrigin: true,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
  });
}

function crearControlDatos() {
  const control = L.control({ position: "bottomleft" });
  control.onAdd = () => {
    const div = L.DomUtil.create("div", "rounded-xl bg-white/95 p-2 text-xs shadow");
    div.innerHTML = "Modo ahorro: zoom maximo limitado, tiles cacheados y carga solo al detener el mapa.";
    return div;
  };
  return control;
}

function registrarServiceWorker() {
  if ("serviceWorker" in navigator) {
    const wb = new Workbox("/sw.js");
    wb.register().catch(() => undefined);
  }
}

Alpine.data("mapaNexo", () => ({
  mapa: null,
  capaTiles: null,
  capas: {},
  filtros: {
    centros: true,
    necesidades: true,
    donaciones: true,
    triage: "todos",
    soloDisponibles: true,
    ahorroDatos: true
  },
  estado: "Listo para sincronizar",
  token: obtenerToken(),
  resumen: {
    centros: 0,
    necesidades: 0,
    donaciones: 0,
    origen: "sin datos"
  },
  datos: {
    centros: [],
    necesidades: [],
    donaciones: [],
    catalogos: []
  },

  async init() {
    registrarServiceWorker();
    this.iniciarMapa();
    await this.sincronizar();
  },

  iniciarMapa() {
    this.mapa = L.map("mapa-nexo", {
      zoomControl: true,
      preferCanvas: true,
      minZoom: ZOOM_MINIMO,
      maxZoom: ZOOM_MAXIMO
    }).setView(MAPA_CENTRO_INICIAL, ZOOM_INICIAL);

    this.capaTiles = crearCapaTiles(this.filtros.ahorroDatos).addTo(this.mapa);
    crearControlDatos().addTo(this.mapa);

    this.capas = {
      centros: L.layerGroup().addTo(this.mapa),
      necesidades: L.layerGroup().addTo(this.mapa),
      donaciones: L.layerGroup().addTo(this.mapa)
    };
  },

  async sincronizar() {
    this.estado = navigator.onLine ? "Sincronizando datos..." : "Sin conexion: usando cache local";
    const resultado = await cargarDatosMapa();
    this.datos = resultado;
    this.resumen = {
      centros: resultado.centros.length,
      necesidades: resultado.necesidades.length,
      donaciones: resultado.donaciones.filter((d) => d.estado === "disponible").length,
      origen: Object.values(resultado.origenes).includes("red") ? "red/cache" : "cache"
    };
    this.estado = resultado.errores.length
      ? "No se pudo contactar la API; mostrando datos locales si existen."
      : `Datos cargados desde ${this.resumen.origen}.`;
    this.renderizar();
  },

  guardarTokenLocal() {
    guardarToken(this.token);
    this.sincronizar();
  },

  async borrarCache() {
    await limpiarCacheLocal();
    this.estado = "Cache local de datos limpiado. Los tiles se purgan por limite automatico.";
    await this.sincronizar();
  },

  cambiarAhorroDatos() {
    if (this.capaTiles) this.mapa.removeLayer(this.capaTiles);
    this.capaTiles = crearCapaTiles(this.filtros.ahorroDatos).addTo(this.mapa);
    this.mapa.setMaxZoom(this.filtros.ahorroDatos ? 11 : ZOOM_MAXIMO);
  },

  renderizar() {
    Object.values(this.capas).forEach((capa) => capa.clearLayers());
    const bounds = [];

    if (this.filtros.centros) {
      this.datos.centros.forEach((centro) => {
        const punto = puntoValido(centro.geolocalizacion);
        if (!esCoordenadaUsable(punto)) return;
        L.marker([punto.lat, punto.lon], { icon: icono("nexo-marker-centro") })
          .bindPopup(popupCentro(centro))
          .addTo(this.capas.centros);
        bounds.push([punto.lat, punto.lon]);
      });
    }

    if (this.filtros.necesidades) {
      this.datos.necesidades
        .filter((necesidad) => ["abierta", "parcial"].includes(necesidad.estado))
        .filter((necesidad) => this.filtros.triage === "todos" || necesidad.nivel_triage === this.filtros.triage)
        .forEach((necesidad) => {
          const centro = this.datos.centros.find((item) => item.id === necesidad.centro);
          const punto = puntoValido(centro?.geolocalizacion);
          if (!esCoordenadaUsable(punto)) return;
          const clase = `nexo-marker-triage-${necesidad.nivel_triage?.charAt(0) || "4"}`;
          L.marker([punto.lat, punto.lon], { icon: icono(clase) })
            .bindPopup(popupNecesidad(necesidad, this.datos.centros, this.datos.catalogos))
            .addTo(this.capas.necesidades);
          bounds.push([punto.lat, punto.lon]);
        });
    }

    if (this.filtros.donaciones) {
      this.datos.donaciones
        .filter((donacion) => !this.filtros.soloDisponibles || donacion.estado === "disponible")
        .forEach((donacion) => {
          const punto = puntoValido(donacion.ubicacion_actual);
          if (!esCoordenadaUsable(punto)) return;
          L.marker([punto.lat, punto.lon], { icon: icono("nexo-marker-donacion") })
            .bindPopup(popupDonacion(donacion, this.datos.catalogos))
            .addTo(this.capas.donaciones);
          bounds.push([punto.lat, punto.lon]);
        });
    }

    if (bounds.length) {
      this.mapa.fitBounds(bounds, { padding: [24, 24], maxZoom: this.filtros.ahorroDatos ? 10 : 12 });
    }
  }
}));

window.Alpine = Alpine;
Alpine.start();
