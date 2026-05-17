// Grand Contract v1.0 — M13 Heatmap Overlay (Konva Layer)
import React, { useEffect, useRef } from "react";
import { Layer, Image as KonvaImage } from "react-konva";
import type { HeatmapData } from "../../types";

interface Props {
  data: HeatmapData;
  canvasWidth: number;
  canvasHeight: number;
  opacity?: number;
}

/**
 * Renders trajectory density heatmap as a semi-transparent colored overlay.
 *
 * Color mapping:
 *   density 0.0 → transparent
 *   density 0.5 → yellow (rgba 255, 255, 0, 0.5)
 *   density 1.0 → red (rgba 255, 0, 0, 0.8)
 *   Uses HSL interpolation: hue 240→0 (blue→red) scaled by density^0.5
 *
 * Algorithm:
 *   1. Create offscreen canvas (data.width × data.height)
 *   2. For each cell, compute RGBA from density
 *   3. Draw cell as filled rect on offscreen canvas
 *   4. Scale offscreen canvas to canvasWidth × canvasHeight via drawImage
 *   5. Convert to HTMLImageElement for Konva
 *
 * Performance note:
 *   Rendered once (data is static); re-renders only when data changes.
 *   offscreen canvas: 100×100 cells → 10k fillRect calls, acceptable.
 */
export const HeatmapOverlay: React.FC<Props> = ({
  data, canvasWidth, canvasHeight, opacity = 0.6
}) => {
  const imageRef = useRef<HTMLImageElement | null>(null);
  const [heatmapImage, setHeatmapImage] = React.useState<HTMLImageElement | null>(null);

  useEffect(() => {
    // TODO: implement per contract — render grid to offscreen canvas → HTMLImageElement
  }, [data, canvasWidth, canvasHeight, opacity]);

  return (
    <Layer opacity={opacity}>
      {heatmapImage && (
        <KonvaImage image={heatmapImage} width={canvasWidth} height={canvasHeight} />
      )}
    </Layer>
  );
};

/**
 * Map normalized density [0,1] to RGBA color.
 * Uses jet colormap: blue → cyan → green → yellow → red.
 */
export function densityToRgba(density: number, alpha: number = 0.7): string {
  // TODO: implement per contract
  return `rgba(255, 0, 0, ${alpha})`;
}
