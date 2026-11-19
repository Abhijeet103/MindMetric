// Separate Remotion entrypoint for vertical marketing shorts.
// Does not touch the existing MainVideo entry (video/src/Root.tsx).
// Rendered by video/scripts/marketing-workflow.py with --props=<run>/props.json --public-dir=<run>/public
import { registerRoot } from "remotion";
import { MarketingRoot } from "./Root";

registerRoot(MarketingRoot);
