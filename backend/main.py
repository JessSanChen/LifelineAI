import base64
import json
import platform
import queue
import sys
import threading
import time

import cv2
import websocket
from flask import Flask
from flask_sock import Sock
from triage import triaging_agent

app = Flask(__name__)
sock = Sock(app)

DEBUG = False

framerate = 2
triage_message_queue = queue.Queue()
fall_detected_queue = queue.Queue()
frame_update_queue = queue.Queue()


@sock.route('/frame_update')
def frame_update(ws):
    while True:
        frame_update = frame_update_queue.get()
        print("FRAME UPDATE", frame_update)
        if frame_update is None:
            break

        ws.send(frame_update)


@sock.route('/fall_detected')
def fall_detected(ws):
    while True:
        fall_detected = fall_detected_queue.get()
        if fall_detected is None:
            break

        ws.send({"fall_detected": True})


@sock.route("/triage")
def triage_messages(ws):
    while True:
        triage_message = triage_message_queue.get()
        if triage_message is None:
            break

        ws.send(json.dumps(triage_message))


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

                # Wait for response and send back to main thread
                fall_data = external_ws.recv()
                if fall_data:
                    fall_data = json.loads(fall_data)
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

    global framerate
    person_in_frame = False

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
            buffer_length = framerate * 6 if person_in_frame else framerate * 2
            if len(frames_buffer) >= buffer_length and external_ready:
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
                    if response["fall"] == True or DEBUG:
                        triaging_agent(triage_message_queue)

                    # Adaptively adjust framerate and rate of inference based on if someone is in the frame.
                    if response["person"] == True and not person_in_frame:
                        framerate = 20
                        person_in_frame = True
                        frame_update_queue.put(framerate)
                    elif not response["person"] and person_in_frame:
                        framerate = 2
                        person_in_frame = False
                        frame_update_queue.put(framerate)

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
    DEBUG = "--debug" in sys.argv
    app.run(host="0.0.0.0", port=5001, debug=True)
