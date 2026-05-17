from worker.detector import Detection
from worker.tracker import DeepSORTTracker


def test_tracker_assigns_stable_track_ids():
    tracker = DeepSORTTracker(max_age=5)

    detections_frame_0 = [
        Detection(x1=10, y1=10, x2=50, y2=50, confidence=0.9, class_id=2, frame_number=0),
        Detection(x1=100, y1=100, x2=150, y2=150, confidence=0.8, class_id=2, frame_number=0),
    ]
    tracked_frame_0 = tracker.update(detections_frame_0, frame_number=0)
    assert len(tracked_frame_0) == 2
    ids_frame_0 = {obj.track_id for obj in tracked_frame_0}
    assert ids_frame_0 == {1, 2}

    detections_frame_1 = [
        Detection(x1=12, y1=12, x2=52, y2=52, confidence=0.92, class_id=2, frame_number=1),
        Detection(x1=102, y1=102, x2=152, y2=152, confidence=0.85, class_id=2, frame_number=1),
    ]
    tracked_frame_1 = tracker.update(detections_frame_1, frame_number=1)
    assert len(tracked_frame_1) == 2
    ids_frame_1 = [obj.track_id for obj in tracked_frame_1]
    assert set(ids_frame_1) == ids_frame_0
    assert tracked_frame_1[0].track_id == 1
    assert tracked_frame_1[1].track_id == 2


def test_tracker_creates_new_track_for_new_object():
    tracker = DeepSORTTracker(max_age=5)

    initial = [
        Detection(x1=0, y1=0, x2=50, y2=50, confidence=0.9, class_id=2, frame_number=0),
    ]
    tracked_initial = tracker.update(initial, frame_number=0)
    assert tracked_initial[0].track_id == 1

    new_object = [
        Detection(x1=0, y1=0, x2=50, y2=50, confidence=0.9, class_id=2, frame_number=1),
        Detection(x1=200, y1=200, x2=240, y2=240, confidence=0.85, class_id=2, frame_number=1),
    ]
    tracked_next = tracker.update(new_object, frame_number=1)
    assert {obj.track_id for obj in tracked_next} == {1, 2}


def test_tracker_reset_clears_state():
    tracker = DeepSORTTracker(max_age=5)
    tracked = tracker.update([
        Detection(x1=0, y1=0, x2=50, y2=50, confidence=0.9, class_id=2, frame_number=0)
    ], frame_number=0)
    assert tracked[0].track_id == 1

    tracker.reset()
    tracked_after_reset = tracker.update([
        Detection(x1=0, y1=0, x2=50, y2=50, confidence=0.9, class_id=2, frame_number=1)
    ], frame_number=1)
    assert tracked_after_reset[0].track_id == 1
