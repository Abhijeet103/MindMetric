import React from "react";
import { AbsoluteFill, Audio, Img, Sequence, interpolate, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { COLORS } from "../constants";
import { INTER, MONO } from "../fonts";
import { clamp, enter, sceneFade } from "../anim";
import { Backdrop, Label, Logo } from "../scenes/Common";
import { LEAD, ShortConfig, localFrame, sceneLayout, wordTime } from "./config";

/** A real product screenshot on a white card, the way it looks in the app. */
const ShotCard: React.FC<{ src: string; width: number; style?: React.CSSProperties }> = ({ src, width, style }) => (
  <div style={{ width, borderRadius: 22, overflow: "hidden", background: "#fff", boxShadow: "0 30px 90px rgba(0,0,0,0.55), 0 0 0 1px rgba(62,207,168,0.15)", ...style }}>
    <Img src={staticFile(`${src}.png`)} style={{ width: "100%", display: "block" }} />
  </div>
);

/** Reels/Shorts (9:16) get larger type, stacked layouts and room for the app's overlays. */
const useVertical = () => {
  const { width, height } = useVideoConfig();
  return height > width;
};

const Fade: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  return <AbsoluteFill style={{ opacity: sceneFade(frame, durationInFrames, 8, 10) }}>{children}</AbsoluteFill>;
};

const Hook: React.FC<{ cfg: ShortConfig }> = ({ cfg }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const q = enter(frame, fps, 2);
  const detailAt = localFrame(cfg, "hook", wordTime(cfg.timeline, cfg.hook.detailAnchor));
  const punchAt = localFrame(cfg, "hook", wordTime(cfg.timeline, cfg.hook.punchAnchor));
  const d = enter(frame, fps, detailAt);
  const p = enter(frame, fps, punchAt);
  const n = cfg.sections.length;
  const V = useVertical();
  return (
    <Backdrop glow="#0e2a21">
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", padding: V ? "0 70px" : 0 }}>
        <div style={{ fontFamily: INTER, fontSize: V ? 108 : 92, lineHeight: 1.05, textAlign: "center", textWrap: "balance", fontWeight: 800, color: COLORS.white, letterSpacing: -2.5, opacity: q.opacity, transform: `translateY(${q.y}px) scale(${q.scale})` }}>
          {cfg.hook.question}
        </div>
        {cfg.hook.showDetail && (
          <div style={{ fontFamily: MONO, fontSize: V ? 56 : 54, fontWeight: 600, color: COLORS.amber, marginTop: V ? 56 : 40, textAlign: "center", opacity: d.opacity, transform: `scale(${d.scale})` }}>{cfg.hook.detail}</div>
        )}
        <div style={{ display: "flex", flexDirection: V ? "column" : "row", gap: V ? 16 : 18, marginTop: cfg.hook.showDetail ? 44 : V ? 80 : 64, opacity: d.opacity }}>
          {cfg.sections.map((s, i) => {
            const e = enter(frame, fps, detailAt + i * 5);
            const drain = interpolate(frame, [detailAt + 20, punchAt + 60], [1, 0.25 + 0.12 * i], clamp);
            return (
              <div key={s.name} style={{ width: V ? 860 : n > 3 ? 230 : 300, padding: V ? "20px 28px" : "18px 20px", borderRadius: 16, background: COLORS.bgCard, border: `1px solid ${COLORS.border}`, opacity: e.opacity, transform: `translateY(${e.y}px)` }}>
                <div style={{ fontFamily: MONO, fontSize: V ? 20 : 15, color: COLORS.muted }}>{`0${i + 1}/0${n}`}</div>
                <div style={{ fontFamily: INTER, fontSize: V ? 38 : 24, fontWeight: 700, color: COLORS.white, marginTop: 6 }}>{s.name}</div>
                <div style={{ height: 6, borderRadius: 3, background: COLORS.border, marginTop: 16 }}>
                  <div style={{ height: 6, borderRadius: 3, width: `${drain * 100}%`, background: drain < 0.45 ? COLORS.amber : COLORS.accent }} />
                </div>
              </div>
            );
          })}
        </div>
        <div style={{ fontFamily: INTER, fontSize: V ? 64 : 52, lineHeight: 1.1, textAlign: "center", textWrap: "balance", fontWeight: 700, color: COLORS.accentBright, marginTop: V ? 80 : 64, opacity: p.opacity, transform: `translateY(${p.y}px)` }}>
          {cfg.hook.punch}
        </div>
      </AbsoluteFill>
    </Backdrop>
  );
};

const Sections: React.FC<{ cfg: ShortConfig }> = ({ cfg }) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  let after = cfg.timeline.starts.sections;
  const starts = cfg.sections.map((s, i) => {
    const t = wordTime(cfg.timeline, s.anchor, after);
    after = t + 0.05;
    return i === 0 ? 0 : localFrame(cfg, "sections", t) - 3;
  });
  const active = starts.reduce((a, st, i) => (frame >= st ? i : a), 0);
  const V = useVertical();
  return (
    <Backdrop>
      {V && (
        <div style={{ position: "absolute", top: 380, left: 0, right: 0, textAlign: "center" }}>
          <div style={{ fontFamily: MONO, fontSize: 30, color: COLORS.accent, letterSpacing: 4 }}>{`${active + 1} / ${cfg.sections.length}`}</div>
          <div key={active} style={{ fontFamily: INTER, fontSize: 92, fontWeight: 800, color: COLORS.white, letterSpacing: -2, marginTop: 10, opacity: enter(frame, fps, starts[active]).opacity }}>{cfg.sections[active].name}</div>
        </div>
      )}
      <div style={{ position: "absolute", top: V ? 1580 : 70, left: 0, right: 0, display: "flex", flexWrap: "wrap", padding: V ? "0 60px" : 0, justifyContent: "center", gap: 14 }}>
        {cfg.sections.map((s, i) => {
          const on = i === active;
          const done = i < active;
          return (
            <div key={s.name} style={{
              fontFamily: INTER, fontSize: V ? 26 : 24, fontWeight: 700, padding: V ? "10px 22px" : "12px 24px", borderRadius: 999,
              color: on ? COLORS.bg : done ? COLORS.accentBright : COLORS.muted,
              background: on ? COLORS.accent : "transparent", border: `2px solid ${on || done ? COLORS.accent : COLORS.border}`,
            }}>{done ? "✓ " : ""}{s.name}</div>
          );
        })}
      </div>
      {cfg.sections.map((s, i) => {
        const st = starts[i];
        const end = i + 1 < starts.length ? starts[i + 1] : durationInFrames + 20;
        if (frame < st - 2 || frame > end + 12) return null;
        const e = enter(frame, fps, st, { damping: 17, stiffness: 190 });
        const out = interpolate(frame, [end - 4, end + 8], [1, 0], clamp);
        const push = interpolate(frame, [st, end], [1, 1.04], clamp);
        return (
          <AbsoluteFill key={s.name} style={{ alignItems: "center", justifyContent: "center", paddingTop: V ? 160 : 110, opacity: e.opacity * out }}>
            <div style={{ display: "flex", flexDirection: "column", gap: 22, alignItems: "center", transform: `translateY(${e.y * 1.5}px) scale(${e.scale * push})` }}>
              {s.shots.map((src, j) => {
                const se = enter(frame, fps, st + j * 22);
                return <ShotCard key={src} src={src} width={V ? 980 : 1000} style={{ opacity: se.opacity, transform: `translateY(${se.y}px)` }} />;
              })}
            </div>
          </AbsoluteFill>
        );
      })}
    </Backdrop>
  );
};

const Explain: React.FC<{ cfg: ShortConfig }> = ({ cfg }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = enter(frame, fps, 2);
  const c = enter(frame, fps, 10);
  const zoom = interpolate(frame, [10, 150], [1, 1.06], clamp);
  const V = useVertical();
  return (
    <Backdrop>
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", padding: V ? "0 60px" : 0 }}>
        <Label style={{ opacity: t.opacity }}>Practice mode · no timer</Label>
        <div style={{ fontFamily: INTER, fontSize: V ? 84 : 64, lineHeight: 1.05, textAlign: "center", textWrap: "balance", fontWeight: 800, color: COLORS.white, letterSpacing: -1.5, marginTop: 14, opacity: t.opacity, transform: `translateY(${t.y}px)` }}>{cfg.explainTitle}</div>
        <ShotCard src={cfg.explainShot} width={V ? 980 : 1050} style={{ marginTop: V ? 70 : 50, opacity: c.opacity, transform: `translateY(${c.y * 2}px) scale(${c.scale * zoom})` }} />
      </AbsoluteFill>
    </Backdrop>
  );
};

const FullTest: React.FC<{ cfg: ShortConfig }> = ({ cfg }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = enter(frame, fps, 2);
  const card = enter(frame, fps, 8);
  const langs = cfg.languages ?? [];
  const langFrames = langs.map((l) => localFrame(cfg, "fulltest", wordTime(cfg.timeline, l.anchor, cfg.timeline.starts.fulltest)) - 3);
  const langStart = langFrames[0] ?? 0;
  const langActive = langFrames.reduce((a, f, i) => (frame >= f ? i : a), 0);
  const V = useVertical();
  return (
    <Backdrop>
      <AbsoluteFill style={{ alignItems: "center", justifyContent: V ? "center" : "flex-start", paddingTop: V ? 0 : 110, padding: V ? "0 50px" : undefined }}>
        <Label style={{ opacity: t.opacity }}>Test mode · fullscreen</Label>
        <div style={{ fontFamily: INTER, fontSize: V ? 84 : 64, lineHeight: 1.05, textAlign: "center", textWrap: "balance", fontWeight: 800, color: COLORS.white, letterSpacing: -1.5, marginTop: 14, opacity: t.opacity }}>{cfg.fullTestTitle}</div>
        <ShotCard src={cfg.fullTestShot} width={V ? 980 : 1000} style={{ marginTop: 44, opacity: card.opacity, transform: `translateY(${card.y * 2}px) scale(${card.scale})` }} />
        {langs.length > 0 && (
          <div style={{ marginTop: 44, display: "flex", flexDirection: "column", alignItems: "center", gap: 22, opacity: interpolate(frame, [langStart - 10, langStart + 5], [0, 1], clamp) }}>
            <div style={{ display: "flex", gap: 14 }}>
              {langs.map((l, i) => (
                <div key={l.label} style={{ fontFamily: INTER, fontSize: V ? 34 : 26, fontWeight: 700, padding: V ? "12px 30px" : "10px 26px", borderRadius: 999, color: i === langActive ? COLORS.bg : COLORS.offWhite, background: i === langActive ? COLORS.accent : "transparent", border: `2px solid ${i === langActive ? COLORS.accent : COLORS.border}` }}>{l.label}</div>
              ))}
            </div>
            <ShotCard src={langs[langActive].shot} width={V ? 980 : 760} />
          </div>
        )}
      </AbsoluteFill>
    </Backdrop>
  );
};

const Cta: React.FC<{ cfg: ShortConfig }> = ({ cfg }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const l = enter(frame, fps, 2);
  const u = enter(frame, fps, 14);
  const f = enter(frame, fps, 26);
  const V = useVertical();
  return (
    <Backdrop glow="#0f3328">
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
        <div style={{ opacity: l.opacity, transform: `scale(${l.scale})` }}><Logo size={V ? 96 : 80} /></div>
        <div style={{ fontFamily: INTER, fontSize: V ? 76 : 60, textAlign: "center", fontWeight: 800, color: COLORS.white, marginTop: 30, letterSpacing: -1.5, opacity: l.opacity }}>{cfg.ctaLine}</div>
        <div style={{ marginTop: V ? 64 : 44, fontFamily: INTER, fontSize: V ? 56 : 44, fontWeight: 800, color: COLORS.bg, background: COLORS.accent, padding: "20px 56px", borderRadius: 18, opacity: u.opacity, transform: `scale(${u.scale})` }}>mindmetric.store</div>
        <div style={{ marginTop: 30, fontFamily: INTER, fontSize: V ? 34 : 26, color: COLORS.offWhite, opacity: f.opacity }}>Free to start · Never auto-renews</div>
      </AbsoluteFill>
    </Backdrop>
  );
};

const SCENES = { hook: Hook, sections: Sections, explain: Explain, fulltest: FullTest, cta: Cta } as const;

export const TestShort: React.FC<{ cfg: ShortConfig }> = ({ cfg }) => (
  <AbsoluteFill style={{ background: COLORS.bg }}>
    {sceneLayout(cfg).map(({ key, from, frames }) => {
      const Scene = SCENES[key];
      return (
        <Sequence key={key} from={from} durationInFrames={frames} name={key}>
          <Fade><Scene cfg={cfg} /></Fade>
        </Sequence>
      );
    })}
    <Sequence from={LEAD}><Audio src={staticFile(`vo/${cfg.voice}/full.mp3`)} /></Sequence>
    <TopBadge cfg={cfg} />
  </AbsoluteFill>
);

const TopBadge: React.FC<{ cfg: ShortConfig }> = ({ cfg }) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const V = useVertical();
  const ctaFrom = sceneLayout(cfg).find((s) => s.key === "cta")!.from;
  const op = interpolate(frame, [4, 16, ctaFrom - 6, ctaFrom + 6], [0, 1, 1, 0], clamp);
  if (!V || frame > durationInFrames) return null;
  return (
    <div style={{ position: "absolute", top: 210, left: 0, right: 0, display: "flex", justifyContent: "center", opacity: op }}>
      <div style={{ display: "flex", alignItems: "center", gap: 18, padding: "14px 30px", borderRadius: 999, background: "rgba(15,26,22,0.85)", border: `1px solid ${COLORS.border}` }}>
        <Logo size={40} />
        <span style={{ width: 2, height: 34, background: COLORS.border }} />
        <span style={{ fontFamily: INTER, fontSize: 34, fontWeight: 800, color: COLORS.accentBright }}>{cfg.testName}</span>
      </div>
    </div>
  );
};
