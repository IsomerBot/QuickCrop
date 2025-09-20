import unittest
from types import SimpleNamespace

from services.detection import (
    compute_iou,
    find_best_overlapping_pair,
    relative_bbox_tuple,
    detection_score,
)


def make_detection(xmin: float, ymin: float, width: float, height: float, score: float):
    bbox = SimpleNamespace(xmin=xmin, ymin=ymin, width=width, height=height)
    location_data = SimpleNamespace(
        relative_bounding_box=bbox,
        relative_keypoints=[]
    )
    return SimpleNamespace(location_data=location_data, score=[score])


class TestDetectionHelpers(unittest.TestCase):
    def test_compute_iou_full_overlap(self):
        box_a = (0.1, 0.1, 0.3, 0.3)
        box_b = (0.1, 0.1, 0.3, 0.3)
        self.assertAlmostEqual(compute_iou(box_a, box_b), 1.0)

    def test_compute_iou_partial_overlap(self):
        box_a = (0.1, 0.1, 0.4, 0.4)
        box_b = (0.2, 0.2, 0.3, 0.3)
        iou = compute_iou(box_a, box_b)
        self.assertGreater(iou, 0.2)
        self.assertLess(iou, 1.0)

    def test_compute_iou_no_overlap(self):
        box_a = (0.1, 0.1, 0.2, 0.2)
        box_b = (0.5, 0.5, 0.2, 0.2)
        self.assertEqual(compute_iou(box_a, box_b), 0.0)

    def test_find_best_overlapping_pair_requires_threshold(self):
        primary = [make_detection(0.1, 0.1, 0.2, 0.2, 0.9)]
        secondary = [make_detection(0.5, 0.5, 0.2, 0.2, 0.8)]
        result = find_best_overlapping_pair(primary, secondary, min_iou=0.3)
        self.assertIsNone(result)

    def test_find_best_overlapping_pair_selects_highest_score(self):
        primary = [
            make_detection(0.1, 0.1, 0.2, 0.2, 0.6),
            make_detection(0.2, 0.2, 0.3, 0.3, 0.9)
        ]
        secondary = [
            make_detection(0.21, 0.21, 0.28, 0.28, 0.85),
            make_detection(0.6, 0.6, 0.2, 0.2, 0.95)
        ]
        match = find_best_overlapping_pair(primary, secondary, min_iou=0.3)
        self.assertIsNotNone(match)
        first, second = match
        self.assertAlmostEqual(detection_score(first), 0.9)
        self.assertAlmostEqual(detection_score(second), 0.85)

    def test_relative_bbox_tuple(self):
        detection = make_detection(0.05, 0.05, 0.4, 0.4, 0.7)
        self.assertEqual(relative_bbox_tuple(detection), (0.05, 0.05, 0.4, 0.4))


if __name__ == '__main__':
    unittest.main()
