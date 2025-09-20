"""
Computer Vision detection service using MediaPipe
"""

import mediapipe as mp
import os
import numpy as np
from typing import Optional, List, Tuple, Dict, Any, Iterable
from dataclasses import dataclass
import cv2
from PIL import Image

from core.config import settings

# Optional: MediaPipe Tasks for object detection
try:
    from mediapipe.tasks import python as mp_python_tasks
    from mediapipe.tasks.python import vision as mp_vision_tasks
    _MP_TASKS_AVAILABLE = True
except Exception:
    _MP_TASKS_AVAILABLE = False


@dataclass
class FaceDetection:
    """Face detection result"""
    bbox: Tuple[float, float, float, float]  # x, y, width, height (normalized)
    confidence: float
    keypoints: Optional[Dict[str, Tuple[float, float]]] = None  # Eye, nose positions


@dataclass
class PoseDetection:
    """Pose detection result"""
    landmarks: List[Tuple[float, float, float]]  # x, y, z coordinates
    confidence: float
    torso_center: Optional[Tuple[float, float]] = None
    shoulder_width: Optional[float] = None


@dataclass
class DetectionResult:
    """Combined detection result"""
    face: Optional[FaceDetection] = None
    pose: Optional[PoseDetection] = None
    image_width: int = 0
    image_height: int = 0
    success: bool = False
    fallback_used: bool = False


def detection_score(detection: Any) -> float:
    """Return the confidence score for a MediaPipe detection."""
    score = getattr(detection, 'score', None)
    if isinstance(score, (list, tuple)) and score:
        return float(score[0])
    if isinstance(score, (np.ndarray,)) and score.size:
        return float(score[0])
    try:
        return float(score)
    except (TypeError, ValueError):
        return 0.0


def relative_bbox_tuple(detection: Any) -> Tuple[float, float, float, float]:
    """Extract (xmin, ymin, width, height) from a detection's relative bounding box."""
    bbox = detection.location_data.relative_bounding_box
    return (bbox.xmin, bbox.ymin, bbox.width, bbox.height)


def average_bounding_boxes(*boxes: Tuple[float, float, float, float]) -> Tuple[float, float, float, float]:
    """Average multiple bounding boxes (element-wise)."""
    if not boxes:
        raise ValueError("At least one bounding box required")
    sums = [0.0, 0.0, 0.0, 0.0]
    for box in boxes:
        for idx, value in enumerate(box):
            sums[idx] += value
    count = float(len(boxes))
    return tuple(value / count for value in sums)


def compute_iou(box_a: Tuple[float, float, float, float],
                box_b: Tuple[float, float, float, float]) -> float:
    """Compute IoU between two relative bounding boxes."""
    ax, ay, aw, ah = box_a
    bx, by, bw, bh = box_b

    a_x2, a_y2 = ax + aw, ay + ah
    b_x2, b_y2 = bx + bw, by + bh

    inter_x1 = max(ax, bx)
    inter_y1 = max(ay, by)
    inter_x2 = min(a_x2, b_x2)
    inter_y2 = min(a_y2, b_y2)

    inter_w = max(0.0, inter_x2 - inter_x1)
    inter_h = max(0.0, inter_y2 - inter_y1)
    inter_area = inter_w * inter_h

    area_a = max(0.0, aw) * max(0.0, ah)
    area_b = max(0.0, bw) * max(0.0, bh)

    denom = area_a + area_b - inter_area
    if denom <= 0.0:
        return 0.0
    return inter_area / denom


def extract_keypoints(detection: Any) -> Dict[str, Tuple[float, float]]:
    """Pull eye/nose keypoints from a MediaPipe detection, if available."""
    location_data = getattr(detection, 'location_data', None)
    if not location_data:
        return {}
    relative_keypoints = getattr(location_data, 'relative_keypoints', None)
    if not relative_keypoints:
        return {}

    keypoints: Dict[str, Tuple[float, float]] = {}
    for idx, kp in enumerate(relative_keypoints):
        if idx == 0:
            keypoints['left_eye'] = (kp.x, kp.y)
        elif idx == 1:
            keypoints['right_eye'] = (kp.x, kp.y)
        elif idx == 2:
            keypoints['nose'] = (kp.x, kp.y)
    return keypoints


def iter_overlapping_pairs(
    primary: Iterable[Any],
    secondary: Iterable[Any],
    min_iou: float
) -> Iterable[Tuple[Any, Any, float]]:
    """Yield detection pairs whose IoU meets the threshold along with average score."""
    for det_primary in primary:
        primary_bbox = relative_bbox_tuple(det_primary)
        primary_score = detection_score(det_primary)

        for det_secondary in secondary:
            secondary_bbox = relative_bbox_tuple(det_secondary)
            iou = compute_iou(primary_bbox, secondary_bbox)

            if iou < min_iou:
                continue

            avg_score = (primary_score + detection_score(det_secondary)) / 2.0
            yield det_primary, det_secondary, avg_score


def find_unique_best_pair(
    primary: Iterable[Any],
    secondary: Iterable[Any],
    min_iou: float
) -> Optional[Tuple[Any, Any]]:
    """Return the highest scoring pair only when exactly one overlapping match exists."""
    best_pair: Optional[Tuple[Any, Any]] = None
    best_score = float('-inf')
    matches = 0

    for det_primary, det_secondary, avg_score in iter_overlapping_pairs(primary, secondary, min_iou):
        matches += 1
        if avg_score > best_score:
            best_score = avg_score
            best_pair = (det_primary, det_secondary)

    if matches == 1:
        return best_pair
    return None


class DetectionService:
    """Service for face and pose detection using MediaPipe"""
    
    def __init__(self):
        # Initialize MediaPipe Face Detection (short and full range)
        self.mp_face_detection = mp.solutions.face_detection
        self.face_detection_short = self.mp_face_detection.FaceDetection(
            min_detection_confidence=settings.MIN_DETECTION_CONFIDENCE,
            model_selection=0
        )
        self.face_detection_full = self.mp_face_detection.FaceDetection(
            min_detection_confidence=settings.MIN_DETECTION_CONFIDENCE,
            model_selection=1
        )
        
        # Initialize MediaPipe Pose Detection
        self.mp_pose = mp.solutions.pose
        self.pose_detection = self.mp_pose.Pose(
            static_image_mode=True,
            model_complexity=1,
            min_detection_confidence=settings.MIN_DETECTION_CONFIDENCE,
            min_tracking_confidence=settings.MIN_TRACKING_CONFIDENCE
        )
        
        # Pose landmark indices
        self.POSE_LANDMARKS = {
            'nose': 0,
            'left_shoulder': 11,
            'right_shoulder': 12,
            'left_hip': 23,
            'right_hip': 24,
        }

        # Initialize Object Detector (if tasks available and model exists)
        self.object_detector = None
        if _MP_TASKS_AVAILABLE:
            model_path = os.environ.get('MP_OBJECT_MODEL', 'models/efficientdet_lite0.tflite')
            try:
                if os.path.exists(model_path):
                    base = mp_python_tasks.BaseOptions(model_asset_path=model_path)
                    options = mp_vision_tasks.ObjectDetectorOptions(
                        base_options=base,
                        score_threshold=0.3,
                        max_results=5,
                    )
                    self.object_detector = mp_vision_tasks.ObjectDetector.create_from_options(options)
            except Exception:
                self.object_detector = None
    
    def detect_face(self, image: np.ndarray) -> Optional[FaceDetection]:
        """
        Detect face in image using MediaPipe
        Returns the most prominent face if multiple detected
        """
        # Convert BGR to RGB if needed
        if len(image.shape) == 3 and image.shape[2] == 3:
            rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        else:
            rgb_image = image
        
        # Process with MediaPipe short- and full-range models
        short_results = self.face_detection_short.process(rgb_image)
        full_results = self.face_detection_full.process(rgb_image)

        if not short_results.detections or not full_results.detections:
            return None

        match = find_unique_best_pair(
            short_results.detections,
            full_results.detections,
            min_iou=settings.FACE_MATCH_IOU_THRESHOLD
        )

        if not match:
            return None

        short_det, full_det = match
        short_bbox = relative_bbox_tuple(short_det)
        full_bbox = relative_bbox_tuple(full_det)

        combined_bbox = average_bounding_boxes(short_bbox, full_bbox)

        short_score = detection_score(short_det)
        full_score = detection_score(full_det)
        confidence = min(short_score, full_score)

        best_det = short_det if short_score >= full_score else full_det
        keypoints = extract_keypoints(best_det)

        return FaceDetection(
            bbox=combined_bbox,
            confidence=confidence,
            keypoints=keypoints if keypoints else None
        )
    
    def detect_pose(self, image: np.ndarray) -> Optional[PoseDetection]:
        """
        Detect pose landmarks in image using MediaPipe
        Focuses on upper body for cropping purposes
        """
        # Convert BGR to RGB if needed
        if len(image.shape) == 3 and image.shape[2] == 3:
            rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        else:
            rgb_image = image
        
        # Process with MediaPipe
        results = self.pose_detection.process(rgb_image)
        
        if not results.pose_landmarks:
            return None
        
        # Extract landmarks
        landmarks = []
        for landmark in results.pose_landmarks.landmark:
            landmarks.append((landmark.x, landmark.y, landmark.z))
        
        # Calculate confidence (average visibility of key points)
        key_landmarks = [
            results.pose_landmarks.landmark[self.POSE_LANDMARKS['left_shoulder']],
            results.pose_landmarks.landmark[self.POSE_LANDMARKS['right_shoulder']],
        ]
        confidence = sum(lm.visibility for lm in key_landmarks) / len(key_landmarks)
        
        # Calculate torso center
        left_shoulder = landmarks[self.POSE_LANDMARKS['left_shoulder']]
        right_shoulder = landmarks[self.POSE_LANDMARKS['right_shoulder']]
        left_hip = landmarks[self.POSE_LANDMARKS['left_hip']]
        right_hip = landmarks[self.POSE_LANDMARKS['right_hip']]
        
        torso_center = (
            (left_shoulder[0] + right_shoulder[0] + left_hip[0] + right_hip[0]) / 4,
            (left_shoulder[1] + right_shoulder[1] + left_hip[1] + right_hip[1]) / 4
        )
        
        # Calculate shoulder width
        shoulder_width = abs(right_shoulder[0] - left_shoulder[0])
        
        return PoseDetection(
            landmarks=landmarks,
            confidence=confidence,
            torso_center=torso_center,
            shoulder_width=shoulder_width
        )
    
    def detect(self, image: np.ndarray) -> DetectionResult:
        """
        Perform complete detection pipeline on image
        """
        height, width = image.shape[:2]
        
        # Detect face
        face_detection = self.detect_face(image)
        
        # Detect pose
        pose_detection = self.detect_pose(image)
        
        # Determine success
        success = face_detection is not None or pose_detection is not None
        fallback_used = not success
        
        return DetectionResult(
            face=face_detection,
            pose=pose_detection,
            image_width=width,
            image_height=height,
            success=success,
            fallback_used=fallback_used
        )

    def detect_objects(self, image: np.ndarray):
        """Run object detection; returns list of dicts with bbox and score (pixel coordinates)."""
        if self.object_detector is None:
            return []
        # Ensure RGB format
        if len(image.shape) == 3 and image.shape[2] == 3:
            rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        else:
            rgb_image = image
        mp_image = mp_vision_tasks.Image(image_format=mp_vision_tasks.ImageFormat.SRGB, data=rgb_image)
        result = self.object_detector.detect(mp_image)
        detections = []
        for det in getattr(result, 'detections', []) or []:
            bbox = det.bounding_box
            category = det.categories[0] if det.categories else None
            detections.append({
                'x': int(bbox.origin_x),
                'y': int(bbox.origin_y),
                'width': int(bbox.width),
                'height': int(bbox.height),
                'score': float(category.score) if category else 0.0,
                'category': category.category_name if category else 'object',
            })
        return detections

    def best_object_roi(self, image: np.ndarray):
        """Choose the most relevant object ROI (largest area; tiebreak by score)."""
        detections = self.detect_objects(image)
        if not detections:
            return None
        detections.sort(key=lambda d: (d['width'] * d['height'], d['score']))
        return detections[-1]
    
    def get_crop_region(self, 
                       detection: DetectionResult, 
                       aspect_ratio: Tuple[int, int],
                       padding_percent: float = 0.2,
                       focus_area: str = 'face') -> Tuple[int, int, int, int]:
        """
        Calculate crop region based on detection results
        Returns: (x, y, width, height) in pixel coordinates
        """
        img_width = detection.image_width
        img_height = detection.image_height
        target_aspect = aspect_ratio[0] / aspect_ratio[1]
        
        # Use face detection if available and requested
        if focus_area == 'face' and detection.face:
            # Convert normalized coordinates to pixels
            face_bbox = detection.face.bbox
            cx = (face_bbox[0] + face_bbox[2] / 2) * img_width
            cy = (face_bbox[1] + face_bbox[3] / 2) * img_height
            
            # Add padding
            face_width = face_bbox[2] * img_width * (1 + padding_percent)
            face_height = face_bbox[3] * img_height * (1 + padding_percent)
            
        # Use pose detection for torso focus
        elif focus_area == 'torso' and detection.pose and detection.pose.torso_center:
            cx = detection.pose.torso_center[0] * img_width
            cy = detection.pose.torso_center[1] * img_height
            
            # Use shoulder width as reference
            if detection.pose.shoulder_width:
                reference_size = detection.pose.shoulder_width * img_width * 2
            else:
                reference_size = min(img_width, img_height) * 0.5
                
            face_width = reference_size * (1 + padding_percent)
            face_height = reference_size * (1 + padding_percent)
            
        # Fallback to center crop
        else:
            cx = img_width / 2
            cy = img_height / 2
            face_width = min(img_width, img_height) * 0.5
            face_height = face_width
        
        # Calculate crop dimensions based on aspect ratio
        current_aspect = img_width / img_height
        
        if target_aspect > current_aspect:
            # Wider crop needed
            crop_width = min(img_width, face_width * 2)
            crop_height = crop_width / target_aspect
        else:
            # Taller crop needed
            crop_height = min(img_height, face_height * 2)
            crop_width = crop_height * target_aspect
        
        # Ensure crop doesn't exceed image bounds
        crop_width = min(crop_width, img_width)
        crop_height = min(crop_height, img_height)
        
        # Calculate crop position
        x = max(0, min(cx - crop_width / 2, img_width - crop_width))
        y = max(0, min(cy - crop_height / 2, img_height - crop_height))
        
        return (int(x), int(y), int(crop_width), int(crop_height))
    
    def __del__(self):
        """Cleanup MediaPipe resources"""
        for attr in ('face_detection_short', 'face_detection_full'):
            if hasattr(self, attr):
                getattr(self, attr).close()
        if hasattr(self, 'pose_detection'):
            self.pose_detection.close()


# Singleton instance
detection_service = DetectionService()
