import { useRef } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";
import { makeWireframeMaterial, makeSolidMaterial } from "./WireframeMaterial";

interface Props {
  color: THREE.Color;
  pulseIntensity: number;
  hovered: boolean;
  onClick: () => void;
  onPointerOver: () => void;
  onPointerOut: () => void;
}

const WHEEL_POSITIONS: [number, number, number][] = [
  [-1.1, -0.55,  1.5],
  [ 1.1, -0.55,  1.5],
  [-1.1, -0.55, -1.5],
  [ 1.1, -0.55, -1.5],
];

export default function Brake({ color, pulseIntensity, hovered, onClick, onPointerOver, onPointerOut }: Props) {
  const refs = [useRef<THREE.Mesh>(null), useRef<THREE.Mesh>(null), useRef<THREE.Mesh>(null), useRef<THREE.Mesh>(null)];

  useFrame(() => {
    refs.forEach(r => {
      if (!r.current) return;
      const mat = r.current.material as THREE.MeshStandardMaterial;
      mat.emissiveIntensity = hovered ? 0.9 : pulseIntensity;
    });
  });

  return (
    <group>
      {WHEEL_POSITIONS.map((pos, i) => (
        <group key={i} position={pos}>
          {/* Disc */}
          <mesh>
            <cylinderGeometry args={[0.28, 0.28, 0.06, 16]} />
            <primitive object={makeSolidMaterial(color, hovered ? 0.35 : 0.18)} />
          </mesh>
          <mesh
            ref={refs[i]}
            onClick={onClick}
            onPointerOver={onPointerOver}
            onPointerOut={onPointerOut}
          >
            <cylinderGeometry args={[0.28, 0.28, 0.06, 16]} />
            <primitive object={makeWireframeMaterial(color)} />
          </mesh>
          {/* Caliper */}
          <mesh position={[0.2, 0, 0]}>
            <boxGeometry args={[0.12, 0.18, 0.22]} />
            <meshStandardMaterial color={color} emissive={color} emissiveIntensity={0.6} transparent opacity={0.6} />
          </mesh>
        </group>
      ))}
    </group>
  );
}
