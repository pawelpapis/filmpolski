#!/usr/bin/env python3
"""Pobieranie i parsowanie filmów z roczników Filmpolski."""

from __future__ import annotations

import argparse
import json
import re
import time
from dataclasses import dataclass, field
from html import unescape
from pathlib import Path
from typing import Dict, List, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen

BASE_URL = "https://filmpolski.pl/fp/index.php?filmy_z_roku={year}&typ=2"
BASE_SITE = "https://filmpolski.pl/fp/"
LI_PATTERN = re.compile(r"<li>\s*<span class=\"ikony\".*?</li>", re.DOTALL | re.IGNORECASE)
TITLE_DIV_PATTERN = re.compile(r'<div class="tytul">(.*?)</div>', re.DOTALL | re.IGNORECASE)
RODZAJ_PATTERN = re.compile(r'<div class="rodzajfilmu">(.*?)</div>', re.DOTALL | re.IGNORECASE)
ANCHOR_PATTERN = re.compile(r'<a\s+href="(index\.php/\d+)"[^>]*>(.*?)</a>', re.DOTALL | re.IGNORECASE)
ALT_TITLE_PATTERN = re.compile(
    r'<span class="tytulnieindeksowany">(.*?)</span>', re.DOTALL | re.IGNORECASE
)
TAG_PATTERN = re.compile(r"<[^>]+>")


@dataclass
class FilmEntry:
    film_id: str
    link: str
    title: str
    alternate_titles: List[str] = field(default_factory=list)
    film_type: Optional[str] = None
    text_author: Optional[str] = None
    creators: Optional[str] = None

    def to_dict(self) -> Dict[str, object]:
        return {
            "film_id": self.film_id,
            "link": self.link,
            "title": self.title,
            "alternate_titles": self.alternate_titles,
            "film_type": self.film_type,
            "text_author": self.text_author,
            "creators": self.creators,
        }


def clean_text(text: str) -> str:
    text = unescape(TAG_PATTERN.sub("", text))
    text = re.sub(r"\s+", " ", text).strip()
    return text


def parse_rodzaj(rodzaj_html: str) -> Dict[str, Optional[str]]:
    raw = clean_text(rodzaj_html)
    parts = [part.strip() for part in raw.split("/")]

    if len(parts) == 1:
        return {"film_type": parts[0] or None, "text_author": None, "creators": None}
    if len(parts) == 2:
        return {
            "film_type": parts[0] or None,
            "text_author": None,
            "creators": parts[1] or None,
        }

    # Dla >= 3 części: łączymy wszystko po drugim ukośniku do twórców.
    return {
        "film_type": parts[0] or None,
        "text_author": parts[1] or None,
        "creators": "/".join(parts[2:]).strip() or None,
    }


def extract_films_from_html(html: str) -> List[Dict[str, object]]:
    films: Dict[str, FilmEntry] = {}

    for li_html in LI_PATTERN.findall(html):
        title_match = TITLE_DIV_PATTERN.search(li_html)
        rodzaj_match = RODZAJ_PATTERN.search(li_html)

        if not title_match:
            continue

        title_html = title_match.group(1)
        rodzaj_html = rodzaj_match.group(1) if rodzaj_match else ""

        anchors = ANCHOR_PATTERN.findall(title_html)
        if not anchors:
            continue

        href, linked_title_html = anchors[0]
        film_id = href.rsplit("/", 1)[-1]
        linked_title = clean_text(linked_title_html)
        alt_titles = [clean_text(t) for t in ALT_TITLE_PATTERN.findall(title_html)]
        alt_titles = [t for t in alt_titles if t and t != linked_title]

        parsed_rodzaj = parse_rodzaj(rodzaj_html)

        if film_id not in films:
            films[film_id] = FilmEntry(
                film_id=film_id,
                link=urljoin(BASE_SITE, href),
                title=linked_title,
                alternate_titles=alt_titles,
                film_type=parsed_rodzaj["film_type"],
                text_author=parsed_rodzaj["text_author"],
                creators=parsed_rodzaj["creators"],
            )
            continue

        existing = films[film_id]
        if not existing.title and linked_title:
            existing.title = linked_title

        for alt in alt_titles:
            if alt not in existing.alternate_titles and alt != existing.title:
                existing.alternate_titles.append(alt)

        for key in ("film_type", "text_author", "creators"):
            if getattr(existing, key) in (None, "") and parsed_rodzaj[key] not in (None, ""):
                setattr(existing, key, parsed_rodzaj[key])

    return [film.to_dict() for film in sorted(films.values(), key=lambda x: int(x.film_id))]


def download_year_html(year: int) -> str:
    url = BASE_URL.format(year=year)
    req = Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; filmpolski-scraper/1.0; +https://filmpolski.pl)",
        },
    )
    with urlopen(req, timeout=30) as response:
        return response.read().decode("utf-8", errors="replace")


def process_year(year: int, output_dir: Path, pause_s: float) -> None:
    html_path = output_dir / f"{year}.html"
    json_path = output_dir / f"{year}.json"

    html = download_year_html(year)
    html_path.write_text(html, encoding="utf-8")

    films = extract_films_from_html(html)
    payload = {"year": year, "films": films}
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    if pause_s > 0:
        time.sleep(pause_s)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Pobiera strony Filmpolski dla zakresu lat i tworzy JSON z filmami."
    )
    parser.add_argument("--start-year", type=int, default=1911)
    parser.add_argument("--end-year", type=int, default=2026)
    parser.add_argument("--output-dir", type=Path, default=Path("data/years"))
    parser.add_argument("--pause", type=float, default=0.2, help="Pauza między requestami w sekundach")
    args = parser.parse_args()

    if args.start_year > args.end_year:
        raise SystemExit("--start-year nie może być większy niż --end-year")

    args.output_dir.mkdir(parents=True, exist_ok=True)

    failures = []
    for year in range(args.start_year, args.end_year + 1):
        try:
            process_year(year, args.output_dir, args.pause)
            print(f"[OK] {year}")
        except (HTTPError, URLError, TimeoutError) as exc:
            failures.append((year, str(exc)))
            print(f"[ERR] {year}: {exc}")

    if failures:
        print("\nNie udało się pobrać części lat:")
        for year, message in failures:
            print(f" - {year}: {message}")
        return 1

    print("\nZakończono sukcesem.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
