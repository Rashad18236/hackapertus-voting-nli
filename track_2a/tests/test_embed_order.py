"""E5Embedder.embed batches texts by length (session 8, P6) and must return the vectors in the texts' order.

No model files needed: a fake tokenizer and a fake ONNX session stand in for e5. The fake model gives each
token a vector from its id, and embed() mean-pools over real tokens, so a text's vector must not depend on
which batch it lands in or how much that batch is padded.
"""

import unittest

import numpy as np

from src.contexts import embed_e5_small


class Encoding:
    def __init__(self, ids, mask):
        self.ids, self.attention_mask = ids, mask


class Tokenizer:
    def encode_batch(self, texts):
        tokens = [[(sum(map(ord, w)) % 50) + 1 for w in t.split()] or [1] for t in texts]
        width = max(map(len, tokens))
        return [Encoding(t + [0] * (width - len(t)), [1] * len(t) + [0] * (width - len(t))) for t in tokens]


class Session:
    def run(self, _, inputs):
        ids = inputs["input_ids"]
        return [np.sin(ids[:, :, None] * np.arange(1, 385)[None, None, :] / 7.0)]


class EmbedOrder(unittest.TestCase):
    def setUp(self):
        self.embedder = object.__new__(embed_e5_small.E5Embedder)
        self.embedder.tokenizer, self.embedder.session = Tokenizer(), Session()
        self.embedder.input_names = {"input_ids", "attention_mask"}

    def test_vectors_in_the_order_of_the_texts_across_batches(self):
        rng = np.random.default_rng(0)
        texts = [" ".join(f"w{rng.integers(1000)}" for _ in range(rng.integers(1, 60))) for _ in range(75)]
        together = self.embedder.embed(texts)  # 75 texts: three batches of up to 32, sorted by length
        alone = np.concatenate([self.embedder.embed([t]) for t in texts])
        self.assertEqual(together.shape, (75, 384))
        self.assertLessEqual(float(np.abs(together - alone).max()), 1e-12)

    def test_no_texts_raises_as_before(self):
        with self.assertRaises(ValueError):  # np.concatenate of no batches, as before session 8
            self.embedder.embed([])


if __name__ == "__main__":
    unittest.main()
