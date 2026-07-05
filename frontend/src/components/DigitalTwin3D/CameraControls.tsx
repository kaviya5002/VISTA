/**
 * CameraControls — OrbitControls configured for a digital twin viewer.
 *
 * - Rotate, zoom, pan enabled
 * - minDistance prevents going inside the model
 * - maxPolarAngle prevents going below the grid
 */
import { OrbitControls } from "@react-three/drei";

interface Props {
  /** Disable pan (e.g. when a camera mode is active) */
  disablePan?: boolean;
}

export default function CameraControls({ disablePan = false }: Props) {
  return (
    <OrbitControls
      enablePan={!disablePan}
      enableDamping
      dampingFactor={0.06}
      minDistance={3}
      maxDistance={16}
      minPolarAngle={0.1}
      maxPolarAngle={Math.PI / 2}
      rotateSpeed={0.7}
      zoomSpeed={0.9}
    />
  );
}
