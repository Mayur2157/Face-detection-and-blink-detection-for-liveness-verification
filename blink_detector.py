import cv2
import numpy as np
import logging
import mediapipe as mp

class BlinkDetector:
    """
    A class to handle blink detection using MediaPipe FaceMesh.
    Tracks eye aspect ratio (EAR) to detect blinks and calculate liveness score.
    """
    
    # Eye landmarks based on MediaPipe FaceMesh indices
    LEFT_EYE = [33, 160, 158, 133, 153, 144]
    RIGHT_EYE = [362, 385, 387, 263, 373, 380]
    
    def __init__(self, blink_threshold=0.30, blink_frames=2):
        """
        Initialize the blink detector with configurable parameters.
        
        Args:
            blink_threshold (float): Threshold for EAR to detect a blink
            blink_frames (int): Minimum consecutive frames to count as a blink
        """
        # Set up logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger("BlinkDetector")
        
        # Initialize MediaPipe FaceMesh
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        
        # Blink detection parameters
        self.BLINK_THRESHOLD = blink_threshold
        self.BLINK_FRAMES = blink_frames
        
        # Initialize tracking variables
        self.reset()
        
    def reset(self):
        """Reset all tracking variables."""
        self.blink_count = 0
        self.blink_frames = 0
        self.liveness_score = 0
        self.last_ear = 0.0
        self.logger.info("Detector reset: all counters set to zero")

    def eye_aspect_ratio(self, eye):
        """
        Calculate the Eye Aspect Ratio (EAR) for blink detection.
        
        Args:
            eye (list): List of (x, y) coordinates for eye landmarks
            
        Returns:
            float: The calculated EAR value
        """
        A = np.linalg.norm(np.array(eye[1]) - np.array(eye[5]))
        B = np.linalg.norm(np.array(eye[2]) - np.array(eye[4]))
        C = np.linalg.norm(np.array(eye[0]) - np.array(eye[3]))
        
        # Prevent division by zero
        if C == 0:
            return 0
            
        EAR = (A + B) / (2.0 * C)
        return EAR

    def process_frame(self, frame):
        """
        Process a video frame to detect face and blinks.
        
        Args:
            frame (numpy.ndarray): Input video frame
            
        Returns:
            tuple: (success, message, results_dict)
                success (bool): Whether processing was successful
                message (str): Status message
                results_dict (dict): Contains detection results
        """
        if frame is None:
            return False, "Invalid frame", {}
            
        # Convert the frame to RGB for MediaPipe
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.face_mesh.process(frame_rgb)

        # Check if a face was detected
        if not results.multi_face_landmarks:
            return False, "No face detected", {
                "blink_count": self.blink_count,
                "liveness_score": self.liveness_score,
                "ear": 0
            }
            
        # For each detected face (usually just one)
        for face_landmarks in results.multi_face_landmarks:
            # Extract eye landmarks
            left_eye = [(face_landmarks.landmark[i].x, face_landmarks.landmark[i].y) 
                      for i in self.LEFT_EYE]
            right_eye = [(face_landmarks.landmark[i].x, face_landmarks.landmark[i].y) 
                       for i in self.RIGHT_EYE]

            # Calculate EAR for both eyes
            left_ear = self.eye_aspect_ratio(left_eye)
            right_ear = self.eye_aspect_ratio(right_eye)
            avg_ear = (left_ear + right_ear) / 2.0
            
            self.last_ear = avg_ear
            
            self.logger.debug(f"EAR: Left {left_ear:.3f}, Right {right_ear:.3f}, Avg {avg_ear:.3f}")

            # Blink detection logic
            if avg_ear < self.BLINK_THRESHOLD:
                self.blink_frames += 1
                self.logger.debug(f"Potential blink frame {self.blink_frames}/{self.BLINK_FRAMES}")
            else:
                # If we've accumulated enough low-EAR frames, count a blink
                if self.blink_frames >= self.BLINK_FRAMES:
                    self.blink_count += 1
                    self.liveness_score += 10
                    self.logger.info(f"Blink detected! Count: {self.blink_count}, Score: {self.liveness_score}")
                
                # Reset the frame counter
                self.blink_frames = 0

        # Return success with current detection state
        return True, "Face processed", {
            "blink_count": self.blink_count,
            "liveness_score": self.liveness_score,
            "ear": self.last_ear
        }
        
    def get_status(self):
        """
        Get the current detection status.
        
        Returns:
            dict: Current blink count and liveness score
        """
        return {
            "blink_count": self.blink_count,
            "liveness_score": self.liveness_score,
            "ear": self.last_ear
        }
        
    def close(self):
        """Release resources."""
        self.face_mesh.close()