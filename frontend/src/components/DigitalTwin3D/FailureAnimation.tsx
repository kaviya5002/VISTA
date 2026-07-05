/**
 * FailureAnimation — Advanced Failure Propagation
 *
 * Animated glowing energy particles travelling along propagation paths.
 * Directional animated arrows.
 * Failure path highlighting with pulse speed ∝ failure_probability.
 * Critical component flashing with volumetric halo.
 * Propagation: Battery → Electrical → Cooling → Motor → Transmission → Brakes.
 * All driven from FAILURE_CHAIN + HOTSPOT_VECTORS + live AI state.
 */

import { useRef, useMemo, memo } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";
import { FAILURE_CHAIN, HOTSPOT_VECTORS } from "./ComponentRegistry";

interface Props {
  criticalComponents: string[];
  pulseTime:          number;
  failureProbs?:      Record<string, number>;
}

// ── Glowing path tube ─────────────────────────────────────────────────────────

const PathTube = memo(function PathTube({ from, to }: { from: THREE.Vector3; to: THREE.Vector3 }) {
  const ref = useRef<THREE.Mesh>(null);

  const { midpoint, length, quaternion } = useMemo(() => {
    const d   = new THREE.Vector3().subVectors(to, from);
    const len = d.length();
    const mid = new THREE.Vector3().addVectors(from, d.clone().multiplyScalar(0.5));
    const q   = new THREE.Quaternion();
    q.setFromUnitVectors(new THREE.Vector3(0, 1, 0), d.clone().normalize());
    return { midpoint: mid, length: len, quaternion: q };
  }, [from, to]);

  useFrame(({ clock }) => {
    if (!ref.current) return;
    const mat = ref.current.material as THREE.MeshStandardMaterial;
    mat.emissiveIntensity = 0.6 + Math.sin(clock.elapsedTime * 2.1) * 0.35;
    mat.opacity           = 0.18 + Math.sin(clock.elapsedTime * 1.7) * 0.08;
  });

  return (
    <mesh ref={ref} position={midpoint} quaternion={quaternion}>
      <cylinderGeometry args={[0.032, 0.032, length, 8]} />
      <meshStandardMaterial
        color="#ef4444" emissive="#ff2222"
        emissiveIntensity={0.8} transparent opacity={0.22}
        depthWrite={false}
      />
    </mesh>
  );
});

// ── Directional arrow cone ────────────────────────────────────────────────────

const ArrowCone = memo(function ArrowCone({ from, to, speed }: { from: THREE.Vector3; to: THREE.Vector3; speed: number }) {
  const ref = useRef<THREE.Mesh>(null);

  const { position, quaternion } = useMemo(() => {
    const d   = new THREE.Vector3().subVectors(to, from);
    const pos = new THREE.Vector3().addVectors(from, d.clone().multiplyScalar(0.65));
    const q   = new THREE.Quaternion();
    q.setFromUnitVectors(new THREE.Vector3(0, 1, 0), d.clone().normalize());
    return { position: pos, quaternion: q };
  }, [from, to]);

  useFrame(({ clock }) => {
    if (!ref.current) return;
    const mat = ref.current.material as THREE.MeshStandardMaterial;
    // Pulse speed proportional to failure probability
    mat.emissiveIntensity = 1.2 + Math.sin(clock.elapsedTime * speed * 3.5) * 0.6;
  });

  return (
    <mesh ref={ref} position={position} quaternion={quaternion}>
      <coneGeometry args={[0.055, 0.14, 8]} />
      <meshStandardMaterial
        color="#ff4444" emissive="#ff2222"
        emissiveIntensity={1.5} transparent opacity={0.9}
      />
    </mesh>
  );
});

// ── Traveling energy particle along a path ────────────────────────────────────

function TravelParticle({
  from, to, speed, offset, size, color,
}: {
  from: THREE.Vector3; to: THREE.Vector3;
  speed: number; offset: number;
  size: number; color: string;
}) {
  const ref  = useRef<THREE.Mesh>(null);
  const tRef = useRef(offset);

  useFrame((_, delta) => {
    tRef.current = (tRef.current + delta * speed) % 1;
    if (ref.current) {
      ref.current.position.lerpVectors(from, to, tRef.current);
      const s = size * (0.7 + Math.sin(tRef.current * Math.PI) * 0.6);
      ref.current.scale.setScalar(s);
    }
  });

  return (
    <mesh ref={ref}>
      <sphereGeometry args={[1, 8, 8]} />
      <meshStandardMaterial
        color={color} emissive={color}
        emissiveIntensity={2.5} transparent opacity={0.9}
        depthWrite={false}
      />
    </mesh>
  );
}

// ── Propagation line with multiple traveling particles ────────────────────────

interface LineProps {
  from:  THREE.Vector3;
  to:    THREE.Vector3;
  speed: number;
}

const PropagationLine = memo(function PropagationLine({ from, to, speed }: LineProps) {
  const lineRef = useRef<THREE.Mesh>(null);

  const { midpoint, length, quaternion } = useMemo(() => {
    const d   = new THREE.Vector3().subVectors(to, from);
    const len = d.length();
    const mid = new THREE.Vector3().addVectors(from, d.clone().multiplyScalar(0.5));
    const q   = new THREE.Quaternion();
    q.setFromUnitVectors(new THREE.Vector3(0, 1, 0), d.clone().normalize());
    return { midpoint: mid, length: len, quaternion: q };
  }, [from, to]);

  useFrame(({ clock }) => {
    if (!lineRef.current) return;
    const mat = lineRef.current.material as THREE.MeshStandardMaterial;
    mat.emissiveIntensity = 0.5 + Math.sin(clock.elapsedTime * speed * 2) * 0.4;
    mat.opacity           = 0.35 + Math.sin(clock.elapsedTime * speed) * 0.2;
  });

  // 3 staggered particles per segment for dense energy flow
  const offsets = useMemo(() => [0, 0.33, 0.66], []);

  return (
    <group>
      <mesh ref={lineRef} position={midpoint} quaternion={quaternion}>
        <cylinderGeometry args={[0.018, 0.018, length, 6]} />
        <meshStandardMaterial
          color="#ef4444" emissive="#ef4444"
          emissiveIntensity={0.7} transparent opacity={0.45}
          depthWrite={false}
        />
      </mesh>

      {offsets.map((off, i) => (
        <TravelParticle
          key={i}
          from={from} to={to}
          speed={speed} offset={off}
          size={i === 0 ? 0.06 : 0.035}
          color={i === 0 ? "#ff6b6b" : "#fca5a5"}
        />
      ))}
    </group>
  );
});

// ── Critical pulse sphere with expanding ring ─────────────────────────────────

const CriticalPulse = memo(function CriticalPulse({ position, speed }: { position: THREE.Vector3; speed: number }) {
  const coreRef  = useRef<THREE.Mesh>(null);
  const ringRef  = useRef<THREE.Mesh>(null);
  const haloRef  = useRef<THREE.Mesh>(null);

  useFrame(({ clock }) => {
    const t = clock.elapsedTime;

    if (coreRef.current) {
      const s = 0.09 + Math.sin(t * speed * 4) * 0.04;
      coreRef.current.scale.setScalar(s);
      (coreRef.current.material as THREE.MeshStandardMaterial).emissiveIntensity =
        1.5 + Math.sin(t * speed * 4) * 0.8;
    }

    if (ringRef.current) {
      const ring = (t * speed * 1.5) % 1;
      ringRef.current.scale.setScalar(0.1 + ring * 0.5);
      (ringRef.current.material as THREE.MeshStandardMaterial).opacity = (1 - ring) * 0.5;
    }

    if (haloRef.current) {
      // Volumetric outer glow — breathes slowly
      const h = 0.8 + Math.sin(t * speed * 1.2) * 0.25;
      haloRef.current.scale.setScalar(h);
      (haloRef.current.material as THREE.MeshBasicMaterial).opacity =
        0.06 + Math.sin(t * speed * 1.2) * 0.04;
    }
  });

  return (
    <group position={position}>
      {/* Core flash */}
      <mesh ref={coreRef}>
        <sphereGeometry args={[1, 10, 10]} />
        <meshStandardMaterial color="#ef4444" emissive="#ef4444" emissiveIntensity={2} transparent opacity={0.7} />
      </mesh>

      {/* Expanding ring */}
      <mesh ref={ringRef} rotation={[Math.PI / 2, 0, 0]}>
        <ringGeometry args={[0.9, 1.0, 24]} />
        <meshStandardMaterial color="#ef4444" emissive="#ef4444" emissiveIntensity={1} transparent opacity={0.4} side={THREE.DoubleSide} />
      </mesh>

      {/* Volumetric outer halo */}
      <mesh ref={haloRef}>
        <sphereGeometry args={[0.7, 16, 16]} />
        <meshBasicMaterial color="#ef4444" transparent opacity={0.08} depthWrite={false} side={THREE.BackSide} />
      </mesh>
    </group>
  );
});

// ── Main component ────────────────────────────────────────────────────────────

export default memo(function FailureAnimation({ criticalComponents, pulseTime: _pulseTime, failureProbs = {} }: Props) {
  if (criticalComponents.length === 0) return null;

  const critSet = useMemo(() => new Set(criticalComponents), [criticalComponents]);

  const pairs = useMemo(() => {
    const out: Array<{ from: THREE.Vector3; to: THREE.Vector3; speed: number }> = [];
    for (let i = 0; i < FAILURE_CHAIN.length - 1; i++) {
      const a = FAILURE_CHAIN[i];
      const b = FAILURE_CHAIN[i + 1];
      if (critSet.has(a) || critSet.has(b)) {
        const posA = HOTSPOT_VECTORS[a];
        const posB = HOTSPOT_VECTORS[b];
        if (posA && posB) {
          const fp = failureProbs[a.toLowerCase()] ?? 0;
          // Speed: 0.4 base + fp contribution + cascade bonus
          out.push({ from: posA, to: posB, speed: 0.4 + fp * 1.2 + criticalComponents.length * 0.08 });
        }
      }
    }
    return out;
  }, [critSet, failureProbs, criticalComponents.length]);

  const critPositions = useMemo(() =>
    criticalComponents
      .map(name => ({ name, pos: HOTSPOT_VECTORS[name] }))
      .filter(x => x.pos != null),
    [criticalComponents]
  );

  return (
    <group>
      {pairs.map((p, i) => (
        <group key={i}>
          <PathTube from={p.from} to={p.to} />
          <PropagationLine from={p.from} to={p.to} speed={p.speed} />
          <ArrowCone from={p.from} to={p.to} speed={p.speed} />
        </group>
      ))}

      {critPositions.map(({ name, pos }) => {
        const fp = failureProbs[name.toLowerCase()] ?? 0.5;
        // Pulse speed proportional to failure probability
        const speed = 0.8 + fp * 2.4;
        return <CriticalPulse key={name} position={pos} speed={speed} />;
      })}
    </group>
  );
});
