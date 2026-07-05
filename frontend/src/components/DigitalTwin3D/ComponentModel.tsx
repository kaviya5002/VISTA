/**
 * ComponentModel — fixed holographic component model.
 * No rotation. No bounce. Slow pulse glow. Scale on hover/select.
 */
import { useRef, useMemo, memo } from "react";
import { useFrame } from "@react-three/fiber";
import { Html } from "@react-three/drei";
import * as THREE from "three";
import type { ComponentDef } from "./ComponentRegistry";
import type { ComponentState } from "./useTwinAnimation";

// ── Material factories ────────────────────────────────────────────────────────

function makeWire(color: THREE.Color, opacity = 0.80) {
  return new THREE.MeshStandardMaterial({
    color, emissive: color, emissiveIntensity: 1.2,
    wireframe: true, transparent: true, opacity,
    toneMapped: false, depthWrite: false,
  });
}

function makeFill(color: THREE.Color, opacity = 0.06) {
  return new THREE.MeshStandardMaterial({
    color, emissive: new THREE.Color("#001a2e"), emissiveIntensity: 0.3,
    transparent: true, opacity, side: THREE.FrontSide, depthWrite: false,
  });
}

// ── Shapes ────────────────────────────────────────────────────────────────────

function BatteryShape({ color }: { color: THREE.Color }) {
  const w = useMemo(() => makeWire(color), [color]);
  const f = useMemo(() => makeFill(color), [color]);
  return (
    <group>
      <mesh><boxGeometry args={[0.85, 0.32, 0.50]} /><primitive object={f} /></mesh>
      <mesh><boxGeometry args={[0.85, 0.32, 0.50]} /><primitive object={w} /></mesh>
      {[-0.20, 0, 0.20].map((x, i) => (
        <mesh key={i} position={[x, 0, 0]}>
          <boxGeometry args={[0.018, 0.30, 0.48]} />
          <primitive object={makeWire(color, 0.40)} />
        </mesh>
      ))}
      {[-0.28, 0.28].map((x, i) => (
        <mesh key={i} position={[x, 0.20, 0]}>
          <cylinderGeometry args={[0.035, 0.035, 0.10, 8]} />
          <primitive object={makeWire(color, 0.90)} />
        </mesh>
      ))}
    </group>
  );
}

function MotorShape({ color }: { color: THREE.Color }) {
  const w = useMemo(() => makeWire(color), [color]);
  const f = useMemo(() => makeFill(color), [color]);
  return (
    <group>
      <mesh><cylinderGeometry args={[0.36, 0.36, 0.52, 20]} /><primitive object={f} /></mesh>
      <mesh><cylinderGeometry args={[0.36, 0.36, 0.52, 20]} /><primitive object={w} /></mesh>
      <mesh><cylinderGeometry args={[0.065, 0.065, 0.75, 10]} /><primitive object={makeWire(color, 0.90)} /></mesh>
      {[0,1,2,3,4,5].map(i => (
        <mesh key={i} rotation={[0, (i/6)*Math.PI*2, 0]}>
          <boxGeometry args={[0.035, 0.48, 0.38]} />
          <primitive object={makeWire(color, 0.30)} />
        </mesh>
      ))}
    </group>
  );
}

function BrakeShape({ color }: { color: THREE.Color }) {
  const w = useMemo(() => makeWire(color), [color]);
  const f = useMemo(() => makeFill(color), [color]);
  return (
    <group>
      <mesh rotation={[Math.PI/2,0,0]}><cylinderGeometry args={[0.40,0.40,0.055,28]} /><primitive object={f} /></mesh>
      <mesh rotation={[Math.PI/2,0,0]}><cylinderGeometry args={[0.40,0.40,0.055,28]} /><primitive object={w} /></mesh>
      <mesh rotation={[Math.PI/2,0,0]}><cylinderGeometry args={[0.11,0.11,0.09,14]} /><primitive object={makeWire(color,0.90)} /></mesh>
      {[0,1,2,3,4,5,6,7].map(i => {
        const a = (i/8)*Math.PI*2;
        return (
          <mesh key={i} position={[Math.cos(a)*0.25, 0, Math.sin(a)*0.25]} rotation={[Math.PI/2,(i/8)*Math.PI*2,0]}>
            <boxGeometry args={[0.035,0.07,0.035]} />
            <primitive object={makeWire(color,0.38)} />
          </mesh>
        );
      })}
      <mesh position={[0.36,0,0]}><boxGeometry args={[0.16,0.20,0.12]} /><primitive object={makeWire(color,0.60)} /></mesh>
    </group>
  );
}

function CoolingShape({ color }: { color: THREE.Color }) {
  const w = useMemo(() => makeWire(color), [color]);
  const f = useMemo(() => makeFill(color), [color]);
  return (
    <group>
      <mesh><boxGeometry args={[0.78,0.58,0.09]} /><primitive object={f} /></mesh>
      <mesh><boxGeometry args={[0.78,0.58,0.09]} /><primitive object={w} /></mesh>
      {[-0.20,-0.10,0,0.10,0.20].map((y,i) => (
        <mesh key={i} position={[0,y,0]}><boxGeometry args={[0.76,0.012,0.11]} /><primitive object={makeWire(color,0.38)} /></mesh>
      ))}
      {[-0.40,0.40].map((x,i) => (
        <mesh key={i} position={[x,0,0]}><boxGeometry args={[0.055,0.60,0.13]} /><primitive object={makeWire(color,0.78)} /></mesh>
      ))}
    </group>
  );
}

function TransmissionShape({ color }: { color: THREE.Color }) {
  const w = useMemo(() => makeWire(color), [color]);
  const f = useMemo(() => makeFill(color), [color]);
  return (
    <group>
      <mesh><boxGeometry args={[0.52,0.42,0.68]} /><primitive object={f} /></mesh>
      <mesh><boxGeometry args={[0.52,0.42,0.68]} /><primitive object={w} /></mesh>
      {[-0.13,0.13].map((x,i) => (
        <group key={i}>
          <mesh position={[x,0,0]}><cylinderGeometry args={[0.055,0.055,0.72,10]} /><primitive object={makeWire(color,0.85)} /></mesh>
          <mesh position={[x,0,0]} rotation={[Math.PI/2,0,0]}><torusGeometry args={[0.15,0.025,6,12]} /><primitive object={makeWire(color,0.50)} /></mesh>
        </group>
      ))}
    </group>
  );
}

function ElectricalShape({ color }: { color: THREE.Color }) {
  const w = useMemo(() => makeWire(color), [color]);
  const f = useMemo(() => makeFill(color), [color]);
  return (
    <group>
      <mesh><boxGeometry args={[0.68,0.075,0.52]} /><primitive object={f} /></mesh>
      <mesh><boxGeometry args={[0.68,0.075,0.52]} /><primitive object={w} /></mesh>
      {[[-0.17,0.055,-0.09],[0.09,0.055,0.07],[-0.04,0.055,0.14],[0.21,0.055,-0.14]].map(([x,y,z],i) => (
        <mesh key={i} position={[x,y,z]}><boxGeometry args={[0.09,0.035,0.09]} /><primitive object={makeWire(color,0.82)} /></mesh>
      ))}
      {[-0.26,0,0.26].map((x,i) => (
        <mesh key={i} position={[x,0,-0.28]}><boxGeometry args={[0.09,0.055,0.035]} /><primitive object={makeWire(color,0.88)} /></mesh>
      ))}
    </group>
  );
}

function ShapeFor({ id, color }: { id: string; color: THREE.Color }) {
  switch (id) {
    case "battery":      return <BatteryShape      color={color} />;
    case "motor":        return <MotorShape         color={color} />;
    case "brakes":       return <BrakeShape         color={color} />;
    case "cooling":      return <CoolingShape       color={color} />;
    case "transmission": return <TransmissionShape  color={color} />;
    case "electrical":   return <ElectricalShape    color={color} />;
    default:             return null;
  }
}

// ── Compact label ─────────────────────────────────────────────────────────────

function CompactLabel({ comp, color, name, icon }: {
  comp: ComponentState; color: THREE.Color; name: string; icon: string;
}) {
  const hex = "#" + color.getHexString();
  const hc  = comp.health >= 75 ? "#00e5a0" : comp.health >= 45 ? "#f59e0b" : "#ef4444";
  const status = comp.health >= 75 ? "Healthy" : comp.health >= 45 ? "Warning" : "Critical";
  return (
    <Html center distanceFactor={11} position={[0, 0.78, 0]} zIndexRange={[5, 0]}>
      <div style={{
        background: "rgba(2,4,10,0.88)",
        border: `1px solid ${hex}50`,
        borderRadius: 5,
        padding: "4px 9px",
        fontFamily: "monospace",
        fontSize: 9,
        textAlign: "center",
        whiteSpace: "nowrap",
        pointerEvents: "none",
        lineHeight: 1.5,
        minWidth: 72,
      }}>
        <div style={{ color: hex, fontWeight: 800, fontSize: 9, letterSpacing: 0.5 }}>
          {icon} {name.toUpperCase()}
        </div>
        <div style={{ color: hc, fontWeight: 900, fontSize: 12 }}>{comp.health}%</div>
        <div style={{ color: hc, fontSize: 8, opacity: 0.85 }}>{status}</div>
      </div>
    </Html>
  );
}

// ── Main export ───────────────────────────────────────────────────────────────

interface Props {
  def:      ComponentDef;
  comp:     ComponentState;
  color:    THREE.Color;
  hovered:  boolean;
  selected: boolean;
  onHover:  (name: string | null) => void;
  onClick:  (name: string) => void;
}

const ComponentModel = memo(function ComponentModel({
  def, comp, color, hovered, selected, onHover, onClick,
}: Props) {
  const groupRef   = useRef<THREE.Group>(null);
  const wireMats   = useRef<THREE.MeshStandardMaterial[]>([]);

  function collectMats(g: THREE.Group | null) {
    if (!g) return;
    wireMats.current = [];
    g.traverse(obj => {
      if (obj instanceof THREE.Mesh) {
        const mats = Array.isArray(obj.material) ? obj.material : [obj.material];
        for (const m of mats) {
          if (m instanceof THREE.MeshStandardMaterial && m.wireframe) wireMats.current.push(m);
        }
      }
    });
  }

  useFrame(({ clock }) => {
    const t = clock.elapsedTime;

    // Smooth scale toward target — no bounce
    if (groupRef.current) {
      const target = selected ? 1.18 : hovered ? 1.10 : 1.0;
      const cur = groupRef.current.scale.x;
      groupRef.current.scale.setScalar(cur + (target - cur) * 0.08);
    }

    // Slow emissive pulse only
    const base   = selected ? 2.2 : hovered ? 1.8 : 1.1;
    const pulse  = base + Math.sin(t * 0.8) * 0.25;
    for (const m of wireMats.current) m.emissiveIntensity = pulse;
  });

  return (
    <group
      ref={groupRef}
      position={def.modelPosition}
      onPointerOver={e => { e.stopPropagation(); onHover(def.name); document.body.style.cursor = "pointer"; }}
      onPointerOut={e  => { e.stopPropagation(); onHover(null);     document.body.style.cursor = "default"; }}
      onClick={e        => { e.stopPropagation(); onClick(def.name); }}
    >
      <group ref={r => collectMats(r)}>
        <ShapeFor id={def.id} color={color} />
      </group>
      <CompactLabel comp={comp} color={color} name={def.name} icon={def.icon} />
    </group>
  );
});

export default ComponentModel;
