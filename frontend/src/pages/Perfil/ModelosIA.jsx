import React, { useState, useEffect } from 'react';
import { RiRobot2Line, RiAddLine, RiDeleteBinLine, RiSave3Line } from 'react-icons/ri';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { ConfirmModal } from '@/components/ui/ConfirmModal';
import { useToast } from '@/hooks/useToast';
import { listarTokensLLM, guardarTokenLLM, eliminarTokenLLM } from '@/services/api';

const MODELOS_DISPONIBLES = [
  { id: 'deepseek', nombre: 'DeepSeek' },
  { id: 'gemini', nombre: 'Google Gemini' },
  { id: 'groq', nombre: 'Groq' },
  { id: 'minimax', nombre: 'MiniMax' },
  { id: 'xiaomi', nombre: 'Xiaomi' }
];

export function ModelosIA() {
  const { addToast } = useToast();
  const [tokens, setTokens] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  
  // Formulario
  const [modeloSeleccionado, setModeloSeleccionado] = useState('');
  const [tokenValor, setTokenValor] = useState('');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    cargarTokens();
  }, []);

  const cargarTokens = async () => {
    setLoading(true);
    try {
      const data = await listarTokensLLM();
      setTokens(Array.isArray(data) ? data : []);
    } catch (error) {
      console.error('Error al cargar tokens', error);
      addToast({ type: 'error', message: 'Error al cargar tokens de IA' });
    } finally {
      setLoading(false);
    }
  };

  const handleSaveToken = async () => {
    if (!modeloSeleccionado || !tokenValor.trim()) {
      addToast({ type: 'error', message: 'Selecciona un modelo y escribe el token' });
      return;
    }

    setSaving(true);
    try {
      await guardarTokenLLM(modeloSeleccionado, tokenValor);
      addToast({ type: 'success', message: 'Token guardado con éxito' });
      setShowForm(false);
      setModeloSeleccionado('');
      setTokenValor('');
      cargarTokens();
    } catch (error) {
      addToast({ type: 'error', message: 'Error al guardar el token' });
    } finally {
      setSaving(false);
    }
  };

  const [modelToDelete, setModelToDelete] = useState(null);

  const handleDeleteClick = (modelo) => {
    setModelToDelete(modelo);
  };

  const handleConfirmDelete = async () => {
    if (!modelToDelete) return;
    try {
      await eliminarTokenLLM(modelToDelete);
      addToast({ type: 'success', message: 'Token eliminado' });
      cargarTokens();
    } catch (error) {
      addToast({ type: 'error', message: 'Error al eliminar el token' });
    } finally {
      setModelToDelete(null);
    }
  };

  const getNombreModelo = (id) => {
    const mod = MODELOS_DISPONIBLES.find(m => m.id === id);
    return mod ? mod.nombre : id;
  };

  return (
    <div className="glass-card p-6 space-y-4">
      <div className="flex items-center justify-between border-b border-white/10 pb-3">
        <h3 className="text-lg font-semibold flex items-center gap-2">
          <RiRobot2Line className="text-royalBlue-400" /> Modelos IA
        </h3>
        {!showForm && (
          <Button
            variant="outline"
            icon={<RiAddLine />}
            onClick={() => setShowForm(true)}
            className="text-xs py-1.5 px-3"
          >
            Añadir Token
          </Button>
        )}
      </div>

      {showForm && (
        <div className="p-4 rounded-xl bg-white/5 border border-white/5 space-y-4 transition-all">
          <h4 className="text-sm font-semibold text-royalBlue-300">Nuevo Token</h4>
          
          <div className="grid grid-cols-1 gap-4">
            <div className="space-y-1.5">
              <label className="block text-xs font-semibold opacity-80" style={{ color: 'var(--text-muted)' }}>
                Modelo *
              </label>
              <select
                value={modeloSeleccionado}
                onChange={(e) => setModeloSeleccionado(e.target.value)}
                className="glass-input w-full px-4 py-2.5 text-sm"
              >
                <option value="" className="bg-slate-900">Seleccionar modelo...</option>
                {MODELOS_DISPONIBLES.map(mod => (
                  <option key={mod.id} value={mod.id} className="bg-slate-900">
                    {mod.nombre}
                  </option>
                ))}
              </select>
            </div>
            
            <Input
              id="token-valor"
              label="API Key *"
              type="password"
              value={tokenValor}
              onChange={(e) => setTokenValor(e.target.value)}
              placeholder="Ej. sk-..."
            />
          </div>

          <div className="flex items-center justify-end gap-2 pt-2">
            <Button
              variant="ghost"
              onClick={() => setShowForm(false)}
              className="text-xs"
            >
              Cancelar
            </Button>
            <Button
              variant="primary"
              onClick={handleSaveToken}
              loading={saving}
              icon={<RiSave3Line />}
              className="text-xs"
            >
              Guardar
            </Button>
          </div>
        </div>
      )}

      {loading ? (
        <div className="py-8 text-center text-sm" style={{ color: 'var(--text-muted)' }}>
          Cargando tokens...
        </div>
      ) : tokens.length > 0 ? (
        <div className="space-y-3">
          {tokens.map((tok) => (
            <div
              key={tok.modelo}
              className="p-4 rounded-xl border transition-all flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-white/5 border-white/5 hover:border-white/10"
            >
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <strong className="text-sm text-slate-100">{getNombreModelo(tok.modelo)}</strong>
                </div>
                <p className="text-xs text-slate-300 font-mono">
                  ••••••••••••••••{tok.token.slice(-4)}
                </p>
                <p className="text-[11px]" style={{ color: 'var(--text-muted)' }}>
                  Actualizado: {new Date(tok.actualizado_en || tok.creado_en).toLocaleDateString()}
                </p>
              </div>

              <div className="flex items-center gap-2 self-end sm:self-auto">
                <button
                  onClick={() => handleDeleteClick(tok.modelo)}
                  className="p-2 rounded-lg hover:bg-red-500/10 text-red-500 transition-colors"
                  title="Eliminar"
                >
                  <RiDeleteBinLine />
                </button>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="py-8 text-center text-sm" style={{ color: 'var(--text-muted)' }}>
          No tienes tokens de IA configurados.
        </div>
      )}

      <ConfirmModal
        isOpen={!!modelToDelete}
        onClose={() => setModelToDelete(null)}
        onConfirm={handleConfirmDelete}
        title="Eliminar Token"
        message={`¿Estás seguro de que deseas eliminar el token de IA para ${getNombreModelo(modelToDelete)}? Esta acción no se puede deshacer.`}
      />
    </div>
  );
}
