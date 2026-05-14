# Problem transportowy

Aplikacja w Pythonie (`Tkinter`) liczaca problem transportowy metoda maksymalnego elementu macierzy.

## Funkcje

- maksymalnie 10 dostawcow i 10 odbiorcow,
- wpisywanie kosztow transportu, kosztow zakupu u dostawcow i cen sprzedazy u odbiorcow,
- liczenie zysku jednostkowego jako `cena sprzedazy - koszt zakupu - koszt transportu`,
- blokowanie wybranych tras,
- blokowanie tras fikcyjnego dostawcy `FD` i fikcyjnego odbiorcy `FO` przed bilansowaniem,
- bilansowanie przez fikcyjnego dostawce `FD` i fikcyjnego odbiorce `FO`,
- tabela koncowa i tabela dla kazdej iteracji,
- wyswietlanie tabel delt oraz informacji, czy plan jest optymalny.

## Uruchomienie

```bash
python3.13 app.py
```

## Algorytm

1. Program sprawdza, czy suma podazy jest rowna sumie popytu.
2. Jezeli nie, dodaje fikcyjnego dostawce albo odbiorce.
3. Program liczy macierz zyskow jednostkowych.
4. W kazdej iteracji wybiera dostepna trase o najwiekszym zysku jednostkowym.
5. Przydziela `min(pozostala podaz, pozostaly popyt)`.
6. Zapisuje stan po iteracji i pokazuje go w tabeli.
7. Po planie startowym liczy delty `delta = z - alpha - beta`.
8. Jezeli istnieje dodatnia delta, poprawia plan i ponownie liczy delty.
