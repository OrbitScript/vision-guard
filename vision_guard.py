#!/usr/bin/env python3
"""
VISION-GUARD - AI-Powered Focus & Posture Monitor
Real-time webcam monitoring for productivity and health
Detects: Focus time, posture issues, eye strain, screen distance
"""

import cv2
import numpy as np
import time
import json
from datetime import datetime, timedelta
from collections import deque
import threading
import tkinter as tk
from tkinter import ttk
import pygame
from pathlib import Path

class VisionGuard:
    """Main Vision Guard application"""
    
    def __init__(self):
        # Initialize webcam
        self.cap = cv2.VideoCapture(0)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        # Load face cascade
        cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        self.face_cascade = cv2.CascadeClassifier(cascade_path)
        
        # Eye cascade
        eye_cascade_path = cv2.data.haarcascades + 'haarcascade_eye.xml'
        self.eye_cascade = cv2.CascadeClassifier(eye_cascade_path)
        
        # State tracking
        self.is_monitoring = False
        self.session_start = None
        self.total_focus_time = 0
        self.break_time = 0
        self.posture_warnings = 0
        self.distance_warnings = 0
        self.eye_strain_warnings = 0
        
        # Real-time metrics
        self.face_detected = False
        self.last_face_time = time.time()
        self.face_position_history = deque(maxlen=30)  # Last 30 frames
        self.blink_counter = 0
        self.last_blink_time = time.time()
        
        # Settings
        self.settings = {
            'work_interval': 25,  # Pomodoro: 25 min work
            'break_interval': 5,   # 5 min break
            'posture_check_interval': 10,  # Check every 10 seconds
            'distance_threshold': 150,  # Face size threshold
            'posture_tilt_threshold': 20,  # Degrees
            'enable_sound': True,
            'enable_notifications': True
        }
        
        # Session data
        self.session_data = {
            'focus_sessions': [],
            'breaks_taken': 0,
            'total_time': 0,
            'posture_score': 100,
            'productivity_score': 100
        }
        
        # Initialize pygame for sounds
        pygame.mixer.init()
        
    def detect_face_and_eyes(self, frame):
        """Detect face and eyes in frame"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(gray, 1.3, 5)
        
        face_data = {
            'detected': False,
            'position': None,
            'size': 0,
            'eyes': 0,
            'tilt': 0
        }
        
        if len(faces) > 0:
            # Get largest face
            faces = sorted(faces, key=lambda x: x[2] * x[3], reverse=True)
            x, y, w, h = faces[0]
            
            face_data['detected'] = True
            face_data['position'] = (x + w//2, y + h//2)
            face_data['size'] = w * h
            
            # Draw rectangle
            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
            
            # Detect eyes
            roi_gray = gray[y:y+h, x:x+w]
            roi_color = frame[y:y+h, x:x+w]
            eyes = self.eye_cascade.detectMultiScale(roi_gray, 1.1, 10)
            
            face_data['eyes'] = len(eyes)
            
            for (ex, ey, ew, eh) in eyes:
                cv2.rectangle(roi_color, (ex, ey), (ex+ew, ey+eh), (255, 0, 0), 2)
            
            # Calculate tilt (basic approximation)
            if len(eyes) >= 2:
                eye1_center = eyes[0][0] + eyes[0][2]//2, eyes[0][1] + eyes[0][1]//2
                eye2_center = eyes[1][0] + eyes[1][2]//2, eyes[1][1] + eyes[1][1]//2
                
                angle = np.arctan2(eye2_center[1] - eye1_center[1], 
                                  eye2_center[0] - eye1_center[0])
                face_data['tilt'] = abs(np.degrees(angle))
        
        return frame, face_data
    
    def check_posture(self, face_data):
        """Check if posture is good"""
        if not face_data['detected']:
            return "No Face", 0
        
        issues = []
        score = 100
        
        # Check distance (too close)
        if face_data['size'] > self.settings['distance_threshold'] * 400:
            issues.append("Too Close")
            score -= 30
        elif face_data['size'] < self.settings['distance_threshold'] * 100:
            issues.append("Too Far")
            score -= 20
        
        # Check tilt
        if face_data['tilt'] > self.settings['posture_tilt_threshold']:
            issues.append("Head Tilted")
            score -= 25
        
        # Check if looking away (no eyes detected)
        if face_data['eyes'] < 2:
            issues.append("Looking Away")
            score -= 15
        
        if not issues:
            return "Good Posture", 100
        
        return ", ".join(issues), max(0, score)
    
    def check_eye_strain(self):
        """Check for potential eye strain"""
        current_time = time.time()
        
        # Blink rate (normal: 15-20 per minute)
        time_diff = current_time - self.last_blink_time
        if time_diff > 60:  # Check every minute
            blinks_per_min = self.blink_counter
            self.blink_counter = 0
            self.last_blink_time = current_time
            
            if blinks_per_min < 10:
                return True, "Low blink rate - Take a break!"
        
        return False, ""
    
    def play_alert(self, alert_type='notification'):
        """Play alert sound"""
        if not self.settings['enable_sound']:
            return
        
        # Create simple beep (frequency, duration)
        if alert_type == 'warning':
            frequency = 800
        else:
            frequency = 600
        
        # Generate beep programmatically
        sample_rate = 22050
        duration = 0.2
        
        n_samples = int(sample_rate * duration)
        buf = np.sin(2 * np.pi * frequency * np.linspace(0, duration, n_samples))
        buf = (buf * 32767).astype(np.int16)
        
        # Convert to stereo
        stereo = np.column_stack((buf, buf))
        
        sound = pygame.sndarray.make_sound(stereo)
        sound.play()
    
    def draw_overlay(self, frame, face_data):
        """Draw information overlay on frame"""
        h, w = frame.shape[:2]
        
        # Semi-transparent overlay at top
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (w, 120), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)
        
        # Session time
        if self.session_start:
            elapsed = time.time() - self.session_start
            session_time = str(timedelta(seconds=int(elapsed)))
            cv2.putText(frame, f"Session: {session_time}", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        # Posture status
        posture_status, posture_score = self.check_posture(face_data)
        color = (0, 255, 0) if posture_score > 80 else (0, 165, 255) if posture_score > 60 else (0, 0, 255)
        cv2.putText(frame, f"Posture: {posture_status}", (10, 60),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        
        # Score
        cv2.putText(frame, f"Score: {posture_score}%", (10, 90),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        
        # Status indicator (bottom right)
        status_color = (0, 255, 0) if face_data['detected'] else (0, 0, 255)
        cv2.circle(frame, (w - 30, h - 30), 15, status_color, -1)
        cv2.putText(frame, "ACTIVE" if face_data['detected'] else "AWAY",
                   (w - 120, h - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, status_color, 2)
        
        # Instructions
        cv2.putText(frame, "Press 'Q' to quit | 'S' for stats", (10, h - 10),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)
        
        return frame
    
    def show_stats_overlay(self, frame):
        """Show detailed statistics overlay"""
        h, w = frame.shape[:2]
        
        # Create stats panel
        overlay = frame.copy()
        cv2.rectangle(overlay, (w//4, h//4), (3*w//4, 3*h//4), (40, 40, 40), -1)
        cv2.addWeighted(overlay, 0.8, frame, 0.2, 0, frame)
        
        # Title
        cv2.putText(frame, "SESSION STATISTICS", (w//4 + 20, h//4 + 40),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
        
        # Stats
        y_offset = h//4 + 80
        stats = [
            f"Focus Time: {str(timedelta(seconds=int(self.total_focus_time)))}",
            f"Break Time: {str(timedelta(seconds=int(self.break_time)))}",
            f"Posture Warnings: {self.posture_warnings}",
            f"Distance Warnings: {self.distance_warnings}",
            f"Eye Strain Alerts: {self.eye_strain_warnings}",
            f"Productivity Score: {self.session_data['productivity_score']}%"
        ]
        
        for stat in stats:
            cv2.putText(frame, stat, (w//4 + 30, y_offset),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            y_offset += 35
        
        cv2.putText(frame, "Press any key to continue", (w//4 + 30, y_offset + 20),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (150, 150, 150), 1)
        
        return frame
    
    def run(self):
        """Main monitoring loop"""
        print("🔮 VISION-GUARD Started!")
        print("Press 'Q' to quit, 'S' for stats, 'P' to pause")
        
        self.session_start = time.time()
        last_posture_check = time.time()
        show_stats = False
        
        while True:
            ret, frame = self.cap.read()
            if not ret:
                break
            
            # Flip frame for mirror effect
            frame = cv2.flip(frame, 1)
            
            # Detect face and eyes
            frame, face_data = self.detect_face_and_eyes(frame)
            
            # Update tracking
            current_time = time.time()
            
            if face_data['detected']:
                self.face_detected = True
                self.last_face_time = current_time
                self.total_focus_time += 1/30  # Assuming 30 FPS
                
                # Track position
                self.face_position_history.append(face_data['position'])
                
                # Periodic posture check
                if current_time - last_posture_check > self.settings['posture_check_interval']:
                    posture_status, posture_score = self.check_posture(face_data)
                    
                    if posture_score < 70:
                        self.posture_warnings += 1
                        self.play_alert('warning')
                    
                    last_posture_check = current_time
            else:
                # Away from desk
                if self.face_detected and current_time - self.last_face_time > 5:
                    self.break_time += 1/30
            
            # Draw overlay
            if show_stats:
                frame = self.show_stats_overlay(frame)
            else:
                frame = self.draw_overlay(frame, face_data)
            
            # Display
            cv2.imshow('VISION-GUARD - Focus & Posture Monitor', frame)
            
            # Handle keys
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('s'):
                show_stats = not show_stats
            elif key == ord('p'):
                cv2.waitKey(0)
        
        # Cleanup
        self.save_session_data()
        self.cap.release()
        cv2.destroyAllWindows()
        print("\n✅ Session saved! Stay healthy! 💪")
    
    def save_session_data(self):
        """Save session data to JSON"""
        session = {
            'date': datetime.now().isoformat(),
            'focus_time': int(self.total_focus_time),
            'break_time': int(self.break_time),
            'posture_warnings': self.posture_warnings,
            'distance_warnings': self.distance_warnings,
            'eye_strain_warnings': self.eye_strain_warnings,
            'productivity_score': self.session_data['productivity_score']
        }
        
        # Load existing data
        data_file = Path('session_history.json')
        if data_file.exists():
            with open(data_file, 'r') as f:
                history = json.load(f)
        else:
            history = {'sessions': []}
        
        history['sessions'].append(session)
        
        # Save
        with open(data_file, 'w') as f:
            json.dump(history, f, indent=2)


def main():
    """Main entry point"""
    print("""
╔══════════════════════════════════════════════════════╗
║           🔮 VISION-GUARD v1.0.0 🔮                 ║
║      AI-Powered Focus & Posture Monitor             ║
╚══════════════════════════════════════════════════════╝

Features:
✅ Real-time posture monitoring
✅ Focus time tracking
✅ Eye strain detection
✅ Distance monitoring
✅ Productivity scoring

Starting webcam...
    """)
    
    try:
        guard = VisionGuard()
        guard.run()
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("Make sure your webcam is connected and accessible!")


if __name__ == '__main__':
    main()
