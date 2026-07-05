import { useEffect, useRef, useState } from "react";

export function useCounter(target: number, duration = 1200) {
  const [value, setValue] = useState(0);
  const raf = useRef(0);

  useEffect(() => {
    if (!target) return;
    const start = performance.now();
    const tick = (now: number) => {
      const p = Math.min((now - start) / duration, 1);
      // ease out cubic
      const ease = 1 - Math.pow(1 - p, 3);
      setValue(Math.round(ease * target));
      if (p < 1) raf.current = requestAnimationFrame(tick);
    };
    raf.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf.current);
  }, [target, duration]);

  return value;
}

export function statusColor(status: string) {
  if (status === "Healthy")  return "#34D399";
  if (status === "Warning")  return "#FBBF24";
  return "#F87171";
}

export function healthColor(h: number) {
  if (h >= 75) return "#34D399";
  if (h >= 45) return "#FBBF24";
  return "#F87171";
}

export function fmt(n: number) {
  return `₹${n.toLocaleString("en-IN")}`;
}
