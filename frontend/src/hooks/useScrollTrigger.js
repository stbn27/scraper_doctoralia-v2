import { useEffect, useRef } from 'react';

/**
 * Hook que observa elementos con la clase 'scroll-reveal' y les añade
 * la clase 'visible' cuando entran al viewport.
 * Usa IntersectionObserver y MutationObserver para asegurar que los elementos
 * cargados dinámicamente sean detectados y revelados correctamente.
 * @param {{ threshold?: number, rootMargin?: string }} options
 */
export function useScrollTrigger(options = {}) {
  const observerRef = useRef(null);

  useEffect(() => {
    const { threshold = 0.1, rootMargin = '0px 0px -50px 0px' } = options;

    observerRef.current = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add('visible');
            observerRef.current?.unobserve(entry.target);
          }
        });
      },
      { threshold, rootMargin }
    );

    const observeElements = () => {
      const elements = document.querySelectorAll('.scroll-reveal:not(.visible)');
      elements.forEach((el) => observerRef.current?.observe(el));
    };

    // Observar los elementos presentes al montar
    observeElements();

    // Observar cambios dinámicos en el DOM (ej. tras finalizar estados de carga)
    const mutationObserver = new MutationObserver(() => {
      observeElements();
    });

    mutationObserver.observe(document.documentElement, {
      childList: true,
      subtree: true,
    });

    return () => {
      observerRef.current?.disconnect();
      mutationObserver.disconnect();
    };
  }, []);
}
