# Built for linux/amd64 (the Makefile passes --platform), CPU only. All dependencies are installed at build time; nothing
# is downloaded at run time. Only src/ goes into the image: no data, no .env.

# Session 12, step 1: model S (src/static_embed.py), sentence-transformers/static-similarity-mrl-multilingual-v1,
# Apache-2.0, pinned to a commit. Downloaded at build time only, in a stage of its own: its table (434 MB) is cut to
# the first 256 dimensions (108 MB) with numpy, and only the cut table and the tokenizer go into the image.
FROM python:3.12-slim AS static-model
RUN pip install --no-cache-dir numpy==2.5.3
ARG S_URL=https://huggingface.co/sentence-transformers/static-similarity-mrl-multilingual-v1/resolve/b68f4122911bcffcd6e1f695f2d99cd6788972d8/0_StaticEmbedding
ADD ${S_URL}/model.safetensors ${S_URL}/tokenizer.json /build/
COPY src/static_embed.py /build/
RUN cd /build && python -c "import static_embed; static_embed.convert('model.safetensors', 'embedding_256.npy')"

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Embedding model for task A context selection (src/contexts/embed_e5_small.py): intfloat/multilingual-e5-small,
# MIT licence, ONNX export from the model's own repository, pinned to a commit. Downloaded at build
# time only; at run time nothing is downloaded. ADD gives remote files mode 600, so make them readable
# for the non-root user the container runs as.
ARG E5_URL=https://huggingface.co/intfloat/multilingual-e5-small/resolve/614241f622f53c4eeff9890bdc4f31cfecc418b3/onnx
ADD ${E5_URL}/model.onnx ${E5_URL}/tokenizer.json /app/models/multilingual-e5-small/
RUN chmod -R a+rX /app/models
ENV EMBED_MODEL_DIR=/app/models/multilingual-e5-small
COPY --from=static-model /build/embedding_256.npy /build/tokenizer.json /app/models/static-similarity-mrl-multilingual-v1/
RUN chmod -R a+rX /app/models/static-similarity-mrl-multilingual-v1
ENV STATIC_MODEL_DIR=/app/models/static-similarity-mrl-multilingual-v1

COPY src/ src/
# Session 10: compile src/ now, so no run spends local time compiling it (the root file system is read-only at
# run time, and PYTHONDONTWRITEBYTECODE stops Python from writing the files). unchecked-hash: the files are used
# as they are; a src/ mounted over /app/src (scripts/local_time.py --src) brings no __pycache__ and is compiled.
RUN python -m compileall -q --invalidation-mode unchecked-hash src

# Official contract: <entrypoint> --input /data/cases.jsonl --output /output/predictions.jsonl
ENTRYPOINT ["python", "-m", "src.cli"]
