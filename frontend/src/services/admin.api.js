/**
 * admin.api.js — Servicios API para el panel de administración.
 *
 * Todos los endpoints requieren usuario con rol ADMIN.
 * El token se envía automáticamente a través del header Authorization.
 *
 * Endpoints:
 * - GET /admin/estadisticas        → Resumen global del sistema
 * - GET /admin/especialistas       → Lista paginada con datos de scraping y análisis
 * - GET /admin/especialistas/{id}  → Detalle admin de un especialista
 * - GET /admin/scraping/resumen    → Estado del pipeline de scraping
 */

import { realizarPeticion } from './api';

/**
 * @typedef {Object} FiltrosAdminEspecialistas
 * @property {string}  [q]                  - Búsqueda por nombre
 * @property {string}  [especialidad]        - Filtrar por especialidad
 * @property {string}  [ciudad]             - Filtrar por ciudad
 * @property {boolean} [conAnalisis]         - Solo con análisis (true) o sin (false)
 * @property {string}  [modeloUsado]         - Filtrar por modelo de IA
 * @property {string}  [estatusAnalisis]     - Filtrar por estatus del análisis
 * @property {number}  [page=1]             - Página actual
 * @property {number}  [limit=20]           - Registros por página
 */

/**
 * Obtiene el resumen estadístico global del sistema.
 *
 * @returns {Promise<Object>} Estadísticas con totales de especialistas, análisis, usuarios, etc.
 */
export async function getEstadisticasGlobales() {
  return realizarPeticion('/admin/estadisticas');
}

/**
 * Lista especialistas con datos de scraping y análisis para el panel admin.
 *
 * @param {FiltrosAdminEspecialistas} [filtros={}] - Filtros y paginación
 * @returns {Promise<{ total: number, page: number, pages: number, especialistas: Array }>}
 *
 * @example
 * const resp = await getEspecialistasAdmin({ conAnalisis: true, modeloUsado: 'deepseek', page: 1 });
 */
export async function getEspecialistasAdmin(filtros = {}) {
  const params = new URLSearchParams();
  if (filtros.q)              params.set('q', filtros.q);
  if (filtros.especialidad)   params.set('especialidad', filtros.especialidad);
  if (filtros.ciudad)         params.set('ciudad', filtros.ciudad);
  if (filtros.conAnalisis != null) params.set('con_analisis', String(filtros.conAnalisis));
  if (filtros.modeloUsado)    params.set('modelo_usado', filtros.modeloUsado);
  if (filtros.estatusAnalisis) params.set('estatus_analisis', filtros.estatusAnalisis);
  if (filtros.page)           params.set('page', String(filtros.page));
  if (filtros.limit)          params.set('limit', String(filtros.limit));

  const query = params.toString();
  return realizarPeticion(`/admin/especialistas${query ? `?${query}` : ''}`);
}

/**
 * Obtiene el detalle completo de un especialista en vista admin.
 *
 * @param {number} doctoraliaId - ID numérico del especialista en Doctoralia
 * @returns {Promise<Object>} Detalle completo con scraping, análisis y estadísticas
 */
export async function getDetalleEspecialistaAdmin(doctoraliaId) {
  return realizarPeticion(`/admin/especialistas/${doctoraliaId}`);
}

/**
 * Obtiene el resumen del pipeline de scraping.
 *
 * @returns {Promise<Object>} Estado con últimos scrapeados y distribución de fuentes
 */
export async function getResumenScraping() {
  return realizarPeticion('/admin/scraping/resumen');
}
