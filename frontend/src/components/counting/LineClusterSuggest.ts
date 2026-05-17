// Grand Contract v1.0 — M13 Client-side Line Cluster Suggestion
import type { SegmentPoint, SuggestedLine, LinePoint } from "../../types";

export function suggestCountingLines(
  segments: SegmentPoint[],
  videoWidth: number,
  videoHeight: number,
  epsPosition: number = 50,
  epsAngle: number = 20,
  minSamples: number = 5
): SuggestedLine[] {
  if (segments.length === 0) return [];

  const distFn = (a: SegmentPoint, b: SegmentPoint) =>
    segmentDistance(a, b, videoWidth, videoHeight);

  // Combined eps: position normalized + angle normalized
  const combinedEps = 0.7 * (epsPosition / Math.max(videoWidth, videoHeight)) + 0.3 * (epsAngle / 180);
  const labels = dbscan(segments, combinedEps, minSamples, distFn);

  // Group segments by cluster
  const clusters: Map<number, SegmentPoint[]> = new Map();
  for (let i = 0; i < labels.length; i++) {
    const label = labels[i];
    if (label === -1) continue;
    if (!clusters.has(label)) clusters.set(label, []);
    clusters.get(label)!.push(segments[i]);
  }

  const results: SuggestedLine[] = [];
  for (const [clusterId, pts] of clusters.entries()) {
    const [dx, dy] = fitLinePCA(pts);
    const cx = pts.reduce((s, p) => s + p.x_mid, 0) / pts.length;
    const cy = pts.reduce((s, p) => s + p.y_mid, 0) / pts.length;
    const [p1, p2] = extendToFrameBounds(cx, cy, dx, dy, videoWidth, videoHeight);
    results.push({ points: [p1, p2], cluster_id: clusterId, segment_count: pts.length });
  }

  return results.sort((a, b) => b.segment_count - a.segment_count);
}

function dbscan(
  points: SegmentPoint[],
  eps: number,
  minSamples: number,
  distanceFn: (a: SegmentPoint, b: SegmentPoint) => number
): number[] {
  const n = points.length;
  const labels = new Array<number>(n).fill(-1);
  let clusterId = 0;

  for (let i = 0; i < n; i++) {
    if (labels[i] !== -1) continue;
    const neighbors = rangeQuery(i, points, eps, distanceFn);
    if (neighbors.length < minSamples) continue;
    labels[i] = clusterId;
    const seeds = [...neighbors];
    for (let si = 0; si < seeds.length; si++) {
      const q = seeds[si];
      if (labels[q] === -1) {
        labels[q] = clusterId;
        const qNeighbors = rangeQuery(q, points, eps, distanceFn);
        if (qNeighbors.length >= minSamples) seeds.push(...qNeighbors);
      } else if (labels[q] === -1) {
        labels[q] = clusterId;
      }
    }
    clusterId++;
  }
  return labels;
}

function rangeQuery(
  idx: number,
  points: SegmentPoint[],
  eps: number,
  distFn: (a: SegmentPoint, b: SegmentPoint) => number
): number[] {
  const result: number[] = [];
  for (let i = 0; i < points.length; i++) {
    if (i !== idx && distFn(points[idx], points[i]) <= eps) result.push(i);
  }
  return result;
}

function fitLinePCA(points: SegmentPoint[]): [number, number] {
  const n = points.length;
  const mx = points.reduce((s, p) => s + p.x_mid, 0) / n;
  const my = points.reduce((s, p) => s + p.y_mid, 0) / n;
  let xx = 0, xy = 0, yy = 0;
  for (const p of points) {
    const dx = p.x_mid - mx;
    const dy = p.y_mid - my;
    xx += dx * dx; xy += dx * dy; yy += dy * dy;
  }
  // Power iteration for first principal component
  let vx = 1, vy = 0;
  for (let iter = 0; iter < 20; iter++) {
    const nx = xx * vx + xy * vy;
    const ny = xy * vx + yy * vy;
    const len = Math.hypot(nx, ny) || 1;
    vx = nx / len; vy = ny / len;
  }
  return [vx, vy];
}

function extendToFrameBounds(
  cx: number, cy: number,
  dx: number, dy: number,
  width: number, height: number
): [LinePoint, LinePoint] {
  // Find t range such that (cx+t*dx, cy+t*dy) stays in [0,W]x[0,H]
  const tBounds: number[] = [];
  if (Math.abs(dx) > 1e-9) {
    tBounds.push(-cx / dx, (width - cx) / dx);
  }
  if (Math.abs(dy) > 1e-9) {
    tBounds.push(-cy / dy, (height - cy) / dy);
  }
  if (tBounds.length === 0) {
    return [{ x: 0, y: cy }, { x: width, y: cy }];
  }
  const tMin = Math.min(...tBounds);
  const tMax = Math.max(...tBounds);
  return [
    { x: Math.round(cx + tMin * dx), y: Math.round(cy + tMin * dy) },
    { x: Math.round(cx + tMax * dx), y: Math.round(cy + tMax * dy) },
  ];
}

function segmentDistance(
  a: SegmentPoint, b: SegmentPoint,
  videoWidth: number, videoHeight: number,
  wPos: number = 0.7, wAng: number = 0.3
): number {
  const dx = (a.x_mid - b.x_mid) / videoWidth;
  const dy = (a.y_mid - b.y_mid) / videoHeight;
  const posDist = Math.hypot(dx, dy);
  const dAngle = Math.abs(a.angle_deg - b.angle_deg) % 180;
  const angDist = Math.min(dAngle, 180 - dAngle) / 180;
  return wPos * posDist + wAng * angDist;
}
