/**
 * especialistas.api.js — Servicios API para la colección doctor_profiles.
 *
 * Adapta el cliente a la nueva estructura de la BD Doctoralia donde:
 * - Los perfiles están en `doctor_profiles` con campos anidados bajo `doctor.*`.
 * - Las opiniones están en `doctor_opinions` con `doctor_id` entero.
 * - Los análisis están en `analisis_especialistas` con `id_doctoralia`.
 */

import { realizarPeticion } from './api';

/**
 * Normaliza la respuesta del endpoint GET /especialistas/.
 * Compatible con el esquema de doctor_profiles de la BD Doctoralia.
 * Asegura que siempre retorne { total, page, limit, pages, results, especialistas }.
 *
 * @param {*} response - Respuesta cruda del backend
 * @returns {{ total: number, page: number, limit: number, pages: number, results: Array, especialistas: Array }}
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

  return { total, page, limit, pages, results, especialistas: results };
}

/**
 * Construye los query params del backend a partir de los filtros del frontend.
 *
 * @param {Object} filtros - Filtros del formulario de búsqueda
 * @param {string} [filtros.especialidad] - Nombre o slug de especialidad
 * @param {string} [filtros.ciudad] - Ciudad, alcaldía o estado
 * @param {string} [filtros.q] - Búsqueda textual por nombre
 * @param {string} [filtros.orden] - Criterio de ordenamiento
 * @param {string} [filtros.tipoPaciente] - ninos|adultos|adolescentes|todos
 * @param {boolean} [filtros.soloAnalizados] - Solo con análisis IA
 * @param {boolean} [filtros.soloConOpiniones] - Solo con opiniones
 * @param {number}  [filtros.page] - Página actual
 * @param {number}  [filtros.limit] - Resultados por página
 * @returns {string} Query string codificado
 */
function buildSpecialistQuery(filtros) {
  const params = new URLSearchParams();

  if (filtros.especialidad) params.set('especialidad', filtros.especialidad);
  if (filtros.ciudad)        params.set('ciudad', filtros.ciudad);
  if (filtros.q)             params.set('q', filtros.q);

  // Tipo de paciente
  if (filtros.tipoPaciente && filtros.tipoPaciente !== 'todos') {
    const pacMap = {
      ninos: 'atiende_ninos',
      adultos: 'atiende_adultos',
      adolescentes: 'atiende_adolescentes',
    };
    filtros.tipoPaciente.split(',').forEach((val) => {
      const backendKey = pacMap[val.trim()];
      if (backendKey) params.set(backendKey, 'true');
    });
  }

  if (filtros.orden)         params.set('orden', filtros.orden);
  if (filtros.confiabilidad) params.set('confiabilidad', filtros.confiabilidad);
  if (filtros.soloAnalizados)   params.set('solo_analizados', 'true');
  if (filtros.soloConOpiniones) params.set('solo_con_opiniones', 'true');
  if (filtros.page != null)  params.set('page', String(filtros.page));
  if (filtros.limit != null) params.set('limit', String(filtros.limit));

  if (filtros.ratingMin != null)     params.set('rating_min', String(filtros.ratingMin));
  if (filtros.ratingMax != null)     params.set('rating_max', String(filtros.ratingMax));
  if (filtros.puntuacionMin != null) params.set('puntuacion_min', String(filtros.puntuacionMin));
  if (filtros.puntuacionMax != null) params.set('puntuacion_max', String(filtros.puntuacionMax));
  if (filtros.precioMin != null)     params.set('precio_min', String(filtros.precioMin));
  if (filtros.precioMax != null)     params.set('precio_max', String(filtros.precioMax));

  // Alcaldía/municipio como filtro específico
  if (filtros.alcaldia)      params.set('alcaldia_o_municipio', filtros.alcaldia);

  return params.toString();
}

/**
 * Busca especialistas con filtros en el backend.
 * Los resultados ya vienen ordenados con los analizados primero.
 *
 * @param {Object} [filtros={}] - Filtros de búsqueda
 * @returns {Promise<{ total: number, page: number, limit: number, pages: number, results: Array }>}
 *
 * @example
 * const resp = await buscarEspecialistas({ especialidad: 'cardiologo', ciudad: 'guadalajara' });
 * console.log(resp.results[0].tiene_analisis); // true (analizados primero)
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
 * Obtiene el detalle completo de un especialista por su _id de MongoDB.
 * Incluye el campo `analisis` con el estado del análisis IA.
 * Si no tiene análisis, el campo incluye `mensaje: "Este especialista aún no ha sido analizado"`.
 *
 * @param {string} id - _id de MongoDB del especialista
 * @returns {Promise<Object|null>} Detalle del especialista o null si no existe
 */
export async function obtenerDetalleEspecialista(id) {
  if (!id) return null;
  return realizarPeticion(`/especialistas/${id}`);
}

// Alias de compatibilidad
export const getSpecialistById = obtenerDetalleEspecialista;

/**
 * Obtiene el detalle de un especialista por su ID de Doctoralia.
 *
 * @param {number} doctoraliaId - ID numérico del especialista en Doctoralia
 * @returns {Promise<Object|null>} Detalle del especialista o null si no existe
 */
export async function obtenerDetalleEspecialistaPorDoctoraliaId(doctoraliaId) {
  if (!doctoraliaId) return null;
  return realizarPeticion(`/especialistas/doctoralia/${doctoraliaId}`);
}

/**
 * Obtiene las opiniones paginadas de un especialista.
 *
 * @param {string} id - _id de MongoDB del especialista
 * @param {Object} [params={}] - Parámetros de paginación y filtros
 * @returns {Promise<Object>} Respuesta paginada con opiniones
 */
export async function obtenerOpinionesEspecialista(id, params = {}) {
  const qParams = new URLSearchParams();
  if (params.page)           qParams.set('page', String(params.page));
  if (params.limit)          qParams.set('limit', String(params.limit));
  if (params.orden)          qParams.set('orden', params.orden);
  if (params.ratingMin)      qParams.set('rating_min', String(params.ratingMin));
  if (params.ratingMax)      qParams.set('rating_max', String(params.ratingMax));
  if (params.soloVerificadas) qParams.set('solo_verificadas', 'true');
  if (params.servicio)       qParams.set('servicio', params.servicio);

  const query = qParams.toString();
  return realizarPeticion(`/especialistas/${id}/opiniones${query ? `?${query}` : ''}`);
}
