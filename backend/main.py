import time
import cv2
import base64
import platform

from flask import Flask
from flask_sock import Sock

app = Flask(__name__)
sock = Sock(app)


@sock.route('/frame_update')
def frame_update(ws):
    while True:
        time.sleep(5)
        ws.send(30)
        time.sleep(5)
        ws.send(5)
        return


@sock.route('/video_feed')
def video_feed(ws):
    """
    This route upgrades HTTP to a WebSocket connection at /ws.
    We'll continuously read frames from the camera, encode them,
    and send them to the connected client as base64 strings.
    """
    camera_idx = 0
    if platform.system() == "Darwin":
        camera_idx = 1

    cap = cv2.VideoCapture(camera_idx)  # Open the default camera
    if not cap.isOpened():
        print("Could not open camera.")
        return

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            # Encode the frame as JPEG
            success, buffer = cv2.imencode('.jpg', frame)
            if not success:
                break

            # Convert to base64
            frame_b64 = base64.b64encode(buffer).decode('utf-8')

            # Send the base64 string to the client
            ws.send(frame_b64)

            # Control the frame rate (about 30 FPS here)
            time.sleep(0.03)
    except Exception as e:
        print(f"Exception during streaming: {e}")
    finally:
        cap.release()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
