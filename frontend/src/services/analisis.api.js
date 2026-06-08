/**
 * analisis.api.js — Servicios API para el Análisis de IA de los Especialistas.
 */

import { obtenerDetalleEspecialista } from './especialistas.api';

/**
 * Obtiene el resumen de IA para compatibilidad con la vista de detalle.
 * @param {string} id - ID del especialista.
 * @returns {Promise<string>}
 */
export async function getReviewSummary(id) {
  const specialist = await obtenerDetalleEspecialista(id);
  return specialist?.analisis?.resumen || 'Sin reseñas disponibles para este especialista.';
}
