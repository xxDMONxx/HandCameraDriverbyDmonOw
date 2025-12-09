"""
Camera utility functions for video capture and processing.
"""
import cv2
import time
from typing import Optional, Tuple


class CameraCapture:
    """Handles camera capture with configuration options."""
    
    def __init__(self, device_id: int = 0, width: int = 640, height: int = 480, 
                 fps: int = 60, flip_horizontal: bool = True):
        """
        Initialize camera capture.
        
        Args:
            device_id: Camera device ID
            width: Frame width
            height: Frame height
            fps: Target frames per second
            flip_horizontal: Whether to flip the frame horizontally
        """
        self.device_id = device_id
        self.width = width
        self.height = height
        self.fps = fps
        self.flip_horizontal = flip_horizontal
        self.cap: Optional[cv2.VideoCapture] = None
        self.frame_count = 0
        self.fps_start_time = time.time()
        self.current_fps = 0.0
        
    def start(self) -> bool:
        """
        Start camera capture.
        
        Returns:
            True if camera started successfully, False otherwise
        """
        try:
            self.cap = cv2.VideoCapture(self.device_id)
            
            if not self.cap.isOpened():
                print(f"Error: Could not open camera {self.device_id}")
                return False
            
            # Set camera properties
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
            self.cap.set(cv2.CAP_PROP_FPS, self.fps)
            
            # Verify settings
            actual_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            actual_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            actual_fps = int(self.cap.get(cv2.CAP_PROP_FPS))
            
            print(f"Camera started: {actual_width}x{actual_height} @ {actual_fps}fps")
            
            return True
            
        except Exception as e:
            print(f"Error starting camera: {e}")
            return False
    
    def read_frame(self) -> Tuple[bool, Optional[cv2.Mat]]:
        """
        Read a frame from the camera.
        
        Returns:
            Tuple of (success, frame)
        """
        if self.cap is None or not self.cap.isOpened():
            return False, None
        
        ret, frame = self.cap.read()
        
        if not ret:
            return False, None
        
        # Flip frame if configured
        if self.flip_horizontal:
            frame = cv2.flip(frame, 1)
        
        # Update FPS counter
        self.frame_count += 1
        elapsed_time = time.time() - self.fps_start_time
        if elapsed_time > 1.0:
            self.current_fps = self.frame_count / elapsed_time
            self.frame_count = 0
            self.fps_start_time = time.time()
        
        return True, frame
    
    def get_fps(self) -> float:
        """Get current FPS."""
        return self.current_fps
    
    def release(self):
        """Release camera resources."""
        if self.cap is not None:
            self.cap.release()
            self.cap = None
            print("Camera released")
    
    def is_opened(self) -> bool:
        """Check if camera is opened."""
        return self.cap is not None and self.cap.isOpened()
