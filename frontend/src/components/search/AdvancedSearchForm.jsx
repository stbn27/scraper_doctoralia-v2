import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { RiCloseLine, RiRobot2Line, RiSearchLine, RiInformationLine, RiCheckLine, RiErrorWarningLine } from 'react-icons/ri';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Checkbox } from '@/components/ui/Checkbox';
import Select from 'react-select';
import { selectStyles } from '@/components/ui/selectStyles';
import { useToast } from '@/hooks/useToast';
import { scrapeAnalyze, listarTokensLLM } from '@/services/api';

const maxOpinionsOptions = [
  { value: 20, label: '20 opiniones' },
  { value: 30, label: '30 opiniones' },
  { value: 40, label: '40 opiniones' },
  { value: 50, label: '50 opiniones' },
];

export function AdvancedSearchForm({ onClose }) {
  const navigate = useNavigate();
  const { addToast } = useToast();
  const [url, setUrl] = useState('');
  const [maxOpinions, setMaxOpinions] = useState(30);
  const [scrapeOnly, setScrapeOnly] = useState(false);
  const [analyze, setAnalyze] = useState(true);
  
  const [tokens, setTokens] = useState([]);
  const [loadingTokens, setLoadingTokens] = useState(true);
  const [selectedModel, setSelectedModel] = useState('');
  
  const [processing, setProcessing] = useState(false);
  const [result, setResult] = useState(null);
  const [showTokenModal, setShowTokenModal] = useState(false);

  useEffect(() => {
    const fetchTokens = async () => {
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
    };
    fetchTokens();
  }, []);

  const handleSubmit = async () => {
    if (!url.includes('doctoralia.com.mx') && !url.includes('doctoralia.es') && !url.includes('doctoralia.co')) {
      addToast({ type: 'error', message: 'Debe ser una URL válida de Doctoralia' });
      return;
    }
    if (analyze && !selectedModel) {
      setShowTokenModal(true);
      return;
    }

    setProcessing(true);
    setResult(null);

    try {
      const response = await scrapeAnalyze({
        url,
        max_opinions: parseInt(maxOpinions, 10),
        scrape_only: scrapeOnly,
        analyze: analyze,
        model: analyze ? selectedModel : null
      });
      
      setResult({ success: true, ...response });
      addToast({ type: 'success', message: 'Proceso finalizado con éxito' });
    } catch (err) {
      console.error(err);
      
      // Check if it's a token error (400)
      if (err.message && err.message.toLowerCase().includes('token')) {
        setShowTokenModal(true);
      } else {
        setResult({ success: false, error: err.message || 'Ocurrió un error en el proceso' });
      }
    } finally {
      setProcessing(false);
    }
  };

  const handleCheckboxChange = (type) => {
    if (type === 'scrape') {
      setScrapeOnly(!scrapeOnly);
      if (!scrapeOnly) setAnalyze(false); // Si marco solo scrape, desmarco analyze
    } else {
      setAnalyze(!analyze);
      if (!analyze) setScrapeOnly(false); // Si marco analyze, desmarco solo scrape
    }
  };

  return (
    <div className="glass-card overflow-hidden p-8 sm:p-10 relative animation-fade-in">
      <button 
        onClick={onClose}
        className="absolute top-4 right-4 p-2 rounded-full bg-white/5 hover:bg-white/10 text-white transition-colors"
        title="Cerrar Búsqueda Avanzada"
      >
        <RiCloseLine size={24} />
      </button>

      <div className="mx-auto max-w-2xl">
        <div className="flex items-center gap-4 mb-6">
          <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-royalBlue-600 text-white shadow-lg shadow-royalBlue-600/30">
            <RiRobot2Line className="text-2xl" />
          </div>
          <div>
            <h2 className="text-2xl font-semibold">Búsqueda Avanzada y Análisis IA</h2>
            <p className="text-sm text-slate-400">Pega el perfil del especialista para analizarlo en tiempo real.</p>
          </div>
        </div>

        <div className="space-y-6">
          <Input
            id="adv-url"
            label="URL de Doctoralia *"
            placeholder="https://www.doctoralia.com.mx/..."
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            disabled={processing}
          />

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 items-end">
            <div className="space-y-1.5">
              <label className="block text-sm font-medium" style={{ color: 'var(--text-muted)' }}>
                Opiniones a analizar (Max)
              </label>
              <Select
                styles={selectStyles}
                options={maxOpinionsOptions}
                value={maxOpinionsOptions.find(opt => opt.value === maxOpinions) || maxOpinionsOptions[1]}
                onChange={(selected) => setMaxOpinions(selected ? selected.value : 30)}
                isDisabled={processing}
                placeholder="Selecciona opiniones..."
              />
            </div>

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

          {analyze && (
            <div className="p-4 rounded-xl bg-white/5 border border-white/10 space-y-3">
              <label className="block text-sm font-medium text-slate-300">
                Selecciona tu modelo de IA:
              </label>
              
              {loadingTokens ? (
                <p className="text-sm text-slate-400">Cargando tokens...</p>
              ) : tokens.length === 0 ? (
                <div className="flex items-center justify-between p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400">
                  <div className="flex items-center gap-2">
                    <RiErrorWarningLine />
                    <span className="text-sm">No tienes tokens configurados</span>
                  </div>
                  <Button variant="ghost" className="text-xs" onClick={() => navigate('/perfil')}>
                    Ir al Perfil
                  </Button>
                </div>
              ) : (
                <select
                  value={selectedModel}
                  onChange={(e) => setSelectedModel(e.target.value)}
                  disabled={processing}
                  className="w-full bg-slate-900 border border-white/10 rounded-lg px-4 py-2.5 text-sm text-white focus:ring-2 focus:ring-royalBlue-500"
                >
                  {tokens.map(t => (
                    <option key={t.modelo} value={t.modelo}>{t.modelo.toUpperCase()}</option>
                  ))}
                </select>
              )}
            </div>
          )}

          <div className="pt-4 flex justify-end">
            <Button 
              variant="primary" 
              onClick={handleSubmit} 
              loading={processing}
              disabled={!url || (analyze && tokens.length === 0)}
              className="px-8"
            >
              {processing ? 'Procesando...' : 'Iniciar Proceso'}
            </Button>
          </div>

          {/* Resultado o Error */}
          {result && (
            <div className={`mt-6 p-4 rounded-xl border ${result.success ? 'bg-emerald-500/10 border-emerald-500/30' : 'bg-red-500/10 border-red-500/30'}`}>
              <div className="flex items-start gap-3">
                {result.success ? <RiCheckLine className="text-emerald-400 text-xl mt-0.5" /> : <RiErrorWarningLine className="text-red-400 text-xl mt-0.5" />}
                <div>
                  <h4 className={`font-medium ${result.success ? 'text-emerald-400' : 'text-red-400'}`}>
                    {result.success ? 'Proceso Completado' : 'Error'}
                  </h4>
                  <p className="text-sm text-slate-300 mt-1">
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

      {/* Modal / Alert de Token Faltante (Estilo iOS) */}
      {showTokenModal && (
        <div className="absolute inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-sm animation-fade-in">
          <div className="bg-[#1c1c1e] w-[300px] rounded-2xl overflow-hidden shadow-2xl flex flex-col items-center border border-white/5 transform scale-100 transition-transform">
            <div className="p-6 text-center space-y-2">
              <h3 className="text-lg font-semibold text-white">Token Requerido</h3>
              <p className="text-sm text-slate-300">
                Necesitas agregar un API Key (token) en tu perfil para poder realizar análisis con IA.
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
