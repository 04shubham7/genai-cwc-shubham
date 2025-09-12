from __future__ import annotations

import sys
from persona.engine import PersonaEngine


def main() -> int:
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
    else:
        query = input("> ")

    engine = PersonaEngine()
    print("\n-- Steps --")
    result = None
    for s in engine.step_generator(query):
        print(f"[{s['step']}] {s['content']}")
        if s.get("step") == "result":
            result = s
            break
    print("\n-- Result --")
    if result:
        print(result.get("content", ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
