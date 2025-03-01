import anthropic
import json
import csv
import os
from dotenv import load_dotenv
import time

# Load environment variables from .env
load_dotenv()

# Get API key from environment variables
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

if not ANTHROPIC_API_KEY:
    raise ValueError("Missing Anthropic API key! Please set it in .env file.")

# Initialize Anthropic client
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

# Read prompt template from file
with open("datagen_prompt.txt", "r") as file:
    SYSTEM_PROMPT = file.read()

# Define number of total conversations to generate
TARGET_CONVERSATIONS = 100
CONVERSATIONS_PER_BATCH = 10
NUM_BATCHES = (TARGET_CONVERSATIONS + CONVERSATIONS_PER_BATCH - 1) // CONVERSATIONS_PER_BATCH  # Ceiling division

# Function to generate multiple triage cases at once
def generate_triage_batch():
    response = client.messages.create(
        model="claude-3-7-sonnet-20250219",
        max_tokens=4000,  # Increased for batch generation
        temperature=0.8,
        system=SYSTEM_PROMPT,
        messages=[
            {"role": "user", "content": f"Generate exactly {CONVERSATIONS_PER_BATCH} different triage conversations in valid JSON array format as specified."}
        ]
    )
    
    # Extract text content
    content = response.content[0].text
    
    # Try to parse JSON
    try:
        # First try direct parsing
        return json.loads(content)
    except json.JSONDecodeError:
        # Try to extract JSON if it's wrapped in markdown code blocks
        if "```json" in content and "```" in content.split("```json", 1)[1]:
            json_content = content.split("```json", 1)[1].split("```", 1)[0].strip()
            return json.loads(json_content)
        elif "```" in content and "```" in content.split("```", 1)[1]:
            json_content = content.split("```", 1)[1].split("```", 1)[0].strip()
            return json.loads(json_content)
        # If still no success, raise the error
        raise

# Generate dataset
all_data = []
for i in range(NUM_BATCHES):
    print(f"Generating batch {i+1}/{NUM_BATCHES} (conversations {i*CONVERSATIONS_PER_BATCH+1}-{min((i+1)*CONVERSATIONS_PER_BATCH, TARGET_CONVERSATIONS)})...")
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            batch_data = generate_triage_batch()
            
            # Validate that we got enough conversations
            if not isinstance(batch_data, list):
                print(f"⚠️ Warning: Expected list but got {type(batch_data)}. Retrying...")
                continue
                
            if len(batch_data) < CONVERSATIONS_PER_BATCH:
                print(f"⚠️ Warning: Only received {len(batch_data)} conversations instead of {CONVERSATIONS_PER_BATCH}. Retrying...")
                continue
                
            all_data.extend(batch_data[:CONVERSATIONS_PER_BATCH])  # Only take the requested number
            print(f"✓ Successfully generated batch {i+1} with {len(batch_data[:CONVERSATIONS_PER_BATCH])} conversations")
            break
            
        except json.JSONDecodeError as e:
            print(f"❌ Error parsing JSON for batch {i+1}, attempt {attempt+1}: {e}")
            if attempt == max_retries - 1:
                print("All retries failed. Moving to next batch.")
            else:
                print("Retrying...")
                time.sleep(2)  # Brief pause before retry
                
        except Exception as e:
            print(f"❌ Unexpected error for batch {i+1}, attempt {attempt+1}: {e}")
            if attempt == max_retries - 1:
                print("All retries failed. Moving to next batch.")
            else:
                print("Retrying...")
                time.sleep(2)  # Brief pause before retry

# Trim to target size if we got more conversations than needed
if len(all_data) > TARGET_CONVERSATIONS:
    all_data = all_data[:TARGET_CONVERSATIONS]

# Save to JSON
json_filename = "triage_synthetic_data.json"
with open(json_filename, "w") as json_file:
    json.dump(all_data, json_file, indent=4)

# Save to CSV
csv_filename = "triage_synthetic_data.csv"
with open(csv_filename, "w", newline="") as csv_file:
    fieldnames = ["situation_context", "conversation_log", "final_decision", "total_score"]
    writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
    
    writer.writeheader()
    for entry in all_data:
        try:
            # Extract total score from the nested structure
            total_score = entry["Trajectory Efficiency Score"]["Total Score"] if isinstance(entry["Trajectory Efficiency Score"], dict) else "N/A"
                
            writer.writerow({
                "situation_context": entry["Situation Context"],
                "conversation_log": entry["Conversation Log"],
                "final_decision": entry["Final Triage Decision"],
                "total_score": total_score
            })
        except KeyError as e:
            print(f"Missing expected key in data: {e}")
            print(f"Entry structure: {entry.keys() if isinstance(entry, dict) else type(entry)}")

print(f"✅ Data generation complete! Generated {len(all_data)} valid conversations.")
print(f"JSON saved to {json_filename}, CSV saved to {csv_filename}.")