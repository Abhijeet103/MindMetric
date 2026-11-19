import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { COLORS } from "../constants";
import { INTER, MONO } from "../fonts";
import { clamp, enter } from "../anim";
import { Backdrop, Label } from "./Common";

export const Hook: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const mail = enter(frame, fps, 8);
  const mailOut = interpolate(frame, [112, 136], [1, 0], clamp);
  const mailShift = interpolate(frame, [112, 136], [0, -60], clamp);
  const bodyLine = enter(frame, fps, 48);

  const p2 = interpolate(frame, [124, 150], [0, 1], clamp);
  const timed = enter(frame, fps, 130);
  const decides = enter(frame, fps, 165);
  const secondsLeft = Math.max(0, 12 * 60 - Math.floor(Math.max(0, frame - 130) * 2.2));
  const clock = `${String(Math.floor(secondsLeft / 60)).padStart(2, "0")}:${String(secondsLeft % 60).padStart(2, "0")}`;

  return (
    <Backdrop glow="#0b1f19">
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", opacity: mailOut, transform: `translateY(${mailShift}px)` }}>
        <div style={{
          width: 980, background: COLORS.bgCard, border: `1px solid ${COLORS.border}`, borderRadius: 22, padding: "38px 46px",
          opacity: mail.opacity, transform: `translateY(${mail.y * 2}px) scale(${mail.scale})`, boxShadow: "0 40px 100px rgba(0,0,0,0.55)",
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: 18 }}>
            <div style={{ width: 56, height: 56, borderRadius: 28, background: COLORS.accentDim, display: "flex", alignItems: "center", justifyContent: "center", fontFamily: INTER, fontWeight: 800, color: COLORS.white, fontSize: 24 }}>HR</div>
            <div>
              <div style={{ fontFamily: INTER, fontSize: 20, color: COLORS.muted }}>Graduate Recruitment Team · now</div>
              <div style={{ fontFamily: INTER, fontSize: 32, fontWeight: 700, color: COLORS.white, marginTop: 4 }}>Next step: your online assessment</div>
            </div>
          </div>
          <div style={{ fontFamily: INTER, fontSize: 24, lineHeight: 1.55, color: COLORS.offWhite, marginTop: 28, opacity: bodyLine.opacity, transform: `translateY(${bodyLine.y}px)` }}>
            Congratulations, you have been shortlisted. Please complete the timed aptitude assessment within <span style={{ color: COLORS.amber, fontWeight: 700 }}>48 hours</span>. You will have <span style={{ color: COLORS.amber, fontWeight: 700 }}>one attempt</span>.
          </div>
        </div>
      </AbsoluteFill>

      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", opacity: p2 }}>
        <div style={{ fontFamily: MONO, fontSize: 150, fontWeight: 600, color: COLORS.red, letterSpacing: 4, opacity: timed.opacity, transform: `scale(${timed.scale})`, textShadow: "0 0 60px rgba(239,68,68,0.35)" }}>
          {clock}
        </div>
        <div style={{ fontFamily: INTER, fontSize: 64, fontWeight: 800, color: COLORS.white, marginTop: 24, letterSpacing: -1.5, opacity: decides.opacity, transform: `translateY(${decides.y}px)` }}>
          It decides whether you get the interview.
        </div>
        <Label color={COLORS.muted} style={{ marginTop: 26, opacity: decides.opacity }}>Thomas GIA · CCAT · SHL · Watson-Glaser · Consulting</Label>
      </AbsoluteFill>
    </Backdrop>
  );
};
