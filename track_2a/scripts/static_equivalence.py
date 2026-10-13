"""Session 12, step 1a: model S's vectors (src/static_embed.py: tokenizers and numpy) against the reference library's
(sentence-transformers). Development machine only: the library and PyTorch are not in the image.

Run from track_2a/ with a Python that has sentence-transformers (for example a separate virtual environment):

    STATIC_MODEL_DIR=models/static-similarity-mrl-multilingual-v1 <venv>/bin/python scripts/static_equivalence.py \\
        --cases output/devA/cases.jsonl --out <file.json>

The 50 sentences are the first 50 claims of the cases file (all three languages). The reference model is loaded
from the Hugging Face hub at the pinned commit, once with truncate_dim=256 and once with all 1,024 dimensions;
both are compared with ours (embedding_256.npy, embedding_1024.npy). Equal means: every element within 1e-5, and
the order of all pairwise similarities the same. Only numbers are written.
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src import static_embed  # noqa: E402

REPO = "sentence-transformers/static-similarity-mrl-multilingual-v1"
REVISION = "b68f4122911bcffcd6e1f695f2d99cd6788972d8"


def compare(ours, ref):
    import numpy as np
    diff = float(np.abs(ours - ref).max())
    cos = (ours * ref).sum(axis=1)
    pairs_ours, pairs_ref = ours @ ours.T, ref @ ref.T
    iu = np.triu_indices(len(ours), 1)
    same_order = bool((np.argsort(-pairs_ours[iu], kind="stable") == np.argsort(-pairs_ref[iu], kind="stable")).all())
    top8_equal = all(set(np.argsort(-pairs_ours[i])[:8]) == set(np.argsort(-pairs_ref[i])[:8]) for i in range(len(ours)))
    return {"max_abs_difference": diff, "min_cosine_ours_vs_reference": float(cos.min()),
            "pairwise_order_equal": same_order, "top8_neighbours_equal_for_every_sentence": top8_equal,
            "equal": diff <= 1e-5 and same_order}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cases", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--n", type=int, default=50)
    args = ap.parse_args()
    import sentence_transformers

    claims = [json.loads(line)["claim"]["text"] for line in args.cases.read_text(encoding="utf-8").splitlines()
              if line.strip()][:args.n]
    result = {"sentences": len(claims), "sentence_transformers": sentence_transformers.__version__,
              "revision": REVISION}
    for dims, matrix in ((256, "embedding_256.npy"), (1024, "embedding_1024.npy")):
        ref_model = sentence_transformers.SentenceTransformer(REPO, revision=REVISION, device="cpu",
                                                              truncate_dim=dims if dims < 1024 else None)
        ref = ref_model.encode(claims, normalize_embeddings=True, convert_to_numpy=True)
        ours = static_embed.StaticEmbedder(static_embed.MODEL_DIR, matrix).embed(claims)
        result[str(dims)] = compare(ours, ref)
    args.out.write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=1))


if __name__ == "__main__":
    main()
