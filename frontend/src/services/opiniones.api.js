/**
 * opiniones.api.js — Servicio para opiniones de especialistas.
 *
 * Consulta la colección ``doctor_opinions`` de la BD Doctoralia a través
 * del endpoint GET /especialistas/{id}/opiniones.
 */

import { realizarPeticion } from './api';

/**
 * @typedef {Object} FiltrosOpiniones
 * @property {number}  [page=1]            - Página actual
 * @property {number}  [limit=20]          - Opiniones por página
 * @property {string}  [orden='reciente']  - reciente|antigua|rating_desc|rating_asc
 * @property {number}  [ratingMin]         - Rating mínimo
 * @property {number}  [ratingMax]         - Rating máximo
 * @property {boolean} [soloVerificadas]   - Solo opiniones verificadas
 * @property {string}  [servicio]          - Filtrar por servicio consultado
 */

/**
 * Obtiene las opiniones paginadas de un especialista por su _id de MongoDB.
 *
 * @param {string} especialistaId - _id de MongoDB del especialista en doctor_profiles
 * @param {FiltrosOpiniones} [filtros={}] - Filtros y paginación
 * @returns {Promise<Object>} Respuesta con especialista, total, pages y results[]
 *
 * @example
 * const resp = await getOpiniones('6789abc123', { page: 1, limit: 10, orden: 'rating_desc' });
 * console.log(resp.results); // Array de opiniones
 */
export async function getOpiniones(especialistaId, filtros = {}) {
  if (!especialistaId) return null;

  const params = new URLSearchParams();
  if (filtros.page)          params.set('page', String(filtros.page));
  if (filtros.limit)         params.set('limit', String(filtros.limit));
  if (filtros.orden)         params.set('orden', filtros.orden);
  if (filtros.ratingMin)     params.set('rating_min', String(filtros.ratingMin));
  if (filtros.ratingMax)     params.set('rating_max', String(filtros.ratingMax));
  if (filtros.soloVerificadas) params.set('solo_verificadas', 'true');
  if (filtros.servicio)      params.set('servicio', filtros.servicio);

  const query = params.toString();
  return realizarPeticion(
    `/especialistas/${especialistaId}/opiniones${query ? `?${query}` : ''}`
  );
}

// Alias para compatibilidad con código previo
export const obtenerOpinionesEspecialista = getOpiniones;

/**
 * Calcula el resumen estadístico de una lista de opiniones.
 *
 * @param {Array<Object>} opiniones - Lista de opiniones del endpoint
 * @returns {{ total: number, promedio: number, verificadas: number, porcentajeVerificadas: number }}
 */
export function calcularResumenOpiniones(opiniones = []) {
  if (!opiniones.length) {
    return { total: 0, promedio: 0, verificadas: 0, porcentajeVerificadas: 0 };
  }

  const total = opiniones.length;
  const verificadas = opiniones.filter((op) => op.es_verificada).length;
  const sumaRating = opiniones.reduce((acc, op) => acc + (op.rating ?? 0), 0);
  const promedio = total > 0 ? Math.round((sumaRating / total) * 10) / 10 : 0;

  return {
    total,
    promedio,
    verificadas,
    porcentajeVerificadas: Math.round((verificadas / total) * 100),
  };
}
