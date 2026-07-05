/**
 * StatusRing — premium holographic vehicle status indicator
 *
 * Four layers:
 *   1. Outer ring  — slow CW rotation, health color, pulsing opacity
 *   2. Inner ring  — slow CCW rotation, dimmer
 *   3. Tick marks  — 16 evenly spaced dashes
 *   4. Arc fill    — partial arc showing health percentage
 */
import { useRef, useMemo } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";

interface Props {
  health: number;
}

function healthRingColor(health: number): THREE.Color {
  if (health >= 75) return new THREE.Color("#00ffcc");
  if (health >= 45) return new THREE.Color("#f59e0b");
  return new THREE.Color("#ef4444");
}

function HealthArc({ health, color }: { health: number; color: THREE.Color }) {
  const ref = useRef<THREE.Mesh>(null);
  const mat = useRef<THREE.MeshBasicMaterial>(null);

  // Build arc geometry based on health %
  const geometry = useMemo(() => {
    const thetaLength = (health / 100) * Math.PI * 2;
    return new THREE.RingGeometry(2.88, 2.98, 64, 1, -Math.PI / 2, thetaLength);
  }, [health]);

  useFrame(({ clock }) => {
    if (mat.current) {
      mat.current.color = color;
      mat.current.opacity = 0.55 + Math.sin(clock.elapsedTime * 1.6) * 0.2;
    }
  });

  return (
    <mesh ref={ref} geometry={geometry} rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.88, 0]}>
      <meshBasicMaterial
        ref={mat}
        color={color}
        transparent
        opacity={0.6}
        side={THREE.DoubleSide}
        depthWrite={false}
      />
    </mesh>
  );
}

export default function StatusRing({ health }: Props) {
  const outerRef = useRef<THREE.Mesh>(null);
  const innerRef = useRef<THREE.Mesh>(null);
  const outerMat = useRef<THREE.MeshBasicMaterial>(null);
  const innerMat = useRef<THREE.MeshBasicMaterial>(null);

  const color = healthRingColor(health);

  const ticks = useMemo(() => {
    const out: { pos: [number, number, number]; rot: number; major: boolean }[] = [];
    for (let i = 0; i < 16; i++) {
      const angle = (i / 16) * Math.PI * 2;
      const r = 2.72;
      out.push({
        pos: [Math.sin(angle) * r, -0.88, Math.cos(angle) * r],
        rot: angle,
        major: i % 4 === 0,
      });
    }
    return out;
  }, []);

  useFrame(({ clock }) => {
    const t = clock.elapsedTime;
    if (outerRef.current) {
      outerRef.current.rotation.z = t * 0.16;
      if (outerMat.current) {
        outerMat.current.color = color;
        outerMat.current.opacity = 0.38 + Math.sin(t * 1.4) * 0.16;
      }
    }
    if (innerRef.current) {
      innerRef.current.rotation.z = -t * 0.26;
      if (innerMat.current) {
        innerMat.current.color = color;
        innerMat.current.opacity = 0.18 + Math.sin(t * 1.8 + 1) * 0.08;
      }
    }
  });

  return (
    <group>
      {/* Outer ring — rotates CW */}
      <mesh ref={outerRef} rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.88, 0]}>
        <ringGeometry args={[2.62, 2.78, 64]} />
        <meshBasicMaterial ref={outerMat} color={color} transparent opacity={0.45}
          side={THREE.DoubleSide} depthWrite={false} />
      </mesh>

      {/* Inner ring — rotates CCW */}
      <mesh ref={innerRef} rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.88, 0]}>
        <ringGeometry args={[2.3, 2.44, 48]} />
        <meshBasicMaterial ref={innerMat} color={color} transparent opacity={0.22}
          side={THREE.DoubleSide} depthWrite={false} />
      </mesh>

      {/* Health arc fill */}
      <HealthArc health={health} color={color} />

      {/* Tick marks */}
      {ticks.map((tick, i) => (
        <mesh key={i} position={tick.pos} rotation={[-Math.PI / 2, 0, tick.rot]}>
          <planeGeometry args={[tick.major ? 0.06 : 0.03, tick.major ? 0.22 : 0.12]} />
          <meshBasicMaterial
            color={color}
            transparent
            opacity={tick.major ? 0.75 : 0.32}
            side={THREE.DoubleSide}
            depthWrite={false}
          />
        </mesh>
      ))}
    </group>
  );
}
