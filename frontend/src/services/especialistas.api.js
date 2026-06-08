/**
 * especialistas.api.js — Servicios API para la colección de Especialistas.
 */

import { realizarPeticion } from './api';

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

  // Filtros adicionales
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
