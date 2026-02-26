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
from typing import Dict, List, Optional, Tuple
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen

BASE_URL = "https://filmpolski.pl/fp/index.php?filmy_z_roku={year}&typ=2"
BASE_SITE = "https://filmpolski.pl/fp/"
LI_PATTERN = re.compile(r"<li>\s*<span class=\"ikony\".*?</li>", re.DOTALL | re.IGNORECASE)
TITLE_DIV_PATTERN = re.compile(r'<div class="tytul">(.*?)</div>', re.DOTALL | re.IGNORECASE)
RODZAJ_PATTERN = re.compile(r'<div class="rodzajfilmu">(.*?)</div>', re.DOTALL | re.IGNORECASE)
ANCHOR_PATTERN = re.compile(r'<a\s+href="(index\.php/\d+)"[^>]*>(.*?)</a>', re.DOTALL | re.IGNORECASE)
ALT_TITLE_PATTERN = re.compile(r'<span class="tytulnieindeksowany">(.*?)</span>', re.DOTALL | re.IGNORECASE)
TAG_PATTERN = re.compile(r"<[^>]+>")
ARTICLE_PATTERN = re.compile(r'<article\s+id="film"[^>]*>(.*?)</article>', re.DOTALL | re.IGNORECASE)
H1_PATTERN = re.compile(r"<h1[^>]*>(.*?)</h1>", re.DOTALL | re.IGNORECASE)
TECH1_PATTERN = re.compile(
    r'<div class="film_tech1">\s*(.*?)\s*</div>\s*<div class="film_tech2">\s*(.*?)\s*</div>',
    re.DOTALL | re.IGNORECASE,
)
TECH3_PATTERN = re.compile(r'<div class="film_tech3">(.*?)</div>', re.DOTALL | re.IGNORECASE)
DESCRIPTION_PATTERN = re.compile(r'<p class="opis">(.*?)</p>', re.DOTALL | re.IGNORECASE)
GALLERY_PATTERN = re.compile(r'<div class="galeria_mala">(.*?)</div>', re.DOTALL | re.IGNORECASE)
PERSON_BLOCK_PATTERN = re.compile(
    r'<div class="(?P<class_attr>ekipa_(?:osoba|opis)[^"]*)"[^>]*>(?P<content>.*?)</div>',
    re.DOTALL | re.IGNORECASE,
)
FUNKCJA_PATTERN = re.compile(r'<div class="ekipa_funkcja[^"]*">(.*?)</div>', re.DOTALL | re.IGNORECASE)
LI_ITEM_PATTERN = re.compile(r"<li[^>]*>(.*?)</li>", re.DOTALL | re.IGNORECASE)


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
    text = re.sub(r"<br\s*/?>", " ", text, flags=re.IGNORECASE)
    text = unescape(TAG_PATTERN.sub("", text))
    return re.sub(r"\s+", " ", text).strip()


def parse_rodzaj(rodzaj_html: str) -> Dict[str, Optional[str]]:
    raw = clean_text(rodzaj_html)
    parts = [part.strip() for part in raw.split("/")]

    if len(parts) == 1:
        return {"film_type": parts[0] or None, "text_author": None, "creators": None}
    if len(parts) == 2:
        return {"film_type": parts[0] or None, "text_author": None, "creators": parts[1] or None}

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


def split_outside_parentheses(text: str) -> List[str]:
    parts: List[str] = []
    current: List[str] = []
    depth = 0
    for ch in text:
        if ch == "(":
            depth += 1
        elif ch == ")" and depth > 0:
            depth -= 1

        if ch == "," and depth == 0:
            segment = "".join(current).strip()
            if segment:
                parts.append(segment)
            current = []
        else:
            current.append(ch)

    tail = "".join(current).strip()
    if tail:
        parts.append(tail)
    return parts


def normalize_location_entry(entry: str) -> List[str]:
    entry = entry.strip()
    open_idx = entry.find("(")
    close_idx = entry.rfind(")")
    if open_idx == -1 or close_idx <= open_idx:
        return [entry]

    city = entry[:open_idx].strip().rstrip(",")
    inside = entry[open_idx + 1 : close_idx].strip()
    if not city or not inside:
        return [entry]

    inner_parts = [p.strip() for p in split_outside_parentheses(inside) if p.strip()]
    if len(inner_parts) <= 1:
        return [entry]

    return [f"{city} ({part})" for part in inner_parts]


def parse_locations_from_tech3(tech3_html: str) -> List[str]:
    tech3_text = clean_text(tech3_html)
    match = re.search(r"Lokacje:\s*(.+)$", tech3_text, re.IGNORECASE)
    if not match:
        return []

    locations_raw = re.sub(r"\.$", "", match.group(1)).strip()
    result: List[str] = []
    for chunk in split_outside_parentheses(locations_raw):
        result.extend(normalize_location_entry(chunk))
    return [item for item in result if item]


def parse_people_with_roles(li_html: str) -> List[Dict[str, Optional[str]]]:
    people: List[Dict[str, Optional[str]]] = []
    pending_person: Optional[Dict[str, Optional[str]]] = None

    for match in PERSON_BLOCK_PATTERN.finditer(li_html):
        class_attr = match.group("class_attr")
        content = match.group("content")

        if class_attr.startswith("ekipa_osoba"):
            a_match = ANCHOR_PATTERN.search(content)
            if not a_match:
                continue
            href, name_html = a_match.groups()
            pending_person = {
                "name": clean_text(name_html),
                "id": href.rsplit("/", 1)[-1],
                "character": None,
                "main": False,
            }
            people.append(pending_person)
            continue

        if class_attr.startswith("ekipa_opis") and pending_person is not None:
            pending_person["character"] = clean_text(content) or None
            pending_person["main"] = "wyroznienie" in class_attr
            pending_person = None

    return people


def dedupe_people(items: List[Dict[str, Optional[str]]]) -> List[Dict[str, Optional[str]]]:
    unique: Dict[str, Dict[str, Optional[str]]] = {}
    for item in items:
        person_id = str(item.get("id") or "")
        if not person_id:
            continue
        if person_id not in unique:
            unique[person_id] = {"name": item.get("name"), "id": person_id}
    return list(unique.values())


def extract_movie_details_from_html(html: str) -> Dict[str, object]:
    article_match = ARTICLE_PATTERN.search(html)
    if not article_match:
        return {}
    article_html = article_match.group(1)

    title_match = H1_PATTERN.search(article_html)
    title = clean_text(title_match.group(1)) if title_match else None

    years = None
    for label_html, value_html in TECH1_PATTERN.findall(article_html):
        label = clean_text(label_html).rstrip(":").lower()
        if label == "rok produkcji":
            years = clean_text(value_html) or None

    tech3_match = TECH3_PATTERN.search(article_html)
    locations = parse_locations_from_tech3(tech3_match.group(1)) if tech3_match else []

    description_match = DESCRIPTION_PATTERN.search(article_html)
    description = clean_text(description_match.group(1)) if description_match else None

    gallery_link = None
    gallery_match = GALLERY_PATTERN.search(article_html)
    if gallery_match:
        links = ANCHOR_PATTERN.findall(gallery_match.group(1))
        if links:
            href, _ = links[-1]
            gallery_link = urljoin(BASE_SITE, href)

    directors: List[Dict[str, Optional[str]]] = []
    screenwriters: List[Dict[str, Optional[str]]] = []
    cinematographers: List[Dict[str, Optional[str]]] = []
    cast_main: List[Dict[str, Optional[str]]] = []
    cast_other: List[Dict[str, Optional[str]]] = []

    for li_html in LI_ITEM_PATTERN.findall(article_html):
        func_match = FUNKCJA_PATTERN.search(li_html)
        if not func_match:
            continue
        role = clean_text(func_match.group(1)).lower()
        people = parse_people_with_roles(li_html)

        if role == "reżyseria":
            directors.extend(people)
        elif role == "scenariusz":
            screenwriters.extend(people)
        elif role == "zdjęcia":
            cinematographers.extend(people)
        elif role == "obsada aktorska":
            for person in people:
                payload = {"name": person.get("name"), "id": person.get("id"), "character": person.get("character")}
                if person.get("main"):
                    cast_main.append(payload)
                else:
                    cast_other.append(payload)

    directors_out = dedupe_people(directors)
    screenwriters_out = dedupe_people(screenwriters)
    cinematographers_out = dedupe_people(cinematographers)

    cast_main_ids = {str(actor.get("id") or "") for actor in cast_main}
    cast_other_out = [actor for actor in cast_other if str(actor.get("id") or "") not in cast_main_ids]

    return {
        "title": title,
        "production_years": years,
        "locations": locations,
        "description": description,
        "gallery_link": gallery_link,
        "directors": directors_out,
        "screenwriters": screenwriters_out,
        "cinematographers": cinematographers_out,
        "cast_main": cast_main,
        "cast_other": cast_other_out,
    }


def download_html(url: str) -> str:
    req = Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; filmpolski-scraper/1.0; +https://filmpolski.pl)",
        },
    )
    with urlopen(req, timeout=30) as response:
        return response.read().decode("utf-8", errors="replace")


def download_year_html(year: int) -> str:
    return download_html(BASE_URL.format(year=year))


def process_year(year: int, output_dir: Path, pause_s: float) -> List[Dict[str, object]]:
    html_path = output_dir / f"{year}.html"
    json_path = output_dir / f"{year}.json"

    html = download_year_html(year)
    html_path.write_text(html, encoding="utf-8")

    films = extract_films_from_html(html)
    payload = {"year": year, "films": films}
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    if pause_s > 0:
        time.sleep(pause_s)
    return films


def matches_type(film: Dict[str, object], download_types: List[str]) -> bool:
    film_type = str(film.get("film_type") or "").strip().lower()
    normalized = {value.strip().lower() for value in download_types}
    return film_type in normalized


def is_movie_downloaded(year_dir: Path, film_id: str) -> bool:
    return (year_dir / f"{film_id}.html").exists() and (year_dir / f"{film_id}.json").exists()


def process_movie_pages(
    year: int,
    films: List[Dict[str, object]],
    download_types: List[str],
    movies_dir: Path,
    pause_s: float,
) -> Tuple[int, int, int]:
    year_dir = movies_dir / str(year)
    year_dir.mkdir(parents=True, exist_ok=True)

    planned = [film for film in films if matches_type(film, download_types)]
    downloaded = 0
    skipped_existing = 0
    total = len(planned)

    for idx, film in enumerate(planned, start=1):
        film_id = str(film["film_id"])
        link = str(film["link"])
        html_path = year_dir / f"{film_id}.html"
        json_path = year_dir / f"{film_id}.json"

        if is_movie_downloaded(year_dir, film_id):
            skipped_existing += 1
            print(f"[MOVIES] {year}: {idx}/{total} (pobrane: {downloaded}, pominięte: {skipped_existing}) - ID {film_id} już istnieje")
            continue

        html = download_html(link)
        html_path.write_text(html, encoding="utf-8")

        details = extract_movie_details_from_html(html)
        details["film_id"] = film_id
        details["link"] = link
        details["year_from_listing"] = year
        json_path.write_text(json.dumps(details, ensure_ascii=False, indent=2), encoding="utf-8")

        downloaded += 1
        print(f"[MOVIES] {year}: {idx}/{total} (pobrane: {downloaded}, pominięte: {skipped_existing})")
        if pause_s > 0:
            time.sleep(pause_s)

    return downloaded, skipped_existing, total


def main() -> int:
    parser = argparse.ArgumentParser(description="Pobiera strony Filmpolski dla zakresu lat i tworzy JSON z filmami.")
    parser.add_argument("--start-year", type=int, default=1911)
    parser.add_argument("--end-year", type=int, default=2026)
    parser.add_argument("--output-dir", type=Path, default=Path("data/years"))
    parser.add_argument("--pause", type=float, default=0.2, help="Pauza między requestami w sekundach")
    parser.add_argument(
        "--download-movies",
        action="append",
        default=[],
        metavar="TYPE",
        help="Pobiera strony filmów tylko dla podanego film_type (można podać wiele razy).",
    )
    parser.add_argument(
        "--movies-dir",
        type=Path,
        default=Path("movies"),
        help="Katalog docelowy dla stron i JSON-ów filmów: movies/YEAR/ID.(html|json)",
    )
    args = parser.parse_args()

    if args.start_year > args.end_year:
        raise SystemExit("--start-year nie może być większy niż --end-year")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    failures = []

    for year in range(args.start_year, args.end_year + 1):
        try:
            films = process_year(year, args.output_dir, args.pause)
            downloaded = skipped = total = 0
            if args.download_movies:
                downloaded, skipped, total = process_movie_pages(
                    year, films, args.download_movies, args.movies_dir, args.pause
                )
                print(
                    f"[OK] {year} | filmy: pobrane {downloaded}/{total}, pominięte {skipped}"
                )
            else:
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
