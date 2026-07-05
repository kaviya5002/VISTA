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

export default function Electrical({ color, pulseIntensity, hovered, onClick, onPointerOver, onPointerOut }: Props) {
  const meshRef = useRef<THREE.Mesh>(null);

  useFrame(() => {
    if (!meshRef.current) return;
    const mat = meshRef.current.material as THREE.MeshStandardMaterial;
    mat.emissiveIntensity = hovered ? 0.9 : pulseIntensity;
  });

  return (
    <group position={[0, -0.3, 0]}>
      {/* Central ECU box */}
      <mesh>
        <boxGeometry args={[0.5, 0.2, 0.7]} />
        <primitive object={makeSolidMaterial(color, hovered ? 0.35 : 0.18)} />
      </mesh>
      <mesh
        ref={meshRef}
        onClick={onClick}
        onPointerOver={onPointerOver}
        onPointerOut={onPointerOut}
      >
        <boxGeometry args={[0.5, 0.2, 0.7]} />
        <primitive object={makeWireframeMaterial(color)} />
      </mesh>
      {/* Wiring tubes */}
      {([-0.8, 0, 0.8] as number[]).map((z, i) => (
        <mesh key={i} position={[0.3, 0, z]} rotation={[0, 0, Math.PI / 2]}>
          <cylinderGeometry args={[0.04, 0.04, 0.6, 6]} />
          <meshStandardMaterial color={color} emissive={color} emissiveIntensity={0.7} transparent opacity={0.7} />
        </mesh>
      ))}
    </group>
  );
}
