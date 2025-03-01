import anthropic
import os
import sys
import time
import select
import json
from dotenv import load_dotenv
from pydantic import BaseModel
import instructor
import requests
from main import text_to_speech

# Load environment variables
load_dotenv()
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

if not ANTHROPIC_API_KEY:
    raise ValueError("Missing Anthropic API key! Please set it in .env file.")

# Initialize Anthropic Client with Instructor
client = instructor.from_anthropic(anthropic.Anthropic(api_key=ANTHROPIC_API_KEY))

# Read the system prompt from file
with open("prime_triage_prompt.txt", "r", encoding="utf8") as file:
    SYSTEM_PROMPT = file.read()

# Flask API base URL
FLASK_API_BASE_URL = "http://localhost:5001"

# Define Structured Response Model
class TriageResponse(BaseModel):
    reasoning: str
    decision_speed: int
    information_gain: int
    correctness: int
    false_positives_negatives: int
    total_reward: int
    response_text: str
    exit_conversation: bool  # 🚀 AI now determines whether to exit

# WebSocket Connection for Streaming Messages
@sock.route("/triage")
def triaging_agent(ws):
    """Handles real-time WebSocket communication for triage dialogue."""
    conversation_history = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": "A possible fall has been detected. Are you okay?"}
    ]

    # Send initial user prompt to frontend
    ws.send(json.dumps({"speaker": "user", "message": "A possible fall has been detected. Are you okay?"}))

    print("\nFall detected. Initiating triage...\n")

    while True:
        # Call Claude to get AI response
        response = call_claude(conversation_history)

        # Send AI's response to frontend
        ws.send(json.dumps({"speaker": "ai", "message": response.response_text}))

        # Print debug information in console
        print(f"\nDEBUG - Reasoning: {response.reasoning}")
        print(f"DEBUG - Rewards: Decision Speed: {response.decision_speed}, Information Gain: {response.information_gain}, Correctness: {response.correctness}, False Positives/Negatives: {response.false_positives_negatives}, Total Reward: {response.total_reward}")
        print(f"\nClaude: {response.response_text}")

        # Add Claude's response to conversation history
        conversation_history.append({"role": "assistant", "content": response.response_text})

        # **Exit if AI determines the conversation is complete**
        if response.exit_conversation:
            ws.send(json.dumps({"speaker": "ai", "message": "Triage complete. Ending session."}))
            print("\nClaude: Triage complete. Ending session.")
            break

        # Wait for user response (with timeout)
        user_input = get_user_input_or_timeout()

        if user_input is None:
            print("\nNo response detected. Checking again...")
            conversation_history.append({"role": "user", "content": "(No response detected)"})
            ws.send(json.dumps({"speaker": "user", "message": "(No response detected)"}))
        else:
            # Add user input to conversation history and send to frontend
            conversation_history.append({"role": "user", "content": user_input})
            ws.send(json.dumps({"speaker": "user", "message": user_input}))  

# Function to call Claude API with structured response
def call_claude(conversation_history):
    """Send conversation history to Claude and get a structured response."""
    if len(conversation_history) < 2:
        print("\nDEBUG - Not enough messages, adding initial user message.\n")
        conversation_history.append({"role": "user", "content": "A possible fall has been detected. Are you okay?"})

    try:
        response = client.chat.completions.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=300,
            temperature=0.5,
            system=SYSTEM_PROMPT,
            messages=conversation_history,
            response_model=TriageResponse
        )

        return response

    except Exception as e:
        print(f"Claude API Error: {e}")
        return TriageResponse(
            reasoning="Error processing response.",
            decision_speed=0,
            information_gain=0,
            correctness=0,
            false_positives_negatives=0,
            total_reward=0,
            response_text="I'm having trouble processing right now.",
            exit_conversation=False
        )
    

def speech_to_text():
    """Opens the microphone and listens for speech."""
    try:
        resp = requests.get(f"{FLASK_API_BASE_URL}/speech_to_text")
        ret = resp.json().get("text")
        return ret
    except requests.exceptions.RequestException as e:
        print(f"Error in speech-to-text: {e}")


# Function to handle waiting for a response, then transitioning if needed
def get_user_input_or_timeout(timeout=6):
    """Passively waits for user input for 'timeout' seconds. If no input, returns None."""
    print("\n(Waiting for response... 6 seconds before timeout)")

    ready, _, _ = select.select([sys.stdin], [], [], timeout)
    
    # TODO: add timeout

    return speech_to_text()  # Read input if available
    # return None  # No input received within timeout

# Main Triage Loop
def triaging_agent():
    """Handles back-and-forth triaging until a clear decision is made."""
    conversation_history = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": "A possible fall has been detected. Are you okay?"}  
    ]

    print("\nFall detected. Initiating triage...\n")

    while True:
        # Call Claude with the conversation history
        response = call_claude(conversation_history)

        # Print debug information
        print(f"\nDEBUG - Reasoning: {response.reasoning}")
        print(f"DEBUG - Rewards: Decision Speed: {response.decision_speed}, Information Gain: {response.information_gain}, Correctness: {response.correctness}, False Positives/Negatives: {response.false_positives_negatives}, Total Reward: {response.total_reward}")

        # Print Claude's response
        print(f"\nClaude: {response.response_text}")
        text_to_speech(response.response_text)

        # Add Claude's response to conversation history
        conversation_history.append({"role": "assistant", "content": response.response_text})

        # **Exit automatically if the AI determines it should**
        if response.exit_conversation:
            print("\nClaude: Triage complete. Ending session.")
            break

        # Get user response (or timeout)
        user_input = get_user_input_or_timeout()

        if user_input is None:
            print("\nNo response detected. Checking again...")
            conversation_history.append({"role": "user", "content": "(No response detected)"})
        else:
            # Add user input to conversation history
            conversation_history.append({"role": "user", "content": user_input})

# Run Agent
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002, debug=True)
