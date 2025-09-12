from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from typing import Generator, Iterable, List, Dict

from dotenv import load_dotenv
from google import genai
from google.genai.types import Content, Part, GenerateContentConfig, Schema, Type


ALLOWED_STEPS: List[str] = ["analyse", "think", "output", "validate", "result"]


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


@dataclass
class PersonaEngine:
    api_key: str | None = None
    model: str = "gemini-2.0-flash"
    temperature: float = 0.2
    max_output_tokens: int = 256
    max_steps: int = 12

    def __post_init__(self) -> None:
        # Load env if present
        load_dotenv()
        key = self.api_key or os.getenv("GOOGLE_API_KEY")
        if not key:
            print(
                "ERROR: Set GOOGLE_API_KEY environment variable or pass api_key to PersonaEngine(...)",
                file=sys.stderr,
            )
            raise RuntimeError("Missing GOOGLE_API_KEY")
        self.client = genai.Client(api_key=key)
        self.config = GenerateContentConfig(
            response_mime_type="application/json",
            temperature=self.temperature,
            max_output_tokens=self.max_output_tokens,
            response_schema=Schema(
                type=Type.OBJECT,
                properties={
                    "step": Schema(type=Type.STRING, enum=ALLOWED_STEPS),
                    "content": Schema(type=Type.STRING),
                },
                required=["step", "content"],
            ),
        )

    def _external_validate_thought(self, thought: str) -> Dict[str, str]:
        return {
            "step": "validate",
            "content": "(external) Validation looks reasonable: " + thought[:200],
        }

    def step_generator(self, query: str) -> Generator[Dict[str, str], None, None]:
        messages: List[Content] = [Content(role="user", parts=[Part(text=SYSTEM_PROMPT.strip())])]
        messages.append(Content(role="user", parts=[Part(text=query)]))

        think_streak = 0
        last_content = ""
        remaining = self.max_steps

        while remaining > 0:
            remaining -= 1
            response = self.client.models.generate_content(
                model=self.model,
                contents=messages,
                config=self.config,
            )
            messages.append(Content(role="model", parts=[Part(text=response.text)]))

            try:
                parsed = json.loads(response.text)
            except json.JSONDecodeError:
                # yield raw text in a fallback step
                yield {"step": "output", "content": response.text}
                break

            step = str(parsed.get("step", "")).lower()
            content = str(parsed.get("content", ""))

            # Validate step and de-dup content
            if step not in ALLOWED_STEPS:
                messages.append(
                    Content(
                        role="user",
                        parts=[
                            Part(
                                text=json.dumps(
                                    {
                                        "step": "validate",
                                        "content": (
                                            "Step invalid. Use one of: analyse, think, output, "
                                            "validate, result. Reply again as JSON only."
                                        ),
                                    }
                                )
                            )
                        ],
                    )
                )
                continue

            if content.strip() == last_content.strip():
                messages.append(
                    Content(role="user", parts=[Part(text="Content repeated. Provide the next distinct step. JSON only.")])
                )
                continue
            last_content = content

            # Yield current step
            yield {"step": step, "content": content}

            # Steering
            if step == "think":
                validate_obj = self._external_validate_thought(content)
                messages.append(Content(role="model", parts=[Part(text=json.dumps(validate_obj))]))
                think_streak += 1
                if think_streak >= 3:
                    messages.append(
                        Content(
                            role="user",
                            parts=[Part(text="Too many 'think' steps. Move to 'output' with a concrete answer. JSON only.")],
                        )
                    )
                else:
                    messages.append(Content(role="user", parts=[Part(text="Next step only.")]))
                continue
            else:
                think_streak = 0

            if step != "result":
                messages.append(Content(role="user", parts=[Part(text="Next step only. JSON only.")]))
                continue

            # We reached result, stop.
            break

    def run(self, query: str) -> Dict[str, object]:
        steps: List[Dict[str, str]] = list(self.step_generator(query))
        result = next((s for s in reversed(steps) if s.get("step") == "result"), None)
        return {"steps": steps, "result": result}
