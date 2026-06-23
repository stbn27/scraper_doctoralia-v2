import React, { useCallback, useEffect, useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  RiSearchLine, RiRefreshLine, RiShieldLine,
  RiDatabase2Line, RiFileList2Line, RiBrainLine,
  RiUserLine, RiTimeLine, RiFilterLine, RiDeleteBinLine, RiExternalLinkLine,
  RiArrowUpLine, RiArrowDownLine, RiArrowLeftSLine, RiArrowRightSLine,
  RiAlertLine, RiCheckLine
} from 'react-icons/ri';
import {
  useReactTable,
  getCoreRowModel,
  flexRender
} from '@tanstack/react-table';
import Select from 'react-select';
import { selectStyles } from '@/components/ui/selectStyles';

import { useAuth } from '@/hooks/useAuth';
import { PageWrapper } from '@/components/layout/PageWrapper';
import { BubbleBackground } from '@/components/layout/BubbleBackground';
import { Navbar } from '@/components/layout/Navbar';
import { ConfirmModal } from '@/components/ui/ConfirmModal';
import { Checkbox } from '@/components/ui/Checkbox';
import { Button } from '@/components/ui/Button';
import { UsersTab } from './UsersTab';

import {
  getEstadisticasGlobales,
  getEspecialistasAdmin,
  deleteEspecialistaAdmin,
  validarUrlAdmin,
  ejecutarScrapingManual
} from '@/services/admin.api';
import { useToast } from '@/hooks/useToast';

/* ─── helpers ─── */
const fmt = (n) => (n ?? 0).toLocaleString('es-MX');
const fmtFecha = (iso) => {
  if (!iso) return '—';
  const d = new Date(iso);
  if (isNaN(d)) return '—';
  return d.toLocaleString('es-MX', {
    day: '2-digit', month: 'short', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  });
};

const normalizeName = (name) => {
  if (!name) return '—';
  return name.replace(/^(Dra\.|Dr\.|Dra|Dr)\s+/i, '');
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
    <div className="glass-card flex items-start gap-4 px-6 py-5 border border-[var(--glass-border)]">
      <div 
        className="w-10 h-10 rounded-xl shrink-0 flex items-center justify-center"
        style={{ background: `${color}22` }}
      >
        <Icon size={20} style={{ color }} />
      </div>
      <div>
        <div className="text-[22px] font-bold text-[var(--text-primary)] leading-none">{value !== undefined ? fmt(value) : '—'}</div>
        <div className="text-xs text-[var(--text-muted)] mt-1">{label}</div>
        {sub && <div className="text-[11px] text-[var(--text-muted)] mt-0.5">{sub}</div>}
      </div>
    </div>
  );
}

function Badge({ texto, color = 'var(--text-muted)' }) {
  return (
    <span 
      className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-[var(--glass-bg)] border border-[var(--glass-border)] shrink-0"
      style={{ color }}
    >
      {texto}
    </span>
  );
}

function Skeleton() {
  return (
    <div className="flex flex-col gap-2">
      {Array.from({ length: 10 }).map((_, i) => (
        <div key={i} className="skeleton-shimmer h-14 rounded-lg" />
      ))}
    </div>
  );
}

/* ─── URL Validation & Scraping ─── */
function UrlScrapingSection({ onScraped }) {
  const { addToast } = useToast();
  const [url, setUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [validationResult, setValidationResult] = useState(null);
  const [analyze, setAnalyze] = useState(false);

  const handleValidate = async () => {
    if (!url) return;
    setLoading(true);
    setValidationResult(null);
    try {
      const res = await validarUrlAdmin(url);
      setValidationResult(res);
      if (!res.valida) {
        addToast({ type: 'error', message: res.error || 'URL inválida' });
      }
    } catch (e) {
      addToast({ type: 'error', message: 'Error al validar URL' });
    } finally {
      setLoading(false);
    }
  };

  const handleScrape = async () => {
    if (!url || !validationResult?.valida || validationResult.existe) return;
    setLoading(true);
    try {
      await ejecutarScrapingManual({ url, analyze });
      addToast({ type: 'success', message: 'Perfil procesado con éxito' });
      setUrl('');
      setValidationResult(null);
      setAnalyze(false);
      onScraped(); // refrescar
    } catch (e) {
      addToast({ type: 'error', message: e.message || 'Error al procesar el perfil' });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="glass-card border border-[var(--glass-border)] px-5 py-4 mb-5 flex flex-col gap-3">
      <div className="text-[13px] font-semibold text-[var(--text-primary)]">Validación y Scraping Manual de Doctoralia</div>
      
      <div className="flex gap-2.5 items-center">
        <input 
          type="text" 
          className="glass-input flex-1 px-3 py-2 text-[13px]"
          value={url} 
          onChange={e => { setUrl(e.target.value); setValidationResult(null); }}
          placeholder="https://www.doctoralia.com.mx/..."
          disabled={loading}
        />
        <Button onClick={handleValidate} disabled={!url || loading} className="text-xs" variant="secondary">
          Validar
        </Button>
      </div>

      {validationResult && (
        <div className="mt-2 text-[13px]">
          {validationResult.existe ? (
            <div className="flex items-center gap-1.5 text-amber-500">
              <RiAlertLine /> El perfil ya existe en la base de datos: <strong className="text-[var(--text-primary)]">{validationResult.nombre}</strong> (ID: {validationResult.doctoralia_id}).
            </div>
          ) : validationResult.valida ? (
            <div className="flex flex-wrap items-center gap-4">
              <div className="flex items-center gap-1.5 text-emerald-500"><RiCheckLine /> Perfil nuevo y válido para scraping.</div>
              <Checkbox 
                label="Generar análisis IA tras scraping" 
                checked={analyze} 
                onChange={e => setAnalyze(e.target.checked)} 
                disabled={loading}
              />
              <Button onClick={handleScrape} disabled={loading} className="text-xs" variant="primary">
                {loading ? 'Procesando...' : 'Extraer Perfil'}
              </Button>
            </div>
          ) : null}
        </div>
      )}
    </div>
  );
}

/* ─── filtros ─── */
const OPT_ANALISIS = [
  { value: '', label: 'Todos' },
  { value: 'true', label: 'Con análisis' },
  { value: 'false', label: 'Sin análisis' }
];

const OPT_MODELOS = [
  { value: '', label: 'Todos' },
  { value: 'deepseek', label: 'deepseek' },
  { value: 'groq', label: 'groq' },
  { value: 'gemini', label: 'gemini' },
  { value: 'minimax', label: 'minimax' },
  { value: 'ollama', label: 'ollama' }
];

const OPT_ESTATUS = [
  { value: '', label: 'Todos' },
  { value: 'completado', label: 'completado' },
  { value: 'sin_opiniones', label: 'sin_opiniones' },
  { value: 'error', label: 'error' },
  { value: 'parcial', label: 'parcial' }
];

function PanelFiltros({ filtros, onChange }) {
  const [qInput, setQInput] = useState(filtros.q);

  useEffect(() => {
    const handler = setTimeout(() => {
      if (qInput !== filtros.q) {
        onChange(f => ({ ...f, q: qInput, page: 1 }));
      }
    }, 500);
    return () => clearTimeout(handler);
  }, [qInput, filtros.q, onChange]);

  return (
    <div className="glass-card" style={{
      display: 'flex', gap: 10, flexWrap: 'wrap', alignItems: 'flex-end',
      border: '1px solid var(--glass-border)', padding: '14px 16px',
    }}>
      <RiFilterLine style={{ color: 'var(--text-muted)', marginBottom: 4 }} />

      <div style={{ display: 'flex', flexDirection: 'column', gap: 4, flex: '1 1 180px' }}>
        <label style={{ fontSize: 10, color: 'var(--text-muted)' }}>Buscar nombre</label>
        <input
          value={qInput}
          onChange={e => setQInput(e.target.value)}
          placeholder="Nombre del doctor..."
          className="glass-input"
          style={{ padding: '8px 10px', fontSize: 13, width: '100%', height: '38px' }}
        />
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 4, flex: '1 1 160px' }}>
        <label style={{ fontSize: 10, color: 'var(--text-muted)' }}>Análisis</label>
        <Select
          options={OPT_ANALISIS}
          styles={selectStyles}
          value={OPT_ANALISIS.find(o => o.value === (filtros.conAnalisis === null ? '' : String(filtros.conAnalisis)))}
          onChange={item => onChange(f => ({ ...f, conAnalisis: item.value === '' ? null : item.value === 'true', page: 1 }))}
          isSearchable={false}
          menuPortalTarget={document.body}
        />
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 4, flex: '1 1 150px' }}>
        <label style={{ fontSize: 10, color: 'var(--text-muted)' }}>Modelo IA</label>
        <Select
          options={OPT_MODELOS}
          styles={selectStyles}
          value={OPT_MODELOS.find(o => o.value === filtros.modeloUsado) || OPT_MODELOS[0]}
          onChange={item => onChange(f => ({ ...f, modeloUsado: item.value, page: 1 }))}
          isSearchable={false}
          menuPortalTarget={document.body}
        />
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 4, flex: '1 1 150px' }}>
        <label style={{ fontSize: 10, color: 'var(--text-muted)' }}>Estatus análisis</label>
        <Select
          options={OPT_ESTATUS}
          styles={selectStyles}
          value={OPT_ESTATUS.find(o => o.value === filtros.estatusAnalisis) || OPT_ESTATUS[0]}
          onChange={item => onChange(f => ({ ...f, estatusAnalisis: item.value, page: 1 }))}
          isSearchable={false}
          menuPortalTarget={document.body}
        />
      </div>
    </div>
  );
}

/* ─── Paginación combinada ─── */
export function Pagination({ page, pages, limit, onPageChange, onLimitChange }) {
  if (pages <= 1) return null;

  // Calculo rango desktop
  const getPageNumbers = () => {
    const p = [];
    const maxVisible = 5;
    let start = Math.max(1, page - 2);
    let end = Math.min(pages, page + 2);

    if (page <= 3) {
      end = Math.min(pages, maxVisible);
    } else if (page >= pages - 2) {
      start = Math.max(1, pages - 4);
    }

    for (let i = start; i <= end; i++) p.push(i);
    return { start, end, p };
  };

  const { start, end, p } = getPageNumbers();

  return (
    <div style={{ padding: '12px 16px', borderTop: '1px solid var(--glass-border)', display: 'flex', gap: 16, justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap' }}>
      
      {/* Límite */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>Mostrar:</span>
        <select 
          value={limit}
          onChange={e => onLimitChange(Number(e.target.value))}
          className="glass-input"
          style={{ padding: '4px 8px', fontSize: 12, cursor: 'pointer' }}
        >
          <option value={20} style={{ color: '#000' }}>20</option>
          <option value={50} style={{ color: '#000' }}>50</option>
          <option value={100} style={{ color: '#000' }}>100</option>
        </select>
      </div>

      {/* Paginador Mobile */}
      <div className="flex md:hidden items-center gap-2">
        <button
          disabled={page <= 1}
          onClick={() => onPageChange(page - 1)}
          className="glass-input hover:bg-white/5"
          style={{ padding: '6px 12px', color: 'var(--text-muted)', fontSize: 12, opacity: page <= 1 ? 0.4 : 1 }}
        >← Anterior</button>
        <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>Pág {page} de {pages}</span>
        <button
          disabled={page >= pages}
          onClick={() => onPageChange(page + 1)}
          className="glass-input hover:bg-white/5"
          style={{ padding: '6px 12px', color: 'var(--text-muted)', fontSize: 12, opacity: page >= pages ? 0.4 : 1 }}
        >Siguiente →</button>
      </div>

      {/* Paginador Desktop */}
      <div className="hidden md:flex items-center gap-1">
        <button
          disabled={page <= 1}
          onClick={() => onPageChange(1)}
          className="glass-input hover:bg-white/5 disabled:opacity-40 flex items-center justify-center min-w-[2rem] px-2 h-8"
          title="Primera página"
          aria-label="Primera página"
        >
          &laquo;
        </button>
        <button
          disabled={page <= 1}
          onClick={() => onPageChange(page - 1)}
          className="glass-input hover:bg-white/5 disabled:opacity-40 flex items-center justify-center min-w-[2rem] px-2 h-8"
          title="Página anterior"
          aria-label="Página anterior"
        >
          <RiArrowLeftSLine />
        </button>

        {start > 1 && <span style={{ color: 'var(--text-muted)', margin: '0 4px' }}>...</span>}

        {p.map(num => (
          <button
            key={num}
            onClick={() => onPageChange(num)}
            className={`glass-input flex items-center justify-center min-w-[2rem] px-2 h-8 ${page === num ? 'border-primary-500 text-primary-500' : 'hover:bg-white/5'}`}
            style={page === num ? { borderColor: 'var(--color-primary-500)', color: 'var(--color-primary-500)', fontWeight: 'bold' } : { color: 'var(--text-muted)' }}
          >
            {num}
          </button>
        ))}

        {end < pages && <span style={{ color: 'var(--text-muted)', margin: '0 4px' }}>...</span>}

        <button
          disabled={page >= pages}
          onClick={() => onPageChange(page + 1)}
          className="glass-input hover:bg-white/5 disabled:opacity-40 flex items-center justify-center min-w-[2rem] px-2 h-8"
          title="Página siguiente"
          aria-label="Página siguiente"
        >
          <RiArrowRightSLine />
        </button>
        <button
          disabled={page >= pages}
          onClick={() => onPageChange(pages)}
          className="glass-input hover:bg-white/5 disabled:opacity-40 flex items-center justify-center min-w-[2rem] px-2 h-8"
          title="Última página"
          aria-label="Última página"
        >
          &raquo;
        </button>
      </div>
    </div>
  );
}

/* ─── página principal ─── */
export default function AdminPage() {
  const { user } = useAuth();
  const { addToast } = useToast();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState('especialistas');
  const [stats, setStats] = useState(null);
  const [data, setData] = useState(null);
  const [cargando, setCargando] = useState(true);
  const [cargandoTabla, setCargandoTabla] = useState(false);
  const [filtros, setFiltros] = useState({
    q: '', conAnalisis: null, modeloUsado: '', estatusAnalisis: '', page: 1, limit: 20, sort_by: '', sort_order: ''
  });
  
  const [deleteModal, setDeleteModal] = useState({ open: false, row: null });

  useEffect(() => {
    if (user && user.rol !== 'ADMIN') navigate('/busqueda', { replace: true });
  }, [user, navigate]);

  const cargarEstadisticas = useCallback(() => {
    getEstadisticasGlobales()
      .then(setStats)
      .catch(() => { })
      .finally(() => setCargando(false));
  }, []);

  useEffect(() => {
    cargarEstadisticas();
  }, [cargarEstadisticas]);

  const cargarTabla = useCallback(async () => {
    setCargandoTabla(true);
    try {
      const resp = await getEspecialistasAdmin(filtros);
      setData(resp);
    } catch (e) {
      addToast({ type: 'error', message: 'Error al cargar especialistas' });
    } finally {
      setCargandoTabla(false);
    }
  }, [filtros, addToast]);

  useEffect(() => {
    let abortController = new AbortController();
    cargarTabla();
    return () => abortController.abort();
  }, [cargarTabla]);

  const handleDelete = async () => {
    if (!deleteModal.row) return;
    try {
      await deleteEspecialistaAdmin(deleteModal.row.doctoralia_id);
      addToast({ type: 'success', message: 'Especialista eliminado con éxito' });
      setDeleteModal({ open: false, row: null });
      cargarTabla();
      cargarEstadisticas();
    } catch (e) {
      addToast({ type: 'error', message: e.message || 'Error al eliminar' });
    }
  };

  const handleSort = (columnId) => {
    const map = {
      'especialista': 'doctor.nombre',
      'especialidades': 'doctor.especialidades',
      'ciudad': 'doctor.direcciones.ciudad',
      'opiniones': 'total_opiniones',
      'fecha_scraping': 'metadata.fecha_consulta'
    };
    
    const sort_by = map[columnId];
    if (!sort_by) return;

    setFiltros(f => {
      let order = 'asc';
      if (f.sort_by === sort_by) {
        if (f.sort_order === 'asc') order = 'desc';
        else if (f.sort_order === 'desc') return { ...f, sort_by: '', sort_order: '', page: 1 };
      }
      return { ...f, sort_by, sort_order: order, page: 1 };
    });
  };

  const columns = useMemo(() => [
    {
      id: 'seq',
      header: '#',
      cell: info => {
        const rowIdx = info.row.index;
        return <span style={{ color: 'var(--text-muted)' }}>{(filtros.page - 1) * filtros.limit + rowIdx + 1}</span>;
      }
    },
    {
      id: 'especialista',
      header: 'Especialista',
      cell: info => {
        const esp = info.row.original;
        return (
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            {esp.foto_perfil ? (
              <img src={esp.foto_perfil} alt="" style={{ width: 36, height: 36, borderRadius: '50%', objectFit: 'cover', flexShrink: 0 }} />
            ) : (
              <div style={{ width: 36, height: 36, borderRadius: '50%', background: 'rgba(79,125,255,0.2)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                <RiUserLine size={16} style={{ color: 'var(--color-primary-500)' }} />
              </div>
            )}
            <div>
              <div 
                className="hover:underline hover:text-primary-400 cursor-pointer"
                style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)' }}
                onClick={(e) => { e.stopPropagation(); navigate(`/admin/especialistas/${esp.doctoralia_id}`); }}
              >
                {normalizeName(esp.nombre)}
              </div>
              <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>ID: {esp.doctoralia_id}</div>
            </div>
          </div>
        );
      }
    },
    {
      id: 'especialidades',
      header: 'Especialidades',
      cell: info => {
        const esp = info.row.original;
        const especialidades = esp.especialidades || [];
        if (especialidades.length === 0) return <span style={{ color: 'var(--text-muted)' }}>—</span>;
        return (
          <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
            {especialidades.slice(0, 2).map((es, i) => <Badge key={i} texto={es} color="var(--text-muted)" />)}
            {especialidades.length > 2 && <Badge texto={`+${especialidades.length - 2}`} color="var(--text-muted)" />}
          </div>
        );
      }
    },
    {
      id: 'ciudad',
      header: 'Ciudad',
      cell: info => {
        const esp = info.row.original;
        const ciudades = esp.ciudades || [];
        if (ciudades.length === 0) return <span style={{ color: 'var(--text-muted)' }}>—</span>;
        return (
          <div style={{ display: 'flex', gap: 4, alignItems: 'center' }} className="tooltip-container">
            <span style={{ fontSize: 12, color: 'var(--text-primary)' }}>{ciudades[0]}</span>
            {ciudades.length > 1 && (
              <>
                <Badge texto={`+${ciudades.length - 1}`} color="var(--text-muted)" />
                <span className="tooltip-text">{ciudades.slice(1).join(', ')}</span>
              </>
            )}
          </div>
        );
      }
    },
    {
      id: 'opiniones',
      header: 'Opiniones',
      cell: info => {
        const esp = info.row.original;
        return (
          <div style={{ textAlign: 'right' }}>
            <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)' }}>{fmt(esp.total_opiniones_perfil)}</div>
            <div style={{ fontSize: 10, color: 'var(--text-muted)' }}>en perfil</div>
          </div>
        );
      }
    },
    {
      id: 'fecha_scraping',
      header: 'Último Scraping',
      cell: info => {
        const esp = info.row.original;
        return <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>{fmtFecha(esp.scraping?.fecha_consulta || esp.scraping?.ultimo_scraping)}</div>;
      }
    },
    {
      id: 'acciones',
      header: 'Acciones',
      cell: info => {
        const esp = info.row.original;
        const fuenteUrl = esp.scraping?.fuente;
        return (
          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            {fuenteUrl ? (
              <a 
                href={fuenteUrl} 
                target="_blank" 
                rel="noopener noreferrer" 
                title="Perfil Oficial Doctoralia"
                style={{ color: 'var(--color-primary-500)', background: 'rgba(79,125,255,0.1)', padding: 6, borderRadius: 6 }}
                onClick={(e) => e.stopPropagation()}
              >
                <RiExternalLinkLine size={16} />
              </a>
            ) : (
              <div style={{ width: 28, height: 28 }} />
            )}
            <button
              onClick={(e) => { e.stopPropagation(); setDeleteModal({ open: true, row: esp }); }}
              style={{ color: '#ef4444', background: 'rgba(239,68,68,0.1)', padding: 6, borderRadius: 6, border: 'none', cursor: 'pointer' }}
              title="Eliminar especialista"
              aria-label="Eliminar especialista"
            >
              <RiDeleteBinLine size={16} />
            </button>
          </div>
        );
      }
    }
  ], [filtros.page, filtros.limit, navigate]);

  const espData = useMemo(() => data?.especialistas || [], [data]);

  const table = useReactTable({
    data: espData,
    columns,
    getCoreRowModel: getCoreRowModel(),
    manualPagination: true,
    pageCount: data?.pages || -1,
  });

  if (user?.rol !== 'ADMIN') return null;

  return (
    <PageWrapper name="admin">
      <BubbleBackground />
      <Navbar />

      <div className="relative z-10 pt-24 pb-12 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto" style={{ color: 'var(--text-primary)' }}>

      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 28 }}>
        <div style={{
          width: 40, height: 40, borderRadius: 10,
          background: 'rgba(79,125,255,0.2)', display: 'flex', alignItems: 'center', justifyContent: 'center',
        }}>
          <RiShieldLine size={22} style={{ color: 'var(--color-primary-500)' }} />
        </div>
        <div>
          <h1 style={{ fontSize: 20, fontWeight: 700, margin: 0, color: 'var(--text-primary)' }}>Panel de Administración</h1>
          <p style={{ fontSize: 12, color: 'var(--text-muted)', margin: 0 }}>Vista completa del sistema MedRec</p>
        </div>
        <button
          onClick={cargarTabla}
          className="glass-input"
          style={{ marginLeft: 'auto', borderRadius: 8, padding: '7px 12px', color: 'var(--text-muted)', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6, fontSize: 12 }}
        >
          <RiRefreshLine size={14} /> Actualizar
        </button>
      </div>

      {/* Estadísticas globales */}
      {!cargando && stats && (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4 mb-8">
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
            color="var(--text-muted)"
          />
        </div>
      )}

      {/* TABS */}
      <div className="flex border-b border-[var(--glass-border)] mb-6">
        <button
          className={`px-6 py-3 font-semibold text-[14px] transition-colors ${
            activeTab === 'especialistas'
              ? 'text-[var(--color-primary-500)] border-b-2 border-[var(--color-primary-500)]'
              : 'text-[var(--text-muted)] hover:text-[var(--text-primary)]'
          }`}
          onClick={() => setActiveTab('especialistas')}
        >
          Especialistas
        </button>
        <button
          className={`px-6 py-3 font-semibold text-[14px] transition-colors ${
            activeTab === 'usuarios'
              ? 'text-[var(--color-primary-500)] border-b-2 border-[var(--color-primary-500)]'
              : 'text-[var(--text-muted)] hover:text-[var(--text-primary)]'
          }`}
          onClick={() => setActiveTab('usuarios')}
        >
          Usuarios
        </button>
      </div>

      {activeTab === 'especialistas' && (
        <>
          <UrlScrapingSection onScraped={cargarTabla} />

          {/* Filtros */}
          <PanelFiltros filtros={filtros} onChange={setFiltros} />

          {/* Tabla (TanStack) */}
          <div className="glass-card" style={{
        marginTop: 16, border: '1px solid var(--glass-border)', overflow: 'hidden',
      }}>
        <div style={{ padding: '14px 16px', borderBottom: '1px solid var(--glass-border)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-muted)' }}>
            Especialistas — <span style={{ color: 'var(--text-primary)' }}>{fmt(data?.total)}</span> resultados
          </span>
          {cargandoTabla && <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>Cargando...</span>}
        </div>

        {cargandoTabla && espData.length === 0 ? <div style={{ padding: 20 }}><Skeleton /></div> : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
              <thead>
                {table.getHeaderGroups().map(headerGroup => (
                  <tr key={headerGroup.id} style={{ background: 'var(--glass-bg)' }}>
                    {headerGroup.headers.map(header => {
                      const isSortable = ['especialista', 'especialidades', 'ciudad', 'opiniones', 'fecha_scraping'].includes(header.id);
                      
                      const mapSort = {
                        'especialista': 'doctor.nombre',
                        'especialidades': 'doctor.especialidades',
                        'ciudad': 'doctor.direcciones.ciudad',
                        'opiniones': 'total_opiniones',
                        'fecha_scraping': 'metadata.fecha_consulta'
                      };
                      
                      const isSorted = isSortable && filtros.sort_by === mapSort[header.id];
                      
                      return (
                        <th 
                          key={header.id} 
                          style={{ 
                            padding: '10px 16px', textAlign: 'left', fontSize: 10, fontWeight: 600, 
                            color: isSorted ? 'var(--color-primary-500)' : 'var(--text-muted)', 
                            textTransform: 'uppercase', whiteSpace: 'nowrap',
                            cursor: isSortable ? 'pointer' : 'default',
                            userSelect: 'none'
                          }}
                          onClick={() => isSortable && handleSort(header.id)}
                        >
                          <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                            {header.isPlaceholder ? null : flexRender(header.column.columnDef.header, header.getContext())}
                            {isSortable && (
                              <span style={{ display: 'inline-flex', flexDirection: 'column', fontSize: 10, opacity: isSorted ? 1 : 0.4 }}>
                                {(!isSorted || filtros.sort_order === 'asc') && <RiArrowUpLine style={{ marginBottom: -3 }} />}
                                {(!isSorted || filtros.sort_order === 'desc') && <RiArrowDownLine />}
                              </span>
                            )}
                          </div>
                        </th>
                      )
                    })}
                  </tr>
                ))}
              </thead>
              <tbody>
                {table.getRowModel().rows.map(row => (
                  <tr key={row.id} className="hover:bg-primary-500/10" style={{ borderBottom: '1px solid var(--glass-border)', transition: 'background 0.2s' }}>
                    {row.getVisibleCells().map(cell => (
                      <td key={cell.id} style={{ padding: '12px 16px' }}
                          onClick={(e) => {
                            if (cell.column.id === 'seq' || cell.column.id === 'especialista') {
                                navigate(`/admin/especialistas/${row.original.doctoralia_id}`);
                            }
                          }}
                          className={(cell.column.id === 'seq' || cell.column.id === 'especialista') ? 'cursor-pointer' : ''}
                      >
                        {flexRender(cell.column.columnDef.cell, cell.getContext())}
                      </td>
                    ))}
                  </tr>
                ))}
                {espData.length === 0 && (
                  <tr>
                    <td colSpan={columns.length} style={{ padding: 40, textAlign: 'center', color: 'var(--text-muted)' }}>
                      Sin resultados para la búsqueda actual
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}

        <Pagination 
          page={filtros.page} 
          pages={data?.pages || 0} 
          limit={filtros.limit}
          onPageChange={p => setFiltros(f => ({ ...f, page: p }))}
          onLimitChange={l => setFiltros(f => ({ ...f, limit: l, page: 1 }))}
        />
      </div>
        </>
      )}

      {activeTab === 'usuarios' && <UsersTab />}

      <ConfirmModal 
        isOpen={deleteModal.open}
        onClose={() => setDeleteModal({ open: false, row: null })}
        onConfirm={handleDelete}
        title="Eliminar Especialista"
        message={`¿Estás seguro de que deseas eliminar a ${deleteModal.row?.nombre}? Esta operación es destructiva e irreversible. También se eliminarán las opiniones y el análisis IA asociado.`}
        confirmText="Eliminar permanentemente"
        cancelText="Cancelar"
      />

      </div>
    </PageWrapper>
  );
}
