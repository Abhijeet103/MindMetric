import React from "react";
import { Composition, registerRoot } from "remotion";
import { MainVideo } from "./MainVideo";
import { FPS, H, TOTAL_FRAMES, W } from "./constants";
import { SHORTS, totalFrames } from "./shorts/config";
import { TestShort } from "./shorts/TestShort";

export const RemotionRoot: React.FC = () => (
  <>
    <Composition id="MainVideo" component={MainVideo} durationInFrames={TOTAL_FRAMES} fps={FPS} width={W} height={H} />
    {SHORTS.map((cfg) => (
      <Composition key={cfg.id} id={cfg.id} component={TestShort} defaultProps={{ cfg }} durationInFrames={totalFrames(cfg)} fps={FPS} width={W} height={H} />
    ))}
    {/* 9:16 for Instagram Reels, YouTube Shorts and TikTok */}
    {SHORTS.map((cfg) => (
      <Composition key={`${cfg.id}-v`} id={cfg.id.replace("Short-", "Reel-")} component={TestShort} defaultProps={{ cfg }} durationInFrames={totalFrames(cfg)} fps={FPS} width={1080} height={1920} />
    ))}
  </>
);

registerRoot(RemotionRoot);
