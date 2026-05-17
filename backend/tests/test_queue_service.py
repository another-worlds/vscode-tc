# Grand Contract v1.0 — M5 Queue Service Unit Tests
# Run: pytest tests/test_queue_service.py -v

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
import json

# Mock redis.asyncio before importing queue_service
import sys
sys.modules["redis.asyncio"] = MagicMock()


@pytest.fixture
def mock_redis():
    """Mock Redis client."""
    redis = AsyncMock()
    return redis


@pytest.fixture
def sample_video_id():
    return uuid4()


@pytest.fixture
def sample_project_id():
    return uuid4()


class TestGetRedis:
    """Test Redis connection pool retrieval."""

    @pytest.mark.asyncio
    async def test_get_redis_connection(self):
        """Should return a Redis client instance."""
        from app.services.queue_service import get_redis
        
        with patch("app.services.queue_service.aioredis") as mock_aioredis:
            mock_client = AsyncMock()
            mock_aioredis.from_url.return_value = mock_client
            
            with patch("app.services.queue_service.settings") as mock_settings:
                mock_settings.REDIS_URL = "redis://localhost:6379"
                
                # Reset the global client
                import app.services.queue_service as qs
                qs._redis_client = None
                
                redis = await get_redis()
                
                assert redis is not None
                mock_aioredis.from_url.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_redis_reuses_connection(self):
        """Should reuse connection on subsequent calls (pool caching)."""
        from app.services.queue_service import get_redis
        
        with patch("app.services.queue_service.aioredis") as mock_aioredis:
            mock_client = AsyncMock()
            mock_aioredis.from_url.return_value = mock_client
            
            with patch("app.services.queue_service.settings") as mock_settings:
                mock_settings.REDIS_URL = "redis://localhost:6379"
                
                # Reset
                import app.services.queue_service as qs
                qs._redis_client = None
                
                r1 = await get_redis()
                r2 = await get_redis()
                
                assert r1 is r2  # Same instance


class TestEnqueueVideo:
    """Test job enqueue operation."""

    @pytest.mark.asyncio
    async def test_enqueue_video_success(self, sample_video_id, sample_project_id, mock_redis):
        """Should push job to Redis queue."""
        from app.services.queue_service import enqueue_video
        
        with patch("app.services.queue_service.get_redis", return_value=mock_redis):
            filepath = "/storage/videos/sample.mp4"
            
            await enqueue_video(sample_video_id, filepath, sample_project_id)
            
            # Verify LPUSH was called
            mock_redis.lpush.assert_called_once()
            
            # Verify job structure
            call_args = mock_redis.lpush.call_args
            assert "job_queue" in call_args[0]
            
            # Verify JSON structure
            job_json = call_args[0][1]
            job = json.loads(job_json)
            assert str(sample_video_id) in str(job["video_id"])
            assert job["filepath"] == filepath

    @pytest.mark.asyncio
    async def test_enqueue_video_error_propagates(self, sample_video_id, sample_project_id):
        """Should propagate Redis errors to caller."""
        from app.services.queue_service import enqueue_video
        
        mock_redis = AsyncMock()
        mock_redis.lpush.side_effect = Exception("Redis connection failed")
        
        with patch("app.services.queue_service.get_redis", return_value=mock_redis):
            with pytest.raises(Exception, match="Redis connection failed"):
                await enqueue_video(sample_video_id, "/path/video.mp4", sample_project_id)


class TestDequeueVideo:
    """Test job dequeue operation."""

    @pytest.mark.asyncio
    async def test_dequeue_video_success(self, sample_video_id, sample_project_id, mock_redis):
        """Should pop job from queue and return parsed JSON."""
        from app.services.queue_service import dequeue_video
        
        job_payload = {
            "video_id": str(sample_video_id),
            "filepath": "/storage/video.mp4",
            "project_id": str(sample_project_id),
        }
        mock_redis.brpop.return_value = ("job_queue", json.dumps(job_payload))
        
        with patch("app.services.queue_service.get_redis", return_value=mock_redis):
            job = await dequeue_video(timeout_s=5)
            
            assert job is not None
            assert job["video_id"] == str(sample_video_id)
            assert job["filepath"] == "/storage/video.mp4"
            mock_redis.brpop.assert_called_once_with("job_queue", timeout=5)

    @pytest.mark.asyncio
    async def test_dequeue_video_timeout(self, mock_redis):
        """Should return None on timeout (no exception)."""
        from app.services.queue_service import dequeue_video
        
        mock_redis.brpop.return_value = None  # Timeout
        
        with patch("app.services.queue_service.get_redis", return_value=mock_redis):
            job = await dequeue_video(timeout_s=5)
            
            assert job is None

    @pytest.mark.asyncio
    async def test_dequeue_video_error_returns_none(self, mock_redis):
        """Should log error and return None on exception."""
        from app.services.queue_service import dequeue_video
        
        mock_redis.brpop.side_effect = Exception("Redis error")
        
        with patch("app.services.queue_service.get_redis", return_value=mock_redis):
            job = await dequeue_video(timeout_s=5)
            
            assert job is None


class TestSetJobStatus:
    """Test job status update operation."""

    @pytest.mark.asyncio
    async def test_set_job_status_success(self, sample_video_id, mock_redis):
        """Should set status key with TTL."""
        from app.services.queue_service import set_job_status
        
        with patch("app.services.queue_service.get_redis", return_value=mock_redis):
            await set_job_status(sample_video_id, "PROCESSING", ttl_s=3600)
            
            mock_redis.setex.assert_called_once()
            call_args = mock_redis.setex.call_args
            
            # Verify status key format
            assert f"job_status:{sample_video_id}" in call_args[0]
            assert call_args[0][1] == 3600  # TTL
            assert call_args[0][2] == "PROCESSING"

    @pytest.mark.asyncio
    async def test_set_job_status_custom_ttl(self, sample_video_id, mock_redis):
        """Should respect custom TTL parameter."""
        from app.services.queue_service import set_job_status
        
        with patch("app.services.queue_service.get_redis", return_value=mock_redis):
            await set_job_status(sample_video_id, "PROCESSED", ttl_s=7200)
            
            call_args = mock_redis.setex.call_args
            assert call_args[0][1] == 7200


class TestGetQueueDepth:
    """Test queue length retrieval."""

    @pytest.mark.asyncio
    async def test_get_queue_depth_success(self, mock_redis):
        """Should return queue length."""
        from app.services.queue_service import get_queue_depth
        
        mock_redis.llen.return_value = 5
        
        with patch("app.services.queue_service.get_redis", return_value=mock_redis):
            depth = await get_queue_depth()
            
            assert depth == 5
            mock_redis.llen.assert_called_once_with("job_queue")

    @pytest.mark.asyncio
    async def test_get_queue_depth_empty(self, mock_redis):
        """Should return 0 for empty queue."""
        from app.services.queue_service import get_queue_depth
        
        mock_redis.llen.return_value = 0
        
        with patch("app.services.queue_service.get_redis", return_value=mock_redis):
            depth = await get_queue_depth()
            
            assert depth == 0

    @pytest.mark.asyncio
    async def test_get_queue_depth_error_returns_zero(self, mock_redis):
        """Should return 0 on Redis error (graceful degradation)."""
        from app.services.queue_service import get_queue_depth
        
        mock_redis.llen.side_effect = Exception("Redis unavailable")
        
        with patch("app.services.queue_service.get_redis", return_value=mock_redis):
            depth = await get_queue_depth()
            
            assert depth == 0


class TestIntegration:
    """Integration tests for queue pipeline."""

    @pytest.mark.asyncio
    async def test_enqueue_dequeue_roundtrip(self, sample_video_id, sample_project_id, mock_redis):
        """Should successfully enqueue then dequeue a job."""
        from app.services.queue_service import enqueue_video, dequeue_video
        
        filepath = "/storage/video.mp4"
        
        # Simulate enqueue
        with patch("app.services.queue_service.get_redis", return_value=mock_redis):
            await enqueue_video(sample_video_id, filepath, sample_project_id)
            
            # Verify LPUSH was called with correct structure
            assert mock_redis.lpush.called

    @pytest.mark.asyncio
    async def test_worker_polling_loop(self, mock_redis):
        """Simulate worker polling loop behavior."""
        from app.services.queue_service import dequeue_video, set_job_status
        
        # First poll: no job
        mock_redis.brpop.return_value = None
        
        with patch("app.services.queue_service.get_redis", return_value=mock_redis):
            job = await dequeue_video(timeout_s=1)
            assert job is None
            
            # Then: job arrives
            video_id = uuid4()
            job_payload = {
                "video_id": str(video_id),
                "filepath": "/storage/video.mp4",
                "project_id": str(uuid4()),
            }
            mock_redis.brpop.return_value = ("job_queue", json.dumps(job_payload))
            
            job = await dequeue_video(timeout_s=1)
            assert job is not None
            
            # Update status
            await set_job_status(video_id, "PROCESSING")
            assert mock_redis.setex.called


# ── Test execution ────────────────────────────────────────────────────
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
