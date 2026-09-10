import json
from pathlib import Path
import tempfile
import unittest

from search_gui import matches, load_records, detail_sections


class SearchTests(unittest.TestCase):
    def test_location_matches_any_single_element(self):
        data = {'locations': ['Warszawa', 'Łódź, ulica Piotrkowska']}
        self.assertTrue(matches(data, 'ŁÓDŹ', ''))
        self.assertFalse(matches(data, 'Warszawa Łódź', ''))

    def test_both_filters_and_literal_pattern(self):
        data = {'locations': ['Łódź'], 'description': 'Historia (rodziny).'}
        self.assertTrue(matches(data, 'łódź', '(RODZINY)'))
        self.assertFalse(matches(data, 'Kraków', 'rodziny'))
        self.assertFalse(matches(data, 'Łódź', 'komedia'))
        self.assertFalse(matches(data, '', '.*'))
        self.assertTrue(matches({}, '', ''))
        self.assertFalse(matches({'description': None}, '', 'tekst'))

    def test_load_only_movie_and_series_records_and_skip_broken_files(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for kind in ('movies', 'series', 'years'):
                path = root / kind / '2000'
                path.mkdir(parents=True)
                (path / '1.json').write_text(json.dumps({'title': kind}))
            (root / 'movies/2000/broken.json').write_text('{')
            records, errors = load_records(root)
            self.assertEqual(len(records), 2)
            self.assertEqual(len(errors), 1)

    def test_details_include_requested_fields_and_roles(self):
        sections = detail_sections({'title': 'Test', 'production_years': '1998', 'directors': [{'name': 'Reżyser'}], 'cast_main': [{'name': 'Aktor', 'character': 'Komisarz'}], 'description': 'Opis'})
        self.assertEqual([value for _, value in sections[:5]], ['Test', '1998', 'Reżyser', 'Aktor — Komisarz', 'Opis'])

    def test_deduplicate_by_id_and_keep_latest_year_not_title(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for kind, year, film_id, description in [
                ('series', '2023', '1265335', 'Starszy opis'),
                ('series', '2025', '1265335', 'Nowszy opis'),
                ('series', '2025', '999', 'Inna produkcja o tym samym tytule'),
                ('movies', '2023', '1265335', 'Kopia w filmach'),
            ]:
                path = root / kind / year
                path.mkdir(parents=True, exist_ok=True)
                (path / f'{film_id}.json').write_text(json.dumps({
                    'film_id': film_id, 'title': 'ZATOKA SZPIEGÓW',
                    'locations': ['Gdynia'], 'description': description,
                }))
            records, errors = load_records(root)
            self.assertEqual(errors, [])
            self.assertEqual(len(records), 2)
            record = next(r for r in records if r[2]['film_id'] == '1265335')
            self.assertEqual(record[0], 'series')
            self.assertEqual(record[2]['description'], 'Nowszy opis')
            self.assertTrue(matches(record[2], 'Gdynia', ''))

    def test_page_contains_every_element_referenced_by_javascript(self):
        import re
        html = (Path(__file__).resolve().parents[1] / 'search_ui.html').read_text()
        ids = set(re.findall(r'id="([^"]+)"', html))
        references = set(re.findall(r"\$\('([^']+)'\)", html))
        self.assertEqual(references - ids, set())
        self.assertIn('id="sort"', html)
        self.assertIn('value="newest"', html)
        self.assertIn('value="oldest"', html)
