import tkinter as tk
from tkinter import messagebox, ttk


MAX_SIZE = 10
EPS = 0.000001


def copy_matrix(matrix):
    return [row[:] for row in matrix]


def calculate_unit_profits(transport_costs, purchase_costs, sale_prices, suppliers, receivers):
    profits = []
    for i, supplier in enumerate(suppliers):
        row = []
        for j, receiver in enumerate(receivers):
            if supplier == "FD" or receiver == "FO":
                row.append(0.0)
            else:
                row.append(sale_prices[j] - purchase_costs[i] - transport_costs[i][j])
        profits.append(row)
    return profits


def calculate_economic_summary(allocation, transport_costs, purchase_costs, sale_prices, suppliers, receivers):
    revenue = 0.0
    transport_cost = 0.0
    purchase_cost = 0.0

    for i, supplier in enumerate(suppliers):
        if supplier == "FD":
            continue
        supplier_real_amount = 0.0
        for j, receiver in enumerate(receivers):
            if receiver == "FO":
                continue
            amount = allocation[i][j]
            supplier_real_amount += amount
            revenue += amount * sale_prices[j]
            transport_cost += amount * transport_costs[i][j]
        purchase_cost += supplier_real_amount * purchase_costs[i]

    return {
        "revenue": revenue,
        "transport_cost": transport_cost,
        "purchase_cost": purchase_cost,
        "profit_check": revenue - transport_cost - purchase_cost,
    }


def parse_number(text, field_name, allow_negative=False):
    text = text.strip().replace(",", ".")
    if text == "":
        raise ValueError(f"Pole '{field_name}' jest puste.")

    try:
        value = float(text)
    except ValueError as error:
        raise ValueError(f"Pole '{field_name}' musi byc liczba.") from error

    if value < 0 and not allow_negative:
        raise ValueError(f"Pole '{field_name}' nie moze byc ujemne.")

    return value


def format_number(value):
    if abs(value) < EPS:
        value = 0.0
    if abs(value - round(value)) < EPS:
        return str(int(round(value)))
    return f"{value:.2f}"


def route_priority(supplier, receiver):
    if supplier == "FD" and receiver == "FO":
        return 3
    if supplier == "FD" and receiver != "FO":
        return 2
    if supplier != "FD" and receiver == "FO":
        return 1
    return 0


def is_number_text(value):
    try:
        float(value)
    except ValueError:
        return False
    return True


def calculate_delta_table(values, allocation, blocked):
    supplier_count = len(values)
    receiver_count = len(values[0]) if values else 0
    basic = [
        [allocation[i][j] > EPS for j in range(receiver_count)]
        for i in range(supplier_count)
    ]

    supplier_potentials, receiver_potentials = calculate_dual_variables(values, allocation)

    deltas = []
    for i in range(supplier_count):
        row = []
        for j in range(receiver_count):
            if basic[i][j]:
                row.append("X")
            elif blocked[i][j]:
                row.append("-inf")
            elif supplier_potentials[i] is None or receiver_potentials[j] is None:
                row.append("-inf")
            else:
                row.append(format_number(values[i][j] - supplier_potentials[i] - receiver_potentials[j]))
        deltas.append(row)

    return deltas


def calculate_dual_variables(values, allocation):
    supplier_count = len(values)
    receiver_count = len(values[0]) if values else 0
    basic = [
        [allocation[i][j] > EPS for j in range(receiver_count)]
        for i in range(supplier_count)
    ]
    supplier_potentials = [None] * supplier_count
    receiver_potentials = [None] * receiver_count

    for start_supplier in range(supplier_count):
        if supplier_potentials[start_supplier] is not None:
            continue
        supplier_potentials[start_supplier] = 0.0
        changed = True
        while changed:
            changed = False
            for i in range(supplier_count):
                for j in range(receiver_count):
                    if not basic[i][j]:
                        continue
                    if supplier_potentials[i] is not None and receiver_potentials[j] is None:
                        receiver_potentials[j] = values[i][j] - supplier_potentials[i]
                        changed = True
                    elif supplier_potentials[i] is None and receiver_potentials[j] is not None:
                        supplier_potentials[i] = values[i][j] - receiver_potentials[j]
                        changed = True

    return supplier_potentials, receiver_potentials


def find_cycle(allocation, entering_row, entering_col):
    supplier_count = len(allocation)
    receiver_count = len(allocation[0]) if allocation else 0
    start = ("r", entering_row)
    target = ("c", entering_col)
    graph = {}

    for i in range(supplier_count):
        graph.setdefault(("r", i), [])
    for j in range(receiver_count):
        graph.setdefault(("c", j), [])

    for i in range(supplier_count):
        for j in range(receiver_count):
            if allocation[i][j] > EPS:
                row_node = ("r", i)
                col_node = ("c", j)
                graph[row_node].append((col_node, (i, j)))
                graph[col_node].append((row_node, (i, j)))

    queue = [start]
    parents = {start: (None, None)}

    while queue and target not in parents:
        current = queue.pop(0)
        for next_node, cell in graph[current]:
            if next_node in parents:
                continue
            parents[next_node] = (current, cell)
            queue.append(next_node)

    if target not in parents:
        return []

    path_cells = []
    node = target
    while parents[node][0] is not None:
        previous, cell = parents[node]
        path_cells.append(cell)
        node = previous
    path_cells.reverse()

    return [(entering_row, entering_col)] + path_cells


def improve_plan_with_deltas(values, allocation, blocked):
    allocation = copy_matrix(allocation)
    delta_steps = []

    while True:
        deltas = calculate_delta_table(values, allocation, blocked)
        best = None
        for i, row in enumerate(deltas):
            for j, value in enumerate(row):
                if not is_number_text(value):
                    continue
                numeric_value = float(value)
                if numeric_value > EPS and (best is None or numeric_value > best[0]):
                    best = (numeric_value, i, j)

        delta_step = {
            "deltas": deltas,
            "entering": None if best is None else (best[1], best[2]),
            "allocation_after": None,
            "theta": None,
        }
        delta_steps.append(delta_step)

        if best is None:
            break

        _, entering_row, entering_col = best
        cycle = find_cycle(allocation, entering_row, entering_col)
        if not cycle:
            break

        minus_cells = cycle[1::2]
        theta = min(allocation[i][j] for i, j in minus_cells)
        for index, (i, j) in enumerate(cycle):
            if index % 2 == 0:
                allocation[i][j] += theta
            else:
                allocation[i][j] -= theta
                if abs(allocation[i][j]) < EPS:
                    allocation[i][j] = 0.0
        delta_step["allocation_after"] = copy_matrix(allocation)
        delta_step["theta"] = theta

    return allocation, delta_steps


def balance_data(values, supply, demand, blocked, suppliers, receivers):
    values = copy_matrix(values)
    blocked = copy_matrix(blocked)
    supply = supply[:]
    demand = demand[:]
    suppliers = suppliers[:]
    receivers = receivers[:]

    supply_sum = sum(supply)
    demand_sum = sum(demand)

    if abs(supply_sum - demand_sum) < EPS:
        return values, supply, demand, blocked, suppliers, receivers, "Problem byl juz zbilansowany."

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

    return values, supply, demand, blocked, suppliers, receivers, "Dodano fikcyjnego dostawce FD i odbiorce FO."


def can_finish_plan(supply, demand, blocked):
    if abs(sum(supply) - sum(demand)) > EPS:
        return False

    supplier_count = len(supply)
    receiver_count = len(demand)
    start = 0
    first_supplier = 1
    first_receiver = first_supplier + supplier_count
    end = first_receiver + receiver_count
    size = end + 1
    capacity = [[0.0 for _ in range(size)] for _ in range(size)]

    for i, amount in enumerate(supply):
        capacity[start][first_supplier + i] = amount

    for i in range(supplier_count):
        for j in range(receiver_count):
            if not blocked[i][j]:
                capacity[first_supplier + i][first_receiver + j] = sum(supply)

    for j, amount in enumerate(demand):
        capacity[first_receiver + j][end] = amount

    flow = 0.0

    while True:
        parent = [-1] * size
        parent[start] = start
        queue = [start]

        while queue and parent[end] == -1:
            current = queue.pop(0)
            for next_node in range(size):
                if parent[next_node] == -1 and capacity[current][next_node] > EPS:
                    parent[next_node] = current
                    queue.append(next_node)

        if parent[end] == -1:
            break

        pushed = float("inf")
        node = end
        while node != start:
            previous = parent[node]
            pushed = min(pushed, capacity[previous][node])
            node = previous

        node = end
        while node != start:
            previous = parent[node]
            capacity[previous][node] -= pushed
            capacity[node][previous] += pushed
            node = previous

        flow += pushed

    return abs(flow - sum(demand)) < EPS


def solve_max_element_method(values, supply, demand, blocked, suppliers, receivers):
    values, supply, demand, blocked, suppliers, receivers, balance_note = balance_data(
        values, supply, demand, blocked, suppliers, receivers
    )

    supplier_count = len(supply)
    receiver_count = len(demand)
    allocation = [[0.0 for _ in range(receiver_count)] for _ in range(supplier_count)]
    iterations = []

    while sum(supply) > EPS or sum(demand) > EPS:
        if not can_finish_plan(supply, demand, blocked):
            raise ValueError("Po ustawionych blokadach nie da sie zbudowac pelnego planu.")

        candidates = []
        for i in range(supplier_count):
            if supply[i] <= EPS:
                continue
            for j in range(receiver_count):
                if demand[j] <= EPS or blocked[i][j]:
                    continue
                amount = min(supply[i], demand[j])
                candidates.append(
                    (
                        values[i][j],
                        route_priority(suppliers[i], receivers[j]),
                        amount,
                        i,
                        j,
                    )
                )

        if not candidates:
            raise ValueError("Brak dostepnej trasy do dalszego przydzialu.")

        candidates.sort(reverse=True)
        chosen = None

        for value, priority, amount, i, j in candidates:
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

    total = sum(
        allocation[i][j] * values[i][j]
        for i in range(supplier_count)
        for j in range(receiver_count)
    )

    return {
        "values": values,
        "blocked": blocked,
        "suppliers": suppliers,
        "receivers": receivers,
        "allocation": allocation,
        "iterations": iterations,
        "delta_steps": delta_steps,
        "total": total,
        "balance_note": balance_note,
    }


class TransportApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Problem transportowy - metoda maksymalnego elementu")
        self.root.geometry("1300x850")

        self.supplier_count = tk.IntVar(value=2)
        self.receiver_count = tk.IntVar(value=3)

        self.value_vars = []
        self.block_vars = []
        self.supply_vars = []
        self.demand_vars = []
        self.purchase_cost_vars = []
        self.sale_price_vars = []
        self.fake_receiver_block_vars = []
        self.fake_supplier_block_vars = []
        self.fake_cross_block_var = tk.BooleanVar(value=False)
        self.supplier_names = []
        self.receiver_names = []

        self.input_frame = None
        self.result_frame = None
        self.result_canvas = None
        self.summary_text = tk.StringVar(value="Wprowadz dane i kliknij Oblicz.")

        self.build_window()
        self.root.bind_all("<MouseWheel>", self.scroll_results)
        self.root.bind_all("<Button-4>", self.scroll_results)
        self.root.bind_all("<Button-5>", self.scroll_results)
        self.build_input_table()
        self.load_example()

    def build_window(self):
        top = ttk.Frame(self.root, padding=10)
        top.pack(fill="x")

        ttk.Label(top, text="Dostawcy:").pack(side="left", padx=5)
        ttk.Spinbox(top, from_=1, to=MAX_SIZE, width=5, textvariable=self.supplier_count).pack(side="left")

        ttk.Label(top, text="Odbiorcy:").pack(side="left", padx=(15, 5))
        ttk.Spinbox(top, from_=1, to=MAX_SIZE, width=5, textvariable=self.receiver_count).pack(side="left")

        ttk.Button(top, text="Utworz tabele", command=self.build_input_table).pack(side="left", padx=10)
        ttk.Button(top, text="Przyklad", command=self.load_example).pack(side="left", padx=5)
        ttk.Button(top, text="Oblicz", command=self.calculate).pack(side="left", padx=5)

        self.input_frame = ttk.Frame(self.root, padding=10)
        self.input_frame.pack(fill="x")

        ttk.Label(
            self.root,
            textvariable=self.summary_text,
            font=("TkDefaultFont", 10, "bold"),
            padding=(10, 5),
        ).pack(anchor="w")

        result_area = ttk.Frame(self.root, padding=10)
        result_area.pack(fill="both", expand=True)

        self.result_canvas = tk.Canvas(result_area, highlightthickness=0)
        scrollbar = ttk.Scrollbar(result_area, orient="vertical", command=self.result_canvas.yview)
        self.result_frame = ttk.Frame(self.result_canvas)

        self.result_frame.bind(
            "<Configure>",
            lambda event: self.result_canvas.configure(scrollregion=self.result_canvas.bbox("all")),
        )

        self.result_canvas.create_window((0, 0), window=self.result_frame, anchor="nw")
        self.result_canvas.configure(yscrollcommand=scrollbar.set)
        self.result_canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def scroll_results(self, event):
        if self.result_canvas is None:
            return

        if getattr(event, "num", None) == 4:
            self.result_canvas.yview_scroll(-3, "units")
        elif getattr(event, "num", None) == 5:
            self.result_canvas.yview_scroll(3, "units")
        elif event.delta != 0:
            direction = -1 if event.delta > 0 else 1
            self.result_canvas.yview_scroll(direction * max(3, abs(event.delta) // 40), "units")

    def build_input_table(self, keep_names=False):
        for widget in self.input_frame.winfo_children():
            widget.destroy()

        rows = max(1, min(MAX_SIZE, self.supplier_count.get()))
        cols = max(1, min(MAX_SIZE, self.receiver_count.get()))
        self.supplier_count.set(rows)
        self.receiver_count.set(cols)

        if not keep_names or len(self.supplier_names) != rows:
            self.supplier_names = [f"D{i + 1}" for i in range(rows)]
        if not keep_names or len(self.receiver_names) != cols:
            self.receiver_names = [f"O{j + 1}" for j in range(cols)]

        self.value_vars = [[tk.StringVar(value="0") for _ in range(cols)] for _ in range(rows)]
        self.block_vars = [[tk.BooleanVar(value=False) for _ in range(cols)] for _ in range(rows)]
        self.supply_vars = [tk.StringVar(value="0") for _ in range(rows)]
        self.demand_vars = [tk.StringVar(value="0") for _ in range(cols)]
        self.purchase_cost_vars = [tk.StringVar(value="0") for _ in range(rows)]
        self.sale_price_vars = [tk.StringVar(value="0") for _ in range(cols)]
        self.fake_receiver_block_vars = [tk.BooleanVar(value=False) for _ in range(rows)]
        self.fake_supplier_block_vars = [tk.BooleanVar(value=False) for _ in range(cols)]
        self.fake_cross_block_var = tk.BooleanVar(value=False)

        show_fake_preview = "FD" not in self.supplier_names and "FO" not in self.receiver_names
        display_receivers = self.receiver_names + (["FO"] if show_fake_preview else [])
        display_rows = rows + (1 if show_fake_preview else 0)
        display_cols = cols + (1 if show_fake_preview else 0)

        ttk.Label(self.input_frame, text="").grid(row=0, column=0, padx=4, pady=4)
        for j, name in enumerate(display_receivers):
            ttk.Label(self.input_frame, text=name).grid(row=0, column=j + 1, padx=4, pady=4)
        ttk.Label(self.input_frame, text="Podaz").grid(row=0, column=display_cols + 1, padx=4, pady=4)
        ttk.Label(self.input_frame, text="Koszty zakupu u dostawcy").grid(
            row=0, column=display_cols + 2, padx=4, pady=4
        )

        for i, name in enumerate(self.supplier_names):
            ttk.Label(self.input_frame, text=name).grid(row=i + 1, column=0, padx=4, pady=4)
            for j in range(cols):
                cell = ttk.Frame(self.input_frame, relief="solid", borderwidth=1, padding=4)
                cell.grid(row=i + 1, column=j + 1, padx=3, pady=3)

                ttk.Entry(cell, width=8, justify="center", textvariable=self.value_vars[i][j]).pack()
                ttk.Checkbutton(cell, text="Blokada", variable=self.block_vars[i][j]).pack()

            if show_fake_preview:
                cell = ttk.Frame(self.input_frame, relief="solid", borderwidth=1, padding=4)
                cell.grid(row=i + 1, column=cols + 1, padx=3, pady=3)
                entry = ttk.Entry(cell, width=8, justify="center")
                entry.insert(0, "0")
                entry.configure(state="disabled")
                entry.pack()
                ttk.Checkbutton(cell, text="Blokada", variable=self.fake_receiver_block_vars[i]).pack()

            ttk.Entry(self.input_frame, width=10, justify="center", textvariable=self.supply_vars[i]).grid(
                row=i + 1, column=display_cols + 1, padx=4, pady=4
            )
            ttk.Entry(
                self.input_frame,
                width=18,
                justify="center",
                textvariable=self.purchase_cost_vars[i],
            ).grid(row=i + 1, column=display_cols + 2, padx=4, pady=4)

        if show_fake_preview:
            fake_row = rows + 1
            ttk.Label(self.input_frame, text="FD").grid(row=fake_row, column=0, padx=4, pady=4)
            for j in range(cols):
                cell = ttk.Frame(self.input_frame, relief="solid", borderwidth=1, padding=4)
                cell.grid(row=fake_row, column=j + 1, padx=3, pady=3)
                entry = ttk.Entry(cell, width=8, justify="center")
                entry.insert(0, "0")
                entry.configure(state="disabled")
                entry.pack()
                ttk.Checkbutton(cell, text="Blokada", variable=self.fake_supplier_block_vars[j]).pack()

            cell = ttk.Frame(self.input_frame, relief="solid", borderwidth=1, padding=4)
            cell.grid(row=fake_row, column=cols + 1, padx=3, pady=3)
            entry = ttk.Entry(cell, width=8, justify="center")
            entry.insert(0, "0")
            entry.configure(state="disabled")
            entry.pack()
            ttk.Checkbutton(cell, text="Blokada", variable=self.fake_cross_block_var).pack()

            ttk.Entry(self.input_frame, width=10, justify="center", state="disabled").grid(
                row=fake_row, column=display_cols + 1, padx=4, pady=4
            )
            ttk.Entry(self.input_frame, width=18, justify="center", state="disabled").grid(
                row=fake_row, column=display_cols + 2, padx=4, pady=4
            )

        ttk.Label(self.input_frame, text="Popyt").grid(row=display_rows + 1, column=0, padx=4, pady=4)
        for j in range(cols):
            ttk.Entry(self.input_frame, width=10, justify="center", textvariable=self.demand_vars[j]).grid(
                row=display_rows + 1, column=j + 1, padx=4, pady=4
            )
        if show_fake_preview:
            ttk.Entry(self.input_frame, width=10, justify="center", state="disabled").grid(
                row=display_rows + 1, column=cols + 1, padx=4, pady=4
            )

        ttk.Label(self.input_frame, text="Cena sprzedazy u odbiorcy").grid(
            row=display_rows + 2, column=0, padx=4, pady=4
        )
        for j in range(cols):
            ttk.Entry(self.input_frame, width=10, justify="center", textvariable=self.sale_price_vars[j]).grid(
                row=display_rows + 2, column=j + 1, padx=4, pady=4
            )
        if show_fake_preview:
            ttk.Entry(self.input_frame, width=10, justify="center", state="disabled").grid(
                row=display_rows + 2, column=cols + 1, padx=4, pady=4
            )

        self.clear_results()

    def load_example(self):
        self.supplier_count.set(2)
        self.receiver_count.set(3)
        self.build_input_table()

        transport_costs = [
            [8, 14, 17],
            [12, 9, 19],
        ]
        supply = [20, 30]
        purchase_costs = [10, 12]
        demand = [10, 28, 27]
        sale_prices = [30, 25, 30]
        blocked = [
            [False, True, False],
            [False, False, False],
        ]

        self.fill_input_table(transport_costs, supply, demand, blocked, purchase_costs, sale_prices)

    def fill_input_table(self, transport_costs, supply, demand, blocked, purchase_costs, sale_prices):
        for i in range(len(supply)):
            self.supply_vars[i].set(str(supply[i]))
            self.purchase_cost_vars[i].set(str(purchase_costs[i]))
            for j in range(len(demand)):
                self.value_vars[i][j].set(str(transport_costs[i][j]))
                self.block_vars[i][j].set(blocked[i][j])

        for j in range(len(demand)):
            self.demand_vars[j].set(str(demand[j]))
            self.sale_price_vars[j].set(str(sale_prices[j]))

    def read_input_data(self):
        rows = self.supplier_count.get()
        cols = self.receiver_count.get()

        transport_costs = [
            [
                parse_number(
                    self.value_vars[i][j].get(),
                    f"koszt transportu {self.supplier_names[i]}-{self.receiver_names[j]}",
                )
                for j in range(cols)
            ]
            for i in range(rows)
        ]
        blocked = [
            [self.block_vars[i][j].get() for j in range(cols)]
            for i in range(rows)
        ]
        supply = [
            parse_number(self.supply_vars[i].get(), f"podaz {self.supplier_names[i]}")
            for i in range(rows)
        ]
        demand = [
            parse_number(self.demand_vars[j].get(), f"popyt {self.receiver_names[j]}")
            for j in range(cols)
        ]
        purchase_costs = [
            parse_number(self.purchase_cost_vars[i].get(), f"koszt zakupu {self.supplier_names[i]}")
            for i in range(rows)
        ]
        sale_prices = [
            parse_number(self.sale_price_vars[j].get(), f"cena sprzedazy {self.receiver_names[j]}")
            for j in range(cols)
        ]

        return (
            transport_costs,
            supply,
            demand,
            blocked,
            purchase_costs,
            sale_prices,
            self.supplier_names[:],
            self.receiver_names[:],
        )

    def read_data(self):
        (
            transport_costs,
            supply,
            demand,
            blocked,
            purchase_costs,
            sale_prices,
            suppliers,
            receivers,
        ) = self.read_input_data()
        transport_costs, supply, demand, blocked, purchase_costs, sale_prices, suppliers, receivers, _ = (
            self.balance_input_data(
                transport_costs,
                supply,
                demand,
                blocked,
                purchase_costs,
                sale_prices,
                suppliers,
                receivers,
            )
        )
        if len(suppliers) > MAX_SIZE or len(receivers) > MAX_SIZE:
            raise ValueError("Po zbilansowaniu tabela przekroczylaby limit 10 x 10.")
        values = calculate_unit_profits(transport_costs, purchase_costs, sale_prices, suppliers, receivers)

        return values, supply, demand, blocked, suppliers, receivers

    def balance_input_data(
        self,
        transport_costs,
        supply,
        demand,
        blocked,
        purchase_costs,
        sale_prices,
        suppliers,
        receivers,
    ):
        supply_sum = sum(supply)
        demand_sum = sum(demand)

        if abs(supply_sum - demand_sum) < EPS:
            return transport_costs, supply, demand, blocked, purchase_costs, sale_prices, suppliers, receivers, (
                "Problem byl juz zbilansowany."
            )

        fake_receiver_blocks = [
            var.get() for var in self.fake_receiver_block_vars[:len(suppliers)]
        ]
        fake_supplier_blocks = [
            var.get() for var in self.fake_supplier_block_vars[:len(receivers)]
        ]
        while len(fake_receiver_blocks) < len(suppliers):
            fake_receiver_blocks.append(False)
        while len(fake_supplier_blocks) < len(receivers):
            fake_supplier_blocks.append(False)

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

        return (
            transport_costs,
            supply,
            demand,
            blocked,
            purchase_costs,
            sale_prices,
            suppliers,
            receivers,
            "Dodano fikcyjnego dostawce FD i odbiorce FO.",
        )

    def clear_results(self):
        for widget in self.result_frame.winfo_children():
            widget.destroy()
        self.summary_text.set("Wprowadz dane i kliknij Oblicz.")

    def calculate(self):
        try:
            (
                transport_costs,
                supply,
                demand,
                blocked,
                purchase_costs,
                sale_prices,
                suppliers,
                receivers,
            ) = self.read_input_data()
            transport_costs, supply, demand, blocked, purchase_costs, sale_prices, suppliers, receivers, _ = (
                self.balance_input_data(
                    transport_costs,
                    supply,
                    demand,
                    blocked,
                    purchase_costs,
                    sale_prices,
                    suppliers,
                    receivers,
                )
            )
            if len(suppliers) > MAX_SIZE or len(receivers) > MAX_SIZE:
                raise ValueError("Po zbilansowaniu tabela przekroczylaby limit 10 x 10.")
            values = calculate_unit_profits(transport_costs, purchase_costs, sale_prices, suppliers, receivers)
            result = solve_max_element_method(values, supply, demand, blocked, suppliers, receivers)
            result["economic_summary"] = calculate_economic_summary(
                result["allocation"],
                transport_costs,
                purchase_costs,
                sale_prices,
                result["suppliers"],
                result["receivers"],
            )
        except ValueError as error:
            messagebox.showerror("Blad danych", str(error))
            return
        except Exception as error:
            messagebox.showerror("Blad", f"Wystapil nieoczekiwany blad:\n{error}")
            return

        self.show_result(result)

    def show_result(self, result):
        self.clear_results()
        self.summary_text.set(
            f"Zysk calkowity: {result['total']:.2f} | "
            f"Liczba iteracji: {len(result['iterations'])}"
        )

        ttk.Label(
            self.result_frame,
            text="Opis komorek: a = przydzial, z = zysk jednostkowy, X = brak przydzialu lub zablokowana trasa.",
            font=("TkDefaultFont", 10, "bold"),
        ).pack(anchor="w", pady=(0, 6))

        final_box = ttk.LabelFrame(self.result_frame, text="Tabela koncowa", padding=8)
        final_box.pack(fill="x", pady=5)
        self.draw_table(
            final_box,
            result,
            result["allocation"],
            [0.0] * len(result["suppliers"]),
            [0.0] * len(result["receivers"]),
            show_duals=True,
        )
        self.draw_economic_summary(result)

        for step in result["iterations"]:
            box = ttk.LabelFrame(self.result_frame, text=f"Iteracja {step['number']}", padding=8)
            box.pack(fill="x", pady=5)

            text = (
                f"Wybrano trase {result['suppliers'][step['row']]} -> "
                f"{result['receivers'][step['col']]}, "
                f"zysk jednostkowy = {step['value']}, przydzial = {step['amount']}."
            )
            ttk.Label(box, text=text).pack(anchor="w", pady=(0, 5))
            self.draw_table(
                box,
                result,
                step["allocation"],
                step["supply"],
                step["demand"],
                (step["row"], step["col"]),
            )

    def draw_economic_summary(self, result):
        summary = result.get("economic_summary")
        if summary is None:
            return

        box = ttk.LabelFrame(self.result_frame, text="Podsumowanie ekonomiczne", padding=8)
        box.pack(fill="x", pady=5)

        lines = [
            f"Przychod calkowity: {format_number(summary['revenue'])}",
            f"Koszt transportu: {format_number(summary['transport_cost'])}",
            f"Koszt zakupu: {format_number(summary['purchase_cost'])}",
        ]
        for line in lines:
            ttk.Label(box, text=line).pack(anchor="w")

    def draw_table(self, parent, result, allocation, supply, demand, selected=None, show_duals=False):
        table = ttk.Frame(parent)
        table.pack(anchor="w")
        supplier_potentials = []
        receiver_potentials = []
        if show_duals:
            supplier_potentials, receiver_potentials = calculate_dual_variables(result["values"], allocation)

        ttk.Label(table, text="").grid(row=0, column=0, padx=3, pady=3)
        for j, name in enumerate(result["receivers"]):
            ttk.Label(table, text=name).grid(row=0, column=j + 1, padx=3, pady=3)
        right_header = "alpha_i" if show_duals else "Pozostala podaz"
        ttk.Label(table, text=right_header).grid(row=0, column=len(result["receivers"]) + 1, padx=3, pady=3)

        for i, name in enumerate(result["suppliers"]):
            ttk.Label(table, text=name).grid(row=i + 1, column=0, padx=3, pady=3)
            for j in range(len(result["receivers"])):
                allocation_text = format_number(allocation[i][j]) if allocation[i][j] > EPS else "X"
                text = f"a={allocation_text}\nz={format_number(result['values'][i][j])}"

                if selected == (i, j):
                    color = "#bfe3b4"
                elif result["blocked"][i][j] and allocation[i][j] <= EPS:
                    text = f"X\nz={format_number(result['values'][i][j])}"
                    color = "#f3c7c7"
                else:
                    color = "#e3ddd5"

                tk.Label(
                    table,
                    text=text,
                    width=12,
                    height=3,
                    relief="solid",
                    bg=color,
                    fg="#1f1f1f",
                    font=("TkDefaultFont", 11),
                ).grid(row=i + 1, column=j + 1, padx=2, pady=2)

            right_value = (
                format_number(supplier_potentials[i])
                if show_duals and supplier_potentials[i] is not None
                else format_number(supply[i])
            )
            ttk.Label(table, text=right_value).grid(
                row=i + 1, column=len(result["receivers"]) + 1, padx=3, pady=3
            )

        bottom_row = len(result["suppliers"]) + 1
        bottom_label = "beta_j" if show_duals else "Pozostaly popyt"
        ttk.Label(table, text=bottom_label).grid(row=bottom_row, column=0, padx=3, pady=3)
        for j in range(len(result["receivers"])):
            bottom_value = (
                format_number(receiver_potentials[j])
                if show_duals and receiver_potentials[j] is not None
                else format_number(demand[j])
            )
            ttk.Label(table, text=bottom_value).grid(
                row=bottom_row, column=j + 1, padx=3, pady=3
            )


def main():
    root = tk.Tk()
    TransportApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
