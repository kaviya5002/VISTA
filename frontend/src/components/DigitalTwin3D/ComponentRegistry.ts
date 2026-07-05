/**
 * ComponentRegistry — single source of truth for the Digital Twin.
 *
 * Every position is calibrated to the scaled GLTF model:
 *   - Model scaled to ~4 units long (Z axis), ~2.4 units wide (X axis)
 *   - Grid sits at Y = -0.9
 *   - Car roof is at approximately Y = 1.8
 *
 * Hotspot positions are placed at the real-world location of each
 * system inside a Tata SUV body shell.
 */

import * as THREE from "three";
import type { CameraMode } from "./useTwinAnimation";

export interface ComponentDef {
  id:          string;                        // matches TwinData key (lowercase)
  name:        string;                        // display name
  icon:        string;
  /** Centre of the invisible clickable hotspot */
  hotspot:     [number, number, number];
  /** Where the floating label HTML anchor sits */
  labelOffset: [number, number, number];
  /** Where the popup panel HTML anchor sits */
  popupOffset: [number, number, number];
  /** Camera mode to activate on click */
  cameraMode:  CameraMode;
  /** World position of the orbiting 3D component model */
  modelPosition: [number, number, number];
}

// Car dimensions after scaling: ~4.5 long (Z), ~2.4 wide (X), ~1.8 tall (Y)
// Front = negative Z, Rear = positive Z, Left = negative X, Right = positive X
// Hotspots sit ON the car body. Component models orbit at radius ~3 units.
export const REGISTRY: ComponentDef[] = [
  {
    id:            "battery",
    name:          "Battery",
    icon:          "🔋",
    hotspot:       [ 0.0,  0.25,  1.60],  // under rear floor
    labelOffset:   [-2.5,  1.2,   1.60],
    popupOffset:   [-2.8,  1.5,   1.60],
    cameraMode:    "battery",
    modelPosition: [-3.0,  1.0,   1.80],  // left-rear
  },
  {
    id:            "motor",
    name:          "Motor",
    icon:          "⚙️",
    hotspot:       [ 0.0,  0.55, -1.80],  // engine bay front
    labelOffset:   [ 2.5,  1.2,  -1.80],
    popupOffset:   [ 2.8,  1.5,  -1.80],
    cameraMode:    "motor",
    modelPosition: [ 0.0,  1.0,  -3.20],  // front-center
  },
  {
    id:            "cooling",
    name:          "Cooling",
    icon:          "❄️",
    hotspot:       [ 0.0,  0.80, -2.10],  // radiator grille
    labelOffset:   [-2.5,  1.5,  -2.10],
    popupOffset:   [-2.8,  1.8,  -2.10],
    cameraMode:    "cooling",
    modelPosition: [-3.0,  1.0,  -1.80],  // left-front
  },
  {
    id:            "brakes",
    name:          "Brakes",
    icon:          "🛑",
    hotspot:       [-1.05, 0.40,  1.35],  // rear-left wheel hub
    labelOffset:   [-2.5,  1.0,   1.35],
    popupOffset:   [-2.8,  1.3,   1.35],
    cameraMode:    "brakes",
    modelPosition: [ 3.0,  1.0,   1.80],  // right-rear
  },
  {
    id:            "electrical",
    name:          "Electrical",
    icon:          "⚡",
    hotspot:       [ 0.0,  1.20,  0.20],  // cabin center / fuse box
    labelOffset:   [ 2.5,  1.6,   0.20],
    popupOffset:   [ 2.8,  1.9,   0.20],
    cameraMode:    "overview",
    modelPosition: [ 0.0,  1.0,   3.20],  // rear-center
  },
  {
    id:            "transmission",
    name:          "Transmission",
    icon:          "🔧",
    hotspot:       [ 0.0,  0.30, -0.40],  // gearbox tunnel center
    labelOffset:   [ 2.5,  1.0,  -0.40],
    popupOffset:   [ 2.8,  1.3,  -0.40],
    cameraMode:    "motor",
    modelPosition: [ 3.0,  1.0,  -1.80],  // right-front
  },
];

/** Lookup by id */
export const REGISTRY_MAP = Object.fromEntries(REGISTRY.map(c => [c.id, c]));

/** Failure propagation chain — order matters */
export const FAILURE_CHAIN = [
  "Battery", "Electrical", "Motor", "Cooling", "Transmission", "Brakes",
];

/** Hotspot positions as THREE.Vector3 — used by FailureAnimation */
export const HOTSPOT_VECTORS: Record<string, THREE.Vector3> = Object.fromEntries(
  REGISTRY.map(c => [c.name, new THREE.Vector3(...c.hotspot)])
);

/**
 * GLTF node names for the 4 wheel assemblies.
 * These are the *parent* nodes that contain both tyre + rim meshes,
 * so rotating them spins the whole wheel.
 */
export const WHEEL_NODES = [
  "Cylinder_2",       // Front-Left
  "Cylinder.001_3",   // Front-Right
  "Cylinder.004_9",   // Rear-Left
  "Cylinder.005_11",  // Rear-Right
];
