import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { RiGoogleFill, RiLoginBoxLine } from 'react-icons/ri';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { useAuth } from '@/hooks/useAuth';
import { useToast } from '@/hooks/useToast';
import logo from '@/assets/logo.png';

/**
 * InlineLogin — Componente de inicio de sesión empotrado (usado en Home).
 */
export function InlineLogin({ onSuccess }) {
  const navigate = useNavigate();
  const { iniciarSesion, loginWithGoogle } = useAuth();
  const { addToast } = useToast();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [errors, setErrors] = useState({});
  const [loading, setLoading] = useState(false);
  const [googleLoading, setGoogleLoading] = useState(false);

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

  const handleSubmit = async () => {
    if (!validate()) return;
    setLoading(true);
    try {
      const result = await iniciarSesion(email, password);
      if (result.success) {
        addToast({ type: 'success', message: result.message });
        if (onSuccess) {
          onSuccess();
        } else {
          navigate('/busqueda');
        }
      } else {
        addToast({ type: 'error', message: result.message });
      }
    } catch (err) {
      addToast({ type: 'error', message: 'Error al iniciar sesión.' });
    } finally {
      setLoading(false);
    }
  };

  const handleGoogle = async () => {
    setGoogleLoading(true);
    try {
      const result = await loginWithGoogle();
      if (result.success) {
        addToast({ type: 'success', message: result.message });
        if (onSuccess) {
          onSuccess();
        } else {
          navigate('/busqueda');
        }
      } else {
        addToast({ type: 'error', message: result.message });
      }
    } catch {
      addToast({ type: 'error', message: 'Error al conectar con Google.' });
    } finally {
      setGoogleLoading(false);
    }
  };

  return (
    <div className="w-full max-w-[440px]">
      <div className="text-center mb-8">
        <img src={logo} alt="MedRec" className="w-14 h-14 rounded-xl mx-auto mb-4" />
        <h1 className="text-2xl font-bold">Iniciar sesión</h1>
        <p className="text-sm mt-1" style={{ color: 'var(--text-muted)' }}>
          Accede a tu cuenta de MedRec
        </p>
      </div>

      <div className="space-y-5">
        <Input
          id="inline-email"
          label="Correo electrónico"
          type="email"
          placeholder="correo@ejemplo.com"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          error={errors.email}
          onKeyDown={(e) => e.key === 'Enter' && handleSubmit()}
        />
        <Input
          id="inline-password"
          label="Contraseña"
          type="password"
          placeholder="••••••••"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          error={errors.password}
          onKeyDown={(e) => e.key === 'Enter' && handleSubmit()}
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
      </div>

      <p className="text-center text-sm mt-6" style={{ color: 'var(--text-muted)' }}>
        ¿No tienes cuenta?{' '}
        <button
          onClick={() => navigate('/login')}
          className="text-royalBlue-400 hover:text-royalBlue-300 transition-colors font-medium"
        >
          Regístrate
        </button>
      </p>
    </div>
  );
}

export default InlineLogin;
