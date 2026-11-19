import giaTimeline from "../../voiceover/gia/timeline.json";
import ccatTimeline from "../../voiceover/ccat/timeline.json";
import shlTimeline from "../../voiceover/shl/timeline.json";

export const FPS = 30;
export const LEAD = 8;   // frames before the voice starts
export const TAIL = 1.3; // seconds the end card holds after the last word

export const SCENE_KEYS = ["hook", "sections", "explain", "fulltest", "cta"] as const;
export type SceneKey = (typeof SCENE_KEYS)[number];

/** One continuous voiceover take and its word timings (scripts/generate-voiceover.py --short NAME). */
export type Timeline = { duration: number; starts: Record<string, number>; words: (string | number)[][] };

/** A word (or any of several spellings) to sync to; matched after the previous anchor. */
export type Anchor = string | string[];

export type ShortSection = { name: string; shots: string[]; anchor: Anchor };
export type ShortConfig = {
  id: string;
  voice: string;
  timeline: Timeline;
  testName: string;
  hook: { question: string; detail: string; detailAnchor: Anchor; punch: string; punchAnchor: Anchor; showDetail?: boolean };
  sections: ShortSection[];
  explainShot: string;
  explainTitle: string;
  fullTestShot: string;
  fullTestTitle: string;
  languages?: { label: string; shot: string; anchor: Anchor }[];
  ctaLine: string;
};

const GIA = "shots/gia/";
const CCAT = "shots/ccat/";
const SHL = "shots/shl/";

export const SHORTS: ShortConfig[] = [
  {
    id: "Short-ThomasGIA",
    voice: "gia",
    timeline: giaTimeline,
    testName: "Thomas GIA",
    hook: { question: "Thomas GIA test coming up?", detail: "Five timed sections.", detailAnchor: "five", punch: "Speed counts as much as accuracy.", punchAnchor: "speed" },
    sections: [
      { name: "Reasoning", shots: [`${GIA}reasoning-context`, `${GIA}reasoning-question`], anchor: "reasoning" },
      { name: "Perceptual speed", shots: [`${GIA}perceptual_speed-context`], anchor: ["perceptual", "deceptional", "speed"] },
      { name: "Number speed", shots: [`${GIA}number_speed_accuracy-question`], anchor: "number" },
      { name: "Word meaning", shots: [`${GIA}word_meaning-question`], anchor: "word" },
      { name: "Spatial", shots: [`${GIA}spatial_visualization-context`], anchor: "spatial" },
    ],
    explainShot: `${GIA}reasoning-answered`,
    explainTitle: "Every answer shows you why",
    fullTestShot: `${GIA}full-test-card`,
    fullTestTitle: "Full timed test",
    languages: [
      { label: "English", shot: `${GIA}reasoning-question`, anchor: "english" },
      { label: "Deutsch", shot: `${GIA}reasoning-question-de`, anchor: ["german", "deutsch"] },
      { label: "Español", shot: `${GIA}reasoning-question-es`, anchor: ["spanish", "espanol"] },
    ],
    ctaLine: "Thomas GIA practice",
  },
  {
    id: "Short-CCAT",
    voice: "ccat",
    timeline: ccatTimeline,
    testName: "CCAT",
    hook: { question: "CCAT invite in your inbox?", detail: "50 questions · 15 minutes", detailAnchor: ["50", "fifty"], punch: "Very few people finish.", punchAnchor: "very", showDetail: true },
    sections: [
      { name: "Math & numerical", shots: [`${CCAT}ccat_numerical-question`], anchor: ["maths", "math"] },
      { name: "Verbal reasoning", shots: [`${CCAT}ccat_verbal-question`], anchor: "verbal" },
      { name: "Spatial & abstract", shots: [`${CCAT}ccat_spatial-question`], anchor: "spatial" },
    ],
    explainShot: `${CCAT}ccat_numerical-answered`,
    explainTitle: "Learn the shortcut on every answer",
    fullTestShot: `${CCAT}full-test-card`,
    fullTestTitle: "50 questions. 15 minutes.",
    ctaLine: "CCAT practice",
  },
  {
    id: "Short-SHL",
    voice: "shl",
    timeline: shlTimeline,
    testName: "SHL-style",
    hook: { question: "SHL test coming up?", detail: "3 types of reasoning", detailAnchor: "three", punch: "The clock never stops.", punchAnchor: "clock", showDetail: true },
    sections: [
      { name: "Numerical", shots: [`${SHL}shl_numerical-question`], anchor: "numerical" },
      { name: "Deductive", shots: [`${SHL}shl_deductive-question`], anchor: "deductive" },
      { name: "Inductive", shots: [`${SHL}shl_inductive-question`], anchor: "inductive" },
    ],
    explainShot: `${SHL}shl_numerical-answered`,
    explainTitle: "A worked solution for every question",
    fullTestShot: `${SHL}full-test-card`,
    fullTestTitle: "24 questions. 36 minutes.",
    ctaLine: "SHL-style reasoning practice",
  },
];

const norm = (w: string) => w.toLowerCase().replace(/[^a-z0-9]/g, "");

/** Seconds into the voiceover when the anchor word is spoken (searching from `after`). */
export function wordTime(tl: Timeline, anchor: Anchor, after = 0): number {
  const alts = (Array.isArray(anchor) ? anchor : [anchor]).map(norm);
  const hit = tl.words.find((w) => (w[1] as number) >= after - 0.01 && alts.includes(norm(String(w[0]))));
  if (!hit) throw new Error(`Anchor ${JSON.stringify(anchor)} not found after ${after}s`);
  return hit[1] as number;
}

/** Frame where each scene starts, plus the total length. Scenes cut just before their first word. */
// The last section name is spoken right before the next line, so its card holds a little into it.
const CUT_DELAY: Partial<Record<SceneKey, number>> = { explain: 0.9 };

export function sceneLayout(cfg: ShortConfig) {
  const f = (s: number) => Math.round(s * FPS) + LEAD;
  const starts = SCENE_KEYS.map((k, i) => (i === 0 ? 0 : f(cfg.timeline.starts[k] + (CUT_DELAY[k] ?? 0)) - 6));
  const total = f(cfg.timeline.duration + TAIL);
  return SCENE_KEYS.map((key, i) => ({ key, from: starts[i], frames: (starts[i + 1] ?? total) - starts[i] }));
}

export const totalFrames = (cfg: ShortConfig) => {
  const layout = sceneLayout(cfg);
  const last = layout[layout.length - 1];
  return last.from + last.frames;
};

/** Convert a voiceover time to a frame inside the given scene. */
export function localFrame(cfg: ShortConfig, scene: SceneKey, seconds: number) {
  const layout = sceneLayout(cfg).find((s) => s.key === scene)!;
  return Math.round(seconds * FPS) + LEAD - layout.from;
}
