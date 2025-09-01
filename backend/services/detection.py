"""
Computer Vision detection service using MediaPipe
"""

import mediapipe as mp
import numpy as np
from typing import Optional, List, Tuple, Dict, Any
from dataclasses import dataclass
import cv2
from PIL import Image

from core.config import settings


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


class DetectionService:
    """Service for face and pose detection using MediaPipe"""
    
    def __init__(self):
        # Initialize MediaPipe Face Detection
        self.mp_face_detection = mp.solutions.face_detection
        self.face_detection = self.mp_face_detection.FaceDetection(
            min_detection_confidence=settings.MIN_DETECTION_CONFIDENCE
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
        
        # Process with MediaPipe
        results = self.face_detection.process(rgb_image)
        
        if not results.detections:
            return None
        
        # Get the detection with highest confidence
        best_detection = max(results.detections, 
                           key=lambda d: d.score[0])
        
        # Extract bounding box
        bbox = best_detection.location_data.relative_bounding_box
        confidence = best_detection.score[0]
        
        # Extract keypoints if available
        keypoints = {}
        if best_detection.location_data.relative_keypoints:
            for idx, kp in enumerate(best_detection.location_data.relative_keypoints):
                if idx == 0:  # Left eye
                    keypoints['left_eye'] = (kp.x, kp.y)
                elif idx == 1:  # Right eye
                    keypoints['right_eye'] = (kp.x, kp.y)
                elif idx == 2:  # Nose tip
                    keypoints['nose'] = (kp.x, kp.y)
        
        return FaceDetection(
            bbox=(bbox.xmin, bbox.ymin, bbox.width, bbox.height),
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
        if hasattr(self, 'face_detection'):
            self.face_detection.close()
        if hasattr(self, 'pose_detection'):
            self.pose_detection.close()


# Singleton instance
detection_service = DetectionService()