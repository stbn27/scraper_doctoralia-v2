import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { RiHeartLine, RiEmotionSadLine, RiSearchLine } from 'react-icons/ri';
import { PageWrapper } from '@/components/layout/PageWrapper';
import { BubbleBackground } from '@/components/layout/BubbleBackground';
import { Navbar } from '@/components/layout/Navbar';
import { SpecialistCard } from '@/components/shared/SpecialistCard';
import { SkeletonCard } from '@/components/ui/SkeletonCard';
import { Button } from '@/components/ui/Button';
import { useAuth } from '@/hooks/useAuth';
import { useToast } from '@/hooks/useToast';
import { getFavoriteSpecialists, removeFavorite } from '@/services/api';

export default function Favoritos() {
  const { user, loading: authLoading } = useAuth();
  const navigate = useNavigate();
  const { addToast } = useToast();

  const [favorites, setFavorites] = useState([]);
  const [loading, setLoading] = useState(true);

  // Redirigir si no autenticado
  useEffect(() => {
    if (!authLoading && !user) {
      navigate('/login', { state: { from: '/favoritos' } });
    }
  }, [user, authLoading, navigate]);

  // Cargar favoritos
  const loadFavorites = useCallback(async () => {
    if (!user) return;
    setLoading(true);
    try {
      const data = await getFavoriteSpecialists();
      setFavorites(data || []);
    } catch (err) {
      console.error('Error al cargar favoritos:', err);
      addToast({ type: 'error', message: 'Error al cargar tus especialistas favoritos.' });
    } finally {
      setLoading(false);
    }
  }, [user, addToast]);

  useEffect(() => {
    loadFavorites();
  }, [loadFavorites]);

  /**
   * Elimina un especialista de favoritos.
   */
  const handleDelete = async (id) => {
    try {
      await removeFavorite(id);
      setFavorites((prev) => prev.filter((f) => f._id !== id));
      addToast({ type: 'success', message: 'Eliminado de favoritos.' });
    } catch {
      addToast({ type: 'error', message: 'Error al eliminar de favoritos.' });
    }
  };

  if (authLoading || (!user && loading)) {
    return (
      <PageWrapper name="favoritos">
        <BubbleBackground />
        <Navbar />
        <div className="relative z-10 pt-20 pb-8 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto space-y-6">
          <div className="h-8 bg-white/10 rounded w-1/4 animate-pulse"></div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {Array.from({ length: 3 }).map((_, i) => <SkeletonCard key={i} />)}
          </div>
        </div>
      </PageWrapper>
    );
  }

  if (!user) return null;

  return (
    <PageWrapper name="favoritos">
      <BubbleBackground />
      <Navbar />

      <div className="relative z-10 pt-20 pb-8 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto">
        <h1 className="text-2xl font-bold flex items-center gap-2 mb-6">
          <RiHeartLine className="text-red-400" /> Mis especialistas favoritos
        </h1>

        {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {Array.from({ length: 3 }).map((_, i) => <SkeletonCard key={i} />)}
          </div>
        ) : favorites.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {favorites.map((spec) => (
              <SpecialistCard
                key={spec._id}
                specialist={spec}
                showDelete
                onDelete={handleDelete}
              />
            ))}
          </div>
        ) : (
          <div className="glass-card p-12 text-center max-w-lg mx-auto">
            <RiEmotionSadLine className="text-5xl mx-auto mb-4" style={{ color: 'var(--text-muted)' }} />
            <h2 className="text-lg font-semibold mb-2">Aún no tienes especialistas guardados.</h2>
            <p className="text-sm mb-6" style={{ color: 'var(--text-muted)' }}>
              Explora y guarda especialistas recomendados para tenerlos a la mano.
            </p>
            <Link to="/busqueda">
              <Button variant="primary" icon={<RiSearchLine />}>
                Buscar especialistas
              </Button>
            </Link>
          </div>
        )}
      </div>
    </PageWrapper>
  );
}
