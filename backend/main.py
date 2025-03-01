from flask import Flask
import base64
import json
import platform
import queue
import threading
import time

import cv2
import websocket
from flask import Flask
from flask_sock import Sock

app = Flask(__name__)
sock = Sock(app)

framerate = 30


app = Flask(__name__)
sock = Sock(app)


framerate = 15


@sock.route('/frame_update')
def frame_update(ws):
    while True:
        time.sleep(5)
        ws.send(30)
        time.sleep(5)
        ws.send(5)
        return


def external_processing_thread(frames_queue, response_queue, external_ws):
    """
    Runs on a separate thread:
      - Receives frame batches from frames_queue
      - Sends them to the external_ws
      - Waits for response
      - Puts the response (or a "ready" signal) in the response_queue
    """
    try:
        while True:
            # Wait for the next batch of frames to process
            frames_batch = frames_queue.get()
            if frames_batch is None:
                break

            # Send the accumulated frames as a JSON array
            try:
                message = json.dumps(frames_batch)
                external_ws.send(message)
                print(
                    f"[External Thread] Sent {len(frames_batch)} frames to server.")

                # Wait for response
                fall_data = external_ws.recv()
                # if fall_data:
                #     print(f"[External Thread] Received response: {fall_data}")
                # Signal we got a response (you could send the actual data or a simple "ready" flag)
                response_queue.put(fall_data)
            except Exception as e:
                print(
                    f"[External Thread] Failed to send frames or receive response: {e}")
                response_queue.put(None)
    finally:
        try:
            external_ws.close()
        except:
            pass
        print("[External Thread] External WebSocket closed.")


@sock.route('/video_feed')
def video_feed(ws):
    """
    On first connection, opens camera and also connects to an external WebSocket server.
    Sends live frames to the client in real-time.
    Batches up frames to send to the external server on a separate thread every 3 seconds,
    but only if we have received a response (ready signal) from the previous batch.
    """

    # Pick the right camera index for macOS vs others
    camera_idx = 1 if platform.system() == "Darwin" else 0
    cap = cv2.VideoCapture(camera_idx)
    if not cap.isOpened():
        print("Could not open camera.")
        return

    # Connect to the northflank WebSocket server
    # external_ws_url = "ws://localhost:8765"
    external_ws_url = "wss://p01--vlm-inference--f6l8w976xnkg.code.run"
    try:
        external_ws = websocket.WebSocket()
        external_ws.connect(external_ws_url)
        print(f"Connected to northflank WebSocket server: {external_ws_url}")
    except Exception as e:
        print(f"Failed to connect to external server: {e}")
        cap.release()
        return

    # Queues for communication between main thread and external thread
    frames_queue = queue.Queue()
    response_queue = queue.Queue()

    # Start the external processing thread
    processing_thread = threading.Thread(
        target=external_processing_thread,
        args=(frames_queue, response_queue, external_ws),
        daemon=True
    )
    processing_thread.start()

    # We'll accumulate 3 seconds worth of frames to send in one batch
    frames_buffer = []
    start_time = time.time()

    # This flag indicates if the external thread is ready for a new batch.
    # For the first batch, let's assume we are ready right away.
    external_ready = True

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("Failed to read frame from camera.")
                break

            # Encode frame as JPEG -> base64
            success, buffer = cv2.imencode('.jpg', frame)
            if not success:
                print("Failed to encode frame.")
                break

            frame_b64 = base64.b64encode(buffer).decode('utf-8')

            # Send current frame to frontend
            try:
                ws.send(frame_b64)
            except Exception as e:
                print(f"Failed to send frame to frontend: {e}")
                break

            # Collect frames for external server *only if* external is ready
            if external_ready:
                frames_buffer.append(frame_b64)

            # Check if some time has elapsed and the external thread is ready
            # if (time.time() - start_time >= 6) and external_ready:
            if len(frames_buffer) >= framerate * 5 and external_ready:
                # Send the accumulated frames to the external thread
                frames_queue.put(frames_buffer)
                # print(f"[Main Thread] Queued {len(frames_buffer)} frames for processing.")

                # Reset for next 3-second batch
                frames_buffer = []
                start_time = time.time()

                # Since we've sent a batch, mark external as not ready
                external_ready = False

            # Check if there's any response from the external thread
            # If we get a response, that means it is ready for the next batch
            try:
                response = response_queue.get_nowait()
                # You can do something with the response here if needed
                if response is not None:
                    print(f"[Main Thread] Server response: {response}")
                # Mark the external as ready for next batch
                external_ready = True
            except queue.Empty:
                # No response yet; just continue
                pass

            # Control the frame rate (approximately 30 FPS)
            time.sleep(1 / framerate)

    except Exception as e:
        print(f"Exception during streaming: {e}")

    finally:
        cap.release()
        # Signal the external processing thread to exit, then join it
        frames_queue.put(None)
        processing_thread.join(timeout=5)
        print("Camera and external processing thread closed.")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
