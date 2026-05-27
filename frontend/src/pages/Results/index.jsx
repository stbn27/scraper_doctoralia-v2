import React, { useState, useEffect, useCallback } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import {
  RiFilterLine,
  RiArrowLeftLine,
  RiSearchLine,
  RiEmotionSadLine,
} from 'react-icons/ri';
import { PageWrapper } from '@/components/layout/PageWrapper';
import { BubbleBackground } from '@/components/layout/BubbleBackground';
import { Navbar } from '@/components/layout/Navbar';
import { SpecialistCard } from '@/components/shared/SpecialistCard';
import { SkeletonCard } from '@/components/ui/SkeletonCard';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { SliderRange } from '@/components/ui/SliderRange';
import { useToast } from '@/hooks/useToast';
import { searchSpecialists } from '@/services/api';

/** Opciones de ordenamiento */
const SORT_OPTIONS = [
  { value: 'score', label: 'Mayor recomendación' },
  { value: 'rating', label: 'Mayor calificación' },
  { value: 'opiniones', label: 'Más opiniones' },
  { value: 'precio', label: 'Precio: menor a mayor' },
];

/**
 * Results — Pantalla de resultados con filtros y grid de tarjetas.
 */
export default function Results() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { addToast } = useToast();

  const initialEspecialidad = searchParams.get('q') || '';
  const initialCiudad = searchParams.get('ciudad') || '';

  const [specialists, setSpecialists] = useState([]);
  const [loading, setLoading] = useState(true);
  const [sortBy, setSortBy] = useState('score');
  const [showFilters, setShowFilters] = useState(false);

  // Estado de filtros
  const [filtros, setFiltros] = useState({
    especialidad: initialEspecialidad,
    ciudad: initialCiudad,
    precioMin: 0,
    precioMax: 30000,
    atiendeNinos: false,
    atiendeAdultos: false,
    minOpiniones: 1,
  });

  /**
   * Ejecuta la búsqueda con los filtros actuales.
   */
  const doSearch = useCallback(async (filters) => {
    setLoading(true);
    try {
      const response = await searchSpecialists(filters);
      setSpecialists(response.especialistas);
    } catch (err) {
      console.error('Error al buscar:', err);
      addToast({ type: 'error', message: 'Error al cargar especialistas.' });
    } finally {
      setLoading(false);
    }
  }, [addToast]);

  useEffect(() => {
    doSearch(filtros);
  }, []); // Solo al montar

  /**
   * Aplica los filtros actuales.
   */
  const applyFilters = () => {
    doSearch(filtros);
    setShowFilters(false);
  };

  /**
   * Limpia todos los filtros.
   */
  const clearFilters = () => {
    const cleared = {
      especialidad: '',
      ciudad: '',
      precioMin: 0,
      precioMax: 30000,
      atiendeNinos: false,
      atiendeAdultos: false,
      minOpiniones: 1,
    };
    setFiltros(cleared);
    doSearch(cleared);
  };

  /**
   * Ordena los especialistas según el criterio seleccionado.
   * @param {Array} list — Lista de especialistas.
   * @returns {Array}
   */
  const sortedSpecialists = [...specialists].sort((a, b) => {
    switch (sortBy) {
      case 'score': return b.score_recomendacion - a.score_recomendacion;
      case 'rating': return b.rating_global - a.rating_global;
      case 'opiniones': return b.total_opiniones - a.total_opiniones;
      case 'precio': {
        const minA = Math.min(...a.servicios.map((s) => s.precio_desde));
        const minB = Math.min(...b.servicios.map((s) => s.precio_desde));
        return minA - minB;
      }
      default: return 0;
    }
  });

  return (
    <PageWrapper name="results">
      <BubbleBackground />
      <Navbar />

      <div className="relative z-10 pt-20 pb-8 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto">
        <div className="flex flex-col lg:flex-row gap-6">
          {/* Toggle filtros mobile */}
          <button
            onClick={() => setShowFilters(!showFilters)}
            className="lg:hidden flex items-center gap-2 glass-card px-4 py-3 text-sm font-medium"
          >
            <RiFilterLine /> Filtros
          </button>

          {/* Panel de filtros */}
          <aside className={`glass-card p-5 space-y-5 shrink-0 w-full lg:w-[280px] ${showFilters ? 'block' : 'hidden lg:block'}`}>
            <h2 className="text-sm font-semibold uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>
              Filtros
            </h2>

            {/* Especialidad */}
            <div className="space-y-1.5">
              <label className="block text-xs font-medium" style={{ color: 'var(--text-muted)' }}>
                Especialidad
              </label>
              <select
                value={filtros.especialidad}
                onChange={(e) => setFiltros({ ...filtros, especialidad: e.target.value })}
                className="glass-input w-full px-3 py-2 text-sm"
              >
                <option value="">Todas</option>
                <option value="Dentista">Dentista</option>
                <option value="Endodoncia">Endodoncia</option>
                <option value="Cardiología">Cardiología</option>
                <option value="Dermatología">Dermatología</option>
                <option value="Ortopedia">Ortopedia</option>
              </select>
            </div>

            {/* Ciudad */}
            <Input
              id="filter-ciudad"
              label="Ciudad"
              placeholder="Ej: Ciudad de México"
              value={filtros.ciudad}
              onChange={(e) => setFiltros({ ...filtros, ciudad: e.target.value })}
            />

            {/* Rango de precio */}
            <SliderRange
              label="Rango de precio"
              min={0}
              max={30000}
              step={500}
              value={[filtros.precioMin, filtros.precioMax]}
              onChange={([min, max]) => setFiltros({ ...filtros, precioMin: min, precioMax: max })}
            />

            {/* Checkboxes */}
            <div className="space-y-2">
              <label className="flex items-center gap-2 text-sm cursor-pointer">
                <input
                  type="checkbox"
                  checked={filtros.atiendeNinos}
                  onChange={(e) => setFiltros({ ...filtros, atiendeNinos: e.target.checked })}
                  className="w-4 h-4 rounded border-white/20 bg-white/10 text-royalBlue-600 focus:ring-royalBlue-500"
                />
                Atiende niños
              </label>
              <label className="flex items-center gap-2 text-sm cursor-pointer">
                <input
                  type="checkbox"
                  checked={filtros.atiendeAdultos}
                  onChange={(e) => setFiltros({ ...filtros, atiendeAdultos: e.target.checked })}
                  className="w-4 h-4 rounded border-white/20 bg-white/10 text-royalBlue-600 focus:ring-royalBlue-500"
                />
                Atiende adultos
              </label>
            </div>

            {/* Mínimo opiniones */}
            <div className="space-y-1.5">
              <label className="block text-xs font-medium" style={{ color: 'var(--text-muted)' }}>
                Mínimo de opiniones
              </label>
              <input
                type="number"
                min={0}
                value={filtros.minOpiniones}
                onChange={(e) => setFiltros({ ...filtros, minOpiniones: parseInt(e.target.value) || 0 })}
                className="glass-input w-full px-3 py-2 text-sm"
              />
            </div>

            {/* Botones */}
            <div className="space-y-2 pt-2">
              <Button variant="primary" fullWidth onClick={applyFilters}>
                Aplicar filtros
              </Button>
              <Button variant="ghost" fullWidth onClick={clearFilters}>
                Limpiar
              </Button>
            </div>
          </aside>

          {/* Área principal */}
          <main className="flex-1">
            {/* Header: conteo + ordenamiento */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-6">
              <p className="text-sm" style={{ color: 'var(--text-muted)' }}>
                {loading ? 'Buscando...' : `${sortedSpecialists.length} especialista${sortedSpecialists.length !== 1 ? 's' : ''} encontrado${sortedSpecialists.length !== 1 ? 's' : ''}`}
              </p>
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value)}
                className="glass-input px-3 py-2 text-sm w-full sm:w-auto"
              >
                {SORT_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>{opt.label}</option>
                ))}
              </select>
            </div>

            {/* Grid */}
            {loading ? (
              <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
                {Array.from({ length: 6 }).map((_, i) => (
                  <SkeletonCard key={i} />
                ))}
              </div>
            ) : sortedSpecialists.length > 0 ? (
              <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
                {sortedSpecialists.map((spec) => (
                  <SpecialistCard key={spec._id} specialist={spec} />
                ))}
              </div>
            ) : (
              /* Estado vacío */
              <div className="glass-card p-12 text-center">
                <RiEmotionSadLine className="text-5xl mx-auto mb-4" style={{ color: 'var(--text-muted)' }} />
                <p className="text-lg font-medium mb-2">No encontramos especialistas para tu búsqueda.</p>
                <p className="text-sm mb-6" style={{ color: 'var(--text-muted)' }}>
                  Intenta con otros filtros o una especialidad diferente.
                </p>
                <Button variant="outline" onClick={() => navigate('/')}>
                  <RiArrowLeftLine /> Volver al inicio
                </Button>
              </div>
            )}
          </main>
        </div>
      </div>
    </PageWrapper>
  );
}
