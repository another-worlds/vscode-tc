// Grand Contract v1.0 — M13 Trajectory Overlay (Konva Layer)
import React from "react";
import { Layer, Line, Circle, Arrow } from "react-konva";
import type { TrajectoryData, Track } from "../../types";
import { VEHICLE_COLORS } from "./constants";

interface Props {
  data: TrajectoryData;
  currentFrame: number;
  canvasWidth: number;
  canvasHeight: number;
}

/**
 * Renders ALL tracking trajectories as polylines on the video frame.
 * Trajectory of each track is drawn from start to currentFrame position.
 *
 * Visual encoding:
 *   - Line color: by class_id (car=blue, truck=red, motorcycle=green, bus=orange)
 *   - Current position: filled circle at head of trajectory
 *   - Direction indicator: arrow at last 2 points
 *   - Opacity: proportional to track recency (recent = opaque)
 *
 * Performance note:
 *   Tracks not visible at currentFrame are skipped.
 *   For >500 tracks: canvas pixel operations instead of Konva shapes.
 *
 * Invariant: all coordinate values are in pixel space (video resolution).
 */
export const TrajectoryOverlay: React.FC<Props> = ({
  data, currentFrame, canvasWidth, canvasHeight
}) => {
  // TODO: implement per contract — filter tracks by currentFrame, render polylines
  return <Layer />;
};

/**
 * Filter track frames up to (and including) currentFrame.
 * Returns null if track has no frames at or before currentFrame.
 */
function getVisiblePoints(track: Track, currentFrame: number): number[] | null {
  // TODO: implement per contract
  return null;
}
