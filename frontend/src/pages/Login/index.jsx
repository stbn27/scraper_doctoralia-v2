import React, { useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { RiGoogleFill, RiLoginBoxLine, RiUserAddLine, RiCloseLine } from "react-icons/ri";
import { BubbleBackground } from "@/components/layout/BubbleBackground";
import { PageWrapper } from "@/components/layout/PageWrapper";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { useAuth } from "@/hooks/useAuth";
import { useToast } from "@/hooks/useToast";
import logo from "@/assets/logo.png";

/**
 * Login — Pantalla de autenticación y registro.
 */
export default function Login() {
   const navigate = useNavigate();
   const location = useLocation();
   const { iniciarSesion, registrarUsuario, loginWithGoogle } = useAuth();
   const { addToast } = useToast();

   const [isRegister, setIsRegister] = useState(false);
   const [email, setEmail] = useState("");
   const [password, setPassword] = useState("");
   const [confirmPassword, setConfirmPassword] = useState("");
   // Campos de registro extendidos
   const [nombre, setNombre] = useState("");
   const [apellidos, setApellidos] = useState("");
   const [telefono, setTelefono] = useState("");
   const [avatarUrl, setAvatarUrl] = useState("");
   const [errors, setErrors] = useState({});
   const [loading, setLoading] = useState(false);
   const [googleLoading, setGoogleLoading] = useState(false);

   // Determinar la redirección tras login
   const from = location.state?.from || "/busqueda";

   /**
    * Valida si una URL apunta a una imagen (extensión o parámetro conocido).
    * @param {string} url
    * @returns {boolean}
    */
   const isImageUrl = (url) => {
      try {
         const u = new URL(url);
         const path = u.pathname.toLowerCase();
         return (
            /\.(jpg|jpeg|png|gif|webp|avif|svg)$/.test(path) ||
            u.searchParams.has("format") ||
            u.searchParams.has("ext")
         );
      } catch {
         return false;
      }
   };

   /**
    * Valida los campos del formulario.
    * @returns {boolean} true si el formulario es válido.
    */
   const validate = () => {
      const newErrors = {};

      if (!email.trim()) {
         newErrors.email = "El correo es obligatorio.";
      } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
         newErrors.email = "Ingresa un correo válido.";
      }

      if (!password.trim()) {
         newErrors.password = "La contraseña es obligatoria.";
      } else if (password.length < 2) {
         newErrors.password = "La contraseña debe tener al menos 2 caracteres.";
      }

      if (isRegister) {
         if (!nombre.trim()) {
            newErrors.nombre = "El nombre es obligatorio.";
         }
         if (!apellidos.trim()) {
            newErrors.apellidos = "Los apellidos son obligatorios.";
         }
         if (
            telefono.trim() &&
            !/^\+?[\d\s\-()]{7,15}$/.test(telefono.trim())
         ) {
            newErrors.telefono = "Ingresa un teléfono válido (7–15 dígitos).";
         }
         if (avatarUrl.trim()) {
            try {
               new URL(avatarUrl.trim());
               if (!isImageUrl(avatarUrl.trim())) {
                  newErrors.avatarUrl =
                     "La URL debe apuntar a una imagen (jpg, png, webp…).";
               }
            } catch {
               newErrors.avatarUrl = "Ingresa una URL válida (https://…).";
            }
         }
         if (!confirmPassword.trim()) {
            newErrors.confirmPassword = "Debes confirmar la contraseña.";
         } else if (confirmPassword !== password) {
            newErrors.confirmPassword = "Las contraseñas no coinciden.";
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
            const result = await registrarUsuario(email, password, {
               nombre: nombre.trim(),
               apellido: apellidos.trim(),
               telefono: telefono.trim() || undefined,
               avatar_url: avatarUrl.trim() || undefined,
            });
            if (result.success) {
               addToast({ type: "success", message: result.message });
               // Limpiar y cambiar a login
               setIsRegister(false);
               setPassword("");
               setConfirmPassword("");
               setNombre("");
               setApellidos("");
               setTelefono("");
               setAvatarUrl("");
            } else {
               addToast({ type: "error", message: result.message });
            }
         } else {
            const result = await iniciarSesion(email, password);
            if (result.success) {
               addToast({ type: "success", message: result.message });
               navigate(from, { replace: true });
            } else {
               addToast({ type: "error", message: result.message });
               setPassword("");
            }
         }
      } catch (err) {
         addToast({ type: "error", message: "Ocurrió un error inesperado." });
         setPassword("");
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
            addToast({ type: "success", message: result.message });
            navigate(from, { replace: true });
         } else {
            addToast({ type: "error", message: result.message });
         }
      } catch {
         addToast({ type: "error", message: "Error al conectar con Google." });
      } finally {
         setGoogleLoading(false);
      }
   };

   /**
    * Maneja Enter en los inputs.
    */
   const handleKeyDown = (e) => {
      if (e.key === "Enter") {
         handleSubmit();
      }
   };

   return (
      <PageWrapper name="login" className="relative">
         <BubbleBackground />

         <div className="relative z-10 min-h-screen flex items-center justify-center p-4">
            <div className={`glass-card relative w-full p-8 transition-all duration-500 ease-out ${isRegister ? 'max-w-[640px]' : 'max-w-[440px]'}`}>

               {/* Botón de cerrar -> Busqueda o regresar en la vista anterior */}
               <button
                  type="button"
                  className="absolute -top-3.5 -right-3.5 w-12 h-12 flex items-center justify-center rounded-full bg-[#0d0d0f]/90 border border-white/10 hover:border-royalBlue-500/50 hover:bg-slate-900 text-slate-400 hover:text-white shadow-xl transition-all duration-300 z-20 group hover:scale-110"
                  onClick={() => navigate(-1)}
                  title="Cerrar"
               >
                  <RiCloseLine className="text-2xl transition-all group-hover:animate-pulse" />
               </button>

               {/* Header */}
               <div className="text-center mb-6">
                  <img
                     src={logo}
                     alt="MedRec"
                     className="w-14 h-14 rounded-xl mx-auto mb-4"
                  />
                  <h1 className="text-2xl font-bold">
                     {isRegister ? "Crear cuenta" : "Iniciar sesión"}
                  </h1>
                  <p
                     className="text-sm mt-1"
                     style={{ color: "var(--text-muted)" }}
                  >
                     {isRegister
                        ? "Regístrate para guardar favoritos e historial"
                        : "Accede a tu cuenta de MedRec"}
                  </p>
               </div>

               {/* Tabs */}
               <div className="flex border-b border-white/10 mb-6">
                  <button
                     className={`flex-1 pb-3 text-sm font-semibold transition-all duration-200 border-b-2 ${
                        !isRegister
                           ? "border-royalBlue-500 text-royalBlue-400"
                           : "border-transparent text-slate-400 hover:text-white"
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
                        isRegister
                           ? "border-royalBlue-500 text-royalBlue-400"
                           : "border-transparent text-slate-400 hover:text-white"
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
               <div className="mt-4">
                  {!isRegister ? (
                     <div key="login-form" className="space-y-4 animate-login-fade">
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
                  ) : (
                     <div key="register-form" className="grid grid-cols-1 md:grid-cols-2 gap-x-4 gap-y-3.5 animate-login-fade">
                        {/* Nombre */}
                        <div className="md:col-span-1">
                           <Input
                              id="reg-nombre"
                              label="Nombre *"
                              placeholder="Ej. José"
                              value={nombre}
                              onChange={(e) => setNombre(e.target.value)}
                              onKeyDown={handleKeyDown}
                              error={errors.nombre}
                           />
                        </div>
                        {/* Apellidos */}
                        <div className="md:col-span-1">
                           <Input
                              id="reg-apellidos"
                              label="Apellidos *"
                              placeholder="Ej. García Pérez"
                              value={apellidos}
                              onChange={(e) => setApellidos(e.target.value)}
                              onKeyDown={handleKeyDown}
                              error={errors.apellidos}
                           />
                        </div>
                        {/* Correo electrónico */}
                        <div className="md:col-span-1">
                           <Input
                              id="reg-email"
                              label="Correo electrónico *"
                              type="email"
                              placeholder="correo@ejemplo.com"
                              value={email}
                              onChange={(e) => setEmail(e.target.value)}
                              onKeyDown={handleKeyDown}
                              error={errors.email}
                           />
                        </div>
                        {/* Teléfono */}
                        <div className="md:col-span-1">
                           <Input
                              id="reg-telefono"
                              label="Teléfono (opcional)"
                              type="tel"
                              placeholder="Ej. 5512345678"
                              value={telefono}
                              onChange={(e) => setTelefono(e.target.value)}
                              onKeyDown={handleKeyDown}
                              error={errors.telefono}
                           />
                        </div>
                        {/* Contraseña */}
                        <div className="md:col-span-1">
                           <Input
                              id="reg-password"
                              label="Contraseña *"
                              type="password"
                              placeholder="••••••••"
                              value={password}
                              onChange={(e) => setPassword(e.target.value)}
                              onKeyDown={handleKeyDown}
                              error={errors.password}
                           />
                        </div>
                        {/* Confirmar Contraseña */}
                        <div className="md:col-span-1">
                           <Input
                              id="login-confirm-password"
                              label="Confirmar contraseña *"
                              type="password"
                              placeholder="••••••••"
                              value={confirmPassword}
                              onChange={(e) => setConfirmPassword(e.target.value)}
                              onKeyDown={handleKeyDown}
                              error={errors.confirmPassword}
                           />
                        </div>
                        {/* URL de foto de perfil & preview */}
                        <div className="md:col-span-2 flex flex-col sm:flex-row sm:items-end gap-3">
                           <div className="flex-1">
                              <Input
                                 id="reg-avatar-url"
                                 label="URL de foto de perfil (opcional)"
                                 type="url"
                                 placeholder="https://ejemplo.com/mi-foto.jpg"
                                 value={avatarUrl}
                                 onChange={(e) => setAvatarUrl(e.target.value)}
                                 onKeyDown={handleKeyDown}
                                 error={errors.avatarUrl}
                              />
                           </div>
                           {avatarUrl && !errors.avatarUrl && (
                              <div className="flex items-center gap-2 pb-2 h-10 shrink-0">
                                 <img
                                    src={avatarUrl}
                                    alt="Vista previa"
                                    className="w-9 h-9 rounded-full object-cover border border-white/15"
                                    onError={(e) => {
                                       e.target.style.display = "none";
                                    }}
                                 />
                                 <span
                                    className="text-[11px]"
                                    style={{ color: "var(--text-muted)" }}
                                 >
                                    Vista previa
                                 </span>
                              </div>
                           )}
                        </div>

                        {/* Botón de envío */}
                        <div className="md:col-span-2 pt-2">
                           <Button
                              variant="primary"
                              fullWidth
                              loading={loading}
                              icon={<RiUserAddLine />}
                              onClick={handleSubmit}
                           >
                              Crear cuenta
                           </Button>
                        </div>
                     </div>
                  )}
               </div>

               {/* Separador */}
               <div className="flex items-center gap-3 my-6">
                  <div className="flex-1 h-px bg-white/15" />
                  <span
                     className="text-xs"
                     style={{ color: "var(--text-muted)" }}
                  >
                     ó
                  </span>
                  <div className="flex-1 h-px bg-white/15" />
               </div>

               {/* Google */}
               {/* <Button
                     variant="outline"
                     fullWidth
                     loading={googleLoading}
                     icon={<RiGoogleFill className="text-lg" />}
                     onClick={handleGoogle}
                     className="bg-white/5 hover:bg-white/10"
                  >
                     Continuar con Google
               </Button> */}

               {/* Enlace alternar */}
               <p
                  className="text-center text-sm mt-6"
                  style={{ color: "var(--text-muted)" }}
               >
                  {isRegister ? "¿Ya tienes una cuenta?" : "¿No tienes cuenta?"}{" "}
                  <button
                     onClick={() => {
                        setIsRegister(!isRegister);
                        setErrors({});
                     }}
                     className="text-royalBlue-400 hover:text-royalBlue-300 transition-colors font-medium"
                  >
                     {isRegister ? "Inicia sesión" : "Regístrate"}
                  </button>
               </p>
            </div>
         </div>
      </PageWrapper>
   );
}