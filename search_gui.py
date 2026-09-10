#!/usr/bin/env python3
"""Lokalna wyszukiwarka filmów i seriali (lokalny interfejs przeglądarkowy)."""
import argparse
import json
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit, parse_qs
import webbrowser


def load_records(data_dir):
    records, errors = {}, []
    for kind in ('movies', 'series'):
        for path in sorted((data_dir / kind).glob('*/*.json')):
            try:
                data = json.loads(path.read_text(encoding='utf-8'))
                if not isinstance(data, dict):
                    raise ValueError('Oczekiwano obiektu JSON')
                # Ten sam identyfikator bywa wymieniony w kilku rocznikach.
                # Wybierz kopię z najnowszego rocznika, nie łącz różnych tytułów.
                identity = str(data.get('film_id') or '').strip()
                key = ('id', identity) if identity else (kind, path.stem)
                previous = records.get(key)
                if previous is None or path.parent.name >= previous[1].parent.name:
                    records[key] = (kind, path, data)
            except (OSError, ValueError) as exc:
                errors.append(f'{path}: {exc}')
    return list(records.values()), errors


def matches(data, location, description):
    """Oba podane fragmenty muszą pasować; lokacja do jednego elementu."""
    location, description = location.strip().casefold(), description.strip().casefold()
    locations = data.get('locations') or []
    if isinstance(locations, str):
        locations = [locations]
    return (
        (not location or any(location in str(item).casefold() for item in locations))
        and description in str(data.get('description') or '').casefold()
    )


def people_text(people):
    lines = []
    for person in people or []:
        if isinstance(person, dict):
            name = str(person.get('name') or '—')
            role = person.get('character')
            lines.append(f'{name} — {role}' if role else name)
        else:
            lines.append(str(person))
    return '\n'.join(lines) or '—'


def detail_sections(data):
    return [
        ('Tytuł (title)', data.get('title') or '—'),
        ('Lata produkcji (production_years)', data.get('production_years') or '—'),
        ('Reżyseria (directors)', people_text(data.get('directors'))),
        ('Obsada główna (cast_main)', people_text(data.get('cast_main'))),
        ('Opis (description)', data.get('description') or '—'),
        ('Lokacje (locations)', '\n'.join(data.get('locations') or []) or '—'),
    ]


def make_handler(records, errors):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            url = urlsplit(self.path)
            if url.path == '/':
                body = Path(__file__).with_name('search_ui.html').read_bytes()
                content_type = 'text/html; charset=utf-8'
            elif url.path == '/api/search':
                query = parse_qs(url.query)
                location = query.get('location', [''])[0]
                description = query.get('description', [''])[0]
                kind = query.get('kind', [''])[0]
                results = [dict(index=i, title=data.get('title') or 'Bez tytułu',
                                years=data.get('production_years') or '—', kind=source)
                           for i, (source, _, data) in enumerate(records)
                           if (not kind or source == kind) and matches(data, location, description)]
                body = json.dumps(dict(results=results, total=len(records), errors=len(errors)), ensure_ascii=False).encode()
                content_type = 'application/json; charset=utf-8'
            elif url.path.startswith('/api/detail/'):
                try:
                    index = int(url.path.rsplit('/', 1)[1])
                    if index < 0:
                        raise IndexError
                    source, _, data = records[index]
                except (ValueError, IndexError):
                    self.send_error(404)
                    return
                body = json.dumps(dict(kind=source, sections=detail_sections(data)), ensure_ascii=False).encode()
                content_type = 'application/json; charset=utf-8'
            else:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format, *args):
            pass
    return Handler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir', type=Path, default=Path(__file__).resolve().parent / 'data')
    parser.add_argument('--no-browser', action='store_true', help='Nie otwieraj automatycznie przeglądarki')
    args = parser.parse_args()
    records, errors = load_records(args.data_dir)
    records.sort(key=lambda item: (str(item[2].get('title') or '').casefold(), str(item[2].get('production_years') or '')))
    for error in errors:
        print(error)
    with ThreadingHTTPServer(('127.0.0.1', 0), make_handler(records, errors)) as server:
        url = f'http://127.0.0.1:{server.server_port}'
        print(f'FilmPolski: {url}\nWczytano {len(records)} rekordów. Zatrzymaj przez Ctrl+C.', flush=True)
        if not args.no_browser:
            webbrowser.open(url)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == '__main__':
    main()
