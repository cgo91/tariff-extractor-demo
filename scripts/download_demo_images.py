"""Download the demo photographs listed in ``data/demo/sources.json``.

The images are not committed: they belong to their authors and carry their own
licences. This script fetches them from Wikimedia Commons using the manifest,
which records file name, title, licence, author and source page for each one.

Usage::

    python scripts/download_demo_images.py            # only what is missing
    python scripts/download_demo_images.py --force    # re-download everything
    python scripts/download_demo_images.py --list     # show the manifest
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

DEMO_DIR = Path(__file__).resolve().parents[1] / "data" / "demo"
MANIFEST = DEMO_DIR / "sources.json"
COMMONS_API = "https://commons.wikimedia.org/w/api.php"

# Commons asks that automated clients identify themselves.
HEADERS = {"User-Agent": "tariff-assistant-demo/0.1 (https://example.invalid; demo)"}

# Wide enough for Claude to read a label, small enough to stay under the
# 10 MB upload limit with room to spare.
THUMBNAIL_WIDTH = 900


def load_manifest() -> list[dict]:
    """Read the image manifest.

    Raises:
        SystemExit: when the manifest is missing, which means the repository
            checkout is incomplete rather than the network being unavailable.
    """
    if not MANIFEST.is_file():
        sys.exit(f"No se encontró el manifiesto {MANIFEST}")
    return json.loads(MANIFEST.read_text(encoding="utf-8"))["images"]


def resolve_url(title: str) -> str | None:
    """Ask Commons for a downloadable URL for the given file title."""
    params = {
        "action": "query",
        "format": "json",
        "titles": title,
        "prop": "imageinfo",
        "iiprop": "url",
        "iiurlwidth": str(THUMBNAIL_WIDTH),
    }
    request = urllib.request.Request(
        f"{COMMONS_API}?{urllib.parse.urlencode(params)}", headers=HEADERS
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        pages = json.load(response)["query"]["pages"]

    info = (next(iter(pages.values())).get("imageinfo") or [{}])[0]
    return info.get("thumburl") or info.get("url")


def download(url: str, target: Path) -> int:
    """Fetch the image and write it; returns the number of bytes written."""
    request = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(request, timeout=90) as response:
        data = response.read()
    target.write_bytes(data)
    return len(data)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--force", action="store_true", help="vuelve a descargar aunque el archivo exista"
    )
    parser.add_argument(
        "--list", action="store_true", help="solo muestra el manifiesto y termina"
    )
    args = parser.parse_args()

    images = load_manifest()
    DEMO_DIR.mkdir(parents=True, exist_ok=True)

    if args.list:
        print(f"{'ARCHIVO':20s} {'LICENCIA':16s} {'SUBPARTIDA ESPERADA':30s} AUTOR")
        for image in images:
            print(
                f"{image['file']:20s} {image['license']:16s} "
                f"{image['expected_subheading']:30s} {image['author']}"
            )
        return 0

    failures = 0
    for image in images:
        target = DEMO_DIR / image["file"]
        if target.is_file() and not args.force:
            print(f"  ya existe   {image['file']}")
            continue

        try:
            url = resolve_url(image["title"])
            if url is None:
                raise ValueError("Commons no devolvió una URL")
            size = download(url, target)
        except (urllib.error.URLError, ValueError, KeyError, OSError) as exc:
            failures += 1
            print(f"  FALLÓ       {image['file']}: {exc}")
            print(f"              descárgala a mano desde {image['page']}")
            continue

        print(f"  descargada  {image['file']} ({size // 1024} KB, {image['license']})")

    print()
    if failures:
        print(f"{failures} imagen(es) no se pudieron descargar; ver los enlaces de arriba.")
        return 1

    print(f"Listo. {len(images)} fotografías en {DEMO_DIR}")
    print("Atribución y licencias en data/demo/sources.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
