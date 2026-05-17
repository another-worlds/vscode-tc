// Grand Contract v1.0 — M13 Heatmap Overlay (Konva Layer)
import React, { useEffect } from "react";
import { Layer, Image as KonvaImage } from "react-konva";
import type { HeatmapData } from "../../types";

interface Props {
  data: HeatmapData;
  canvasWidth: number;
  canvasHeight: number;
  opacity?: number;
}

export const HeatmapOverlay: React.FC<Props> = ({
  data, canvasWidth, canvasHeight, opacity = 0.6
}) => {
  const [heatmapImage, setHeatmapImage] = React.useState<HTMLImageElement | null>(null);

  useEffect(() => {
    const cellW = data.width;
    const cellH = data.height;
    const gridW = data.grid.length;
    const gridH = data.grid[0]?.length ?? 0;
    if (gridW === 0 || gridH === 0) return;

    const offscreen = document.createElement("canvas");
    offscreen.width = cellW;
    offscreen.height = cellH;
    const ctx = offscreen.getContext("2d");
    if (!ctx) return;

    const cellPixW = cellW / gridW;
    const cellPixH = cellH / gridH;

    for (let xi = 0; xi < gridW; xi++) {
      for (let yi = 0; yi < gridH; yi++) {
        const density = data.grid[xi][yi];
        if (density <= 0) continue;
        ctx.fillStyle = densityToRgba(density, opacity);
        ctx.fillRect(xi * cellPixW, yi * cellPixH, cellPixW, cellPixH);
      }
    }

    // Scale to canvas dimensions
    const scaled = document.createElement("canvas");
    scaled.width = canvasWidth;
    scaled.height = canvasHeight;
    const sctx = scaled.getContext("2d");
    if (!sctx) return;
    sctx.drawImage(offscreen, 0, 0, canvasWidth, canvasHeight);

    const img = new Image();
    img.onload = () => setHeatmapImage(img);
    img.src = scaled.toDataURL();
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
 * Map normalized density [0,1] to RGBA using jet colormap.
 */
export function densityToRgba(density: number, alpha: number = 0.7): string {
  // Jet colormap: blue(0) → cyan → green → yellow → red(1)
  const d = Math.max(0, Math.min(1, density));
  let r = 0, g = 0, b = 0;
  if (d < 0.25) {
    r = 0; g = d * 4; b = 1;
  } else if (d < 0.5) {
    r = 0; g = 1; b = 1 - (d - 0.25) * 4;
  } else if (d < 0.75) {
    r = (d - 0.5) * 4; g = 1; b = 0;
  } else {
    r = 1; g = 1 - (d - 0.75) * 4; b = 0;
  }
  return `rgba(${Math.round(r * 255)}, ${Math.round(g * 255)}, ${Math.round(b * 255)}, ${alpha})`;
}
