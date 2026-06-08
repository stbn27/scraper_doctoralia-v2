import { useCallback, useEffect, useState } from 'react';
import { getCatalogs } from '../services/catalogos.api';

/**
 * useCatalogs — Hook para cargar catálogos (especialidades y ciudades).
 *
 * Uso:
 *   const { specialties, cities, loading, error, reload } = useCatalogs();
 *
 * @returns {{ specialties: Array, cities: Array, loading: boolean, error: Error|null, reload: Function }}
 */
export function useCatalogs() {
  const [specialties, setSpecialties] = useState([]);
  const [cities, setCities] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const loadCatalogs = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const data = await getCatalogs();
      setSpecialties(data.specialties);
      setCities(data.cities);
    } catch (err) {
      console.error('Error cargando catálogos:', err);
      setError(err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadCatalogs();
  }, [loadCatalogs]);

  return {
    specialties,
    cities,
    loading,
    error,
    reload: loadCatalogs,
  };
}
