"""Download the booklets used by the unseen-booklets check (vote dates in neither dev nor test).

Run from track_2a/:  python3 scripts/fetch_unseen_booklets.py

Writes output/booklets_unseen/<date>_<lang>.pdf (git-ignored); files already there are skipped.

Session 11, parser coverage: `--since 2016 --out <folder outside the repository>` reads the archive page and
downloads every booklet from that year on in de, fr and it, plus 2026-09-27 (not yet in the archive). The
sealed test dates (SEALED below) are dropped from the list before any request is made, so they are never
downloaded.
URLs from the Federal Chancellery's archive (https://www.bk.admin.ch/de/sammlung-der-abstimmungsbuechlein-seit-1978)
and, for 2026-09-27 (after the dataset), from https://www.admin.ch/de/volksabstimmung-vom-27-september-2026.
Checked 2026-10-09. Every 2020-2026 date in the archive is already in the dataset.
"""

import argparse
import re
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "output" / "booklets_unseen"

BK = "https://www.bk.admin.ch/dam/{lang}/sd-web/{key}/{date}_{name}.pdf"
NAMES = {"de": "erlaeuterungen_des_bundesrates", "fr": "explications_du_conseil_federal",
         "it": "spiegazioni_del_consigliofederale"}
ARCHIVE = {"2019-05-19": "JidqjDWbXbrM", "2019-02-10": "feT3z55YdiNa", "2018-11-25": "6GNsLC1DGu87",
           "2018-09-23": "vGKL0XXiP381"}
ADMIN_2026_09_27 = {
    "de": "https://www.admin.ch/dam/de/sd-web/3E6DtQlSES3i/DE-%20Volksabstimmung%20vom%2027.%20September%202026%20-"
          "%20Erl%C3%A4uterungen%20des%20Bundesrates.pdf",
    "fr": "https://www.admin.ch/dam/fr/sd-web/3E6DtQlSES3i/Votation%20populaire%20du%2027%20septembre%202026%20-"
          "%20Explications%20du%20Conseil%20f%C3%A9d%C3%A9ral.pdf",
    "it": "https://www.admin.ch/dam/it/sd-web/3E6DtQlSES3i/Votazione%20popolare%20del%2027%20settembre%202026%20-"
          "%20Spiegazioni%20del%20Consiglio%20federale.pdf",
}


SEALED = {"2020-02-09", "2022-02-13", "2022-05-15"}  # session 11: never run, parsed, downloaded or opened
ARCHIVE_PAGE = "https://www.bk.admin.ch/de/sammlung-der-abstimmungsbuechlein-seit-1978"
_DE_LINK = re.compile(r'href="(https://www\.bk\.admin\.ch/dam/de/sd-web/[^"/]+/(\d{4}-\d{2}-\d{2})_erlaeuterungen_des_bundesrates\.pdf)"')


def archive_urls(since):
    """(file name, url) for every archive date from `since` on, sealed dates left out, in de, fr and it."""
    page = requests.get(ARCHIVE_PAGE, timeout=120)
    page.raise_for_status()
    dates = {}
    for url, date in _DE_LINK.findall(page.text):
        if int(date[:4]) >= since and date not in SEALED:
            dates[date] = url
    for date, url in sorted(dates.items()):
        for lang, name in NAMES.items():
            yield f"{date.replace('-', '_')}_{lang}.pdf", url.replace("/dam/de/", f"/dam/{lang}/").replace(NAMES["de"], name)
    for lang, url in ADMIN_2026_09_27.items():
        yield f"2026_09_27_{lang}.pdf", url


def urls():
    for date, key in ARCHIVE.items():
        for lang, name in NAMES.items():
            yield f"{date.replace('-', '_')}_{lang}.pdf", BK.format(lang=lang, key=key, date=date, name=name)
    for lang, url in ADMIN_2026_09_27.items():
        yield f"2026_09_27_{lang}.pdf", url


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--since", type=int, help="every archive booklet from this year on (session 11)")
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    out = args.out
    out.mkdir(parents=True, exist_ok=True)
    for name, url in (archive_urls(args.since) if args.since else urls()):
        assert name[:10].replace("_", "-") not in SEALED
        target = out / name
        if target.exists():
            continue
        response = requests.get(url, timeout=120)
        response.raise_for_status()
        if not response.content.startswith(b"%PDF"):
            raise SystemExit(f"{name}: not a PDF ({url})")
        target.write_bytes(response.content)
        print(f"{name}: {len(response.content) // 1024} KB")
    print(f"{len(list(out.glob('*.pdf')))} booklets in {out}")


if __name__ == "__main__":
    main()
