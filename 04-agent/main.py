
from dotenv import load_dotenv
import google.generativeai as genai
import json
import requests
import os

load_dotenv()
def get_weather(city: str):
    url = f"https://wttr.in/{city}?format=%C+%t"
    response = requests.get(url)
    if response.status_code == 200:
        return f"The weather in {city} is {response.text}."
    return "Something went wrong"
# SYSTEM_PROMPT = f"""
# You are a helpful AI Assistant who is specialized in resolving user queries.
# You work in a step-by-step loop: plan, action, observe.

# For any user query, you must follow this sequence:
# 1. First, create one or more 'plan' steps to outline your approach.
# 2. Next, create a single 'action' step to call a tool.
# 3. Finally, after observing the result, create a final 'output' step to answer the user.

# Rules:
# - You MUST respond with ONLY ONE valid JSON object per turn. Do not include any extra text or formatting.
# - If you cannot fulfill the request, respond with a valid JSON object explaining why.
# - CRITICAL RULE: For any file writing, creation, or modification, you MUST use the 'write_to_file' tool.
# - The 'run_command' tool is ONLY for executing shell commands that DO NOT write to files (e.g., 'ls -l', 'pwd').
# - WARNING: Using 'run_command' for file writing is a strict violation and will fail.

# Output JSON Format:
# {{
#     "step": "string",
#     "content": "string",
#     "function": "The name of function if the step is action",
#     "input": "The input parameter for the function (for write_to_file, pass a dict with 'filename' and 'content')"
# }}

# Available Tools:
# - "get_weather": Takes a city name as an input and returns the current weather for the city
# - "run_command": Takes a linux command as a string and executes the command and returns the output after executing it. DO NOT use for file writing.
# - "write_to_file": Takes a dict with 'filename' and 'content' and writes the content to the file. Returns success or error message. ALWAYS use for file writing.

# Example for writing to file:
# User Query: Write 'hello world' to hello.txt
# Output: {{ "step": "plan", "content": "The user wants to write text to a file." }}
# Output: {{ "step": "plan", "content": "From the available tools I should call write_to_file." }}
# Output: {{ "step": "action", "function": "write_to_file", "input": {{"filename": "hello.txt", "content": "hello world"}} }}
# Output: {{ "step": "observe", "output": "Successfully wrote to hello.txt." }}
# Output: {{ "step": "output", "content": "The text was written to hello.txt." }}
# """
SYSTEM_PROMPT = f"""
You are an AI assistant that controls tools. You work in a strict, step-by-step loop.

**CRITICAL RULES:**
1.  **SINGLE JSON RESPONSE:** You MUST respond with ONLY ONE valid JSON object per turn. Nothing else. No extra text, no explanations, and NO multiple JSON objects.
2.  **FILE WRITING:** To write, create, or change a file, you MUST use the `write_to_file` tool.
3.  **COMMANDS:** Use the `run_command` tool ONLY for simple shell commands that DO NOT write files (e.g., `ls -l`, `pwd`).
4.  **STAY IN THE LOOP:** Respond with a 'plan'. Wait for the next prompt. Respond with an 'action'. Wait for the next prompt. Respond with an 'output'. Do not combine these steps.

**JSON OUTPUT FORMAT:**
{{
    "step": "plan | action | output",
    "content": "Your thought, or the final response to the user.",
    "function": "tool_name (This key is ONLY for the 'action' step)",
    "input": "tool_input (This key is ONLY for the 'action' step)"
}}

**EXAMPLE OF A CORRECT CONVERSATION:**

User Query: "Write 'Gemini' to a file called gemini.txt"

Your First Response:
{{ "step": "plan", "content": "The user wants to write text to a file. I must use the write_to_file tool." }}

Your Second Response (after receiving the observation from the plan):
{{ "step": "action", "function": "write_to_file", "input": {{"filename": "gemini.txt", "content": "Gemini"}} }}

Your Third Response (after receiving the observation from the action):
{{ "step": "output", "content": "I have successfully written the text to gemini.txt." }}
"""
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=GOOGLE_API_KEY)

model = genai.GenerativeModel("models/gemini-2.0-flash-thinking-exp")

import subprocess

def run_command(params):
    # Check if the input is a dictionary or a plain string
    if isinstance(params, dict):
        cmd = params.get('command')
    elif isinstance(params, str):
        cmd = params
    else:
        return "Error: Invalid input type for run_command. Must be a dict or a string."

    if not cmd:
        return "Error: Command is empty or not found in input."

    try:
        # Execute the command
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        # Return stdout if it exists, otherwise a success message
        return result.stdout.strip() if result.stdout.strip() else "Command executed successfully."
    except subprocess.CalledProcessError as e:
        # Return the error message from stderr
        return f"Error executing command:\n{e.stderr.strip()}"
    
    
def write_to_file(params):
    """
    params: dict with keys 'filename' and 'content'
    """
    filename = params.get('filename')
    content = params.get('content')
    if not filename or content is None:
        return "Error: 'filename' and 'content' required."
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"Successfully wrote to {filename}."
    except Exception as e:
        return f"Error writing to file: {e}"
available_tools = {
    "get_weather": get_weather,
    "run_command": run_command,
    "write_to_file": write_to_file
}
messages = [
  { "role": "system", "content": SYSTEM_PROMPT }
]

import re

def extract_json(text):
    """Extract the first valid JSON object from text."""
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except Exception:
            return None
    return None

while True:
    query = input("> ")
    messages.append({ "role": "user", "content": query })
    while True:
        prompt = "\n".join([f"{m['role']}: {m['content']}" for m in messages])
        response = model.generate_content(prompt)
        content = response.text
        messages.append({ "role": "assistant", "content": content })
        parsed_response = extract_json(content)
        if not parsed_response:
            print("Error: Gemini response is not valid JSON.")
            print(content)
            break

        if parsed_response.get("step") == "plan":
            print(f"🧠: {parsed_response.get('content')}")
            continue

        if parsed_response.get("step") == "action":
            tool_name = parsed_response.get("function")
            tool_input = parsed_response.get("input")

            print(f"🛠️: Calling Tool:{tool_name} with input {tool_input}")

            if available_tools.get(tool_name):
                output = available_tools[tool_name](tool_input)
                messages.append({ "role": "user", "content": json.dumps({ "step": "observe", "output": output }) })
                continue

        if parsed_response.get("step") == "output":
            print(f"🤖: {parsed_response.get('content')}")
            break