/**
 * BackgroundParticles — minimal ambient dust only.
 * 60 particles. No orbit ring. No data streams. 60fps friendly.
 */
import { useRef, useMemo } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";

const COUNT  = 60;
const SPREAD = 12;
const HEIGHT = 6;

export default function BackgroundParticles() {
  const ref = useRef<THREE.Points>(null);

  const { positions, speeds } = useMemo(() => {
    const positions = new Float32Array(COUNT * 3);
    const speeds    = new Float32Array(COUNT);
    for (let i = 0; i < COUNT; i++) {
      positions[i * 3]     = (Math.random() - 0.5) * SPREAD;
      positions[i * 3 + 1] = Math.random() * HEIGHT - 1;
      positions[i * 3 + 2] = (Math.random() - 0.5) * SPREAD;
      speeds[i] = 0.002 + Math.random() * 0.003;
    }
    return { positions, speeds };
  }, []);

  useFrame(() => {
    if (!ref.current) return;
    const pos = ref.current.geometry.attributes.position.array as Float32Array;
    for (let i = 0; i < COUNT; i++) {
      pos[i * 3 + 1] += speeds[i];
      if (pos[i * 3 + 1] > HEIGHT - 1) {
        pos[i * 3]     = (Math.random() - 0.5) * SPREAD;
        pos[i * 3 + 1] = -1;
        pos[i * 3 + 2] = (Math.random() - 0.5) * SPREAD;
      }
    }
    ref.current.geometry.attributes.position.needsUpdate = true;
  });

  return (
    <points ref={ref}>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" args={[positions, 3]} />
      </bufferGeometry>
      <pointsMaterial
        color="#00CFFF"
        size={0.018}
        transparent
        opacity={0.18}
        sizeAttenuation
        depthWrite={false}
      />
    </points>
  );
}
