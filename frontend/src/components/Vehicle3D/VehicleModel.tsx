/**
 * VehicleModel — procedural 3D car built entirely from Three.js primitives.
 *
 * Layout (top view):
 *   ┌──────────────────────────┐
 *   │  [battery][motor][trans] │  ← engine bay (front half)
 *   │  [cooling]               │
 *   │  [brakes L/R]            │  ← wheel corners
 *   │  [electrical]            │  ← cabin floor
 *   └──────────────────────────┘
 *
 * Each part is a separate mesh, clickable, colour-coded by AI health.
 */

import { useRef } from "react";
import type { ThreeEvent } from "@react-three/fiber";
import { RoundedBox, Text } from "@react-three/drei";
import * as THREE from "three";
import { healthToColor, healthToEmissive } from "./utils";
import type { ComponentKey } from "./utils";

interface PartProps {
  position: [number, number, number];
  size:     [number, number, number];
  health:   number;
  label:    string;
  id:       ComponentKey;
  selected: boolean;
  onClick:  (id: ComponentKey) => void;
}

function Part({ position, size, health, label, id, selected, onClick }: PartProps) {
  const meshRef = useRef<THREE.Mesh>(null);
  const color   = healthToColor(health);
  const emissive = selected ? color : healthToEmissive(health);

  return (
    <group position={position}>
      <RoundedBox
        ref={meshRef}
        args={size}
        radius={0.04}
        smoothness={4}
        onClick={(e: ThreeEvent<MouseEvent>) => { e.stopPropagation(); onClick(id); }}
        onPointerOver={() => document.body.style.cursor = "pointer"}
        onPointerOut={() =>  document.body.style.cursor = "default"}
      >
        <meshStandardMaterial
          color={color}
          emissive={emissive}
          emissiveIntensity={selected ? 0.6 : 0.2}
          roughness={0.4}
          metalness={0.5}
        />
      </RoundedBox>
      {/* Health % label floating above */}
      <Text
        position={[0, size[1] / 2 + 0.12, 0]}
        fontSize={0.11}
        color={color}
        anchorX="center"
        anchorY="bottom"
        renderOrder={10}
      >
        {label} {health}%
      </Text>
    </group>
  );
}

interface Props {
  twin:       Record<string, any>;   // component twin payload
  selected:   ComponentKey | null;
  onSelect:   (id: ComponentKey) => void;
}

export default function VehicleModel({ twin, selected, onSelect }: Props) {
  const g = (key: string) => twin?.[key]?.health ?? 80;

  return (
    <group>
      {/* ── Car body shell ─────────────────────────────────────── */}
      {/* Bottom chassis */}
      <mesh position={[0, -0.18, 0]}>
        <boxGeometry args={[2.4, 0.08, 1.1]} />
        <meshStandardMaterial color="#1e293b" roughness={0.8} />
      </mesh>

      {/* Cabin */}
      <mesh position={[0.1, 0.22, 0]}>
        <boxGeometry args={[1.0, 0.36, 0.92]} />
        <meshStandardMaterial color="#0f172a" roughness={0.6} metalness={0.3} />
      </mesh>

      {/* Windshield tint */}
      <mesh position={[0.56, 0.26, 0]} rotation={[0, 0, -0.4]}>
        <planeGeometry args={[0.44, 0.3]} />
        <meshStandardMaterial color="#7dd3fc" transparent opacity={0.35} />
      </mesh>

      {/* ── Wheels ─────────────────────────────────────────────── */}
      {([ [-0.95, -0.22,  0.62], [-0.95, -0.22, -0.62],
          [ 0.95, -0.22,  0.62], [ 0.95, -0.22, -0.62] ] as [number,number,number][])
        .map((pos, i) => (
          <mesh key={i} position={pos} rotation={[Math.PI / 2, 0, 0]}>
            <cylinderGeometry args={[0.18, 0.18, 0.14, 20]} />
            <meshStandardMaterial color="#1e1e2e" roughness={0.9} />
          </mesh>
        ))
      }

      {/* ── Interactive component parts ─────────────────────────── */}
      {/* Battery — front-left */}
      <Part
        id="battery" label="Battery"
        position={[-0.75, 0.0, 0.3]}
        size={[0.44, 0.2, 0.38]}
        health={g("battery")}
        selected={selected === "battery"}
        onClick={onSelect}
      />

      {/* Motor — centre-front */}
      <Part
        id="motor" label="Motor"
        position={[-0.75, 0.0, -0.1]}
        size={[0.44, 0.22, 0.32]}
        health={g("motor")}
        selected={selected === "motor"}
        onClick={onSelect}
      />

      {/* Transmission — rear */}
      <Part
        id="transmission" label="Trans"
        position={[0.75, 0.0, -0.1]}
        size={[0.38, 0.18, 0.32]}
        health={g("transmission")}
        selected={selected === "transmission"}
        onClick={onSelect}
      />

      {/* Cooling — front-centre-top */}
      <Part
        id="cooling" label="Cooling"
        position={[-1.0, 0.06, -0.1]}
        size={[0.26, 0.22, 0.7]}
        health={g("cooling")}
        selected={selected === "cooling"}
        onClick={onSelect}
      />

      {/* Brakes — rear axle area */}
      <Part
        id="brakes" label="Brakes"
        position={[0.78, -0.05, 0.48]}
        size={[0.28, 0.12, 0.18]}
        health={g("brakes")}
        selected={selected === "brakes"}
        onClick={onSelect}
      />

      {/* Electrical — under cabin */}
      <Part
        id="electrical" label="Elec"
        position={[0.1, -0.08, 0.35]}
        size={[0.48, 0.12, 0.3]}
        health={g("electrical")}
        selected={selected === "electrical"}
        onClick={onSelect}
      />
    </group>
  );
}
