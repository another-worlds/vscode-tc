from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from worker.detector import Detection, detect_frame, detect_video_stream


class DummyBoxes:
    def __init__(self, data):
        self.data = data


class DummyResult:
    def __init__(self, boxes):
        self.boxes = boxes


class DummyModel:
    def __init__(self, result):
        self._result = result

    def __call__(self, frame, **kwargs):
        return [self._result]


def test_detect_frame_filters_non_vehicle_classes():
    mock_data = np.array([
        [10.0, 20.0, 30.0, 40.0, 0.9, 2],
        [15.0, 25.0, 35.0, 45.0, 0.8, 1],
    ], dtype=np.float32)
    model = DummyModel(DummyResult(DummyBoxes(mock_data)))

    detections = detect_frame(model, np.zeros((480, 640, 3), dtype=np.uint8), 0)

    assert len(detections) == 1
    assert detections[0].class_id == 2
    assert detections[0].confidence == pytest.approx(0.9)


def test_detect_frame_returns_empty_on_inference_error():
    class BrokenModel:
        def __call__(self, *args, **kwargs):
            raise RuntimeError("inference failure")

    detections = detect_frame(BrokenModel(), np.zeros((480, 640, 3), dtype=np.uint8), 0)
    assert detections == []


@patch("worker.detector.cv2.VideoCapture")
def test_detect_video_stream_reads_frames(mock_capture):
    mock_cap = MagicMock()
    mock_cap.isOpened.return_value = True
    mock_cap.read.side_effect = [
        (True, np.zeros((480, 640, 3), dtype=np.uint8)),
        (False, None),
    ]
    mock_capture.return_value = mock_cap

    model = DummyModel(DummyResult(DummyBoxes(np.empty((0, 6), dtype=np.float32))))
    generator = detect_video_stream(model, "/tmp/video.mp4", total_frames=1)

    frames = list(generator)
    assert frames == [(0, [])]
