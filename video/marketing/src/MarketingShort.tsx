import React from "react";
import { AbsoluteFill, Audio, Img, Sequence, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import layout from "../layout.json";
// Reuse the existing font loading (read-only import; MainVideo is untouched).
import { INTER, MONO } from "../../src/fonts";
import { Callout, Crop, Cue, Scene, Shot, ShortProps } from "./types";

const C = {
  bg: "#08100d",
  card: "#0f1a16",
  accent: "#3ecfa8",
  accentBright: "#7ee8c8",
  white: "#f4f7f5",
  offWhite: "#c9d4cf",
  muted: "#9aa8a2",
  border: "#1f2e28",
  amber: "#f2a33a",
};
const B = layout.boxes;
const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;
const box = (b: { x: number; y: number; w: number; h: number }): React.CSSProperties => ({
  position: "absolute", left: b.x, top: b.y, width: b.w, height: b.h,
});

function useEnter(at: number, cfg = { damping: 18, stiffness: 160 }) {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const p = spring({ frame: frame - at, fps, config: cfg });
  return { opacity: interpolate(p, [0, 0.35], [0, 1], clamp), scale: interpolate(p, [0, 1], [0.94, 1]), y: interpolate(p, [0, 1], [20, 0]) };
}

const IMG_W = B.card.w;
const IMG_H = B.card.h - B.card.urlBarHeight;

function cropAt(crops: Crop[], t: number): Crop {
  if (crops.length === 1) return crops[0];
  const ats = crops.map((c) => c.at);
  const pick = (k: "x" | "y" | "w") => interpolate(t, ats, crops.map((c) => c[k]), clamp);
  return { at: t, x: pick("x"), y: pick("y"), w: pick("w") };
}

const ShotView: React.FC<{ shot: Shot; t: number; opacity: number }> = ({ shot, t, opacity }) => {
  const c = cropAt(shot.crops, t);
  const scale = IMG_W / c.w;
  return (
    <Img
      src={staticFile(`shots/${shot.src}`)}
      style={{
        position: "absolute", left: -c.x * scale, top: -c.y * scale, opacity,
        width: layout.screenshot.sourceWidth * scale, height: layout.screenshot.sourceHeight * scale, maxWidth: "none",
      }}
    />
  );
};

const Header: React.FC<{ scene: Scene; tag: string; immediate?: boolean }> = ({ scene, tag, immediate }) => {
  const e = useEnter(immediate ? -6 : 2);
  return (
    <div style={{ ...box(B.header), display: "flex", flexDirection: "column", justifyContent: "flex-end", opacity: e.opacity, transform: `translateY(${e.y}px)` }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 20 }}>
        <div style={{ fontFamily: MONO, fontSize: B.header.labelFontSize, letterSpacing: 3, textTransform: "uppercase", color: C.accent, fontWeight: 600, whiteSpace: "nowrap" }}>
          {scene.label}
        </div>
        <div style={{ fontFamily: INTER, fontSize: B.header.tagFontSize, fontWeight: 600, color: C.offWhite, border: `2px solid ${C.border}`, background: "rgba(255,255,255,0.06)", padding: "4px 14px", borderRadius: 10, whiteSpace: "nowrap" }}>
          {tag}
        </div>
      </div>
      <div style={{ fontFamily: INTER, fontSize: B.header.fontSize, fontWeight: 800, color: C.white, lineHeight: 1.12, letterSpacing: -1, marginTop: 14 }}>
        {scene.headline}
      </div>
    </div>
  );
};

const Card: React.FC<{ scene: Scene; immediate?: boolean }> = ({ scene, immediate }) => {
  const frame = useCurrentFrame();
  const dur = scene.durationInFrames;
  const e = useEnter(immediate ? -8 : 0);
  const shots = scene.shots ?? [];
  // The URL bar always shows the page of the screenshot currently on top.
  const visible = [...shots].reverse().find((s) => frame >= Math.round(s.from * dur)) ?? shots[0];
  const url = visible?.url ?? scene.url ?? "mindmetric.store";
  return (
    <div style={{
      ...box(B.card), borderRadius: 26, overflow: "hidden", background: "#f5f5f3", border: `2px solid ${C.border}`,
      boxShadow: "0 40px 100px rgba(0,0,0,0.55)", opacity: e.opacity, transform: `scale(${e.scale})`,
    }}>
      <div style={{ height: B.card.urlBarHeight, background: "#e8ecea", display: "flex", alignItems: "center", padding: "0 24px", gap: 10, borderBottom: "1px solid #d5dcd8" }}>
        {["#ff5f57", "#febc2e", "#28c840"].map((c) => <div key={c} style={{ width: 16, height: 16, borderRadius: 8, background: c }} />)}
        <div style={{ marginLeft: 14, flex: 1, height: 42, borderRadius: 10, background: "#fff", border: "1px solid #d5dcd8", display: "flex", alignItems: "center", padding: "0 16px", fontFamily: INTER, fontSize: B.card.urlFontSize, color: "#40504a", overflow: "hidden", whiteSpace: "nowrap", textOverflow: "ellipsis" }}>
          {url}
        </div>
      </div>
      <div style={{ position: "relative", width: IMG_W, height: IMG_H, overflow: "hidden" }}>
        {shots.map((s, i) => {
          const start = Math.round(s.from * dur);
          const op = i === 0 ? 1 : interpolate(frame, [start, start + 12], [0, 1], clamp);
          return <ShotView key={s.src + i} shot={s} t={interpolate(frame, [0, dur], [0, 1], clamp)} opacity={op} />;
        })}
      </div>
    </div>
  );
};

const CalloutView: React.FC<{ c: Callout; dur: number }> = ({ c, dur }) => {
  const frame = useCurrentFrame();
  const from = Math.round(c.from * dur);
  const to = Math.round(c.to * dur);
  const e = useEnter(from, { damping: 16, stiffness: 170 });
  const out = c.to >= 1 ? 1 : interpolate(frame, [to - 8, to], [1, 0], clamp);
  if (frame < from - 1 || (c.to < 1 && frame > to)) return null;
  return (
    <div style={{ ...box(B.callout), display: "flex", alignItems: "center", justifyContent: "center" }}>
      <div style={{
        opacity: e.opacity * out, transform: `scale(${e.scale})`, background: "rgba(8,16,13,0.94)", border: `3px solid ${C.accent}`,
        borderRadius: 22, padding: `18px ${B.callout.paddingX}px`, maxWidth: B.callout.w, boxShadow: "0 24px 60px rgba(0,0,0,0.5)",
        fontFamily: INTER, fontSize: B.callout.fontSize, fontWeight: 800, color: C.accentBright, textAlign: "center", lineHeight: 1.15,
      }}>
        {c.text}
      </div>
    </div>
  );
};

const Logo: React.FC<{ size: number }> = ({ size }) => (
  <div style={{ display: "flex", alignItems: "center", gap: size * 0.35 }}>
    <svg width={size} height={size} viewBox="0 0 40 40">
      {[0, 60, 120, 180, 240, 300].map((a) => (
        <circle key={a} cx={20 + 13 * Math.cos((a * Math.PI) / 180)} cy={20 + 13 * Math.sin((a * Math.PI) / 180)} r={3.6} fill={C.accent} />
      ))}
      <circle cx={20} cy={20} r={5.5} fill={C.accentBright} />
    </svg>
    <span style={{ fontFamily: INTER, fontWeight: 800, fontSize: size * 0.8, color: C.white, letterSpacing: -0.5 }}>MindMetric</span>
  </div>
);

const CtaScene: React.FC<{ scene: Scene; cta: ShortProps["cta"] }> = ({ scene, cta }) => {
  const a = useEnter(0);
  const b = useEnter(10);
  const c = useEnter(22);
  return (
    <div style={{ ...box(B.cta), display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", textAlign: "center", gap: 40 }}>
      <div style={{ opacity: a.opacity, transform: `scale(${a.scale})` }}><Logo size={84} /></div>
      <div style={{ opacity: a.opacity, fontFamily: INTER, fontWeight: 700, fontSize: B.cta.fontSize * 1.3, color: C.white, lineHeight: 1.15, letterSpacing: -0.8 }}>
        {scene.headline}
      </div>
      <div style={{ opacity: b.opacity, transform: `scale(${b.scale})`, fontFamily: INTER, fontWeight: 800, fontSize: B.cta.urlFontSize, color: C.accentBright, letterSpacing: -1.5, padding: "18px 0", borderTop: `3px solid ${C.accent}`, borderBottom: `3px solid ${C.accent}` }}>
        {cta.url}
      </div>
      <div style={{ opacity: c.opacity, display: "flex", flexDirection: "column", gap: 18 }}>
        {cta.lines.map((l) => (
          <div key={l} style={{ fontFamily: INTER, fontSize: B.cta.fontSize, fontWeight: 600, color: C.white }}>{l}</div>
        ))}
        <div style={{ fontFamily: INTER, fontSize: B.cta.smallFontSize, color: C.muted, lineHeight: 1.3 }}>{cta.disclaimer}</div>
      </div>
    </div>
  );
};

const SceneView: React.FC<{ scene: Scene; props: ShortProps; first: boolean; last: boolean }> = ({ scene, props, first, last }) => {
  const frame = useCurrentFrame();
  const dur = scene.durationInFrames;
  const fade = interpolate(frame, [0, first ? 1 : 8, dur - (last ? 1 : 8), dur], [first ? 1 : 0, 1, 1, last ? 1 : 0], clamp);
  return (
    <AbsoluteFill style={{ opacity: fade }}>
      {scene.kind === "cta" ? (
        <CtaScene scene={scene} cta={props.cta} />
      ) : (
        <>
          <Header scene={scene} tag={props.screenshotTag} immediate={first} />
          <Card scene={scene} immediate={first} />
          {(scene.callouts ?? []).map((c) => <CalloutView key={c.text} c={c} dur={dur} />)}
        </>
      )}
    </AbsoluteFill>
  );
};

const Subtitles: React.FC<{ cues: Cue[] }> = ({ cues }) => {
  const frame = useCurrentFrame();
  const cue = cues.find((c) => frame >= c.from && frame < c.to);
  if (!cue) return null;
  const op = interpolate(frame, [cue.from, cue.from + 4], [0.4, 1], clamp);
  return (
    <div style={{ ...box(B.subtitles), display: "flex", alignItems: "center", justifyContent: "center" }}>
      <div style={{
        opacity: op, background: "rgba(0,0,0,0.78)", borderRadius: 18, padding: `14px ${B.subtitles.paddingX}px`, maxWidth: B.subtitles.w,
        fontFamily: INTER, fontSize: B.subtitles.fontSize, fontWeight: 700, color: C.white, textAlign: "center", lineHeight: 1.22,
      }}>
        {cue.text}
      </div>
    </div>
  );
};

const Disclosure: React.FC<{ d: ShortProps["disclosure"] }> = ({ d }) => (
  <div style={{ ...box(B.disclosure), display: "flex", alignItems: "center", justifyContent: "center" }}>
    <div style={{
      fontFamily: INTER, fontSize: B.disclosure.fontSize, fontWeight: 600, padding: "8px 22px", borderRadius: 30,
      color: d.tone === "amber" ? "#1a1205" : C.offWhite, background: d.tone === "amber" ? C.amber : "rgba(255,255,255,0.08)",
      border: d.tone === "amber" ? "none" : `1px solid ${C.border}`,
    }}>
      {d.text}
    </div>
  </div>
);

export const MarketingShort: React.FC<ShortProps> = (props) => (
  <AbsoluteFill style={{ background: `radial-gradient(ellipse at 50% 30%, #0f3326 0%, ${C.bg} 62%)` }}>
    {props.scenes.map((s, i) => (
      <Sequence key={s.id} from={s.from} durationInFrames={s.durationInFrames} name={s.id}>
        <SceneView scene={s} props={props} first={i === 0} last={i === props.scenes.length - 1} />
        {s.audio ? (
          <Sequence from={s.audio.startFrame} name={`vo-${s.id}`}>
            <Audio src={staticFile(s.audio.src)} />
          </Sequence>
        ) : null}
      </Sequence>
    ))}
    <Subtitles cues={props.cues} />
    <Disclosure d={props.disclosure} />
  </AbsoluteFill>
);
