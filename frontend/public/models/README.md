# 3D Vehicle Model

Place your downloaded GLB file here as:

    frontend/public/models/vehicle.glb

Vite serves everything in `public/` at the root URL, so the file will be
accessible at `/models/vehicle.glb` — exactly what `VehicleModel.tsx` expects.

## Where to download a free GLB

| Site | Search term |
|------|-------------|
| [Sketchfab](https://sketchfab.com/features/free-3d-models) | "low poly car" → filter Format: glTF |
| [Poly Pizza](https://poly.pizza) | "car" |
| [CGTrader](https://www.cgtrader.com/free-3d-models/car) | filter: Free, glTF/GLB |

## Requirements

- Format: `.glb` (binary glTF) — preferred, or `.gltf` + textures
- Size: under 20 MB
- Separate wheel meshes (named `Wheel_FL`, `Wheel_FR`, etc.) — optional but
  enables per-wheel rotation animation later

## What happens without the file

`Vehicle.tsx` wraps `VehicleModel` in a `<Suspense>` boundary.
If the GLB is missing, the scene automatically falls back to the procedural
blue-wireframe car — no errors, no blank screen.
