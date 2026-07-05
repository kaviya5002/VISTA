/**
 * ScanLine — premium holographic diagnostic sweep
 *
 * Four layers:
 *   1. Main scan plane  — wide translucent sweep
 *   2. Leading edge     — bright thin line at the scan front
 *   3. Secondary sweep  — offset by half period, dimmer
 *   4. Horizontal bands — static faint horizontal stripes (CRT feel)
 */
import { useRef, useMemo } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";

const SCAN_BOTTOM = -0.05;
const SCAN_TOP    =  2.6;
const PERIOD      =  2.4;

function HorizontalBands() {
  const meshes = useMemo(() => {
    const out: { y: number; opacity: number }[] = [];
    for (let i = 0; i < 8; i++) {
      out.push({ y: SCAN_BOTTOM + (i / 7) * (SCAN_TOP - SCAN_BOTTOM), opacity: 0.012 + (i % 2) * 0.008 });
    }
    return out;
  }, []);

  return (
    <>
      {meshes.map((m, i) => (
        <mesh key={i} position={[0, m.y, 0]} rotation={[-Math.PI / 2, 0, 0]}>
          <planeGeometry args={[7, 0.02]} />
          <meshBasicMaterial
            color="#00CFFF"
            transparent
            opacity={m.opacity}
            side={THREE.DoubleSide}
            depthWrite={false}
          />
        </mesh>
      ))}
    </>
  );
}

export default function ScanLine() {
  const planeRef  = useRef<THREE.Mesh>(null);
  const edgeRef   = useRef<THREE.Mesh>(null);
  const plane2Ref = useRef<THREE.Mesh>(null);
  const trailRef  = useRef<THREE.Mesh>(null);
  const planeMat  = useRef<THREE.MeshBasicMaterial>(null);
  const edgeMat   = useRef<THREE.MeshBasicMaterial>(null);
  const plane2Mat = useRef<THREE.MeshBasicMaterial>(null);
  const trailMat  = useRef<THREE.MeshBasicMaterial>(null);

  useFrame(({ clock }) => {
    const t  = (clock.elapsedTime % PERIOD) / PERIOD;
    const t2 = ((clock.elapsedTime + PERIOD * 0.5) % PERIOD) / PERIOD;

    const ping  = t  < 0.5 ? t  * 2 : (1 - t)  * 2;
    const ping2 = t2 < 0.5 ? t2 * 2 : (1 - t2) * 2;

    const y  = SCAN_BOTTOM + ping  * (SCAN_TOP - SCAN_BOTTOM);
    const y2 = SCAN_BOTTOM + ping2 * (SCAN_TOP - SCAN_BOTTOM);

    if (planeRef.current)  planeRef.current.position.y  = y;
    if (edgeRef.current)   edgeRef.current.position.y   = y + 0.02;
    if (trailRef.current)  trailRef.current.position.y  = y - 0.12;
    if (plane2Ref.current) plane2Ref.current.position.y = y2;

    if (planeMat.current)  planeMat.current.opacity  = 0.06 + ping  * 0.10;
    if (edgeMat.current)   edgeMat.current.opacity   = 0.80 + ping  * 0.18;
    if (trailMat.current)  trailMat.current.opacity  = 0.05 + ping  * 0.08;
    if (plane2Mat.current) plane2Mat.current.opacity = 0.02 + ping2 * 0.04;
  });

  return (
    <group>
      {/* Main scan plane */}
      <mesh ref={planeRef} rotation={[-Math.PI / 2, 0, 0]}>
        <planeGeometry args={[7, 7]} />
        <meshBasicMaterial ref={planeMat} color="#00CFFF" transparent opacity={0.08}
          side={THREE.DoubleSide} depthWrite={false} />
      </mesh>

      {/* Leading edge — bright thin strip */}
      <mesh ref={edgeRef} rotation={[-Math.PI / 2, 0, 0]}>
        <planeGeometry args={[7, 0.03]} />
        <meshBasicMaterial ref={edgeMat} color="#00CFFF" transparent opacity={0.75}
          side={THREE.DoubleSide} depthWrite={false} />
      </mesh>

      {/* Trailing glow */}
      <mesh ref={trailRef} rotation={[-Math.PI / 2, 0, 0]}>
        <planeGeometry args={[7, 0.22]} />
        <meshBasicMaterial ref={trailMat} color="#38bdf8" transparent opacity={0.05}
          side={THREE.DoubleSide} depthWrite={false} />
      </mesh>

      {/* Secondary sweep — dimmer, offset */}
      <mesh ref={plane2Ref} rotation={[-Math.PI / 2, 0, 0]}>
        <planeGeometry args={[7, 7]} />
        <meshBasicMaterial ref={plane2Mat} color="#38bdf8" transparent opacity={0.03}
          side={THREE.DoubleSide} depthWrite={false} />
      </mesh>

      <HorizontalBands />
    </group>
  );
}
