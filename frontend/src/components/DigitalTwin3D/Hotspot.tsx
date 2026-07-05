/**
 * Hotspot — premium interactive component marker
 *
 * Visual layers (bottom → top):
 *   1. Invisible hit sphere  — captures pointer events
 *   2. Base disc             — subtle floor shadow
 *   3. Outer pulsing ring    — health color, slow pulse
 *   4. Inner spinning ring   — faster, selected state
 *   5. Glow sphere           — hovered/selected fill
 *   6. Vertical connector    — line down to hotspot centre
 *   7. Selection burst ring  — expands outward on select
 *   8. Idle breathing halo   — slow scale breathe when idle
 *   9. Animated connection line to label anchor
 *
 * Pulse speed scales with health: critical = 4× faster.
 * Camera easing handled by CameraController (smooth lerp).
 */
import { useRef, useMemo, memo } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";
import type { ComponentDef } from "./ComponentRegistry";
import type { ComponentState } from "./useTwinAnimation";

interface Props {
  def:      ComponentDef;
  comp:     ComponentState;
  color:    THREE.Color;
  hovered:  boolean;
  selected: boolean;
  onHover:  (id: string | null) => void;
  onClick:  (id: string) => void;
}

// ── Animated connection line from hotspot to label ────────────────────────────

function ConnectionLine({
  from, to, color, active,
}: {
  from: [number, number, number];
  to:   [number, number, number];
  color: THREE.Color;
  active: boolean;
}) {
  const ref = useRef<THREE.Line>(null);

  const { geometry, material } = useMemo(() => {
    const a   = new THREE.Vector3(...from);
    const b   = new THREE.Vector3(...to);
    const mid = new THREE.Vector3(a.x, b.y, a.z);
    const geo = new THREE.BufferGeometry().setFromPoints([a, mid, b]);
    const mat = new THREE.LineBasicMaterial({
      color,
      transparent: true,
      opacity: 0,
      depthWrite: false,
    });
    return { geometry: geo, material: mat };
  }, [from, to, color]);

  useFrame(({ clock }) => {
    if (!ref.current) return;
    const mat = ref.current.material as THREE.LineBasicMaterial;
    const target = active ? 0.55 + Math.sin(clock.elapsedTime * 2) * 0.2 : 0;
    mat.opacity += (target - mat.opacity) * 0.08; // smooth easing
    mat.color   = color;
  });

  return <primitive object={new THREE.Line(geometry, material)} ref={ref} />;
}

// ── Main hotspot ──────────────────────────────────────────────────────────────

export default memo(function Hotspot({ def, comp, color, hovered, selected, onHover, onClick }: Props) {
  const outerRingRef  = useRef<THREE.Mesh>(null);
  const innerRingRef  = useRef<THREE.Mesh>(null);
  const glowRef       = useRef<THREE.Mesh>(null);
  const burstRef      = useRef<THREE.Mesh>(null);
  const connectorRef  = useRef<THREE.Mesh>(null);
  const breatheRef    = useRef<THREE.Mesh>(null);

  // Stable material refs — avoid re-creating every render
  const outerMat = useRef(new THREE.MeshBasicMaterial({
    color, transparent: true, opacity: 0.7,
    side: THREE.DoubleSide, depthWrite: false,
  }));
  const innerMat = useRef(new THREE.MeshBasicMaterial({
    color, transparent: true, opacity: 0.4,
    side: THREE.DoubleSide, depthWrite: false,
  }));
  const glowMat = useRef(new THREE.MeshBasicMaterial({
    color, transparent: true, opacity: 0,
    depthWrite: false,
  }));
  const burstMat = useRef(new THREE.MeshBasicMaterial({
    color, transparent: true, opacity: 0,
    side: THREE.DoubleSide, depthWrite: false,
  }));
  const connMat = useRef(new THREE.MeshBasicMaterial({
    color, transparent: true, opacity: 0.35,
    depthWrite: false,
  }));
  const breatheMat = useRef(new THREE.MeshBasicMaterial({
    color, transparent: true, opacity: 0.06,
    side: THREE.DoubleSide, depthWrite: false,
  }));

  // Keep colors in sync with prop
  outerMat.current.color  = color;
  innerMat.current.color  = color;
  glowMat.current.color   = color;
  burstMat.current.color  = color;
  connMat.current.color   = color;
  breatheMat.current.color = color;

  useFrame(({ clock }) => {
    const t      = clock.elapsedTime;
    const speed  = comp.health < 35 ? 4.5 : comp.health < 60 ? 2.2 : 1.0;
    const pulse  = 0.45 + Math.sin(t * speed) * 0.32;
    const active = hovered || selected;

    // Outer ring — health pulse with smooth scale easing
    if (outerRingRef.current) {
      outerMat.current.opacity = active ? 0.95 : pulse * 0.72;
      const targetS = active ? 1.0 + Math.sin(t * 3) * 0.06 : 1.0;
      outerRingRef.current.scale.lerp(
        new THREE.Vector3(targetS, targetS, targetS), 0.1
      );
    }

    // Inner ring — spins when selected, smooth easing
    if (innerRingRef.current) {
      innerMat.current.opacity = selected ? 0.65 : hovered ? 0.35 : 0.15;
      innerRingRef.current.rotation.z = selected ? t * 1.8 : t * 0.4;
    }

    // Glow sphere — smooth fade in/out
    if (glowRef.current) {
      const targetOpacity = active ? 0.22 + Math.sin(t * 3) * 0.08 : 0;
      glowMat.current.opacity += (targetOpacity - glowMat.current.opacity) * 0.1;
      const gs = active ? 1.0 + Math.sin(t * 4) * 0.1 : 1.0;
      glowRef.current.scale.lerp(new THREE.Vector3(gs, gs, gs), 0.1);
    }

    // Burst ring — expands outward when selected
    if (burstRef.current) {
      if (selected) {
        const burst = ((t * 1.2) % 1);
        burstRef.current.scale.setScalar(0.5 + burst * 1.8);
        burstMat.current.opacity = (1 - burst) * 0.55;
      } else {
        burstMat.current.opacity += (0 - burstMat.current.opacity) * 0.1;
      }
    }

    // Connector brightness
    if (connectorRef.current) {
      connMat.current.opacity = active ? 0.7 : 0.28 + Math.sin(t * speed) * 0.12;
    }

    // Idle breathing halo — slow sine when not active
    if (breatheRef.current) {
      const breathe = 0.8 + Math.sin(t * 0.9 + def.hotspot[0]) * 0.25;
      breatheRef.current.scale.setScalar(breathe);
      breatheMat.current.opacity = active ? 0 : 0.04 + Math.sin(t * 0.9) * 0.025;
    }
  });

  return (
    <group position={def.hotspot}>
      {/* Invisible hit target */}
      <mesh
        onPointerOver={e => { e.stopPropagation(); onHover(def.name); document.body.style.cursor = "pointer"; }}
        onPointerOut={e  => { e.stopPropagation(); onHover(null);     document.body.style.cursor = "default"; }}
        onClick={e        => { e.stopPropagation(); onClick(def.name); }}
      >
        <sphereGeometry args={[0.48, 8, 8]} />
        <meshBasicMaterial transparent opacity={0} depthWrite={false} />
      </mesh>

      {/* Idle breathing halo */}
      <mesh ref={breatheRef} rotation={[-Math.PI / 2, 0, 0]}>
        <ringGeometry args={[0.44, 0.62, 32]} />
        <primitive object={breatheMat.current} />
      </mesh>

      {/* Outer pulsing ring */}
      <mesh ref={outerRingRef} rotation={[-Math.PI / 2, 0, 0]}>
        <ringGeometry args={[0.28, 0.44, 36]} />
        <primitive object={outerMat.current} />
      </mesh>

      {/* Inner spinning ring */}
      <mesh ref={innerRingRef} rotation={[-Math.PI / 2, 0, 0]}>
        <ringGeometry args={[0.16, 0.26, 24]} />
        <primitive object={innerMat.current} />
      </mesh>

      {/* Glow sphere */}
      <mesh ref={glowRef}>
        <sphereGeometry args={[0.22, 12, 12]} />
        <primitive object={glowMat.current} />
      </mesh>

      {/* Burst ring — selection animation */}
      <mesh ref={burstRef} rotation={[-Math.PI / 2, 0, 0]}>
        <ringGeometry args={[0.38, 0.46, 32]} />
        <primitive object={burstMat.current} />
      </mesh>

      {/* Vertical connector line */}
      <mesh ref={connectorRef} position={[0, -0.18, 0]}>
        <cylinderGeometry args={[0.010, 0.010, 0.36, 6]} />
        <primitive object={connMat.current} />
      </mesh>

      {/* Animated connection line to label anchor */}
      <ConnectionLine
        from={[0, 0, 0]}
        to={[
          def.labelOffset[0] - def.hotspot[0],
          def.labelOffset[1] - def.hotspot[1],
          def.labelOffset[2] - def.hotspot[2],
        ]}
        color={color}
        active={hovered || selected}
      />
    </group>
  );
});
