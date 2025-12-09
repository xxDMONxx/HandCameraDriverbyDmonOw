"""
Hand tracking camera capture and processing for SteamVR.
Captures video, detects hands using MediaPipe, and sends data to SteamVR driver.
"""
import cv2
import mediapipe as mp
import json
import time
import sys
from typing import List, Tuple, Optional
from hand_data import HandData
from gesture_detector import GestureDetector
from utils.camera_utils import CameraCapture
from utils.socket_client import SocketClient


class HandTracker:
    """Main hand tracking system."""
    
    def __init__(self, config_path: str = "config.json"):
        """
        Initialize hand tracker with configuration.
        
        Args:
            config_path: Path to configuration JSON file
        """
        # Load configuration
        self.config = self.load_config(config_path)
        
        # Initialize MediaPipe Hands
        self.mp_hands = mp.solutions.hands
        self.mp_drawing = mp.solutions.drawing_utils
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=self.config['tracking']['max_hands'],
            min_detection_confidence=self.config['tracking']['detection_confidence'],
            min_tracking_confidence=self.config['tracking']['tracking_confidence'],
            model_complexity=self.config['tracking']['model_complexity']
        )
        
        # Initialize camera
        cam_config = self.config['camera']
        self.camera = CameraCapture(
            device_id=cam_config['device_id'],
            width=cam_config['width'],
            height=cam_config['height'],
            fps=cam_config['fps'],
            flip_horizontal=cam_config['flip_horizontal']
        )
        
        # Initialize gesture detector
        gesture_config = self.config['gestures']
        self.gesture_detector = GestureDetector(
            pinch_threshold=gesture_config['pinch_threshold'],
            finger_extended_threshold=gesture_config['finger_extended_threshold']
        )
        
        # Initialize socket client
        net_config = self.config['network']
        self.socket_client = SocketClient(
            host=net_config['host'],
            port=net_config['port']
        )
        
        # Debug settings
        self.debug = self.config['debug']
        
        # Calibration
        self.calibration = self.config.get('calibration', {
            'position_offset': [0.0, 0.0, 0.0],
            'scale': 1.0
        })
        
        print("HandTracker initialized")
        print(f"Camera: {cam_config['width']}x{cam_config['height']} @ {cam_config['fps']}fps")
        print(f"Tracking: max {self.config['tracking']['max_hands']} hands")
        print(f"Network: {net_config['host']}:{net_config['port']}")
    
    def load_config(self, config_path: str) -> dict:
        """
        Load configuration from JSON file.
        
        Args:
            config_path: Path to config file
        
        Returns:
            Configuration dictionary
        """
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
            print(f"Configuration loaded from {config_path}")
            return config
        except Exception as e:
            print(f"Error loading config: {e}")
            print("Using default configuration")
            # Return default config
            return {
                "camera": {"device_id": 0, "width": 640, "height": 480, "fps": 60, "flip_horizontal": True},
                "tracking": {"max_hands": 2, "detection_confidence": 0.7, "tracking_confidence": 0.5, "model_complexity": 1},
                "network": {"host": "127.0.0.1", "port": 65432},
                "gestures": {"pinch_threshold": 0.05, "finger_extended_threshold": 0.6},
                "calibration": {"position_offset": [0.0, 0.0, 0.0], "scale": 1.0},
                "debug": {"show_video": True, "show_landmarks": True, "show_fps": True, "log_gestures": False}
            }
    
    def process_hand_landmarks(self, hand_landmarks, hand_label: str, 
                               frame_width: int, frame_height: int) -> HandData:
        """
        Process MediaPipe hand landmarks into HandData object.
        
        Args:
            hand_landmarks: MediaPipe hand landmarks
            hand_label: "Left" or "Right"
            frame_width: Frame width in pixels
            frame_height: Frame height in pixels
        
        Returns:
            HandData object with processed hand information
        """
        # Extract landmarks as list of tuples
        landmarks = []
        for landmark in hand_landmarks.landmark:
            landmarks.append((landmark.x, landmark.y, landmark.z))
        
        # Calculate hand position (using wrist position)
        wrist = landmarks[0]
        
        # Convert normalized coordinates to world coordinates
        # Center the coordinates around 0 and scale appropriately
        x = (wrist[0] - 0.5) * 2.0  # Range: -1.0 to 1.0
        y = -(wrist[1] - 0.5) * 2.0  # Range: -1.0 to 1.0, inverted
        
        # Estimate Z based on hand size (larger hand = closer to camera = more negative Z)
        palm_size = self.calculate_palm_size(landmarks)
        z = -0.5 - (palm_size * 2.0)  # Approximate depth
        
        # Apply calibration
        scale = self.calibration['scale']
        offset = self.calibration['position_offset']
        position = (
            x * scale + offset[0],
            y * scale + offset[1],
            z * scale + offset[2]
        )
        
        # Calculate hand orientation
        rotation = self.gesture_detector.calculate_hand_orientation(landmarks)
        
        # Detect gesture
        gesture = self.gesture_detector.detect_gesture(landmarks)
        
        # Calculate trigger and grip values
        trigger_value = self.gesture_detector.get_trigger_value(gesture)
        grip_value = self.gesture_detector.get_grip_value(gesture)
        
        # Determine hand type
        hand_type = "left" if hand_label == "Left" else "right"
        
        return HandData(
            hand_type=hand_type,
            position=position,
            rotation=rotation,
            gesture=gesture,
            trigger_value=trigger_value,
            grip_value=grip_value,
            landmarks=landmarks,
            is_detected=True
        )
    
    def calculate_palm_size(self, landmarks: List[Tuple[float, float, float]]) -> float:
        """
        Calculate palm size for depth estimation.
        
        Args:
            landmarks: List of hand landmarks
        
        Returns:
            Palm size as average of key distances
        """
        if len(landmarks) < 21:
            return 0.1
        
        # Calculate distances between key palm points
        wrist = landmarks[0]
        index_mcp = landmarks[5]
        pinky_mcp = landmarks[17]
        
        dist1 = self.gesture_detector.calculate_distance(wrist, index_mcp)
        dist2 = self.gesture_detector.calculate_distance(wrist, pinky_mcp)
        dist3 = self.gesture_detector.calculate_distance(index_mcp, pinky_mcp)
        
        return (dist1 + dist2 + dist3) / 3.0
    
    def draw_landmarks(self, frame, hand_landmarks):
        """
        Draw hand landmarks on frame.
        
        Args:
            frame: OpenCV frame
            hand_landmarks: MediaPipe hand landmarks
        """
        self.mp_drawing.draw_landmarks(
            frame,
            hand_landmarks,
            self.mp_hands.HAND_CONNECTIONS,
            self.mp_drawing.DrawingSpec(color=(0, 255, 0), thickness=2, circle_radius=2),
            self.mp_drawing.DrawingSpec(color=(255, 0, 0), thickness=2)
        )
    
    def draw_info(self, frame, hands_data: List[HandData], fps: float):
        """
        Draw information overlay on frame.
        
        Args:
            frame: OpenCV frame
            hands_data: List of detected hands
            fps: Current FPS
        """
        # Draw FPS
        if self.debug['show_fps']:
            cv2.putText(frame, f"FPS: {fps:.1f}", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        # Draw hand information
        y_offset = 60
        for hand in hands_data:
            if hand.is_detected:
                info_text = f"{hand.hand_type.upper()}: {hand.gesture}"
                cv2.putText(frame, info_text, (10, y_offset),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
                y_offset += 30
    
    def run(self):
        """Main tracking loop."""
        print("\n=== Starting Hand Tracking ===")
        
        # Start camera
        if not self.camera.start():
            print("Failed to start camera. Exiting.")
            return
        
        # Connect to driver
        print("Connecting to SteamVR driver...")
        if not self.socket_client.connect():
            print("Warning: Could not connect to driver. Will keep trying...")
        
        print("\nHand tracking active!")
        print("Press 'q' to quit\n")
        
        try:
            while True:
                # Read frame
                ret, frame = self.camera.read_frame()
                if not ret:
                    print("Failed to read frame")
                    break
                
                # Convert to RGB for MediaPipe
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                
                # Process with MediaPipe
                results = self.hands.process(frame_rgb)
                
                # Prepare hand data
                hands_data = []
                
                if results.multi_hand_landmarks and results.multi_handedness:
                    for hand_landmarks, handedness in zip(results.multi_hand_landmarks, results.multi_handedness):
                        # Get hand label
                        hand_label = handedness.classification[0].label
                        
                        # Process hand
                        hand_data = self.process_hand_landmarks(
                            hand_landmarks, hand_label,
                            frame.shape[1], frame.shape[0]
                        )
                        hands_data.append(hand_data)
                        
                        # Draw landmarks if enabled
                        if self.debug['show_landmarks']:
                            self.draw_landmarks(frame, hand_landmarks)
                        
                        # Log gesture if enabled
                        if self.debug['log_gestures']:
                            print(f"{hand_data.hand_type}: {hand_data.gesture} "
                                  f"T:{hand_data.trigger_value:.2f} G:{hand_data.grip_value:.2f}")
                
                # Send data to driver
                for hand_data in hands_data:
                    protocol_string = hand_data.to_protocol_string()
                    self.socket_client.send(protocol_string)
                
                # Draw info overlay
                if self.debug['show_video']:
                    self.draw_info(frame, hands_data, self.camera.get_fps())
                    cv2.imshow('Hand Tracking', frame)
                    
                    # Handle keyboard input
                    key = cv2.waitKey(1) & 0xFF
                    if key == ord('q'):
                        print("\nQuitting...")
                        break
                
        except KeyboardInterrupt:
            print("\nInterrupted by user")
        except Exception as e:
            print(f"\nError in tracking loop: {e}")
            import traceback
            traceback.print_exc()
        finally:
            # Cleanup
            print("\nCleaning up...")
            self.camera.release()
            self.socket_client.close()
            self.hands.close()
            cv2.destroyAllWindows()
            print("Cleanup complete")


def main():
    """Main entry point."""
    print("=" * 50)
    print("Hand Camera Driver for SteamVR")
    print("=" * 50)
    
    # Check for config file argument
    config_path = "config.json"
    if len(sys.argv) > 1:
        config_path = sys.argv[1]
    
    # Create and run tracker
    tracker = HandTracker(config_path)
    tracker.run()


if __name__ == "__main__":
    main()