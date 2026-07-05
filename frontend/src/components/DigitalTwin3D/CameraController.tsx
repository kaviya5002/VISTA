import { useRef, useEffect } from "react";
import { useThree, useFrame } from "@react-three/fiber";
import * as THREE from "three";
import { CAMERA_POSITIONS, CAMERA_TARGETS } from "./useTwinAnimation";
import type { CameraMode } from "./useTwinAnimation";

interface Props {
  mode:          CameraMode;
  criticalCount?: number;   // number of critical components → drives shake amplitude
}

const ORBIT_RADIUS = 7;
const ORBIT_HEIGHT = 3.5;
const ORBIT_SPEED  = 0.08; // radians/sec — slow cinematic orbit

export default function CameraController({ mode, criticalCount = 0 }: Props) {
  const { camera } = useThree();
  const targetPos     = useRef(new THREE.Vector3(...CAMERA_POSITIONS[mode]));
  const targetLookAt  = useRef(new THREE.Vector3(...CAMERA_TARGETS[mode]));
  const currentLookAt = useRef(new THREE.Vector3(0, 0, 0));
  const orbitAngle    = useRef(0);

  useEffect(() => {
    targetPos.current.set(...CAMERA_POSITIONS[mode]);
    targetLookAt.current.set(...CAMERA_TARGETS[mode]);
  }, [mode]);

  useFrame((_, delta) => {
    const isOrbit = mode === "overview" || mode === "auto";

    if (isOrbit) {
      orbitAngle.current += ORBIT_SPEED * delta;
      targetPos.current.set(
        Math.sin(orbitAngle.current) * ORBIT_RADIUS,
        ORBIT_HEIGHT,
        Math.cos(orbitAngle.current) * ORBIT_RADIUS,
      );
      targetLookAt.current.set(0, 0.5, 0);
    }

    camera.position.lerp(targetPos.current, 0.04);
    currentLookAt.current.lerp(targetLookAt.current, 0.04);
    camera.lookAt(currentLookAt.current);

    // No camera shake — removed for stability
  });

  return null;
}
