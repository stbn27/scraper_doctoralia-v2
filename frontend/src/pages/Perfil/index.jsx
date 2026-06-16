import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import {
  RiUserLine,
  RiMapPinLine,
  RiHeartLine,
  RiHistoryLine,
  RiLogoutBoxRLine,
  RiSave3Line,
  RiAddLine,
  RiDeleteBinLine,
  RiEditLine,
  RiCheckboxCircleLine,
  RiArrowRightSLine,
  RiArrowLeftLine
} from 'react-icons/ri';
import { PageWrapper } from '@/components/layout/PageWrapper';
import { BubbleBackground } from '@/components/layout/BubbleBackground';
import { Navbar } from '@/components/layout/Navbar';
import { ModelosIA } from './ModelosIA';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { useAuth } from '@/hooks/useAuth';
import { useToast } from '@/hooks/useToast';
import {
  listarDirecciones,
  crearDireccion,
  actualizarDireccion,
  eliminarDireccion
} from '@/services/api';

export default function Perfil() {
  const { user, updateProfile, cerrarSesion } = useAuth();
  const navigate = useNavigate();
  const { addToast } = useToast();

  // Estados del perfil
  const [nombre, setNombre] = useState('');
  const [apellido, setApellido] = useState('');
  const [telefono, setTelefono] = useState('');
  const [avatarUrl, setAvatarUrl] = useState('');
  const [imgError, setImgError] = useState(false);
  const [profileSaving, setProfileSaving] = useState(false);

  const isAvatarInvalid = avatarUrl.trim() !== '' && (!avatarUrl.startsWith('http') || imgError);

  // Estados de direcciones
  const [direcciones, setDirecciones] = useState([]);
  const [dirsLoading, setDirsLoading] = useState(true);
  const [editingDir, setEditingDir] = useState(null); // null para nuevo, o { id, ... }
  const [showDirForm, setShowDirForm] = useState(false);

  // Campos formulario dirección
  const [alias, setAlias] = useState('');
  const [calle, setCalle] = useState('');
  const [municipioAlcaldia, setMunicipioAlcaldia] = useState('');
  const [ciudad, setCiudad] = useState('');
  const [estado, setEstado] = useState('');
  const [codigoPostal, setCodigoPostal] = useState('');
  const [esPrincipal, setEsPrincipal] = useState(false);
  const [dirSaving, setDirSaving] = useState(false);

  // Cargar perfil
  useEffect(() => {
    if (user) {
      setNombre(user.nombre || user.name || '');
      setApellido(user.apellido || user.lastName || '');
      setTelefono(user.telefono || '');
      setAvatarUrl(user.avatar_url || user.avatar || '');
    }
  }, [user]);

  // Resetear error de imagen cuando cambia la URL del avatar
  useEffect(() => {
    setImgError(false);
  }, [avatarUrl]);

  // Cargar direcciones
  const loadDirecciones = useCallback(async () => {
    setDirsLoading(true);
    try {
      const data = await listarDirecciones();
      // La API puede devolver un array directo o un wrapper { items: [], data: [] }
      const list = Array.isArray(data)
        ? data
        : (data?.items || data?.data || data?.direcciones || []);
      setDirecciones(list);
    } catch (err) {
      console.error('Error al cargar direcciones:', err);
    } finally {
      setDirsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadDirecciones();
  }, [loadDirecciones]);

  // Guardar perfil
  const handleSaveProfile = async () => {
    if (!nombre.trim()) {
      addToast({ type: 'error', message: 'El nombre es obligatorio.' });
      return;
    }
    if (isAvatarInvalid) {
      addToast({ type: 'error', message: 'Por favor introduce una URL de foto de perfil válida.' });
      return;
    }
    setProfileSaving(true);
    try {
      const res = await updateProfile({
        nombre,
        apellido,
        telefono,
        avatar_url: avatarUrl
      });
      if (res.success) {
        addToast({ type: 'success', message: 'Perfil actualizado con éxito.' });
      } else {
        addToast({ type: 'error', message: res.message });
      }
    } catch {
      addToast({ type: 'error', message: 'Error al actualizar perfil.' });
    } finally {
      setProfileSaving(false);
    }
  };

  // Abrir formulario dirección para crear
  const handleNewDir = () => {
    setEditingDir(null);
    setAlias('');
    setCalle('');
    setMunicipioAlcaldia('');
    setCiudad('');
    setEstado('');
    setCodigoPostal('');
    setEsPrincipal(direcciones.length === 0); // Si es la primera, principal
    setShowDirForm(true);
  };

  // Abrir formulario dirección para editar
  const handleEditDir = (dir) => {
    setEditingDir(dir);
    setAlias(dir.alias || '');
    setCalle(dir.calle || '');
    setMunicipioAlcaldia(dir.municipio_alcaldia || '');
    setCiudad(dir.ciudad || '');
    setEstado(dir.estado || '');
    setCodigoPostal(dir.codigo_postal || '');
    setEsPrincipal(dir.es_principal || false);
    setShowDirForm(true);
  };

  // Guardar dirección
  const handleSaveDir = async () => {
    if (!alias.trim() || !calle.trim() || !ciudad.trim() || !codigoPostal.trim()) {
      addToast({ type: 'error', message: 'Por favor completa los campos requeridos.' });
      return;
    }

    setDirSaving(true);
    const slug = ciudad.toLowerCase().replace(/\s+/g, '-').normalize("NFD").replace(/[\u0300-\u036f]/g, "");

    const payload = {
      alias,
      calle,
      municipio_alcaldia: municipioAlcaldia,
      ciudad,
      ciudad_slug: slug,
      estado,
      pais: 'México',
      codigo_postal: codigoPostal,
      es_principal: esPrincipal
    };

    try {
      if (editingDir) {
        await actualizarDireccion(editingDir.id || editingDir._id, payload);
        addToast({ type: 'success', message: 'Dirección actualizada.' });
      } else {
        await crearDireccion(payload);
        addToast({ type: 'success', message: 'Dirección agregada.' });
      }
      setShowDirForm(false);
      loadDirecciones();
    } catch (err) {
      console.error(err);
      addToast({ type: 'error', message: 'Error al guardar dirección.' });
    } finally {
      setDirSaving(false);
    }
  };

  // Eliminar dirección
  const handleDeleteDir = async (dirId) => {
    if (window.confirm('¿Estás seguro de eliminar esta dirección?')) {
      try {
        await eliminarDireccion(dirId);
        addToast({ type: 'success', message: 'Dirección eliminada.' });
        loadDirecciones();
      } catch {
        addToast({ type: 'error', message: 'Error al eliminar dirección.' });
      }
    }
  };

  // Marcar como principal
  const handleSetPrincipal = async (dir) => {
    try {
      await actualizarDireccion(dir.id || dir._id, { es_principal: true });
      addToast({ type: 'success', message: 'Dirección principal actualizada.' });
      loadDirecciones();
    } catch {
      addToast({ type: 'error', message: 'Error al actualizar dirección principal.' });
    }
  };

  // Cerrar sesión
  const handleLogout = () => {
    cerrarSesion();
    addToast({ type: 'info', message: 'Sesión cerrada.' });
    navigate('/');
  };

  const formattedDate = user?.created_at
    ? new Date(user.created_at).toLocaleDateString('es-MX', { year: 'numeric', month: 'long', day: 'numeric' })
    : 'Reciente';

  // Volver a la búsqueda
  const handleBack = () => {
    if (window.history.state && window.history.state.idx > 0) {
      navigate(-1);
    } else {
      navigate('/busqueda');
    }
  };

  return (
    <PageWrapper name="perfil">
      <BubbleBackground />
      <Navbar />

      <div className="relative z-10 pt-20 pb-8 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">


          {/* Columna Izquierda: Información de Usuario */}
          <div className="lg:col-span-4 lg:sticky lg:top-24 h-fit space-y-6">
            {/* Botón volver */}
            <button
              onClick={handleBack}
              className="flex items-center gap-2 text-sm hover:text-royalBlue-400 transition-colors"
              style={{ color: 'var(--text-muted)' }}
            >
              <RiArrowLeftLine /> Volver a la búsqueda
            </button>
            <div className="glass-card p-6 flex flex-col items-center text-center">
              {/* Avatar */}
              <div className="relative mb-4">
                <div
                  className="w-24 h-24 rounded-3xl bg-royalBlue-800/40 border border-white/10 flex items-center justify-center overflow-hidden hover:border-royalBlue-400/50 transition-all duration-300 shadow-xl"
                >
                  {avatarUrl && avatarUrl.startsWith('http') && !imgError ? (
                    <img
                      src={avatarUrl}
                      alt="Avatar de usuario"
                      className="w-full h-full object-cover"
                      onError={() => setImgError(true)}
                    />
                  ) : (
                    <RiUserLine className="text-5xl text-slate-300" />
                  )}
                </div>
              </div>

              <h2 className="text-xl font-bold text-slate-100">{nombre} {apellido}</h2>
              <p className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>{user?.email}</p>
              <p className="text-[10px] mt-2 bg-royalBlue-950/40 border border-white/5 px-2.5 py-1 rounded-full text-slate-400">
                Miembro desde: {formattedDate}
              </p>

              {/* Accesos rápidos */}
              <div className="w-full border-t border-white/10 mt-6 pt-4 space-y-2">
                <Link
                  to="/favoritos"
                  className="flex items-center justify-between p-3 rounded-xl hover:bg-white/5 transition-colors text-sm"
                >
                  <span className="flex items-center gap-2 text-slate-300">
                    <RiHeartLine className="text-red-400 text-base" /> Mis favoritos
                  </span>
                  <RiArrowRightSLine style={{ color: 'var(--text-muted)' }} />
                </Link>
                <Link
                  to="/historial"
                  className="flex items-center justify-between p-3 rounded-xl hover:bg-white/5 transition-colors text-sm"
                >
                  <span className="flex items-center gap-2 text-slate-300">
                    <RiHistoryLine className="text-royalBlue-400 text-base" /> Historial de búsqueda
                  </span>
                  <RiArrowRightSLine style={{ color: 'var(--text-muted)' }} />
                </Link>
                <Link
                  to="/busqueda"
                  className="flex items-center justify-between p-3 rounded-xl hover:bg-white/5 transition-colors text-sm"
                >
                  <span className="flex items-center gap-2 text-slate-300">
                    <RiUserLine className="text-emerald-400 text-base" /> Buscar especialistas
                  </span>
                  <RiArrowRightSLine style={{ color: 'var(--text-muted)' }} />
                </Link>
              </div>

              {/* Logout */}
              <button
                onClick={handleLogout}
                className="w-full mt-6 flex items-center justify-center gap-2 p-3 text-sm font-semibold rounded-xl text-red-500 hover:bg-red-500/10 transition-colors border border-red-500/20"
              >
                <RiLogoutBoxRLine /> Cerrar sesión
              </button>
            </div>
          </div>

          {/* Columna Derecha: Editar Datos y Direcciones */}
          <div className="lg:col-span-8 space-y-6">

            {/* Editor Datos Personales */}
            <div className="glass-card p-6 space-y-4">
              <h3 className="text-lg font-semibold flex items-center gap-2">
                <RiUserLine className="text-royalBlue-400" /> Información personal
              </h3>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <Input
                  id="profile-nombre"
                  label="Nombre *"
                  value={nombre}
                  onChange={(e) => setNombre(e.target.value)}
                  placeholder="Ej. José"
                />
                <Input
                  id="profile-apellido"
                  label="Apellido"
                  value={apellido}
                  onChange={(e) => setApellido(e.target.value)}
                  placeholder="Ej. Pérez"
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <Input
                  id="profile-telefono"
                  label="Teléfono"
                  value={telefono}
                  onChange={(e) => setTelefono(e.target.value)}
                  placeholder="Ej. 5512345678"
                />
                <div className="space-y-1.5">
                  <label className="block text-xs font-semibold opacity-80" style={{ color: 'var(--text-muted)' }}>
                    Correo electrónico
                  </label>
                  <input
                    type="email"
                    value={user?.email || ''}
                    readOnly
                    className="glass-input w-full px-4 py-2.5 text-sm opacity-60 cursor-not-allowed"
                  />
                </div>
              </div>

              {/* Avatar URL */}
              <div className="space-y-1.5">
                <div className="flex items-end gap-3">
                  <div className="flex-1">
                    <Input
                      id="profile-avatar-url"
                      label="URL de foto de perfil (opcional)"
                      type="url"
                      value={avatarUrl && avatarUrl.startsWith('http') ? avatarUrl : ''}
                      onChange={(e) => setAvatarUrl(e.target.value || '')}
                      placeholder="https://ejemplo.com/mi-foto.jpg"
                    />
                  </div>
                  {avatarUrl && avatarUrl.startsWith('http') && !imgError && (
                    <img
                      src={avatarUrl}
                      alt="Vista previa"
                      className="w-10 h-10 mb-0.5 rounded-full object-cover border border-white/15 shrink-0"
                      onError={() => setImgError(true)}
                    />
                  )}
                </div>
                {avatarUrl && avatarUrl.startsWith('http') && !imgError && (
                  <div className="flex justify-end pt-0.5">
                    <span className="text-[11px] text-right" style={{ color: 'var(--text-muted)' }}>Vista previa del avatar</span>
                  </div>
                )}
                {isAvatarInvalid && (
                  <div className="text-red-500 text-xs mt-1">
                    La URL no es válida o no corresponde a una imagen.
                  </div>
                )}
              </div>

              <div className="flex justify-end pt-2">
                <Button
                  variant="primary"
                  icon={<RiSave3Line />}
                  loading={profileSaving}
                  onClick={handleSaveProfile}
                  className="text-xs"
                >
                  Guardar perfil
                </Button>
              </div>
            </div>

            {/* Gestión de Direcciones */}
            <div className="glass-card p-6 space-y-4">
              <div className="flex items-center justify-between border-b border-white/10 pb-3">
                <h3 className="text-lg font-semibold flex items-center gap-2">
                  <RiMapPinLine className="text-royalBlue-400" /> Direcciones del paciente
                </h3>
                {!showDirForm && (
                  <Button
                    variant="outline"
                    icon={<RiAddLine />}
                    onClick={handleNewDir}
                    className="text-xs py-1.5 px-3"
                  >
                    Agregar dirección
                  </Button>
                )}
              </div>

              {/* Formulario de Dirección */}
              {showDirForm && (
                <div className="p-4 rounded-xl bg-white/5 border border-white/5 space-y-4 transition-all">
                  <h4 className="text-sm font-semibold text-royalBlue-300">
                    {editingDir ? 'Editar dirección' : 'Nueva dirección'}
                  </h4>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <Input
                      id="dir-alias"
                      label="Alias de dirección * (ej. Casa, Trabajo)"
                      value={alias}
                      onChange={(e) => setAlias(e.target.value)}
                      placeholder="Ej. Casa"
                    />
                    <Input
                      id="dir-calle"
                      label="Calle y número *"
                      value={calle}
                      onChange={(e) => setCalle(e.target.value)}
                      placeholder="Ej. Av. Reforma 100"
                    />
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                    <Input
                      id="dir-cp"
                      label="Código Postal *"
                      value={codigoPostal}
                      onChange={(e) => setCodigoPostal(e.target.value)}
                      placeholder="Ej. 06700"
                    />
                    <Input
                      id="dir-alcaldia"
                      label="Municipio / Alcaldía"
                      value={municipioAlcaldia}
                      onChange={(e) => setMunicipioAlcaldia(e.target.value)}
                      placeholder="Ej. Cuauhtémoc"
                    />
                    <Input
                      id="dir-ciudad"
                      label="Ciudad *"
                      value={ciudad}
                      onChange={(e) => setCiudad(e.target.value)}
                      placeholder="Ej. Ciudad de México"
                    />
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <Input
                      id="dir-estado"
                      label="Estado"
                      value={estado}
                      onChange={(e) => setEstado(e.target.value)}
                      placeholder="Ej. CDMX"
                    />
                    <div className="flex items-center gap-2 h-full pt-6">
                      <input
                        type="checkbox"
                        id="dir-principal"
                        checked={esPrincipal}
                        onChange={(e) => setEsPrincipal(e.target.checked)}
                        className="w-4 h-4 accent-royalBlue-500"
                      />
                      <label htmlFor="dir-principal" className="text-xs cursor-pointer select-none">
                        Marcar como dirección principal
                      </label>
                    </div>
                  </div>

                  <div className="flex items-center justify-end gap-2 pt-2">
                    <Button
                      variant="ghost"
                      onClick={() => setShowDirForm(false)}
                      className="text-xs"
                    >
                      Cancelar
                    </Button>
                    <Button
                      variant="primary"
                      onClick={handleSaveDir}
                      loading={dirSaving}
                      className="text-xs"
                    >
                      Guardar
                    </Button>
                  </div>
                </div>
              )}

              {/* Lista de Direcciones */}
              {dirsLoading ? (
                <div className="py-8 text-center text-sm" style={{ color: 'var(--text-muted)' }}>
                  Cargando direcciones...
                </div>
              ) : direcciones.length > 0 ? (
                <div className="space-y-3">
                  {direcciones.map((dir) => (
                    <div
                      key={dir.id || dir._id}
                      className={`p-4 rounded-xl border transition-all flex flex-col sm:flex-row sm:items-center justify-between gap-3 ${dir.es_principal
                        ? 'bg-royalBlue-950/20 border-royalBlue-500/30'
                        : 'bg-white/5 border-white/5 hover:border-white/10'
                        }`}
                    >
                      <div className="space-y-1">
                        <div className="flex items-center gap-2">
                          <strong className="text-sm text-slate-100">{dir.alias}</strong>
                          {dir.es_principal && (
                            <span className="text-[9px] bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 px-2 py-0.5 rounded-full font-medium">
                              Principal
                            </span>
                          )}
                        </div>
                        <p className="text-xs text-slate-300">
                          {dir.calle}, Col. {dir.municipio_alcaldia || 'N/A'}, CP {dir.codigo_postal}
                        </p>
                        <p className="text-[11px]" style={{ color: 'var(--text-muted)' }}>
                          {dir.ciudad}, {dir.estado}, {dir.pais}
                        </p>
                      </div>

                      <div className="flex items-center gap-2 self-end sm:self-auto">
                        {!dir.es_principal && (
                          <button
                            onClick={() => handleSetPrincipal(dir)}
                            className="p-2 text-xs rounded-lg hover:bg-white/10 text-emerald-400 font-semibold transition-colors flex items-center gap-1"
                            title="Marcar como principal"
                          >
                            <RiCheckboxCircleLine className="text-base" /> Principal
                          </button>
                        )}
                        <button
                          onClick={() => handleEditDir(dir)}
                          className="p-2 rounded-lg hover:bg-white/15 text-slate-300 transition-colors"
                          title="Editar"
                        >
                          <RiEditLine />
                        </button>
                        <button
                          onClick={() => handleDeleteDir(dir.id || dir._id)}
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
                  Aún no tienes direcciones registradas.
                </div>
              )}
            </div>

            {/* Gestión de Tokens LLM */}
            <ModelosIA />
          </div>
        </div>
      </div>
    </PageWrapper>
  );
}
