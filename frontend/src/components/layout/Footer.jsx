import logo from '@/assets/logo.png';
import { RiGithubFill, RiInstagramLine } from 'react-icons/ri';

export function Footer() {
    return (
        <footer className="bg-neutral-primary-soft font-secondary">
            <div className="mx-auto w-full max-w-screen-xl p-4 py-6 lg:py-8 mt-10 border-t border-indigo-900 border-opacity-20">
                <div className="md:flex md:justify-between">
                    <div className="mb-6 md:mb-0">
                        <a href="/" className="flex items-center">
                            <img
                                src={logo}
                                alt="Logo de MedRec"
                                className="h-12 w-12 rounded-lg"
                            />
                            <span className="text-heading self-center text-2xl font-semibold whitespace-nowrap">MedRec</span>
                        </a>
                    </div>
                    <div className="grid grid-cols-2 gap-8 sm:gap-6 sm:grid-cols-2">
                        <div>
                            <h2 className="mb-6 text-xs font-semibold text-heading uppercase">Siguenos</h2>
                            <ul className="text-body font-medium">
                                <li className="mb-2 text-xs">
                                    <a href="www.github.com/stbn27" className="hover:underline ">Github</a>
                                </li>
                                <li className='text-xs'>
                                    <a href="#" className="hover:underline">Instagram</a>
                                </li>
                            </ul>
                        </div>
                        <div>
                            <h2 className="mb-6 text-xs font-semibold text-heading uppercase">Legal</h2>
                            <ul className="text-body font-medium">
                                <li className="mb-2 text-xs">
                                    <a href="#" className="hover:underline">Política de privacidad</a>
                                </li>
                                <li className='text-xs'>
                                    <a href="#" className="hover:underline">Términos y Condiciones</a>
                                </li>
                            </ul>
                        </div>
                    </div>
                </div>
                <hr className="my-6 border-default sm:mx-auto lg:my-8" />
                <div className="sm:flex sm:items-center sm:justify-between">

                    <span className="text-xs text-body sm:text-center">© {new Date().getFullYear()} <a href="#" className="ms-4 hover:underline">MedRec™</a>. Todos los derechos reservados.
                    </span>

                    <div className="flex mt-4 sm:justify-center sm:mt-0 gap-5">
                        <a href="https://github.com/stbn27" target="_blank" rel="noopener noreferrer" className="text-body text-xs hover:text-heading">
                            <RiGithubFill className="w-5 h-5" />
                            <span className="sr-only">Desarrollador Github</span>
                        </a>

                        <a href="#" className="text-body text-xs hover:text-heading">
                            <RiInstagramLine className="w-5 h-5" />
                            <span className="sr-only">Instagram desarrollador</span>
                        </a>
                    </div>
                </div>
            </div>
        </footer>
    )
}