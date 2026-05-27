import { useState, useEffect, useCallback } from 'react';
import { searchSpecialists, getSpecialistById } from '@/services/api';

/**
 * Hook para buscar y manejar especialistas con estados de carga.
 * @param {{ especialidad?: string, ciudad?: string }} initialFilters — Filtros iniciales.
 * @returns {{ specialists: Array, loading: boolean, error: string|null, search: Function, getById: Function }}
 * @example
 * const { specialists, loading, search } = useSpecialists({ especialidad: 'Dentista' });
 */
export function useSpecialists(initialFilters = {}) {
  const [specialists, setSpecialists] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  /**
   * Ejecuta una búsqueda con los filtros proporcionados.
   * @param {Object} filtros — Filtros de búsqueda.
   */
  const search = useCallback(async (filtros = {}) => {
    setLoading(true);
    setError(null);
    try {
      const response = await searchSpecialists(filtros);
      setSpecialists(response.especialistas);
    } catch (err) {
      console.error('Error al buscar especialistas:', err);
      setError('Error al cargar los especialistas. Intenta de nuevo.');
    } finally {
      setLoading(false);
    }
  }, []);

  /**
   * Obtiene un especialista por ID.
   * @param {string} id
   * @returns {Promise<Object|null>}
   */
  const getById = useCallback(async (id) => {
    setLoading(true);
    setError(null);
    try {
      const result = await getSpecialistById(id);
      return result;
    } catch (err) {
      console.error('Error al obtener especialista:', err);
      setError('Error al cargar el especialista.');
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (initialFilters.especialidad || initialFilters.ciudad) {
      search(initialFilters);
    }
  }, []); // Solo al montar

  return { specialists, loading, error, search, getById };
}
