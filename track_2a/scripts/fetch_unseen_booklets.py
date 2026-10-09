"""Download the booklets used by the unseen-booklets check (vote dates in neither dev nor test).

Run from track_2a/:  python3 scripts/fetch_unseen_booklets.py

Writes output/booklets_unseen/<date>_<lang>.pdf (git-ignored); files already there are skipped.
URLs from the Federal Chancellery's archive (https://www.bk.admin.ch/de/sammlung-der-abstimmungsbuechlein-seit-1978)
and, for 2026-09-27 (after the dataset), from https://www.admin.ch/de/volksabstimmung-vom-27-september-2026.
Checked 2026-10-09. Every 2020-2026 date in the archive is already in the dataset.
"""

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


def urls():
    for date, key in ARCHIVE.items():
        for lang, name in NAMES.items():
            yield f"{date.replace('-', '_')}_{lang}.pdf", BK.format(lang=lang, key=key, date=date, name=name)
    for lang, url in ADMIN_2026_09_27.items():
        yield f"2026_09_27_{lang}.pdf", url


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for name, url in urls():
        target = OUT / name
        if target.exists():
            continue
        response = requests.get(url, timeout=120)
        response.raise_for_status()
        if not response.content.startswith(b"%PDF"):
            raise SystemExit(f"{name}: not a PDF ({url})")
        target.write_bytes(response.content)
        print(f"{name}: {len(response.content) // 1024} KB")
    print(f"{len(list(OUT.glob('*.pdf')))} booklets in {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
