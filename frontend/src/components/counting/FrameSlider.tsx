// Grand Contract v1.0 — M13 Frame Slider component
import React from "react";

interface Props {
  frameCount: number;
  currentFrame: number;
  onChange: (frame: number) => void;
}

/**
 * Horizontal slider to navigate through uniformly sampled video frames.
 *
 * Displays: frame number / total frames, time position if fps known.
 * Range: [0, frameCount - 1].
 * Invariant: currentFrame ∈ [0, frameCount - 1].
 */
export const FrameSlider: React.FC<Props> = ({ frameCount, currentFrame, onChange }) => {
  // TODO: implement per contract
  return (
    <div className="flex items-center gap-3 p-2 bg-gray-800">
      <span className="text-white text-sm w-24">Frame {currentFrame + 1}/{frameCount}</span>
      <input
        type="range"
        min={0}
        max={frameCount - 1}
        value={currentFrame}
        onChange={(e) => onChange(Number(e.target.value))}
        className="flex-1"
      />
    </div>
  );
};
