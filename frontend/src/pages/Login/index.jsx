import React, { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { RiGoogleFill, RiLoginBoxLine, RiUserAddLine } from 'react-icons/ri';
import { BubbleBackground } from '@/components/layout/BubbleBackground';
import { PageWrapper } from '@/components/layout/PageWrapper';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { useAuth } from '@/hooks/useAuth';
import { useToast } from '@/hooks/useToast';
import logo from '@/assets/logo.png';

/**
 * Login — Pantalla de autenticación y registro.
 */
export default function Login() {
  const navigate = useNavigate();
  const location = useLocation();
  const { iniciarSesion, registrarUsuario, loginWithGoogle } = useAuth();
  const { addToast } = useToast();

  const [isRegister, setIsRegister] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [errors, setErrors] = useState({});
  const [loading, setLoading] = useState(false);
  const [googleLoading, setGoogleLoading] = useState(false);

  // Determinar la redirección tras login
  const from = location.state?.from || '/busqueda';

  /**
   * Valida los campos del formulario.
   * @returns {boolean} true si el formulario es válido.
   */
  const validate = () => {
    const newErrors = {};

    if (!email.trim()) {
      newErrors.email = 'El correo es obligatorio.';
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      newErrors.email = 'Ingresa un correo válido.';
    }

    if (!password.trim()) {
      newErrors.password = 'La contraseña es obligatoria.';
    } else if (password.length < 6) {
      newErrors.password = 'La contraseña debe tener al menos 6 caracteres.';
    }

    if (isRegister) {
      if (!confirmPassword.trim()) {
        newErrors.confirmPassword = 'Debes confirmar la contraseña.';
      } else if (confirmPassword !== password) {
        newErrors.confirmPassword = 'Las contraseñas no coinciden.';
      }
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  /**
   * Maneja el submit del formulario de login / registro.
   */
  const handleSubmit = async () => {
    if (!validate()) return;

    setLoading(true);
    try {
      if (isRegister) {
        const result = await registrarUsuario(email, password);
        if (result.success) {
          addToast({ type: 'success', message: result.message });
          // Cambiar a pestaña de login y limpiar password
          setIsRegister(false);
          setPassword('');
          setConfirmPassword('');
        } else {
          addToast({ type: 'error', message: result.message });
        }
      } else {
        const result = await iniciarSesion(email, password);
        if (result.success) {
          addToast({ type: 'success', message: result.message });
          navigate(from, { replace: true });
        } else {
          addToast({ type: 'error', message: result.message });
        }
      }
    } catch (err) {
      addToast({ type: 'error', message: 'Ocurrió un error inesperado.' });
    } finally {
      setLoading(false);
    }
  };

  /**
   * Maneja el login con Google (mock).
   */
  const handleGoogle = async () => {
    setGoogleLoading(true);
    try {
      const result = await loginWithGoogle();
      if (result.success) {
        addToast({ type: 'success', message: result.message });
        navigate(from, { replace: true });
      } else {
        addToast({ type: 'error', message: result.message });
      }
    } catch {
      addToast({ type: 'error', message: 'Error al conectar con Google.' });
    } finally {
      setGoogleLoading(false);
    }
  };

  /**
   * Maneja Enter en los inputs.
   */
  const handleKeyDown = (e) => {
    if (e.key === 'Enter') {
      handleSubmit();
    }
  };

  return (
    <PageWrapper name="login" className="relative">
      <BubbleBackground />

      <div className="relative z-10 min-h-screen flex items-center justify-center p-4">
        <div className="glass-card w-full max-w-[440px] p-8 transition-all duration-300">
          {/* Header */}
          <div className="text-center mb-6">
            <img src={logo} alt="MedRec" className="w-14 h-14 rounded-xl mx-auto mb-4" />
            <h1 className="text-2xl font-bold">{isRegister ? 'Crear cuenta' : 'Iniciar sesión'}</h1>
            <p className="text-sm mt-1" style={{ color: 'var(--text-muted)' }}>
              {isRegister ? 'Regístrate para guardar favoritos e historial' : 'Accede a tu cuenta de MedRec'}
            </p>
          </div>

          {/* Tabs */}
          <div className="flex border-b border-white/10 mb-6">
            <button
              className={`flex-1 pb-3 text-sm font-semibold transition-all duration-200 border-b-2 ${
                !isRegister ? 'border-royalBlue-500 text-royalBlue-400' : 'border-transparent text-slate-400 hover:text-white'
              }`}
              onClick={() => {
                setIsRegister(false);
                setErrors({});
              }}
            >
              Ingresar
            </button>
            <button
              className={`flex-1 pb-3 text-sm font-semibold transition-all duration-200 border-b-2 ${
                isRegister ? 'border-royalBlue-500 text-royalBlue-400' : 'border-transparent text-slate-400 hover:text-white'
              }`}
              onClick={() => {
                setIsRegister(true);
                setErrors({});
              }}
            >
              Registrarse
            </button>
          </div>

          {/* Formulario */}
          <div className="space-y-4">
            <Input
              id="login-email"
              label="Correo electrónico"
              type="email"
              placeholder="correo@ejemplo.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              onKeyDown={handleKeyDown}
              error={errors.email}
            />

            <Input
              id="login-password"
              label="Contraseña"
              type="password"
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              onKeyDown={handleKeyDown}
              error={errors.password}
            />

            {isRegister && (
              <Input
                id="login-confirm-password"
                label="Confirmar contraseña"
                type="password"
                placeholder="••••••••"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                onKeyDown={handleKeyDown}
                error={errors.confirmPassword}
              />
            )}

            <Button
              variant="primary"
              fullWidth
              loading={loading}
              icon={isRegister ? <RiUserAddLine /> : <RiLoginBoxLine />}
              onClick={handleSubmit}
            >
              {isRegister ? 'Crear cuenta' : 'Entrar'}
            </Button>
          </div>

          {/* Separador */}
          <div className="flex items-center gap-3 my-6">
            <div className="flex-1 h-px bg-white/15" />
            <span className="text-xs" style={{ color: 'var(--text-muted)' }}>ó</span>
            <div className="flex-1 h-px bg-white/15" />
          </div>

          {/* Google */}
          <Button
            variant="outline"
            fullWidth
            loading={googleLoading}
            icon={<RiGoogleFill className="text-lg" />}
            onClick={handleGoogle}
            className="bg-white/5 hover:bg-white/10"
          >
            Continuar con Google
          </Button>

          {/* Enlace alternar */}
          <p className="text-center text-sm mt-6" style={{ color: 'var(--text-muted)' }}>
            {isRegister ? '¿Ya tienes una cuenta?' : '¿No tienes cuenta?'}{' '}
            <button
              onClick={() => {
                setIsRegister(!isRegister);
                setErrors({});
              }}
              className="text-royalBlue-400 hover:text-royalBlue-300 transition-colors font-medium"
            >
              {isRegister ? 'Inicia sesión' : 'Regístrate'}
            </button>
          </p>
        </div>
      </div>
    </PageWrapper>
  );
}
