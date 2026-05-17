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

export const TrajectoryOverlay: React.FC<Props> = ({
  data, currentFrame,
}) => {
  return (
    <Layer>
      {data.tracks.map((track) => {
        const pts = getVisiblePoints(track, currentFrame);
        if (!pts || pts.length < 2) return null;
        const color = VEHICLE_COLORS[track.class_id] ?? "#FFFFFF";
        const lastX = pts[pts.length - 2];
        const lastY = pts[pts.length - 1];
        return (
          <React.Fragment key={track.track_id}>
            <Line points={pts} stroke={color} strokeWidth={1.5} opacity={0.7} />
            <Circle x={lastX} y={lastY} radius={4} fill={color} />
          </React.Fragment>
        );
      })}
    </Layer>
  );
};

function getVisiblePoints(track: Track, currentFrame: number): number[] | null {
  const visible = track.frames.filter((f) => f.f <= currentFrame);
  if (visible.length === 0) return null;
  const pts: number[] = [];
  for (const f of visible) {
    pts.push(f.x, f.y);
  }
  return pts.length >= 4 ? pts : null;
}
