import cv2
import numpy as np
import os
from datetime import datetime
import base64
import json

class VideoRecorder:
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.recording = False
        self.frames = []
        self.start_time = None
        self.max_duration = 600  # 10 minutes in seconds
        self.output_dir = "recordings"
        
        # Create output directory if it doesn't exist
        os.makedirs(self.output_dir, exist_ok=True)
    
    def start_recording(self):
        """Start recording"""
        self.recording = True
        self.start_time = datetime.now()
        self.frames = []
    
    def add_frame(self, frame_data: str):
        """Add a frame to recording (base64 encoded)"""
        if not self.recording:
            return
        
        # Check if 10 minutes have passed
        if self.start_time:
            elapsed = (datetime.now() - self.start_time).total_seconds()
            if elapsed >= self.max_duration:
                self.stop_recording()
                return
        
        # Decode base64 frame
        try:
            frame_bytes = base64.b64decode(frame_data)
            nparr = np.frombuffer(frame_bytes, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if frame is not None:
                self.frames.append(frame)
        except Exception as e:
            print(f"Error adding frame: {e}")
    
    def stop_recording(self) -> str:
        """Stop recording and save compressed video"""
        if not self.recording:
            return None
        
        self.recording = False
        
        if not self.frames:
            return None
        
        try:
            # Get video path
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            video_filename = f"vkyc_{self.session_id}_{timestamp}.mp4"
            video_path = os.path.join(self.output_dir, video_filename)
            
            # Get frame dimensions
            height, width = self.frames[0].shape[:2]
            
            # Define codec and create VideoWriter with compression
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            fps = 10  # Reduced FPS for compression
            out = cv2.VideoWriter(video_path, fourcc, fps, (width, height))
            
            # Write frames
            for frame in self.frames:
                out.write(frame)
            
            out.release()
            
            # Further compress using ffmpeg if available (optional)
            # For now, return the path
            return video_path
            
        except Exception as e:
            print(f"Error saving video: {e}")
            return None

