/**
 * VehicleWireframe — holographic wireframe SUV for the Digital Twin center.
 *
 * Built entirely from Three.js primitives — no GLTF, no external assets.
 * Every part uses two mesh layers: transparent fill + emissive wireframe.
 * Only animation: slow emissive shimmer. No movement, no rotation.
 *
 * Car coordinate system (all units):
 *   Z-  = front (bonnet)   Z+ = rear (boot)
 *   X-  = left             X+ = right
 *   Y=0 = ground           Y+ = up
 *
 * Overall size: ~4.4 long × 2.0 wide × 1.7 tall  (fits inside component ring)
 */
import { useRef, useMemo } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";

// ── Palette ───────────────────────────────────────────────────────────────────

const CYAN       = new THREE.Color("#00CFFF");
const CYAN_DIM   = new THREE.Color("#003a5c");
const RED_TAIL   = new THREE.Color("#ff2222");
const WHITE_HEAD = new THREE.Color("#e0f8ff");

// ── Material factories ────────────────────────────────────────────────────────

function wire(opacity = 0.85): THREE.MeshStandardMaterial {
  return new THREE.MeshStandardMaterial({
    color:             CYAN,
    emissive:          CYAN,
    emissiveIntensity: 2.2,
    wireframe:         true,
    transparent:       true,
    opacity,
    toneMapped:        false,
    depthWrite:        false,
  });
}

function fill(opacity = 0.08): THREE.MeshStandardMaterial {
  return new THREE.MeshStandardMaterial({
    color:             CYAN_DIM,
    emissive:          CYAN_DIM,
    emissiveIntensity: 0.4,
    transparent:       true,
    opacity,
    side:              THREE.FrontSide,
    depthWrite:        false,
  });
}

function light(color: THREE.Color, intensity = 3.0, opacity = 0.95): THREE.MeshStandardMaterial {
  return new THREE.MeshStandardMaterial({
    color,
    emissive:          color,
    emissiveIntensity: intensity,
    transparent:       true,
    opacity,
    toneMapped:        false,
    depthWrite:        false,
  });
}

// ── Dual-layer mesh helper ────────────────────────────────────────────────────

interface PartProps {
  geo:      THREE.BufferGeometry;
  pos?:     [number, number, number];
  rot?:     [number, number, number];
  scale?:   [number, number, number];
  wOpacity?: number;
  fOpacity?: number;
  wireMats: React.MutableRefObject<THREE.MeshStandardMaterial[]>;
}

function Part({ geo, pos = [0,0,0], rot = [0,0,0], scale = [1,1,1], wOpacity = 0.85, fOpacity = 0.08, wireMats }: PartProps) {
  const wm = useMemo(() => wire(wOpacity), [wOpacity]);
  const fm = useMemo(() => fill(fOpacity), [fOpacity]);

  useMemo(() => { wireMats.current.push(wm); }, [wm, wireMats]);

  return (
    <group position={pos} rotation={rot} scale={scale}>
      <mesh geometry={geo}><primitive object={fm} attach="material" /></mesh>
      <mesh geometry={geo}><primitive object={wm} attach="material" /></mesh>
    </group>
  );
}

// ── Geometry builders ─────────────────────────────────────────────────────────

// Tapered box: bottom W/D, top W/D, height — approximates car body curves
function taperedBox(
  bw: number, bd: number,   // bottom width, depth
  tw: number, td: number,   // top width, depth
  h:  number,               // height
  ty: number = 0,           // top Y offset (taper forward/back)
): THREE.BufferGeometry {
  const hw = bw / 2, hd = bd / 2, thw = tw / 2, thd = td / 2;
  const y0 = 0, y1 = h;

  // 8 vertices: bottom 4, top 4
  const verts = new Float32Array([
    // bottom
    -hw,  y0, -hd,
     hw,  y0, -hd,
     hw,  y0,  hd,
    -hw,  y0,  hd,
    // top (narrower, possibly offset)
    -thw, y1, -thd + ty,
     thw, y1, -thd + ty,
     thw, y1,  thd + ty,
    -thw, y1,  thd + ty,
  ]);

  // 6 faces × 2 triangles each
  const idx = new Uint16Array([
    0,1,2, 0,2,3,       // bottom
    4,6,5, 4,7,6,       // top
    0,4,1, 1,4,5,       // front
    1,5,2, 2,5,6,       // right
    2,6,3, 3,6,7,       // back
    3,7,0, 0,7,4,       // left
  ]);

  const geo = new THREE.BufferGeometry();
  geo.setAttribute("position", new THREE.BufferAttribute(verts, 3));
  geo.setIndex(new THREE.BufferAttribute(idx, 1));
  geo.computeVertexNormals();
  return geo;
}

// Wheel arch cutout shape — flat torus segment
function wheelArch(rx: number, ry: number, thickness: number): THREE.BufferGeometry {
  return new THREE.TorusGeometry(rx, thickness, 6, 20, Math.PI);
}

// ── Main component ────────────────────────────────────────────────────────────

export default function VehicleWireframe() {
  const wireMats = useRef<THREE.MeshStandardMaterial[]>([]);

  // Slow emissive shimmer — only animation
  useFrame(({ clock }) => {
    const s = 2.0 + Math.sin(clock.elapsedTime * 0.65) * 0.35;
    for (const m of wireMats.current) m.emissiveIntensity = s;
  });

  // ── Pre-built geometries (memoized) ────────────────────────────────────────

  // Chassis sill — long flat base
  const gChassis = useMemo(() => new THREE.BoxGeometry(1.92, 0.14, 4.20), []);

  // Lower body — main slab with slight taper
  const gLowerBody = useMemo(() => taperedBox(1.96, 4.00, 1.88, 3.80, 0.52, 0), []);

  // Upper body — door belt line to window sill
  const gUpperBody = useMemo(() => taperedBox(1.90, 3.60, 1.80, 3.20, 0.38, 0), []);

  // Cabin — tapered toward front and rear, narrower
  const gCabin = useMemo(() => taperedBox(1.72, 2.10, 1.52, 1.70, 0.62, 0.05), []);

  // Bonnet — sloped flat panel
  const gBonnet = useMemo(() => taperedBox(1.82, 1.20, 1.60, 0.90, 0.10, -0.08), []);

  // Boot lid — flat panel
  const gBoot = useMemo(() => taperedBox(1.78, 0.80, 1.60, 0.60, 0.10, 0.06), []);

  // Front bumper — wide low bar
  const gFBumper = useMemo(() => taperedBox(1.96, 0.22, 1.88, 0.18, 0.36, 0), []);

  // Rear bumper
  const gRBumper = useMemo(() => taperedBox(1.96, 0.22, 1.88, 0.18, 0.32, 0), []);

  // A-pillar (windshield pillar) — thin bar
  const gAPillar = useMemo(() => new THREE.BoxGeometry(0.06, 0.72, 0.06), []);

  // C-pillar (rear pillar)
  const gCPillar = useMemo(() => new THREE.BoxGeometry(0.06, 0.58, 0.06), []);

  // Roof rail — thin strip along top edge
  const gRoofRail = useMemo(() => new THREE.BoxGeometry(0.05, 0.05, 2.10), []);

  // Side mirror — small box
  const gMirror = useMemo(() => new THREE.BoxGeometry(0.08, 0.12, 0.22), []);

  // Wheel — tyre torus
  const gTyre = useMemo(() => new THREE.TorusGeometry(0.38, 0.13, 10, 28), []);

  // Rim disc
  const gRimDisc = useMemo(() => new THREE.CylinderGeometry(0.28, 0.28, 0.06, 20), []);

  // Rim spoke
  const gSpoke = useMemo(() => new THREE.BoxGeometry(0.04, 0.50, 0.04), []);

  // Hub cap
  const gHub = useMemo(() => new THREE.CylinderGeometry(0.07, 0.07, 0.08, 12), []);

  // Wheel arch — half torus
  const gArch = useMemo(() => wheelArch(0.44, 0.44, 0.04), []);

  // Headlight lens
  const gHeadlight = useMemo(() => new THREE.BoxGeometry(0.42, 0.16, 0.06), []);

  // Headlight inner strip (DRL)
  const gDRL = useMemo(() => new THREE.BoxGeometry(0.36, 0.04, 0.04), []);

  // Taillight
  const gTaillight = useMemo(() => new THREE.BoxGeometry(0.44, 0.14, 0.06), []);

  // Grille bar
  const gGrille = useMemo(() => new THREE.BoxGeometry(1.20, 0.04, 0.04), []);

  // Door line crease — thin horizontal strip
  const gDoorCrease = useMemo(() => new THREE.BoxGeometry(0.04, 0.04, 3.20), []);

  // Windshield frame
  const gWindscreen = useMemo(() => taperedBox(1.68, 0.06, 1.48, 0.06, 0.60, 0), []);

  // Rear screen frame
  const gRearScreen = useMemo(() => taperedBox(1.60, 0.06, 1.42, 0.06, 0.52, 0), []);

  // ── Wheel positions: [x, z]  (y computed from wheel radius) ───────────────
  const WHEEL_Y   = 0.38;   // wheel center height
  const WHEEL_X   = 0.98;   // half-track
  const WHEEL_ZF  = -1.42;  // front axle Z
  const WHEEL_ZR  =  1.42;  // rear axle Z

  const wheelPositions: [number, number, number][] = [
    [-WHEEL_X, WHEEL_Y, WHEEL_ZF],  // front-left
    [ WHEEL_X, WHEEL_Y, WHEEL_ZF],  // front-right
    [-WHEEL_X, WHEEL_Y, WHEEL_ZR],  // rear-left
    [ WHEEL_X, WHEEL_Y, WHEEL_ZR],  // rear-right
  ];

  return (
    <group position={[0, 0, 0]}>

      {/* ── Chassis ─────────────────────────────────────────────────────── */}
      <Part geo={gChassis}   pos={[0, 0.07, 0]}          wireMats={wireMats} fOpacity={0.12} />

      {/* ── Lower body ──────────────────────────────────────────────────── */}
      <Part geo={gLowerBody} pos={[0, 0.21, 0]}          wireMats={wireMats} />

      {/* ── Upper body (door panels) ─────────────────────────────────────── */}
      <Part geo={gUpperBody} pos={[0, 0.73, 0]}          wireMats={wireMats} />

      {/* ── Cabin / greenhouse ──────────────────────────────────────────── */}
      <Part geo={gCabin}     pos={[0, 1.11, 0.08]}       wireMats={wireMats} fOpacity={0.06} />

      {/* ── Bonnet ──────────────────────────────────────────────────────── */}
      <Part geo={gBonnet}    pos={[0, 0.88, -1.62]}      wireMats={wireMats} fOpacity={0.10} />

      {/* ── Boot lid ────────────────────────────────────────────────────── */}
      <Part geo={gBoot}      pos={[0, 1.02, 1.68]}       wireMats={wireMats} fOpacity={0.10} />

      {/* ── Front bumper ────────────────────────────────────────────────── */}
      <Part geo={gFBumper}   pos={[0, 0.36, -2.20]}      wireMats={wireMats} wOpacity={0.70} />

      {/* ── Rear bumper ─────────────────────────────────────────────────── */}
      <Part geo={gRBumper}   pos={[0, 0.32, 2.20]}       wireMats={wireMats} wOpacity={0.70} />

      {/* ── Windshield frame ────────────────────────────────────────────── */}
      <Part geo={gWindscreen} pos={[0, 1.18, -0.72]}     wireMats={wireMats} wOpacity={0.50} fOpacity={0.04} />

      {/* ── Rear screen frame ───────────────────────────────────────────── */}
      <Part geo={gRearScreen} pos={[0, 1.14, 1.02]}      wireMats={wireMats} wOpacity={0.50} fOpacity={0.04} />

      {/* ── A-pillars (windshield pillars) ──────────────────────────────── */}
      {([-0.82, 0.82] as number[]).map((x, i) => (
        <Part key={`ap${i}`} geo={gAPillar}
          pos={[x, 1.22, -0.68]}
          rot={[0.38, 0, 0]}
          wireMats={wireMats} wOpacity={0.90} />
      ))}

      {/* ── C-pillars (rear pillars) ─────────────────────────────────────── */}
      {([-0.82, 0.82] as number[]).map((x, i) => (
        <Part key={`cp${i}`} geo={gCPillar}
          pos={[x, 1.20, 0.98]}
          rot={[-0.30, 0, 0]}
          wireMats={wireMats} wOpacity={0.90} />
      ))}

      {/* ── Roof rails ──────────────────────────────────────────────────── */}
      {([-0.84, 0.84] as number[]).map((x, i) => (
        <Part key={`rr${i}`} geo={gRoofRail}
          pos={[x, 1.73, 0.08]}
          wireMats={wireMats} wOpacity={0.80} />
      ))}

      {/* ── Door crease lines ───────────────────────────────────────────── */}
      {([-0.97, 0.97] as number[]).map((x, i) => (
        <Part key={`dc${i}`} geo={gDoorCrease}
          pos={[x, 0.82, 0]}
          wireMats={wireMats} wOpacity={0.60} />
      ))}

      {/* ── Side mirrors ────────────────────────────────────────────────── */}
      {([-1.02, 1.02] as number[]).map((x, i) => (
        <Part key={`sm${i}`} geo={gMirror}
          pos={[x, 1.18, -0.92]}
          wireMats={wireMats} wOpacity={0.75} />
      ))}

      {/* ── Grille bars ─────────────────────────────────────────────────── */}
      {[-0.10, -0.04, 0.02, 0.08].map((y, i) => (
        <Part key={`gr${i}`} geo={gGrille}
          pos={[0, 0.42 + y * 4, -2.22]}
          wireMats={wireMats} wOpacity={0.65} />
      ))}

      {/* ── Headlights ──────────────────────────────────────────────────── */}
      {([-0.66, 0.66] as number[]).map((x, i) => (
        <group key={`hl${i}`}>
          {/* Lens housing */}
          <mesh position={[x, 0.78, -2.20]}>
            <primitive object={gHeadlight} />
            <primitive object={light(WHITE_HEAD, 3.5, 0.92)} attach="material" />
          </mesh>
          {/* DRL strip */}
          <mesh position={[x, 0.72, -2.21]}>
            <primitive object={gDRL} />
            <primitive object={light(CYAN, 4.0, 0.95)} attach="material" />
          </mesh>
        </group>
      ))}

      {/* ── Taillights ──────────────────────────────────────────────────── */}
      {([-0.66, 0.66] as number[]).map((x, i) => (
        <mesh key={`tl${i}`} position={[x, 0.78, 2.20]}>
          <primitive object={gTaillight} />
          <primitive object={light(RED_TAIL, 3.0, 0.90)} attach="material" />
        </mesh>
      ))}

      {/* ── Wheel arches ────────────────────────────────────────────────── */}
      {wheelPositions.map(([x, y, z], i) => (
        <mesh
          key={`wa${i}`}
          position={[x, y + 0.10, z]}
          rotation={[0, 0, x < 0 ? Math.PI : 0]}
        >
          <primitive object={gArch} />
          <meshStandardMaterial
            color={CYAN} emissive={CYAN} emissiveIntensity={1.8}
            wireframe transparent opacity={0.55}
            toneMapped={false} depthWrite={false}
          />
        </mesh>
      ))}

      {/* ── Wheels ──────────────────────────────────────────────────────── */}
      {wheelPositions.map(([x, y, z], i) => {
        const wm1 = wire(0.88);
        const wm2 = wire(0.70);
        const wm3 = wire(0.95);
        wireMats.current.push(wm1, wm2, wm3);
        return (
          <group key={`wh${i}`} position={[x, y, z]} rotation={[0, 0, Math.PI / 2]}>
            {/* Tyre */}
            <mesh geometry={gTyre}>
              <primitive object={fill(0.12)} attach="material" />
            </mesh>
            <mesh geometry={gTyre}>
              <primitive object={wm1} attach="material" />
            </mesh>

            {/* Rim disc */}
            <mesh geometry={gRimDisc}>
              <primitive object={fill(0.10)} attach="material" />
            </mesh>
            <mesh geometry={gRimDisc}>
              <primitive object={wm2} attach="material" />
            </mesh>

            {/* 5 spokes */}
            {[0,1,2,3,4].map(s => (
              <mesh key={s} geometry={gSpoke} rotation={[0, (s / 5) * Math.PI * 2, 0]}>
                <primitive object={wm3} attach="material" />
              </mesh>
            ))}

            {/* Hub */}
            <mesh geometry={gHub}>
              <meshStandardMaterial
                color={CYAN} emissive={CYAN} emissiveIntensity={3.0}
                transparent opacity={0.95} toneMapped={false} depthWrite={false}
              />
            </mesh>
          </group>
        );
      })}

    </group>
  );
}
