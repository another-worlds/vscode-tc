import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from worker.trajectory_writer import TrajectoryWriter
from worker.tracker import TrackedObject


@pytest.fixture
def tmp_parquet_dir(tmp_path):
    return tmp_path / "parquet"


def make_tracked_object(track_id: int, frame_number: int) -> TrackedObject:
    return TrackedObject(
        track_id=track_id,
        frame_number=frame_number,
        x1=10.0,
        y1=20.0,
        x2=30.0,
        y2=40.0,
        class_id=2,
        confidence=0.95,
    )


def test_append_and_flush_writes_parquet(tmp_parquet_dir):
    writer = TrajectoryWriter(video_id="00000000-0000-0000-0000-000000000001", parquet_dir=str(tmp_parquet_dir))

    writer.append([make_tracked_object(1, 0), make_tracked_object(2, 0)])
    output_path = writer.flush()

    assert output_path.exists()
    assert str(output_path).endswith(".parquet")
    assert writer.output_path == output_path

    # Second flush after empty buffer returns same path and does not error
    second_path = writer.flush()
    assert second_path == output_path


def test_output_path_before_flush_raises(tmp_parquet_dir):
    writer = TrajectoryWriter(video_id="00000000-0000-0000-0000-000000000002", parquet_dir=str(tmp_parquet_dir))

    with pytest.raises(ValueError):
        _ = writer.output_path


def test_flush_empty_buffer_creates_path(tmp_parquet_dir):
    writer = TrajectoryWriter(video_id="00000000-0000-0000-0000-000000000003", parquet_dir=str(tmp_parquet_dir))
    output_path = writer.flush()

    assert output_path.exists() is False
    assert writer.output_path == output_path
