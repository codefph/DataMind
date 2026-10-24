import { useEffect, useRef } from 'react';

export function useResize<T extends HTMLElement>(
  ref: React.RefObject<T>,
  cb: (rect: DOMRectReadOnly) => void
) {
  useEffect(() => {
    if (!ref.current) return;
    const observer = new ResizeObserver((entries) => {
      cb(entries[0].contentRect);
    });
    observer.observe(ref.current);
    return () => observer.disconnect();
  }, [ref, cb]);
}