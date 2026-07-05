/**
 * ConnectionBeam — thin fixed glowing line from component to vehicle hotspot.
 * Straight line (no arc). 2 flowing particles. Brightens when active.
 */
import { useRef, useMemo } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";

const CYAN = new THREE.Color("#00CFFF");
const PARTICLE_COUNT = 3;

interface Props {
  from:      [number, number, number];
  to:        [number, number, number];
  color?:    THREE.Color;
  active?:   boolean;
  highlight?: boolean;
}

export default function ConnectionBeam({
  from, to, color = CYAN, active = true, highlight = false,
}: Props) {
  const lineRef      = useRef<THREE.Line>(null);
  const particleRefs = useRef<(THREE.Mesh | null)[]>([]);

  const { geometry, points } = useMemo(() => {
    const a = new THREE.Vector3(...from);
    const b = new THREE.Vector3(...to);
    const pts = [a, b];
    const geo = new THREE.BufferGeometry().setFromPoints(pts);
    return { geometry: geo, points: pts };
  }, [from, to]);

  const lineMat = useMemo(() => new THREE.LineBasicMaterial({
    color,
    transparent: true,
    opacity: 0,
    depthWrite: false,
    toneMapped: false,
  }), [color]);

  const particleOffsets = useMemo(
    () => Array.from({ length: PARTICLE_COUNT }, (_, i) => i / PARTICLE_COUNT),
    []
  );

  useFrame(({ clock }) => {
    const t = clock.elapsedTime;
    const targetOpacity = active ? (highlight ? 0.95 : 0.45) : 0.18;
    lineMat.opacity += (targetOpacity - lineMat.opacity) * 0.06;
    lineMat.color   = color;

    const a = points[0];
    const b = points[1];

    particleRefs.current.forEach((mesh, i) => {
      if (!mesh) return;
      const offset = (particleOffsets[i] + t * 0.22) % 1;
      mesh.position.lerpVectors(a, b, offset);
      const mat = mesh.material as THREE.MeshStandardMaterial;
      const edge = Math.min(offset, 1 - offset) * 5;
      const targetPOp = Math.min(edge, 1) * (active ? (highlight ? 1.0 : 0.7) : 0.2);
      mat.opacity += (targetPOp - mat.opacity) * 0.08;
      mat.emissiveIntensity = highlight ? 4.0 : 2.5;
    });
  });

  return (
    <group>
      <primitive object={new THREE.Line(geometry, lineMat)} ref={lineRef} />
      {particleOffsets.map((_, i) => (
        <mesh key={i} ref={el => { particleRefs.current[i] = el; }}>
          <sphereGeometry args={[0.038, 5, 5]} />
          <meshStandardMaterial
            color={color}
            emissive={color}
            emissiveIntensity={2.5}
            transparent
            opacity={0}
            toneMapped={false}
            depthWrite={false}
          />
        </mesh>
      ))}
    </group>
  );
}
