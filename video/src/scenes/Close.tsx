import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { COLORS } from "../constants";
import { INTER } from "../fonts";
import { clamp, enter } from "../anim";
import { Backdrop, Label, Logo } from "./Common";

const TESTS = ["Thomas GIA", "CCAT", "SHL-style", "Watson-Glaser-style", "Consulting cases"];

export const Close: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const free = enter(frame, fps, 6);
  const logo = enter(frame, fps, 95);
  const tag = enter(frame, fps, 125);
  const cta = enter(frame, fps, 150);
  const cornerOp = interpolate(frame, [90, 120], [0, 1], clamp);
  const corner = (extra: React.CSSProperties): React.CSSProperties => ({ position: "absolute", width: 60, height: 60, opacity: cornerOp, borderColor: COLORS.accent, ...extra });
  return (
    <Backdrop glow="#0e2f25">
      <div style={corner({ top: 48, left: 48, borderTop: "3px solid", borderLeft: "3px solid" })} />
      <div style={corner({ top: 48, right: 48, borderTop: "3px solid", borderRight: "3px solid" })} />
      <div style={corner({ bottom: 48, left: 48, borderBottom: "3px solid", borderLeft: "3px solid" })} />
      <div style={corner({ bottom: 48, right: 48, borderBottom: "3px solid", borderRight: "3px solid" })} />
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
        <div style={{ display: "flex", gap: 22, opacity: free.opacity, transform: `translateY(${free.y}px)` }}>
          {["Free to start", "Never auto-renews"].map((t) => (
            <div key={t} style={{ fontFamily: INTER, fontSize: 24, fontWeight: 600, color: COLORS.accentBright, padding: "10px 22px", borderRadius: 999, border: `1px solid ${COLORS.accentDim}`, background: "rgba(62,207,168,0.08)" }}>{t}</div>
          ))}
        </div>
        <div style={{ marginTop: 70, opacity: logo.opacity, transform: `scale(${logo.scale})` }}><Logo size={84} /></div>
        <div style={{ fontFamily: INTER, fontSize: 76, fontWeight: 800, color: COLORS.white, marginTop: 30, letterSpacing: -2, opacity: tag.opacity, transform: `translateY(${tag.y}px)` }}>
          From invite to interview.
        </div>
        <div style={{ marginTop: 50, opacity: cta.opacity, transform: `scale(${cta.scale})`, fontFamily: INTER, fontSize: 38, fontWeight: 700, color: COLORS.bg, background: COLORS.accent, padding: "20px 54px", borderRadius: 16 }}>
          mindmetric.store
        </div>
        <Label color={COLORS.muted} style={{ marginTop: 40, opacity: cta.opacity }}>{TESTS.join("  ·  ")}</Label>
      </AbsoluteFill>
    </Backdrop>
  );
};
