import anthropic
import os
import json
import time
from dotenv import load_dotenv
from pydantic import BaseModel
import instructor

# Load environment variables
load_dotenv()
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

if not ANTHROPIC_API_KEY:
    raise ValueError("Missing Anthropic API key! Please set it in .env file.")

# Initialize Anthropic Client with Instructor
client = instructor.from_anthropic(anthropic.Anthropic(api_key=ANTHROPIC_API_KEY))

# Read the system prompt from file
with open("prime_triage_prompt.txt", "r") as file:
    SYSTEM_PROMPT = file.read()

# Load patient profiles from JSON file
with open("patients.json", "r") as file:
    patient_profiles = json.load(file)

# Define Structured Response Model
class TriageResponse(BaseModel):
    reasoning: str
    decision_speed: int
    information_gain: int
    correctness: int
    false_positives_negatives: int
    total_reward: int
    response_text: str
    exit_conversation: bool
    final_decision: str  # AI's final decision: "ALERT_EMERGENCY" or "DO_NOTHING"

# Define Patient Simulator Model
class PatientSimulator(BaseModel):
    response_text: str

# Function to simulate patient response based on profile
def simulate_patient_response(conversation_history, patient_profile):
    """Generates AI-driven patient responses based on the patient profile."""
    
    system_prompt = f"""
    You are simulating a patient in an emergency triage situation.
    - Context: {patient_profile['context']}
    - You {'have' if patient_profile['actually_fell'] else 'have not'} actually fallen.
    - The correct triage decision is: {patient_profile['right_action']}
    - Your injury severity is: {patient_profile['severity']}
    - Your response clarity is: {patient_profile['response_clarity']}
    
    Given the last message from the AI, respond naturally as a patient would.
    """

    try:
        response = client.chat.completions.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=100,
            temperature=0.7,
            system=system_prompt,
            messages=conversation_history,
            response_model=PatientSimulator
        )

        return response.response_text

    except Exception as e:
        print(f"Patient Simulation Error: {e}")
        return "I... I'm not sure..."  # Default fallback response

def triaging_agent(patient_profile):
    """Handles AI-to-AI triage evaluation."""
    
    print(f"\n🚀 Evaluating Patient {patient_profile['id']} - {patient_profile['context']}\n")

    conversation_history = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": "A possible fall has been detected. Are you okay?"}
    ]

    print(f"👤 **Patient Context:** {patient_profile['context']}")
    print(f"🏥 **Expected Outcome:** {patient_profile['right_action'].upper()}")
    print("\n🔄 **Starting Triage Conversation**\n")

    turn_count = 0  # Track number of conversation turns

    while True:
        turn_count += 1

        # Call Claude (Triage Agent)
        response = call_claude(conversation_history)

        # Log AI response
        print(f"🤖 **AI Agent:** {response.response_text}")

        # Add AI's response to conversation history
        conversation_history.append({"role": "assistant", "content": response.response_text})

        # **Exit if AI determines the conversation is complete**
        if response.exit_conversation:
            print("\nClaude: Triage complete. Ending session.")
            evaluate_triage(response.final_decision, turn_count, patient_profile)
            break

        # Simulate Patient Response
        patient_response = simulate_patient_response(conversation_history, patient_profile)

        # Log Patient Response
        print(f"👤 **Patient:** {patient_response}")

        # Add Patient Response to conversation history
        conversation_history.append({"role": "user", "content": patient_response})

# Function to call Claude API with structured response
def call_claude(conversation_history):
    """Send conversation history to Claude and get a structured response."""
    
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
            exit_conversation=False,
            final_decision="do_nothing"
        )

# Evaluation Function
def evaluate_triage(final_decision, turn_count, patient_profile):
    """Compares Claude's final decision against the correct triage decision."""
    
    correct_action = patient_profile["right_action"]
    correct_decision = final_decision == correct_action

    print("\n🚀 TRIAGE EVALUATION 🚀")
    print(f"- Patient actually fell? {patient_profile['actually_fell']}")
    print(f"- Correct triage decision: {correct_action}")
    print(f"- AI's decision: {final_decision}")
    print(f"- AI was {'✅ CORRECT' if correct_decision else '❌ INCORRECT'}")
    print(f"- Number of conversation turns: {turn_count}")
    print("\n")

# Run evaluation on all patients
if __name__ == "__main__":
    for patient in patient_profiles:
        triaging_agent(patient)
