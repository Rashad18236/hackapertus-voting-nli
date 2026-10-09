#!/bin/bash
# Speed and peak memory of the real CLI inside the image, without a model (session 8).
#
# Run from track_2a/ (Docker running; image built with `make build`; dev booklets in output/booklets_dev):
#
#     scripts/container_speed.sh OUT_DIR [extra docker run options, e.g. -e E5_BATCH_SIZE=16]
#
# The 300 dev task A cases (data/dev/cases.jsonl) run with the default settings, in one process, inside the
# image with 2 CPUs and 4 GB (no swap), a read-only root, /tmp as tmpfs and the data read-only, on an internal
# Docker network without internet. The fake model (scripts/stub_llm.py, in a second container of the same
# image) answers in milliseconds, so the times are the local steps only. The working tree's src/ is mounted
# over the image's /app/src, so the measurement uses the code as it is now; the Dockerfile and everything
# else come from the image. The booklet cache starts empty (tmpfs).
#
# Writes OUT_DIR/predictions.jsonl, OUT_DIR/cli.log and OUT_DIR/result.txt: WALL (seconds from the CLI's
# start to its end), PEAK_BYTES (the container's cgroup v1 memory.max_usage_in_bytes at the end).
set -euo pipefail
OUT=$(mkdir -p "$1" && cd "$1" && pwd); shift
T=$(pwd)
IMAGE=${IMAGE:-hackapertus-voting-nli}
NET=speed-net-$$
grep -- '-A"' data/dev/cases.jsonl > "$OUT/cases.jsonl"
docker network create --internal "$NET" > /dev/null
trap 'docker rm -f stub-$$ > /dev/null 2>&1 || true; docker network rm "$NET" > /dev/null 2>&1 || true' EXIT
docker run -d --rm --name stub-$$ --network "$NET" --network-alias stub --read-only \
    -v "$T/scripts:/app/scripts:ro" --entrypoint python "$IMAGE" scripts/stub_llm.py --host 0.0.0.0 --port 8099 > /dev/null
sleep 2
docker run --rm --network "$NET" --cpus 2 --memory 4g --memory-swap 4g --read-only --tmpfs /tmp \
    -v "$T/src:/app/src:ro" -v "$T/output/booklets_dev:/data/booklets:ro" -v "$OUT/cases.jsonl:/data/cases.jsonl:ro" \
    -v "$OUT:/output" -e BASE_URL=http://stub:8099/v1 -e API_KEY=stub "$@" --entrypoint python "$IMAGE" -c '
import subprocess, sys, time
t = time.time()
with open("/output/cli.log", "w") as log:
    code = subprocess.run([sys.executable, "-m", "src.cli", "--input", "/data/cases.jsonl",
                           "--output", "/output/predictions.jsonl"], stderr=log).returncode
wall = time.time() - t
peak = open("/sys/fs/cgroup/memory/memory.max_usage_in_bytes").read().strip()
print(f"EXIT {code}\nWALL {wall:.1f}\nPEAK_BYTES {peak}")
' | tee "$OUT/result.txt"
