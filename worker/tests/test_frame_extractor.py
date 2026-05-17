import numpy as np
import pytest

from worker.frame_extractor import extract_frames, get_frame_indices


class DummyCapture:
    def __init__(self, frame_count, frames):
        self._frame_count = frame_count
        self._frames = frames
        self._current_index = 0
        self.called_positions = []

    def isOpened(self):
        return True

    def get(self, prop_id):
        if prop_id == 7:  # cv2.CAP_PROP_FRAME_COUNT
            return float(self._frame_count)
        return 0.0

    def set(self, prop_id, value):
        self._current_index = int(value)
        self.called_positions.append(self._current_index)
        return True

    def read(self):
        if self._current_index >= len(self._frames):
            return False, None
        frame = self._frames[self._current_index]
        self._current_index += 1
        return True, frame

    def release(self):
        pass


def test_get_frame_indices_zero_frames():
    assert get_frame_indices(0, 10) == []


def test_get_frame_indices_equal_or_less():
    assert get_frame_indices(5, 10) == [0, 1, 2, 3, 4]


def test_get_frame_indices_uniform_spread():
    indices = get_frame_indices(10, 4)
    assert indices == [0, 3, 6, 9]


def test_extract_frames_writes_selected_jpegs(monkeypatch, tmp_path):
    from worker.frame_extractor import cv2

    frames = [np.zeros((100, 100, 3), dtype=np.uint8) for _ in range(5)]
    capture = DummyCapture(frame_count=5, frames=frames)
    monkeypatch.setattr(cv2, "VideoCapture", lambda path: capture)
    monkeypatch.setattr(cv2, "imencode", lambda ext, frame, params: (True, np.ones((10,), dtype=np.uint8)))

    output_dir = tmp_path / "frames"
    paths = extract_frames("/tmp/video.mp4", output_dir, sample_count=3, jpeg_quality=75)

    assert len(paths) == 3
    assert all(path.exists() for path in paths)
    assert paths[0].name.endswith(".jpg")


def test_extract_frames_skips_invalid_frames(monkeypatch, tmp_path):
    from worker.frame_extractor import cv2

    frames = [np.zeros((100, 100, 3), dtype=np.uint8) for _ in range(5)]
    capture = DummyCapture(frame_count=5, frames=frames)
    monkeypatch.setattr(cv2, "VideoCapture", lambda path: capture)

    def failed_imencode(ext, frame, params):
        return (False, None)

    monkeypatch.setattr(cv2, "imencode", failed_imencode)

    output_dir = tmp_path / "frames"
    paths = extract_frames("/tmp/video.mp4", output_dir, sample_count=3, jpeg_quality=75)

    assert paths == []
