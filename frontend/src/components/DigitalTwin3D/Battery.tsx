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

export default function Battery({ color, pulseIntensity, hovered, onClick, onPointerOver, onPointerOut }: Props) {
  const meshRef = useRef<THREE.Mesh>(null);

  useFrame(() => {
    if (!meshRef.current) return;
    const mat = meshRef.current.material as THREE.MeshStandardMaterial;
    mat.emissiveIntensity = hovered ? 0.9 : pulseIntensity;
  });

  return (
    <group position={[-1.1, -0.25, 0.6]}>
      {/* Solid fill */}
      <mesh>
        <boxGeometry args={[0.9, 0.35, 1.4]} />
        <primitive object={makeSolidMaterial(color, hovered ? 0.35 : 0.18)} />
      </mesh>
      {/* Wireframe overlay */}
      <mesh
        ref={meshRef}
        onClick={onClick}
        onPointerOver={onPointerOver}
        onPointerOut={onPointerOut}
      >
        <boxGeometry args={[0.9, 0.35, 1.4]} />
        <primitive object={makeWireframeMaterial(color)} />
      </mesh>
      {/* Terminal nubs */}
      <mesh position={[0.3, 0.22, -0.5]}>
        <cylinderGeometry args={[0.06, 0.06, 0.12, 8]} />
        <meshStandardMaterial color={color} emissive={color} emissiveIntensity={0.8} />
      </mesh>
      <mesh position={[-0.3, 0.22, -0.5]}>
        <cylinderGeometry args={[0.06, 0.06, 0.12, 8]} />
        <meshStandardMaterial color={color} emissive={color} emissiveIntensity={0.8} />
      </mesh>
    </group>
  );
}
