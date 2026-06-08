/**
 * api.js — Capa de servicios de MedRec.
 * Conexión con backend real en API_BASE_URL.
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
 * Realiza una petición HTTP con el token JWT si está disponible.
 */
export async function realizarPeticion(endpoint, opciones = {}) {
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
    if (canUseStorage()) {
      window.localStorage.removeItem('medrec_token');
      window.localStorage.removeItem('medrec_user');
    }
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
    } catch (_) {}
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

/**
 * Normaliza la respuesta del endpoint /especialistas/.
 * Asegura que devuelva tanto `results` como `especialistas` para compatibilidad.
 */
export function normalizeSpecialistsResponse(response) {
  if (!response) {
    return { total: 0, page: 1, limit: 12, pages: 0, results: [], especialistas: [] };
  }

  let results = [];
  let total = 0;
  let page = 1;
  let limit = 12;
  let pages = 0;

  if (Array.isArray(response)) {
    results = response;
    total = response.length;
    limit = response.length;
    pages = 1;
  } else if (Array.isArray(response.results)) {
    results = response.results;
    total = response.total ?? response.results.length;
    page = response.page ?? 1;
    limit = response.limit ?? response.results.length;
    pages = response.pages ?? 1;
  } else if (Array.isArray(response.especialistas)) {
    results = response.especialistas;
    total = response.total ?? response.especialistas.length;
    page = response.page ?? 1;
    limit = response.limit ?? response.especialistas.length;
    pages = response.pages ?? 1;
  }

  return {
    total,
    page,
    limit,
    pages,
    results,
    especialistas: results
  };
}

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
export async function registrarUsuario(email, password) {
  return realizarPeticion('/auth/register', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
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
 * Obtiene lista de ciudades.
 */
export async function obtenerCiudades(query = '') {
  const data = await realizarPeticion(`/catalogos/ciudades${query ? `?q=${query}` : ''}`);
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
   Especialistas y Opiniones
   ────────────────────────────────────────────── */

/**
 * Convierte filtros del frontend a query params del backend.
 */
function buildSpecialistQuery(filters) {
  const params = new URLSearchParams();

  if (filters.especialidad) params.set('especialidad', filters.especialidad);
  if (filters.ciudad) params.set('ciudad', filters.ciudad);
  if (filters.q) params.set('q', filters.q);

  // Pacientes
  if (filters.tipoPaciente && filters.tipoPaciente !== 'todos') {
    const pacMap = {
      ninos: 'atiende_ninos',
      adultos: 'atiende_adultos',
      adolescentes: 'atiende_adolescentes',
    };
    filters.tipoPaciente.split(',').forEach((val) => {
      const backendKey = pacMap[val.trim()];
      if (backendKey) params.set(backendKey, 'true');
    });
  }

  if (filters.orden) params.set('orden', filters.orden);
  if (filters.confiabilidad) params.set('confiabilidad', filters.confiabilidad);

  if (filters.soloAnalizados) params.set('solo_analizados', 'true');
  if (filters.soloConOpiniones) params.set('solo_con_opiniones', 'true');

  if (filters.page != null) params.set('page', String(filters.page));
  if (filters.limit != null) params.set('limit', String(filters.limit));

  // Filtros adicionales si existen
  if (filters.ratingMin != null) params.set('rating_min', String(filters.ratingMin));
  if (filters.ratingMax != null) params.set('rating_max', String(filters.ratingMax));
  if (filters.puntuacionMin != null) params.set('puntuacion_min', String(filters.puntuacionMin));
  if (filters.puntuacionMax != null) params.set('puntuacion_max', String(filters.puntuacionMax));
  if (filters.precioMin != null) params.set('precio_min', String(filters.precioMin));
  if (filters.precioMax != null) params.set('precio_max', String(filters.precioMax));

  return params.toString();
}

/**
 * Busca especialistas con filtros reales en backend.
 */
export async function buscarEspecialistas(filtros = {}) {
  const query = buildSpecialistQuery(filtros);
  const url = `/especialistas/${query ? `?${query}` : ''}`;
  const data = await realizarPeticion(url);
  return normalizeSpecialistsResponse(data);
}

// Alias de compatibilidad
export const searchSpecialists = buscarEspecialistas;

/**
 * Obtiene detalle completo de un especialista por ID.
 */
export async function obtenerDetalleEspecialista(id) {
  if (!id) return null;
  return realizarPeticion(`/especialistas/${id}`);
}

// Alias de compatibilidad
export const getSpecialistById = obtenerDetalleEspecialista;

/**
 * Obtiene especialista por ID de Doctoralia.
 */
export async function obtenerDetalleEspecialistaPorDoctoraliaId(doctoraliaId) {
  if (!doctoraliaId) return null;
  return realizarPeticion(`/especialistas/doctoralia/${doctoraliaId}`);
}

/**
 * Obtiene opiniones de un especialista paginadas y filtradas.
 */
export async function obtenerOpinionesEspecialista(id, params = {}) {
  const qParams = new URLSearchParams();
  if (params.page) qParams.set('page', String(params.page));
  if (params.limit) qParams.set('limit', String(params.limit));
  if (params.orden) qParams.set('orden', params.orden);
  if (params.ratingMin) qParams.set('rating_min', String(params.ratingMin));
  if (params.ratingMax) qParams.set('rating_max', String(params.ratingMax));
  if (params.soloVerificadas) qParams.set('solo_verificadas', 'true');
  if (params.servicio) qParams.set('servicio', params.servicio);

  const query = qParams.toString();
  return realizarPeticion(`/especialistas/${id}/opiniones${query ? `?${query}` : ''}`);
}

/**
 * Obtiene el resumen de IA para compatibilidad.
 */
export async function getReviewSummary(id) {
  const specialist = await obtenerDetalleEspecialista(id);
  return specialist?.analisis?.resumen || 'Sin reseñas disponibles para este especialista.';
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
    const results = await Promise.allSettled(favorites.map((id) => obtenerDetalleEspecialista(id)));
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
  // Normalizar respuesta
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
    // Retorno simulado local si no hay auth
    return readStoredArray(SEARCH_HISTORY_STORAGE_KEY);
  }

  return realizarPeticion(`/usuarios/historial?page=${page}&limit=${limit}`);
}

export const getSearchHistory = async (filtrosLocales = {}) => {
  const token = canUseStorage() ? window.localStorage.getItem('medrec_token') : null;
  let history = [];
  
  if (token) {
    const data = await listarHistorial(1, 100);
    // El backend retorna { total, results } o array directo
    history = Array.isArray(data) ? data : (data.results || data.historial || []);
  } else {
    history = readStoredArray(SEARCH_HISTORY_STORAGE_KEY);
  }

  // Filtros locales para el dashboard (compatibilidad)
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

  const data = await realizarPeticion('/chat/interpretar', {
    method: 'POST',
    body: JSON.stringify({
      consulta,
      messages,
      provider: 'auto',
      auto_search: false,
    }),
  });

  const detected = data?.detected ?? {};
  const searchParams = data?.search_params ?? {};

  return {
    role: 'assistant',
    content: data?.reply ?? 'No pude procesar tu mensaje.',
    especialidad: searchParams.especialidad ?? detected.especialidad_slug ?? null,
    ciudad: searchParams.ciudad ?? detected.ciudad_slug ?? null,
    ready: Boolean(data?.ready),
    suggestions: Array.isArray(data?.suggestions) ? data.suggestions : [],
    missingFields: Array.isArray(data?.missing_fields) ? data.missing_fields : [],
    safety: data?.safety ?? null,
  };
}
