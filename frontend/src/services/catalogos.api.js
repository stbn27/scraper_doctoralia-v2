/**
 * catalogos.api.js — Servicio para catálogos de especialidades y ubicaciones.
 *
 * Fuente de datos: BD Doctoralia (27017) vía:
 * - GET /catalogos/especialidades   → colección specializations
 * - GET /catalogos/ciudades         → colección cities
 * - GET /catalogos/ubicaciones      → cities + provinces (autocompletado mixto)
 */

import { peticionBase } from './api';

/**
 * Obtiene lista de especialidades para autocompletado.
 * Normaliza a { label, value, nombre, slug }.
 *
 * @param {string} [q=''] - Búsqueda parcial por nombre
 * @returns {Promise<Array<{label: string, value: string, nombre: string, slug: string}>>}
 *
 * @example
 * const especialidades = await getSpecialties('cardio');
 * // [{ label: 'Cardiólogo', value: 'cardiologo', nombre: 'Cardiólogo', slug: 'cardiologo' }]
 */
export async function getSpecialties(q = '') {
  const params = q ? `?q=${encodeURIComponent(q)}` : '';
  const data = await peticionBase(`/catalogos/especialidades${params}`);
  return normalizarCatalogo(data, 'especialidades');
}

/**
 * Obtiene lista de ciudades.
 * Normaliza a { label, value, nombre, slug }.
 *
 * @param {string} [q=''] - Búsqueda parcial
 * @returns {Promise<Array<{label: string, value: string, nombre: string, slug: string}>>}
 */
export async function getCities(q = '') {
  const params = q ? `?q=${encodeURIComponent(q)}` : '';
  const data = await peticionBase(`/catalogos/ciudades${params}`);
  return normalizarCatalogo(data, 'ciudades');
}

/**
 * Carga catálogos de especialidades y ciudades en paralelo.
 * Usado para precarga inicial del formulario de búsqueda.
 *
 * @returns {Promise<{ specialties: Array, cities: Array }>}
 */
export async function getCatalogs() {
  const [specialties, cities] = await Promise.all([getSpecialties(), getCities()]);
  return { specialties, cities };
}

/* ─── Helpers ─── */

/**
 * Normaliza la respuesta de catálogos (especialidades o ciudades).
 * Siempre retorna { label, value, nombre, slug }.
 *
 * @param {*} response - Respuesta cruda del backend
 * @param {'especialidades'|'ciudades'} clave - Clave del array en la respuesta
 * @returns {Array}
 */
function normalizarCatalogo(response, clave) {
  if (!response) return [];

  // Array directo
  if (Array.isArray(response)) {
    return response.map(normalizarItem);
  }

  // response.especialidades / response.ciudades / response.results
  const lista = response?.[clave] ?? response?.results ?? [];
  if (Array.isArray(lista)) {
    return lista.map(normalizarItem);
  }

  return [];
}

/**
 * Normaliza un ítem de catálogo al formato estándar.
 * Soporta los campos del nuevo esquema Doctoralia (name, urlname, displayName, slug)
 * y el esquema legacy (nombre, slug).
 *
 * @param {Object|string} item - Ítem a normalizar
 * @returns {{ label: string, value: string, nombre: string, slug: string }}
 */
function normalizarItem(item) {
  if (typeof item === 'string') {
    return { label: item, value: item, nombre: item, slug: item };
  }

  // Soporte para campos de specializations (name, urlname) y cities (displayName, slug)
  const nombre =
    item.nombre ?? item.displayName ?? item.name ?? item.label ?? '';
  const slug =
    item.slug ?? item.urlname ?? item.valor ?? item.value ??
    nombre.toLowerCase().replace(/\s+/g, '-');

  return { label: nombre, value: slug, nombre, slug };
}