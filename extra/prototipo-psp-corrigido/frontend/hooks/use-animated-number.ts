import { useEffect, useRef, useState } from "react";

const DURATION_MS = 500;

/**
 * Smoothly animates a number from its previous value to the new target
 * using requestAnimationFrame with an ease-out curve.
 */
export function useAnimatedNumber(target: number): number {
  const [display, setDisplay] = useState(target);
  const fromRef = useRef(target);
  const rafRef = useRef<number>(0);

  useEffect(() => {
    const from = fromRef.current;
    if (from === target) return;

    const start = performance.now();

    function tick(now: number) {
      const elapsed = now - start;
      const progress = Math.min(elapsed / DURATION_MS, 1);
      // ease-out cubic: decelerates towards the end
      const eased = 1 - (1 - progress) ** 3;
      const current = from + (target - from) * eased;

      setDisplay(current);

      if (progress < 1) {
        rafRef.current = requestAnimationFrame(tick);
      } else {
        fromRef.current = target;
      }
    }

    rafRef.current = requestAnimationFrame(tick);

    return () => cancelAnimationFrame(rafRef.current);
  }, [target]);

  return display;
}
