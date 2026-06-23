import React, { useState, useEffect } from 'react';
import { getUsuariosAdmin } from '@/services/admin.api';
import { useToast } from '@/hooks/useToast';
import { Button } from '@/components/ui/Button';
import { RiSearchLine, RiEyeLine, RiCloseLine, RiUserLine } from 'react-icons/ri';
import { Pagination } from './index';

function fmtFecha(iso) {
  if (!iso) return 'N/A';
  try {
    return new Intl.DateTimeFormat('es-MX', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(iso));
  } catch (e) {
    return iso;
  }
}

export function UsersTab() {
  const { addToast } = useToast();
  const [data, setData] = useState({ usuarios: [], total: 0, page: 1, pages: 1 });
  const [loading, setLoading] = useState(true);
  const [filtros, setFiltros] = useState({ q: '', page: 1, limit: 20 });
  const [qInput, setQInput] = useState('');
  const [selectedUser, setSelectedUser] = useState(null);

  const cargarUsuarios = async () => {
    setLoading(true);
    try {
      const res = await getUsuariosAdmin(filtros);
      setData({ usuarios: res.usuarios || [], total: res.total, page: res.page, pages: res.pages });
    } catch (e) {
      addToast({ type: 'error', message: 'Error al cargar usuarios' });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    cargarUsuarios();
  }, [filtros]); // eslint-disable-line

  useEffect(() => {
    const handler = setTimeout(() => {
      if (qInput !== filtros.q) {
        setFiltros(f => ({ ...f, q: qInput, page: 1 }));
      }
    }, 500);
    return () => clearTimeout(handler);
  }, [qInput, filtros.q]);

  return (
    <div className="flex flex-col gap-6">
      <div className="glass-card flex gap-2 items-center p-4 border border-[var(--glass-border)]">
        <RiSearchLine className="text-[var(--text-muted)]" />
        <input
          value={qInput}
          onChange={e => setQInput(e.target.value)}
          placeholder="Buscar por nombre, email..."
          className="glass-input flex-1 px-3 py-2 text-[13px]"
          disabled={loading}
        />
      </div>

      <div className="glass-card border border-[var(--glass-border)] overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-[13px] text-[var(--text-primary)]">
            <thead className="bg-[var(--glass-bg)] border-b border-[var(--glass-border)]">
              <tr>
                <th className="px-4 py-3 font-semibold">Usuario</th>
                <th className="px-4 py-3 font-semibold">Email</th>
                <th className="px-4 py-3 font-semibold">Rol</th>
                <th className="px-4 py-3 font-semibold">Registro</th>
                <th className="px-4 py-3 font-semibold text-center">Acción</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan={5} className="text-center py-8 text-[var(--text-muted)]">Cargando...</td></tr>
              ) : data.usuarios.length === 0 ? (
                <tr><td colSpan={5} className="text-center py-8 text-[var(--text-muted)]">No se encontraron usuarios.</td></tr>
              ) : (
                data.usuarios.map(u => (
                  <tr key={u.id} className="border-b border-[var(--glass-border)] hover:bg-white/5 transition-colors">
                    <td className="px-4 py-3 font-medium">
                      <div className="flex items-center gap-2">
                        {u.avatar_url ? (
                          <img src={u.avatar_url} alt="avatar" className="w-6 h-6 rounded-full" />
                        ) : (
                          <div className="w-6 h-6 rounded-full bg-[var(--glass-bg)] border border-[var(--glass-border)] flex items-center justify-center text-[10px] text-[var(--text-muted)]">
                            {u.nombre ? u.nombre.charAt(0).toUpperCase() : <RiUserLine />}
                          </div>
                        )}
                        <span>{u.nombre} {u.apellido}</span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-[var(--text-muted)]">{u.email}</td>
                    <td className="px-4 py-3">
                      <span className={`text-[10px] px-2 py-1 rounded-full font-semibold ${u.rol === 'ADMIN' ? 'bg-amber-500/20 text-amber-500' : 'bg-emerald-500/20 text-emerald-500'}`}>
                        {u.rol}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-[11px] text-[var(--text-muted)]">{fmtFecha(u.created_at)}</td>
                    <td className="px-4 py-3 text-center">
                      <Button variant="secondary" onClick={() => setSelectedUser(u)} className="text-xs px-2 py-1 h-auto">
                        <RiEyeLine className="mr-1" /> Ver info
                      </Button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        <Pagination
          page={data.page}
          pages={data.pages}
          limit={filtros.limit}
          onPageChange={p => setFiltros(f => ({ ...f, page: p }))}
          onLimitChange={l => setFiltros(f => ({ ...f, limit: l, page: 1 }))}
        />
      </div>

      {selectedUser && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm" onClick={() => setSelectedUser(null)}>
          <div className="glass-card w-full max-w-md p-6 border border-[var(--glass-border)] bg-[var(--bg-body)]" onClick={e => e.stopPropagation()}>
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-bold flex items-center gap-2"><RiUserLine /> Información del Usuario</h3>
              <button onClick={() => setSelectedUser(null)} className="text-[var(--text-muted)] hover:text-[var(--text-primary)]">
                <RiCloseLine size={24} />
              </button>
            </div>
            
            <div className="flex flex-col gap-3 text-[13px]">
              <div className="flex items-center gap-4 border-b border-[var(--glass-border)] pb-4">
                 {selectedUser.avatar_url ? (
                    <img src={selectedUser.avatar_url} alt="avatar" className="w-12 h-12 rounded-full border border-[var(--glass-border)]" />
                  ) : (
                    <div className="w-12 h-12 rounded-full bg-[var(--glass-bg)] border border-[var(--glass-border)] flex items-center justify-center text-lg text-[var(--text-muted)]">
                      {selectedUser.nombre ? selectedUser.nombre.charAt(0).toUpperCase() : <RiUserLine />}
                    </div>
                  )}
                  <div>
                    <div className="font-bold text-[15px]">{selectedUser.nombre} {selectedUser.apellido}</div>
                    <div className="text-[var(--text-muted)]">{selectedUser.email}</div>
                  </div>
              </div>
              <div className="flex justify-between border-b border-[var(--glass-border)] py-2">
                <span className="text-[var(--text-muted)]">ID:</span>
                <span className="font-medium">{selectedUser.id}</span>
              </div>
              <div className="flex justify-between border-b border-[var(--glass-border)] py-2">
                <span className="text-[var(--text-muted)]">Teléfono:</span>
                <span className="font-medium">{selectedUser.telefono || 'No registrado'}</span>
              </div>
              <div className="flex justify-between border-b border-[var(--glass-border)] py-2">
                <span className="text-[var(--text-muted)]">Rol:</span>
                <span className={`text-[10px] px-2 py-0.5 rounded-full font-semibold ${selectedUser.rol === 'ADMIN' ? 'bg-amber-500/20 text-amber-500' : 'bg-emerald-500/20 text-emerald-500'}`}>
                  {selectedUser.rol}
                </span>
              </div>
              <div className="flex justify-between border-b border-[var(--glass-border)] py-2">
                <span className="text-[var(--text-muted)]">Registro:</span>
                <span className="font-medium">{fmtFecha(selectedUser.created_at)}</span>
              </div>
            </div>

            <div className="mt-6 flex justify-end">
              <Button onClick={() => setSelectedUser(null)}>Cerrar</Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
