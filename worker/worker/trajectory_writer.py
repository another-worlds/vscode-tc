# Grand Contract v1.0 — M6 GPU Worker: Trajectory Parquet Writer
from __future__ import annotations
from pathlib import Path
from uuid import UUID
import pyarrow as pa
import pyarrow.parquet as pq
from worker.tracker import TrackedObject

# Parquet schema — raw bounding box + centroid per frame per track
TRAJECTORY_SCHEMA = pa.schema([
    pa.field("track_id",     pa.int32()),
    pa.field("frame_no",     pa.int32()),
    pa.field("x1",           pa.float32()),
    pa.field("y1",           pa.float32()),
    pa.field("x2",           pa.float32()),
    pa.field("y2",           pa.float32()),
    pa.field("cx",           pa.float32()),   # centroid x
    pa.field("cy",           pa.float32()),   # centroid y
    pa.field("class_id",     pa.int8()),
    pa.field("confidence",   pa.float32()),
])


class TrajectoryWriter:
    """
    Buffered writer for trajectory data → Parquet file.

    Contract:
        - One instance per video processing job
        - append() called once per frame with all tracked objects
        - flush() called at end to write final Parquet file

    Performance notes:
        - Buffers rows in memory (list of dicts) until flush
        - For very long videos (>1h @ 30fps = 108k frames), consider
          incremental write with row group size = 10k frames
    """

    def __init__(self, video_id: UUID, parquet_dir: str):
        """
        Args:
            video_id:    used to construct output filename
            parquet_dir: base directory for parquet files (PARQUET_DIR)
        """
        self.video_id = video_id
        self.parquet_dir = Path(parquet_dir)
        self.parquet_dir.mkdir(parents=True, exist_ok=True)
        self._buffer: list[dict[str, int | float]] = []
        self._flushed_path: Path | None = None

    def append(self, tracked_objects: list[TrackedObject]) -> None:
        """
        Buffer tracked objects from one frame.

        Args:
            tracked_objects: list from DeepSORTTracker.update()

        Side-effects: appends to internal buffer (no I/O until flush)
        """
        for obj in tracked_objects:
            self._buffer.append({
                "track_id": int(obj.track_id),
                "frame_no": int(obj.frame_number),
                "x1": float(obj.x1),
                "y1": float(obj.y1),
                "x2": float(obj.x2),
                "y2": float(obj.y2),
                "cx": float(obj.cx),
                "cy": float(obj.cy),
                "class_id": int(obj.class_id),
                "confidence": float(obj.confidence),
            })

    def flush(self) -> Path:
        """
        Write all buffered rows to Parquet file using TRAJECTORY_SCHEMA.

        Returns:
            Path to written parquet file.

        Side-effects:
            - Creates PARQUET_DIR/{video_id}.parquet
            - Clears internal buffer

        Error modes:
            - Raises IOError if directory not writable
            - Returns existing path if buffer is empty (no-op)

        Compression: snappy (good balance of size/speed for numeric data)
        """
        output_path = self.parquet_dir / f"{self.video_id}.parquet"
        self._flushed_path = output_path

        if not self._buffer:
            return output_path

        try:
            table = pa.Table.from_pylist(self._buffer, schema=TRAJECTORY_SCHEMA)
            pq.write_table(table, output_path, compression="snappy")
        except Exception as exc:
            raise IOError(f"Unable to write Parquet file to {output_path}: {exc}") from exc
        finally:
            self._buffer.clear()

        return output_path

    @property
    def output_path(self) -> Path:
        """Expected output path. Valid after flush()."""
        if self._flushed_path is None:
            raise ValueError("TrajectoryWriter output path is not available until flush() is called")
        return self._flushed_path
