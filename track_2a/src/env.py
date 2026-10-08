"""Minimal .env reader, so we need no extra dependency.

Reads KEY=VALUE lines. Variables already set in the environment win, so values
exported in the shell take precedence over .env. Values are never printed.
Inside Docker there is no .env file (see .dockerignore); docker run passes
the variables instead.
"""

import os
from pathlib import Path


def load_env_file(path=Path(__file__).resolve().parent.parent / ".env"):
    path = Path(path)
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())
