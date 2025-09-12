from google import genai
import os
import sys
import json
from dotenv import load_dotenv
from google.genai.types import Content, Part, GenerateContentConfig, Schema, Type

# Load environment variables from .env file
load_dotenv()

api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    print("ERROR: Set GOOGLE_API_KEY environment variable or pass api_key to genai.Client(...)", file=sys.stderr)
    sys.exit(1)

client = genai.Client(api_key=api_key)

ALLOWED_STEPS = ["analyse", "think", "output", "validate", "result"]

# Focused system guidance: tone like Piyush, but output must be STRICT JSON with next step only.
SYSTEM_PROMPT = """
You are the AI persona of Piyush Garg. Use his tone and style in word choice, but your OUTPUT MUST BE STRICT JSON ONLY.

Contract:
- Always respond with a single JSON object exactly matching this schema: {"step": "string", "content": "string"}.
- step must be one of: analyse, think, output, validate, result (lowercase).
- Do exactly ONE step per response.
- No greetings, no questions like "What else can I help with?", no chit-chat, no emojis.
- content must be concise, directly about solving the user's current query, and must not repeat prior content verbatim.
- Start with step="analyse" for the user's question, then alternate think/validate as needed, then output, then result.
- When you reach a decisive final answer and brief rationale, return step="result".

Important: Return JSON only; do not include any extra text before or after the JSON.
"""

# --- One-shot demo (kept for reference; now commented) ---
# response = client.models.generate_content(
#     model="gemini-2.0-flash",  # or "gemini-2.5-flash" if enabled
#     contents=[
#         Content(role="user", parts=[Part(text=SYSTEM_PROMPT.strip())]),
#         Content(role="user", parts=[Part(text="Hey, My name is Piyush")]),
#         Content(role="assistant", parts=[Part(text="Alright Piyush, let's cut the introductions. You got Python problems? I've got Python solutions. Let's see what you've got.")]),
#         Content(role="user", parts=[Part(text="How do make chicken for best protein intake?")]),
#     ],
# )
# print(response.text)

# --- CoT interactive loop with JSON enforcement ---
config = GenerateContentConfig(
    response_mime_type="application/json",
    temperature=0.2,
    max_output_tokens=256,
    response_schema=Schema(
        type=Type.OBJECT,
        properties={
            "step": Schema(type=Type.STRING, enum=ALLOWED_STEPS),
            "content": Schema(type=Type.STRING),
        },
        required=["step", "content"],
    ),
)

def _external_validate_thought(thought: str) -> dict:
    return {
        "step": "validate",
        "content": "(external) Validation looks reasonable: " + thought[:200],
    }

messages: list[Content] = [Content(role="user", parts=[Part(text=SYSTEM_PROMPT.strip())])]
query = input("> ")
messages.append(Content(role="user", parts=[Part(text=query)]))

max_steps = 12
think_streak = 0
last_content = ""
while True and max_steps > 0:
    max_steps -= 1
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=messages,
        config=config,
    )

    # Save assistant JSON back into the conversation
    messages.append(Content(role="model", parts=[Part(text=response.text)]))

    try:
        parsed_response = json.loads(response.text)
    except json.JSONDecodeError:
        print(response.text)
        break

    step = str(parsed_response.get("step", "")).lower()
    content = str(parsed_response.get("content", ""))

    # Guard: enforce allowed steps
    if step not in ALLOWED_STEPS:
        messages.append(Content(role="user", parts=[Part(text=json.dumps({
            "step": "validate",
            "content": "Step invalid. Use one of: analyse, think, output, validate, result. Reply again as JSON only."
        }))]))
        continue

    # Guard: avoid repeating the same content
    if content.strip() == last_content.strip():
        messages.append(Content(role="user", parts=[Part(text="Content repeated. Provide the next distinct step. JSON only.")]))
        continue
    last_content = content

    if step == "think":
        validate_obj = _external_validate_thought(content)
        messages.append(Content(role="model", parts=[Part(text=json.dumps(validate_obj))]))
        think_streak += 1
        if think_streak >= 3:
            # Nudge to produce concrete output after too many thinks
            messages.append(Content(role="user", parts=[Part(text="Too many 'think' steps. Move to 'output' with a concrete answer. JSON only.")]))
        else:
            messages.append(Content(role="user", parts=[Part(text="Next step only.")]))
        continue
    else:
        think_streak = 0

    if step != "result":
        print(f"          🧠 [{step}]:", content)
        messages.append(Content(role="user", parts=[Part(text="Next step only. JSON only.")]))
        continue

    print("🤖:", content)
    break
# Example response:
# Okay, let's break down how AI works. It's a broad field, so I'll focus on the ...
#
# Here's a simplified overview:
# ...