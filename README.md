# filmpolski

Uporządkowany skrypt CLI do pracy na danych FilmPolski. Działa etapami, które można uruchamiać niezależnie:

1. pobieranie stron roczników,
2. parsowanie roczników do JSON,
3. pobieranie stron filmów,
4. parsowanie stron filmów do JSON,
5. pobieranie galerii zdjęć.

Plik: `scrape_filmpolski_years.py`.

## Najważniejsze założenia

- Zakres lat wybierasz przez `--start-year` i `--end-year`.
- Każdy etap uruchamiasz osobną flagą: `--download-years`, `--parse-years`, `--download-movies`, `--parse-movies`, `--download-galleries`.
- Etapy można łączyć w jednym uruchomieniu.
- Domyślnie istniejące pliki są **pomijane** (brak ponownego pobierania/przetwarzania).
- Użyj `--overwrite`, aby wymusić nadpisanie.

## Katalogi

- roczniki: `data/years`
  - `YEAR.html`
  - `YEAR.json`
- filmy (strony i JSON): `movies/YEAR`
  - `movies/YEAR/ID.html`
  - `movies/YEAR/ID.json`
- galerie zdjęć: `movies/ID`
  - `movies/ID/gallery_ID.html`
  - `movies/ID/*.jpg`

Możesz zmienić katalogi przez:
- `--years-dir`
- `--movies-dir`

## Przykłady użycia

### 1) Tylko pobranie stron roczników

```bash
python3 scrape_filmpolski_years.py --download-years --start-year 1911 --end-year 2026
```

### 2) Tylko parsowanie wcześniej pobranych roczników do JSON

```bash
python3 scrape_filmpolski_years.py --parse-years --start-year 1911 --end-year 2026
```

### 3) Tylko pobieranie stron filmów (z filtrem rodzaju)

```bash
python3 scrape_filmpolski_years.py --download-movies --movie-type "Film fabularny" --start-year 2000 --end-year 2005
```

Możesz podać wiele typów:

```bash
python3 scrape_filmpolski_years.py --download-movies --movie-type "Film fabularny" --movie-type "Serial fabularny"
```

W trakcie pobierania filmów skrypt wypisuje postęp: ile pobrano i ile pominięto względem planu rocznego.

### 4) Tylko parsowanie wcześniej pobranych stron filmów do JSON

```bash
python3 scrape_filmpolski_years.py --parse-movies --start-year 2000 --end-year 2005
```

### 5) Pobieranie galerii zdjęć

```bash
python3 scrape_filmpolski_years.py --download-galleries --start-year 2000 --end-year 2005
```

Jak działa `--download-galleries`:
- dla każdego `movies/YEAR/ID.json` bierze pole `gallery_link`,
- jeśli `gallery_link` ma postać `https://filmpolski.pl/fp/index.php/<GALERIA_ID>`, pobiera stronę:
  - `https://filmpolski.pl/fp/index.php?galeria_filmu=<GALERIA_ID>`
- zapisuje ją jako `movies/ID/gallery_ID.html`,
- z `<article id="galeria_filmu">` zbiera wszystkie `<img src="...">`,
- w ścieżce obrazka zamienia segment `.../<liczba>i/...` na `.../<liczba>z/...`,
- pobiera zdjęcia do `movies/ID/`.

W logu postępu podaje:
- który film jest aktualnie przetwarzany w danym roku,
- które zdjęcie (x/y) jest aktualnie pobierane.

### 6) Łączenie etapów w jednym wywołaniu

```bash
python3 scrape_filmpolski_years.py \
  --download-years --parse-years \
  --download-movies --parse-movies --download-galleries \
  --movie-type "Film fabularny" \
  --start-year 2020 --end-year 2021
```

### 7) Wymuszenie nadpisania

```bash
python3 scrape_filmpolski_years.py --download-years --overwrite
```

## Struktura JSON rocznika (`data/years/YEAR.json`)

Każdy film (unikalny po `index.php/<id>`) ma pola:
- `film_id`
- `link`
- `title`
- `alternate_titles` (z `span.tytulnieindeksowany`)
- `film_type`
- `text_author`
- `creators`

## Struktura JSON filmu (`movies/YEAR/ID.json`)

- `title`
- `production_years`
- `locations` (z logiką nawiasów, np. `Zawiercie (a, b)` → `Zawiercie (a)`, `Zawiercie (b)`)
- `description`
- `gallery_link`
- `directors` (unikalne obiekty: `name`, `id`)
- `screenwriters` (unikalne obiekty: `name`, `id`)
- `cinematographers` (unikalne obiekty: `name`, `id`)
- `cast_main` (`name`, `id`, `character`)
- `cast_other` (`name`, `id`, `character`)

Dodatkowo aktor z `cast_main` jest usuwany z `cast_other`.
