/**
 * GroundReflection — Industrial environment polish
 *
 * Layers:
 *   1. Reflective mirror plane  — MeshStandardMaterial with metalness/roughness
 *      giving a subtle wet-floor reflection of the vehicle above
 *   2. Holographic floor pulse  — radial gradient disc that breathes
 *   3. Critical component glow  — volumetric point-light halos at each
 *      critical component hotspot, colour-coded red
 *   4. Alarm ring               — fast-pulsing ring when vehicle health < 30%
 */

import { useRef, useMemo } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";
import { REGISTRY } from "./ComponentRegistry";

// ── Reflective floor plane ────────────────────────────────────────────────────

function ReflectivePlane({ health }: { health: number }) {
  const ref = useRef<THREE.Mesh>(null);

  const material = useMemo(
    () =>
      new THREE.MeshStandardMaterial({
        color: new THREE.Color("#050d1a"),
        metalness: 0.82,
        roughness: 0.38,
        envMapIntensity: 0.6,
        transparent: true,
        opacity: 0.72,
      }),
    []
  );

  useFrame(({ clock }) => {
    if (!ref.current) return;
    // Subtle shimmer — health-reactive tint
    const t = clock.elapsedTime;
    const shimmer = 0.68 + Math.sin(t * 0.7) * 0.06;
    material.opacity = shimmer;
    // Shift colour toward red as health degrades
    const r = health < 45 ? 0.08 + (1 - health / 45) * 0.06 : 0.05;
    material.color.setRGB(r, 0.05, 0.1);
  });

  return (
    <mesh ref={ref} rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.901, 0]} receiveShadow>
      <planeGeometry args={[22, 22]} />
      <primitive object={material} />
    </mesh>
  );
}

// ── Holographic floor pulse disc ──────────────────────────────────────────────

function FloorPulseDisc() {
  const ref = useRef<THREE.Mesh>(null);
  const mat = useRef<THREE.MeshBasicMaterial>(null);

  useFrame(({ clock }) => {
    if (!ref.current || !mat.current) return;
    const t = clock.elapsedTime;
    const s = 1.0 + Math.sin(t * 0.55) * 0.08;
    ref.current.scale.setScalar(s);
    mat.current.opacity = 0.06 + Math.sin(t * 0.55) * 0.025;
  });

  return (
    <mesh ref={ref} rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.895, 0]}>
      <circleGeometry args={[3.8, 64]} />
      <meshBasicMaterial
        ref={mat}
        color="#00CFFF"
        transparent
        opacity={0.07}
        side={THREE.DoubleSide}
        depthWrite={false}
      />
    </mesh>
  );
}

// ── Volumetric glow halo around a critical component ─────────────────────────

function CriticalHalo({ position }: { position: [number, number, number] }) {
  const ref = useRef<THREE.Mesh>(null);
  const mat = useRef<THREE.MeshBasicMaterial>(null);

  useFrame(({ clock }) => {
    if (!ref.current || !mat.current) return;
    const t = clock.elapsedTime;
    const s = 0.9 + Math.sin(t * 3.8) * 0.35;
    ref.current.scale.setScalar(s);
    mat.current.opacity = 0.12 + Math.sin(t * 3.8) * 0.08;
  });

  return (
    <mesh ref={ref} position={position}>
      <sphereGeometry args={[0.55, 16, 16]} />
      <meshBasicMaterial
        ref={mat}
        color="#ef4444"
        transparent
        opacity={0.15}
        depthWrite={false}
        side={THREE.BackSide}
      />
    </mesh>
  );
}

// ── Critical alarm ring (health < 30%) ────────────────────────────────────────

function AlarmRing() {
  const ref = useRef<THREE.Mesh>(null);
  const mat = useRef<THREE.MeshBasicMaterial>(null);

  useFrame(({ clock }) => {
    if (!ref.current || !mat.current) return;
    const t = ((clock.elapsedTime * 2.2) % 1);
    ref.current.scale.setScalar(0.8 + t * 3.5);
    mat.current.opacity = (1 - t) * 0.28;
  });

  return (
    <mesh ref={ref} rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.88, 0]}>
      <ringGeometry args={[0.9, 1.0, 64]} />
      <meshBasicMaterial
        ref={mat}
        color="#ef4444"
        transparent
        opacity={0.2}
        side={THREE.DoubleSide}
        depthWrite={false}
      />
    </mesh>
  );
}

// ── Grid distortion wave under scan line ──────────────────────────────────────

function GridDistortion() {
  const ref = useRef<THREE.Mesh>(null);
  const mat = useRef<THREE.MeshBasicMaterial>(null);

  useFrame(({ clock }) => {
    if (!ref.current || !mat.current) return;
    const t = clock.elapsedTime;
    // Ripple outward from centre
    const wave = (t * 0.4) % 1;
    ref.current.scale.setScalar(0.5 + wave * 5);
    mat.current.opacity = (1 - wave) * 0.055;
  });

  return (
    <mesh ref={ref} rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.893, 0]}>
      <ringGeometry args={[0.98, 1.0, 48]} />
      <meshBasicMaterial
        ref={mat}
        color="#38bdf8"
        transparent
        opacity={0.04}
        side={THREE.DoubleSide}
        depthWrite={false}
      />
    </mesh>
  );
}

// ── Main export ───────────────────────────────────────────────────────────────

interface Props {
  vehicleHealth:       number;
  criticalComponents:  string[];
}

export default function GroundReflection({ vehicleHealth, criticalComponents }: Props) {
  const isCritical = vehicleHealth < 30;
  const critSet    = useMemo(() => new Set(criticalComponents.map(c => c.toLowerCase())), [criticalComponents]);

  return (
    <group>
      <ReflectivePlane health={vehicleHealth} />
      <FloorPulseDisc />
      <GridDistortion />

      {/* Volumetric halos at each critical component hotspot */}
      {REGISTRY.map(def => {
        if (!critSet.has(def.id)) return null;
        return <CriticalHalo key={def.id} position={def.hotspot} />;
      })}

      {/* Alarm ring when health < 30% */}
      {isCritical && <AlarmRing />}
    </group>
  );
}
