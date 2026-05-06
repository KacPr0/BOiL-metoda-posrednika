# Problem transportowy

## Program umozliwia

- wpisanie danych dla maksymalnie 10 dostawcow i 10 odbiorcow,
- liczenie metoda maksymalnego elementu macierzy,
- blokowanie wybranych tras,
- bilansowanie przez fikcyjnego dostawce albo odbiorce,
- pokazanie fikcyjnego dostawcy/odbiorcy w tabeli po kliknieciu `Zbilansuj`,
- pokazanie wynikow posrednich dla kazdej iteracji,
- pokazanie tabeli koncowej.

## Uruchomienie

```bash
/opt/homebrew/bin/python3.13 app.py
```

## Logika algorytmu

1. Program odczytuje macierz, podaz, popyt i blokady.
2. Przycisk `Zbilansuj` dodaje fikcyjny wiersz albo kolumne przed obliczaniem.
3. Szuka najwiekszej dostepnej wartosci w macierzy.
4. Przydziela tyle, ile sie da: `min(podaz, popyt)`.
5. Zapisuje stan tabeli po iteracji.
6. Powtarza kroki az do wyczerpania podazy i popytu.
