import tkinter as tk
from tkinter import messagebox, ttk


MAX_SIZE = 10
EPS = 0.000001


# Tworzy niezalezna kopie dwuwymiarowej listy.
def copy_matrix(matrix):
    return [row[:] for row in matrix]


# Formatuje liczby do czytelnego wyswietlania w tabelach.
def format_number(value):
    if abs(value) < EPS:
        value = 0.0
    if abs(value - round(value)) < EPS:
        return str(int(round(value)))
    return f"{value:.2f}"


# Zamienia tekst z pola formularza na liczbe i sprawdza poprawnosc danych.
def parse_number(text, field_name):
    text = text.strip().replace(",", ".")
    if not text:
        raise ValueError(f"Pole '{field_name}' jest puste.")
    try:
        value = float(text)
    except ValueError as error:
        raise ValueError(f"Pole '{field_name}' musi byc liczba.") from error
    if value < 0:
        raise ValueError(f"Pole '{field_name}' nie moze byc ujemne.")
    return value


# Wylicza zysk jednostkowy dla kazdej trasy dostawca-odbiorca.
def calculate_unit_profits(transport_costs, purchase_costs, sale_prices, suppliers, receivers):
    return [
        [
            0.0 if supplier == "FD" or receiver == "FO" else sale_prices[j] - purchase_costs[i] - transport_costs[i][j]
            for j, receiver in enumerate(receivers)
        ]
        for i, supplier in enumerate(suppliers)
    ]


# Podsumowuje przychody oraz koszty wynikajace z koncowego planu transportu.
def calculate_economic_summary(allocation, transport_costs, purchase_costs, sale_prices, suppliers, receivers):
    revenue = transport_cost = purchase_cost = 0.0
    for i, supplier in enumerate(suppliers):
        if supplier == "FD":
            continue
        amount_from_supplier = 0.0
        for j, receiver in enumerate(receivers):
            if receiver == "FO":
                continue
            amount = allocation[i][j]
            amount_from_supplier += amount
            revenue += amount * sale_prices[j]
            transport_cost += amount * transport_costs[i][j]
        purchase_cost += amount_from_supplier * purchase_costs[i]

    return {
        "revenue": revenue,
        "transport_cost": transport_cost,
        "purchase_cost": purchase_cost,
    }


# Ustala priorytet tras pomocniczych przy wyborze kolejnego przydzialu.
def route_priority(supplier, receiver):
    if supplier == "FD":
        return 2 + (receiver == "FO")
    if receiver == "FO":
        return 1
    return 0


# Bilansuje dane, dodajac fikcyjnego dostawce lub odbiorce gdy podaz i popyt sa rozne.
def balance_data(values, supply, demand, blocked, suppliers, receivers):
    values = copy_matrix(values)
    blocked = copy_matrix(blocked)
    supply, demand = supply[:], demand[:]
    suppliers, receivers = suppliers[:], receivers[:]
    supply_sum, demand_sum = sum(supply), sum(demand)

    if abs(supply_sum - demand_sum) < EPS:
        return values, supply, demand, blocked, suppliers, receivers

    for row in values:
        row.append(0.0)
    for row in blocked:
        row.append(False)
    demand.append(supply_sum)
    receivers.append("FO")

    values.append([0.0] * len(demand))
    blocked.append([False] * len(demand))
    supply.append(demand_sum)
    suppliers.append("FD")

    return values, supply, demand, blocked, suppliers, receivers


# Sprawdza metoda przeplywu, czy przy aktualnych blokadach da sie domknac plan.
def can_finish_plan(supply, demand, blocked):
    total_supply = sum(supply)
    total_demand = sum(demand)
    if abs(total_supply - total_demand) > EPS:
        return False

    suppliers_count, receivers_count = len(supply), len(demand)
    start = 0
    first_supplier = 1
    first_receiver = first_supplier + suppliers_count
    end = first_receiver + receivers_count
    size = end + 1
    capacity = [[0.0] * size for _ in range(size)]

    for i, amount in enumerate(supply):
        capacity[start][first_supplier + i] = amount
    for i in range(suppliers_count):
        for j in range(receivers_count):
            if not blocked[i][j]:
                capacity[first_supplier + i][first_receiver + j] = total_supply
    for j, amount in enumerate(demand):
        capacity[first_receiver + j][end] = amount

    flow = 0.0
    while True:
        parent = [-1] * size
        parent[start] = start
        queue = [start]

        while queue and parent[end] == -1:
            node = queue.pop(0)
            for next_node, amount in enumerate(capacity[node]):
                if parent[next_node] == -1 and amount > EPS:
                    parent[next_node] = node
                    queue.append(next_node)

        if parent[end] == -1:
            return abs(flow - total_demand) < EPS

        pushed = float("inf")
        node = end
        while node != start:
            pushed = min(pushed, capacity[parent[node]][node])
            node = parent[node]

        node = end
        while node != start:
            previous = parent[node]
            capacity[previous][node] -= pushed
            capacity[node][previous] += pushed
            node = previous
        flow += pushed


# Oblicza zmienne dualne alpha i beta dla aktualnej bazy przydzialow.
def calculate_dual_variables(values, allocation):
    suppliers_count = len(values)
    receivers_count = len(values[0]) if values else 0
    basic = [[allocation[i][j] > EPS for j in range(receivers_count)] for i in range(suppliers_count)]
    alpha = [None] * suppliers_count
    beta = [None] * receivers_count

    for start_supplier in range(suppliers_count):
        if alpha[start_supplier] is not None:
            continue
        alpha[start_supplier] = 0.0
        changed = True
        while changed:
            changed = False
            for i in range(suppliers_count):
                for j in range(receivers_count):
                    if not basic[i][j]:
                        continue
                    if alpha[i] is not None and beta[j] is None:
                        beta[j] = values[i][j] - alpha[i]
                        changed = True
                    elif alpha[i] is None and beta[j] is not None:
                        alpha[i] = values[i][j] - beta[j]
                        changed = True
    return alpha, beta


# Buduje tabele delt uzywana do oceny, czy plan mozna jeszcze poprawic.
def calculate_delta_table(values, allocation, blocked):
    alpha, beta = calculate_dual_variables(values, allocation)
    deltas = []
    for i, row in enumerate(values):
        delta_row = []
        for j, value in enumerate(row):
            if allocation[i][j] > EPS:
                delta_row.append("X")
            elif blocked[i][j] or alpha[i] is None or beta[j] is None:
                delta_row.append("-inf")
            else:
                delta_row.append(format_number(value - alpha[i] - beta[j]))
        deltas.append(delta_row)
    return deltas


# Szuka cyklu korekcyjnego po dodaniu nowej komorki bazowej do planu.
def find_cycle(allocation, entering_row, entering_col):
    suppliers_count = len(allocation)
    receivers_count = len(allocation[0]) if allocation else 0
    graph = {("r", i): [] for i in range(suppliers_count)}
    graph.update({("c", j): [] for j in range(receivers_count)})

    for i in range(suppliers_count):
        for j in range(receivers_count):
            if allocation[i][j] > EPS:
                graph[("r", i)].append((("c", j), (i, j)))
                graph[("c", j)].append((("r", i), (i, j)))

    start = ("r", entering_row)
    target = ("c", entering_col)
    queue = [start]
    parents = {start: (None, None)}

    while queue and target not in parents:
        node = queue.pop(0)
        for next_node, cell in graph[node]:
            if next_node not in parents:
                parents[next_node] = (node, cell)
                queue.append(next_node)

    if target not in parents:
        return []

    path = []
    node = target
    while parents[node][0] is not None:
        node, cell = parents[node]
        path.append(cell)
    path.reverse()
    return [(entering_row, entering_col)] + path


# Poprawia plan transportowy metoda potencjalow, wykorzystujac dodatnie delty.
def improve_plan_with_deltas(values, allocation, blocked):
    allocation = copy_matrix(allocation)
    steps = []

    while True:
        deltas = calculate_delta_table(values, allocation, blocked)
        best = None
        for i, row in enumerate(deltas):
            for j, value in enumerate(row):
                try:
                    value = float(value)
                except ValueError:
                    continue
                if value > EPS and (best is None or value > best[0]):
                    best = (value, i, j)

        step = {
            "deltas": deltas,
            "entering": None if best is None else (best[1], best[2]),
            "allocation_after": None,
            "theta": None,
        }
        steps.append(step)

        if best is None:
            break

        _, row, col = best
        cycle = find_cycle(allocation, row, col)
        if not cycle:
            break

        theta = min(allocation[i][j] for i, j in cycle[1::2])
        for index, (i, j) in enumerate(cycle):
            allocation[i][j] += theta if index % 2 == 0 else -theta
            if abs(allocation[i][j]) < EPS:
                allocation[i][j] = 0.0

        step["allocation_after"] = copy_matrix(allocation)
        step["theta"] = theta

    return allocation, steps


# Wyznacza plan startowy metoda maksymalnego elementu, a nastepnie go optymalizuje.
def solve_max_element_method(values, supply, demand, blocked, suppliers, receivers):
    values, supply, demand, blocked, suppliers, receivers = balance_data(
        values, supply, demand, blocked, suppliers, receivers
    )
    suppliers_count, receivers_count = len(supply), len(demand)
    allocation = [[0.0] * receivers_count for _ in range(suppliers_count)]
    iterations = []

    while sum(supply) > EPS or sum(demand) > EPS:
        if not can_finish_plan(supply, demand, blocked):
            raise ValueError("Po ustawionych blokadach nie da sie zbudowac pelnego planu.")

        candidates = []
        for i in range(suppliers_count):
            if supply[i] <= EPS:
                continue
            for j in range(receivers_count):
                if demand[j] > EPS and not blocked[i][j]:
                    candidates.append(
                        (values[i][j], route_priority(suppliers[i], receivers[j]), min(supply[i], demand[j]), i, j)
                    )

        if not candidates:
            raise ValueError("Brak dostepnej trasy do dalszego przydzialu.")

        chosen = None
        for value, _, amount, i, j in sorted(candidates, reverse=True):
            test_supply = supply[:]
            test_demand = demand[:]
            test_supply[i] -= amount
            test_demand[j] -= amount
            if can_finish_plan(test_supply, test_demand, blocked):
                chosen = (value, amount, i, j)
                break

        if chosen is None:
            raise ValueError("Blokady nie pozwalaja domknac calego planu.")

        value, amount, i, j = chosen
        allocation[i][j] += amount
        supply[i] -= amount
        demand[j] -= amount
        if abs(supply[i]) < EPS:
            supply[i] = 0.0
        if abs(demand[j]) < EPS:
            demand[j] = 0.0

        iterations.append(
            {
                "number": len(iterations) + 1,
                "row": i,
                "col": j,
                "value": value,
                "amount": amount,
                "allocation": copy_matrix(allocation),
                "supply": supply[:],
                "demand": demand[:],
            }
        )

    allocation, delta_steps = improve_plan_with_deltas(values, allocation, blocked)
    total = sum(allocation[i][j] * values[i][j] for i in range(suppliers_count) for j in range(receivers_count))

    return {
        "values": values,
        "blocked": blocked,
        "suppliers": suppliers,
        "receivers": receivers,
        "allocation": allocation,
        "iterations": iterations,
        "delta_steps": delta_steps,
        "total": total,
    }


class TransportApp:
    # Inicjalizuje glowne okno aplikacji, zmienne formularza i dane przykladowe.
    def __init__(self, root):
        self.root = root
        self.root.title("Problem transportowy - metoda maksymalnego elementu")
        self.root.geometry("1300x850")

        self.supplier_count = tk.IntVar(value=2)
        self.receiver_count = tk.IntVar(value=3)
        self.fake_cross_block_var = tk.BooleanVar(value=False)
        self.summary_text = tk.StringVar(value="Wprowadz dane i kliknij Oblicz.")

        self.supplier_names = []
        self.receiver_names = []
        self.value_vars = []
        self.block_vars = []
        self.supply_vars = []
        self.demand_vars = []
        self.purchase_cost_vars = []
        self.sale_price_vars = []
        self.fake_receiver_block_vars = []
        self.fake_supplier_block_vars = []

        self.build_window()
        self.root.bind_all("<MouseWheel>", self.scroll_results)
        self.root.bind_all("<Button-4>", self.scroll_results)
        self.root.bind_all("<Button-5>", self.scroll_results)
        self.build_input_table()
        self.load_example()

    # Buduje podstawowy uklad okna: panel sterowania, formularz i obszar wynikow.
    def build_window(self):
        top = ttk.Frame(self.root, padding=10)
        top.pack(fill="x")

        for text, variable in (("Dostawcy:", self.supplier_count), ("Odbiorcy:", self.receiver_count)):
            ttk.Label(top, text=text).pack(side="left", padx=(15 if text == "Odbiorcy:" else 5, 5))
            ttk.Spinbox(top, from_=1, to=MAX_SIZE, width=5, textvariable=variable).pack(side="left")

        ttk.Button(top, text="Utworz tabele", command=self.build_input_table).pack(side="left", padx=10)
        ttk.Button(top, text="Przyklad", command=self.load_example).pack(side="left", padx=5)
        ttk.Button(top, text="Oblicz", command=self.calculate).pack(side="left", padx=5)

        self.input_frame = ttk.Frame(self.root, padding=10)
        self.input_frame.pack(fill="x")
        ttk.Label(self.root, textvariable=self.summary_text, font=("TkDefaultFont", 10, "bold"), padding=(10, 5)).pack(
            anchor="w"
        )

        result_area = ttk.Frame(self.root, padding=10)
        result_area.pack(fill="both", expand=True)
        self.result_canvas = tk.Canvas(result_area, highlightthickness=0)
        scrollbar = ttk.Scrollbar(result_area, orient="vertical", command=self.result_canvas.yview)
        self.result_frame = ttk.Frame(self.result_canvas)
        self.result_frame.bind("<Configure>", lambda event: self.result_canvas.configure(scrollregion=self.result_canvas.bbox("all")))
        self.result_canvas.create_window((0, 0), window=self.result_frame, anchor="nw")
        self.result_canvas.configure(yscrollcommand=scrollbar.set)
        self.result_canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    # Obsluguje przewijanie obszaru wynikow kolkiem myszy.
    def scroll_results(self, event):
        if getattr(event, "num", None) == 4:
            self.result_canvas.yview_scroll(-3, "units")
        elif getattr(event, "num", None) == 5:
            self.result_canvas.yview_scroll(3, "units")
        elif event.delta:
            self.result_canvas.yview_scroll((-1 if event.delta > 0 else 1) * max(3, abs(event.delta) // 40), "units")

    # Dodaje pojedyncze pole tekstowe do siatki formularza.
    def add_entry(self, parent, row, col, variable=None, width=10, disabled=False):
        entry = ttk.Entry(parent, width=width, justify="center", textvariable=variable)
        if disabled:
            entry.insert(0, "0")
            entry.configure(state="disabled")
        entry.grid(row=row, column=col, padx=4, pady=4)

    # Dodaje etykiete tekstowa do siatki formularza.
    def add_label(self, text, row, col):
        ttk.Label(self.input_frame, text=text).grid(row=row, column=col, padx=4, pady=4)

    # Dodaje komorke kosztu z polem wartosci i checkboxem blokady trasy.
    def add_cell(self, row, col, variable=None, block_var=None, disabled=False):
        cell = ttk.Frame(self.input_frame, relief="solid", borderwidth=1, padding=4)
        cell.grid(row=row, column=col, padx=3, pady=3)
        entry = ttk.Entry(cell, width=8, justify="center", textvariable=variable)
        if disabled:
            entry.insert(0, "0")
            entry.configure(state="disabled")
        entry.pack()
        ttk.Checkbutton(cell, text="Blokada", variable=block_var).pack()

    # Tworzy lub odtwarza tabele danych wejsciowych dla podanej liczby dostawcow i odbiorcow.
    def build_input_table(self):
        for widget in self.input_frame.winfo_children():
            widget.destroy()

        rows = max(1, min(MAX_SIZE, self.supplier_count.get()))
        cols = max(1, min(MAX_SIZE, self.receiver_count.get()))
        self.supplier_count.set(rows)
        self.receiver_count.set(cols)
        self.supplier_names = [f"D{i + 1}" for i in range(rows)]
        self.receiver_names = [f"O{j + 1}" for j in range(cols)]

        text_vars = lambda size: [tk.StringVar(value="0") for _ in range(size)]
        bool_vars = lambda size: [tk.BooleanVar(value=False) for _ in range(size)]
        self.value_vars = [text_vars(cols) for _ in range(rows)]
        self.block_vars = [bool_vars(cols) for _ in range(rows)]
        self.supply_vars, self.purchase_cost_vars = text_vars(rows), text_vars(rows)
        self.demand_vars, self.sale_price_vars = text_vars(cols), text_vars(cols)
        self.fake_receiver_block_vars = bool_vars(rows)
        self.fake_supplier_block_vars = bool_vars(cols)
        self.fake_cross_block_var = tk.BooleanVar(value=False)

        display_receivers = self.receiver_names + ["FO"]
        display_cols = cols + 1
        display_rows = rows + 1

        self.add_label("", 0, 0)
        for j, name in enumerate(display_receivers):
            self.add_label(name, 0, j + 1)
        self.add_label("Podaz", 0, display_cols + 1)
        self.add_label("Koszty zakupu u dostawcy", 0, display_cols + 2)

        for i, name in enumerate(self.supplier_names):
            self.add_label(name, i + 1, 0)
            for j in range(cols):
                self.add_cell(i + 1, j + 1, self.value_vars[i][j], self.block_vars[i][j])
            self.add_cell(i + 1, cols + 1, block_var=self.fake_receiver_block_vars[i], disabled=True)
            self.add_entry(self.input_frame, i + 1, display_cols + 1, self.supply_vars[i])
            self.add_entry(self.input_frame, i + 1, display_cols + 2, self.purchase_cost_vars[i], width=18)

        fake_row = rows + 1
        self.add_label("FD", fake_row, 0)
        for j in range(cols):
            self.add_cell(fake_row, j + 1, block_var=self.fake_supplier_block_vars[j], disabled=True)
        self.add_cell(fake_row, cols + 1, block_var=self.fake_cross_block_var, disabled=True)
        self.add_entry(self.input_frame, fake_row, display_cols + 1, width=10, disabled=True)
        self.add_entry(self.input_frame, fake_row, display_cols + 2, width=18, disabled=True)

        self.add_label("Popyt", display_rows + 1, 0)
        for j in range(cols):
            self.add_entry(self.input_frame, display_rows + 1, j + 1, self.demand_vars[j])
        self.add_entry(self.input_frame, display_rows + 1, cols + 1, disabled=True)

        self.add_label("Cena sprzedazy u odbiorcy", display_rows + 2, 0)
        for j in range(cols):
            self.add_entry(self.input_frame, display_rows + 2, j + 1, self.sale_price_vars[j])
        self.add_entry(self.input_frame, display_rows + 2, cols + 1, disabled=True)
        self.clear_results()

    # Wczytuje przykladowy zestaw danych do szybkiego testowania programu.
    def load_example(self):
        self.supplier_count.set(2)
        self.receiver_count.set(3)
        self.build_input_table()
        self.fill_input_table(
            [[8, 14, 17], [12, 9, 19]],
            [20, 30],
            [10, 28, 27],
            [[False, True, False], [False, False, False]],
            [10, 12],
            [30, 25, 30],
        )

    # Uzupelnia pola formularza przekazanymi kosztami, podaza, popytem i blokadami.
    def fill_input_table(self, transport_costs, supply, demand, blocked, purchase_costs, sale_prices):
        for i, amount in enumerate(supply):
            self.supply_vars[i].set(str(amount))
            self.purchase_cost_vars[i].set(str(purchase_costs[i]))
            for j, value in enumerate(demand):
                self.value_vars[i][j].set(str(transport_costs[i][j]))
                self.block_vars[i][j].set(blocked[i][j])
        for j, amount in enumerate(demand):
            self.demand_vars[j].set(str(amount))
            self.sale_price_vars[j].set(str(sale_prices[j]))

    # Odczytuje serie pol liczbowych i zwraca je jako liste wartosci float.
    def read_numbers(self, variables, names, text):
        return [parse_number(var.get(), f"{text} {names[i]}") for i, var in enumerate(variables)]

    # Pobiera wszystkie dane wpisane przez uzytkownika w formularzu.
    def read_input_data(self):
        rows, cols = self.supplier_count.get(), self.receiver_count.get()
        transport_costs = [
            [
                parse_number(self.value_vars[i][j].get(), f"koszt transportu {self.supplier_names[i]}-{self.receiver_names[j]}")
                for j in range(cols)
            ]
            for i in range(rows)
        ]
        blocked = [[self.block_vars[i][j].get() for j in range(cols)] for i in range(rows)]
        supply = self.read_numbers(self.supply_vars, self.supplier_names, "podaz")
        demand = self.read_numbers(self.demand_vars, self.receiver_names, "popyt")
        purchase_costs = self.read_numbers(self.purchase_cost_vars, self.supplier_names, "koszt zakupu")
        sale_prices = self.read_numbers(self.sale_price_vars, self.receiver_names, "cena sprzedazy")
        return transport_costs, supply, demand, blocked, purchase_costs, sale_prices, self.supplier_names[:], self.receiver_names[:]

    # Bilansuje dane formularza z uwzglednieniem blokad dla fikcyjnych tras.
    def balance_input_data(self, transport_costs, supply, demand, blocked, purchase_costs, sale_prices, suppliers, receivers):
        supply_sum, demand_sum = sum(supply), sum(demand)
        if abs(supply_sum - demand_sum) < EPS:
            return transport_costs, supply, demand, blocked, purchase_costs, sale_prices, suppliers, receivers

        fake_receiver_blocks = [var.get() for var in self.fake_receiver_block_vars[: len(suppliers)]]
        fake_supplier_blocks = [var.get() for var in self.fake_supplier_block_vars[: len(receivers)]]

        for i, row in enumerate(transport_costs):
            row.append(0.0)
            blocked[i].append(fake_receiver_blocks[i])
        demand.append(supply_sum)
        sale_prices.append(0.0)
        receivers.append("FO")

        transport_costs.append([0.0] * len(demand))
        blocked.append(fake_supplier_blocks + [self.fake_cross_block_var.get()])
        supply.append(demand_sum)
        purchase_costs.append(0.0)
        suppliers.append("FD")
        return transport_costs, supply, demand, blocked, purchase_costs, sale_prices, suppliers, receivers

    # Czysci poprzednie wyniki i przywraca komunikat poczatkowy.
    def clear_results(self):
        for widget in self.result_frame.winfo_children():
            widget.destroy()
        self.summary_text.set("Wprowadz dane i kliknij Oblicz.")

    # Uruchamia walidacje danych, obliczenia i wyswietlenie wynikow.
    def calculate(self):
        try:
            data = self.read_input_data()
            transport_costs, supply, demand, blocked, purchase_costs, sale_prices, suppliers, receivers = self.balance_input_data(*data)
            if len(suppliers) > MAX_SIZE or len(receivers) > MAX_SIZE:
                raise ValueError("Po zbilansowaniu tabela przekroczylaby limit 10 x 10.")

            values = calculate_unit_profits(transport_costs, purchase_costs, sale_prices, suppliers, receivers)
            result = solve_max_element_method(values, supply, demand, blocked, suppliers, receivers)
            result["economic_summary"] = calculate_economic_summary(
                result["allocation"], transport_costs, purchase_costs, sale_prices, result["suppliers"], result["receivers"]
            )
        except ValueError as error:
            messagebox.showerror("Blad danych", str(error))
            return
        except Exception as error:
            messagebox.showerror("Blad", f"Wystapil nieoczekiwany blad:\n{error}")
            return

        self.show_result(result)

    # Renderuje wynik koncowy oraz kolejne iteracje w obszarze wynikow.
    def show_result(self, result):
        self.clear_results()
        self.summary_text.set(f"Zysk calkowity: {result['total']:.2f} | Liczba iteracji: {len(result['iterations'])}")
        ttk.Label(
            self.result_frame,
            text="Opis komorek: a = przydzial, z = zysk jednostkowy, X = brak przydzialu lub zablokowana trasa.",
            font=("TkDefaultFont", 10, "bold"),
        ).pack(anchor="w", pady=(0, 6))

        final_box = ttk.LabelFrame(self.result_frame, text="Tabela koncowa", padding=8)
        final_box.pack(fill="x", pady=5)
        changes = self.get_final_changes(result)
        if changes:
            ttk.Label(final_box, text="Zielony = przydzial zwiekszony po poprawce, pomaranczowy = przydzial zmniejszony po poprawce.").pack(anchor="w", pady=(0, 5))
        self.draw_table(final_box, result, result["allocation"], [0.0] * len(result["suppliers"]), [0.0] * len(result["receivers"]), show_duals=True, changes=changes)
        self.draw_economic_summary(result)
        self.draw_delta_steps(result)

        for step in result["iterations"]:
            box = ttk.LabelFrame(self.result_frame, text=f"Iteracja {step['number']}", padding=8)
            box.pack(fill="x", pady=5)
            ttk.Label(
                box,
                text=(
                    f"Wybrano trase {result['suppliers'][step['row']]} -> {result['receivers'][step['col']]}, "
                    f"zysk jednostkowy = {step['value']}, przydzial = {step['amount']}."
                ),
            ).pack(anchor="w", pady=(0, 5))
            self.draw_table(box, result, step["allocation"], step["supply"], step["demand"], (step["row"], step["col"]))

    # Wyswietla tabele delt i informacje o ewentualnych poprawkach planu.
    def draw_delta_steps(self, result):
        box = ttk.LabelFrame(self.result_frame, text="Delty i ocena optymalnosci", padding=8)
        box.pack(fill="x", pady=5)
        ttk.Label(box, text="delta = z - alpha - beta. Dodatnia delta oznacza, ze plan mozna poprawic.").pack(anchor="w", pady=(0, 6))

        for index, step in enumerate(result["delta_steps"], start=1):
            frame = ttk.LabelFrame(box, text=f"Tabela delt {index}", padding=6)
            frame.pack(fill="x", pady=5)

            if step["entering"] is None:
                ttk.Label(frame, text="Wszystkie delty sa niedodatnie - plan jest optymalny.").pack(anchor="w", pady=(0, 5))
            else:
                row, col = step["entering"]
                text = f"Najwieksza dodatnia delta: {result['suppliers'][row]} -> {result['receivers'][col]}"
                if step["theta"] is not None:
                    text += f", przesuniecie = {format_number(step['theta'])}"
                ttk.Label(frame, text=text).pack(anchor="w", pady=(0, 5))

            self.draw_delta_table(frame, result, step["deltas"], step["entering"])

            if step["allocation_after"] is not None:
                allocation_box = ttk.LabelFrame(frame, text="Plan po poprawce", padding=6)
                allocation_box.pack(fill="x", pady=5)
                self.draw_table(
                    allocation_box,
                    result,
                    step["allocation_after"],
                    [0.0] * len(result["suppliers"]),
                    [0.0] * len(result["receivers"]),
                )

    # Rysuje pojedyncza tabele delt.
    def draw_delta_table(self, parent, result, deltas, selected=None):
        table = ttk.Frame(parent)
        table.pack(anchor="w")

        ttk.Label(table, text="").grid(row=0, column=0, padx=3, pady=3)
        for j, name in enumerate(result["receivers"]):
            ttk.Label(table, text=name).grid(row=0, column=j + 1, padx=3, pady=3)

        for i, name in enumerate(result["suppliers"]):
            ttk.Label(table, text=name).grid(row=i + 1, column=0, padx=3, pady=3)
            for j in range(len(result["receivers"])):
                value = deltas[i][j]
                color = "#e3ddd5"
                if selected == (i, j):
                    color = "#bfe3b4"
                elif value == "X":
                    color = "#d8d8d8"
                else:
                    try:
                        if float(value) > EPS:
                            color = "#ffd49a"
                    except ValueError:
                        color = "#f3c7c7"

                tk.Label(
                    table,
                    text=str(value),
                    width=12,
                    height=2,
                    relief="solid",
                    bg=color,
                    fg="#1f1f1f",
                    font=("TkDefaultFont", 11),
                ).grid(row=i + 1, column=j + 1, padx=2, pady=2)

    # Porownuje plan po metodzie delt z ostatnia iteracja planu startowego.
    def get_final_changes(self, result):
        if not result["iterations"]:
            return {}
        before = result["iterations"][-1]["allocation"]
        after = result["allocation"]
        return {
            (i, j): "up" if after[i][j] > before[i][j] else "down"
            for i in range(len(after))
            for j in range(len(after[i]))
            if abs(after[i][j] - before[i][j]) > EPS
        }

    # Wyswietla przychod, koszt transportu i koszt zakupu dla planu koncowego.
    def draw_economic_summary(self, result):
        box = ttk.LabelFrame(self.result_frame, text="Podsumowanie ekonomiczne", padding=8)
        box.pack(fill="x", pady=5)
        for label, key in (
            ("Przychod calkowity", "revenue"),
            ("Koszt transportu", "transport_cost"),
            ("Koszt zakupu", "purchase_cost"),
        ):
            ttk.Label(box, text=f"{label}: {format_number(result['economic_summary'][key])}").pack(anchor="w")

    # Rysuje tabele przydzialow, zyskow jednostkowych oraz opcjonalnie zmiennych dualnych.
    def draw_table(self, parent, result, allocation, supply, demand, selected=None, show_duals=False, changes=None):
        changes = changes or {}
        table = ttk.Frame(parent)
        table.pack(anchor="w")
        alpha, beta = (calculate_dual_variables(result["values"], allocation) if show_duals else ([], []))

        ttk.Label(table, text="").grid(row=0, column=0, padx=3, pady=3)
        for j, name in enumerate(result["receivers"]):
            ttk.Label(table, text=name).grid(row=0, column=j + 1, padx=3, pady=3)
        ttk.Label(table, text="alpha_i" if show_duals else "Pozostala podaz").grid(row=0, column=len(result["receivers"]) + 1, padx=3, pady=3)

        for i, name in enumerate(result["suppliers"]):
            ttk.Label(table, text=name).grid(row=i + 1, column=0, padx=3, pady=3)
            for j in range(len(result["receivers"])):
                amount = format_number(allocation[i][j]) if allocation[i][j] > EPS else "X"
                text = f"a={amount}\nz={format_number(result['values'][i][j])}"
                color = "#e3ddd5"
                if selected == (i, j):
                    color = "#bfe3b4"
                elif changes.get((i, j)) == "up":
                    color = "#bfe3b4"
                elif changes.get((i, j)) == "down":
                    color = "#ffd49a"
                elif result["blocked"][i][j] and allocation[i][j] <= EPS:
                    text = f"X\nz={format_number(result['values'][i][j])}"
                    color = "#f3c7c7"
                tk.Label(table, text=text, width=12, height=3, relief="solid", bg=color, fg="#1f1f1f", font=("TkDefaultFont", 11)).grid(
                    row=i + 1, column=j + 1, padx=2, pady=2
                )

            value = alpha[i] if show_duals and alpha[i] is not None else supply[i]
            ttk.Label(table, text=format_number(value)).grid(row=i + 1, column=len(result["receivers"]) + 1, padx=3, pady=3)

        bottom_row = len(result["suppliers"]) + 1
        ttk.Label(table, text="beta_j" if show_duals else "Pozostaly popyt").grid(row=bottom_row, column=0, padx=3, pady=3)
        for j in range(len(result["receivers"])):
            value = beta[j] if show_duals and beta[j] is not None else demand[j]
            ttk.Label(table, text=format_number(value)).grid(row=bottom_row, column=j + 1, padx=3, pady=3)


# Startuje aplikacje Tkinter.
def main():
    root = tk.Tk()
    TransportApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
