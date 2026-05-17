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

  const loadFrameImage = useCallback(
    (frameNumber: number): void => {
      const url = getFrameUrl(projectId, video.id, frameNumber);
      const img = new Image();
      img.onload = () => setFrameImage(img);
      img.src = url;
    },
    [video.id, projectId]
  );

  const loadTrajectories = useCallback(async (): Promise<void> => {
    try {
      const data = await getTrajectories(projectId, video.id);
      setTrajectoryData(data);
    } catch (e) {
      console.error("Failed to load trajectories", e);
    }
  }, [video.id, projectId]);

  const loadHeatmap = useCallback(async (): Promise<void> => {
    try {
      const data = await getHeatmapData(video.id);
      setHeatmapData(data);
    } catch (e) {
      console.error("Failed to load heatmap", e);
    }
  }, [video.id]);

  const handleSuggestLines = useCallback(async (): Promise<void> => {
    try {
      let segs = suggestData;
      if (!segs) {
        segs = await getSuggestData(video.id);
        setSuggestData(segs);
      }
      const suggestions = suggestCountingLines(segs, canvasWidth, canvasHeight);
      setSuggestedLines(suggestions);
      setLayers((l) => ({ ...l, suggestedLines: true }));
    } catch (e) {
      console.error("Failed to load suggest data", e);
    }
  }, [video.id, suggestData, canvasWidth, canvasHeight]);

  const handleStageClick = useCallback(
    (e: any): void => {
      if (drawingMode !== "drawing") return;
      const stage = e.target.getStage();
      const pos = stage.getPointerPosition();
      if (!pos) return;
      const point: LinePoint = { x: pos.x, y: pos.y };
      if (e.evt.detail === 2 && inProgressPoints.length >= 2) {
        // Double click: finalize
        saveLine();
        return;
      }
      setInProgressPoints((prev) => [...prev, point]);
    },
    [drawingMode, inProgressPoints]
  );

  const saveLine = useCallback(async (): Promise<void> => {
    if (inProgressPoints.length < 2 || !newLineName.trim()) return;
    setLoading(true);
    try {
      await createCountingLine(video.id, {
        name: newLineName.trim(),
        points: inProgressPoints,
        color: newLineColor,
      });
      setInProgressPoints([]);
      setDrawingMode("idle");
      setNewLineName("");
      const lines = await listCountingLines(video.id);
      setCountingLines(lines);
    } catch (e) {
      setError("Failed to save counting line");
    } finally {
      setLoading(false);
    }
  }, [inProgressPoints, newLineName, newLineColor, video.id]);

  const handleDeleteLine = useCallback(
    async (lineId: string): Promise<void> => {
      try {
        await deleteCountingLine(video.id, lineId);
        setCountingLines((prev) => prev.filter((l) => l.id !== lineId));
        setResults((prev) => { const r = { ...prev }; delete r[lineId]; return r; });
      } catch (e) {
        setError("Failed to delete line");
      }
    },
    [video.id]
  );

  const loadResult = useCallback(
    async (lineId: string): Promise<void> => {
      if (results[lineId]) return;
      try {
        const result = await getCountingResult(video.id, lineId);
        setResults((prev) => ({ ...prev, [lineId]: result }));
      } catch {
        // result not yet computed
      }
    },
    [video.id, results]
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
        {/* Layer toggles */}
        <div>
          <h3 className="font-semibold mb-2 text-sm text-gray-300">Layers</h3>
          {(["trajectories", "heatmap", "countingLines", "suggestedLines"] as const).map((key) => (
            <label key={key} className="flex items-center gap-2 text-sm mb-1 cursor-pointer">
              <input
                type="checkbox"
                checked={layers[key]}
                onChange={(e) => setLayers((l) => ({ ...l, [key]: e.target.checked }))}
              />
              {key}
            </label>
          ))}
        </div>

        {/* Drawing mode */}
        <div>
          <h3 className="font-semibold mb-2 text-sm text-gray-300">Drawing</h3>
          <button
            className={"px-3 py-1 rounded text-sm mr-2 " + (drawingMode === "drawing" ? "bg-blue-600" : "bg-gray-700")}
            onClick={() => setDrawingMode(drawingMode === "drawing" ? "idle" : "drawing")}
          >
            {drawingMode === "drawing" ? "Stop Drawing" : "Draw Line"}
          </button>
          {drawingMode === "drawing" && (
            <div className="mt-2 flex flex-col gap-2">
              <input
                type="text"
                placeholder="Line name"
                value={newLineName}
                onChange={(e) => setNewLineName(e.target.value)}
                className="bg-gray-800 text-white px-2 py-1 rounded text-sm w-full"
              />
              <div className="flex items-center gap-2 text-sm">
                <label>Color:</label>
                <input type="color" value={newLineColor} onChange={(e) => setNewLineColor(e.target.value)} />
              </div>
              {inProgressPoints.length >= 2 && (
                <button
                  className="bg-green-600 hover:bg-green-700 px-3 py-1 rounded text-sm"
                  onClick={saveLine}
                  disabled={!newLineName.trim() || loading}
                >
                  {loading ? "Saving..." : "Save Line"}
                </button>
              )}
            </div>
          )}
        </div>

        {/* Suggest button */}
        <button
          className="bg-purple-600 hover:bg-purple-700 px-3 py-1 rounded text-sm"
          onClick={handleSuggestLines}
        >
          Suggest Lines
        </button>

        {/* Counting lines list */}
        <div>
          <h3 className="font-semibold mb-2 text-sm text-gray-300">Counting Lines</h3>
          {countingLines.map((line) => (
            <div
              key={line.id}
              className={"p-2 rounded mb-1 cursor-pointer " + (selectedLineId === line.id ? "bg-gray-700" : "hover:bg-gray-800")}
              onClick={() => { setSelectedLineId(line.id); loadResult(line.id); }}
            >
              <div className="flex items-center gap-2">
                <span className="w-3 h-3 rounded-full inline-block" style={{ backgroundColor: line.color }} />
                <span className="text-sm flex-1">{line.name}</span>
                <button
                  className="text-red-400 text-xs hover:text-red-300"
                  onClick={(e) => { e.stopPropagation(); handleDeleteLine(line.id); }}
                >Del</button>
              </div>
              {results[line.id] && (
                <div className="text-xs text-gray-400 mt-1">
                  In: {results[line.id].count_in} | Out: {results[line.id].count_out}
                </div>
              )}
            </div>
          ))}
        </div>

        {/* Export */}
        <a
          href={getExportUrl(video.id)}
          download
          className="bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded text-sm text-center"
        >
          Export XLSX
        </a>

        {error && <div className="text-red-400 text-sm">{error}</div>}
      </div>
    </div>
  );
};
