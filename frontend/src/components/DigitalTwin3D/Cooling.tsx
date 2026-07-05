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

export default function Cooling({ color, pulseIntensity, hovered, onClick, onPointerOver, onPointerOut }: Props) {
  const meshRef = useRef<THREE.Mesh>(null);
  const fanRef  = useRef<THREE.Mesh>(null);

  useFrame((_state, delta) => {
    if (!meshRef.current) return;
    const mat = meshRef.current.material as THREE.MeshStandardMaterial;
    mat.emissiveIntensity = hovered ? 0.9 : pulseIntensity;
    if (fanRef.current) fanRef.current.rotation.z += delta * 2.5;
  });

  return (
    <group position={[0, 0.1, -1.9]}>
      {/* Radiator grid */}
      <mesh>
        <boxGeometry args={[1.6, 0.9, 0.12]} />
        <primitive object={makeSolidMaterial(color, hovered ? 0.35 : 0.18)} />
      </mesh>
      <mesh
        ref={meshRef}
        onClick={onClick}
        onPointerOver={onPointerOver}
        onPointerOut={onPointerOut}
      >
        <boxGeometry args={[1.6, 0.9, 0.12]} />
        <primitive object={makeWireframeMaterial(color)} />
      </mesh>
      {/* Horizontal fins */}
      {[-0.3, -0.1, 0.1, 0.3].map((y, i) => (
        <mesh key={i} position={[0, y, 0.08]}>
          <boxGeometry args={[1.5, 0.04, 0.04]} />
          <meshStandardMaterial color={color} emissive={color} emissiveIntensity={0.6} transparent opacity={0.6} />
        </mesh>
      ))}
      {/* Fan blade (spinning) */}
      <mesh ref={fanRef} position={[0, 0, 0.15]}>
        <torusGeometry args={[0.3, 0.04, 6, 4]} />
        <meshStandardMaterial color={color} emissive={color} emissiveIntensity={0.8} transparent opacity={0.8} />
      </mesh>
    </group>
  );
}
