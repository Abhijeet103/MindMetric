export type Crop = { at: number; x: number; y: number; w: number };
export type Shot = { src: string; from: number; crops: Crop[]; url?: string };
export type Callout = { text: string; from: number; to: number };
export type Scene = {
  id: string;
  kind: "hook" | "demo" | "cta";
  label: string;
  headline: string;
  url?: string;
  shots?: Shot[];
  callouts?: Callout[];
  from: number;
  durationInFrames: number;
  audio: { src: string; startFrame: number } | null;
};
export type Cue = { text: string; from: number; to: number; scene: string };

export type ShortProps = {
  fps: number;
  width: number;
  height: number;
  durationInFrames: number;
  topicId: string;
  scenes: Scene[];
  cues: Cue[];
  draft: boolean;
  disclosure: { text: string; tone: "neutral" | "amber" };
  cta: { url: string; lines: string[]; disclaimer: string };
  screenshotTag: string;
};
