/**
 * api.js — Capa de servicios y cliente HTTP central de MedRec.
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const FAVORITES_STORAGE_KEY = 'medrec_favorites';
const SEARCH_HISTORY_STORAGE_KEY = 'medrec_search_history';

/**
 * Helper para verificar si localStorage está disponible.
 */
function canUseStorage() {
  return typeof window !== 'undefined' && typeof window.localStorage !== 'undefined';
}

/**
 * Lee un array de localStorage.
 */
function readStoredArray(key) {
  if (!canUseStorage()) return [];
  try {
    const raw = window.localStorage.getItem(key);
    const parsed = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

/**
 * Escribe un array en localStorage.
 */
function writeStoredArray(key, value) {
  if (!canUseStorage()) return;
  window.localStorage.setItem(key, JSON.stringify(value));
}

/**
 * Intenta refrescar el JWT silenciosamente.
 * Retorna el nuevo token si tiene éxito, o null si falla.
 * @returns {Promise<string|null>}
 */
async function _intentarRefresh() {
  const token = canUseStorage() ? window.localStorage.getItem('medrec_token') : null;
  if (!token) return null;
  try {
    const res = await fetch(`${API_BASE_URL}/auth/refresh`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
    });
    if (!res.ok) return null;
    const data = await res.json();
    if (data?.access_token) {
      window.localStorage.setItem('medrec_token', data.access_token);
      return data.access_token;
    }
    return null;
  } catch {
    return null;
  }
}

/** Flag para evitar bucles de refresh simultáneos */
let _refreshEnProceso = false;
let _refreshPromise = null;

/**
 * Realiza una petición HTTP con el token JWT si está disponible.
 * Si recibe un 401 intenta refrescar el token una sola vez antes de rendirse.
 */
export async function realizarPeticion(endpoint, opciones = {}, _esReintento = false) {
  const url = `${API_BASE_URL}${endpoint}`;

  const headers = { ...opciones.headers };
  if (!(opciones.body instanceof FormData) && !headers['Content-Type']) {
    headers['Content-Type'] = 'application/json';
  }

  if (canUseStorage()) {
    const token = window.localStorage.getItem('medrec_token');
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
  }

  const response = await fetch(url, {
    ...opciones,
    headers,
  });

  if (response.status === 401) {
    // Si ya es un reintento, la sesión definitivamente expiró
    if (_esReintento) {
      if (canUseStorage()) {
        window.localStorage.removeItem('medrec_token');
        window.localStorage.removeItem('medrec_user');
      }
      // Emitir evento global para que el contexto de auth lo maneje
      window.dispatchEvent(new CustomEvent('medrec:session-expired'));
      throw new Error('Sesión expirada. Por favor, inicia sesión nuevamente.');
    }

    // Primer intento — tratar de refrescar silenciosamente
    if (!_refreshEnProceso) {
      _refreshEnProceso = true;
      _refreshPromise = _intentarRefresh().finally(() => {
        _refreshEnProceso = false;
        _refreshPromise = null;
      });
    }

    const nuevoToken = await _refreshPromise;

    if (nuevoToken) {
      // Reintento con el token nuevo
      return realizarPeticion(endpoint, opciones, true);
    }

    // Refresh falló — sesión expirada
    if (canUseStorage()) {
      window.localStorage.removeItem('medrec_token');
      window.localStorage.removeItem('medrec_user');
    }
    window.dispatchEvent(new CustomEvent('medrec:session-expired'));
    throw new Error('Sesión expirada. Por favor, inicia sesión nuevamente.');
  }

  if (response.status === 404) {
    return null;
  }

  if (!response.ok) {
    let mensaje = `Error HTTP: ${response.status}`;
    try {
      const errorJson = await response.json();
      if (errorJson?.detail) {
        mensaje = typeof errorJson.detail === 'string' ? errorJson.detail : JSON.stringify(errorJson.detail);
      }
    } catch (_) { }
    throw new Error(mensaje);
  }

  return response.json();
}


/**
 * Petición base compatible con código existente.
 */
export const peticionBase = async (endpoint, opciones = {}) => {
  try {
    return await realizarPeticion(endpoint, opciones);
  } catch (error) {
    console.error("Error en la petición base:", error);
    throw error;
  }
};

/* ──────────────────────────────────────────────
   Re-exportar servicios especializados (Modularidad)
   ────────────────────────────────────────────── */
export {
  normalizeSpecialistsResponse,
  buscarEspecialistas,
  searchSpecialists,
  obtenerDetalleEspecialista,
  getSpecialistById,
  obtenerDetalleEspecialistaPorDoctoraliaId,
  obtenerOpinionesEspecialista
} from './especialistas.api';

export {
  getReviewSummary
} from './analisis.api';

export {
  buscarUbicaciones,
  getCiudades,
  getEstados,
} from './ubicaciones.api';

export {
  getOpiniones,
  calcularResumenOpiniones,
} from './opiniones.api';

export {
  listarTokensLLM,
  guardarTokenLLM,
  eliminarTokenLLM,
  scrapeAnalyze,
} from './llm.api';

/* ──────────────────────────────────────────────
   Autenticación y Perfil
   ────────────────────────────────────────────── */

/**
 * Inicia sesión con email y contraseña. Devuelve token y datos del usuario.
 */
export async function iniciarSesion(email, password) {
  const data = await realizarPeticion('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  });

  if (data?.access_token) {
    if (canUseStorage()) {
      window.localStorage.setItem('medrec_token', data.access_token);
    }
    // Obtener datos del perfil tras loguearse
    const perfil = await obtenerPerfilUsuario();
    if (canUseStorage()) {
      window.localStorage.setItem('medrec_user', JSON.stringify(perfil));
    }

    // Cargar favoritos del backend al iniciar sesión
    try {
      const favs = await listarFavoritos();
      const favIds = (favs?.favoritos || favs || []).map(f => f.especialista?._id || f.medico_id || f._id);
      writeStoredArray(FAVORITES_STORAGE_KEY, favIds.filter(Boolean));
    } catch (e) {
      console.error("Error al precargar favoritos en login", e);
    }

    return { token: data.access_token, user: perfil };
  }
  throw new Error("No se recibió token de acceso.");
}

/**
 * Registra un nuevo usuario en la base de datos.
 */
export async function registrarUsuario(email, password, extraFields = {}) {
  return realizarPeticion('/auth/register', {
    method: 'POST',
    body: JSON.stringify({ email, password, ...extraFields }),
  });
}

/**
 * Obtiene el perfil del usuario autenticado.
 */
export async function obtenerPerfilUsuario() {
  return realizarPeticion('/usuarios/me');
}

/**
 * Actualiza los datos básicos del perfil.
 */
export async function actualizarPerfilUsuario(datos) {
  const res = await realizarPeticion('/usuarios/me', {
    method: 'PATCH',
    body: JSON.stringify(datos),
  });
  if (canUseStorage()) {
    window.localStorage.setItem('medrec_user', JSON.stringify(res));
  }
  return res;
}

/* ──────────────────────────────────────────────
   Direcciones del Usuario
   ────────────────────────────────────────────── */

/**
 * Lista las direcciones del usuario.
 */
export async function listarDirecciones() {
  return realizarPeticion('/usuarios/direcciones');
}

/**
 * Crea una dirección nueva.
 */
export async function crearDireccion(direccion) {
  return realizarPeticion('/usuarios/direcciones', {
    method: 'POST',
    body: JSON.stringify(direccion),
  });
}

/**
 * Actualiza parcialmente una dirección.
 */
export async function actualizarDireccion(id, direccion) {
  return realizarPeticion(`/usuarios/direcciones/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(direccion),
  });
}

/**
 * Elimina una dirección.
 */
export async function eliminarDireccion(id) {
  return realizarPeticion(`/usuarios/direcciones/${id}`, {
    method: 'DELETE',
  });
}

/* ──────────────────────────────────────────────
   Catálogos
   ────────────────────────────────────────────── */

/**
 * Obtiene lista de especialidades.
 */
export async function obtenerEspecialidades(query = '') {
  const data = await realizarPeticion(`/catalogos/especialidades${query ? `?q=${query}` : ''}`);
  return data;
}

/**
 * Obtiene lista de ciudades usando el endpoint de ubicaciones.
 * Soporta ciudades, alcaldías y estados.
 *
 * @param {string} [q=''] - Texto de búsqueda opcional
 * @returns {Promise<Object>} Respuesta del backend con lista de ubicaciones
 */
export async function obtenerCiudades(q = '') {
  const params = q ? `?q=${encodeURIComponent(q)}` : '';
  const data = await realizarPeticion(`/catalogos/ubicaciones${params}`);
  return data;
}

/**
 * Obtiene catálogos completos (ciudades y especialidades).
 */
export async function obtenerCatalogos() {
  const [especialidades, ciudades] = await Promise.all([
    obtenerEspecialidades(),
    obtenerCiudades(),
  ]);
  return { especialidades, ciudades };
}

/* ──────────────────────────────────────────────
   Favoritos
   ────────────────────────────────────────────── */

/**
 * Listar favoritos del usuario desde el backend.
 */
export async function listarFavoritos() {
  const token = canUseStorage() ? window.localStorage.getItem('medrec_token') : null;
  if (!token) {
    // Si no está autenticado, retornar estructura simulada basada en localStorage para no romper
    const favorites = readStoredArray(FAVORITES_STORAGE_KEY);
    const results = await Promise.allSettled(favorites.map((id) => realizarPeticion(`/especialistas/${id}`)));
    const items = results
      .filter((r) => r.status === 'fulfilled' && r.value)
      .map((r, index) => ({
        favorito_id: index + 1,
        guardado_en: new Date().toISOString(),
        especialista: r.value,
        medico_id: r.value._id
      }));
    return { total: items.length, favoritos: items };
  }

  // Si está autenticado, llamar backend
  const data = await realizarPeticion('/usuarios/favoritos');
  let items = [];
  if (Array.isArray(data)) {
    items = data;
  } else if (data && Array.isArray(data.favoritos)) {
    items = data.favoritos;
  }

  // Actualizar caché local de favoritos para que isFavorite() funcione síncronamente
  const favIds = items.map(f => f.especialista?._id || f.medico_id || f._id);
  writeStoredArray(FAVORITES_STORAGE_KEY, favIds.filter(Boolean));

  return {
    total: data.total ?? items.length,
    favoritos: items
  };
}

export const getFavoriteSpecialists = async () => {
  const response = await listarFavoritos();
  return response.favoritos.map(f => f.especialista).filter(Boolean);
};

/**
 * Guarda especialista como favorito.
 */
export async function agregarFavorito(medicoId) {
  const token = canUseStorage() ? window.localStorage.getItem('medrec_token') : null;

  // Guardar localmente
  const favorites = readStoredArray(FAVORITES_STORAGE_KEY);
  if (!favorites.includes(medicoId)) {
    writeStoredArray(FAVORITES_STORAGE_KEY, [...favorites, medicoId]);
  }

  if (!token) {
    return { success: true };
  }

  // Guardar en backend
  return realizarPeticion('/usuarios/favoritos', {
    method: 'POST',
    body: JSON.stringify({ medico_id: medicoId }),
  });
}

export const addFavorite = agregarFavorito;

/**
 * Elimina favorito.
 */
export async function eliminarFavorito(medicoId) {
  const token = canUseStorage() ? window.localStorage.getItem('medrec_token') : null;

  // Quitar localmente
  const favorites = readStoredArray(FAVORITES_STORAGE_KEY).filter((favId) => favId !== medicoId);
  writeStoredArray(FAVORITES_STORAGE_KEY, favorites);

  if (!token) {
    return { success: true };
  }

  // Quitar de backend
  return realizarPeticion(`/usuarios/favoritos/${medicoId}`, {
    method: 'DELETE',
  });
}

export const removeFavorite = eliminarFavorito;

/**
 * Comprueba si un especialista es favorito localmente.
 */
export function isFavorite(id) {
  return readStoredArray(FAVORITES_STORAGE_KEY).includes(id);
}

/* ──────────────────────────────────────────────
   Historial
   ────────────────────────────────────────────── */

/**
 * Listar historial de búsqueda.
 */
export async function listarHistorial(page = 1, limit = 20) {
  const token = canUseStorage() ? window.localStorage.getItem('medrec_token') : null;
  if (!token) {
    return readStoredArray(SEARCH_HISTORY_STORAGE_KEY);
  }

  return realizarPeticion(`/usuarios/historial?page=${page}&limit=${limit}`);
}

export const getSearchHistory = async (filtrosLocales = {}) => {
  const token = canUseStorage() ? window.localStorage.getItem('medrec_token') : null;
  let history = [];

  if (token) {
    const data = await listarHistorial(1, 100);
    history = Array.isArray(data) ? data : (data.results || data.historial || []);
  } else {
    history = readStoredArray(SEARCH_HISTORY_STORAGE_KEY);
  }

  if (filtrosLocales.especialidad) {
    const esp = filtrosLocales.especialidad.toLowerCase();
    history = history.filter((entry) =>
      String(entry.especialidad || '').toLowerCase().includes(esp)
    );
  }

  if (filtrosLocales.fechaDesde) {
    const desde = new Date(filtrosLocales.fechaDesde);
    history = history.filter((entry) => new Date(entry.fecha || entry.created_at) >= desde);
  }

  if (filtrosLocales.fechaHasta) {
    const hasta = new Date(filtrosLocales.fechaHasta);
    history = history.filter((entry) => new Date(entry.fecha || entry.created_at) <= hasta);
  }

  return history;
};

/**
 * Guarda una búsqueda en el historial.
 */
export async function guardarBusquedaHistorial(busqueda) {
  const token = canUseStorage() ? window.localStorage.getItem('medrec_token') : null;

  const nuevoItem = {
    id: String(Date.now()),
    query: busqueda.consulta_texto || busqueda.especialidad || '',
    especialidad: busqueda.especialidad || '',
    ciudad: busqueda.ubicacion || '',
    fecha: new Date().toISOString(),
    created_at: new Date().toISOString(),
    filtros: busqueda.filtros || {},
    origen: busqueda.origen || 'tradicional',
    total_resultados: busqueda.total_resultados || 0
  };

  // Guardar local
  const history = readStoredArray(SEARCH_HISTORY_STORAGE_KEY);
  writeStoredArray(SEARCH_HISTORY_STORAGE_KEY, [nuevoItem, ...history].slice(0, 50));

  if (!token) {
    return nuevoItem;
  }

  // Guardar en backend
  return realizarPeticion('/usuarios/historial', {
    method: 'POST',
    body: JSON.stringify(busqueda),
  });
}

/**
 * Limpia todo el historial.
 */
export async function limpiarHistorial() {
  const token = canUseStorage() ? window.localStorage.getItem('medrec_token') : null;

  writeStoredArray(SEARCH_HISTORY_STORAGE_KEY, []);

  if (!token) {
    return { success: true };
  }

  return realizarPeticion('/usuarios/historial', {
    method: 'DELETE',
  });
}

/* ──────────────────────────────────────────────
   Chat
   ────────────────────────────────────────────── */

/**
 * Envía el historial del chat al backend.
 */
export async function chatMessage(history = []) {
  const messages = Array.isArray(history)
    ? history
      .filter((msg) => msg?.role && typeof msg?.content === 'string')
      .map(({ role, content }) => ({ role, content }))
    : [];

  const consulta = messages[messages.length - 1]?.content?.trim() ?? '';

  if (!consulta) {
    throw new Error('No hay mensaje para enviar al chat');
  }

  const token = canUseStorage() ? window.localStorage.getItem('medrec_token') : null;
  const endpoint = token ? '/chat/interpretar/auth' : '/chat/interpretar';

  const data = await realizarPeticion(endpoint, {
    method: 'POST',
    body: JSON.stringify({
      consulta,
      messages,
      provider: 'auto',
      auto_search: false,
    }),
  });

  const filtros = data?.filtros ?? {};

  return {
    role: 'assistant',
    content: data?.mensaje ?? 'No pude procesar tu mensaje.',
    respuesta: Array.isArray(data?.respuesta) ? data.respuesta : ['Lo siento, hubo un error procesando el mensaje.'],
    especialidad: filtros?.especialidad ?? null,
    ciudad: filtros?.ubicacion ?? null,
    filtros: filtros,
    sql: data?.sql ?? null,
    ready: Boolean(data?.ready),
    suggestions: Array.isArray(data?.sugerencias) ? data.sugerencias : [],
    ubicaciones_usuario: Array.isArray(data?.ubicaciones_usuario) ? data.ubicaciones_usuario : [],
  };
}
