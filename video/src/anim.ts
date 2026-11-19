import { interpolate, spring } from "remotion";

export const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;

export function enter(frame: number, fps: number, at: number, cfg = { damping: 18, stiffness: 155 }) {
  const p = spring({ frame: frame - at, fps, config: cfg });
  return {
    opacity: interpolate(p, [0, 0.35], [0, 1], clamp),
    scale: interpolate(p, [0, 1], [0.94, 1]),
    y: interpolate(p, [0, 1], [24, 0]),
  };
}

/** Fade the whole scene in and out so cuts never pop. */
export function sceneFade(frame: number, total: number, inF = 12, outF = 14) {
  return interpolate(frame, [0, inF, total - outF, total], [0, 1, 1, 0], clamp);
}
