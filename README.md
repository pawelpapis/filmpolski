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

### Opcje

```bash
python3 scrape_filmpolski_years.py --start-year 1946 --end-year 1950 --pause 0.1
```

Dostępne flagi:
- `--start-year`
- `--end-year`
- `--output-dir`
- `--pause`

## Struktura JSON

Każdy film (unikalny po ID z linku `index.php/<id>`) zawiera:
- `film_id`
- `link`
- `title`
- `alternate_titles` (np. wartości z `span.tytulnieindeksowany`)
- `film_type`
- `text_author`
- `creators`

Pola `film_type`, `text_author`, `creators` są wyliczane z `div.rodzajfilmu` zgodnie z liczbą separatorów `/`.
