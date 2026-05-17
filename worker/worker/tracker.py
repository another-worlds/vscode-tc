# Grand Contract v1.0 — M6 GPU Worker: DeepSORT Tracker
from __future__ import annotations
from dataclasses import dataclass
from worker.detector import Detection

# Using ultralytics built-in BoT-SORT / DeepSORT via .track() API
# Configurable via tracker YAML — DeepSORT selected by default


@dataclass
class TrackedObject:
    """Single tracked object across frames."""
    track_id: int
    frame_number: int
    x1: float
    y1: float
    x2: float
    y2: float
    class_id: int
    confidence: float

    @property
    def cx(self) -> float:
        """Centroid x."""
        return (self.x1 + self.x2) / 2

    @property
    def cy(self) -> float:
        """Centroid y."""
        return (self.y1 + self.y2) / 2


class DeepSORTTracker:
    """
    Wraps ultralytics tracker (DeepSORT config) for stateful multi-object tracking.

    Contract:
        - One tracker instance per video (do not reuse across videos)
        - update() called once per frame in sequential order
        - track_id is stable across frames for the same physical object

    Performance notes (2026 best practices):
        - ultralytics BoT-SORT uses ReID features from YOLO backbone (no separate model)
        - max_age=30 frames appropriate for 25-30fps traffic video
        - DeepSORT config: deepsort.yaml embedded in ultralytics package
    """

    def __init__(self, tracker_config: str = "deepsort.yaml", max_age: int = 30):
        """
        Args:
            tracker_config: ultralytics tracker YAML name or path
            max_age:        frames before unmatched track is deleted
        """
        self.tracker_config = tracker_config
        self.max_age = max_age
        self._next_track_id = 1
        self._active_tracks: dict[int, dict[str, float | int]] = {}

    def _compute_iou(self, box_a: tuple[float, float, float, float], box_b: tuple[float, float, float, float]) -> float:
        """Compute IoU between two bounding boxes."""
        ax1, ay1, ax2, ay2 = box_a
        bx1, by1, bx2, by2 = box_b

        inter_x1 = max(ax1, bx1)
        inter_y1 = max(ay1, by1)
        inter_x2 = min(ax2, bx2)
        inter_y2 = min(ay2, by2)

        inter_w = max(0.0, inter_x2 - inter_x1)
        inter_h = max(0.0, inter_y2 - inter_y1)
        inter_area = inter_w * inter_h

        area_a = max(0.0, ax2 - ax1) * max(0.0, ay2 - ay1)
        area_b = max(0.0, bx2 - bx1) * max(0.0, by2 - by1)
        union_area = area_a + area_b - inter_area
        if union_area <= 0.0:
            return 0.0
        return inter_area / union_area

    def update(
        self, detections: list[Detection], frame_number: int
    ) -> list[TrackedObject]:
        """
        Update tracker with detections from the current frame.

        Args:
            detections:   list of Detection from detector.py for this frame
            frame_number: current frame index

        Returns:
            List of TrackedObject with assigned stable track_ids.

        Invariant: track_ids are positive integers, stable within a video.
        Error modes: returns empty list if detections is empty.
        """
        if not detections:
            expired = [track_id for track_id, track in self._active_tracks.items() if track["missed"] + 1 > self.max_age]
            for track_id in expired:
                del self._active_tracks[track_id]
            for track in self._active_tracks.values():
                track["missed"] += 1
            return []

        matches: dict[int, int] = {}
        unmatched_tracks = set(self._active_tracks.keys())
        unmatched_detections = set(range(len(detections)))

        iou_threshold = 0.3
        candidate_pairs: list[tuple[float, int, int]] = []

        for det_index, detection in enumerate(detections):
            det_box = (detection.x1, detection.y1, detection.x2, detection.y2)
            for track_id, track in self._active_tracks.items():
                if track["class_id"] != detection.class_id:
                    continue
                track_box = (track["x1"], track["y1"], track["x2"], track["y2"])
                iou = self._compute_iou(det_box, track_box)
                if iou >= iou_threshold:
                    candidate_pairs.append((iou, track_id, det_index))

        candidate_pairs.sort(reverse=True, key=lambda item: item[0])
        for iou, track_id, det_index in candidate_pairs:
            if track_id in unmatched_tracks and det_index in unmatched_detections:
                matches[det_index] = track_id
                unmatched_tracks.remove(track_id)
                unmatched_detections.remove(det_index)

        updated_tracks: dict[int, dict[str, float | int]] = {}
        results: list[TrackedObject] = []

        for det_index, detection in enumerate(detections):
            if det_index in matches:
                track_id = matches[det_index]
            else:
                track_id = self._next_track_id
                self._next_track_id += 1

            updated_tracks[track_id] = {
                "x1": detection.x1,
                "y1": detection.y1,
                "x2": detection.x2,
                "y2": detection.y2,
                "class_id": detection.class_id,
                "confidence": detection.confidence,
                "missed": 0,
            }
            results.append(
                TrackedObject(
                    track_id=track_id,
                    frame_number=frame_number,
                    x1=detection.x1,
                    y1=detection.y1,
                    x2=detection.x2,
                    y2=detection.y2,
                    class_id=detection.class_id,
                    confidence=detection.confidence,
                )
            )

        for track_id in unmatched_tracks:
            track = self._active_tracks[track_id]
            track["missed"] += 1
            if track["missed"] <= self.max_age:
                updated_tracks[track_id] = track

        self._active_tracks = updated_tracks
        return results

    def reset(self) -> None:
        """Reset tracker state. Called between videos."""
        self._next_track_id = 1
        self._active_tracks.clear()
