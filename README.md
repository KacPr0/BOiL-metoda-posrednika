# Problem transportowy

Aplikacja w Pythonie (`Tkinter`) liczaca problem transportowy metoda maksymalnego elementu macierzy.

## Funkcje

- maksymalnie 10 dostawcow i 10 odbiorcow,
- blokowanie wybranych tras,
- bilansowanie przez fikcyjnego dostawce `DF` albo fikcyjnego odbiorce `OF`,
- przycisk `Zbilansuj`, ktory pokazuje `DF/OF` przed obliczeniami,
- tabela koncowa i tabela dla kazdej iteracji.

## Uruchomienie

```bash
/opt/homebrew/bin/python3.13 app.py
```

## Algorytm

1. Program sprawdza, czy suma podazy jest rowna sumie popytu.
2. Jezeli nie, dodaje fikcyjnego dostawce albo odbiorce.
3. W kazdej iteracji wybiera dostepna trase o najwiekszej wartosci.
4. Przydziela `min(pozostala podaz, pozostaly popyt)`.
5. Zapisuje stan po iteracji i pokazuje go w tabeli.
