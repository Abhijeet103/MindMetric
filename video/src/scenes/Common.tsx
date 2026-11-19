import React from "react";
import { AbsoluteFill, Img, interpolate, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { COLORS } from "../constants";
import { INTER, MONO } from "../fonts";
import { clamp, enter } from "../anim";

export const Backdrop: React.FC<{ children: React.ReactNode; glow?: string }> = ({ children, glow }) => (
  <AbsoluteFill style={{ background: `radial-gradient(ellipse at 50% 35%, ${glow ?? "#0d2a21"} 0%, ${COLORS.bg} 65%)` }}>
    {children}
  </AbsoluteFill>
);

export const Label: React.FC<{ children: React.ReactNode; color?: string; style?: React.CSSProperties }> = ({ children, color, style }) => (
  <div style={{ fontFamily: MONO, fontSize: 16, letterSpacing: 3, textTransform: "uppercase", color: color ?? COLORS.accent, ...style }}>
    {children}
  </div>
);

export const Logo: React.FC<{ size?: number }> = ({ size = 40 }) => (
  <div style={{ display: "flex", alignItems: "center", gap: size * 0.35 }}>
    <Img src={staticFile("brand-icon.svg")} style={{ width: size, height: size }} />
    <span style={{ fontFamily: INTER, fontWeight: 800, fontSize: size * 0.8, color: COLORS.white, letterSpacing: -0.5 }}>MindMetric</span>
  </div>
);

type Shot = { src: string; from: number; to?: number; zoom?: [number, number]; pan?: [number, number]; panX?: [number, number] };
type Callout = { text: string; sub?: string; at: number; until?: number; x: number; y: number };

/**
 * A browser window showing real product screenshots (2560x1440 captures of 1280x720 pages),
 * with slow zoom/pan, crossfades between shots, a caption and timed callouts.
 */
export const BrowserShots: React.FC<{
  url: string; label: string; title: string; shots: Shot[]; callouts?: Callout[];
}> = ({ url, label, title, shots, callouts = [] }) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const win = enter(frame, fps, 0);
  const cap = enter(frame, fps, 6);
  const WW = 1440, WH = 810;
  return (
    <Backdrop>
      <div style={{ position: "absolute", top: 54, left: 0, right: 0, textAlign: "center", opacity: cap.opacity, transform: `translateY(${cap.y}px)` }}>
        <Label>{label}</Label>
        <div style={{ fontFamily: INTER, fontWeight: 700, fontSize: 44, color: COLORS.white, marginTop: 10, letterSpacing: -0.8 }}>{title}</div>
      </div>
      <div style={{
        position: "absolute", left: (1920 - WW) / 2, top: 208, width: WW, height: WH - 60,
        borderRadius: 16, overflow: "hidden", border: `1px solid ${COLORS.border}`, background: "#fff",
        boxShadow: "0 40px 120px rgba(0,0,0,0.6), 0 0 0 1px rgba(62,207,168,0.08)",
        opacity: win.opacity, transform: `translateY(${win.y * 2}px) scale(${win.scale})`,
      }}>
        <div style={{ height: 44, background: "#eef1ef", display: "flex", alignItems: "center", padding: "0 18px", gap: 8, borderBottom: "1px solid #dde3e0" }}>
          {["#ff5f57", "#febc2e", "#28c840"].map((c) => <div key={c} style={{ width: 12, height: 12, borderRadius: 6, background: c }} />)}
          <div style={{ marginLeft: 18, flex: 1, maxWidth: 560, height: 28, borderRadius: 8, background: "#fff", border: "1px solid #dde3e0", display: "flex", alignItems: "center", padding: "0 14px", fontFamily: INTER, fontSize: 15, color: "#4f5d57" }}>
            {url}
          </div>
        </div>
        <div style={{ position: "relative", width: WW, height: WH - 104, overflow: "hidden" }}>
          {shots.map((s, i) => {
            const end = s.to ?? durationInFrames;
            const op = interpolate(frame, [s.from, s.from + 14, end - 1, end + 13], [0, 1, 1, i === shots.length - 1 ? 1 : 0], clamp);
            const t = interpolate(frame, [s.from, end], [0, 1], clamp);
            const z = s.zoom ? interpolate(t, [0, 1], s.zoom) : 1;
            const py = s.pan ? interpolate(t, [0, 1], s.pan) : 0;
            const px = s.panX ? interpolate(t, [0, 1], s.panX) : 0;
            return (
              <Img key={s.src + i} src={staticFile(`shots/${s.src}.png`)} style={{
                position: "absolute", top: 0, left: 0, width: WW, height: (WW * 1440) / 2560, opacity: op,
                transform: `scale(${z}) translate(${px}px, ${-py}px)`, transformOrigin: "50% 30%",
              }} />
            );
          })}
        </div>
      </div>
      {callouts.map((c) => {
        const e = enter(frame, fps, c.at, { damping: 16, stiffness: 170 });
        const out = c.until ? interpolate(frame, [c.until - 12, c.until], [1, 0], clamp) : 1;
        return (
          <div key={c.text} style={{
            position: "absolute", left: c.x, top: c.y, opacity: e.opacity * out, transform: `scale(${e.scale})`,
            background: "rgba(8,16,13,0.92)", border: `2px solid ${COLORS.accent}`, borderRadius: 14, padding: "14px 22px",
            maxWidth: 400, boxShadow: "0 20px 50px rgba(0,0,0,0.45)",
          }}>
            <div style={{ fontFamily: INTER, fontSize: 24, fontWeight: 700, color: COLORS.accentBright }}>{c.text}</div>
            {c.sub && <div style={{ fontFamily: INTER, fontSize: 17, color: COLORS.offWhite, marginTop: 4 }}>{c.sub}</div>}
          </div>
        );
      })}
      <AbsoluteFill style={{ pointerEvents: "none", background: "radial-gradient(ellipse at center, transparent 60%, rgba(0,0,0,0.45) 100%)" }} />
    </Backdrop>
  );
};
