import anthropic
import os
import time
import threading
import queue
import requests
import websocket
from dotenv import load_dotenv
from enum import Enum
from pydantic import BaseModel
import instructor

# Load environment variables from .env
load_dotenv()
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

if not ANTHROPIC_API_KEY:
    raise ValueError("Missing Anthropic API key! Please set it in .env file.")

# Initialize Anthropic Client with Instructor
client = instructor.from_anthropic(anthropic.Anthropic(api_key=ANTHROPIC_API_KEY))

# Read the system prompt from file
with open("triage_prompt.txt", "r") as file:
    SYSTEM_PROMPT = file.read()

# Flask API base URL
FLASK_API_BASE_URL = "http://localhost:5001"

# Define States as Enum
class TriagingState(Enum):
    INIT_FALL_DETECTED = "INIT_FALL_DETECTED"
    RESPONSIVE = "RESPONSIVE"
    NON_RESPONSIVE = "NON_RESPONSIVE"
    NOT_FALL = "NOT_FALL"
    CONFIRMED_HURT = "CONFIRMED_HURT"
    LOW_SEVERITY = "LOW_SEVERITY"
    HIGH_SEVERITY = "HIGH_SEVERITY"
    AWAITING_CONFIRMATION = "AWAITING_CONFIRMATION"
    ALERT_MEDICAL = "ALERT_MEDICAL"

# Define Structured Response Model with PRIME scoring
class TriageResponse(BaseModel):
    response_text: str
    next_state: TriagingState
    trajectory_score: float  # PRIME assigns this to optimize inference

# Function to call Claude API with structured response & PRIME reward
def call_claude(state, user_input=None, past_rewards=[]):
    user_prompt = user_input if user_input else "What should happen next?"

    # Constructing reward model feedback for PRIME
    reward_feedback = (
        f"Prior rewards for triage optimization: {past_rewards}. "
        "Your response should prioritize fast, accurate decision-making."
    )

    try:
        response = client.chat.completions.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=150,
            temperature=0.5,
            system=f"{SYSTEM_PROMPT}\n\n{reward_feedback}",
            messages=[{"role": "user", "content": user_prompt}],
            response_model=TriageResponse
        )

        return response

    except Exception as e:
        print(f"Claude API Error: {e}")
        return TriageResponse(
            response_text="I'm having trouble processing right now.", 
            next_state=state, 
            trajectory_score=0.0
        )

# Function to send text response to TTS API
def speak_text(text):
    """Send Claude's response to Flask TTS API for speech output."""
    try:
        requests.get(f"{FLASK_API_BASE_URL}/text_to_speech", params={"text": text})
    except requests.exceptions.RequestException as e:
        print(f"Error in text-to-speech: {e}")

import websocket
import ssl
import queue
import time
import threading

def get_speech_input(timeout=6):
    """Listens for speech input via WebSocket with a passive timeout."""
    def listen_speech(ws):
        """Receives speech-to-text input from WebSocket."""
        while True:
            try:
                message = ws.recv()
                if message and message not in {"Listening...", "Listening timed out.", "Could not understand the audio."}:
                    speech_queue.put(message)
                    break  # Stop listening once valid input is received
            except websocket.WebSocketConnectionClosedException:
                break

    speech_queue = queue.Queue()

    # ✅ FIX: Remove 'Sec-WebSocket-Extensions' header to prevent 'rsv is not implemented' error
    ws = websocket.WebSocket()
    
    try:
        ws.connect(
            "ws://localhost:5001/speech_to_text",
            header=["Sec-WebSocket-Extensions: "],  # ✅ Overrides and removes compression header
            skip_utf8_validation=True
        )

        listen_thread = threading.Thread(target=listen_speech, args=(ws,))
        listen_thread.daemon = True
        listen_thread.start()

        start_time = time.time()
        while time.time() - start_time < timeout:
            if not speech_queue.empty():
                return speech_queue.get()  # ✅ Return recognized speech immediately
            time.sleep(0.1)

    except websocket.WebSocketProtocolException:
        print("WebSocket error: Removing Sec-WebSocket-Extensions resolved issue.")
    except Exception as e:
        print(f"Speech recognition error: {e}")
    
    finally:
        ws.close()  # ✅ Always close WebSocket after use

    return None  # Return None if timeout occurs

# Function to capture speech input using WebSocket
# def get_speech_input(timeout=6):
#     """Listens for speech input with a passive timeout."""
#     def listen_speech(ws):
#         """Receives speech-to-text input from WebSocket."""
#         while True:
#             message = ws.recv()
#             if message and message not in {"Listening...", "Listening timed out.", "Could not understand the audio."}:
#                 speech_queue.put(message)
#                 ws.close()
#                 break

#     speech_queue = queue.Queue()
#     ws = websocket.WebSocket()
    
#     try:
#         ws.connect(f"ws://localhost:5001/speech_to_text")
#         listen_thread = threading.Thread(target=listen_speech, args=(ws,))
#         listen_thread.daemon = True
#         listen_thread.start()

#         start_time = time.time()
#         while time.time() - start_time < timeout:
#             if not speech_queue.empty():
#                 return speech_queue.get()
#             time.sleep(0.1)  # Non-blocking sleep

#     except Exception as e:
#         print(f"Speech recognition error: {e}")

#     return None  # Return None if timeout occurs

# Main State Machine Loop with Speech Integration
def triaging_state_machine():
    state = TriagingState.INIT_FALL_DETECTED
    past_rewards = []  # Store PRIME reward scores for learning optimization

    print("\nFall detected. Initiating triage...\n")

    # First call to Claude (before user input)
    response = call_claude(state, past_rewards=past_rewards)
    speak_text(response.response_text)  # Speak Claude's response
    state = response.next_state  # Update state immediately
    past_rewards.append(response.trajectory_score)

    # Start loop for user interaction
    while state not in {TriagingState.ALERT_MEDICAL, TriagingState.NOT_FALL, TriagingState.LOW_SEVERITY}:
        print(f"\nCurrent State: {state.value}")  # Debugging: Show Current State

        # Wait for speech input (or timeout after 6 seconds)
        user_input = get_speech_input()

        if user_input is None:
            print("\nNo response detected. Checking again...")
            if state not in {TriagingState.NON_RESPONSIVE, TriagingState.ALERT_MEDICAL}:  # Avoid looping endlessly
                state = TriagingState.NON_RESPONSIVE
                response = call_claude(state, past_rewards=past_rewards)
                speak_text(response.response_text)  # Speak non-responsive prompt
                user_input = get_speech_input()  # One more chance to respond
                if user_input is None:
                    print("\nStill no response. Escalating to emergency services.")
                    state = TriagingState.ALERT_MEDICAL
                    break

        # Process user's response and determine next state dynamically
        response = call_claude(state, user_input, past_rewards=past_rewards)
        
        # Debugging: Show response & next state
        print(f"\nDEBUG - Next State from Claude: {response.next_state} (Score: {response.trajectory_score})")

        # Speak Claude's response
        speak_text(response.response_text)

        # Store trajectory rewards for PRIME optimization
        past_rewards.append(response.trajectory_score)

        # Handle HIGH_SEVERITY with verbal confirmation
        if response.next_state == TriagingState.HIGH_SEVERITY:
            speak_text("This sounds serious. Should I call emergency services?")
            state = TriagingState.AWAITING_CONFIRMATION
            user_input = get_speech_input()

            if user_input and user_input.lower() in {"yes", "call", "help"}:
                speak_text("Understood. Contacting emergency services now.")
                state = TriagingState.ALERT_MEDICAL
                break
            else:
                speak_text("Okay, I will stay with you. Let me know if your condition worsens.")
                state = TriagingState.LOW_SEVERITY

        # Ensure state actually updates
        elif response.next_state in TriagingState:
            state = response.next_state
        else:
            print("Invalid state returned, staying in current state.")

    # Exit message based on final state
    if state == TriagingState.ALERT_MEDICAL:
        speak_text("Emergency services are being alerted now. Stay with me.")
    elif state == TriagingState.NOT_FALL:
        speak_text("It looks like this wasn't a fall after all. Glad you're okay!")
    elif state == TriagingState.LOW_SEVERITY:
        speak_text("This doesn't seem serious, but take it slow. Let me know if you need anything else.")

# Run State Machine
if __name__ == "__main__":
    triaging_state_machine()
