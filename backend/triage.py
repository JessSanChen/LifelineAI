import anthropic
import os
import sys
import time
import select
from dotenv import load_dotenv
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
with open("prime_triage_prompt.txt", "r") as file:
    SYSTEM_PROMPT = file.read()

# Define Structured Response Model
class TriageResponse(BaseModel):
    reasoning: str
    decision_speed: int
    information_gain: int
    correctness: int
    false_positives_negatives: int
    total_reward: int
    response_text: str
    action: str  # One of: "CONTINUE", "ALERT_MEDICAL", "LOW_SEVERITY", "NOT_FALL"

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
            action="CONTINUE"
        )

# Function to handle waiting for a response, then transitioning if needed
def get_user_input_or_timeout(timeout=6):
    """Passively waits for user input for 'timeout' seconds. If no input, returns None."""
    print("\n(Waiting for response... 6 seconds before timeout)")

    ready, _, _ = select.select([sys.stdin], [], [], timeout)
    
    if ready:
        return sys.stdin.readline().strip()  # Read input if available
    return None  # No input received within timeout

# Main Triage Loop
def triaging_agent():
    """Handles back-and-forth triaging until a clear decision is made."""
    conversation_history = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": "A possible fall has been detected. Are you okay?"}  # ✅ Ensures we have an initial message
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

        # Add Claude's response to conversation history
        conversation_history.append({"role": "assistant", "content": response.response_text})

        # **Check if we need to exit the loop**
        if response.action == "ALERT_MEDICAL":
            print("\nClaude: Emergency services are being alerted now. Stay with me.")
            break
        elif response.action == "LOW_SEVERITY":
            print("\nClaude: This doesn’t seem serious, but take it slow. Let me know if you need anything else.")
            break
        elif response.action == "NOT_FALL":
            print("\nClaude: It looks like this wasn’t a fall after all. Glad you’re okay!")
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
    triaging_agent()
