---
name: demo-video
description: Create hackathon/product demo videos using Remotion. Handles video structure, scene creation, screen recordings, voiceover generation, and final rendering. Use when building demo videos, explainer videos, or pitch videos for any project.
argument-hint: [project-name or brief]
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, Agent, WebFetch
---

# Demo Video Creation Skill

Build compelling product demo videos using Remotion (React-based video framework). This skill encodes the full workflow: narrative structure, scene patterns, recording integration, voiceover, and rendering.

If `~/.claude/remotion-best-practices.md` exists, read it before starting any Remotion work. Otherwise follow sections 7 and 8 below and check the installed Remotion version's docs (`npx remotion --version`) before using an API you are unsure of.

## 1. Video Narrative Structure

Every demo video follows this arc. Adapt durations to fit the target length.

```
HOOK (10-15s)        → Grab attention with the problem
CONTRAST (5-10s)     → "Them vs Us" — show the gap
PRODUCT PITCH (10-15s) → 2-3 value props, one sentence each
LIVE DEMO (30-60s)   → Real product screenshots or screen recordings
ARCHITECTURE (8-12s) → How it works at a glance
PROOF (30-90s)       → Real recordings proving it works (terminal, explorer, traces)
CLOSE (15-30s)       → Split into two phases:
  Phase 1: Forward momentum (live data, pending actions)
  Phase 2: CTA + summary line
```

**Timing rule:** At 30fps, 1 second = 30 frames. A 3-minute video = 5400 frames.

**Narrative rules:**
- Hook must make the viewer feel the problem, not describe it
- Never open with "This is [product name]" — open with the pain
- Value props should map to hackathon tracks or product pillars
- Proof sections use REAL recordings, not mocks — label them "REAL TERMINAL OUTPUT"
- Close Phase 1 shows forward momentum (pending work, live data)
- Close Phase 2 is the CTA — breathing room, clean layout

## 2. Project Setup

```bash
mkdir video && cd video
npm init -y
npm install remotion @remotion/cli @remotion/google-fonts react react-dom
npm install -D typescript @types/react @types/react-dom
```

### File Structure

```
video/
  public/              # staticFile() reads from here
    *.png              # Illustrations, screenshots, logos
    *.mp4              # Screen recordings (1920x1080 @ 30fps)
  src/
    Root.tsx            # All Compositions registered here
    constants.ts        # COLORS, FPS, W, H, demo data
    fonts.ts            # Font loading via @remotion/google-fonts
    [MainVideo].tsx     # Main composition — sequences all scenes
    scenes/             # One file per scene
      Hook.tsx
      Contrast.tsx
      Bridge.tsx         # Product pitch / value props
      DashboardShowcase.tsx
      ArchFlash.tsx      # Architecture overview
      [Recording].tsx    # Screen recording scenes
      Close.tsx
  scripts/
    generate-voiceover.py  # TTS generation script
  voiceover/               # Generated audio segments
  out/                     # Rendered videos
```

### Root.tsx Pattern

```tsx
import { Composition, registerRoot } from "remotion";
import { MainVideo } from "./MainVideo";
import { FPS, W, H } from "./constants";

export const RemotionRoot: React.FC = () => (
  <>
    <Composition
      id="MainVideo"
      component={MainVideo}
      durationInFrames={6300}  // calculate from scene sum
      fps={FPS}
      width={W}
      height={H}
    />
    {/* Register individual scenes for preview/testing */}
  </>
);

registerRoot(RemotionRoot);
```

### constants.ts Pattern

```ts
export const COLORS = {
  bg: "#09090b",
  bgCard: "#111114",
  accent: "#22c55e",       // primary brand color
  accentDim: "#166534",
  accentBright: "#4ade80",
  white: "#fafafa",
  offWhite: "#d4d4d8",
  muted: "#71717a",
  border: "#27272a",
  red: "#ef4444",
  amber: "#f59e0b",
};

export const FPS = 30;
export const W = 1920;
export const H = 1080;
```

### fonts.ts Pattern

```ts
import { loadFont as loadInter } from "@remotion/google-fonts/Inter";
import { loadFont as loadMono } from "@remotion/google-fonts/JetBrainsMono";

export const { fontFamily: INTER } = loadInter("normal", {
  weights: ["400", "500", "600", "700", "800", "900"],
  subsets: ["latin"],
});

export const { fontFamily: MONO } = loadMono("normal", {
  weights: ["400", "600", "700"],
  subsets: ["latin"],
});
```

## 3. Scene Patterns

### Pattern A: Illustrated Hook

Two or three phases in one scene. Each phase has illustration + text, cross-fading between them.

```tsx
// Phase 1: Optimistic (0-140 frames)
// Phase 2: Doubt / problem (140-300 frames)
// Phase 3: Punchline (300-450 frames)

const phase1Exit = interpolate(frame, [130, 160], [1, 0], {
  extrapolateLeft: "clamp", extrapolateRight: "clamp",
});

// Use spring for entrances
const investProg = spring({
  frame: frame - 5, fps,
  config: { damping: 18, stiffness: 160 },
});
const investOp = interpolate(investProg, [0, 0.35], [0, 1]);

// Use Img + staticFile for illustrations
<Img src={staticFile("ill-investing.png")} style={{ width: 420, height: 420 }} />
```

**Key rules:**
- Illustrations on one side, text on the other (alternating left/right per phase)
- Spring config: `damping: 16-20, stiffness: 140-180`
- Opacity from spring progress `[0, 0.35] → [0, 1]` (quick fade-in)
- Scale from spring `[0, 1] → [0.93, 1]` (subtle zoom-in, NEVER from 0)
- Phase exits use `interpolate` with 30-frame crossfade

### Pattern B: Side-by-Side Contrast

```tsx
// Left side (them) enters first, then divider, then right side (us)
const leftProg = spring({ frame: frame - 10, fps, config: { damping: 18, stiffness: 150 } });
const dividerOp = interpolate(frame, [40, 60], [0, 1], { ... });
const rightProg = spring({ frame: frame - 50, fps, config: { damping: 18, stiffness: 150 } });

// Bottom tagline appears last
const bottomOp = interpolate(frame, [120, 150], [0, 1], { ... });
```

### Pattern C: Staggered Value Props

```tsx
const props = [
  { label: "TRACK NAME", text: "Value proposition.", accent: "key phrase." },
  // ...
];

{props.map((p, i) => {
  const enter = 25 + i * 80;  // 80-frame stagger between props
  const prog = spring({ frame: frame - enter, fps, config: { damping: 16, stiffness: 140 } });
  // ...
})}
```

### Pattern D: Screenshot Showcase (Dashboard Demo)

Vertical strip of screenshots with animated scroll, zoom, and timed callouts.

```tsx
// Screenshots stacked vertically in a PageStrip component
const PageStrip = ({ screenshots, scrollY, zoom, panX, opacity }) => (
  <div style={{
    transform: `translateY(${-scrollY}px) scale(${zoom}) translateX(${panX}px)`,
    transformOrigin: "center 540px",
    opacity,
  }}>
    {screenshots.map(src => (
      <Img key={src} src={staticFile(src)} style={{ width: 1920, height: 1200, display: "block" }} />
    ))}
  </div>
);

// Scroll through sections with interpolate
const dashScroll = interpolate(frame, [0, 60, 150, 250, 330], [0, 0, 1400, 4000, 4800], { ... });

// Callouts use spring-based enter/exit
function useCallout(frame, fps, enterFrame, exitFrame) {
  const prog = spring({ frame: frame - enterFrame, fps, config: { damping: 18, stiffness: 150 } });
  const fadeOut = interpolate(frame, [exitFrame - 20, exitFrame], [1, 0], { ... });
  return {
    opacity: interpolate(prog, [0, 0.3], [0, 1]) * fadeOut,
    scale: interpolate(prog, [0, 1], [0.92, 1]),
  };
}
```

**Screenshot prep:**
- Take retina screenshots (2880x1800) → render at 1920x1200
- Multiple screenshots per page section for scroll effect
- 4-6 screenshots for main dashboard, 2-3 for secondary pages

### Pattern E: Hybrid Recording Scene

Animated title intro → crossfade into real screen recording → timed callouts → closing statement.

```tsx
// Title: appears 0-90 frames, fades out
const titleProg = spring({ frame: frame - 5, fps, config: { damping: 18, stiffness: 155 } });
const titleOp = interpolate(titleProg, [0, 0.35], [0, 1]);
const titleFade = interpolate(frame, [60, 90], [1, 0], { ... });

// Video: crossfades in as title fades out
const videoOp = interpolate(frame, [50, 80], [0, 1], { ... });
const videoScale = interpolate(frame, [50, 120], [1.02, 1], { ... }); // subtle zoom settle

// Video fades out for closing statement
const videoFadeOut = interpolate(frame, [780, 820], [1, 0], { ... });

// Closing statement springs in after video
const closeProg = spring({ frame: frame - 820, fps, config: { damping: 16, stiffness: 140 } });

<OffthreadVideo src={staticFile("recording.mp4")} startFrom={16 * 30} style={{ width: "100%", height: "100%" }} />
```

**Recording prep:**
- Screen recordings MUST be 1920x1080 @ 30fps
- Re-encode odd resolutions: `ffmpeg -i raw.mp4 -vf "scale=1920:1080" -r 30 -c:v libx264 -crf 18 output.mp4`
- Use `startFrom` to skip the first few seconds of setup in recordings
- Add gradient overlays (top/bottom) for text readability over recordings
- Label recordings: "REAL TERMINAL OUTPUT", "REAL ETHERSCAN", etc.

**Floating callout component (reuse across recording scenes):**

```tsx
const FloatingCallout = ({ text, subtext, opacity, scale, color, style }) => (
  <div style={{
    position: "absolute", opacity, transform: `scale(${scale})`,
    background: "rgba(0,0,0,0.85)", border: `2px solid ${color ?? COLORS.accent}`,
    borderRadius: 12, padding: "12px 20px", maxWidth: 380,
    backdropFilter: "blur(8px)", zIndex: 10, ...style,
  }}>
    <div style={{ fontFamily: INTER, fontSize: 20, fontWeight: 700, color: color ?? COLORS.accent }}>
      {text}
    </div>
    {subtext && <div style={{ fontFamily: INTER, fontSize: 14, color: COLORS.offWhite, marginTop: 4 }}>{subtext}</div>}
  </div>
);
```

### Pattern F: Two-Phase Close

Phase 1 shows forward momentum. Phase 2 is the CTA. They crossfade.

```tsx
// Phase 1 (0-480): Logo + live data + momentum text
const phase1Op = interpolate(frame, [0, 15, 430, 470], [0, 1, 1, 0], { ... });

// Phase 2 (470-900): CTA + summary
const phase2Op = interpolate(frame, [470, 510], [0, 1], { ... });

// Corner brackets for visual framing
const corner = (extra) => ({
  position: "absolute", width: 50, height: 50, opacity: cornerOp,
  borderColor: COLORS.accent, ...extra,
});
<div style={corner({ top: 40, left: 40, borderTop: "3px solid", borderLeft: "3px solid" })} />
```

### Pattern G: Architecture Flash

Two columns: product components (left) → arrow → infrastructure (right). Staggered line entrances.

```tsx
const agents = [
  { name: "Component A", desc: "does X" },
  { name: "Component B", desc: "does Y" },
];

// Arrow between columns
const arrowOp = interpolate(frame, [110, 130], [0, 1], { ... });
<div style={{ fontSize: 48, color: COLORS.accent, opacity: arrowOp }}>→</div>
```

## 4. Main Composition Assembly

```tsx
import { AbsoluteFill, Sequence } from "remotion";

export const MainVideo: React.FC = () => (
  <AbsoluteFill style={{ background: COLORS.bg }}>
    <Sequence from={0} durationInFrames={450}>
      <HookScene />
    </Sequence>
    <Sequence from={450} durationInFrames={240}>
      <ContrastScene />
    </Sequence>
    {/* ... add all scenes with calculated offsets */}
  </AbsoluteFill>
);
```

**Duration calculation:** Sum all scene durations. Update Root.tsx `durationInFrames` to match. Add a comment block at the top of the main composition showing the timeline:

```tsx
//    0 –  450  ( 0:00 – 0:15)  Hook
//  450 –  690  ( 0:15 – 0:23)  Contrast
//  690 – 1050  ( 0:23 – 0:35)  Product Pitch
// 1050 – 2250  ( 0:35 – 1:15)  Dashboard
// ...
```

## 5. Voiceover Generation

### Script Writing Rules

- Match voiceover text to what's on screen — read the scene components to see the text
- Each segment must fit within its scene duration
- Pace: ~150 words per minute for narration
- Short sentences. Pause-worthy. Not a wall of text.
- Don't describe what's visible — add context the visuals can't convey

### ElevenLabs Generation (if API available)

```python
# Use shared/community voices for African accents:
# "Taiwo" (CaroURy2Tqx0hGMqPyp8) — Nigerian male
# "Thabiso" (j32TutubsmjTPYaEhg5T) — South African male
# "JB Pro" (NZ8KtusXpnktPYja5Qko) — African male

# Voice settings for narration:
voice_settings = {
    "stability": 0.65,
    "similarity_boost": 0.78,
    "style": 0.15,
    "use_speaker_boost": True,
}
model_id = "eleven_multilingual_v2"
```

### Azure TTS (best African voices)

```python
# Nigerian: en-NG-AbeoNeural
# Kenyan: en-KE-ChilembaNeural
# South African: en-ZA-LukaasNeural
```

### Assembly with ffmpeg

Generate individual MP3s per scene segment, then combine:

```python
# Place each segment at its start time
# adelay=<ms>|<ms> for left and right channels
filter_parts.append(f"[{i}]adelay={delay_ms}|{delay_ms}[d{i}]")

# Mix all delayed streams
mix_inputs = "".join(f"[d{i}]" for i in range(len(segments)))
filter_parts.append(f"{mix_inputs}amix=inputs={len(segments)}:duration=longest:dropout_transition=0[out]")

# Merge audio with video
# ffmpeg -y -i video.mp4 -i voiceover.mp3 -c:v copy -c:a aac -b:a 192k -map 0:v:0 -map 1:a:0 -shortest output.mp4
```

## 6. Rendering

```bash
# Preview in browser
cd video && npx remotion studio src/Root.tsx

# Render specific composition
npx remotion render src/Root.tsx MainVideo out/demo.mp4

# Fast render (lower quality, for testing)
npx remotion render src/Root.tsx MainVideo out/demo.mp4 --quality 60
```

**Pre-render checklist:**
- Scrub through every scene in Studio — check for flash/pop/missing content
- Verify all `staticFile()` assets exist in `public/`
- Check that screen recordings are 1920x1080 @ 30fps
- Confirm total `durationInFrames` in Root.tsx matches scene sum
- Test text isn't cut off (60px minimum padding from edges)

## 7. Design Principles

- **Dark theme always.** Background: near-black (#09090b). Never white.
- **One accent color.** Green (#22c55e) for positive/brand. Red for problems. Amber for pending.
- **Radial gradient backgrounds** for important scenes: `radial-gradient(ellipse at 50% 40%, #0a1a0a 0%, #09090b 65%)`
- **Vignette overlay** on screenshot/recording scenes for depth
- **Corner brackets** on closing scenes for visual framing
- **Green separator lines** between sections: `linear-gradient(90deg, transparent, accent, transparent)`
- **Font hierarchy:** Inter for all text. JetBrains Mono for code/terminal/technical labels.
- **Font sizes:** Headlines 44-56px, body 18-24px, labels 13-16px, code 12-14px
- **Never use emojis** in video text unless explicitly requested

## 8. Common Gotchas

- **OffthreadVideo crashes on odd resolutions** — always re-encode to 1920x1080 first
- **Fonts don't load in render** — must use `@remotion/google-fonts`, never CDN
- **`npx remotion render` fails from wrong directory** — must `cd` into the video/ directory
- **Screen recordings at 60fps cause sync issues** — re-encode to 30fps
- **Large recordings (>100MB) slow down Studio** — trim with ffmpeg before importing
- **`staticFile()` only reads from `public/`** — never use relative paths
- **Spring from 0 looks jarring** — always start scale from 0.93 minimum