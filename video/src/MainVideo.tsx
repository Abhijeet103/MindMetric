import React from "react";
import { AbsoluteFill, Audio, Sequence, staticFile } from "remotion";
import { COLORS, ORDER, SceneKey, VO_LEAD, sceneFrames } from "./constants";
import { sceneFade } from "./anim";
import { useCurrentFrame, useVideoConfig } from "remotion";
import { Hook } from "./scenes/Hook";
import { Contrast } from "./scenes/Contrast";
import { Pitch } from "./scenes/Pitch";
import { Close } from "./scenes/Close";
import { BrowserShots } from "./scenes/Common";

// Scene lengths follow the generated voiceover (voiceover/durations.json); see constants.ts.
const SHOTS: Partial<Record<SceneKey, React.FC>> = {
  home: () => (
    <BrowserShots url="mindmetric.store" label="Start in seconds" title="Find the test in your invite"
      shots={[{ src: "home-hero", from: 0, zoom: [1.0, 1.12] }]}
      callouts={[
        { text: "Search by test or company", at: 60, x: 250, y: 560 },
        { text: "Try a question instantly", sub: "No sign-up needed", at: 130, x: 1320, y: 690 },
      ]} />
  ),
  tracks: () => (
    <BrowserShots url="mindmetric.store/practice" label="Six practice tracks" title="Choose the test in your application"
      shots={[{ src: "practice", from: 0, to: 150, zoom: [1, 1.04] }, { src: "practice-2", from: 150, zoom: [1, 1.04] }]}
      callouts={[
        { text: "Thomas GIA · CCAT", at: 40, until: 150, x: 1330, y: 420 },
        { text: "SHL · Watson-Glaser · Consulting", at: 170, x: 1270, y: 420 },
      ]} />
  ),
  question: () => (
    <BrowserShots url="mindmetric.store/practice/prepgia/modules/reasoning" label="Practice mode" title="Answer, then see why"
      shots={[{ src: "reasoning-question", from: 0, to: 95, zoom: [1.0, 1.04] }, { src: "reasoning-answered", from: 95, zoom: [1.04, 1.1] }]}
      callouts={[{ text: "Instant feedback", sub: "With a worked explanation", at: 115, x: 1420, y: 290 }]} />
  ),
  spatial: () => (
    <BrowserShots url="mindmetric.store/practice/prepgia/modules/spatial_visualization" label="Real formats" title="Every section, the way it's tested"
      shots={[{ src: "spatial-context", from: 0, zoom: [1.05, 1.16] }]}
      callouts={[{ text: "Rotated or mirrored?", at: 50, x: 260, y: 560 }]} />
  ),
  case: () => (
    <BrowserShots url="mindmetric.store/practice/consulting_cases" label="Consulting" title="Linked business cases with real exhibits"
      shots={[{ src: "case-answered", from: 0, zoom: [1.0, 1.06], pan: [0, 40] }]}
      callouts={[
        { text: "Charts and tables", sub: "Shared across four linked questions", at: 50, x: 230, y: 380 },
        { text: "The maths, explained", at: 150, x: 1330, y: 760 },
      ]} />
  ),
  language: () => (
    <BrowserShots url="mindmetric.store/practice/prepgia?lang=de" label="New" title="Thomas GIA in German and Spanish"
      shots={[{ src: "gia-de", from: 0, zoom: [1.0, 1.1] }]}
      callouts={[{ text: "Deutsch · Español", sub: "Beta", at: 40, x: 1330, y: 330 }]} />
  ),
  testmode: () => (
    <BrowserShots url="mindmetric.store/practice/prepgia" label="Test mode" title="Fullscreen, timed, scored by section"
      shots={[{ src: "gia", from: 0, zoom: [1.0, 1.1] }]}
      callouts={[
        { text: "Full timed test", sub: "Every section, back to back", at: 60, x: 1310, y: 600 },
      ]} />
  ),
};

const SCENES: Record<SceneKey, React.FC> = { hook: Hook, contrast: Contrast, pitch: Pitch, close: Close, ...SHOTS } as Record<SceneKey, React.FC>;

const Faded: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  return <AbsoluteFill style={{ opacity: sceneFade(frame, durationInFrames) }}>{children}</AbsoluteFill>;
};

export const MainVideo: React.FC = () => {
  let from = 0;
  return (
    <AbsoluteFill style={{ background: COLORS.bg }}>
      {ORDER.map((key) => {
        const dur = sceneFrames(key);
        const start = from;
        from += dur;
        const Scene = SCENES[key];
        return (
          <Sequence key={key} from={start} durationInFrames={dur} name={key}>
            <Faded><Scene /></Faded>
            <Sequence from={VO_LEAD}><Audio src={staticFile(`${key}.mp3`)} /></Sequence>
          </Sequence>
        );
      })}
    </AbsoluteFill>
  );
};
