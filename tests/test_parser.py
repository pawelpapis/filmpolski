import unittest

from scrape_filmpolski_years import (
    build_gallery_page_url,
    extract_films_from_html,
    extract_gallery_image_urls,
    extract_movie_details_from_html,
    parse_locations_from_tech3,
)


SAMPLE_YEAR_HTML = '''
<ul>
<li><span class="ikony"></span><div class="tytul"><a href="index.php/428802">A 1</a></div><div class="rodzajfilmu">Film animowany / Władysław Nehrebecki</div></li>
<li><span class="ikony"></span><div class="tytul"><span class="tytulnieindeksowany">BIAŁY REDYK</span> patrz <a href="index.php/427356">WIELKI REDYK</a></div><div class="rodzajfilmu">Film dokumentalny / Stanisław Możdżeński  Jarosław Brzozowski</div></li>
<li><span class="ikony"></span><div class="tytul"><a href="index.php/427356">WIELKI REDYK</a></div><div class="rodzajfilmu">Film dokumentalny / Stanisław Możdżeński  Jarosław Brzozowski</div></li>
<li><span class="ikony"></span><div class="tytul"><a href="index.php/999999">X</a></div><div class="rodzajfilmu">Film fabularny / Jan Kowalski / Adam Nowak</div></li>
</ul>
'''

SAMPLE_MOVIE_HTML = '''
<article id="film">
<h1>POJEDYNEK</h1><div class="koniecnaglowka"></div>
<ul class="tech">
<li><div class="film_tech1">Rok produkcji:</div><div class="film_tech2">2021-2025</div></li>
<li><div class="film_tech3">Lokacje: Zawiercie (basen przy ul. Glinianej, Miejski Ośrodek Kultury przy ul. Piastowskiej 1, ulice: Huldczyńskiego i Senatorska, blok przy ul. Wschodniej 2), Łódź.</div></li>
</ul>
<p class="opis">Opis filmu.<br />Drugi akapit.</p>
<div class="galeria_mala"><a href="index.php/1556274" title="Galeria zdjęć (45)"><img></a></div>
<ul class="ekipa" id="ekipa_pelna1271156">
<li><div class="ekipa_funkcja wyroznienie">Reżyseria</div><div class="ekipa_osoba wyroznienie"><a href="index.php/1193213">Maciej Kawalski</a></div><div class="ekipa_opis wyroznienie">&nbsp;</div><div class="ekipa_osoba wyroznienie"><a href="index.php/1193213">Maciej Kawalski</a></div><div class="ekipa_opis wyroznienie">&nbsp;</div></li>
<li><div class="ekipa_funkcja wyroznienie">Scenariusz</div><div class="ekipa_osoba wyroznienie"><a href="index.php/11144590">Łukasz Światowiec</a></div><div class="ekipa_opis wyroznienie">&nbsp;</div></li>
<li><div class="ekipa_funkcja wyroznienie">Zdjęcia</div><div class="ekipa_osoba wyroznienie"><a href="index.php/1142176">Piotr Sobociński jr</a></div><div class="ekipa_opis wyroznienie">&nbsp;</div></li>
<li><div class="ekipa_funkcja wyroznienie">Obsada aktorska</div><div class="ekipa_osoba wyroznienie"><a href="index.php/114681">Arkadiusz Jakubik</a></div><div class="ekipa_opis wyroznienie">psycholog więzienny Rafał Wejman</div><div class="ekipa_osoba"><a href="index.php/114681">Arkadiusz Jakubik</a></div><div class="ekipa_opis">psycholog więzienny Rafał Wejman</div><div class="ekipa_osoba"><a href="index.php/1119917">Maja Ostaszewska</a></div><div class="ekipa_opis">Magda Wejman</div></li>
</ul>
</article>
'''

SAMPLE_GALLERY_HTML = '''
<article id="galeria_filmu">
<img src="/z1/17i/5617_1.jpg">
<img src="/z1/117i/5617_2.jpg">
</article>
'''


class ParserTests(unittest.TestCase):
    def test_extract_and_deduplicate_films(self):
        films = extract_films_from_html(SAMPLE_YEAR_HTML)

        self.assertEqual(3, len(films))
        by_id = {film["film_id"]: film for film in films}

        self.assertIn("427356", by_id)
        self.assertEqual("WIELKI REDYK", by_id["427356"]["title"])
        self.assertEqual(["BIAŁY REDYK"], by_id["427356"]["alternate_titles"])

        self.assertEqual("Film fabularny", by_id["999999"]["film_type"])
        self.assertEqual("Jan Kowalski", by_id["999999"]["text_author"])
        self.assertEqual("Adam Nowak", by_id["999999"]["creators"])

    def test_parse_locations_parentheses_expansion(self):
        locations = parse_locations_from_tech3(
            "Lokacje: Zawiercie (basen przy ul. Glinianej, Miejski Ośrodek Kultury przy ul. Piastowskiej 1, ulice: Huldczyńskiego i Senatorska, blok przy ul. Wschodniej 2)."
        )
        self.assertEqual(
            [
                "Zawiercie (basen przy ul. Glinianej)",
                "Zawiercie (Miejski Ośrodek Kultury przy ul. Piastowskiej 1)",
                "Zawiercie (ulice: Huldczyńskiego i Senatorska)",
                "Zawiercie (blok przy ul. Wschodniej 2)",
            ],
            locations,
        )

    def test_extract_movie_details(self):
        details = extract_movie_details_from_html(SAMPLE_MOVIE_HTML)
        self.assertEqual("POJEDYNEK", details["title"])
        self.assertEqual("2021-2025", details["production_years"])
        self.assertIn("Zawiercie (basen przy ul. Glinianej)", details["locations"])
        self.assertIn("Łódź", details["locations"])
        self.assertIn("Opis filmu.", details["description"])
        self.assertEqual("https://filmpolski.pl/fp/index.php/1556274", details["gallery_link"])

        self.assertEqual([{"name": "Maciej Kawalski", "id": "1193213"}], details["directors"])
        self.assertEqual([{"name": "Łukasz Światowiec", "id": "11144590"}], details["screenwriters"])
        self.assertEqual([{"name": "Piotr Sobociński jr", "id": "1142176"}], details["cinematographers"])

        self.assertEqual("Arkadiusz Jakubik", details["cast_main"][0]["name"])
        cast_other_ids = {a["id"] for a in details["cast_other"]}
        self.assertNotIn("114681", cast_other_ids)
        self.assertIn("1119917", cast_other_ids)

    def test_gallery_utils(self):
        self.assertEqual(
            "https://filmpolski.pl/fp/index.php?galeria_filmu=155617",
            build_gallery_page_url("https://filmpolski.pl/fp/index.php/155617"),
        )
        self.assertEqual(
            [
                "https://filmpolski.pl/z1/17z/5617_1.jpg",
                "https://filmpolski.pl/z1/117z/5617_2.jpg",
            ],
            extract_gallery_image_urls(SAMPLE_GALLERY_HTML),
        )


if __name__ == "__main__":
    unittest.main()
