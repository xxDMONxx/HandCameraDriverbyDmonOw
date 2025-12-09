"""
Data class for hand tracking information.
"""
from typing import Tuple, List, Optional
from dataclasses import dataclass


@dataclass
class HandData:
    """Encapsulates all data for a tracked hand."""
    
    hand_type: str  # "left" or "right"
    position: Tuple[float, float, float]  # x, y, z in world coordinates
    rotation: Tuple[float, float, float, float]  # qw, qx, qy, qz quaternion
    gesture: str  # Current gesture name
    trigger_value: float  # 0.0-1.0
    grip_value: float  # 0.0-1.0
    landmarks: List[Tuple[float, float, float]]  # 21 hand landmarks
    is_detected: bool = True
    
    def to_protocol_string(self) -> str:
        """
        Convert hand data to protocol string for socket transmission.
        Format: HAND:LEFT,X:0.5,Y:0.3,Z:-0.2,QW:1.0,QX:0.0,QY:0.0,QZ:0.0,TRIGGER:0.8,GRIP:0.0,GESTURE:POINT
        """
        return (
            f"HAND:{self.hand_type.upper()},"
            f"X:{self.position[0]:.4f},"
            f"Y:{self.position[1]:.4f},"
            f"Z:{self.position[2]:.4f},"
            f"QW:{self.rotation[0]:.4f},"
            f"QX:{self.rotation[1]:.4f},"
            f"QY:{self.rotation[2]:.4f},"
            f"QZ:{self.rotation[3]:.4f},"
            f"TRIGGER:{self.trigger_value:.2f},"
            f"GRIP:{self.grip_value:.2f},"
            f"GESTURE:{self.gesture}"
        )
    
    @staticmethod
    def create_default(hand_type: str) -> 'HandData':
        """Create a default HandData object with neutral values."""
        return HandData(
            hand_type=hand_type,
            position=(0.0, 0.0, 0.0),
            rotation=(1.0, 0.0, 0.0, 0.0),  # Identity quaternion
            gesture="OPEN",
            trigger_value=0.0,
            grip_value=0.0,
            landmarks=[],
            is_detected=False
        )