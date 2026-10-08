"""Send one short message to the model and print the answer and token counts.

Run from track_2a/:  python3 scripts/smoke_test.py

Reads LLM_NAME, LLM_BASE_URL and LLM_API_KEY from the shell, or from .env if
they are not exported. Never prints their values.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src import env, llm  # noqa: E402


def main():
    env.load_env_file()
    result = llm.chat([{"role": "user", "content": "Hallo, antworte in einem Satz."}], max_tokens=100)
    print("Answer:       ", result.text.strip())
    print("Input tokens: ", result.input_tokens)
    print("Output tokens:", result.output_tokens)
    print("Elapsed ms:   ", result.elapsed_ms)


if __name__ == "__main__":
    main()
