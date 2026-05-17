# Master Contract: TRAFFIC-COUNT-MVP-ARCH-v1.0

**Version:** 1.0 (immutable baseline)  
**Status:** Validated (Phase 1 Complete)  
**Single Source of Truth:** All child contracts reference this document.

## Executive Summary

End-to-end GPU-accelerated video traffic-counting MVP. Workspace/project ingestion from Yandex Disk → YOLOv8m tracking + line-crossing counting → Parquet analytics + OD matrix export → Hybrid Streamlit + React UI with RBAC. Containerized via Docker Compose (single `sudo docker compose up`). Success: E2E processing in <5 min on A100-class GPU.

## Scope

- **Input:** Workspace/project creation; video ingestion from Yandex Disk (mounted volume)
- **Processing:** GPU-accelerated YOLOv8m inference + ByteTrack persistent ID tracking
- **Line Counting:** Center-point method (cx, cy vs. polyline) per frame
- **Output:** Parquet tracking dataset + 2D origin-destination (OD) matrix + Excel export
- **UI:** Streamlit dashboard (workspace/project mgmt, RBAC) + embedded React component (line drawing, auto-suggest, heatmap, directional analytics)
- **RBAC:** Role-based access control (pm, analyst, admin); DEBUG=1 overrides all
- **Logging:** All mutations → AuditLog (timestamp, user_id, action, details)

## Architectural Invariants (Enforced in All Child Contracts)

1. **Multi-container Docker Compose only** – Single `sudo docker compose up`; no Kubernetes, no manual startup scripts
2. **GPU isolation** – Workers use NVIDIA runtime + `deploy.resources.reservations.devices`; each worker pinned to one GPU device
3. **Modularity** – Each service independently replaceable (model swap via config dict only, no code changes)
4. **One-shot tasks only** – No task spans >1 coding session; each <400 LOC change, clear contract input, testable in <10 min
5. **RBAC + DEBUG=1** – DEBUG=1 env var sets roles = ["admin"] for all users; all actions logged (timestamp + user_id + action + target)
6. **Performance** – Configurable frame skip targeting ≥20 effective FPS; Parquet for all tracking data (high-speed I/O)
7. **Best Practices** – NVIDIA Compose patterns, Ultralytics Docker, Streamlit Custom Components v1 (official React template), watchdog recursive observer, FastAPI JWT+role dependencies, YOLOv8m + ByteTrack line-crossing (center-point method)

## Data Model (High-Level)

### Core Entities
- **Workspace** – Isolated projects, storage quota, owner
- **Project** – Video metadata (path, resolution, duration), processing status, line config, OD matrix result
- **User** – Credentials, roles (pm/analyst/admin), debug override flag
- **AuditLog** – Every action: timestamp, user_id, action name, target_id, details JSON
- **Job** – Async processing queue entry (video_id, config, lines, status, worker_id)
- **Track** – Parquet: frame, track_id, bbox, class, center (cx, cy), direction vector, line crossing events

## Dataflow (Explicit Working Contract)

```
┌─────────────────────────────────────────────────────────────────────┐
│ YANDEX DISK (Mounted Volume /mnt/yandex)                           │
└────────────────────────────────────┬────────────────────────────────┘
                                     │ (file create event)
┌────────────────────────────────────▼────────────────────────────────┐
│ WATCHER SERVICE (watchdog.Observer)                                 │
│ - Detect new files: workspace_id/project_id/video.mp4              │
│ - Validate structure, deduplicate by hash                          │
│ - Call Backend POST /ingest                                         │
└────────────────────────────────────┬────────────────────────────────┘
                                     │ (POST /ingest)
┌────────────────────────────────────▼────────────────────────────────┐
│ BACKEND (FastAPI Orchestration + REST API)                          │
│ - Project CRUD, workspace mgmt, audit logging                       │
│ - Job enqueue to Redis queue                                        │
│ - Status polling, analytics aggregation                             │
└────────────────────────────────────┬────────────────────────────────┘
                                     │ (enqueue: video_id, config, lines)
┌────────────────────────────────────▼────────────────────────────────┐
│ GPU WORKER POOL (Docker Compose workers + Redis consumer)           │
│ - Dequeue job from Redis                                            │
│ - Load YOLOv8m.pt + ByteTrack (config-driven)                      │
│ - Frame-by-frame inference → tracking IDs                           │
│ - Line crossing: center-point (cx, cy) vs polyline                 │
│ - Write Parquet: frame, track_id, bbox, class, direction          │
│ - Update Postgres: job status, processed frames                    │
└────────────────────────────────────┬────────────────────────────────┘
                                     │ (Parquet + Postgres update)
┌────────────────────────────────────▼────────────────────────────────┐
│ PARQUET STORE + POSTGRES METADATA                                   │
│ - Parquet: all tracking data (high-speed I/O)                      │
│ - Postgres: job status, project metadata, audit logs               │
│ - OD Matrix: aggregated from line start/end zones                  │
└────────────────────────────────────┬────────────────────────────────┘
                                     │ (GET /projects/{id}, POST /export)
┌────────────────────────────────────▼────────────────────────────────┐
│ FRONTEND (Streamlit Dashboard + React Component)                    │
│ - Streamlit: workspace list, project status, RBAC-protected pages  │
│ - React: video viewport, line drawing, auto-suggest, heatmap       │
│ - Bidirectional: save lines → Backend, export → Excel              │
└────────────────────────────────────┬────────────────────────────────┘
                                     │ (GET + POST)
┌────────────────────────────────────▼────────────────────────────────┐
│ EXPORT (Excel OD Matrix + Statistics)                               │
│ - Format: origin zones (rows) vs destination zones (cols)           │
│ - Values: count + percentage                                        │
│ - openpyxl formatting + auto-fit columns                            │
└─────────────────────────────────────────────────────────────────────┘
```

### Inter-Service Communication

All via typed REST/queue contracts:
- **Backend ↔ Frontend**: HTTP (JSON + JWT auth)
- **Backend ↔ Watcher**: HTTP (JWT auth)
- **Backend ↔ Workers**: Redis queue (JSON jobs)
- **Backend ↔ Database**: SQLAlchemy ORM (Postgres)
- **Backend ↔ Parquet**: PyArrow + Pandas (direct file I/O)

**No direct file writes by LLM-generated code; only validated engine mutations.**

## Success Criteria (Testable)

- ✅ `docker compose up` succeeds on GPU VM (all services healthy within 30s)
- ✅ New Yandex videos auto-ingest (watcher detects + Backend enqueues within 2s)
- ✅ One video processes end-to-end with line markup + OD export in <5 min on A100-class GPU
- ✅ RBAC blocks unauthorized actions except in DEBUG=1 mode
- ✅ E2E test script passes: upload → process → export → verify Parquet schema + Excel download

## Versioning & Immutability

This contract is **immutable at v1.0**. All child module contracts (MOD-A through MOD-E) reference this master.

If changes required:
1. Create new numbered version (v1.1, v2.0, etc.)
2. Update all child contract references
3. Tag all Docker images with new version
4. Regenerate Alembic migration if schema changes

---

## Child Module Contracts

See separate files:
- [MOD-A-RBAC-v1.0.md](MOD-A-RBAC-v1.0.md) – Workspace & Project Management + RBAC + Logging
- [MOD-B-PROCESS-v1.0.md](MOD-B-PROCESS-v1.0.md) – Video Processing Engine + YOLO Config + Parquet + OD Matrix
- [MOD-C-REACT-UI-v1.0.md](MOD-C-REACT-UI-v1.0.md) – Advanced Counting Line Interface (React Component)
- [MOD-D-WATCHER-v1.0.md](MOD-D-WATCHER-v1.0.md) – Yandex Disk Passive Watcher + Ingestion
- [MOD-E-GPU-POOL-v1.0.md](MOD-E-GPU-POOL-v1.0.md) – GPU Worker Pool + Orchestration

---

**Approved & Validated:** May 17, 2026  
**Ready for Implementation:** Phase 1 ✓, Phase 2-5 in progress
