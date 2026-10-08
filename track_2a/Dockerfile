# Built for linux/amd64 (the Makefile passes --platform), CPU only. All dependencies are installed at build time; nothing
# is downloaded at run time. Only src/ goes into the image: no data, no .env.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ src/

# Official contract: <entrypoint> --input /data/cases.jsonl --output /output/predictions.jsonl
ENTRYPOINT ["python", "-m", "src.cli"]
