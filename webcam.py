import cv2

camera = cv2.VideoCapture(0) # webcam index

if not camera.isOpened():
    raise RuntimeError("Could not open webcam")

ret, frame = camera.read()
camera.release()

if not ret:
    raise RuntimeError("Could not read frame from webcam")

cv2.imwrite("snapshot.jpg", frame)
print("Saved snapshot.jpg")