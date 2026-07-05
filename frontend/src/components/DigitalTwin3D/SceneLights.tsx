/**
 * SceneLights — premium holographic lighting rig
 *
 * Lights:
 *   1. Ambient       — health-reactive: smooth lerp cool-blue → red as health degrades
 *   2. Key light     — cool white from above-front
 *   3. Cyan rim      — left-rear blue-cyan edge glow (pulsing)
 *   4. Purple fill   — right side depth (pulsing)
 *   5. Ground bounce — teal from below
 *   6. Front accent  — subtle front fill
 *   7. Top halo      — overhead blue-white
 *   8. Critical alarm — red point light, only when health < 30, fast pulse
 *   9. Dynamic fill  — intensity scales with vehicle health
 */
import { useRef, useMemo } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";

interface Props {
  vehicleHealth?: number;
}

function PulsingLight({
  position, color, baseIntensity, speed,
}: {
  position: [number, number, number];
  color: string;
  baseIntensity: number;
  speed: number;
}) {
  const ref = useRef<THREE.PointLight>(null);
  useFrame(({ clock }) => {
    if (ref.current) {
      ref.current.intensity = baseIntensity + Math.sin(clock.elapsedTime * speed) * (baseIntensity * 0.18);
    }
  });
  return (
    <pointLight
      ref={ref}
      position={position}
      intensity={baseIntensity}
      color={color}
      distance={20}
      decay={2}
    />
  );
}

/** Critical alarm — fast red pulse, only rendered when health < 30 */
function CriticalAlarmLight() {
  const ref = useRef<THREE.PointLight>(null);
  useFrame(({ clock }) => {
    if (ref.current) {
      ref.current.intensity = 1.8 + Math.sin(clock.elapsedTime * 4 * Math.PI * 2) * 1.4;
    }
  });
  return (
    <pointLight
      ref={ref}
      position={[0, 3, 0]}
      intensity={2.0}
      color="#ef4444"
      distance={12}
      decay={2}
    />
  );
}

/** Dynamic ambient — smoothly lerps color and intensity based on health */
function DynamicAmbient({ health }: { health: number }) {
  const ref = useRef<THREE.AmbientLight>(null);

  // Target values derived from health
  const target = useMemo(() => {
    if (health < 30)  return { color: new THREE.Color("#1a0505"), intensity: 0.22 };
    if (health < 60)  return { color: new THREE.Color("#120d05"), intensity: 0.18 };
    return { color: new THREE.Color("#060d1f"), intensity: 0.14 };
  }, [health]);

  const currentColor = useRef(target.color.clone());
  const currentIntensity = useRef(target.intensity);

  useFrame(() => {
    if (!ref.current) return;
    // Smooth lerp toward target
    currentColor.current.lerp(target.color, 0.02);
    currentIntensity.current += (target.intensity - currentIntensity.current) * 0.02;
    ref.current.color.copy(currentColor.current);
    ref.current.intensity = currentIntensity.current;
  });

  return <ambientLight ref={ref} intensity={target.intensity} color={target.color} />;
}

/** Dynamic fill light — dims as health degrades to increase drama */
function DynamicFill({ health }: { health: number }) {
  const ref = useRef<THREE.PointLight>(null);

  useFrame(() => {
    if (!ref.current) return;
    const targetIntensity = 0.3 + (health / 100) * 0.7;
    ref.current.intensity += (targetIntensity - ref.current.intensity) * 0.02;
  });

  return (
    <pointLight
      ref={ref}
      position={[0, 1.5, -5]}
      intensity={0.6}
      color="#38bdf8"
      distance={10}
      decay={2}
    />
  );
}

export default function SceneLights({ vehicleHealth = 85 }: Props) {
  const isCritical = vehicleHealth < 30;

  return (
    <>
      {/* 1. Ambient — health-reactive smooth lerp */}
      <DynamicAmbient health={vehicleHealth} />

      {/* 2. Key light — cool white from above-front */}
      <directionalLight position={[3, 9, 5]} intensity={0.65} color="#c8e8ff" />

      {/* 3. Cyan rim — holographic signature glow from left-rear (pulsing) */}
      <PulsingLight position={[-6, 4, -6]} color="#00CFFF" baseIntensity={2.8} speed={0.9} />

      {/* 4. Purple fill — right side depth (pulsing) */}
      <PulsingLight position={[6, 3, 2]} color="#818cf8" baseIntensity={1.4} speed={1.3} />

      {/* 5. Ground bounce — teal from below */}
      <pointLight position={[0, -0.5, 0]} intensity={1.0} color="#00ffcc" distance={9} decay={2} />

      {/* 6. Front accent — dynamic intensity */}
      <DynamicFill health={vehicleHealth} />

      {/* 7. Top halo — overhead blue-white */}
      <pointLight position={[0, 7, 0]} intensity={0.5} color="#e0f2fe" distance={14} decay={2} />

      {/* 8. Critical alarm — only when health < 30 */}
      {isCritical && <CriticalAlarmLight />}
    </>
  );
}
