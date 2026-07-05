/**
 * GlowEffects — minimal bloom + vignette only.
 * Reduced intensity for clean industrial look and 60fps performance.
 */
import { EffectComposer, Bloom, Vignette } from "@react-three/postprocessing";
import { BlendFunction } from "postprocessing";

interface Props {
  vehicleHealth?: number;
}

export default function GlowEffects({ vehicleHealth = 85 }: Props) {
  const intensity  = vehicleHealth < 30 ? 1.8 : vehicleHealth < 60 ? 1.4 : 1.1;
  const threshold  = 0.18;

  return (
    <EffectComposer multisampling={2}>
      <Bloom
        intensity={intensity}
        luminanceThreshold={threshold}
        luminanceSmoothing={0.85}
        mipmapBlur
        radius={0.55}
      />
      <Vignette
        offset={0.28}
        darkness={0.55}
        blendFunction={BlendFunction.NORMAL}
      />
    </EffectComposer>
  );
}
