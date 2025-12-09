"""
Gesture detection module for hand tracking.
Detects various hand gestures based on MediaPipe landmarks.
"""
import math
from typing import List, Tuple, Optional
import numpy as np


class GestureDetector:
    """Detects hand gestures from MediaPipe landmarks."""
    
    # MediaPipe hand landmark indices
    WRIST = 0
    THUMB_CMC = 1
    THUMB_MCP = 2
    THUMB_IP = 3
    THUMB_TIP = 4
    INDEX_FINGER_MCP = 5
    INDEX_FINGER_PIP = 6
    INDEX_FINGER_DIP = 7
    INDEX_FINGER_TIP = 8
    MIDDLE_FINGER_MCP = 9
    MIDDLE_FINGER_PIP = 10
    MIDDLE_FINGER_DIP = 11
    MIDDLE_FINGER_TIP = 12
    RING_FINGER_MCP = 13
    RING_FINGER_PIP = 14
    RING_FINGER_DIP = 15
    RING_FINGER_TIP = 16
    PINKY_MCP = 17
    PINKY_PIP = 18
    PINKY_DIP = 19
    PINKY_TIP = 20
    
    def __init__(self, pinch_threshold: float = 0.05, finger_extended_threshold: float = 0.6):
        """
        Initialize gesture detector.
        
        Args:
            pinch_threshold: Distance threshold for pinch detection
            finger_extended_threshold: Ratio threshold for finger extension detection
        """
        self.pinch_threshold = pinch_threshold
        self.finger_extended_threshold = finger_extended_threshold
    
    @staticmethod
    def calculate_distance(point1: Tuple[float, float, float], 
                          point2: Tuple[float, float, float]) -> float:
        """Calculate Euclidean distance between two 3D points."""
        return math.sqrt(
            (point1[0] - point2[0]) ** 2 +
            (point1[1] - point2[1]) ** 2 +
            (point1[2] - point2[2]) ** 2
        )
    
    def is_finger_extended(self, landmarks: List[Tuple[float, float, float]], 
                          finger_name: str) -> bool:
        """
        Check if a finger is extended.
        
        Args:
            landmarks: List of 21 hand landmarks
            finger_name: One of 'thumb', 'index', 'middle', 'ring', 'pinky'
        
        Returns:
            True if finger is extended, False otherwise
        """
        if len(landmarks) < 21:
            return False
        
        finger_tips = {
            'thumb': self.THUMB_TIP,
            'index': self.INDEX_FINGER_TIP,
            'middle': self.MIDDLE_FINGER_TIP,
            'ring': self.RING_FINGER_TIP,
            'pinky': self.PINKY_TIP
        }
        
        finger_mcp = {
            'thumb': self.THUMB_MCP,
            'index': self.INDEX_FINGER_MCP,
            'middle': self.MIDDLE_FINGER_MCP,
            'ring': self.RING_FINGER_MCP,
            'pinky': self.PINKY_MCP
        }
        
        if finger_name not in finger_tips:
            return False
        
        tip_idx = finger_tips[finger_name]
        mcp_idx = finger_mcp[finger_name]
        
        # For thumb, use different logic (check distance from wrist)
        if finger_name == 'thumb':
            dist_tip_to_wrist = self.calculate_distance(landmarks[tip_idx], landmarks[self.WRIST])
            dist_mcp_to_wrist = self.calculate_distance(landmarks[mcp_idx], landmarks[self.WRIST])
            return dist_tip_to_wrist > dist_mcp_to_wrist * 1.2
        
        # For other fingers, check if tip is farther from wrist than MCP
        dist_tip_to_wrist = self.calculate_distance(landmarks[tip_idx], landmarks[self.WRIST])
        dist_mcp_to_wrist = self.calculate_distance(landmarks[mcp_idx], landmarks[self.WRIST])
        
        # Finger is extended if tip is significantly farther from wrist than MCP
        return dist_tip_to_wrist > dist_mcp_to_wrist * self.finger_extended_threshold
    
    def detect_pinch(self, landmarks: List[Tuple[float, float, float]]) -> bool:
        """
        Detect pinch gesture (thumb and index finger touching).
        
        Args:
            landmarks: List of 21 hand landmarks
        
        Returns:
            True if pinch is detected, False otherwise
        """
        if len(landmarks) < 21:
            return False
        
        thumb_tip = landmarks[self.THUMB_TIP]
        index_tip = landmarks[self.INDEX_FINGER_TIP]
        
        distance = self.calculate_distance(thumb_tip, index_tip)
        return distance < self.pinch_threshold
    
    def detect_gesture(self, landmarks: List[Tuple[float, float, float]]) -> str:
        """
        Detect the current gesture from hand landmarks.
        
        Args:
            landmarks: List of 21 hand landmarks
        
        Returns:
            Gesture name: 'FIST', 'POINT', 'OPEN', 'THUMBS_UP', 'PEACE', 'PINCH', 'UNKNOWN'
        """
        if len(landmarks) < 21:
            return 'UNKNOWN'
        
        # Check finger extension states
        thumb_extended = self.is_finger_extended(landmarks, 'thumb')
        index_extended = self.is_finger_extended(landmarks, 'index')
        middle_extended = self.is_finger_extended(landmarks, 'middle')
        ring_extended = self.is_finger_extended(landmarks, 'ring')
        pinky_extended = self.is_finger_extended(landmarks, 'pinky')
        
        # Count extended fingers
        extended_count = sum([
            thumb_extended, index_extended, middle_extended, 
            ring_extended, pinky_extended
        ])
        
        # Detect pinch first (highest priority)
        if self.detect_pinch(landmarks):
            return 'PINCH'
        
        # Fist: all fingers closed
        if extended_count == 0:
            return 'FIST'
        
        # Point: only index finger extended
        if index_extended and not middle_extended and not ring_extended and not pinky_extended and not thumb_extended:
            return 'POINT'
        
        # Peace sign: index and middle fingers extended
        if index_extended and middle_extended and not ring_extended and not pinky_extended:
            return 'PEACE'
        
        # Thumbs up: only thumb extended
        if thumb_extended and not index_extended and not middle_extended and not ring_extended and not pinky_extended:
            return 'THUMBS_UP'
        
        # Open hand: all fingers extended
        if extended_count >= 4:
            return 'OPEN'
        
        return 'UNKNOWN'
    
    def calculate_hand_orientation(self, landmarks: List[Tuple[float, float, float]]) -> Tuple[float, float, float, float]:
        """
        Calculate hand orientation as a quaternion.
        
        Args:
            landmarks: List of 21 hand landmarks
        
        Returns:
            Quaternion (qw, qx, qy, qz) representing hand orientation
        """
        if len(landmarks) < 21:
            return (1.0, 0.0, 0.0, 0.0)  # Identity quaternion
        
        # Get key points for orientation calculation
        wrist = np.array(landmarks[self.WRIST])
        middle_mcp = np.array(landmarks[self.MIDDLE_FINGER_MCP])
        index_mcp = np.array(landmarks[self.INDEX_FINGER_MCP])
        
        # Calculate forward vector (from wrist to middle finger base)
        forward = middle_mcp - wrist
        forward_norm = np.linalg.norm(forward)
        if forward_norm > 0:
            forward = forward / forward_norm
        else:
            return (1.0, 0.0, 0.0, 0.0)
        
        # Calculate right vector (from index to middle MCP)
        right = middle_mcp - index_mcp
        right_norm = np.linalg.norm(right)
        if right_norm > 0:
            right = right / right_norm
        else:
            right = np.array([1.0, 0.0, 0.0])
        
        # Calculate up vector (cross product)
        up = np.cross(forward, right)
        up_norm = np.linalg.norm(up)
        if up_norm > 0:
            up = up / up_norm
        else:
            up = np.array([0.0, 1.0, 0.0])
        
        # Recalculate right to ensure orthogonality
        right = np.cross(up, forward)
        
        # Convert rotation matrix to quaternion
        # Using the rotation matrix [right, up, forward] as columns
        m00, m01, m02 = right
        m10, m11, m12 = up
        m20, m21, m22 = forward
        
        trace = m00 + m11 + m22
        
        if trace > 0:
            s = 0.5 / math.sqrt(trace + 1.0)
            qw = 0.25 / s
            qx = (m21 - m12) * s
            qy = (m02 - m20) * s
            qz = (m10 - m01) * s
        elif m00 > m11 and m00 > m22:
            s = 2.0 * math.sqrt(1.0 + m00 - m11 - m22)
            qw = (m21 - m12) / s
            qx = 0.25 * s
            qy = (m01 + m10) / s
            qz = (m02 + m20) / s
        elif m11 > m22:
            s = 2.0 * math.sqrt(1.0 + m11 - m00 - m22)
            qw = (m02 - m20) / s
            qx = (m01 + m10) / s
            qy = 0.25 * s
            qz = (m12 + m21) / s
        else:
            s = 2.0 * math.sqrt(1.0 + m22 - m00 - m11)
            qw = (m10 - m01) / s
            qx = (m02 + m20) / s
            qy = (m12 + m21) / s
            qz = 0.25 * s
        
        return (qw, qx, qy, qz)
    
    def get_trigger_value(self, gesture: str) -> float:
        """
        Get trigger value based on gesture.
        
        Args:
            gesture: Current gesture name
        
        Returns:
            Trigger value between 0.0 and 1.0
        """
        if gesture == 'POINT':
            return 0.8
        elif gesture == 'PINCH':
            return 1.0
        else:
            return 0.0
    
    def get_grip_value(self, gesture: str) -> float:
        """
        Get grip value based on gesture.
        
        Args:
            gesture: Current gesture name
        
        Returns:
            Grip value between 0.0 and 1.0
        """
        if gesture == 'FIST':
            return 1.0
        elif gesture == 'PINCH':
            return 0.5
        else:
            return 0.0
