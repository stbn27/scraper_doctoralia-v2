import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  RiCloseLine, RiRobot2Line, RiCheckLine, RiErrorWarningLine,
  RiServerLine, RiLoader4Line,
} from 'react-icons/ri';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Checkbox } from '@/components/ui/Checkbox';
import Select from 'react-select';
import { selectStyles } from '@/components/ui/selectStyles';
import { useToast } from '@/hooks/useToast';
import { scrapeAnalyze, listarTokensLLM, realizarPeticion } from '@/services/api';

const maxOpinionsOptions = [
  { value: 20, label: '20 opiniones' },
  { value: 30, label: '30 opiniones' },
  { value: 40, label: '40 opiniones' },
  { value: 50, label: '50 opiniones' },
];

/**
 * AdvancedSearchForm — Formulario de scraping en tiempo real + análisis IA.
 *
 * @param {Function} props.onClose - Callback para cerrar el formulario
 */
export function AdvancedSearchForm({ onClose }) {
  const navigate = useNavigate();
  const { addToast } = useToast();

  // — URL y opciones
  const [url, setUrl] = useState('');
  const [maxOpinions, setMaxOpinions] = useState(30);
  const [scrapeOnly, setScrapeOnly] = useState(false);
  const [analyze, setAnalyze] = useState(true);

  // — Tokens de usuario (modelos externos)
  const [tokens, setTokens] = useState([]);
  const [loadingTokens, setLoadingTokens] = useState(true);
  const [selectedModel, setSelectedModel] = useState('');

  // — Estado de Ollama local
  const [ollamaStatus, setOllamaStatus] = useState(null); // null = cargando, {disponible, modelos}
  const [selectedOllamaModel, setSelectedOllamaModel] = useState('');

  // — Flujo
  const [processing, setProcessing] = useState(false);
  const [result, setResult] = useState(null);
  const [showTokenModal, setShowTokenModal] = useState(false);

  // Determina si el modelo seleccionado es local (Ollama o LM Studio)
  const esLocal = selectedModel === 'local';

  // ── Carga inicial: tokens del usuario + estado Ollama ──
  useEffect(() => {
    const init = async () => {
      // Cargar tokens del usuario
      try {
        const data = await listarTokensLLM();
        const availableTokens = Array.isArray(data) ? data : [];
        setTokens(availableTokens);
        if (availableTokens.length > 0) {
          setSelectedModel(availableTokens[0].modelo);
        }
      } catch (err) {
        console.error('Error al cargar tokens', err);
      } finally {
        setLoadingTokens(false);
      }

      // Siempre verificar proveedores locales al montar si analyze está activo
      if (analyze) {
        try {
          setOllamaStatus({ cargando: true });
          const data = await realizarPeticion('/especialistas/avanzada/ollama-status');
          // modelos es ahora array de {name, proveedor}
          const modelos = data?.modelos || [];
          setOllamaStatus({ disponible: data?.disponible === true, modelos, ollama: !!data?.ollama, lm_studio: !!data?.lm_studio });
          if (data?.disponible && modelos.length > 0) {
            setSelectedOllamaModel(modelos[0].name);
            // Auto-seleccionar local si no hay tokens configurados
            setSelectedModel((prev) => (prev === '' ? 'local' : prev));
          }
        } catch {
          setOllamaStatus({ disponible: false, modelos: [], ollama: false, lm_studio: false });
        }
      }
    };
    init();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Verificar Ollama cuando el usuario activa el análisis con IA
  const verificarOllama = useCallback(async () => {
    if (ollamaStatus !== null) return; // ya se verificó
    setOllamaStatus({ cargando: true });
    try {
      const data = await realizarPeticion('/especialistas/avanzada/ollama-status');
      const modelos = data?.modelos || [];
      setOllamaStatus({ disponible: data?.disponible === true, modelos, ollama: !!data?.ollama, lm_studio: !!data?.lm_studio });
      if (data?.disponible && modelos.length > 0) {
        setSelectedOllamaModel(modelos[0].name);
        // Solo auto-seleccionar local si el usuario no tiene otros tokens
        setSelectedModel((prev) => (prev === '' ? 'local' : prev));
      }
    } catch {
      setOllamaStatus({ disponible: false, modelos: [], ollama: false, lm_studio: false });
    }
  }, [ollamaStatus]);

  const handleCheckboxChange = (type) => {
    if (type === 'scrape') {
      const next = !scrapeOnly;
      setScrapeOnly(next);
      if (next) setAnalyze(false);
    } else {
      const next = !analyze;
      setAnalyze(next);
      if (next) {
        setScrapeOnly(false);
        verificarOllama();
      }
    }
  };

  // ── Enviar ──
  const handleSubmit = async () => {
    const urlTrimmed = url.trim();
    if (
      !urlTrimmed.includes('doctoralia.com.mx') &&
      !urlTrimmed.includes('doctoralia.es') &&
      !urlTrimmed.includes('doctoralia.co')
    ) {
      addToast({ type: 'error', message: 'Debe ser una URL válida de Doctoralia.' });
      return;
    }

    if (analyze) {
      // Si seleccionó un proveedor local, verificar que esté disponible
      if (esLocal) {
        if (!ollamaStatus?.disponible) {
          addToast({ type: 'error', message: 'Ningún proveedor local (Ollama / LM Studio) está disponible.' });
          return;
        }
      } else if (!selectedModel) {
        // Solo mostrar el modal si TAMPOCO hay proveedor local disponible
        const localDisponible = ollamaStatus?.disponible && (ollamaStatus?.modelos?.length ?? 0) > 0;
        if (!localDisponible) {
          setShowTokenModal(true);
          return;
        }
        // Si hay proveedor local disponible pero no estaba seleccionado, seleccionarlo ahora
        setSelectedModel('local');
        if (ollamaStatus.modelos.length > 0 && !selectedOllamaModel) {
          setSelectedOllamaModel(ollamaStatus.modelos[0].name);
        }
        return; // Dejar que el usuario revise y vuelva a enviar
      }
    }

    setProcessing(true);
    setResult(null);

    try {
      const payload = {
        url: urlTrimmed,
        max_opinions: parseInt(maxOpinions, 10),
        scrape_only: scrapeOnly,
        analyze,
        model: analyze ? (esLocal ? 'local' : selectedModel) : null,
        ollama_model: analyze && esLocal ? selectedOllamaModel : null,
      };

      const response = await scrapeAnalyze(payload);
      setResult({ success: true, ...response });
      addToast({ type: 'success', message: 'Proceso finalizado con éxito.' });
    } catch (err) {
      console.error('[AdvancedSearchForm] Error:', err);
      if (err.message?.toLowerCase().includes('token')) {
        setShowTokenModal(true);
      } else {
        setResult({ success: false, error: err.message || 'Ocurrió un error en el proceso.' });
      }
    } finally {
      setProcessing(false);
    }
  };

  // ── Opciones de modelo ──
  // Etiqueta descriptiva para cada proveedor local
  const proveedorLabel = (proveedor) => {
    if (proveedor === 'lm_studio') return 'LM Studio';
    return 'Ollama';
  };

  const modelOptions = [
    ...tokens.map((t) => ({
      value: t.modelo,
      label: `${t.modelo.toUpperCase()} (token propio)`,
      group: 'API Externas',
    })),
    ...(ollamaStatus?.disponible
      ? [{ value: 'local', label: proveedorLabel((ollamaStatus.modelos[0] || {}).proveedor), group: 'Local' }]
      : []),
  ];

  const isSubmitDisabled =
    !url.trim() ||
    processing ||
    (analyze && !selectedModel) ||
    (analyze && esLocal && !ollamaStatus?.disponible);

  // ── Render ──
  return (
    <div className="glass-card overflow-hidden p-8 sm:p-10 relative">
      {/* Botón cerrar */}
      <button
        onClick={onClose}
        className="absolute top-4 right-4 p-2 rounded-full bg-white/5 hover:bg-white/10 text-white transition-colors z-10"
        title="Cerrar Búsqueda Avanzada"
      >
        <RiCloseLine size={22} />
      </button>

      <div className="mx-auto max-w-2xl">
        {/* Header */}
        <div className="flex items-center gap-4 mb-8">
          <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-royalBlue-600 text-white shadow-lg shadow-royalBlue-600/30 shrink-0">
            <RiRobot2Line className="text-2xl" />
          </div>
          <div>
            <h2 className="text-2xl font-semibold">Búsqueda Avanzada y Análisis IA</h2>
            <p className="text-sm text-slate-400">
              Pega el perfil del especialista para analizarlo en tiempo real.
            </p>
          </div>
        </div>

        <div className="space-y-6">
          {/* URL */}
          <Input
            id="adv-url"
            label="URL de Doctoralia *"
            placeholder="https://www.doctoralia.com.mx/nombre-doctor/especialidad/ciudad"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            disabled={processing}
          />

          {/* Opciones */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 items-end">
            {/* Max opiniones */}
            <div className="space-y-1.5">
              <label className="block text-sm font-medium" style={{ color: 'var(--text-muted)' }}>
                Opiniones a analizar (Máx)
              </label>
              <Select
                styles={selectStyles}
                options={maxOpinionsOptions}
                value={maxOpinionsOptions.find((opt) => opt.value === maxOpinions) || maxOpinionsOptions[1]}
                onChange={(selected) => setMaxOpinions(selected ? selected.value : 30)}
                isDisabled={processing}
                menuPortalTarget={document.body}
              />
            </div>

            {/* Checkboxes */}
            <div className="space-y-3 pb-1">
              <Checkbox
                id="scrape-only"
                label="Solo hacer Scraping (Extraer datos)"
                checked={scrapeOnly}
                onChange={() => handleCheckboxChange('scrape')}
                disabled={processing}
              />
              <Checkbox
                id="analyze-ia"
                label="Realizar Análisis con IA"
                checked={analyze}
                onChange={() => handleCheckboxChange('analyze')}
                disabled={processing}
              />
            </div>
          </div>

          {/* Panel de selección de modelo (cuando analyze=true) */}
          {analyze && (
            <div className="p-4 rounded-xl bg-white/5 border border-white/10 space-y-4">
              <label className="block text-sm font-medium text-slate-300">
                Modelo de IA a usar:
              </label>

              {/* Estado de Ollama */}
              <OllamaStatusBadge status={ollamaStatus} />

              {loadingTokens ? (
                <p className="text-sm text-slate-400 flex items-center gap-2">
                  <RiLoader4Line className="animate-spin" /> Cargando modelos disponibles...
                </p>
              ) : modelOptions.length === 0 ? (
                /* Sin tokens disponibles */
                <div className="flex items-center justify-between p-3 rounded-lg bg-amber-500/10 border border-amber-500/20">
                  <div className="flex items-center gap-2 text-amber-400">
                    <RiErrorWarningLine />
                    <span className="text-sm">
                      {ollamaStatus?.cargando
                        ? 'Buscando modelos disponibles...'
                        : 'No tienes tokens configurados. Agrega uno desde tu perfil para continuar.'}
                    </span>
                  </div>
                  <Button variant="ghost" className="text-xs shrink-0" onClick={() => navigate('/perfil')}>
                    Agregar Token
                  </Button>
                </div>
              ) : (
                /* Selector de modelo */
                <select
                  value={selectedModel}
                  onChange={(e) => setSelectedModel(e.target.value)}
                  disabled={processing}
                  className="w-full bg-slate-900 border border-white/10 rounded-lg px-4 py-2.5 text-sm text-white focus:ring-2 focus:ring-royalBlue-500"
                >
                  {modelOptions.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
              )}

              {/* Si seleccionó un proveedor local, mostrar selector de modelo */}
              {esLocal && ollamaStatus?.disponible && ollamaStatus.modelos.length > 0 && (
                <div className="space-y-1.5">
                  <label className="block text-xs font-medium" style={{ color: 'var(--text-muted)' }}>
                    Modelo local:
                  </label>
                  <select
                    value={selectedOllamaModel}
                    onChange={(e) => setSelectedOllamaModel(e.target.value)}
                    disabled={processing}
                    className="w-full bg-slate-900 border border-white/10 rounded-lg px-4 py-2 text-sm text-white focus:ring-2 focus:ring-royalBlue-500"
                  >
                    {ollamaStatus.modelos.map((m) => (
                      <option key={m.name} value={m.name}>
                        {m.name} ({m.proveedor === 'lm_studio' ? 'LM Studio' : 'Ollama'})
                      </option>
                    ))}
                  </select>
                </div>
              )}
            </div>
          )}

          {/* Botón enviar */}
          <div className="pt-2 flex justify-end">
            <Button
              variant="primary"
              onClick={handleSubmit}
              loading={processing}
              disabled={isSubmitDisabled}
              className="px-8"
            >
              {processing ? 'Procesando...' : 'Iniciar Proceso'}
            </Button>
          </div>

          {/* Resultado */}
          {result && (
            <div
              className={`mt-4 p-4 rounded-xl border ${result.success
                  ? 'bg-emerald-500/10 border-emerald-500/30'
                  : 'bg-red-500/10 border-red-500/30'
                }`}
            >
              <div className="flex items-start gap-3">
                {result.success ? (
                  <RiCheckLine className="text-emerald-400 text-xl mt-0.5 shrink-0" />
                ) : (
                  <RiErrorWarningLine className="text-red-400 text-xl mt-0.5 shrink-0" />
                )}
                <div className="min-w-0">
                  <h4 className={`font-medium ${result.success ? 'text-emerald-400' : 'text-red-400'}`}>
                    {result.success ? 'Proceso Completado' : 'Error en el proceso'}
                  </h4>
                  <p className="text-sm text-slate-300 mt-1 break-words">
                    {result.error || result.mensaje}
                  </p>
                  {result.success && result.especialista_id && (
                    <div className="mt-3">
                      <Button
                        variant="outline"
                        className="text-xs"
                        onClick={() => navigate(`/especialistas/${result.especialista_id}`)}
                      >
                        Ver Perfil del Especialista
                      </Button>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Modal iOS — Token requerido */}
      {showTokenModal && (
        <div className="absolute inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
          <div className="bg-[#1c1c1e] w-[300px] rounded-2xl overflow-hidden shadow-2xl flex flex-col items-center border border-white/5">
            <div className="p-6 text-center space-y-2">
              <h3 className="text-lg font-semibold text-white">Token Requerido</h3>
              <p className="text-sm text-slate-300">
                Necesitas agregar un API Key en tu perfil para poder realizar análisis con IA, o
                puedes instalar Ollama localmente para hacerlo sin costo.
              </p>
            </div>
            <div className="w-full flex flex-col border-t border-white/10">
              <button
                className="w-full py-3 text-royalBlue-400 font-semibold hover:bg-white/5 transition-colors border-b border-white/10"
                onClick={() => navigate('/perfil')}
              >
                Ir a agregar token
              </button>
              <button
                className="w-full py-3 text-white hover:bg-white/5 transition-colors font-medium"
                onClick={() => setShowTokenModal(false)}
              >
                Cancelar
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ── Sub-componente: badge de estado de proveedores locales ──
function OllamaStatusBadge({ status }) {
  if (!status) return null;

  if (status.cargando) {
    return (
      <div className="flex items-center gap-2 text-slate-400 text-xs">
        <RiLoader4Line className="animate-spin" />
        Verificando proveedores locales (Ollama / LM Studio)...
      </div>
    );
  }

  if (status.disponible) {
    const proveedoresActivos = [
      status.ollama && 'Ollama',
      status.lm_studio && 'LM Studio',
    ].filter(Boolean).join(' + ');

    return (
      <div className="flex items-center gap-2 text-emerald-400 text-xs bg-emerald-500/10 border border-emerald-500/20 px-3 py-1.5 rounded-lg">
        <RiServerLine />
        <span>
          {proveedoresActivos} disponible — {status.modelos.length} modelo{status.modelos.length !== 1 ? 's' : ''} instalado{status.modelos.length !== 1 ? 's' : ''}
        </span>
      </div>
    );
  }

  return (
    <div className="flex items-center gap-2 text-slate-500 text-xs">
      <RiServerLine />
      Sin proveedores locales disponibles. Agrega un token de API en tu perfil para continuar.
    </div>
  );
}
