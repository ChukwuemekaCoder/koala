import { useEffect, useRef } from "react";

/**
 * Adds `reveal--visible` to each `.reveal` child of the returned ref's
 * element once it scrolls into view, staggered ~60ms per item in DOM order.
 */
export function useScrollReveal<T extends HTMLElement>() {
  const containerRef = useRef<T>(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const items = Array.from(container.querySelectorAll<HTMLElement>(".reveal"));

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (!entry.isIntersecting) return;
          const el = entry.target as HTMLElement;
          const index = items.indexOf(el);
          el.style.animationDelay = `${Math.max(index, 0) * 60}ms`;
          el.classList.add("reveal--visible");
          observer.unobserve(el);
        });
      },
      { threshold: 0.2 },
    );

    items.forEach((item) => observer.observe(item));
    return () => observer.disconnect();
  }, []);

  return containerRef;
}
