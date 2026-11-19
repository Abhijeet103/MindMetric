import durations from "../voiceover/durations.json";

export const COLORS = {
  bg: "#08100d",
  bgCard: "#0f1a16",
  accent: "#3ecfa8",
  accentDim: "#0f5c4c",
  accentBright: "#7ee8c8",
  white: "#f4f7f5",
  offWhite: "#c9d4cf",
  muted: "#7c8a84",
  border: "#1f2e28",
  red: "#ef4444",
  amber: "#f2a33a",
};

export const FPS = 30;
export const W = 1920;
export const H = 1080;

/** Voiceover starts this many frames into each scene. */
export const VO_LEAD = 12;

export type SceneKey = keyof typeof durations;
const TAIL: Partial<Record<SceneKey, number>> = { close: 60, hook: 20, pitch: 15 };

export const sceneFrames = (key: SceneKey) =>
  Math.ceil(durations[key] * FPS) + VO_LEAD + (TAIL[key] ?? 24);

export const ORDER: SceneKey[] = [
  "hook", "contrast", "pitch", "home", "tracks", "question", "spatial", "case", "language", "testmode", "close",
];

export const TOTAL_FRAMES = ORDER.reduce((sum, k) => sum + sceneFrames(k), 0);
