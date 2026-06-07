/* ──────────────────────────────────────────────
   Catálogos
   ────────────────────────────────────────────── 
*/

import { peticionBase } from "./api";

/**
 * Obtiene lista de especialidades desde el backend.
 * Normaliza la respuesta a { label, value, nombre, slug }[].
 * @returns {Promise<Array<{ label: string, value: string, nombre: string, slug: string }>>}
 */
export async function getSpecialties() {
    const data = await peticionBase(`/catalogos/especialidades`);
    return normalizeCatalogResponse(data, 'especialidades');
}

/**
 * Obtiene lista de ciudades desde el backend.
 * Normaliza la respuesta a { label, value, nombre, slug }[].
 * @returns {Promise<Array<{ label: string, value: string, nombre: string, slug: string }>>}
 */
export async function getCities() {
    const data = await peticionBase(`/catalogos/ciudades`);
    return normalizeCatalogResponse(data, 'ciudades');
}

/**
 * Carga catálogos de especialidades y ciudades en paralelo.
 * @returns {Promise<{ specialties: Array, cities: Array }>}
 */
export async function getCatalogs() {
    const [specialties, cities] = await Promise.all([
        getSpecialties(),
        getCities(),
    ]);

    return { specialties, cities };
}


/* ─── Helpers ─── */

/**
 * Normaliza la respuesta de catálogos (especialidades o ciudades)
 * para que el frontend siempre trabaje con { label, value, nombre, slug }.
 */
function normalizeCatalogResponse(response, key) {
  // Array directo
  if (Array.isArray(response)) {
    return response.map((item) => normalizeCatalogItem(item));
  }

  // response.especialidades / response.ciudades / response.results
  const data = response?.[key] ?? response?.results ?? [];
  if (Array.isArray(data)) {
    return data.map((item) => normalizeCatalogItem(item));
  }

  return [];
}

function normalizeCatalogItem(item) {
  if (typeof item === 'string') {
    return {
      label: item,
      value: item,
      nombre: item,
      slug: item,
    };
  }

  const nombre = item.nombre || item.label || item.name || '';
  const slug = item.slug || item.valor || item.value || nombre.toLowerCase().replace(/\s+/g, '-');

  return {
    label: nombre,
    value: slug,
    nombre,
    slug,
  };
}