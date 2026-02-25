import unittest

from scrape_filmpolski_years import extract_films_from_html


SAMPLE_HTML = '''
<ul>
<li><span class="ikony"></span><div class="tytul"><a href="index.php/428802">A 1</a></div><div class="rodzajfilmu">Film animowany / Władysław Nehrebecki</div></li>
<li><span class="ikony"></span><div class="tytul"><span class="tytulnieindeksowany">BIAŁY REDYK</span> patrz <a href="index.php/427356">WIELKI REDYK</a></div><div class="rodzajfilmu">Film dokumentalny / Stanisław Możdżeński  Jarosław Brzozowski</div></li>
<li><span class="ikony"></span><div class="tytul"><a href="index.php/427356">WIELKI REDYK</a></div><div class="rodzajfilmu">Film dokumentalny / Stanisław Możdżeński  Jarosław Brzozowski</div></li>
<li><span class="ikony"></span><div class="tytul"><a href="index.php/999999">X</a></div><div class="rodzajfilmu">Film fabularny / Jan Kowalski / Adam Nowak</div></li>
</ul>
'''


class ParserTests(unittest.TestCase):
    def test_extract_and_deduplicate_films(self):
        films = extract_films_from_html(SAMPLE_HTML)

        self.assertEqual(3, len(films))
        by_id = {film["film_id"]: film for film in films}

        self.assertIn("427356", by_id)
        self.assertEqual("WIELKI REDYK", by_id["427356"]["title"])
        self.assertEqual(["BIAŁY REDYK"], by_id["427356"]["alternate_titles"])

        self.assertEqual("Film fabularny", by_id["999999"]["film_type"])
        self.assertEqual("Jan Kowalski", by_id["999999"]["text_author"])
        self.assertEqual("Adam Nowak", by_id["999999"]["creators"])


if __name__ == "__main__":
    unittest.main()
