# Built for linux/amd64 (the Makefile passes --platform), CPU only. All dependencies are installed at build time; nothing
# is downloaded at run time. Only src/ goes into the image: no data, no .env.
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

COPY src/ src/
# Session 10: compile src/ now, so no run spends local time compiling it (the root file system is read-only at
# run time, and PYTHONDONTWRITEBYTECODE stops Python from writing the files). unchecked-hash: the files are used
# as they are; a src/ mounted over /app/src (scripts/local_time.py --src) brings no __pycache__ and is compiled.
RUN python -m compileall -q --invalidation-mode unchecked-hash src

# Official contract: <entrypoint> --input /data/cases.jsonl --output /output/predictions.jsonl
ENTRYPOINT ["python", "-m", "src.cli"]
