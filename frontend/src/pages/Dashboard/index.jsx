import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  RiDeleteBinLine,
  RiSearchLine,
  RiHeartLine,
  RiSave3Line,
  RiEmotionSadLine,
} from 'react-icons/ri';
import Select from 'react-select';
import { PageWrapper } from '@/components/layout/PageWrapper';
import { BubbleBackground } from '@/components/layout/BubbleBackground';
import { Navbar } from '@/components/layout/Navbar';
import { Sidebar } from '@/components/layout/Sidebar';
import { SpecialistCard } from '@/components/shared/SpecialistCard';
import { SkeletonCard } from '@/components/ui/SkeletonCard';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { useAuth } from '@/hooks/useAuth';
import { useToast } from '@/hooks/useToast';
import { getFavoriteSpecialists, removeFavorite, getSearchHistory } from '@/services/api';
import ChatPanel from '@/components/shared/ChatPanel';

/**
 * Dashboard — Panel del usuario autenticado.
 * Sub-secciones: Favoritos, Historial, Perfil.
 */
export default function Dashboard() {
  const { user, updateProfile } = useAuth();
  const navigate = useNavigate();
  const { addToast } = useToast();
  const [activeSection, setActiveSection] = useState('buscar');

  // Redirigir si no autenticado
  useEffect(() => {
    if (!user) {
      navigate('/login');
    }
  }, [user, navigate]);

  if (!user) return null;

  return (
    <PageWrapper name="dashboard">
      <BubbleBackground />
      <Navbar />

      <div className="relative z-10 pt-20 pb-8 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto">
        <div className="flex flex-col lg:flex-row gap-6">
          <Sidebar activeSection={activeSection} onSectionChange={setActiveSection} />

          <main className="flex-1">
            {activeSection === 'buscar' && <SearchSection navigate={navigate} />}
            {activeSection === 'favoritos' && <FavoritesSection addToast={addToast} />}
            {activeSection === 'historial' && <HistorySection addToast={addToast} navigate={navigate} />}
            {activeSection === 'perfil' && <ProfileSection user={user} updateProfile={updateProfile} addToast={addToast} />}
          </main>
        </div>
      </div>
    </PageWrapper>
  );
}

/* ──────────────────────────────────────────────
   Sub-sección: Buscar especialistas
   ────────────────────────────────────────────── */

/**
 * SearchSection — Permite buscar por select o por chat (tab)
 */
function SearchSection({ navigate }) {
  const [mode, setMode] = React.useState('select'); // 'select' | 'chat'
  const [q, setQ] = React.useState('');
  const [ciudad, setCiudad] = React.useState('');

  const go = () => {
    const params = new URLSearchParams();
    if (q) params.set('q', q);
    if (ciudad) params.set('ciudad', ciudad);
    navigate(`/resultados?${params.toString()}`);
  };

  return (
    <div>
      <h2 className="text-xl font-semibold mb-4">Buscar especialistas</h2>
      <div className="flex items-center gap-3 mb-4">
        <button className={`px-3 py-2 rounded-lg ${mode === 'select' ? 'bg-royalBlue-600/20' : 'bg-transparent'}`} onClick={() => setMode('select')}>Por lista</button>
        <button className={`px-3 py-2 rounded-lg ${mode === 'chat' ? 'bg-royalBlue-600/20' : 'bg-transparent'}`} onClick={() => setMode('chat')}>Por chat</button>
      </div>

      {mode === 'select' ? (
        <div className="glass-card p-4 space-y-3">
          <select value={q} onChange={(e) => setQ(e.target.value)} className="glass-input w-full px-3 py-2 text-sm">
            <option value="">Seleccione especialidad</option>
            <option>Dentista</option>
            <option>Cardiólogo</option>
            <option>Dermatólogo</option>
            <option>Ortopedista</option>
          </select>
          <input value={ciudad} onChange={(e) => setCiudad(e.target.value)} placeholder="Ciudad" className="glass-input px-3 py-2 text-sm w-full" />
          <Button variant="primary" onClick={go}>Buscar</Button>
        </div>
      ) : (
        <div className="glass-card p-0">
          <ChatPanel compact onDetectedChange={(d) => {
            // si el chat detecta ready podemos navegar
            if (d.ready) {
              const params = new URLSearchParams();
              if (d.especialidad) params.set('q', d.especialidad);
              if (d.ciudad) params.set('ciudad', d.ciudad);
              navigate(`/resultados?${params.toString()}`);
            }
          }} />
        </div>
      )}
    </div>
  );
}


/* ──────────────────────────────────────────────
   Sub-sección: Mis favoritos
   ────────────────────────────────────────────── */

/**
 * FavoritesSection — Grid de especialistas guardados como favoritos.
 */
function FavoritesSection({ addToast }) {
  const [favorites, setFavorites] = useState([]);
  const [loading, setLoading] = useState(true);

  const loadFavorites = useCallback(async () => {
    setLoading(true);
    try {
      const data = await getFavoriteSpecialists();
      setFavorites(data);
    } catch {
      addToast({ type: 'error', message: 'Error al cargar favoritos.' });
    } finally {
      setLoading(false);
    }
  }, [addToast]);

  useEffect(() => {
    loadFavorites();
  }, [loadFavorites]);

  /**
   * Elimina un especialista de favoritos.
   * @param {string} id
   */
  const handleDelete = async (id) => {
    await removeFavorite(id);
    setFavorites((prev) => prev.filter((f) => f._id !== id));
    addToast({ type: 'success', message: 'Eliminado de favoritos.' });
  };

  return (
    <div>
      <h2 className="text-xl font-semibold mb-6 flex items-center gap-2">
        <RiHeartLine className="text-red-400" /> Mis favoritos
      </h2>

      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {Array.from({ length: 4 }).map((_, i) => <SkeletonCard key={i} />)}
        </div>
      ) : favorites.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
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
        <div className="glass-card p-12 text-center">
          <RiEmotionSadLine className="text-5xl mx-auto mb-4" style={{ color: 'var(--text-muted)' }} />
          <p className="text-lg font-medium mb-2">Aún no has guardado favoritos.</p>
          <p className="text-sm" style={{ color: 'var(--text-muted)' }}>
            Busca especialistas y guarda los que más te interesen.
          </p>
        </div>
      )}
    </div>
  );
}

/* ──────────────────────────────────────────────
   Sub-sección: Historial de búsquedas
   ────────────────────────────────────────────── */

/**
 * HistorySection — Lista de búsquedas previas con filtros.
 */
function HistorySection({ addToast, navigate }) {
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filterEsp, setFilterEsp] = useState('');
  const [filterFechaDesde, setFilterFechaDesde] = useState('');
  const [filterFechaHasta, setFilterFechaHasta] = useState('');

  const loadHistory = useCallback(async () => {
    setLoading(true);
    try {
      const data = await getSearchHistory({
        especialidad: filterEsp,
        fechaDesde: filterFechaDesde,
        fechaHasta: filterFechaHasta,
      });
      setHistory(data);
    } catch {
      addToast({ type: 'error', message: 'Error al cargar historial.' });
    } finally {
      setLoading(false);
    }
  }, [filterEsp, filterFechaDesde, filterFechaHasta, addToast]);

  useEffect(() => {
    loadHistory();
  }, [loadHistory]);

  /**
   * Repite una búsqueda del historial.
   * @param {{ especialidad: string, ciudad: string }} entry
   */
  const repeatSearch = (entry) => {
    const params = new URLSearchParams();
    if (entry.especialidad) params.set('q', entry.especialidad);
    if (entry.ciudad) params.set('ciudad', entry.ciudad);
    navigate(`/resultados?${params.toString()}`);
  };

  /**
   * Formatea una fecha ISO a formato local.
   * @param {string} dateStr
   * @returns {string}
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

  const especialidades = ['Dentista', 'Endodoncia', 'Cardiología', 'Dermatología', 'Ortopedia'];

  return (
    <div>
      <h2 className="text-xl font-semibold mb-6">Historial de búsquedas</h2>

      {/* Filtros */}
      <div className="glass-card p-4 mb-6 flex flex-col sm:flex-row gap-3">
        <div className="flex-1">
          <Select
            options={[{ value: '', label: 'Todas las especialidades' }, ...especialidades.map((e) => ({ value: e, label: e }))]}
            value={filterEsp}
            onChange={(option) => setFilterEsp(option.value)}
            className="react-select-container glass-input w-full px-3 py-2 text-sm z-3"
            classNamePrefix="react-select"
            placeholder="Filtrar por especialidad"
          />
        </div>
        <input
          type="date"
          value={filterFechaDesde}
          onChange={(e) => setFilterFechaDesde(e.target.value)}
          className="glass-input px-3 py-2 text-sm"
          placeholder="Desde"
        />
        <input
          type="date"
          value={filterFechaHasta}
          onChange={(e) => setFilterFechaHasta(e.target.value)}
          className="glass-input px-3 py-2 text-sm"
          placeholder="Hasta"
        />
      </div>

      {/* Lista */}
      {loading ? (
        <div className="space-y-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="glass-card p-4 space-y-2">
              <div className="h-4 skeleton-shimmer rounded w-3/4" />
              <div className="h-3 skeleton-shimmer rounded w-1/2" />
            </div>
          ))}
        </div>
      ) : history.length > 0 ? (
        <div className="space-y-3">
          {history.map((entry) => (
            <div key={entry.id} className="glass-card p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3 hover-lift">
              <div className="flex-1">
                <p className="text-sm font-medium">"{entry.query}"</p>
                <div className="flex flex-wrap gap-3 mt-1.5 text-xs" style={{ color: 'var(--text-muted)' }}>
                  <span>Especialidad: <strong className="text-royalBlue-300">{entry.especialidad}</strong></span>
                  <span>Ciudad: <strong>{entry.ciudad}</strong></span>
                  <span>{formatDate(entry.fecha)}</span>
                </div>
              </div>
              <Button
                variant="outline"
                className="text-xs shrink-0"
                icon={<RiSearchLine />}
                onClick={() => repeatSearch(entry)}
              >
                Repetir búsqueda
              </Button>
            </div>
          ))}
        </div>
      ) : (
        <div className="glass-card p-8 text-center">
          <p className="text-sm" style={{ color: 'var(--text-muted)' }}>No hay búsquedas que coincidan con los filtros.</p>
        </div>
      )}
    </div>
  );
}

/* ──────────────────────────────────────────────
   Sub-sección: Mi perfil
   ────────────────────────────────────────────── */

/** Emojis disponibles para avatar */
const AVATAR_EMOJIS = ['👤', '👩‍⚕️', '👨‍⚕️', '🧑‍💻', '🦊', '🐱', '🌟', '🎯', '💎', '🔥'];

/**
 * ProfileSection — Editor de perfil del usuario.
 */
function ProfileSection({ user, updateProfile, addToast }) {
  const [name, setName] = useState(user.name || '');
  const [avatar, setAvatar] = useState(user.avatar || '👤');
  const [showAvatarPicker, setShowAvatarPicker] = useState(false);

  /**
   * Guarda los cambios del perfil.
   */
  const handleSave = () => {
    updateProfile({ name, avatar });
    addToast({ type: 'success', message: 'Perfil actualizado.' });
  };

  return (
    <div>
      <h2 className="text-xl font-semibold mb-6">Mi perfil</h2>

      <div className="glass-card p-6 max-w-lg space-y-6">
        {/* Avatar */}
        <div className="space-y-2">
          <label className="block text-sm font-medium" style={{ color: 'var(--text-muted)' }}>
            Avatar
          </label>
          <div className="relative">
            <button
              onClick={() => setShowAvatarPicker(!showAvatarPicker)}
              className="w-20 h-20 rounded-2xl bg-royalBlue-800/50 border border-white/15 flex items-center justify-center text-4xl hover:border-royalBlue-400/50 transition-all duration-200"
              aria-label="Seleccionar avatar"
            >
              {avatar}
            </button>
            {showAvatarPicker && (
              <div className="absolute top-full mt-2 glass-card p-3 flex flex-wrap gap-2 w-64 z-10">
                {AVATAR_EMOJIS.map((emoji) => (
                  <button
                    key={emoji}
                    onClick={() => {
                      setAvatar(emoji);
                      setShowAvatarPicker(false);
                    }}
                    className={`w-10 h-10 rounded-lg flex items-center justify-center text-xl hover:bg-white/15 transition-colors ${avatar === emoji ? 'bg-royalBlue-600/40 ring-2 ring-royalBlue-400' : ''
                      }`}
                  >
                    {emoji}
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Nombre */}
        <Input
          id="profile-name"
          label="Nombre"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Tu nombre"
        />

        {/* Email (solo lectura) */}
        <div className="space-y-1.5">
          <label className="block text-sm font-medium" style={{ color: 'var(--text-muted)' }}>
            Correo electrónico
          </label>
          <input
            type="email"
            value={user.email}
            readOnly
            className="glass-input w-full px-4 py-2.5 text-sm opacity-60 cursor-not-allowed"
          />
          <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
            El correo no se puede modificar.
          </p>
        </div>

        {/* Guardar */}
        <Button variant="primary" icon={<RiSave3Line />} onClick={handleSave}>
          Guardar cambios
        </Button>
      </div>
    </div>
  );
}
