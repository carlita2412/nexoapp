import Dexie from "dexie";

const API_BASE = __NEXO_API_BASE__;

export const db = new Dexie("nexo_pwa_mapa");
db.version(1).stores({
  colecciones: "nombre, actualizado_en"
});

function normalizarColeccion(data) {
  if (Array.isArray(data)) return data;
  if (Array.isArray(data?.results)) return data.results;
  return [];
}

function tokenGuardado() {
  return localStorage.getItem("nexo_token") || "";
}

export function guardarToken(token) {
  const limpio = token.trim();
  if (limpio) localStorage.setItem("nexo_token", limpio);
  else localStorage.removeItem("nexo_token");
}

export function obtenerToken() {
  return tokenGuardado();
}

async function leerCache(nombre) {
  const fila = await db.colecciones.get(nombre);
  return fila?.data ?? [];
}

async function guardarCache(nombre, data) {
  await db.colecciones.put({
    nombre,
    data,
    actualizado_en: new Date().toISOString()
  });
}

async function pedirColeccion(nombre, ruta) {
  const headers = { Accept: "application/json" };
  const token = tokenGuardado();
  if (token) headers.Authorization = `Token ${token}`;

  try {
    const response = await fetch(`${API_BASE}${ruta}`, { headers });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = normalizarColeccion(await response.json());
    await guardarCache(nombre, data);
    return { data, origen: "red" };
  } catch (error) {
    const data = await leerCache(nombre);
    return { data, origen: data.length ? "cache" : "error", error };
  }
}

export async function cargarDatosMapa() {
  const [centros, necesidades, donaciones, catalogos] = await Promise.all([
    pedirColeccion("centros", "/centros-salud/"),
    pedirColeccion("necesidades", "/necesidades/"),
    pedirColeccion("donaciones", "/donaciones/"),
    pedirColeccion("catalogos", "/catalogos/")
  ]);

  return {
    centros: centros.data,
    necesidades: necesidades.data,
    donaciones: donaciones.data,
    catalogos: catalogos.data,
    origenes: {
      centros: centros.origen,
      necesidades: necesidades.origen,
      donaciones: donaciones.origen,
      catalogos: catalogos.origen
    },
    errores: [centros, necesidades, donaciones, catalogos]
      .filter((item) => item.origen === "error")
      .map((item) => item.error?.message || "Sin conexión")
  };
}

export async function limpiarCacheLocal() {
  await db.colecciones.clear();
}
