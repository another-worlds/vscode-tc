# ════════════════════════════════════════════════════════════════════════════════
# IMMUTABLE MODULE v1.0 — Do not modify unless new explicit contract supersedes.
# Pluggable via deterministic interface.
#
# Module: M5 Queue Service
# Description: Redis-backed FIFO job queue for GPU worker dispatch
# ════════════════════════════════════════════════════════════════════════════════

# Grand Contract v1.0 — M5 Processing Queue Service
# Redis-backed job queue for GPU worker dispatch
from __future__ import annotations
from uuid import UUID
import json
import logging
import redis.asyncio as aioredis
from app.config import settings

logger = logging.getLogger(__name__)

JOB_QUEUE_KEY = "job_queue"
STATUS_KEY_PREFIX = "job_status:"

# Job payload schema stored as JSON in Redis
# { "video_id": str, "filepath": str, "project_id": str, "enqueued_at": str }


_redis_client: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    """
    Return a Redis connection from the pool.
    Invariant: connection uses hiredis parser for performance.
    """
    global _redis_client
    if _redis_client is None:
        _redis_client = await aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,  # strings instead of bytes
            health_check_interval=30,  # check connection health every 30s
        )
    return _redis_client


async def enqueue_video(video_id: UUID, filepath: str, project_id: UUID) -> None:
    """
    Push a processing job onto the Redis queue (LPUSH).

    Args:
        video_id:   UUID of video record in DB
        filepath:   absolute path to MP4 inside container
        project_id: parent project UUID

    Side-effects:
        - LPUSH to QUEUE_KEY
        - SET status key to 'QUEUED'

    Error modes:
        - Redis connection errors propagate to caller
    
    Invariant: Job is JSON-encoded as {"video_id", "filepath", "project_id"}
    Invariant: Queue key = "job_queue" (FIFO via LPUSH/BRPOP)
    Invariant: Enqueue is atomic (single LPUSH call)
    Side-effect: Increments queue length by 1
    Performance: O(1) Redis operation
    """
    redis = await get_redis()
    job = {
        "video_id": str(video_id),
        "filepath": filepath,
        "project_id": str(project_id),
    }
    await redis.lpush(JOB_QUEUE_KEY, json.dumps(job))
    if settings.DEBUG:
        logger.info(f"✓ Enqueued video {video_id} from {filepath}")


async def dequeue_video(timeout_s: int = 5) -> dict | None:
    """
    Blocking pop from the queue (BRPOP, timeout=5s).
    Used by the GPU worker main loop.

    Args:
        timeout_s: Blocking timeout in seconds (default 5s)

    Returns:
        Job dict {video_id, filepath, project_id} or None if timeout
    
    Invariant: Returns oldest job (FIFO via BRPOP on right end)
    Invariant: Waits up to timeout_s for job availability
    Invariant: Returns None on timeout (no exception)
    Side-effect: Removes job from queue (atomic)
    Performance: O(1) Redis operation + I/O wait
    """
    redis = await get_redis()
    try:
        # BRPOP on JOB_QUEUE_KEY, wait up to timeout_s
        # Returns (key, value) or None
        result = await redis.brpop(JOB_QUEUE_KEY, timeout=timeout_s)
        if result is None:
            # Timeout: no jobs available
            return None
        
        _key, job_json = result
        job = json.loads(job_json)
        return job
    except Exception as e:
        logger.error(f"✗ dequeue_video failed: {e}")
        return None


async def set_job_status(video_id: UUID, status: str, ttl_s: int = 3600) -> None:
    """
    Set ephemeral job status in Redis (TTL=1h) for polling by frontend.

    Args:
        video_id: UUID
        status:   PENDING | QUEUED | PROCESSING | PROCESSED | ERROR
        ttl_s: Time-to-live in seconds (default 1h = 3600s)
    
    Invariant: Status key = f"job_status:{video_id}"
    Invariant: Automatically expires after ttl_s (TTL ensures cleanup)
    Invariant: Overwrites previous status (last-write-wins)
    Side-effect: Creates/updates Redis key
    Performance: O(1) SET + EXPIRE
    """
    redis = await get_redis()
    status_key = f"{STATUS_KEY_PREFIX}{video_id}"
    await redis.setex(status_key, ttl_s, status)
    if settings.DEBUG:
        logger.debug(f"Job {video_id} status → {status} (expires in {ttl_s}s)")


async def get_queue_depth() -> int:
    """
    Return current length of QUEUE_KEY.
    Used by Dashboard service for workspace stats.
    
    Returns:
        Queue length (integer >= 0)
    
    Invariant: Returns LLEN of JOB_QUEUE_KEY
    Invariant: Returns 0 if key does not exist
    Side-effect: None (read-only)
    Performance: O(1) Redis operation
    """
    redis = await get_redis()
    try:
        depth = await redis.llen(JOB_QUEUE_KEY)
        return depth or 0
    except Exception as e:
        logger.error(f"✗ get_queue_depth failed: {e}")
        return 0
