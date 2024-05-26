﻿import cv2
from ultralytics import YOLO

# TODO 1: test this code with the camera
# TODO 2: test this code with a video file

# Load the trained YOLO model
model = YOLO('weights/best.pt')

# Start capturing video
cap = cv2.VideoCapture(0)  # 0 for the default camera

# # Open the video file # cap = cv2.VideoCapture('path_to_video')  # replace 'path_to_video' with the path to the video file

# Set the frame width and height
cap.set(3, 1920)  # Width
cap.set(4, 1080)  # Height

while True:
    # Read a frame from the camera
    ret, frame = cap.read()
    if not ret:
        break

    # Apply the YOLO model to detect cards in the frame
    detect_result = model(frame)

    # Draw bounding boxes and labels on the detections
    detect_image = detect_result[0].plot()

    # Display the frame
    cv2.imshow('Card Detection', detect_image)

    # Break the loop if 'q' is pressed
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Release the video capture object
cap.release()

# Close all OpenCV windows
cv2.destroyAllWindows()
