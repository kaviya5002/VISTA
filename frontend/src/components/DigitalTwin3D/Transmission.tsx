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

export default function Transmission({ color, pulseIntensity, hovered, onClick, onPointerOver, onPointerOut }: Props) {
  const meshRef = useRef<THREE.Mesh>(null);
  const gearRef = useRef<THREE.Mesh>(null);

  useFrame((_state, delta) => {
    if (!meshRef.current) return;
    const mat = meshRef.current.material as THREE.MeshStandardMaterial;
    mat.emissiveIntensity = hovered ? 0.9 : pulseIntensity;
    if (gearRef.current) gearRef.current.rotation.y += delta * 1.5;
  });

  return (
    <group position={[1.0, -0.2, 0.3]}>
      <mesh>
        <boxGeometry args={[0.65, 0.5, 0.65]} />
        <primitive object={makeSolidMaterial(color, hovered ? 0.35 : 0.18)} />
      </mesh>
      <mesh
        ref={meshRef}
        onClick={onClick}
        onPointerOver={onPointerOver}
        onPointerOut={onPointerOut}
      >
        <boxGeometry args={[0.65, 0.5, 0.65]} />
        <primitive object={makeWireframeMaterial(color)} />
      </mesh>
      {/* Gear disc */}
      <mesh ref={gearRef} position={[0, 0.35, 0]}>
        <torusGeometry args={[0.22, 0.05, 6, 8]} />
        <meshStandardMaterial color={color} emissive={color} emissiveIntensity={0.8} transparent opacity={0.8} />
      </mesh>
    </group>
  );
}
