#!/usr/bin/env python3
"""Connections — lokalny graf współpracy aktorów i reżyserów."""
import argparse
from collections import defaultdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
import webbrowser

from search_gui import load_records


class Connections:
    def __init__(self, records):
        self.people = {}
        self.projects = []
        self.credits = defaultdict(set)
        for kind, path, data in records:
            roles = {}
            for role, fields in [('actor', ('cast_main', 'cast_other')), ('director', ('directors',))]:
                ids = set()
                for field in fields:
                    for person in data.get(field) or []:
                        if not isinstance(person, dict) or not person.get('name'):
                            continue
                        name = str(person['name']).strip()
                        identity = str(person.get('id') or '').strip()
                        key = 'id:' + identity if identity else 'name:' + name.casefold()
                        self.people.setdefault(key, name)
                        ids.add(key)
                roles[role] = ids
                for key in ids:
                    self.credits[key, role].add(len(self.projects))
            self.projects.append(dict(title=data.get('title') or 'Bez tytułu',
                                      years=data.get('production_years') or '—', kind=kind, roles=roles))

    def search(self, query='', role='actor'):
        query = query.strip().casefold()
        found = [dict(id=key, name=name, projects=len(self.credits[key, role]))
                 for key, name in self.people.items()
                 if query in name.casefold() and self.credits.get((key, role))]
        found.sort(key=lambda p: (-p['projects'], p['name'].casefold(), p['id']))
        return found[:60]

    def graph(self, identity, role='actor', kind='', limit=20):
        if (identity, role) not in self.credits or not self.credits[identity, role]:
            raise KeyError(identity)
        partners = defaultdict(set)
        projects = [i for i in self.credits[identity, role] if not kind or self.projects[i]['kind'] == kind]
        for i in projects:
            for other_role in (('actor', 'director') if role == 'actor' else ('actor',)):
                for key in self.projects[i]['roles'][other_role]:
                    if key != identity:
                        partners[key, other_role].add(i)
        nodes = []
        for (key, other_role), shared in partners.items():
            titles = [{k: self.projects[i][k] for k in ('title', 'years', 'kind')} for i in shared]
            titles.sort(key=lambda p: (str(p['years']), p['title']))
            nodes.append(dict(id=key, name=self.people[key], role=other_role, count=len(shared), projects=titles))
        nodes.sort(key=lambda p: (-p['count'], p['name'].casefold(), p['role'], p['id']))
        # Separate quotas keep directors visible even for actors with a large cast network.
        visible = [n for r in ('actor', 'director') for n in [p for p in nodes if p['role'] == r][:limit]]
        return dict(person=dict(id=identity, name=self.people[identity], role=role),
                    projects=len(projects), total=len(nodes), nodes=visible)


def make_handler(index, errors):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            url = urlsplit(self.path)
            params = parse_qs(url.query)
            get = lambda key, default='': params.get(key, [default])[0]
            if url.path == '/':
                body = Path(__file__).with_name('connections_ui.html').read_bytes()
                content_type = 'text/html; charset=utf-8'
            elif url.path in ('/api/people', '/api/connections'):
                role, kind = get('role', 'actor'), get('kind')
                try:
                    if role not in ('actor', 'director') or kind not in ('', 'movies', 'series'):
                        raise ValueError
                    if url.path == '/api/people':
                        result = dict(people=index.search(get('q'), role), errors=len(errors), total=len(index.projects))
                    else:
                        limit = int(get('limit', '20'))
                        if not 1 <= limit <= 50:
                            raise ValueError
                        result = index.graph(get('id'), role, kind, limit)
                except ValueError:
                    self.send_error(400)
                    return
                except KeyError:
                    self.send_error(404)
                    return
                body = json.dumps(result, ensure_ascii=False).encode()
                content_type = 'application/json; charset=utf-8'
            else:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(body)))
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass
    return Handler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir', type=Path, default=Path(__file__).resolve().parent / 'data')
    parser.add_argument('--no-browser', action='store_true')
    args = parser.parse_args()
    records, errors = load_records(args.data_dir)
    index = Connections(records)
    for error in errors:
        print(error)
    with ThreadingHTTPServer(('127.0.0.1', 0), make_handler(index, errors)) as server:
        url = f'http://127.0.0.1:{server.server_port}'
        print(f'Connections: {url}\nWczytano {len(records)} produkcji i {len(index.people)} osób. Ctrl+C kończy pracę.', flush=True)
        if not args.no_browser:
            webbrowser.open(url)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == '__main__':
    main()
