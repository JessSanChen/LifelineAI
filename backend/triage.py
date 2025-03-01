import anthropic
import os
import time
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

# Define Structured Response Model
class TriageResponse(BaseModel):
    response_text: str
    next_state: TriagingState

# Function to call Claude API with structured response
def call_claude(state, user_input=None):
    user_prompt = user_input if user_input else "What should happen next?"

    try:
        response = client.chat.completions.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=150,
            temperature=0.5,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
            response_model=TriageResponse
        )

        return response

    except Exception as e:
        print(f"Claude API Error: {e}")
        return TriageResponse(response_text="I'm having trouble processing right now.", next_state=state)

# Function to handle waiting for a response, then transitioning if needed
def get_user_input_or_timeout():
    """Waits for 6 seconds for user input; if no response, returns None."""
    start_time = time.time()
    while time.time() - start_time < 6:
        user_input = input("\nYour Response (or wait for timeout): ").strip()
        if user_input:
            return user_input
    return None  # Timeout reached

# Main State Machine Loop
def triaging_state_machine():
    state = TriagingState.INIT_FALL_DETECTED
    print("\nFall detected. Initiating triage...\n")

    # First call to Claude (before user input)
    response = call_claude(state)
    print(f"\nClaude: {response.response_text}")
    state = response.next_state  # Update state immediately

    # Start loop for user interaction
    while state not in {TriagingState.ALERT_MEDICAL, TriagingState.NOT_FALL, TriagingState.LOW_SEVERITY}:
        print(f"\nCurrent State: {state.value}")  # Debugging: Show Current State

        # Wait for user response (or timeout after 6 seconds)
        user_input = get_user_input_or_timeout()

        if user_input is None:
            print("\nNo response detected. Checking again...")
            if state not in {TriagingState.NON_RESPONSIVE, TriagingState.ALERT_MEDICAL}:  # Avoid looping endlessly
                state = TriagingState.NON_RESPONSIVE
                response = call_claude(state)
                print(f"\nClaude: {response.response_text}")
                user_input = get_user_input_or_timeout()  # One more chance to respond
                if user_input is None:
                    print("\nStill no response. Escalating to emergency services.")
                    state = TriagingState.ALERT_MEDICAL
                    break

        # Process user's response and determine next state dynamically
        response = call_claude(state, user_input)
        
        # Debugging: Show response & next state
        print(f"\nDEBUG - Next State from Claude: {response.next_state}")

        # Always print Claude's response before continuing
        if response.response_text:
            print(f"\nClaude: {response.response_text}")
        else:
            print("\nClaude: I didn't catch that. Can you repeat?")

        # Handle HIGH_SEVERITY with verbal confirmation
        if response.next_state == TriagingState.HIGH_SEVERITY:
            print("\nClaude: This sounds serious. Should I call emergency services?")
            state = TriagingState.AWAITING_CONFIRMATION
            user_input = get_user_input_or_timeout()
            
            if user_input and user_input.lower() in {"yes", "call", "help"}:
                print("\nClaude: Understood. Contacting emergency services now.")
                state = TriagingState.ALERT_MEDICAL
                break
            else:
                print("\nClaude: Okay, I will stay with you. Let me know if your condition worsens.")
                state = TriagingState.LOW_SEVERITY

        # Ensure state actually updates
        elif response.next_state in TriagingState:
            state = response.next_state
        else:
            print("Invalid state returned, staying in current state.")

    # Exit message based on final state
    if state == TriagingState.ALERT_MEDICAL:
        print("\nClaude: Emergency services are being alerted now. Stay with me.")
    elif state == TriagingState.NOT_FALL:
        print("\nClaude: It looks like this wasn't a fall after all. Glad you're okay!")
    elif state == TriagingState.LOW_SEVERITY:
        print("\nClaude: This doesn't seem serious, but take it slow. Let me know if you need anything else.")

# Run State Machine
if __name__ == "__main__":
    triaging_state_machine()
