/**
 * ubicaciones.api.js — Servicio para búsqueda de ubicaciones geográficas.
 *
 * Consulta la BD Doctoralia para autocompletado mixto de:
 * - Ciudades
 * - Alcaldías / municipios
 * - Estados / provincias
 *
 * Endpoint principal: GET /catalogos/ubicaciones?q={texto}
 */

import { peticionBase } from './api';

/**
 * @typedef {Object} Ubicacion
 * @property {string} nombre       - Nombre legible (ej: "Azcapotzalco")
 * @property {string} slug         - Slug URL (ej: "azcapotzalco")
 * @property {string} tipo         - Tipo de ubicación: "ciudad" | "estado"
 * @property {string} searchLoc    - Texto de búsqueda (ej: "Azcapotzalco")
 */

/**
 * Busca ubicaciones (ciudades, alcaldías y estados) para autocompletado.
 *
 * Prioriza ciudades; si hay pocos resultados, complementa con estados.
 * Requiere mínimo 2 caracteres para hacer la petición.
 *
 * @param {string} q - Texto libre de búsqueda (mínimo 2 caracteres)
 * @param {number} [limite=15] - Máximo de resultados a retornar
 * @returns {Promise<Ubicacion[]>} Lista de ubicaciones sugeridas
 *
 * @example
 * const sugerencias = await buscarUbicaciones('azca');
 * // [{ nombre: 'Azcapotzalco', slug: 'azcapotzalco', tipo: 'ciudad', searchLoc: 'Azcapotzalco' }]
 */
export async function buscarUbicaciones(q, limite = 15) {
  if (!q || q.trim().length < 2) return [];
  const params = new URLSearchParams({ q: q.trim(), limit: String(limite) });
  const data = await peticionBase(`/catalogos/ubicaciones?${params}`);
  return normalizarUbicaciones(data);
}

/**
 * Obtiene el listado completo de ciudades del catálogo.
 *
 * @param {string} [q=''] - Filtro de búsqueda opcional
 * @param {number} [limite=100] - Máximo de resultados
 * @returns {Promise<Ubicacion[]>} Lista de ciudades
 */
export async function getCiudades(q = '', limite = 100) {
  const params = new URLSearchParams({ limit: String(limite) });
  if (q) params.set('q', q);
  const data = await peticionBase(`/catalogos/ciudades?${params}`);
  return normalizarListaCiudades(data);
}

/**
 * Obtiene el listado de estados/provincias.
 * Actualmente delegado al endpoint de ubicaciones filtrando por tipo.
 *
 * @param {string} [q=''] - Filtro de búsqueda opcional
 * @returns {Promise<Ubicacion[]>} Lista de estados
 */
export async function getEstados(q = '') {
  const sugerencias = await buscarUbicaciones(q || 'a', 50);
  return sugerencias.filter((u) => u.tipo === 'estado');
}

/* ─── Helpers de normalización ─── */

/**
 * Normaliza la respuesta del endpoint /catalogos/ubicaciones.
 * @param {*} data - Respuesta cruda del backend
 * @returns {Ubicacion[]}
 */
function normalizarUbicaciones(data) {
  if (!data) return [];
  const lista = data?.ubicaciones ?? (Array.isArray(data) ? data : []);
  return lista.map((item) => ({
    nombre: item.displayName ?? item.nombre ?? item.name ?? '',
    slug: item.slug ?? '',
    tipo: item.tipo ?? 'ciudad',
    searchLoc: item.searchLoc ?? item.nombre ?? item.displayName ?? '',
    label: `${item.displayName ?? item.nombre ?? ''} · ${_etiquetaTipo(item.tipo)}`,
    value: item.slug ?? '',
  }));
}

/**
 * Normaliza la respuesta del endpoint /catalogos/ciudades.
 * @param {*} data - Respuesta cruda del backend
 * @returns {Ubicacion[]}
 */
function normalizarListaCiudades(data) {
  if (!data) return [];
  const lista = data?.ciudades ?? (Array.isArray(data) ? data : []);
  return lista.map((item) => ({
    nombre: item.displayName ?? item.nombre ?? '',
    slug: item.slug ?? '',
    tipo: 'ciudad',
    searchLoc: item.searchLoc ?? item.nombre ?? '',
    label: item.displayName ?? item.nombre ?? '',
    value: item.slug ?? '',
  }));
}

/**
 * Retorna la etiqueta legible del tipo de ubicación.
 * @param {string} tipo
 * @returns {string}
 */
function _etiquetaTipo(tipo) {
  const etiquetas = {
    ciudad: 'Ciudad',
    estado: 'Estado',
    alcaldia: 'Alcaldía',
    municipio: 'Municipio',
  };
  return etiquetas[tipo] ?? 'Ubicación';
}
