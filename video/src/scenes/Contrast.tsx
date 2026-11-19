import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { COLORS } from "../constants";
import { INTER } from "../fonts";
import { clamp, enter } from "../anim";
import { Backdrop, Label } from "./Common";

const Column: React.FC<{ title: string; label: string; items: string[]; good: boolean; at: number }> = ({ title, label, items, good, at }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const e = enter(frame, fps, at);
  const color = good ? COLORS.accent : COLORS.red;
  return (
    <div style={{ width: 640, opacity: e.opacity, transform: `translateY(${e.y}px) scale(${e.scale})` }}>
      <Label color={color}>{label}</Label>
      <div style={{ fontFamily: INTER, fontSize: 46, fontWeight: 800, color: good ? COLORS.white : COLORS.offWhite, marginTop: 14, letterSpacing: -1 }}>{title}</div>
      <div style={{ marginTop: 34, display: "flex", flexDirection: "column", gap: 18 }}>
        {items.map((it, i) => {
          const ie = enter(frame, fps, at + 14 + i * 10);
          return (
            <div key={it} style={{ display: "flex", alignItems: "center", gap: 18, opacity: ie.opacity, transform: `translateX(${ie.y}px)` }}>
              <div style={{ width: 40, height: 40, borderRadius: 20, border: `2px solid ${color}`, color, display: "flex", alignItems: "center", justifyContent: "center", fontFamily: INTER, fontWeight: 800, fontSize: 22 }}>{good ? "✓" : "×"}</div>
              <div style={{ fontFamily: INTER, fontSize: 30, color: good ? COLORS.white : COLORS.muted }}>{it}</div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export const Contrast: React.FC = () => {
  const frame = useCurrentFrame();
  const divider = interpolate(frame, [70, 100], [0, 1], clamp);
  return (
    <Backdrop glow="#0b1a15">
      <AbsoluteFill style={{ flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 120 }}>
        <Column label="How most people prepare" title="Random question banks" items={["No clock", "Generic question types", "Answers without the why"]} good={false} at={8} />
        <div style={{ width: 2, height: 440 * divider, background: `linear-gradient(180deg, transparent, ${COLORS.accent}, transparent)` }} />
        <Column label="What the real test is like" title="Timed, format-specific" items={["Strict section timers", "Exact question formats", "Pressure on speed and accuracy"]} good at={130} />
      </AbsoluteFill>
    </Backdrop>
  );
};
