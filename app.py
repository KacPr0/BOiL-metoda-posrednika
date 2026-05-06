import tkinter as tk
from tkinter import messagebox, ttk


MAX_SIZE = 10


def kopiuj_macierz(macierz):
    return [wiersz[:] for wiersz in macierz]


def bilansuj_problem(zyski, podaz, popyt, blokady, dostawcy, odbiorcy):
    suma_podazy = sum(podaz)
    suma_popytu = sum(popyt)
    komunikat = "Problem byl juz zbilansowany."

    if suma_podazy > suma_popytu:
        roznica = suma_podazy - suma_popytu
        for wiersz in zyski:
            wiersz.append(0.0)
        for wiersz in blokady:
            wiersz.append(False)
        popyt.append(roznica)
        odbiorcy.append("OF")
        komunikat = "Dodano fikcyjnego odbiorce."

    elif suma_popytu > suma_podazy:
        roznica = suma_popytu - suma_podazy
        zyski.append([0.0] * len(popyt))
        blokady.append([False] * len(popyt))
        podaz.append(roznica)
        dostawcy.append("DF")
        komunikat = "Dodano fikcyjnego dostawce."

    return komunikat


def czy_da_sie_domknac(podaz, popyt, blokady):
    for i in range(len(podaz)):
        if podaz[i] > 0 and not any(popyt[j] > 0 and not blokady[i][j] for j in range(len(popyt))):
            return False

    for j in range(len(popyt)):
        if popyt[j] > 0 and not any(podaz[i] > 0 and not blokady[i][j] for i in range(len(podaz))):
            return False

    return True


def rozwiaz_metoda_maksymalnego_elementu(zyski, podaz, popyt, blokady, dostawcy, odbiorcy):
    zyski = kopiuj_macierz(zyski)
    blokady = kopiuj_macierz(blokady)
    podaz = podaz[:]
    popyt = popyt[:]
    dostawcy = dostawcy[:]
    odbiorcy = odbiorcy[:]

    komunikat_bilansu = bilansuj_problem(
        zyski, podaz, popyt, blokady, dostawcy, odbiorcy
    )

    liczba_dostawcow = len(podaz)
    liczba_odbiorcow = len(popyt)
    alokacja = [[0.0 for _ in range(liczba_odbiorcow)] for _ in range(liczba_dostawcow)]
    iteracje = []

    while sum(podaz) > 0 or sum(popyt) > 0:
        if not czy_da_sie_domknac(podaz, popyt, blokady):
            raise ValueError("Po ustawionych blokadach nie da sie zbudowac pelnego planu.")

        najlepszy_wiersz = -1
        najlepsza_kolumna = -1
        najlepsza_wartosc = -1

        for i in range(liczba_dostawcow):
            if podaz[i] <= 0:
                continue
            for j in range(liczba_odbiorcow):
                if popyt[j] <= 0:
                    continue
                if blokady[i][j]:
                    continue
                if zyski[i][j] > najlepsza_wartosc:
                    najlepsza_wartosc = zyski[i][j]
                    najlepszy_wiersz = i
                    najlepsza_kolumna = j

        if najlepszy_wiersz == -1 or najlepsza_kolumna == -1:
            raise ValueError("Nie znaleziono dostepnej trasy do dalszego przydzialu.")

        przydzial = min(podaz[najlepszy_wiersz], popyt[najlepsza_kolumna])
        alokacja[najlepszy_wiersz][najlepsza_kolumna] += przydzial
        podaz[najlepszy_wiersz] -= przydzial
        popyt[najlepsza_kolumna] -= przydzial

        iteracje.append(
            {
                "nr": len(iteracje) + 1,
                "wiersz": najlepszy_wiersz,
                "kolumna": najlepsza_kolumna,
                "wartosc": najlepsza_wartosc,
                "przydzial": przydzial,
                "alokacja": kopiuj_macierz(alokacja),
                "podaz": podaz[:],
                "popyt": popyt[:],
            }
        )

    wynik = sum(
        alokacja[i][j] * zyski[i][j]
        for i in range(liczba_dostawcow)
        for j in range(liczba_odbiorcow)
    )

    return {
        "alokacja": alokacja,
        "iteracje": iteracje,
        "wynik": wynik,
        "zyski": zyski,
        "blokady": blokady,
        "dostawcy": dostawcy,
        "odbiorcy": odbiorcy,
        "komunikat_bilansu": komunikat_bilansu,
    }


class AplikacjaTransportowa:
    def __init__(self, root):
        self.root = root
        self.root.title("Problem transportowy")
        self.root.geometry("1300x850")

        self.liczba_dostawcow = tk.IntVar(value=3)
        self.liczba_odbiorcow = tk.IntVar(value=3)

        self.pola_zyskow = []
        self.pola_blokad = []
        self.pola_podazy = []
        self.pola_popytu = []
        self.nazwy_dostawcow = []
        self.nazwy_odbiorcow = []

        self.ramka_danych = None
        self.ramka_wynikow = None
        self.canvas_wynikow = None
        self.opis_wyniku = tk.StringVar(value="Wpisz dane i kliknij Oblicz.")

        self.zbuduj_okno()
        self.root.bind_all("<MouseWheel>", self.scroll_myszki)
        self.root.bind_all("<Button-4>", self.scroll_myszki)
        self.root.bind_all("<Button-5>", self.scroll_myszki)
        self.utworz_tabele()
        self.wczytaj_przyklad()

    def zbuduj_okno(self):
        gora = ttk.Frame(self.root, padding=10)
        gora.pack(fill="x")

        ttk.Label(gora, text="Dostawcy:").pack(side="left", padx=5)
        ttk.Spinbox(gora, from_=1, to=MAX_SIZE, width=5, textvariable=self.liczba_dostawcow).pack(side="left")

        ttk.Label(gora, text="Odbiorcy:").pack(side="left", padx=(15, 5))
        ttk.Spinbox(gora, from_=1, to=MAX_SIZE, width=5, textvariable=self.liczba_odbiorcow).pack(side="left")

        ttk.Button(gora, text="Utworz tabele", command=self.utworz_tabele).pack(side="left", padx=10)
        ttk.Button(gora, text="Przyklad", command=self.wczytaj_przyklad).pack(side="left", padx=5)
        ttk.Button(gora, text="Zbilansuj", command=self.zbilansuj_tabele).pack(side="left", padx=5)
        ttk.Button(gora, text="Oblicz", command=self.oblicz).pack(side="left", padx=5)

        ttk.Label(
            self.root,
            text="W komorce wpisujesz wartosc. Zaznaczenie pola 'Blokada' oznacza zakaz transportu na tej trasie.",
            padding=(10, 0),
        ).pack(anchor="w")

        self.ramka_danych = ttk.Frame(self.root, padding=10)
        self.ramka_danych.pack(fill="x")

        ttk.Label(
            self.root,
            textvariable=self.opis_wyniku,
            font=("TkDefaultFont", 10, "bold"),
            padding=(10, 5),
        ).pack(anchor="w")

        obszar = ttk.Frame(self.root, padding=10)
        obszar.pack(fill="both", expand=True)

        canvas = tk.Canvas(obszar, highlightthickness=0)
        self.canvas_wynikow = canvas
        pasek = ttk.Scrollbar(obszar, orient="vertical", command=canvas.yview)
        self.ramka_wynikow = ttk.Frame(canvas)

        self.ramka_wynikow.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")),
        )

        canvas.create_window((0, 0), window=self.ramka_wynikow, anchor="nw")
        canvas.configure(yscrollcommand=pasek.set)

        canvas.pack(side="left", fill="both", expand=True)
        pasek.pack(side="right", fill="y")

    def scroll_myszki(self, event):
        if self.canvas_wynikow is None:
            return

        if getattr(event, "num", None) == 4:
            self.canvas_wynikow.yview_scroll(-3, "units")
        elif getattr(event, "num", None) == 5:
            self.canvas_wynikow.yview_scroll(3, "units")
        elif event.delta != 0:
            kierunek = -1 if event.delta > 0 else 1
            przesuniecie = max(3, abs(event.delta) // 40)
            self.canvas_wynikow.yview_scroll(kierunek * przesuniecie, "units")

    def utworz_tabele(self, resetuj_nazwy=True):
        for widget in self.ramka_danych.winfo_children():
            widget.destroy()

        wiersze = max(1, min(MAX_SIZE, self.liczba_dostawcow.get()))
        kolumny = max(1, min(MAX_SIZE, self.liczba_odbiorcow.get()))
        self.liczba_dostawcow.set(wiersze)
        self.liczba_odbiorcow.set(kolumny)

        self.pola_zyskow = [
            [tk.StringVar(value="0") for _ in range(kolumny)] for _ in range(wiersze)
        ]
        self.pola_blokad = [
            [tk.BooleanVar(value=False) for _ in range(kolumny)] for _ in range(wiersze)
        ]
        self.pola_podazy = [tk.StringVar(value="0") for _ in range(wiersze)]
        self.pola_popytu = [tk.StringVar(value="0") for _ in range(kolumny)]

        if resetuj_nazwy or len(self.nazwy_dostawcow) != wiersze:
            self.nazwy_dostawcow = [f"D{i + 1}" for i in range(wiersze)]
        if resetuj_nazwy or len(self.nazwy_odbiorcow) != kolumny:
            self.nazwy_odbiorcow = [f"O{j + 1}" for j in range(kolumny)]

        ttk.Label(self.ramka_danych, text="").grid(row=0, column=0, padx=4, pady=4)
        for j in range(kolumny):
            ttk.Label(self.ramka_danych, text=self.nazwy_odbiorcow[j]).grid(
                row=0, column=j + 1, padx=4, pady=4
            )
        ttk.Label(self.ramka_danych, text="Podaz").grid(
            row=0, column=kolumny + 1, padx=4, pady=4
        )

        for i in range(wiersze):
            ttk.Label(self.ramka_danych, text=self.nazwy_dostawcow[i]).grid(
                row=i + 1, column=0, padx=4, pady=4
            )
            for j in range(kolumny):
                ramka_komorki = ttk.Frame(
                    self.ramka_danych, relief="solid", borderwidth=1, padding=4
                )
                ramka_komorki.grid(row=i + 1, column=j + 1, padx=3, pady=3)

                ttk.Entry(
                    ramka_komorki,
                    width=8,
                    justify="center",
                    textvariable=self.pola_zyskow[i][j],
                ).pack()
                ttk.Checkbutton(
                    ramka_komorki,
                    text="Blokada",
                    variable=self.pola_blokad[i][j],
                ).pack()

            ttk.Entry(
                self.ramka_danych,
                width=10,
                justify="center",
                textvariable=self.pola_podazy[i],
            ).grid(row=i + 1, column=kolumny + 1, padx=4, pady=4)

        ttk.Label(self.ramka_danych, text="Popyt").grid(
            row=wiersze + 1, column=0, padx=4, pady=4
        )
        for j in range(kolumny):
            ttk.Entry(
                self.ramka_danych,
                width=10,
                justify="center",
                textvariable=self.pola_popytu[j],
            ).grid(row=wiersze + 1, column=j + 1, padx=4, pady=4)

        self.wyczysc_wyniki()

    def wczytaj_przyklad(self):
        self.liczba_dostawcow.set(2)
        self.liczba_odbiorcow.set(3)
        self.utworz_tabele()

        przyklad_zyskow = [
            [8, 14, 17],
            [12, 9, 19],
        ]
        przyklad_podazy = [20, 30]
        przyklad_popytu = [10, 28, 29]
        przyklad_blokad = [
            [False, False, False],
            [False, False, False],
        ]

        for i, podaz in enumerate(przyklad_podazy):
            self.pola_podazy[i].set(str(podaz))
            for j, zysk in enumerate(przyklad_zyskow[i]):
                self.pola_zyskow[i][j].set(str(zysk))
                self.pola_blokad[i][j].set(przyklad_blokad[i][j])

        for j, popyt in enumerate(przyklad_popytu):
            self.pola_popytu[j].set(str(popyt))

    def wpisz_dane_do_tabeli(self, zyski, podaz, popyt, blokady):
        for i in range(len(podaz)):
            self.pola_podazy[i].set(str(podaz[i]))
            for j in range(len(popyt)):
                self.pola_zyskow[i][j].set(str(zyski[i][j]))
                self.pola_blokad[i][j].set(blokady[i][j])

        for j in range(len(popyt)):
            self.pola_popytu[j].set(str(popyt[j]))

    def zbilansuj_tabele(self):
        try:
            zyski, podaz, popyt, blokady, dostawcy, odbiorcy = self.pobierz_dane()
        except ValueError as blad:
            messagebox.showerror("Blad", str(blad))
            return

        suma_podazy = sum(podaz)
        suma_popytu = sum(popyt)

        if suma_podazy == suma_popytu:
            messagebox.showinfo("Bilans", "Problem jest juz zbilansowany.")
            return

        if suma_podazy > suma_popytu:
            if len(popyt) >= MAX_SIZE:
                messagebox.showerror("Blad", "Nie mozna dodac fikcyjnego odbiorcy, bo jest juz 10 odbiorcow.")
                return
            roznica = suma_podazy - suma_popytu
            for wiersz in zyski:
                wiersz.append(0.0)
            for wiersz in blokady:
                wiersz.append(False)
            popyt.append(roznica)
            odbiorcy.append("OF")
        else:
            if len(podaz) >= MAX_SIZE:
                messagebox.showerror("Blad", "Nie mozna dodac fikcyjnego dostawcy, bo jest juz 10 dostawcow.")
                return
            roznica = suma_popytu - suma_podazy
            zyski.append([0.0] * len(popyt))
            blokady.append([False] * len(popyt))
            podaz.append(roznica)
            dostawcy.append("DF")

        self.nazwy_dostawcow = dostawcy
        self.nazwy_odbiorcow = odbiorcy
        self.liczba_dostawcow.set(len(dostawcy))
        self.liczba_odbiorcow.set(len(odbiorcy))
        self.utworz_tabele(resetuj_nazwy=False)
        self.wpisz_dane_do_tabeli(zyski, podaz, popyt, blokady)
        self.opis_wyniku.set("Tabela zostala zbilansowana. Mozesz teraz ustawic blokady i kliknac Oblicz.")

    def pobierz_liczbe(self, tekst, nazwa):
        tekst = tekst.strip().replace(",", ".")
        if tekst == "":
            raise ValueError(f"Pole {nazwa} nie moze byc puste.")
        try:
            liczba = float(tekst)
        except ValueError as blad:
            raise ValueError(f"Pole {nazwa} musi byc liczba.") from blad
        if liczba < 0:
            raise ValueError(f"Pole {nazwa} nie moze byc ujemne.")
        return liczba

    def pobierz_dane(self):
        wiersze = self.liczba_dostawcow.get()
        kolumny = self.liczba_odbiorcow.get()

        zyski = [
            [
                self.pobierz_liczbe(self.pola_zyskow[i][j].get(), f"D{i + 1}-O{j + 1}")
                for j in range(kolumny)
            ]
            for i in range(wiersze)
        ]
        blokady = [
            [self.pola_blokad[i][j].get() for j in range(kolumny)]
            for i in range(wiersze)
        ]
        podaz = [
            self.pobierz_liczbe(self.pola_podazy[i].get(), f"podaz D{i + 1}")
            for i in range(wiersze)
        ]
        popyt = [
            self.pobierz_liczbe(self.pola_popytu[j].get(), f"popyt O{j + 1}")
            for j in range(kolumny)
        ]
        dostawcy = self.nazwy_dostawcow[:]
        odbiorcy = self.nazwy_odbiorcow[:]

        return zyski, podaz, popyt, blokady, dostawcy, odbiorcy

    def wyczysc_wyniki(self):
        for widget in self.ramka_wynikow.winfo_children():
            widget.destroy()
        self.opis_wyniku.set("Wpisz dane i kliknij Oblicz.")

    def oblicz(self):
        try:
            dane = self.pobierz_dane()
            wynik = rozwiaz_metoda_maksymalnego_elementu(*dane)
        except ValueError as blad:
            messagebox.showerror("Blad", str(blad))
            return
        except Exception as blad:
            messagebox.showerror("Blad", f"Wystapil nieoczekiwany blad:\n{blad}")
            return

        self.pokaz_wyniki(wynik)

    def pokaz_wyniki(self, wynik):
        self.wyczysc_wyniki()
        self.opis_wyniku.set(
            f"Wynik koncowy: {wynik['wynik']:.2f} | "
            f"Liczba iteracji: {len(wynik['iteracje'])} | "
            f"{wynik['komunikat_bilansu']}"
        )

        ramka = ttk.LabelFrame(self.ramka_wynikow, text="Tabela koncowa", padding=8)
        ramka.pack(fill="x", pady=5)
        self.rysuj_tabele(
            ramka,
            wynik["dostawcy"],
            wynik["odbiorcy"],
            wynik["alokacja"],
            wynik["zyski"],
            wynik["blokady"],
            [0] * len(wynik["dostawcy"]),
            [0] * len(wynik["odbiorcy"]),
        )

        for iteracja in wynik["iteracje"]:
            ramka_iteracji = ttk.LabelFrame(
                self.ramka_wynikow,
                text=f"Iteracja {iteracja['nr']}",
                padding=8,
            )
            ramka_iteracji.pack(fill="x", pady=5)

            opis = (
                f"Wybrano trase {wynik['dostawcy'][iteracja['wiersz']]} -> "
                f"{wynik['odbiorcy'][iteracja['kolumna']]}, "
                f"wartosc = {iteracja['wartosc']}, przydzial = {iteracja['przydzial']}."
            )
            ttk.Label(ramka_iteracji, text=opis).pack(anchor="w", pady=(0, 5))

            self.rysuj_tabele(
                ramka_iteracji,
                wynik["dostawcy"],
                wynik["odbiorcy"],
                iteracja["alokacja"],
                wynik["zyski"],
                wynik["blokady"],
                iteracja["podaz"],
                iteracja["popyt"],
                (iteracja["wiersz"], iteracja["kolumna"]),
            )

    def rysuj_tabele(
        self,
        rodzic,
        dostawcy,
        odbiorcy,
        alokacja,
        zyski,
        blokady,
        podaz,
        popyt,
        zaznaczenie=None,
    ):
        tabela = ttk.Frame(rodzic)
        tabela.pack(anchor="w")

        ttk.Label(tabela, text="").grid(row=0, column=0, padx=3, pady=3)
        for j, nazwa in enumerate(odbiorcy):
            ttk.Label(tabela, text=nazwa).grid(row=0, column=j + 1, padx=3, pady=3)
        ttk.Label(tabela, text="Pozostala podaz").grid(
            row=0, column=len(odbiorcy) + 1, padx=3, pady=3
        )

        for i, nazwa in enumerate(dostawcy):
            ttk.Label(tabela, text=nazwa).grid(row=i + 1, column=0, padx=3, pady=3)
            for j in range(len(odbiorcy)):
                tekst = f"a={alokacja[i][j]:.2f}\nz={zyski[i][j]:.2f}"
                if blokady[i][j] and alokacja[i][j] == 0:
                    tekst = f"X\nz={zyski[i][j]:.2f}"

                if zaznaczenie == (i, j):
                    kolor = "#bfe3b4"
                elif blokady[i][j] and alokacja[i][j] == 0:
                    kolor = "#f3c7c7"
                else:
                    kolor = "#e3ddd5"

                tk.Label(
                    tabela,
                    text=tekst,
                    width=12,
                    height=3,
                    relief="solid",
                    bg=kolor,
                    fg="#1f1f1f",
                    font=("TkDefaultFont", 11),
                ).grid(row=i + 1, column=j + 1, padx=2, pady=2)

            ttk.Label(tabela, text=f"{podaz[i]:.2f}").grid(
                row=i + 1,
                column=len(odbiorcy) + 1,
                padx=3,
                pady=3,
            )

        ttk.Label(tabela, text="Pozostaly popyt").grid(
            row=len(dostawcy) + 1,
            column=0,
            padx=3,
            pady=3,
        )
        for j in range(len(odbiorcy)):
            ttk.Label(tabela, text=f"{popyt[j]:.2f}").grid(
                row=len(dostawcy) + 1,
                column=j + 1,
                padx=3,
                pady=3,
            )


def main():
    root = tk.Tk()
    AplikacjaTransportowa(root)
    root.mainloop()


if __name__ == "__main__":
    main()
