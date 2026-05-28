import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { RiGoogleFill, RiLoginBoxLine } from 'react-icons/ri';
import { BubbleBackground } from '@/components/layout/BubbleBackground';
import { PageWrapper } from '@/components/layout/PageWrapper';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { useAuth } from '@/hooks/useAuth';
import { useToast } from '@/hooks/useToast';
import logo from '@/assets/logo.png';

/**
 * Login — Pantalla de autenticación mockeada.
 * Credenciales válidas: josejulianstbn27@gmail.com / 1234
 */
export default function Login() {
  const navigate = useNavigate();
  const { login, loginWithGoogle } = useAuth();
  const { addToast } = useToast();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [errors, setErrors] = useState({});
  const [loading, setLoading] = useState(false);
  const [googleLoading, setGoogleLoading] = useState(false);

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
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  /**
   * Maneja el submit del formulario de login.
   */
  const handleSubmit = () => {
    if (!validate()) return;

    setLoading(true);
    // Simular delay
    setTimeout(() => {
      const result = login(email, password);
      if (result.success) {
        addToast({ type: 'success', message: result.message });
        navigate('/dashboard');
      } else {
        addToast({ type: 'error', message: result.message });
      }
      setLoading(false);
    }, 500);
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
        navigate('/dashboard');
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
        <div className="glass-card w-full max-w-[440px] p-8">
          {/* Header */}
          <div className="text-center mb-8">
            <img src={logo} alt="MedRec" className="w-14 h-14 rounded-xl mx-auto mb-4" />
            <h1 className="text-2xl font-bold">Iniciar sesión</h1>
            <p className="text-sm mt-1" style={{ color: 'var(--text-muted)' }}>
              Accede a tu cuenta de MedRec
            </p>
          </div>

          {/* Formulario */}
          <div className="space-y-5">
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

            <Button
              variant="primary"
              fullWidth
              loading={loading}
              icon={<RiLoginBoxLine />}
              onClick={handleSubmit}
            >
              Entrar
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

          {/* Enlace registro */}
          <p className="text-center text-sm mt-6" style={{ color: 'var(--text-muted)' }}>
            ¿No tienes cuenta?{' '}
            <button
              onClick={() => addToast({ type: 'info', message: 'Registro próximamente disponible.' })}
              className="text-royalBlue-400 hover:text-royalBlue-300 transition-colors font-medium"
            >
              Regístrate
            </button>
          </p>
        </div>
      </div>
    </PageWrapper>
  );
}
