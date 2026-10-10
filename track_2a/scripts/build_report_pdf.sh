#!/bin/bash
# Build technical_report.pdf from technical_report.md: pandoc (Markdown -> HTML) and headless Chromium
# (HTML -> PDF, A4, 10 pt; style in docs/report/report.css). Run from track_2a/. Prints the page count.
# CHROME: path of a Chromium binary (default: the one Playwright installs under /opt/pw-browsers).
set -euo pipefail
CHROME=${CHROME:-$(ls -d /opt/pw-browsers/chromium-*/chrome-linux/chrome 2>/dev/null | head -1)}
OUT=$(mktemp -d)
pandoc technical_report.md --standalone --metadata pagetitle="Technical report" --css docs/report/report.css \
  --embed-resources -o "$OUT/report.html"
"$CHROME" --headless=new --no-sandbox --disable-gpu --no-pdf-header-footer \
  --print-to-pdf=technical_report.pdf "$OUT/report.html" 2>/dev/null
rm -rf "$OUT"
python3 -c "import re; d=open('technical_report.pdf','rb').read(); print('pages:', len(re.findall(rb'/Type\s*/Page[^s]', d)))"
