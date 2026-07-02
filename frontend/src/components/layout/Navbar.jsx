import React from 'react';
import {Link, useLocation, useNavigate} from 'react-router-dom';
import {
    RiArrowLeftLine, RiHeartLine, RiLoginBoxLine, RiSearchLine,
} from 'react-icons/ri';

import {ThemeToggle} from '@/components/shared/ThemeToggle';
import {UserDropdown} from '@/components/layout/UserDropdown';
import {useAuth} from '@/hooks/useAuth';
import logo from '@/assets/logo.png';

/**
 * Navbar principal del sistema.
 *
 * Muestra:
 * - Logo y nombre del sistema.
 * - Acceso rápido a búsqueda.
 * - Cambio de tema.
 * - Botón de login si no hay sesión.
 * - Menú de usuario si hay sesión.
 */
export function Navbar() {
    const {user, logout} = useAuth();
    const location = useLocation();
    const navigate = useNavigate();


    const isHome = location.pathname === '/';
    const isSearchPage = location.pathname === '/busqueda';

    const shouldShowBackButton = false;

    const getSectionTitle = () => {
        const path = location.pathname;

        if (path === '/busqueda') return 'Búsqueda';
        if (path.startsWith('/especialista')) return 'Detalle del especialista';
        if (path === '/login') return 'Iniciar sesión';
        if (path === '/perfil') return 'Mi perfil';
        if (path === '/favoritos') return 'Mis favoritos';
        if (path === '/historial') return 'Historial de búsqueda';

        return '';
    };

    const handleLogout = () => {
        logout();
        navigate('/');
    };

    return (<nav
        className={`
            fixed top-0 left-0 right-0 z-30
            shadow-md shadow-blue-50 dark:shadow-none
            transition-all duration-300 
            ${isHome ? 'bg-transparent' : 'glass-card rounded-none border-x-0 border-t-0'}`
        }
    >
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
            <div className="flex h-16 items-center justify-between">

                {/* Zona izquierda */}
                <div className="flex items-center gap-3">
                    {shouldShowBackButton && (<button
                        type="button"
                        onClick={() => navigate(-1)}
                        className="rounded-lg p-2 transition-colors hover:bg-black/10 dark:hover:bg-white/10"
                        style={{color: 'var(--text-muted)'}}
                        aria-label="Volver"
                    >
                        <RiArrowLeftLine className="text-xl"/>
                    </button>)}

                    <Link to="/" className="group flex items-center gap-2">
                        <img
                            src={logo}
                            alt="Logo de MedRec"
                            className="h-8 w-8 rounded-lg"
                        />

                        <span className="text-lg font-semibold transition-colors group-hover:text-royalBlue-400">
                            MedRec
                        </span>
                    </Link>
                </div>

                {/* Zona derecha */}
                <div className="flex items-center gap-2">

                    {!isSearchPage && (<Link
                        to="/busqueda"
                        className="rounded-xl p-2 transition-colors hover:bg-black/10 dark:hover:bg-white/10"
                        aria-label="Ir a búsqueda"
                        title="Buscar especialistas"
                    >
                        <RiSearchLine className="text-xl"/>
                    </Link>)}

                    <ThemeToggle/>

                    {user ? (<>
                        <Link
                            to="/favoritos"
                            className="rounded-xl p-2 transition-colors hover:bg-black/10 dark:hover:bg-white/10"
                            aria-label="Mis favoritos"
                            title="Mis favoritos"
                        >
                            <RiHeartLine className="text-xl"/>
                        </Link>

                        <UserDropdown user={user} onLogout={handleLogout}/>
                    </>) : (<Link
                        to="/login"
                        className="
                            flex items-center gap-2
                            px-4 py-2
                            border border-transparent rounded-xl
                            bg-royalBlue-600 hover:bg-transparent hover:border hover:border-royalBlue-500
                            text-sm font-medium text-white hover:text-royalBlue-500 dark:hover:text-royalBlue-500
                            transition-colors duration-500"
                    >
                        <RiLoginBoxLine/>
                        <span className="hidden sm:inline">Iniciar sesión</span>
                    </Link>)}
                </div>
            </div>
        </div>
    </nav>);
}