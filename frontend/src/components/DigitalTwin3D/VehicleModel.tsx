/**
 * VehicleModel — holographic wireframe car centered at world origin.
 * Two material layers per mesh: transparent fill + bright emissive wireframe.
 * Only animation: slow emissive shimmer.
 */
import { useMemo, useRef } from "react";
import { useGLTF } from "@react-three/drei";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";

const MODEL_PATH = "/models/sport_utility_vehicle/scene.gltf";

const HOLO_CYAN  = new THREE.Color("#00CFFF");
const FILL_COLOR = new THREE.Color("#001a2e");

function makeSolid(): THREE.MeshStandardMaterial {
  return new THREE.MeshStandardMaterial({
    color: FILL_COLOR,
    emissive: FILL_COLOR,
    emissiveIntensity: 0.3,
    transparent: true,
    opacity: 0.10,
    side: THREE.FrontSide,
    depthWrite: false,
  });
}

function makeWire(): THREE.MeshStandardMaterial {
  return new THREE.MeshStandardMaterial({
    color: HOLO_CYAN,
    emissive: HOLO_CYAN,
    emissiveIntensity: 2.0,
    wireframe: true,
    transparent: true,
    opacity: 0.90,
    toneMapped: false,
    depthWrite: false,
  });
}

export default function VehicleModel() {
  const { scene } = useGLTF(MODEL_PATH);
  const wireRefs  = useRef<THREE.MeshStandardMaterial[]>([]);

  // Build a centered, scaled group from the GLTF scene — memoized so it only
  // runs once per scene load, not every render.
  const centeredGroup = useMemo(() => {
    // Deep-clone so we never mutate the cached GLTF asset
    const root = scene.clone(true);

    // ── 1. Scale to target size ──────────────────────────────────────────────
    // Measure raw bounding box first
    const rawBox  = new THREE.Box3().setFromObject(root);
    const rawSize = new THREE.Vector3();
    rawBox.getSize(rawSize);
    // Scale so the longest horizontal dimension = 4.5 units
    const scale = 4.5 / Math.max(rawSize.x, rawSize.z, 0.001);
    root.scale.setScalar(scale);

    // ── 2. Center at world origin ────────────────────────────────────────────
    // Re-measure after scaling
    const box    = new THREE.Box3().setFromObject(root);
    const center = new THREE.Vector3();
    box.getCenter(center);
    // Shift so XZ center = 0,0 and bottom of car sits on Y=0
    root.position.set(
      root.position.x - center.x,
      root.position.y - box.min.y,
      root.position.z - center.z,
    );

    // ── 3. Apply holographic materials ───────────────────────────────────────
    wireRefs.current = [];
    root.traverse((obj) => {
      if (!(obj instanceof THREE.Mesh)) return;
      obj.castShadow    = false;
      obj.receiveShadow = false;
      const solid = makeSolid();
      const wire  = makeWire();
      obj.material = [solid, wire];
      wireRefs.current.push(wire);
    });

    return root;
  }, [scene]);

  // Slow emissive shimmer — no position or rotation changes
  useFrame(({ clock }) => {
    const shimmer = 1.8 + Math.sin(clock.elapsedTime * 0.7) * 0.3;
    for (const m of wireRefs.current) m.emissiveIntensity = shimmer;
  });

  return <primitive object={centeredGroup} />;
}

useGLTF.preload(MODEL_PATH);
