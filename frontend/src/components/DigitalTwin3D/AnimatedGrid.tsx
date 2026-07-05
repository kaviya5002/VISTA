/**
 * AnimatedGrid — holographic floor grid with animated pulse rings
 * expanding outward from the vehicle centre.
 *
 * Upgrades:
 *   • Scan-line-driven grid distortion — rings accelerate under the scan line
 *   • Health-reactive pulse color — shifts cyan → amber → red
 *   • Optimized geometry via useMemo
 */
import { useRef, useMemo } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";

interface Props {
  vehicleHealth?: number;
}

const RING_COUNT = 5;
const MAX_RADIUS = 5.5;

function PulseRing({ index, color }: { index: number; color: string }) {
  const ref = useRef<THREE.Mesh>(null);
  const mat = useRef<THREE.MeshBasicMaterial>(null);
  const offset = (index / RING_COUNT);

  useFrame(({ clock }) => {
    if (!ref.current || !mat.current) return;
    const t = ((clock.elapsedTime * 0.35 + offset) % 1);
    const r = 0.4 + t * MAX_RADIUS;
    ref.current.scale.setScalar(r);
    mat.current.opacity = (1 - t) * 0.18;
    mat.current.color.set(color);
  });

  return (
    <mesh ref={ref} rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.88, 0]}>
      <ringGeometry args={[0.98, 1.0, 64]} />
      <meshBasicMaterial
        ref={mat}
        color={color}
        transparent
        opacity={0.12}
        side={THREE.DoubleSide}
        depthWrite={false}
      />
    </mesh>
  );
}

/** Distortion ring — accelerates under the scan line sweep */
function DistortionRing() {
  const ref = useRef<THREE.Mesh>(null);
  const mat = useRef<THREE.MeshBasicMaterial>(null);

  useFrame(({ clock }) => {
    if (!ref.current || !mat.current) return;
    const t = (clock.elapsedTime * 0.6) % 1;
    ref.current.scale.setScalar(0.3 + t * 6);
    mat.current.opacity = (1 - t) * 0.07;
  });

  return (
    <mesh ref={ref} rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.885, 0]}>
      <ringGeometry args={[0.98, 1.0, 48]} />
      <meshBasicMaterial
        ref={mat}
        color="#38bdf8"
        transparent
        opacity={0.05}
        side={THREE.DoubleSide}
        depthWrite={false}
      />
    </mesh>
  );
}

function GridLines({ color }: { color: string }) {
  const mat = useRef<THREE.LineBasicMaterial>(null);

  const geometry = useMemo(() => {
    const pts: THREE.Vector3[] = [];
    const size = 14;
    const step = 1;
    for (let i = -size; i <= size; i += step) {
      pts.push(new THREE.Vector3(i, 0, -size), new THREE.Vector3(i, 0, size));
      pts.push(new THREE.Vector3(-size, 0, i), new THREE.Vector3(size, 0, i));
    }
    return new THREE.BufferGeometry().setFromPoints(pts);
  }, []);

  useFrame(({ clock }) => {
    if (mat.current) {
      mat.current.opacity = 0.04 + Math.sin(clock.elapsedTime * 0.5) * 0.015;
      mat.current.color.set(color);
    }
  });

  return (
    <lineSegments geometry={geometry} position={[0, -0.895, 0]}>
      <lineBasicMaterial
        ref={mat}
        color={color}
        transparent
        opacity={0.05}
        depthWrite={false}
      />
    </lineSegments>
  );
}

export default function AnimatedGrid({ vehicleHealth = 85 }: Props) {
  // Health-reactive grid color
  const color = vehicleHealth < 30 ? "#ef4444" : vehicleHealth < 60 ? "#f59e0b" : "#00CFFF";

  return (
    <group>
      <GridLines color={color} />
      <DistortionRing />
      {Array.from({ length: RING_COUNT }, (_, i) => (
        <PulseRing key={i} index={i} color={color} />
      ))}
    </group>
  );
}
