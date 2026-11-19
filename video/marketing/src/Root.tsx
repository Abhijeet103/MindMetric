import React from "react";
import { CalculateMetadataFunction, Composition } from "remotion";
import layout from "../layout.json";
import { MarketingShort } from "./MarketingShort";
import { ShortProps } from "./types";

// Placeholder used only by Remotion Studio when no --props are given.
const defaultProps: ShortProps = {
  fps: layout.fps,
  width: layout.width,
  height: layout.height,
  durationInFrames: 90,
  topicId: "preview",
  scenes: [{ id: "cta", kind: "cta", label: "Preview", headline: "Render via marketing-workflow.py", from: 0, durationInFrames: 90, audio: null }],
  cues: [],
  draft: true,
  disclosure: { text: "PREVIEW: no voiceover", tone: "amber" },
  cta: { url: "mindmetric.store", lines: ["Free to start. Never auto-renews."], disclaimer: "Independent practice. Not affiliated with any test publisher." },
  screenshotTag: "Real MindMetric screenshot",
};

const calculateMetadata: CalculateMetadataFunction<ShortProps> = ({ props }) => ({
  durationInFrames: props.durationInFrames,
  fps: props.fps,
  width: props.width,
  height: props.height,
});

export const MarketingRoot: React.FC = () => (
  <Composition
    id="MarketingShort"
    component={MarketingShort}
    durationInFrames={defaultProps.durationInFrames}
    fps={layout.fps}
    width={layout.width}
    height={layout.height}
    defaultProps={defaultProps}
    calculateMetadata={calculateMetadata}
  />
);
