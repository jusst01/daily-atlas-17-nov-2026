# THE DAILY ATLAS — 17 November 2026

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
![Python 3.13](https://img.shields.io/badge/python-3.13-blue.svg)

A 1024×1024 front-page image for [make.fun bounty *news-image-20261117*](https://make.fun/c/news-image-20261117):
a single broadsheet page carrying **all 42 stories** reported on Tuesday 17
November 2026.

## What the image shows

A newspaper front page in warm paper tones, set in DejaVu Serif and Sans:

- **Masthead** — the date, then the *THE DAILY ATLAS* name strip on double rules.
- **Featured row** — the three lead stories as large cards, each with a
  full-bleed artwork panel, a caption bar and headline: the Kerch Bridge span
  brought down, tankers mined in the Strait of Hormuz, and the Trump–Xi–Putin
  summit in Shenzhen.
- **Story grid** — twelve further stories as tiles, each with a photo strip or a
  vector banner illustration (jets, measles virions, Geneva talks, Gaza aid,
  Aden, the UK, Temu).
- **"Where it happened"** — a hand-built equirectangular world map with pins
  numbered to the stories, coloured by continent, plus a legend.
- **Also on Tuesday** — the remaining 27 stories as a numbered briefs column.

Every story number 1–42 appears exactly once. The renderer refuses to write the
file if a story is missing or if any text block overflows its box.

## How it is built

Two pieces, with a deliberate split between build time and run time:

- **`draw.py`** (build time) — renders `entry.png` from the story data embedded
  in the file and the seven artwork assets in `assets/ultra-*.png`, using
  Pillow. It self-checks story coverage, text overflow and the 1 MiB size cap,
  then writes `entry.png` next to itself.
- **`main.py`** (run time) — the submitted entrypoint. Standard library only: it
  copies the bundled `entry.png` into the output directory. It resolves the
  source relative to its own file location, writes through a temporary file in
  the destination directory and finishes with an atomic rename, so an
  interrupted run never leaves a partial image.

## Running it

Deploy the finished image:

```sh
python main.py                       # writes /output/entry.png
MAKEFUN_OUTPUT_DIR=./out python main.py
```

The script exits non-zero with a clear message if the bundled `entry.png` is
missing, if the output directory cannot be created, or if the deployed copy's
byte size does not match the source.

Re-render the page from scratch (needs Pillow and the DejaVu fonts):

```sh
python -m venv .venv
.venv/bin/pip install pillow
.venv/bin/python draw.py             # rewrites entry.png
```

## Layout

```
draw.py             build-time renderer
main.py             stdlib-only entrypoint that deploys entry.png
entry.png           the rendered 1024x1024 front page
assets/             seven ultra-*.png artwork files used by draw.py
.makefun/owner.json payout wallet for the bounty
```

## Licence

MIT — see [LICENSE](LICENSE).
