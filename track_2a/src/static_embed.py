"""Model S (session 12): sentence-transformers/static-similarity-mrl-multilingual-v1, a static embedding model.

Apache-2.0; repository commit b68f4122911bcffcd6e1f695f2d99cd6788972d8. The model is a table with one vector per
token of a multilingual BERT vocabulary (105,879 tokens x 1,024 dimensions): a text's vector is the mean of its
tokens' vectors, normalised to length 1. There is no neural network to run, so it needs no onnxruntime and almost
no time, and only the rows of the tokens a text uses are read from the file.

Matryoshka training puts the most information into the first dimensions, so the table is cut to its first DIMS
(256) dimensions when the image is built (convert(), from the repository's model.safetensors; the cut table is
105,879 x 256 float32 = 108 MB instead of 434 MB). Cutting before averaging gives the same vector as averaging
then cutting, since the mean is linear.

How a text is embedded, as the reference library does it (sentence-transformers' StaticEmbedding: tokenizer
without special tokens, mean of the token vectors; then normalisation for cosine similarity):

1. tokenizers reads the repository's tokenizer.json (BERT normaliser: lower case; WordPiece) and encodes the text
   with add_special_tokens=False;
2. the rows of those token ids are averaged (an empty text gives the zero vector);
3. the mean is divided by its length.

scripts/static_equivalence.py checks on 50 sentences that these vectors equal the reference library's (development
machine only; the library is not in the image). No prefixes ("query: ", "passage: "): the model has none.

Only Apertus decides labels; this model only chooses what Apertus reads.
"""

import json
import os
import struct
from pathlib import Path

MODEL_DIR = Path(os.environ.get("STATIC_MODEL_DIR", "/app/models/static-similarity-mrl-multilingual-v1"))
DIMS = 256
MATRIX_FILE = f"embedding_{DIMS}.npy"


def convert(safetensors_file, out_file, dims=DIMS):
    """Write the first `dims` columns of the safetensors file's single float32 matrix as a .npy file. Reads the
    safetensors format directly (8-byte header length, JSON header, raw little-endian data), so the conversion
    needs numpy only."""
    import numpy as np

    with open(safetensors_file, "rb") as f:
        header_len = struct.unpack("<Q", f.read(8))[0]
        header = json.loads(f.read(header_len))
    (name, info), = [(k, v) for k, v in header.items() if k != "__metadata__"]
    if info["dtype"] != "F32" or len(info["shape"]) != 2:
        raise ValueError(f"unexpected tensor {name}: {info['dtype']} {info['shape']}")
    rows, cols = info["shape"]
    start, end = info["data_offsets"]
    matrix = np.memmap(safetensors_file, dtype="<f4", mode="r", offset=8 + header_len + start, shape=(rows, cols))
    if end - start != rows * cols * 4:
        raise ValueError("tensor size does not match its shape")
    np.save(out_file, np.ascontiguousarray(matrix[:, :dims] if dims else matrix, dtype=np.float32))


class StaticEmbedder:
    """embed(texts) -> (len(texts), dims) array of unit-length vectors (zero rows for texts without tokens)."""

    def __init__(self, model_dir=MODEL_DIR, matrix_file=MATRIX_FILE):
        import numpy as np
        from tokenizers import Tokenizer

        self.tokenizer = Tokenizer.from_file(str(Path(model_dir) / "tokenizer.json"))
        self.tokenizer.no_truncation()
        self.tokenizer.no_padding()
        # mmap: only the rows of tokens that occur are read from disk; the whole table never has to fit in memory.
        self.matrix = np.load(Path(model_dir) / matrix_file, mmap_mode="r")

    def embed(self, texts):
        import numpy as np

        out = np.zeros((len(texts), self.matrix.shape[1]), dtype=np.float32)
        for i, encoding in enumerate(self.tokenizer.encode_batch(list(texts), add_special_tokens=False)):
            if encoding.ids:
                mean = np.asarray(self.matrix[encoding.ids], dtype=np.float32).mean(axis=0)
                norm = np.linalg.norm(mean)
                out[i] = mean / norm if norm > 0 else mean
        return out


_embedders = {}


def get(model_dir=None, matrix_file=MATRIX_FILE):
    """The run's StaticEmbedder, loaded on first use (once, also when several threads ask at the same time)."""
    from src import memo

    model_dir = Path(model_dir or MODEL_DIR)
    return memo.once(_embedders, (model_dir, matrix_file), lambda: StaticEmbedder(model_dir, matrix_file))
