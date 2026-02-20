#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Camera module for pepper_test.
Handles camera/video functionality for the Pepper robot.
"""

import time
import os
import tempfile
import threading


def capture_image(robot):
    """
    Capture a single image from the robot's camera.
    
    Args:
        robot: RobotManager instance
    
    Returns:
        tuple: (image_data, width, height) or (None, None, None) on error
    """
    return robot.capture_image_from_camera()


def capture_and_save(robot, filepath=None):
    """
    Capture an image and save it to a file.
    
    Args:
        robot: RobotManager instance
        filepath: Path to save the image (optional, creates temp file if None)
    
    Returns:
        str: Path to saved image, or None on error
    """
    image_data, width, height = capture_image(robot)
    
    if not image_data:
        return None
    
    try:
        from PIL import Image
        
        if filepath is None:
            temp_file = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
            filepath = temp_file.name
            temp_file.close()
        
        image_bytes = bytes(bytearray(image_data))
        im = Image.frombytes("RGB", (width, height), image_bytes)
        im.save(filepath, "JPEG")
        
        return filepath
    except Exception as e:
        print("Error saving image: {}".format(e))
        return None


def start_video_stream(robot):
    """
    Start continuous video stream for face detection.
    
    Args:
        robot: RobotManager instance
    
    Returns:
        bool: True if started successfully
    """
    return robot.start_continuous_video_stream()


def stop_video_stream(robot):
    """
    Stop continuous video stream.
    
    Args:
        robot: RobotManager instance
    
    Returns:
        bool: True if stopped successfully
    """
    return robot.stop_continuous_video_stream()


def recognize_face(robot, use_stream=True, max_attempts=15, delay=0.3):
    """
    Recognize a face from the camera.
    
    Args:
        robot: RobotManager instance
        use_stream: Whether to use continuous stream (True) or single capture (False)
        max_attempts: Maximum attempts when using stream
        delay: Delay between attempts
    
    Returns:
        str: Name of recognized person, or None
    """
    if use_stream and robot.video_stream_active:
        return robot.recognize_face_from_stream(max_attempts=max_attempts, delay=delay)
    else:
        return robot.recognize_face_from_camera()


def recognize_face_from_image_file(robot, image_path):
    """
    Recognize a face from an image file.
    
    Args:
        robot: RobotManager instance
        image_path: Path to image file
    
    Returns:
        str: Name of recognized person, or None
    """
    try:
        from api.flask_check import post_file_with_retries, API_CONFIG
        
        if not os.path.exists(image_path):
            print("Image file not found: {}".format(image_path))
            return None
        
        with open(image_path, 'rb') as f:
            response = post_file_with_retries(
                "{}/face/detect".format(API_CONFIG["base_url"]),
                files={"file": f},
            )
        
        if response.ok:
            result = response.json()
            recognized_persons = result.get("recognized_persons", [])
            
            if recognized_persons and len(recognized_persons) > 0:
                return recognized_persons[0]
        return None
    except Exception as e:
        print("Error recognizing face from file: {}".format(e))
        return None


def scan_qr_code(robot, image_path=None, camera_url=None):
    """
    Scan a QR code from image or camera.
    
    Args:
        robot: RobotManager instance
        image_path: Path to image file (optional)
        camera_url: URL of camera stream (optional)
    
    Returns:
        dict: QR scan result or None
    """
    from api.client import scan_qr_code_with_api
    
    if image_path:
        return scan_qr_code_with_api(image_file_path=image_path)
    elif camera_url:
        return scan_qr_code_with_api(camera_url=camera_url)
    else:
        return scan_qr_code_with_api(camera_url=robot.camera_url)


def get_camera_urls(robot_ip):
    """
    Get list of possible camera URLs for a Pepper robot.
    
    Args:
        robot_ip: IP address of the robot
    
    Returns:
        list: List of possible camera URLs
    """
    return [
        "http://{}:8080/cameras/front".format(robot_ip),
        "http://{}:8080/video".format(robot_ip),
        "http://{}:8080/cameras/head".format(robot_ip),
        "http://{}:9559/video".format(robot_ip),
    ]

