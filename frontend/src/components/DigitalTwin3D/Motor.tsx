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

export default function Motor({ color, pulseIntensity, hovered, onClick, onPointerOver, onPointerOut }: Props) {
  const meshRef = useRef<THREE.Mesh>(null);
  const shaftRef = useRef<THREE.Mesh>(null);

  useFrame((_state, delta) => {
    if (!meshRef.current) return;
    const mat = meshRef.current.material as THREE.MeshStandardMaterial;
    mat.emissiveIntensity = hovered ? 0.9 : pulseIntensity;
    // Shaft spins
    if (shaftRef.current) shaftRef.current.rotation.z += delta * 3;
  });

  return (
    <group position={[1.0, -0.1, -0.8]}>
      {/* Motor block */}
      <mesh>
        <boxGeometry args={[0.8, 0.6, 0.8]} />
        <primitive object={makeSolidMaterial(color, hovered ? 0.35 : 0.18)} />
      </mesh>
      <mesh
        ref={meshRef}
        onClick={onClick}
        onPointerOver={onPointerOver}
        onPointerOut={onPointerOut}
      >
        <boxGeometry args={[0.8, 0.6, 0.8]} />
        <primitive object={makeWireframeMaterial(color)} />
      </mesh>
      {/* Rotating shaft */}
      <mesh ref={shaftRef} position={[0.5, 0, 0]} rotation={[0, 0, Math.PI / 2]}>
        <cylinderGeometry args={[0.06, 0.06, 0.5, 12]} />
        <meshStandardMaterial color={color} emissive={color} emissiveIntensity={0.9} />
      </mesh>
      {/* Cooling fins */}
      {[-0.25, 0, 0.25].map((z, i) => (
        <mesh key={i} position={[0, 0.38, z]}>
          <boxGeometry args={[0.7, 0.06, 0.06]} />
          <meshStandardMaterial color={color} emissive={color} emissiveIntensity={0.5} transparent opacity={0.7} />
        </mesh>
      ))}
    </group>
  );
}
