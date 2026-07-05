import { useRef, useMemo } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";

interface Props {
  twinData: {
    battery:    { health: number };
    cooling:    { health: number };
    motor:      { health: number };
    electrical: { health: number };
  };
}

function Particles({ position, color, count, speed, spread }: {
  position: [number, number, number];
  color: string;
  count: number;
  speed: number;
  spread: number;
}) {
  const ref = useRef<THREE.Points>(null);

  const { positions, velocities } = useMemo(() => {
    const positions  = new Float32Array(count * 3);
    const velocities = new Float32Array(count * 3);
    for (let i = 0; i < count; i++) {
      positions[i * 3]     = (Math.random() - 0.5) * spread;
      positions[i * 3 + 1] = Math.random() * 0.3;
      positions[i * 3 + 2] = (Math.random() - 0.5) * spread;
      velocities[i * 3]     = (Math.random() - 0.5) * 0.01;
      velocities[i * 3 + 1] = Math.random() * speed;
      velocities[i * 3 + 2] = (Math.random() - 0.5) * 0.01;
    }
    return { positions, velocities };
  }, [count, speed, spread]);

  useFrame(() => {
    if (!ref.current) return;
    const pos = ref.current.geometry.attributes.position.array as Float32Array;
    for (let i = 0; i < count; i++) {
      pos[i * 3]     += velocities[i * 3];
      pos[i * 3 + 1] += velocities[i * 3 + 1];
      pos[i * 3 + 2] += velocities[i * 3 + 2];
      // Reset when particle goes too high
      if (pos[i * 3 + 1] > 1.5) {
        pos[i * 3]     = (Math.random() - 0.5) * spread;
        pos[i * 3 + 1] = 0;
        pos[i * 3 + 2] = (Math.random() - 0.5) * spread;
      }
    }
    ref.current.geometry.attributes.position.needsUpdate = true;
  });

  return (
    <points ref={ref} position={position}>
      <bufferGeometry>
        <bufferAttribute
          attach="attributes-position"
          args={[positions, 3]}
        />
      </bufferGeometry>
      <pointsMaterial
        color={color}
        size={0.04}
        transparent
        opacity={0.8}
        sizeAttenuation
      />
    </points>
  );
}

export default function ParticleEffects({ twinData }: Props) {
  return (
    <group>
      {/* Battery sparks — yellow, only when health < 50 */}
      {twinData.battery.health < 50 && (
        <Particles
          position={[-1.1, -0.05, 0.6]}
          color="#fbbf24"
          count={30}
          speed={0.018}
          spread={0.5}
        />
      )}

      {/* Cooling steam — cyan, only when health < 60 */}
      {twinData.cooling.health < 60 && (
        <Particles
          position={[0, 0.5, -1.9]}
          color="#67e8f9"
          count={40}
          speed={0.022}
          spread={0.8}
        />
      )}

      {/* Motor heat — orange, only when health < 55 */}
      {twinData.motor.health < 55 && (
        <Particles
          position={[1.0, 0.5, -0.8]}
          color="#f97316"
          count={25}
          speed={0.015}
          spread={0.4}
        />
      )}

      {/* Electrical pulses — always present, blue */}
      <Particles
        position={[0, 0.1, 0]}
        color="#38bdf8"
        count={20}
        speed={0.025}
        spread={1.2}
      />
    </group>
  );
}
