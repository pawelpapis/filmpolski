# filmpolski

Skrypt do pobierania stron roczników FilmPolski oraz budowania plików JSON z listą filmów.

## Uruchomienie

```bash
python3 scrape_filmpolski_years.py
```

Domyślnie skrypt:
- pobiera lata `1911..2026` z URL `https://filmpolski.pl/fp/index.php?filmy_z_roku=YEAR&typ=2`,
- zapisuje surowy HTML do `data/years/YEAR.html`,
- generuje JSON do `data/years/YEAR.json`.

## Pobieranie stron filmów wybranego rodzaju

```bash
python3 scrape_filmpolski_years.py --start-year 2021 --end-year 2021 --download-movies "Serial fabularny"
```

Po użyciu `--download-movies TYPE` skrypt dla filmów z pasującym `film_type` zapisuje:
- `movies/YEAR/ID.html`
- `movies/YEAR/ID.json`

Plik `movies/YEAR/ID.json` zawiera (o ile dostępne):
- `title`
- `production_years`
- `locations` (lista)
- `description`
- `gallery_link`
- `directors`
- `screenwriters`
- `cinematographers`
- `cast_main`
- `cast_other`

Każdy aktor w `cast_main` / `cast_other` ma pola:
- `name`
- `id`
- `character`

## Opcje

```bash
python3 scrape_filmpolski_years.py --start-year 1946 --end-year 1950 --pause 0.1 --download-movies "Film fabularny"
```

Dostępne flagi:
- `--start-year`
- `--end-year`
- `--output-dir`
- `--pause`
- `--download-movies` (można podać wiele razy)
- `--movies-dir`

## Struktura JSON dla roczników

Każdy film (unikalny po ID z linku `index.php/<id>`) zawiera:
- `film_id`
- `link`
- `title`
- `alternate_titles` (np. wartości z `span.tytulnieindeksowany`)
- `film_type`
- `text_author`
- `creators`

Pola `film_type`, `text_author`, `creators` są wyliczane z `div.rodzajfilmu` zgodnie z liczbą separatorów `/`.
