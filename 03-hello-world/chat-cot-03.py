from google import genai
import os
import sys
from dotenv import load_dotenv
from google.genai.types import Content, Part, GenerateContentConfig, Schema, Type
import json

import anthropic

client = anthropic.Anthropic(
    # defaults to os.environ.get("ANTHROPIC_API_KEY")
    api_key="my_api_key",
)
message = client.messages.create(
    model="claude-opus-4-1-20250805",
    max_tokens=1024,
    messages=[
        {"role": "user", "content": "Hello, Claude"}
    ]
)

# Load environment variables from .env file
load_dotenv()

api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    print("ERROR: Set GOOGLE_API_KEY environment variable or pass api_key to genai.Client(...)", file=sys.stderr)
    sys.exit(1)

client = genai.Client(api_key=api_key)

# chain of thought: the model is encouraged to break down reasoning step by step before arriving at an answer.

SYSTEM_PROMPT = """
 
 you are a helpful ai assistant who is specialized in resolving user's query.
 for the given user input, analyze the input and break down the problem step by step.

 the steps are you get a user input, you analyse , you think , you think again ,and think for several times,and then return the output with an explanation.

 follow the steps in seequence that is "analyse","think","output","validate" and finally "result".

 
    Rules:
    1. Follow the strict JSON output as per schema.
    2. Always perform one step at a time and wait for the next input.
    3. Carefully analyse the user query,

    Output Format:
    {{ "step": "string", "content": "string" }}

    Example:
    Input: What is 2 + 2
    Output: {{ "step": "analyse", "content": "Alight! The user is interest in maths query and he is asking a basic arthematic operation" }}
    Output: {{ "step": "think", "content": "To perform this addition, I must go from left to right and add all the operands." }}
    Output: {{ "step": "output", "content": "4" }}
    Output: {{ "step": "validate", "content": "Seems like 4 is correct ans for 2 + 2" }}
    Output: {{ "step": "result", "content": "2 + 2 = 4 and this is calculated by adding all numbers" }}

    Example:
    Input: What is 2 + 2 * 5 / 3
    Output: {{ "step": "analyse", "content": "Alight! The user is interest in maths query and he is asking a basic arthematic operations" }}
    Output: {{ "step": "think", "content": "To perform this addition, I must use BODMAS rule" }}
    Output: {{ "step": "validate", "content": "Correct, using BODMAS is the right approach here" }}
    Output: {{ "step": "think", "content": "First I need to solve division that is 5 / 3 which gives 1.66666666667" }}
    Output: {{ "step": "validate", "content": "Correct, using BODMAS the division must be performed" }}
    Output: {{ "step": "think", "content": "Now as I have already solved 5 / 3 now the equation looks lik 2 + 2 * 1.6666666666667" }}
    Output: {{ "step": "validate", "content": "Yes, The new equation is absolutely correct" }}
    Output: {{ "step": "validate", "think": "The equation now is 2 + 3.33333333333" }}
    and so on.....
"""

config = GenerateContentConfig(
    response_mime_type="application/json",
    response_schema=Schema(
        type=Type.OBJECT,
        properties={
            "step": Schema(type=Type.STRING),
            "content": Schema(type=Type.STRING),
        },
        required=["step", "content"],
    ),
)

# Seed the previous step you provided so the model advances to the next one
prev_step = {
    "step": "analyse",
    "content": (
        "The user is asking to solve a mathematical expression involving addition, "
        "multiplication, and division. I need to follow the order of operations "
        "(PEMDAS/BODMAS) to get the correct answer."
    ),
}

prev_step1 = {
  "step": "think",
  "content": "According to the order of operations, I need to perform multiplication and division before addition. So, I will first calculate 2 * 5, then divide the result by 3, and finally add 2 to the result."
}

prev_step2 = {
  "step": "output",
  "content": "2 * 5 = 10, then 10 / 3 = 3.333..., and finally 2 + 3.333... = 5.333..."
}

prev_step3={
  "step": "validate",
  "content": "The calculation appears to be correct, following the order of operations (PEMDAS/BODMAS)."
}

# --- One-shot seeded example (commented, preserved) ---
# contents = [
#     Content(role="user", parts=[Part(text=SYSTEM_PROMPT.strip())]),
#     Content(role="user", parts=[Part(text="What is 2 + 2 * 5 / 3")]),
#     Content(role="model", parts=[Part(text=json.dumps(prev_step))]),
#     Content(role="model", parts=[Part(text=json.dumps(prev_step1))]),
#     Content(role="model", parts=[Part(text=json.dumps(prev_step2))]),
#     Content(role="model", parts=[Part(text=json.dumps(prev_step3))]),
#     Content(role="user", parts=[Part(text="Next step only. Continue to the next step in the sequence.")]),
# ]
# response = client.models.generate_content(
#     model="gemini-2.0-flash",  # or "gemini-2.5-flash" if enabled
#     contents=contents,
#     config=config,
# )
# try:
#     obj = json.loads(response.text)
#     print(json.dumps(obj, indent=2))
# except json.JSONDecodeError:
#     print(response.text)

# --- Interactive loop (OpenAI-style) ---
def _external_validate_thought(thought: str) -> dict:
    """Stub external validator; returns a validate step JSON."""
    return {
        "step": "validate",
        "content": "(external) Validation looks reasonable: " + thought[:200],
    }

messages: list[Content] = [Content(role="user", parts=[Part(text=SYSTEM_PROMPT.strip())])]
query = input("> ")
messages.append(Content(role="user", parts=[Part(text=query)]))

max_steps = 12
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

    if step == "think":
        # Example: call Claude (stubbed here) and append as validate
        validate_obj = _external_validate_thought(content)
        messages.append(Content(role="model", parts=[Part(text=json.dumps(validate_obj))]))
        continue

    if step != "result":
        print("          🧠:", content)
        messages.append(Content(role="user", parts=[Part(text="Next step only.")]))
        continue

    print("🤖:", content)
    break
