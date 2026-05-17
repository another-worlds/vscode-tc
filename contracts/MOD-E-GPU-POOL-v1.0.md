# Module Contract E: GPU Worker Pool + Orchestration
**Contract ID:** MOD-E-GPU-POOL-v1.0  
**Status:** Immutable on green (Phase 2, Task 7)  
**Scope:** Redis queue setup, worker job dequeue/process/enqueue, GPU pinning, YOLOv8m config loading

## Queue Architecture

### Redis Setup

**Service:** `tc-redis` (Docker Compose, Redis 7 Alpine)  
**URL:** `redis://redis:6379`  
**Data Structures:**
- Queue: `rq_queue:default` (RQ queue) OR simple Redis list `job_queue`
- Job records: `job:{job_id}` (hash with status, worker_id, progress)
- Worker registry: `worker:{worker_id}` (hash with status, GPU_device, last_heartbeat)

### Job Queue Schema

Job enqueued by Backend:
```json
{
  "job_id": "uuid-1",
  "video_id": "project-uuid",
  "video_path": "/mnt/yandex/workspace-uuid/project-uuid/video.mp4",
  "config": {
    "model": "yolov8m.pt",
    "frame_skip": 2,
    "conf": 0.25,
    "iou": 0.45,
    ...  // from yolo_config.json
  },
  "lines": [
    {"id": "line-1", "points": [[100, 200], [400, 250]], "name": "Entry"}
  ],
  "output_parquet": "/app/parquet_store/project-uuid.parquet",
  "created_at": "2026-05-17T02:23:00Z",
  "status": "pending"  // pending | processing | done | failed
}
```

### Job Lifecycle

```
Backend enqueue (POST /projects/{id}/process)
    ↓
Redis LPUSH job_queue
    ↓
Worker RPOP job_queue (blocking)
    ↓
Worker processing (YOLOv8m + tracking)
    ↓
Worker writes Parquet
    ↓
Worker updates Postgres: job status = done
    ↓
Worker ready for next job
```

## Worker Process Specification

### Worker Dockerfile

**Base Image:** `nvidia/cuda:12.2.0-runtime-ubuntu22.04`  
**Include:**
- Python 3.11
- Ultralytics YOLOv8 + dependencies
- PyTorch + Torchvision (GPU-optimized)
- OpenCV, PyArrow, Pandas
- Redis + RQ (or redis-py for direct Redis access)

**Environment Variables:**
```
DB_URL=postgresql://...
REDIS_URL=redis://redis:6379
YOLO_CONFIG_PATH=/app/config/yolo_config.json
GPU_DEVICE=0  # 0-based GPU device index
DEBUG=0
```

**Runtime:** `runtime: nvidia` (Docker Compose) + GPU device reservation

### Worker Process Main Loop (`worker/process.py`)

```python
import redis
import json
import logging

def main():
    r = redis.Redis.from_url(os.environ.get("REDIS_URL"))
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    # Load config once on startup
    config = load_yolo_config()
    
    logger.info(f"Worker ready on GPU {os.environ.get('GPU_DEVICE')}")
    
    while True:
        # Blocking pop from queue (30s timeout)
        job_data = r.brpop("job_queue", timeout=30)
        
        if job_data is None:
            logger.debug("Queue idle")
            continue
        
        job_json = job_data[1].decode()
        job = json.loads(job_json)
        job_id = job["job_id"]
        
        try:
            logger.info(f"Processing job {job_id}")
            
            # Set status to processing
            update_job_status(job_id, "processing")
            
            # Run inference pipeline
            result = process_video(
                video_path=job["video_path"],
                config=config,
                lines=job["lines"],
                output_parquet=job["output_parquet"]
            )
            
            # Update Postgres + job status
            update_job_status(job_id, "done")
            logger.info(f"Job {job_id} completed")
            
        except Exception as e:
            logger.error(f"Job {job_id} failed: {e}")
            update_job_status(job_id, "failed", error_msg=str(e))
```

### Config Loader

**Location:** `worker/config/yolo_config.json` (mounted from Docker Compose)

```python
def load_yolo_config():
    config_path = os.environ.get("YOLO_CONFIG_PATH", "/app/config/yolo_config.json")
    with open(config_path, "r") as f:
        config = json.load(f)
    
    # Validate schema
    required_keys = ["model", "tracker", "frame_skip", "conf", "iou"]
    for key in required_keys:
        assert key in config, f"Missing key in config: {key}"
    
    return config
```

### Video Processing Pipeline (Simplified Pseudocode)

```python
def process_video(video_path, config, lines, output_parquet):
    # 1. Load model
    model = YOLO(config["model"])  # Download if needed
    
    # 2. Initialize tracker
    tracker = model.track(classes=config["classes"])
    
    # 3. Open video
    cap = cv2.VideoCapture(video_path)
    frame_count = 0
    parquet_rows = []
    
    # 4. Frame-by-frame inference
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        frame_count += 1
        
        # Apply frame skip
        if frame_count % config["frame_skip"] != 0:
            continue
        
        # Inference + tracking
        results = model.track(
            frame,
            conf=config["conf"],
            iou=config["iou"],
            max_det=config["max_det"],
            persist=True
        )
        
        # Extract bboxes + IDs
        for r in results:
            for track in r.boxes.id:
                # Get bbox, class, confidence
                # Compute center (cx, cy)
                # Check line crossing
                # Append to parquet_rows
        
    # 5. Write Parquet
    df = pd.DataFrame(parquet_rows)
    df.to_parquet(output_parquet, engine="pyarrow", index=False)
    
    cap.release()
    return {"parquet_path": output_parquet, "total_tracks": len(set(t["track_id"] for t in parquet_rows))}
```

## Scaling

### Single GPU VM

**Compose config:** 1 worker service
```yaml
worker:
  ...
  deploy:
    resources:
      reservations:
        devices:
          - driver: nvidia
            count: 1
```

### Multi-GPU VM

**Option 1: Manual service replication**
```yaml
worker-0:
  environment:
    GPU_DEVICE: 0
  ...
worker-1:
  environment:
    GPU_DEVICE: 1
  ...
```

**Option 2: Docker Compose scaling with environment override**
```bash
docker compose up -d --scale worker=4  # 4 workers, share 1 GPU (contention)
```

Better: Manual definition of N worker services (one per GPU).

### Job Fairness

Redis queue is FIFO; all workers share same queue → fair distribution.

## Invariants

1. **One job per worker** – No multi-job parallelism within single worker
2. **GPU device pinned** – Each worker reserved to specific GPU (env var `GPU_DEVICE`)
3. **Config dict only** – Model/tracker swaps via JSON config, no code changes
4. **Atomic Parquet writes** – Single write per job (no partial files)
5. **Status updates** – Job status in Postgres + Redis for polling
6. **Heartbeat (optional)** – Worker registers heartbeat every 30s to detect stale workers

## Implementation Scope (Task 7, One-Shot)

- `worker/Dockerfile` – GPU-enabled image (NVIDIA base)
- `worker/process.py` – Main job loop + error handling
- `worker/config/yolo_config.json` – Swappable model config
- `backend/routers/jobs.py` – Job enqueue/status endpoints (partial; completed in Task 5)
- <400 LOC per file

## Success Criteria

- [x] Worker starts + connects to Redis
- [x] Backend enqueues test job
- [x] Worker dequeues + processes + writes Parquet
- [x] Job status updates in Postgres
- [x] Config JSON swap works (new model loads on restart)
- [x] GPU memory <80% peak during inference
- [x] Multiple workers share queue (scale test)

---

**References:** [MASTER.md](MASTER.md), [MOD-B-PROCESS-v1.0.md](MOD-B-PROCESS-v1.0.md), [MOD-D-WATCHER-v1.0.md](MOD-D-WATCHER-v1.0.md)  
**Version:** 1.0 (immutable)
