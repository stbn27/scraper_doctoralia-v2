import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import {
  RiHistoryLine,
  RiSearchLine,
  RiDeleteBin7Line,
  RiEmotionSadLine,
  RiCalendarLine,
  RiMapPinLine,
  RiCompass3Line
} from 'react-icons/ri';
import { PageWrapper } from '@/components/layout/PageWrapper';
import { BubbleBackground } from '@/components/layout/BubbleBackground';
import { Navbar } from '@/components/layout/Navbar';
import { Button } from '@/components/ui/Button';
import { useAuth } from '@/hooks/useAuth';
import { useToast } from '@/hooks/useToast';
import { getSearchHistory, limpiarHistorial } from '@/services/api';

export default function Historial() {
  const { user, loading: authLoading } = useAuth();
  const navigate = useNavigate();
  const { addToast } = useToast();

  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);

  // Redirigir si no autenticado
  useEffect(() => {
    if (!authLoading && !user) {
      navigate('/login', { state: { from: '/historial' } });
    }
  }, [user, authLoading, navigate]);

  // Cargar historial
  const loadHistory = useCallback(async () => {
    if (!user) return;
    setLoading(true);
    try {
      const data = await getSearchHistory();
      setHistory(data || []);
    } catch (err) {
      console.error('Error al cargar historial:', err);
      addToast({ type: 'error', message: 'Error al cargar el historial de búsquedas.' });
    } finally {
      setLoading(false);
    }
  }, [user, addToast]);

  useEffect(() => {
    loadHistory();
  }, [loadHistory]);

  /**
   * Repite una búsqueda del historial.
   */
  const repeatSearch = (entry) => {
    const params = new URLSearchParams();
    const filtros = entry.filtros || {};
    
    const especialidad = filtros.especialidad || entry.especialidad || '';
    const ciudad = filtros.ciudad || entry.ciudad || entry.ubicacion || '';
    
    if (especialidad) params.set('especialidad', especialidad);
    if (ciudad) params.set('ciudad', ciudad);
    
    // Mapear el resto de los filtros para recrear la consulta exacta
    Object.keys(filtros).forEach((key) => {
      if (key !== 'especialidad' && key !== 'ciudad' && filtros[key] !== undefined && filtros[key] !== null) {
        params.set(key, String(filtros[key]));
      }
    });

    navigate(`/busqueda?${params.toString()}`);
  };

  /**
   * Limpia todo el historial.
   */
  const handleClearHistory = async () => {
    if (window.confirm('¿Estás seguro de eliminar todo tu historial de búsqueda?')) {
      try {
        await limpiarHistorial();
        setHistory([]);
        addToast({ type: 'success', message: 'Historial de búsqueda eliminado.' });
      } catch {
        addToast({ type: 'error', message: 'Error al limpiar el historial.' });
      }
    }
  };

  /**
   * Formatea la fecha.
   */
  const formatDate = (dateStr) => {
    return new Date(dateStr).toLocaleDateString('es-MX', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  if (authLoading || (!user && loading)) {
    return (
      <PageWrapper name="historial">
        <BubbleBackground />
        <Navbar />
        <div className="relative z-10 pt-20 pb-8 px-4 sm:px-6 lg:px-8 max-w-4xl mx-auto space-y-4">
          <div className="h-8 bg-white/10 rounded w-1/4 animate-pulse"></div>
          <div className="h-20 bg-white/5 rounded animate-pulse"></div>
          <div className="h-20 bg-white/5 rounded animate-pulse"></div>
        </div>
      </PageWrapper>
    );
  }

  if (!user) return null;

  return (
    <PageWrapper name="historial">
      <BubbleBackground />
      <Navbar />

      <div className="relative z-10 pt-20 pb-8 px-4 sm:px-6 lg:px-8 max-w-4xl mx-auto space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <RiHistoryLine className="text-royalBlue-400" /> Historial de búsqueda
          </h1>
          {history.length > 0 && (
            <Button
              variant="outline"
              icon={<RiDeleteBin7Line />}
              onClick={handleClearHistory}
              className="text-xs border-red-500/30 text-red-400 hover:bg-red-500/10 self-start sm:self-auto"
            >
              Limpiar historial
            </Button>
          )}
        </div>

        {loading ? (
          <div className="space-y-3">
            {Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="glass-card p-5 space-y-2 animate-pulse">
                <div className="h-4 bg-white/10 rounded w-1/3"></div>
                <div className="h-3 bg-white/10 rounded w-1/2"></div>
              </div>
            ))}
          </div>
        ) : history.length > 0 ? (
          <div className="space-y-3">
            {history.map((entry) => (
              <div
                key={entry.id || entry._id}
                className="glass-card p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4 hover-lift border border-white/5 transition-all"
              >
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-semibold text-slate-100">
                      Búsqueda de {entry.especialidad || 'Especialista'}
                    </span>
                    <Badge variant={entry.origen === 'chat' ? 'purple' : 'blue'} className="text-[10px]">
                      Origen: {entry.origen === 'chat' ? 'Chat' : 'Tradicional'}
                    </Badge>
                  </div>

                  <div className="flex flex-wrap gap-4 text-xs" style={{ color: 'var(--text-muted)' }}>
                    {entry.ciudad && (
                      <span className="flex items-center gap-1">
                        <RiMapPinLine /> {entry.ciudad}
                      </span>
                    )}
                    <span className="flex items-center gap-1">
                      <RiCalendarLine /> {formatDate(entry.fecha || entry.created_at)}
                    </span>
                    {entry.total_resultados !== undefined && (
                      <span className="flex items-center gap-1 text-slate-400">
                        <RiCompass3Line /> {entry.total_resultados} resultados
                      </span>
                    )}
                  </div>
                </div>

                <Button
                  variant="outline"
                  icon={<RiSearchLine />}
                  onClick={() => repeatSearch(entry)}
                  className="text-xs self-start sm:self-auto"
                >
                  Repetir búsqueda
                </Button>
              </div>
            ))}
          </div>
        ) : (
          <div className="glass-card p-12 text-center max-w-lg mx-auto">
            <RiEmotionSadLine className="text-5xl mx-auto mb-4" style={{ color: 'var(--text-muted)' }} />
            <h2 className="text-lg font-semibold mb-2">Todavía no has realizado búsquedas.</h2>
            <p className="text-sm mb-6" style={{ color: 'var(--text-muted)' }}>
              Tus consultas e intenciones de búsqueda se guardarán aquí para que puedas repetirlas rápidamente.
            </p>
            <Link to="/busqueda">
              <Button variant="primary" icon={<RiSearchLine />}>
                Ir a buscar
              </Button>
            </Link>
          </div>
        )}
      </div>
    </PageWrapper>
  );
}
