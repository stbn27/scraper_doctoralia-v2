import React, { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  RiSearchLine, RiRefreshLine, RiShieldLine,
  RiDatabase2Line, RiFileList2Line, RiBrainLine,
  RiUserLine, RiTimeLine, RiFilterLine,
} from 'react-icons/ri';
import { useAuth } from '@/hooks/useAuth';
import { PageWrapper } from '@/components/layout/PageWrapper';
import { BubbleBackground } from '@/components/layout/BubbleBackground';
import { Navbar } from '@/components/layout/Navbar';
import {
  getEstadisticasGlobales,
  getEspecialistasAdmin,
} from '@/services/admin.api';

/* ─── helpers ─── */
const fmt = (n) => (n ?? 0).toLocaleString('es-MX');
const fmtFecha = (iso) => {
  if (!iso) return '—';
  return new Date(iso).toLocaleString('es-MX', {
    day: '2-digit', month: 'short', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  });
};

const MODELO_COLORS = {
  deepseek: '#4f7dff',
  groq: '#10b981',
  gemini: '#f59e0b',
  minimax: '#a78bfa',
  ollama: '#fb923c',
};

const ESTATUS_COLORS = {
  completado: '#10b981',
  sin_opiniones: '#6b7280',
  error: '#ef4444',
  parcial: '#f59e0b',
};

/* ─── subcomponentes ─── */
function StatCard({ icon: Icon, label, value, sub, color = '#4f7dff' }) {
  return (
    <div style={{
      background: 'rgba(255,255,255,0.04)',
      border: '1px solid rgba(255,255,255,0.08)',
      borderRadius: 12,
      padding: '20px 24px',
      display: 'flex', gap: 16, alignItems: 'flex-start',
    }}>
      <div style={{
        width: 40, height: 40, borderRadius: 10, flexShrink: 0,
        background: `${color}22`, display: 'flex', alignItems: 'center', justifyContent: 'center',
      }}>
        <Icon size={20} style={{ color }} />
      </div>
      <div>
        <div style={{ fontSize: 22, fontWeight: 700, color: '#fff', lineHeight: 1 }}>{fmt(value)}</div>
        <div style={{ fontSize: 12, color: '#94a3b8', marginTop: 4 }}>{label}</div>
        {sub && <div style={{ fontSize: 11, color: '#64748b', marginTop: 2 }}>{sub}</div>}
      </div>
    </div>
  );
}

function Badge({ texto, color = '#4f7dff' }) {
  return (
    <span style={{
      fontSize: 10, fontWeight: 600, padding: '2px 7px', borderRadius: 999,
      background: `${color}22`, color, flexShrink: 0,
    }}>{texto}</span>
  );
}

function Skeleton() {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
      {Array.from({ length: 10 }).map((_, i) => (
        <div key={i} style={{
          height: 56, borderRadius: 8,
          background: 'rgba(255,255,255,0.04)',
          animation: 'pulse 1.5s ease infinite',
        }} />
      ))}
    </div>
  );
}

/* ─── tabla de especialistas ─── */
function FilaEspecialista({ esp }) {
  const navigate = useNavigate();
  const ana = esp.analisis;
  return (
    <tr
      onClick={() => navigate(`/admin/especialistas/${esp.doctoralia_id}`)}
      style={{ cursor: 'pointer', borderBottom: '1px solid rgba(255,255,255,0.05)' }}
      onMouseEnter={e => e.currentTarget.style.background = 'rgba(79,125,255,0.06)'}
      onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
    >
      {/* Foto + Nombre */}
      <td style={{ padding: '12px 16px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          {esp.foto_perfil ? (
            <img src={esp.foto_perfil} alt="" style={{ width: 36, height: 36, borderRadius: '50%', objectFit: 'cover', flexShrink: 0 }} />
          ) : (
            <div style={{ width: 36, height: 36, borderRadius: '50%', background: 'rgba(79,125,255,0.2)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
              <RiUserLine size={16} style={{ color: '#4f7dff' }} />
            </div>
          )}
          <div>
            <div style={{ fontSize: 13, fontWeight: 600, color: '#e2e8f0' }}>{esp.nombre || '—'}</div>
            <div style={{ fontSize: 11, color: '#64748b' }}>ID: {esp.doctoralia_id}</div>
          </div>
        </div>
      </td>

      {/* Especialidad */}
      <td style={{ padding: '12px 8px' }}>
        <div style={{ fontSize: 12, color: '#94a3b8' }}>
          {(esp.especialidades || [])[0] || '—'}
        </div>
      </td>

      {/* Ciudad */}
      <td style={{ padding: '12px 8px' }}>
        <div style={{ fontSize: 12, color: '#94a3b8' }}>{esp.ciudad || esp.estado || '—'}</div>
      </td>

      {/* Opiniones */}
      <td style={{ padding: '12px 8px', textAlign: 'right' }}>
        <div style={{ fontSize: 13, fontWeight: 600, color: '#fff' }}>{fmt(esp.total_opiniones_bd)}</div>
        <div style={{ fontSize: 10, color: '#64748b' }}>en BD</div>
      </td>

      {/* Último scraping */}
      <td style={{ padding: '12px 8px' }}>
        <div style={{ fontSize: 11, color: '#94a3b8' }}>
          {fmtFecha(esp.scraping?.ultimo_scraping)}
        </div>
      </td>

      {/* Análisis */}
      <td style={{ padding: '12px 16px' }}>
        {ana ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
            <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
              <Badge
                texto={ana.estatus || 'sin estado'}
                color={ESTATUS_COLORS[ana.estatus] || '#64748b'}
              />
              {ana.modelo_usado && (
                <Badge
                  texto={ana.modelo_usado}
                  color={MODELO_COLORS[ana.modelo_usado?.split('-')[0]] || '#a78bfa'}
                />
              )}
            </div>
            {ana.puntuacion != null && (
              <div style={{ fontSize: 11, color: '#94a3b8' }}>
                Puntuación: <strong style={{ color: '#fff' }}>{ana.puntuacion}</strong>
                {ana.confiabilidad && ` · ${ana.confiabilidad}`}
              </div>
            )}
          </div>
        ) : (
          <span style={{ fontSize: 11, color: '#475569', fontStyle: 'italic' }}>Sin análisis</span>
        )}
      </td>
    </tr>
  );
}

/* ─── filtros ─── */
const MODELOS = ['', 'deepseek', 'groq', 'gemini', 'minimax', 'ollama'];
const ESTATUS = ['', 'completado', 'sin_opiniones', 'error', 'parcial'];

function PanelFiltros({ filtros, onChange }) {
  return (
    <div style={{
      display: 'flex', gap: 10, flexWrap: 'wrap', alignItems: 'flex-end',
      background: 'rgba(255,255,255,0.03)',
      border: '1px solid rgba(255,255,255,0.07)',
      borderRadius: 10, padding: '14px 16px',
    }}>
      <RiFilterLine style={{ color: '#64748b', marginBottom: 4 }} />

      <div style={{ display: 'flex', flexDirection: 'column', gap: 4, flex: '1 1 180px' }}>
        <label style={{ fontSize: 10, color: '#64748b' }}>Buscar nombre</label>
        <input
          value={filtros.q}
          onChange={e => onChange({ ...filtros, q: e.target.value, page: 1 })}
          placeholder="Nombre del doctor..."
          style={inputStyle}
        />
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 4, flex: '1 1 140px' }}>
        <label style={{ fontSize: 10, color: '#64748b' }}>Análisis</label>
        <select
          value={filtros.conAnalisis === null ? '' : String(filtros.conAnalisis)}
          onChange={e => onChange({ ...filtros, conAnalisis: e.target.value === '' ? null : e.target.value === 'true', page: 1 })}
          style={selectStyle}
        >
          <option value="">Todos</option>
          <option value="true">Con análisis</option>
          <option value="false">Sin análisis</option>
        </select>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 4, flex: '1 1 130px' }}>
        <label style={{ fontSize: 10, color: '#64748b' }}>Modelo IA</label>
        <select
          value={filtros.modeloUsado}
          onChange={e => onChange({ ...filtros, modeloUsado: e.target.value, page: 1 })}
          style={selectStyle}
        >
          {MODELOS.map(m => <option key={m} value={m}>{m || 'Todos'}</option>)}
        </select>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 4, flex: '1 1 130px' }}>
        <label style={{ fontSize: 10, color: '#64748b' }}>Estatus análisis</label>
        <select
          value={filtros.estatusAnalisis}
          onChange={e => onChange({ ...filtros, estatusAnalisis: e.target.value, page: 1 })}
          style={selectStyle}
        >
          {ESTATUS.map(s => <option key={s} value={s}>{s || 'Todos'}</option>)}
        </select>
      </div>
    </div>
  );
}

const inputStyle = {
  background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.1)',
  borderRadius: 7, padding: '6px 10px', color: '#e2e8f0', fontSize: 13, width: '100%',
  outline: 'none',
};
const selectStyle = { ...inputStyle, cursor: 'pointer' };

/* ─── página principal ─── */
export default function AdminPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [stats, setStats] = useState(null);
  const [data, setData] = useState(null);
  const [cargando, setCargando] = useState(true);
  const [cargandoTabla, setCargandoTabla] = useState(false);
  const [error, setError] = useState(null);
  const [filtros, setFiltros] = useState({
    q: '', conAnalisis: null, modeloUsado: '', estatusAnalisis: '', page: 1, limit: 20,
  });

  // Guard de rol
  useEffect(() => {
    if (user && user.rol !== 'ADMIN') navigate('/busqueda', { replace: true });
  }, [user, navigate]);

  // Cargar estadísticas
  useEffect(() => {
    getEstadisticasGlobales()
      .then(setStats)
      .catch(() => { })
      .finally(() => setCargando(false));
  }, []);

  // Cargar tabla
  const cargarTabla = useCallback(async () => {
    setCargandoTabla(true);
    try {
      const resp = await getEspecialistasAdmin(filtros);
      setData(resp);
    } catch (e) {
      setError(e.message || 'Error al cargar especialistas');
    } finally {
      setCargandoTabla(false);
    }
  }, [filtros]);

  useEffect(() => { cargarTabla(); }, [cargarTabla]);

  if (user?.rol !== 'ADMIN') return null;

  const esp = data?.especialistas || [];
  const totalPages = data?.pages || 0;

  return (
    <PageWrapper name="admin">
      <BubbleBackground />
      <Navbar />

      <div className="relative z-10 pt-24 pb-12 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto" style={{ color: '#e2e8f0' }}>

      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 28 }}>
        <div style={{
          width: 40, height: 40, borderRadius: 10,
          background: 'rgba(79,125,255,0.2)', display: 'flex', alignItems: 'center', justifyContent: 'center',
        }}>
          <RiShieldLine size={22} style={{ color: '#4f7dff' }} />
        </div>
        <div>
          <h1 style={{ fontSize: 20, fontWeight: 700, margin: 0, color: '#fff' }}>Panel de Administración</h1>
          <p style={{ fontSize: 12, color: '#64748b', margin: 0 }}>Vista completa del sistema MedRec</p>
        </div>
        <button
          onClick={cargarTabla}
          style={{ marginLeft: 'auto', background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8, padding: '7px 12px', color: '#94a3b8', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6, fontSize: 12 }}
        >
          <RiRefreshLine size={14} /> Actualizar
        </button>
      </div>

      {/* Estadísticas globales */}
      {!cargando && stats && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 12, marginBottom: 28 }}>
          <StatCard icon={RiUserLine} label="Especialistas en BD" value={stats.especialistas?.total} color="#4f7dff" />
          <StatCard icon={RiBrainLine} label="Con análisis IA" value={stats.especialistas?.con_analisis}
            sub={`Sin análisis: ${fmt(stats.especialistas?.sin_analisis)}`} color="#10b981" />
          <StatCard icon={RiFileList2Line} label="Opiniones en BD" value={stats.opiniones?.total} color="#f59e0b" />
          <StatCard icon={RiDatabase2Line} label="Análisis generados" value={stats.analisis?.total} color="#a78bfa" />
          <StatCard icon={RiUserLine} label="Usuarios registrados" value={stats.usuarios?.total} color="#fb923c" />
          <StatCard
            icon={RiTimeLine}
            label="Último scraping"
            value="—"
            sub={fmtFecha(stats.scraping?.ultimo_registro)}
            color="#64748b"
          />
        </div>
      )}

      {/* Modelos usados */}
      {stats?.analisis?.por_modelo && Object.keys(stats.analisis.por_modelo).length > 0 && (
        <div style={{
          background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.07)',
          borderRadius: 10, padding: '16px 20px', marginBottom: 20,
        }}>
          <div style={{ fontSize: 12, color: '#64748b', marginBottom: 10, fontWeight: 600, letterSpacing: '0.05em' }}>
            ANÁLISIS POR MODELO
          </div>
          <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
            {Object.entries(stats.analisis.por_modelo).map(([modelo, total]) => (
              <div key={modelo} style={{
                display: 'flex', alignItems: 'center', gap: 6,
                background: `${MODELO_COLORS[modelo.split('-')[0]] || '#a78bfa'}15`,
                border: `1px solid ${MODELO_COLORS[modelo.split('-')[0]] || '#a78bfa'}30`,
                borderRadius: 8, padding: '6px 12px',
              }}>
                <span style={{ fontSize: 12, fontWeight: 600, color: MODELO_COLORS[modelo.split('-')[0]] || '#a78bfa' }}>{modelo}</span>
                <span style={{ fontSize: 11, color: '#94a3b8' }}>{fmt(total)}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Filtros */}
      <PanelFiltros filtros={filtros} onChange={setFiltros} />

      {/* Tabla */}
      <div style={{
        marginTop: 16, background: 'rgba(255,255,255,0.02)',
        border: '1px solid rgba(255,255,255,0.07)', borderRadius: 12, overflow: 'hidden',
      }}>
        <div style={{ padding: '14px 16px', borderBottom: '1px solid rgba(255,255,255,0.06)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <span style={{ fontSize: 13, fontWeight: 600, color: '#94a3b8' }}>
            Especialistas — <span style={{ color: '#fff' }}>{fmt(data?.total)}</span> resultados
          </span>
          {cargandoTabla && <span style={{ fontSize: 11, color: '#64748b' }}>Cargando...</span>}
        </div>

        {cargandoTabla ? <div style={{ padding: 20 }}><Skeleton /></div> : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
              <thead>
                <tr style={{ background: 'rgba(255,255,255,0.03)' }}>
                  {['Especialista', 'Especialidad', 'Ciudad', 'Opiniones', 'Último Scraping', 'Análisis IA'].map(h => (
                    <th key={h} style={{ padding: '10px 16px', textAlign: 'left', fontSize: 10, fontWeight: 600, color: '#64748b', letterSpacing: '0.06em', textTransform: 'uppercase', whiteSpace: 'nowrap' }}>
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {esp.length === 0 ? (
                  <tr><td colSpan={6} style={{ padding: 40, textAlign: 'center', color: '#475569' }}>Sin resultados</td></tr>
                ) : esp.map(e => <FilaEspecialista key={e._id} esp={e} />)}
              </tbody>
            </table>
          </div>
        )}

        {/* Paginación */}
        {totalPages > 1 && (
          <div style={{ padding: '12px 16px', borderTop: '1px solid rgba(255,255,255,0.06)', display: 'flex', gap: 8, justifyContent: 'flex-end', alignItems: 'center' }}>
            <span style={{ fontSize: 11, color: '#64748b', marginRight: 8 }}>
              Página {filtros.page} de {totalPages}
            </span>
            <button
              disabled={filtros.page <= 1}
              onClick={() => setFiltros(f => ({ ...f, page: f.page - 1 }))}
              style={{ ...btnPage, opacity: filtros.page <= 1 ? 0.4 : 1 }}
            >← Anterior</button>
            <button
              disabled={filtros.page >= totalPages}
              onClick={() => setFiltros(f => ({ ...f, page: f.page + 1 }))}
              style={{ ...btnPage, opacity: filtros.page >= totalPages ? 0.4 : 1 }}
            >Siguiente →</button>
          </div>
        )}
      </div>

      <style>{`@keyframes pulse { 0%,100%{opacity:.4} 50%{opacity:.8} }`}</style>
      </div>
    </PageWrapper>
  );
}

const btnPage = {
  background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.1)',
  borderRadius: 6, padding: '6px 12px', color: '#94a3b8', cursor: 'pointer', fontSize: 12,
};
