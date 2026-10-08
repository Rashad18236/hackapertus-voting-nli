"""Send one short message to the model and print the answer and token counts.

Run from track_2a/:  python3 scripts/smoke_test.py

Reads LLM_NAME, LLM_BASE_URL and LLM_API_KEY from the shell, or from .env if
they are not exported. Never prints their values.
"""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src import llm  # noqa: E402


def load_env_file(path):
    """Minimal .env reader: KEY=VALUE lines; shell variables take precedence."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


def main():
    load_env_file(ROOT / ".env")
    result = llm.chat([{"role": "user", "content": "Hallo, antworte in einem Satz."}], max_tokens=100)
    print("Answer:       ", result.text.strip())
    print("Input tokens: ", result.input_tokens)
    print("Output tokens:", result.output_tokens)
    print("Elapsed ms:   ", result.elapsed_ms)


if __name__ == "__main__":
    main()
