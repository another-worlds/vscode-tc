// Grand Contract v1.0 — M13 Counting Line Editor
// Central counting UI: frame slider, trajectory overlay, line drawing, heatmap, cluster suggest
import React, { useCallback, useEffect, useRef, useState } from "react";
import { Stage, Layer, Line, Image as KonvaImage, Circle, Text } from "react-konva";
import type {
  Video, CountingLine, CountingResult, TrajectoryData,
  HeatmapData, SegmentPoint, SuggestedLine, LinePoint,
} from "../../types";
import { FrameSlider } from "./FrameSlider";
import { TrajectoryOverlay } from "./TrajectoryOverlay";
import { HeatmapOverlay } from "./HeatmapOverlay";
import { suggestCountingLines } from "./LineClusterSuggest";
import {
  listCountingLines, createCountingLine, deleteCountingLine,
  getCountingResult, getHeatmapData, getSuggestData,
  getFrameUrl, getTrajectories, getExportUrl,
} from "../../api/videos";

// ── Layer visibility flags ────────────────────────────────────────
export interface LayerVisibility {
  trajectories: boolean;
  heatmap: boolean;
  countingLines: boolean;
  suggestedLines: boolean;
}

// ── Drawing mode ──────────────────────────────────────────────────
export type DrawingMode = "idle" | "drawing" | "select";

interface Props {
  video: Video;
  projectId: string;
}

/**
 * CountingLineEditor — the main M13 component.
 *
 * Renders:
 *   - Konva Stage with video frame as background image
 *   - TrajectoryOverlay: all tracks as polylines, filtered by frame slider
 *   - HeatmapOverlay: density grid as semi-transparent colored canvas
 *   - CountingLine layer: all saved lines with count labels
 *   - Drawing layer: in-progress line drawn by user
 *   - SuggestedLines layer: client-side DBSCAN cluster suggestions
 *   - FrameSlider: controls current frame index (0–frame_count-1)
 *   - Control panel: layer toggles, mode selector, line list, export button
 *
 * State invariants:
 *   - trajectoryData loaded once after video.status === PROCESSED
 *   - heatmapData loaded on first heatmap layer toggle
 *   - suggestData loaded on first suggest request
 *   - countingLines refreshed after each create/delete
 *   - currentFrame ∈ [0, video.frame_count - 1]
 */
export const CountingLineEditor: React.FC<Props> = ({ video, projectId }) => {
  // Frame state
  const [currentFrame, setCurrentFrame] = useState(0);
  const [frameImage, setFrameImage] = useState<HTMLImageElement | null>(null);

  // Data state
  const [trajectoryData, setTrajectoryData] = useState<TrajectoryData | null>(null);
  const [heatmapData, setHeatmapData] = useState<HeatmapData | null>(null);
  const [suggestData, setSuggestData] = useState<SegmentPoint[] | null>(null);
  const [suggestedLines, setSuggestedLines] = useState<SuggestedLine[]>([]);
  const [countingLines, setCountingLines] = useState<CountingLine[]>([]);
  const [results, setResults] = useState<Record<string, CountingResult>>({});

  // UI state
  const [layers, setLayers] = useState<LayerVisibility>({
    trajectories: true,
    heatmap: false,
    countingLines: true,
    suggestedLines: false,
  });
  const [drawingMode, setDrawingMode] = useState<DrawingMode>("idle");
  const [inProgressPoints, setInProgressPoints] = useState<LinePoint[]>([]);
  const [newLineName, setNewLineName] = useState("");
  const [newLineColor, setNewLineColor] = useState("#FF0000");
  const [selectedLineId, setSelectedLineId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const stageRef = useRef<any>(null);

  // Canvas dimensions derived from video resolution
  const canvasWidth = video.resolution_w ?? 1280;
  const canvasHeight = video.resolution_h ?? 720;

  /**
   * Load frame JPEG image when currentFrame changes.
   * Uses browser Image() to load from /api/.../frames/{n}.
   */
  const loadFrameImage = useCallback(
    (frameNumber: number): void => {
      // TODO: implement per contract
    },
    [video.id, projectId]
  );

  /**
   * Load all trajectory data once (large payload, cached in state).
   * Triggered when video becomes PROCESSED.
   */
  const loadTrajectories = useCallback(async (): Promise<void> => {
    // TODO: implement per contract
  }, [video.id, projectId]);

  /**
   * Load heatmap data on first heatmap layer enable.
   */
  const loadHeatmap = useCallback(async (): Promise<void> => {
    // TODO: implement per contract
  }, [video.id]);

  /**
   * Fetch server segment data, run client-side DBSCAN, set suggestedLines.
   * DBSCAN parameters: eps=50px (position), angle_eps=20°; minSamples=5.
   */
  const handleSuggestLines = useCallback(async (): Promise<void> => {
    // TODO: implement per contract
  }, [video.id]);

  /**
   * Handle Konva stage click in drawing mode.
   * - First click: start line
   * - Subsequent clicks: extend line
   * - Double-click: finalize line → prompt name → save to backend
   */
  const handleStageClick = useCallback(
    (e: any): void => {
      // TODO: implement per contract
    },
    [drawingMode, inProgressPoints]
  );

  /**
   * Save the in-progress line to backend.
   * Requires newLineName to be non-empty.
   */
  const saveLine = useCallback(async (): Promise<void> => {
    // TODO: implement per contract
  }, [inProgressPoints, newLineName, newLineColor, video.id]);

  /**
   * Delete a counting line and its result.
   */
  const handleDeleteLine = useCallback(
    async (lineId: string): Promise<void> => {
      // TODO: implement per contract
    },
    [video.id]
  );

  /**
   * Load counting result for a specific line.
   * Results lazy-loaded per line on first select.
   */
  const loadResult = useCallback(
    async (lineId: string): Promise<void> => {
      // TODO: implement per contract
    },
    [video.id]
  );

  useEffect(() => { loadFrameImage(currentFrame); }, [currentFrame, loadFrameImage]);
  useEffect(() => { if (video.status === "PROCESSED") loadTrajectories(); }, [video.status, loadTrajectories]);
  useEffect(() => { if (layers.heatmap && !heatmapData) loadHeatmap(); }, [layers.heatmap, heatmapData, loadHeatmap]);

  // ── Render ────────────────────────────────────────────────────────
  return (
    <div className="flex h-full">
      {/* Left: Konva canvas viewport */}
      <div className="flex-1 flex flex-col">
        <Stage
          ref={stageRef}
          width={canvasWidth}
          height={canvasHeight}
          onClick={handleStageClick}
          style={{ cursor: drawingMode === "drawing" ? "crosshair" : "default" }}
        >
          {/* Layer 0: video frame background */}
          <Layer>
            {frameImage && <KonvaImage image={frameImage} width={canvasWidth} height={canvasHeight} />}
          </Layer>

          {/* Layer 1: heatmap overlay */}
          {layers.heatmap && heatmapData && (
            <HeatmapOverlay
              data={heatmapData}
              canvasWidth={canvasWidth}
              canvasHeight={canvasHeight}
            />
          )}

          {/* Layer 2: trajectory polylines */}
          {layers.trajectories && trajectoryData && (
            <TrajectoryOverlay
              data={trajectoryData}
              currentFrame={currentFrame}
              canvasWidth={canvasWidth}
              canvasHeight={canvasHeight}
            />
          )}

          {/* Layer 3: saved counting lines with count labels */}
          {layers.countingLines && (
            <Layer>
              {countingLines.map((line) => (
                <React.Fragment key={line.id}>
                  <Line
                    points={line.points.flatMap((p) => [p.x, p.y])}
                    stroke={line.color}
                    strokeWidth={3}
                    onClick={() => { setSelectedLineId(line.id); loadResult(line.id); }}
                  />
                  {results[line.id] && (
                    <Text
                      x={line.points[0].x}
                      y={line.points[0].y - 20}
                      text={`${line.name}: ↑${results[line.id].count_in} ↓${results[line.id].count_out}`}
                      fill={line.color}
                      fontSize={14}
                    />
                  )}
                </React.Fragment>
              ))}
            </Layer>
          )}

          {/* Layer 4: suggested lines */}
          {layers.suggestedLines && (
            <Layer>
              {suggestedLines.map((sl, i) => (
                <Line
                  key={i}
                  points={sl.points.flatMap((p) => [p.x, p.y])}
                  stroke="#00FF88"
                  strokeWidth={2}
                  dash={[8, 4]}
                />
              ))}
            </Layer>
          )}

          {/* Layer 5: in-progress drawing */}
          {drawingMode === "drawing" && inProgressPoints.length > 0 && (
            <Layer>
              <Line
                points={inProgressPoints.flatMap((p) => [p.x, p.y])}
                stroke={newLineColor}
                strokeWidth={2}
              />
              {inProgressPoints.map((p, i) => (
                <Circle key={i} x={p.x} y={p.y} radius={4} fill={newLineColor} />
              ))}
            </Layer>
          )}
        </Stage>

        <FrameSlider
          frameCount={video.frame_count ?? 100}
          currentFrame={currentFrame}
          onChange={setCurrentFrame}
        />
      </div>

      {/* Right: control panel */}
      <div className="w-80 p-4 bg-gray-900 text-white overflow-y-auto flex flex-col gap-4">
        {/* TODO: implement control panel per contract */}
        {/* Layer toggles, mode buttons, line list, name/color inputs, export button */}
      </div>
    </div>
  );
};
