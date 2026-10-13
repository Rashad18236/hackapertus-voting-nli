"""Download facebook/m2m100_418M and convert it to CTranslate2 int8 for src/translate.py (robustness experiments).

Run once from track_2a/. The conversion needs PyTorch and transformers, which the pipeline itself never needs, so
it runs in a throwaway virtual environment outside the project:

    python3 scripts/fetch_mt_model.py [--out models/m2m100_418M-ct2] [--venv /tmp/mt-convert]

It creates the venv (if missing), installs torch, transformers, sentencepiece, protobuf and ctranslate2 into it,
and runs ct2-transformers-converter with int8 quantization. Result: about 476 MB in --out (model.bin, the
SentencePiece model and the vocabulary). models/ is git-ignored. Then run with MT_MODEL_DIR=models/m2m100_418M-ct2
and `pip install -r requirements-experiments.txt` in the project's environment.

Model: https://huggingface.co/facebook/m2m100_418M (MIT licence).
"""

import argparse
import subprocess
import sys
from pathlib import Path


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--out", type=Path, default=Path("models/m2m100_418M-ct2"))
    p.add_argument("--venv", type=Path, default=Path("/tmp/mt-convert"))
    args = p.parse_args()
    if (args.out / "model.bin").is_file():
        print(f"{args.out} already has a model; nothing to do")
        return 0
    python = args.venv / "bin" / "python"
    if not python.is_file():
        subprocess.run([sys.executable, "-m", "venv", str(args.venv)], check=True)
    subprocess.run([str(python), "-m", "pip", "install", "-q", "torch", "transformers", "sentencepiece", "protobuf",
                    "ctranslate2"], check=True)
    subprocess.run([str(args.venv / "bin" / "ct2-transformers-converter"), "--model", "facebook/m2m100_418M",
                    "--output_dir", str(args.out), "--quantization", "int8", "--copy_files",
                    "sentencepiece.bpe.model", "tokenizer_config.json", "special_tokens_map.json", "vocab.json"],
                   check=True)
    print(f"converted model in {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
