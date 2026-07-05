import * as THREE from "three";

// True holographic cyan — matches the spec (#00CFFF)
export const HOLO_CYAN = new THREE.Color("#00CFFF");

/**
 * Emissive wireframe — glows in bloom post-processing.
 * MeshStandardMaterial with emissive so bloom picks it up.
 */
export function makeBasicWireframe(color: THREE.Color = HOLO_CYAN, opacity = 0.85) {
  return new THREE.MeshStandardMaterial({
    color,
    emissive: color,
    emissiveIntensity: 1.8,
    wireframe: true,
    transparent: true,
    opacity,
    toneMapped: false,
  });
}

/**
 * Transparent solid fill — soft blue interior glow.
 */
export function makeBasicSolid(color: THREE.Color = HOLO_CYAN, opacity = 0.06) {
  return new THREE.MeshStandardMaterial({
    color,
    emissive: new THREE.Color("#003a5c"),
    emissiveIntensity: 0.6,
    transparent: true,
    opacity,
    side: THREE.FrontSide,
    depthWrite: false,
  });
}

/**
 * Edge glow layer — bright emissive, very thin wireframe for the outer rim glow.
 */
export function makeEdgeGlow(color: THREE.Color = HOLO_CYAN, opacity = 0.45) {
  return new THREE.MeshStandardMaterial({
    color,
    emissive: color,
    emissiveIntensity: 3.5,
    wireframe: true,
    transparent: true,
    opacity,
    toneMapped: false,
    depthWrite: false,
  });
}

// Health → holographic color
export function healthColor(health: number): THREE.Color {
  if (health >= 75) return new THREE.Color("#00ffcc");   // cyan-green: healthy
  if (health >= 45) return new THREE.Color("#f59e0b");   // amber: warning
  return new THREE.Color("#ef4444");                      // red: critical
}

// Base holographic blue for the car body
export const HOLO_BLUE   = new THREE.Color("#38bdf8");
export const HOLO_DIM    = new THREE.Color("#0f3460");
export const BACKGROUND  = "#05070A";

export function makeWireframeMaterial(color: THREE.Color, opacity = 0.85) {
  return new THREE.MeshStandardMaterial({
    color,
    emissive: color,
    emissiveIntensity: 0.45,
    wireframe: true,
    transparent: true,
    opacity,
  });
}

export function makeSolidMaterial(color: THREE.Color, opacity = 0.18) {
  return new THREE.MeshStandardMaterial({
    color,
    emissive: color,
    emissiveIntensity: 0.2,
    transparent: true,
    opacity,
    side: THREE.FrontSide,
  });
}
