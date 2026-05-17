# Module Contract C: Advanced Counting Line Interface (React-Embedded Custom Component)
**Contract ID:** MOD-C-REACT-UI-v1.0  
**Status:** Immutable on green (Phase 3, Task 10)  
**Scope:** Streamlit main app + official React custom component (line drawing, auto-suggest, analytics, export)

## Technology Stack

- **Main UI:** Streamlit (Python)
- **Custom Component:** Official Streamlit Components v1 (React template)
- **React libs:** React 18, Canvas API (drawing), Chart.js (optional heatmap)
- **Bidirectional Communication:** Streamlit.setComponentValue + Python callbacks
- **Heavy Computation:** Backend (Python, not React)

## UI Architecture

### Streamlit Main App (`frontend/streamlit_app.py`)

Hosts the custom React component + dashboard controls:
- Page: Login (JWT)
- Page: Workspace selector
- Page: Project list + status dashboard
- Page: Project detail + **embedded React component** (Task 10)

### React Custom Component (`frontend/components/counting_line/`)

Official template structure:
```
counting_line/
├── package.json (React app)
├── public/index.html
├── src/
│   ├── App.tsx (main component)
│   ├── Viewport.tsx (video + canvas overlay)
│   ├── DrawingTools.tsx (line draw, delete, toggle)
│   ├── AnalyticsOverlay.tsx (% per line, counts, heatmap)
│   ├── AutoSuggest.tsx (clustering button + suggestions)
│   └── index.tsx (entry point for Streamlit)
└── build/ (webpack output)
```

## Component Props & Events (Bi-Directional)

### Props IN (from Streamlit Python)

```python
{
  "video_url": "http://backend:8000/projects/{id}/video",
  # OR
  "frame_list": [base64_frame_1, base64_frame_2, ...],
  
  "existing_lines": [
    {
      "id": "line-1",
      "name": "Entry Zone",
      "points": [[100, 200], [400, 250]],  # polyline coords
      "color": "#FF0000",
      "visible": true,
      "statistics": {
        "count": 150,
        "percentage": 25.3,
        "direction": "NE"
      }
    }
  ],
  
  "trajectories": [  # Optional: render tracking history
    {
      "track_id": 42,
      "class": "car",
      "points": [[100, 200], [105, 210], [110, 220], ...],
      "color": "#00FF00",
      "alpha": 0.5
    }
  ],
  
  "current_frame": 0,
  "total_frames": 100,
  "video_fps": 30,
  "resolution": [1920, 1080]
}
```

### Events OUT (to Streamlit Python)

```typescript
// Fired when user draws/deletes lines
onLinesChange({
  lines: [
    { id: "line-1", points: [[x1, y1], [x2, y2]], name: "Entry" }
  ]
})

// Fired when user clicks "Auto-Suggest Lines"
onAutoSuggest({
  suggestion: "clustering_based" | "sector_detection",
  suggested_lines: [...]
})

// Fired when user clicks "Export to Excel"
onExport({
  export_format: "od_matrix",
  include_trajectories: true
})
```

## Features (Exact Implementation)

### 1. Central Viewport

- **HTML5 Video Player** – Play, pause, frame-by-frame (← →)
- **Canvas Overlay** – Draw lines on top of video frames
- **Layer Toggle** – Show/hide lines, trajectories, heatmap
- **100-Frame Slider** – Seek to frame (updates video + analytics)
- **Persistent All Lines** – All counting lines shown simultaneously with distinct colors

### 2. Drawing Tools Panel

- **"Draw Line" Button** – Click to start drawing; click two points on canvas to define line
- **"Delete Line" Button** – Select line (highlight), press delete key
- **"Layer Toggle"** – Checkbox list:
  - [x] Counting Lines
  - [x] Trajectories
  - [x] Heatmap
  - [x] Direction Arrows
- **"Trajectory Hover"** – Mouse over trajectory to show track_id + class tooltip

### 3. Analytics Overlay

- **Per-Line Statistics** (rendered on canvas):
  - Line name + count (e.g., "Entry Zone: 150")
  - Percentage of total (e.g., "25.3%")
  - Directional arrow (avg direction vector)
- **Total Counts** – Bottom-right summary: "Total: 600 objects"
- **Heatmap** – Optional canvas gradient showing density per region (canvas 2D context + fillRect with alpha)
- **Direction Arrows** – Small arrows overlaid on line, colored by average direction (N/S/E/W)

### 4. Automation: Auto-Suggest Lines

**Button:** "Auto-Suggest Optimal Lines"

**Algorithm:**
1. If trajectories provided, extract all direction vectors (end - start of each trajectory)
2. Run DBSCAN clustering on vectors (eps=0.3 radians, min_samples=5)
3. For each cluster:
   - Compute centroid direction
   - Draw perpendicular line (perpendicular to avg direction) at cluster density peak
   - Suggest 2–4 candidate lines (top 4 by count)
4. Show suggestions to user: preview in different color (e.g., dashed lines)
5. User clicks to accept suggested lines → merge into main line list

**Sector Detection (Fallback):**
- If <10 trajectories: divide viewport into 4 quadrants, suggest one line per quadrant

### 5. Export Trigger

**Button:** "Export to Excel"
- Calls Streamlit callback: `onExport({"export_format": "od_matrix"})`
- Backend `POST /projects/{id}/export` triggered
- React component disables button + shows spinner until download completes
- Browser triggers Excel file download (openpyxl-generated .xlsx)

## Bidirectional Communication (Streamlit Components v1)

```typescript
// React side (counting_line/src/App.tsx)
import { Streamlit } from "streamlit-component-lib"

const handleLinesChange = (lines) => {
  Streamlit.setComponentValue(lines)  // Send back to Python
}

// Python side (frontend/pages/project_detail.py)
import streamlit.components.v1 as components

lines_result = components.declare_component(
  "counting_line",
  url="http://localhost:3000"  # Dev mode
)

lines_changed = lines_result(
  video_url=f"...",
  existing_lines=project_lines,
  trajectories=tracking_data,
  key="counting_line"
)

if lines_changed:
  # Update Backend
  requests.post(f"/projects/{project_id}/lines", json={"lines": lines_changed})
  st.success("Lines saved!")
```

## Implementation Scope (Task 10, One-Shot)

- Full React app (TypeScript, functional components)
- Canvas drawing library (fabric.js or custom)
- DBSCAN clustering (scipy Python → JSON result → React display)
- Streamlit integration page (`frontend/pages/project_detail.py`)
- Build process: `npm run build` → `frontend/components/counting_line/build/`
- <400 LOC per file (split across Viewport.tsx, Tools.tsx, Analytics.tsx, etc.)

## Success Criteria

- [x] Component renders video + canvas overlay
- [x] Lines draw/delete correctly
- [x] Slider seeks video frame + updates analytics
- [x] Auto-Suggest clustering proposes 2–4 lines
- [x] Export button triggers Excel download
- [x] Bidirectional communication: lines saved to Backend on change
- [x] Performance: interactive on 1920x1080 60fps video (canvas <100ms per frame)

---

**References:** [MASTER.md](MASTER.md), [MOD-A-RBAC-v1.0.md](MOD-A-RBAC-v1.0.md), [MOD-B-PROCESS-v1.0.md](MOD-B-PROCESS-v1.0.md)  
**Version:** 1.0 (immutable)
