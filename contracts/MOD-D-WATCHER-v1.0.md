# Module Contract D: Yandex Disk Passive Watcher + Ingestion
**Contract ID:** MOD-D-WATCHER-v1.0  
**Status:** Immutable on green (Phase 2, Task 6)  
**Scope:** Watchdog observer (passive, no polling), file validation, deduplication, Backend ingestion trigger

## Behavior Specification

### Passive Monitoring

- **Watchdog Observer** – `watchdog.observers.Observer` with `recursive=True`
- **Event:** File create event (not modification or deletion)
- **Monitoring Path:** `$YANDEX_MOUNT_PATH` environment variable (default: `/mnt/yandex`)
- **Polling Interval:** <1s (internal watchdog polling, not application polling)

### File Structure Validation

Expect mounted Yandex Disk directory structure:
```
/mnt/yandex/
├── workspace-uuid-1/
│   ├── project-uuid-1/
│   │   └── video.mp4
│   └── project-uuid-2/
│       └── traffic_video.mov
├── workspace-uuid-2/
│   └── project-uuid-3/
│       └── sample.avi
```

**Validation Logic:**
1. On file create event → extract path: `/mnt/yandex/{workspace_id}/{project_id}/{filename}`
2. Validate:
   - `workspace_id` = valid UUID (regex or UUID.parse)
   - `project_id` = valid UUID
   - `filename` ends in `.mp4`, `.mov`, `.avi`, `.mkv`
3. If invalid → log warning, skip
4. If valid → proceed to deduplication

### Deduplication

**By File Hash:**
1. Compute SHA256 hash of file (first 1MB for speed, or full if <10MB)
2. Query Postgres: `SELECT * FROM projects WHERE file_hash = ?`
3. If found → skip (already ingested)
4. If not found → compute full hash + store in Postgres (new column: `file_hash`)

**By Path:**
1. Check if same `workspace_id/project_id/filename` already ingested
2. If yes → skip

### Atomic Ingestion

On new file detected + validated + deduplicated:

1. **Call Backend Endpoint**
   ```
   POST /ingest
   Headers: Authorization: Bearer <SERVICE_TOKEN>
   Body:
   {
     "workspace_id": "uuid-1",
     "project_id": "uuid-2",
     "video_path": "/mnt/yandex/uuid-1/uuid-2/video.mp4",
     "file_hash": "sha256_hash",
     "file_size_bytes": 1000000,
     "detected_at": "2026-05-17T02:23:00Z"
   }
   ```

2. **Backend Validation** (Task 5 endpoint)
   - Verify workspace exists + user has access
   - Verify project exists + belongs to workspace
   - Create ProjectIngestion record (pending)
   - Enqueue job to Redis: `{"video_id": project_id, "config": yolo_config, "lines": []}`
   - Return 202 Accepted: `{"job_id": "...", "status": "queued"}`

3. **Watcher Updates Status**
   - Poll Backend: `GET /jobs/{job_id}` (optional, or let Backend notify)
   - Log success/failure

### Invariants

- **Passive only** – No polling loops >1s; watchdog internal polling only
- **Atomic dedup** – All ingestion logic transactional (single DB write)
- **Idempotent** – Calling ingest twice with same file_hash = no effect (returns existing job_id)
- **No direct DB writes** – Only via Backend `/ingest` endpoint (enforced by network isolation in Docker)

## Service Architecture

### Watcher Container

**Image:** `Dockerfile.watcher` (Python 3.11 slim)  
**Dependencies:**
- `watchdog==3.0.0` – File system observer
- `requests==2.31.0` – HTTP client to Backend
- `pydantic==2.6.3` – Request validation
- `python-dotenv==1.0.0` – Env var loading

**Environment Variables:**
```
YANDEX_MOUNT_PATH=/mnt/yandex
BACKEND_URL=http://backend:8000
DB_URL=postgresql://...  # For optional direct polling (or use Backend only)
DEBUG=0  # Logging verbosity
SERVICE_TOKEN=watcher-secret-token  # Optional: Backend validation token
```

**Entry Point:** `python main.py` (watcher/main.py)

### Watcher Main Loop

```python
# watcher/main.py
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class VideoFileHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory:
            return
        
        # Extract workspace_id, project_id from path
        # Validate structure
        # Compute hash
        # Call Backend /ingest
        # Log result

observer = Observer()
observer.schedule(VideoFileHandler(), path=YANDEX_MOUNT_PATH, recursive=True)
observer.start()
observer.join()
```

### Backend Endpoint (Task 5)

**Endpoint:** `POST /projects/ingest`

```python
@router.post("/projects/ingest", status_code=202)
async def ingest_video(
    ingest: IngestionRequest,
    user: User = Depends(get_current_user)
):
    """Receive ingestion notification from watcher"""
    # 1. Verify workspace + project + access
    # 2. Check file_hash dedup
    # 3. Create ProjectIngestion record
    # 4. Enqueue job
    # 5. Return job_id
```

## Implementation Scope (Task 6, One-Shot)

- `watcher/main.py` – Main watchdog loop + file handler
- `watcher/handlers.py` – Path validation, hash computation, Backend call
- `watcher/models.py` – Pydantic IngestionRequest model
- `backend/routers/ingest.py` – POST /ingest endpoint (partial; completed in Task 5)
- <400 LOC per file

## Success Criteria

- [x] Watcher detects file creation in <2s
- [x] Valid file structure → ingestion started
- [x] Invalid file structure → skipped + logged
- [x] Duplicate file_hash → skipped
- [x] Backend enqueue → job queued in Redis
- [x] No direct Postgres writes by watcher (all via Backend)

---

**References:** [MASTER.md](MASTER.md), [MOD-A-RBAC-v1.0.md](MOD-A-RBAC-v1.0.md), [MOD-E-GPU-POOL-v1.0.md](MOD-E-GPU-POOL-v1.0.md)  
**Version:** 1.0 (immutable)
