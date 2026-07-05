/**
 * WheelAnimator — spins the 4 wheel assemblies in the loaded GLTF scene.
 *
 * The wheel parent nodes (Cylinder_2, Cylinder.001_3, etc.) are separate
 * objects in the scene graph, so we can rotate them independently.
 * We find them by name after the model mounts, then drive rotation in useFrame.
 */
import { useEffect, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";
import { WHEEL_NODES } from "./ComponentRegistry";

interface Props {
  /** The root THREE.Group that contains the cloned GLTF scene */
  root: THREE.Group | null;
}

const WHEEL_SPEED = 1.2; // radians/sec at normal speed

export default function WheelAnimator({ root }: Props) {
  const wheels = useRef<THREE.Object3D[]>([]);

  useEffect(() => {
    if (!root) return;
    wheels.current = [];
    root.traverse((obj) => {
      if (WHEEL_NODES.includes(obj.name)) {
        wheels.current.push(obj);
      }
    });
  }, [root]);

  useFrame((_, delta) => {
    wheels.current.forEach(w => {
      // Wheels rotate around their local X axis (forward roll)
      w.rotation.x += WHEEL_SPEED * delta;
    });
  });

  return null;
}
