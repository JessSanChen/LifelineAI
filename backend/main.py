import time
import cv2
import base64
import platform
import pyttsx3
import speech_recognition as sr

from flask import Flask, request, jsonify
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


def text_to_speech(text):
    engine = pyttsx3.init()
    engine.say(text)
    engine.runAndWait()


@app.route('/text_to_speech', methods=['GET'])
def handle_text_to_speech():
    text = request.args.get('text')
    if not text:
        return jsonify({"error": "Text parameter is required"}), 400

    text_to_speech(text)
    return jsonify({"message": "Speech played successfully", "text": text})


@app.route('/speech_to_text', methods=['GET'])
def speech_to_text():
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        recognizer.adjust_for_ambient_noise(source)
        try:
            audio = recognizer.listen(source, timeout=5)
            text = recognizer.recognize_google(audio)
            print(text)
            return jsonify({"text": text})
        except sr.UnknownValueError:
            return jsonify({"text": "Could not understand the audio."})
        except sr.RequestError:
            return jsonify({"text": "Error: Check your internet connection."})
        except sr.WaitTimeoutError:
            return jsonify({"text": "Listening timed out."})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
