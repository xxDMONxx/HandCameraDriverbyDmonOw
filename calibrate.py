"""
Calibration script for hand tracking.
Allows users to calibrate position offset and scale.
"""
import cv2
import mediapipe as mp
import json
import sys
from utils.camera_utils import CameraCapture


class Calibrator:
    """Hand tracking calibration system."""
    
    def __init__(self, config_path: str = "config.json"):
        """
        Initialize calibrator.
        
        Args:
            config_path: Path to configuration JSON file
        """
        self.config_path = config_path
        self.config = self.load_config()
        
        # Calibration values
        self.position_offset = self.config.get('calibration', {}).get('position_offset', [0.0, 0.0, 0.0])
        self.scale = self.config.get('calibration', {}).get('scale', 1.0)
        
        # Initialize MediaPipe Hands
        self.mp_hands = mp.solutions.hands
        self.mp_drawing = mp.solutions.drawing_utils
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=1,  # Calibrate with one hand
            min_detection_confidence=0.7,
            min_tracking_confidence=0.5
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
        
        print("Calibrator initialized")
    
    def load_config(self) -> dict:
        """Load configuration from JSON file."""
        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)
            return config
        except Exception as e:
            print(f"Error loading config: {e}")
            return {
                "camera": {"device_id": 0, "width": 640, "height": 480, "fps": 60, "flip_horizontal": True},
                "tracking": {"max_hands": 2, "detection_confidence": 0.7, "tracking_confidence": 0.5, "model_complexity": 1},
                "network": {"host": "127.0.0.1", "port": 65432},
                "gestures": {"pinch_threshold": 0.05, "finger_extended_threshold": 0.6},
                "calibration": {"position_offset": [0.0, 0.0, 0.0], "scale": 1.0},
                "debug": {"show_video": True, "show_landmarks": True, "show_fps": True, "log_gestures": False}
            }
    
    def save_config(self):
        """Save configuration to JSON file."""
        try:
            # Update calibration values
            if 'calibration' not in self.config:
                self.config['calibration'] = {}
            self.config['calibration']['position_offset'] = self.position_offset
            self.config['calibration']['scale'] = self.scale
            
            with open(self.config_path, 'w') as f:
                json.dump(self.config, f, indent=2)
            print(f"\nCalibration saved to {self.config_path}")
            return True
        except Exception as e:
            print(f"Error saving config: {e}")
            return False
    
    def draw_instructions(self, frame):
        """Draw calibration instructions on frame."""
        instructions = [
            "=== CALIBRATION MODE ===",
            "Position Offset (X, Y, Z):",
            f"  X: {self.position_offset[0]:.3f} (Left/Right)",
            f"  Y: {self.position_offset[1]:.3f} (Up/Down)",
            f"  Z: {self.position_offset[2]:.3f} (Forward/Back)",
            f"Scale: {self.scale:.3f}",
            "",
            "Controls:",
            "  A/D: Adjust X offset",
            "  W/S: Adjust Y offset",
            "  Q/E: Adjust Z offset",
            "  +/-: Adjust scale",
            "  R: Reset to default",
            "  Space: Save and exit",
            "  ESC: Exit without saving"
        ]
        
        y_offset = 30
        for i, line in enumerate(instructions):
            color = (0, 255, 255) if i == 0 else (255, 255, 255)
            thickness = 2 if i == 0 else 1
            cv2.putText(frame, line, (10, y_offset),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, thickness)
            y_offset += 25
    
    def run(self):
        """Run calibration process."""
        print("\n=== Starting Calibration ===")
        print("Place your hand in a comfortable neutral position")
        print("Use keyboard controls to adjust calibration values")
        
        if not self.camera.start():
            print("Failed to start camera. Exiting.")
            return
        
        adjustment_step = 0.05
        scale_step = 0.1
        
        try:
            while True:
                ret, frame = self.camera.read_frame()
                if not ret:
                    print("Failed to read frame")
                    break
                
                # Convert to RGB for MediaPipe
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                
                # Process with MediaPipe
                results = self.hands.process(frame_rgb)
                
                # Draw landmarks if hand detected
                if results.multi_hand_landmarks:
                    for hand_landmarks in results.multi_hand_landmarks:
                        self.mp_drawing.draw_landmarks(
                            frame,
                            hand_landmarks,
                            self.mp_hands.HAND_CONNECTIONS,
                            self.mp_drawing.DrawingSpec(color=(0, 255, 0), thickness=2, circle_radius=2),
                            self.mp_drawing.DrawingSpec(color=(255, 0, 0), thickness=2)
                        )
                
                # Draw instructions
                self.draw_instructions(frame)
                
                # Show frame
                cv2.imshow('Calibration', frame)
                
                # Handle keyboard input
                key = cv2.waitKey(1) & 0xFF
                
                # Position adjustments
                if key == ord('a'):
                    self.position_offset[0] -= adjustment_step
                elif key == ord('d'):
                    self.position_offset[0] += adjustment_step
                elif key == ord('w'):
                    self.position_offset[1] += adjustment_step
                elif key == ord('s'):
                    self.position_offset[1] -= adjustment_step
                elif key == ord('q'):
                    self.position_offset[2] -= adjustment_step
                elif key == ord('e'):
                    self.position_offset[2] += adjustment_step
                
                # Scale adjustments
                elif key == ord('+') or key == ord('='):
                    self.scale += scale_step
                elif key == ord('-') or key == ord('_'):
                    self.scale = max(0.1, self.scale - scale_step)
                
                # Reset
                elif key == ord('r'):
                    self.position_offset = [0.0, 0.0, 0.0]
                    self.scale = 1.0
                    print("Calibration reset to defaults")
                
                # Save and exit
                elif key == ord(' '):
                    if self.save_config():
                        print("Calibration saved successfully!")
                    break
                
                # Exit without saving
                elif key == 27:  # ESC
                    print("Exiting without saving")
                    break
        
        except KeyboardInterrupt:
            print("\nInterrupted by user")
        except Exception as e:
            print(f"\nError in calibration: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.camera.release()
            self.hands.close()
            cv2.destroyAllWindows()
            print("Calibration complete")


def main():
    """Main entry point."""
    print("=" * 50)
    print("Hand Camera Driver - Calibration")
    print("=" * 50)
    
    config_path = "config.json"
    if len(sys.argv) > 1:
        config_path = sys.argv[1]
    
    calibrator = Calibrator(config_path)
    calibrator.run()


if __name__ == "__main__":
    main()