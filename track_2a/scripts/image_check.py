"""Does the endpoint accept a page image? One request, for information only (session 11, step 3d).

Run from track_2a/ (.env for the endpoint; pdftoppm installed):

    python3 scripts/image_check.py --pdf output/booklets_dev/<booklet>.pdf --page 8 --out docs/runs/<folder>

Renders one booklet page as a PNG (pdftoppm, 72 dpi, in a temporary folder), sends it with the question "What is the
heading of this page?" as an OpenAI-style image part, and records the answer (or the error), the tokens and the
backend. The image and the page text are not written; the answer is a heading of an official booklet page.
"""

import argparse
import base64
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src import env, llm  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pdf", type=Path, required=True)
    ap.add_argument("--page", type=int, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    env.load_env_file()
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(["pdftoppm", "-r", "72", "-png", "-f", str(args.page), "-l", str(args.page), "-singlefile",
                        str(args.pdf), f"{tmp}/page"], check=True)
        png = Path(f"{tmp}/page.png").read_bytes()
    url = "data:image/png;base64," + base64.b64encode(png).decode("ascii")
    messages = [{"role": "user", "content": [{"type": "text", "text": "What is the heading of this page?"},
                                             {"type": "image_url", "image_url": {"url": url}}]}]
    record = {"booklet": args.pdf.name, "page": args.page, "image_bytes": len(png), "dpi": 72}
    try:
        result = llm.chat(messages, max_tokens=60)
        record.update(accepted=True, answer=result.text, input_tokens=result.input_tokens,
                      output_tokens=result.output_tokens, backend=result.endpoint.get("system_fingerprint"))
    except llm.LLMError as e:
        record.update(accepted=False, error=str(e)[:300], backend=(getattr(e, "endpoint", None) or {}).get(
            "system_fingerprint"))
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "image_check.json").write_text(json.dumps(record, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(record, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
