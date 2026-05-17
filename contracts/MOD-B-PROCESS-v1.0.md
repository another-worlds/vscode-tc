# Module Contract B: Video Processing Engine + YOLO Config + Parquet + OD Matrix
**Contract ID:** MOD-B-PROCESS-v1.0  
**Status:** Immutable on green (Phase 2, Task 8)  
**Scope:** Frame inference pipeline, line-crossing detection, Parquet writer, OD matrix aggregator, Excel export

## Configuration (Swappable, JSON)

Located at `/app/config/yolo_config.json` (mounted in worker container):

```json
{
  "model": "yolov8m.pt",
  "tracker": "bytetrack.yaml",
  "classes": [0, 2, 3, 5, 7],
  "class_names": {
    "0": "person",
    "2": "car",
    "3": "motorcycle",
    "5": "bus",
    "7": "truck"
  },
  "frame_skip": 2,
  "conf": 0.25,
  "iou": 0.45,
  "max_det": 300,
  "imgsz": 640,
  "device": 0,
  "verbose": false,
  "persist": true
}
```

**Purpose:** Model swap without code changes. New YOLOv8 version? Update config.json + restart worker.

## Dataflow Pipeline

```
┌────────────────────────────────┐
│ Video File (MP4/AVI/MOV)       │
└───────────────┬────────────────┘
                │
┌───────────────▼────────────────┐
│ Frame Generator (OpenCV)       │
│ - Read video at frame_skip rate│
│ - Apply resize (imgsz)         │
└───────────────┬────────────────┘
                │
┌───────────────▼────────────────┐
│ YOLOv8m Inference (GPU)        │
│ - Detect bboxes, class, conf   │
│ - Filter by confidence         │
└───────────────┬────────────────┘
                │
┌───────────────▼────────────────┐
│ ByteTrack Tracking             │
│ - Assign persistent IDs        │
│ - Track across frames          │
│ - Persist=true for line cross  │
└───────────────┬────────────────┘
                │
┌───────────────▼────────────────┐
│ Line Crossing Detection        │
│ - Center-point method (cx, cy) │
│ - Check vs. polyline endpoints │
│ - Compute direction vector     │
│ - Emit crossing event          │
└───────────────┬────────────────┘
                │
┌───────────────▼────────────────┐
│ Parquet Writer (PyArrow)       │
│ - Schema: frame, id, bbox...   │
│ - Append mode (efficient I/O)  │
└───────────────┬────────────────┘
                │
        ┌───────┴───────┐
        │               │
┌───────▼──────┐  ┌─────▼──────────┐
│ Postgres     │  │ OD Aggregator  │
│ Job Status   │  │ - Zone mapping │
│ Update       │  │ - Count matrix │
└──────────────┘  └─────┬──────────┘
                        │
                ┌───────▼────────┐
                │ Excel Export   │
                │ - openpyxl fmt │
                │ - Download     │
                └────────────────┘
```

## Parquet Schema (All Tracking Data)

Table: `tracks.parquet`

```
{
  "frame": int32,           // Frame number
  "track_id": int32,        // Persistent tracking ID from ByteTrack
  "bbox_x": float32,        // Bounding box (x_min, pixels)
  "bbox_y": float32,        // Bounding box (y_min, pixels)
  "bbox_w": float32,        // Bounding box width
  "bbox_h": float32,        // Bounding box height
  "cx": float32,            // Center X (x_min + w/2)
  "cy": float32,            // Center Y (y_min + h/2)
  "class_id": int32,        // Class ID (0=person, 2=car, etc.)
  "class_name": utf8,       // Class name (lookup from config)
  "confidence": float32,    // Detection confidence
  "prev_cx": float32,       // Previous frame center X (for direction)
  "prev_cy": float32,       // Previous frame center Y (for direction)
  "dx": float32,            // Direction X (cx - prev_cx)
  "dy": float32,            // Direction Y (cy - prev_cy)
  "line_id": utf8,          // Which counting line (if any)
  "crossing_event": int32   // 0=none, 1=entry, 2=exit
}
```

High-speed I/O: Parquet columnar format for efficient filtering & aggregation.

## Line Crossing Detection (Center-Point Method)

### Algorithm

For each tracked object in frame T:
1. Get current center: `(cx, cy)` from YOLO bbox
2. Get previous center: `(prev_cx, prev_cy)` from frame T-1
3. For each counting line L:
   - Line L defined by two points: `(x1, y1)` and `(x2, y2)`
   - Check if center moved across line:
     ```
     side_prev = sign((x2-x1)*(prev_cy-y1) - (y2-y1)*(prev_cx-x1))
     side_curr = sign((x2-x1)*(cy-y1) - (y2-y1)*(cx-x1))
     
     if side_prev != side_curr:  # Crossed the line
       # Determine direction from (dx, dy)
       dx = cx - prev_cx
       dy = cy - prev_cy
       direction = atan2(dy, dx)
       # Emit crossing event
     ```
4. Write to Parquet: frame, track_id, cx, cy, ..., line_id, crossing_event

### Direction Estimation

From consecutive frame centers:
- `dx = cx_curr - cx_prev`
- `dy = cy_curr - cy_prev`
- `direction_angle = atan2(dy, dx)` (radians, 0 = right, π/2 = down)
- Categorize: N/S/E/W/NE/NW/SE/SW (8 sectors) or continuous angle

## OD Matrix Aggregation

### Zone Definition

From line config (React-drawn lines), define zones:
- **Origin Zone:** Start polyline + buffer radius
- **Destination Zone:** End polyline + buffer radius
- Or: User defines explicit zones in line config JSON

### Aggregation Logic

Read Parquet → filter by line_id & crossing_event:
```python
# For each line with two endpoints (entry/exit):
entry_zone = lines[line_id].start_zone
exit_zone = lines[line_id].end_zone

# Count tracks: entered entry_zone, then exited exit_zone
od_counts[entry_zone][exit_zone] += 1

# Result: 2D matrix (n_zones × n_zones)
# Rows = origin zones, Cols = destination zones
# Values = count of objects
```

### Excel Export Format

Using `openpyxl`:
- Header: "OD Matrix - Project {project_name}"
- Rows: Origin zones (A2:A_n)
- Cols: Destination zones (B1:N1)
- Data cells: Count + percentage (e.g., "150 (25.3%)")
- Total row: Sum per destination
- Total col: Sum per origin
- Grand total: Sum all
- Formatting: Center align, borders, light background, bold headers

## Performance Invariants

1. **Effective FPS:** Configurable `frame_skip` (default 2) → processes every 2nd frame → targets ≥20 effective FPS on A100 GPU
   - `effective_fps = video_fps / frame_skip`
   - For 60fps video, skip=2 → 30 effective fps ✓

2. **GPU Memory:** Peak <80% during inference + tracking
   - Monitor via `nvidia-smi` in worker logs
   - If exceed: reduce `imgsz` or `max_det` in config

3. **Total Time:** One video <5 min from enqueue to Parquet written + job status updated
   - Includes: Frame extraction, inference, tracking, line crossing, write I/O

## Implementation Scope (Task 8, One-Shot)

- `backend/engine/tracking.py` – Line-crossing detection (center-point algorithm)
- `backend/engine/parquet_writer.py` – PyArrow Parquet schema + append logic
- `backend/engine/od_aggregator.py` – Zone-to-zone counting + matrix construction
- `backend/routers/export.py` – POST /export endpoint + openpyxl Excel generation
- Config loader: JSON → dict (in worker process.py)
- <400 LOC per file

## Success Criteria

- [x] Line crossing detects center-point crossings correctly
- [x] Parquet file has 100+ rows for test video (frame, track_id, crossing_event)
- [x] OD matrix sums to total crossing count (verifiable from Parquet)
- [x] Excel export downloads + opens in Excel with correct formatting
- [x] Effective FPS ≥20 on test hardware
- [x] Config JSON swap works: change model, restart worker, new model loads

---

**References:** [MASTER.md](MASTER.md), [MOD-E-GPU-POOL-v1.0.md](MOD-E-GPU-POOL-v1.0.md)  
**Version:** 1.0 (immutable)
