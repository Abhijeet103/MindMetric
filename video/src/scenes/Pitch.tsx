import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";
import { COLORS } from "../constants";
import { INTER } from "../fonts";
import { enter } from "../anim";
import { Backdrop, Label, Logo } from "./Common";

const PROPS = [
  { label: "Formats", text: "The real section formats.", accent: "Built for the test in your invite." },
  { label: "Timing", text: "The real timing.", accent: "Fullscreen, timed test mode." },
  { label: "Learning", text: "An explanation after every answer.", accent: "Know why, not just what." },
];

export const Pitch: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const logo = enter(frame, fps, 4);
  return (
    <Backdrop>
      <AbsoluteFill style={{ alignItems: "center", paddingTop: 150 }}>
        <div style={{ opacity: logo.opacity, transform: `scale(${logo.scale})` }}><Logo size={64} /></div>
        <div style={{ fontFamily: INTER, fontSize: 30, color: COLORS.offWhite, marginTop: 22, opacity: logo.opacity }}>Practice built for the test in your invite.</div>
        <div style={{ display: "flex", gap: 36, marginTop: 90 }}>
          {PROPS.map((p, i) => {
            const e = enter(frame, fps, 95 + i * 55, { damping: 16, stiffness: 140 });
            return (
              <div key={p.label} style={{ width: 470, padding: "36px 38px", borderRadius: 20, background: COLORS.bgCard, border: `1px solid ${COLORS.border}`, borderTop: `3px solid ${COLORS.accent}`, opacity: e.opacity, transform: `translateY(${e.y}px) scale(${e.scale})` }}>
                <Label>{`0${i + 1} · ${p.label}`}</Label>
                <div style={{ fontFamily: INTER, fontSize: 36, fontWeight: 800, color: COLORS.white, marginTop: 18, lineHeight: 1.15, letterSpacing: -0.8 }}>{p.text}</div>
                <div style={{ fontFamily: INTER, fontSize: 22, color: COLORS.accentBright, marginTop: 14 }}>{p.accent}</div>
              </div>
            );
          })}
        </div>
      </AbsoluteFill>
    </Backdrop>
  );
};
