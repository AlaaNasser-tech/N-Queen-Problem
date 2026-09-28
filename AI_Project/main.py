"""
N-Queens Solver — Professional GUI Application
===============================================
Framework : CustomTkinter (modern dark-themed widgets)
Charts    : Matplotlib embedded via FigureCanvasTkAgg
Threading : Background worker threads keep the UI responsive

Layout
------
  NQueensApp
  ├── Sidebar          (left, fixed 230 px)
  │   ├── Logo / title
  │   ├── Nav buttons  (Solve / Compare)
  │   └── Algorithm legend chips
  ├── Right panel
  │   ├── Header bar
  │   ├── SolvePage    ─ algorithm dropdown, N input, ChessboardCanvas, ResultPanel
  │   ├── ComparePage  ─ comparison table + 3 Matplotlib chart tabs
  │   └── StatusBar    (bottom, colour-coded feedback)
  └── (pages swapped via pack/pack_forget)

Algorithm files expected in the same directory:
  backtracking.py  →  solve(n)
  Bestfirst.py     →  best_first_search(n)
  genetic.py       →  solve(n)
  HillClimbing.py  →  NQueenHC(n).solve()  or  .HillClimbing()
"""

import time
import threading
import tkinter as tk

import customtkinter as ctk
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.ticker as mticker

# ──────────────────────────────────────────────────────────────────────────────
# Algorithm imports  (graceful fallback if files are missing)
# ──────────────────────────────────────────────────────────────────────────────
try:
    from backtracking import solve as backtracking_solve
    from Bestfirst import best_first_search
    from genetic import solve as genetic_solve
    from HillClimbing import NQueenHC
    _ALGO_OK  = True
    _ALGO_ERR = ""
except ImportError as _e:
    _ALGO_OK  = False
    _ALGO_ERR = str(_e)


# ──────────────────────────────────────────────────────────────────────────────
# Global theme / colour palette
# ──────────────────────────────────────────────────────────────────────────────
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

C = {
    # Backgrounds
    "bg":        "#0d0f18",
    "bg_card":   "#161929",
    "bg_side":   "#10121c",
    "bg_input":  "#0d0f18",
    "border":    "#252840",
    # Accent palette
    "accent":    "#7c6fe0",
    "accent2":   "#a78bfa",
    "accent3":   "#c4b5fd",
    # Semantic
    "success":   "#22c55e",
    "warning":   "#f59e0b",
    "danger":    "#ef4444",
    "info":      "#38bdf8",
    # Text
    "text":      "#f1f5f9",
    "muted":     "#64748b",
    "subtle":    "#94a3b8",
    # Chess squares
    "sq_light":  "#f0d9b5",
    "sq_dark":   "#b58863",
    # Queen
    "queen":     "#7c6fe0",
}

# Per-algorithm accent colours (used in charts and badges)
ALGO_COLORS = {
    "Backtracking":     "#7c6fe0",
    "Best First Search":"#06b6d4",
    "Genetic Algorithm":"#22c55e",
    "Hill Climbing":    "#f59e0b",
}


# ──────────────────────────────────────────────────────────────────────────────
# Algorithm wrappers & metadata
# ──────────────────────────────────────────────────────────────────────────────
def _run_hill_climbing(n):
    hc = NQueenHC(n)
    for method in ("solve", "HillClimbing"):
        fn = getattr(hc, method, None)
        if callable(fn):
            return fn()
    raise AttributeError("NQueenHC has no solve() or HillClimbing() method.")


ALGO_META = {
    "Backtracking": {
        "func":        lambda n: backtracking_solve(n),
        "complexity":  "O(N!)",
        "type":        "Systematic Search",
        "description": (
            "Explores all possibilities systematically using depth-first search "
            "with pruning. Guaranteed to find a solution if one exists, "
            "but becomes very slow for large N."
        ),
    },
    "Best First Search": {
        "func":        lambda n: best_first_search(n),
        "complexity":  "O(b^m)",
        "type":        "Heuristic Search",
        "description": (
            "Uses a conflict-based heuristic to prioritise the most promising "
            "paths in the search tree. Typically faster than pure backtracking "
            "because it avoids exploring high-conflict states."
        ),
    },
    "Genetic Algorithm": {
        "func":        lambda n: genetic_solve(n),
        "complexity":  "O(G × P × N²)",
        "type":        "Evolutionary Algorithm",
        "description": (
            "Simulates biological evolution: a population of candidate solutions "
            "evolves through crossover and mutation. Non-deterministic — results "
            "may vary between runs. Scales well for larger N."
        ),
    },
    "Hill Climbing": {
        "func":        lambda n: _run_hill_climbing(n),
        "complexity":  "O(Attempts × N²)",
        "type":        "Local Search",
        "description": (
            "Iteratively moves to a neighbouring state with fewer conflicts. "
            "Uses random restarts to escape local optima. Fast per iteration "
            "but not guaranteed to find the global optimum."
        ),
    },
}

ALGO_NAMES = list(ALGO_META.keys())


# ──────────────────────────────────────────────────────────────────────────────
# Pure helper functions
# ──────────────────────────────────────────────────────────────────────────────
def is_valid_solution(result, n: int) -> bool:
    if result is None or not isinstance(result, (list, tuple)):
        return False
    if len(result) != n:
        return False
    if not all(isinstance(x, int) for x in result):
        return False
    if not all(0 <= x < n for x in result):
        return False

    for i in range(n):
        for j in range(i + 1, n):
            if result[i] == result[j]:
                return False
            if abs(result[i] - result[j]) == abs(i - j):
                return False
    return True


def normalize_result(raw, n: int):
    if raw is None:
        return None

    # Case 1: plain list/tuple of columns
    if isinstance(raw, (list, tuple)):
        # A) already integer columns
        if len(raw) == n and all(isinstance(x, int) for x in raw):
            vals = list(raw)

            # zero-based: 0..n-1
            if all(0 <= x < n for x in vals):
                return vals

            # one-based: 1..n  -> convert to zero-based
            if all(1 <= x <= n for x in vals):
                return [x - 1 for x in vals]

            return None

        # B) board matrix NxN with one queen per row
        if len(raw) == n and all(isinstance(row, (list, tuple)) and len(row) == n for row in raw):
            cols = []
            for row in raw:
                queen_cols = [i for i, v in enumerate(row) if v in (1, True, "Q", "q", "♛")]
                if len(queen_cols) != 1:
                    return None
                cols.append(queen_cols[0])
            return cols

        # C) list of coordinates [(r,c), ...]
        if all(isinstance(p, (list, tuple)) and len(p) == 2 for p in raw):
            cols = [None] * n
            for r, c in raw:
                r, c = int(r), int(c)
                if not (0 <= r < n and 0 <= c < n):
                    return None
                cols[r] = c
            return cols if all(v is not None for v in cols) else None

    return None


def validate_n(value: str):
    if not value.strip():
        return None, "Please enter a value for N."
    try:
        n = int(value.strip())
    except ValueError:
        return None, "N must be a whole number (e.g. 8)."
    if n < 1:
        return None, "N must be at least 1."
    if n in (2, 3):
        return None, "No solution exists for N = 2 or N = 3."
    if n > 30:
        return None, "N > 30 may take a very long time. Please use N ≤ 30."
    return n, None


def measure_algorithm(algo_name: str, n: int, runs: int = 3) -> dict:
    func = ALGO_META[algo_name]["func"]
    times, successes = [], 0
    first_valid_result = None

    for _ in range(runs):
        t0 = time.perf_counter()
        try:
            raw = func(n) if _ALGO_OK else None
        except Exception:
            raw = None
        t1 = time.perf_counter()

        times.append(t1 - t0)
        norm = normalize_result(raw, n)

        if is_valid_solution(norm, n):
            successes += 1
            if first_valid_result is None:
                first_valid_result = norm

    return {
        "avg_time": sum(times) / len(times),
        "min_time": min(times),
        "max_time": max(times),
        "success": successes,
        "result": first_valid_result,   # بدل last_result
    }


def fmt_time(seconds: float) -> str:
    """Human-readable time string."""
    if seconds < 1e-3:
        return f"{seconds * 1e6:.1f} µs"
    if seconds < 1:
        return f"{seconds * 1e3:.3f} ms"
    return f"{seconds:.4f} s"


# ══════════════════════════════════════════════════════════════════════════════
# ChessboardCanvas
# ══════════════════════════════════════════════════════════════════════════════
class ChessboardCanvas(tk.Canvas):
    """
    Resizable tk.Canvas that renders an N×N chessboard.
    Call set_solution(result_list, n) to draw queens.
    Call clear() to reset to an empty board.
    """

    def __init__(self, parent, **kwargs):
        super().__init__(
            parent,
            bg=C["bg_card"],
            highlightthickness=0,
            **kwargs,
        )
        self._n = 8
        self._solution = None
        self.bind("<Configure>", lambda e: self._redraw())

    def set_solution(self, solution, n: int):
        self._n = n
        self._solution = solution
        self._redraw()

    def clear(self):
        self._n = 8
        self._solution = None
        self._redraw()

    def _cell_size(self) -> int:
        canvas_w = self.winfo_width() or 400
        canvas_h = self.winfo_height() or 400
        return max(1, min(canvas_w, canvas_h) // self._n)

    def _draw_queen(self, cx, cy, cs):
        """
        Draw a stylized queen using only valid tkinter colors.
        No alpha colors, no text glyphs.
        """
        size = cs * 0.60

        left = cx - size * 0.22
        right = cx + size * 0.22
        top = cy - size * 0.28
        mid = cy - size * 0.05
        bottom = cy + size * 0.26

        # Shadow (solid color only)
        self.create_oval(
            left + 3, bottom - 2,
            right + 3, bottom + size * 0.10,
            fill="#2a2238",
            outline=""
        )

        # Base
        self.create_oval(
            left, bottom - size * 0.05,
            right, bottom + size * 0.12,
            fill=C["accent2"],
            outline=C["border"],
            width=1
        )

        # Body
        self.create_polygon(
            cx - size * 0.18, mid + size * 0.14,
            cx - size * 0.14, mid - size * 0.02,
            cx - size * 0.10, mid - size * 0.18,
            cx,               mid - size * 0.08,
            cx + size * 0.10, mid - size * 0.18,
            cx + size * 0.14, mid - size * 0.02,
            cx + size * 0.18, mid + size * 0.14,
            fill=C["queen"],
            outline=C["border"],
            width=1,
            smooth=True
        )

        # Crown
        self.create_polygon(
            cx - size * 0.22, mid - size * 0.02,
            cx - size * 0.16, top + size * 0.12,
            cx - size * 0.08, mid + size * 0.02,
            cx,               top,
            cx + size * 0.08, mid + size * 0.02,
            cx + size * 0.16, top + size * 0.12,
            cx + size * 0.22, mid - size * 0.02,
            fill=C["queen"],
            outline=C["border"],
            width=1,
            smooth=True
        )

        # Jewels
        jewel_y = top + size * 0.04
        for dx in (-size * 0.14, 0, size * 0.14):
            self.create_oval(
                cx + dx - size * 0.03, jewel_y - size * 0.03,
                cx + dx + size * 0.03, jewel_y + size * 0.03,
                fill=C["accent3"],
                outline=""
            )

        # Top gem
        self.create_oval(
            cx - size * 0.03, top - size * 0.03,
            cx + size * 0.03, top + size * 0.03,
            fill=C["accent3"],
            outline=""
        )

    def _redraw(self):
        self.delete("all")
        n = self._n
        cs = self._cell_size()
        board_px = n * cs

        # Squares
        for row in range(n):
            for col in range(n):
                fill = C["sq_light"] if (row + col) % 2 == 0 else C["sq_dark"]
                self.create_rectangle(
                    col * cs, row * cs,
                    col * cs + cs, row * cs + cs,
                    fill=fill, outline=""
                )

        # Queens
        if self._solution:
            for row, col in enumerate(self._solution):
                if not (0 <= col < n):
                    continue

                cx = col * cs + cs // 2
                cy = row * cs + cs // 2
                self._draw_queen(cx, cy, cs)

        # Border
        self.create_rectangle(
            0, 0, board_px, board_px,
            outline=C["border"], width=2
        )
# ══════════════════════════════════════════════════════════════════════════════
# ResultPanel
# ══════════════════════════════════════════════════════════════════════════════
class ResultPanel(ctk.CTkScrollableFrame):
    """
    Right-hand card showing algorithm stats, description,
    and the raw solution array.
    """

    _STATS = [
        ("algorithm",  "Algorithm"),
        ("time",       "Avg Time"),
        ("success",    "Success"),
        ("complexity", "Complexity"),
        ("algo_type",  "Type"),
    ]

    def __init__(self, parent, **kwargs):
        super().__init__(parent, fg_color=C["bg_card"], corner_radius=14, **kwargs)
        self._stat_vals: dict[str, ctk.CTkLabel] = {}
        self._build()

    # ── Build ─────────────────────────────────────────────────────────────
    def _build(self):
        # Title
        ctk.CTkLabel(
            self,
            text="Result Details",
            font=ctk.CTkFont("Segoe UI", 16, "bold"),
            text_color=C["text"],
        ).pack(anchor="w", padx=20, pady=(16, 12))

        # Stat chips (2-column grid)
        grid = ctk.CTkFrame(self, fg_color="transparent")
        grid.pack(fill="x", padx=16, pady=(0, 4))
        grid.columnconfigure((0, 1), weight=1)

        for idx, (key, label) in enumerate(self._STATS):
            chip = ctk.CTkFrame(grid, fg_color=C["bg_input"], corner_radius=10)
            chip.grid(row=idx // 2, column=idx % 2, padx=4, pady=4, sticky="ew")

            ctk.CTkLabel(
                chip, text=label,
                font=ctk.CTkFont("Segoe UI", 10),
                text_color=C["muted"],
            ).pack(anchor="w", padx=12, pady=(8, 0))

            val = ctk.CTkLabel(
                chip, text="—",
                font=ctk.CTkFont("Segoe UI", 13, "bold"),
                text_color=C["text"],
            )
            val.pack(anchor="w", padx=12, pady=(2, 8))
            self._stat_vals[key] = val

        # Validity badge row
        self._badge = ctk.CTkLabel(
            self, text="",
            font=ctk.CTkFont("Segoe UI", 13, "bold"),
            text_color=C["success"],
        )
        self._badge.pack(anchor="w", padx=20, pady=(8, 0))

        # Divider
        ctk.CTkFrame(self, fg_color=C["border"], height=1).pack(fill="x", padx=16, pady=12)

        # Description
        ctk.CTkLabel(
            self, text="About this algorithm",
            font=ctk.CTkFont("Segoe UI", 12, "bold"),
            text_color=C["subtle"],
        ).pack(anchor="w", padx=20)

        self._desc = ctk.CTkLabel(
            self,
            text="Run an algorithm to see details here.",
            font=ctk.CTkFont("Segoe UI", 12),
            text_color=C["text"],
            wraplength=310,
            justify="left",
        )
        self._desc.pack(anchor="w", padx=20, pady=(4, 12))

        # Raw result
        ctk.CTkLabel(
            self, text="Solution Array",
            font=ctk.CTkFont("Segoe UI", 12, "bold"),
            text_color=C["subtle"],
        ).pack(anchor="w", padx=20)

        self._raw = ctk.CTkTextbox(
            self, height=64,
            font=ctk.CTkFont("Courier New", 12),
            fg_color=C["bg_input"],
            text_color=C["accent2"],
            border_color=C["border"],
            border_width=1,
            state="disabled",
        )
        self._raw.pack(fill="x", padx=16, pady=(4, 16))

    # ── Public API ────────────────────────────────────────────────────────
    def update_results(self, algo_name: str, stats: dict, runs: int):
        meta = ALGO_META[algo_name]

        # Colour-code success
        suc = stats["success"]
        suc_color = (C["success"] if suc == runs
                     else C["warning"] if suc > 0
                     else C["danger"])

        self._stat_vals["algorithm"].configure(text=algo_name)
        self._stat_vals["time"].configure(text=fmt_time(stats["avg_time"]))
        self._stat_vals["success"].configure(
            text=f"{suc}/{runs} runs", text_color=suc_color)
        self._stat_vals["complexity"].configure(text=meta["complexity"])
        self._stat_vals["algo_type"].configure(text=meta["type"])

        # Validity badge
        if stats["result"]:
            valid = is_valid_solution(stats["result"], len(stats["result"]))
            if valid:
                self._badge.configure(text="✓  Valid solution", text_color=C["success"])
            else:
                self._badge.configure(text="⚠  Solution returned but invalid", text_color=C["warning"])
        else:
            self._badge.configure(text="✗  No solution found", text_color=C["danger"])

        self._desc.configure(text=meta["description"])

        # Raw array
        self._raw.configure(state="normal")
        self._raw.delete("1.0", "end")
        self._raw.insert("1.0", str(stats["result"]) if stats["result"] else "None")
        self._raw.configure(state="disabled")

    def reset(self):
        for lbl in self._stat_vals.values():
            lbl.configure(text="—", text_color=C["text"])
        self._badge.configure(text="")
        self._desc.configure(text="Run an algorithm to see details here.")
        self._raw.configure(state="normal")
        self._raw.delete("1.0", "end")
        self._raw.configure(state="disabled")


# ══════════════════════════════════════════════════════════════════════════════
# SolvePage
# ══════════════════════════════════════════════════════════════════════════════
class SolvePage(ctk.CTkFrame):
    """
    Main solving page:
      - Top controls bar (algorithm, N, runs, buttons)
      - Left: ChessboardCanvas + algorithm badge
      - Right: ResultPanel
    """

    def __init__(self, parent, status_fn, **kwargs):
        super().__init__(parent, fg_color=C["bg"], corner_radius=0, **kwargs)
        self._status = status_fn
        self._build()

    # ── Build ─────────────────────────────────────────────────────────────
    def _build(self):
        self._build_controls()
        self._build_content()

    def _build_controls(self):
        card = ctk.CTkFrame(self, fg_color=C["bg_card"], corner_radius=14)
        card.pack(fill="x", padx=20, pady=(20, 10))

        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x", padx=20, pady=16)
        row.columnconfigure((0, 1, 2), weight=0)
        row.columnconfigure(3, weight=1)

        # Algorithm
        col = ctk.CTkFrame(row, fg_color="transparent")
        col.grid(row=0, column=0, padx=(0, 20), sticky="w")
        ctk.CTkLabel(col, text="Algorithm", font=ctk.CTkFont("Segoe UI", 11),
                     text_color=C["muted"]).pack(anchor="w")
        self._algo_var = ctk.StringVar(value=ALGO_NAMES[0])
        ctk.CTkOptionMenu(
            col,
            variable=self._algo_var,
            values=ALGO_NAMES,
            font=ctk.CTkFont("Segoe UI", 13),
            fg_color=C["bg_input"],
            button_color=C["accent"],
            button_hover_color=C["accent2"],
            dropdown_fg_color=C["bg_card"],
            width=230,
            command=self._on_algo_change,
        ).pack(anchor="w", pady=(4, 0))

        # N queens
        col2 = ctk.CTkFrame(row, fg_color="transparent")
        col2.grid(row=0, column=1, padx=(0, 20), sticky="w")
        ctk.CTkLabel(col2, text="N  (queens)", font=ctk.CTkFont("Segoe UI", 11),
                     text_color=C["muted"]).pack(anchor="w")
        self._n_entry = ctk.CTkEntry(
            col2,
            placeholder_text="e.g. 8",
            font=ctk.CTkFont("Segoe UI", 14),
            fg_color=C["bg_input"],
            border_color=C["border"],
            border_width=1,
            width=110,
        )
        self._n_entry.insert(0, "8")
        self._n_entry.pack(anchor="w", pady=(4, 0))

        # Runs
        col3 = ctk.CTkFrame(row, fg_color="transparent")
        col3.grid(row=0, column=2, padx=(0, 20), sticky="w")
        ctk.CTkLabel(col3, text="Runs", font=ctk.CTkFont("Segoe UI", 11),
                     text_color=C["muted"]).pack(anchor="w")
        self._runs_var = ctk.StringVar(value="3")
        ctk.CTkOptionMenu(
            col3,
            variable=self._runs_var,
            values=["1", "3", "5"],
            font=ctk.CTkFont("Segoe UI", 13),
            fg_color=C["bg_input"],
            button_color=C["accent"],
            button_hover_color=C["accent2"],
            dropdown_fg_color=C["bg_card"],
            width=80,
        ).pack(anchor="w", pady=(4, 0))

        # Buttons (right-aligned)
        btn_frame = ctk.CTkFrame(row, fg_color="transparent")
        btn_frame.grid(row=0, column=3, sticky="e")

        self._solve_btn = ctk.CTkButton(
            btn_frame, text="▶  Solve",
            font=ctk.CTkFont("Segoe UI", 14, "bold"),
            fg_color=C["accent"], hover_color=C["accent2"],
            corner_radius=10, width=130, height=42,
            command=self._on_solve,
        )
        self._solve_btn.pack(side="left", padx=(0, 10))

        ctk.CTkButton(
            btn_frame, text="Clear",
            font=ctk.CTkFont("Segoe UI", 13),
            fg_color="transparent",
            hover_color=C["border"],
            border_color=C["border"],
            border_width=1,
            corner_radius=10,
            width=90, height=42,
            command=self._on_clear,
        ).pack(side="left")

    def _build_content(self):
        area = ctk.CTkFrame(self, fg_color="transparent")
        area.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        area.columnconfigure(0, weight=3)
        area.columnconfigure(1, weight=2)
        area.rowconfigure(0, weight=1)

        # ── Board card ────────────────────────────────────────────────────
        board_card = ctk.CTkFrame(area, fg_color=C["bg_card"], corner_radius=14)
        board_card.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        board_card.rowconfigure(1, weight=1)
        board_card.columnconfigure(0, weight=1)

        ctk.CTkLabel(
            board_card, text="Chessboard",
            font=ctk.CTkFont("Segoe UI", 15, "bold"),
            text_color=C["text"],
        ).grid(row=0, column=0, sticky="w", padx=20, pady=(16, 6))

        board_wrapper = ctk.CTkFrame(board_card, fg_color="transparent")
        board_wrapper.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 8))

        self._board = ChessboardCanvas(board_wrapper)
        self._board.pack(fill="both", expand=True)

        # Algorithm badge (below board)
        badge = ctk.CTkFrame(board_card, fg_color=C["bg_input"], corner_radius=8)
        badge.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 16))

        self._badge_dot = ctk.CTkLabel(
            badge, text="●",
            font=ctk.CTkFont("Segoe UI", 12),
            text_color=ALGO_COLORS[ALGO_NAMES[0]],
        )
        self._badge_dot.pack(side="left", padx=(12, 6), pady=10)

        self._badge_lbl = ctk.CTkLabel(
            badge,
            text=self._badge_text(ALGO_NAMES[0]),
            font=ctk.CTkFont("Segoe UI", 12),
            text_color=C["subtle"],
        )
        self._badge_lbl.pack(side="left", pady=10)

        # ── Result panel ─────────────────────────────────────────────────
        self._result_panel = ResultPanel(area)
        self._result_panel.grid(row=0, column=1, sticky="nsew")

    # ── Helpers ───────────────────────────────────────────────────────────
    @staticmethod
    def _badge_text(algo_name: str) -> str:
        meta = ALGO_META[algo_name]
        return f"{algo_name}  ·  {meta['complexity']}  ·  {meta['type']}"

    def _on_algo_change(self, name: str):
        self._badge_dot.configure(text_color=ALGO_COLORS.get(name, C["accent"]))
        self._badge_lbl.configure(text=self._badge_text(name))

    # ── Event handlers ────────────────────────────────────────────────────
    def _on_solve(self):
        n, err = validate_n(self._n_entry.get())
        if err:
            self._status(err, "error")
            return
        if not _ALGO_OK:
            self._status(f"Import error: {_ALGO_ERR}", "error")
            return

        algo = self._algo_var.get()
        runs = int(self._runs_var.get())

        self._solve_btn.configure(state="disabled", text="⏳  Solving…")
        self._status(f"Running {algo} for N = {n}…", "info")

        def _worker():
            try:
                stats = measure_algorithm(algo, n, runs)
            except Exception as ex:
                self.after(0, lambda: self._finish(None, None, algo, runs, str(ex)))
            else:
                self.after(0, lambda: self._finish(stats, n, algo, runs, None))

        threading.Thread(target=_worker, daemon=True).start()

    def _finish(self, stats, n, algo, runs, error):
        self._solve_btn.configure(state="normal", text="▶  Solve")

        if error:
            self._status(f"Error: {error}", "error")
            return

        self._result_panel.update_results(algo, stats, runs)

        if stats["result"] is not None and is_valid_solution(stats["result"], n):
            self._board.set_solution(stats["result"], n)
            self._status(
                f"{algo}  ·  N={n}  ·  {fmt_time(stats['avg_time'])}  ·  ✓ Valid",
                "success",
            )
        else:
            self._board.clear()
            self._status(f"{algo}: No valid solution for N = {n}.", "warning")

    def _on_clear(self):
        self._board.clear()
        self._result_panel.reset()
        self._n_entry.delete(0, "end")
        self._n_entry.insert(0, "8")
        self._status("Cleared.", "info")


# ══════════════════════════════════════════════════════════════════════════════
# ComparePage
# ══════════════════════════════════════════════════════════════════════════════
class ComparePage(ctk.CTkFrame):
    """
    Runs all four algorithms and displays:
      - A comparison table (tab 1)
      - Execution-time bar chart (tab 2)
      - Success-rate bar chart (tab 3)
      - Efficiency pie chart (tab 4)
    """

    def __init__(self, parent, status_fn, **kwargs):
        super().__init__(parent, fg_color=C["bg"], corner_radius=0, **kwargs)
        self._status = status_fn
        self._data: dict = {}
        self._build()

    # ── Build ─────────────────────────────────────────────────────────────
    def _build(self):
        self._build_controls()
        self._build_tabs()

    def _build_controls(self):
        card = ctk.CTkFrame(self, fg_color=C["bg_card"], corner_radius=14)
        card.pack(fill="x", padx=20, pady=(20, 10))

        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x", padx=20, pady=16)

        # N input
        ctk.CTkLabel(row, text="N (queens):",
                     font=ctk.CTkFont("Segoe UI", 13),
                     text_color=C["muted"]).pack(side="left", padx=(0, 8))
        self._n_entry = ctk.CTkEntry(
            row, placeholder_text="e.g. 8",
            font=ctk.CTkFont("Segoe UI", 13),
            fg_color=C["bg_input"], border_color=C["border"],
            border_width=1, width=100,
        )
        self._n_entry.insert(0, "8")
        self._n_entry.pack(side="left", padx=(0, 20))

        # Runs
        ctk.CTkLabel(row, text="Runs per algorithm:",
                     font=ctk.CTkFont("Segoe UI", 13),
                     text_color=C["muted"]).pack(side="left", padx=(0, 8))
        self._runs_var = ctk.StringVar(value="3")
        ctk.CTkOptionMenu(
            row,
            variable=self._runs_var,
            values=["1", "3", "5"],
            font=ctk.CTkFont("Segoe UI", 13),
            fg_color=C["bg_input"],
            button_color=C["accent"],
            button_hover_color=C["accent2"],
            dropdown_fg_color=C["bg_card"],
            width=80,
        ).pack(side="left", padx=(0, 24))

        # Buttons
        self._cmp_btn = ctk.CTkButton(
            row, text="⚡  Compare All",
            font=ctk.CTkFont("Segoe UI", 14, "bold"),
            fg_color=C["accent"], hover_color=C["accent2"],
            corner_radius=10, width=160, height=40,
            command=self._on_compare,
        )
        self._cmp_btn.pack(side="left", padx=(0, 10))

        ctk.CTkButton(
            row, text="Reset",
            font=ctk.CTkFont("Segoe UI", 13),
            fg_color="transparent",
            hover_color=C["border"],
            border_color=C["border"],
            border_width=1,
            corner_radius=10,
            width=90, height=40,
            command=self._on_reset,
        ).pack(side="left")

    def _build_tabs(self):
        self._tab = ctk.CTkTabview(
            self,
            fg_color=C["bg_card"],
            segmented_button_fg_color=C["bg_input"],
            segmented_button_selected_color=C["accent"],
            segmented_button_selected_hover_color=C["accent2"],
            corner_radius=14,
        )
        self._tab.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        for name in ("📋  Table", "⏱  Time", "✅  Success", "🥧  Efficiency"):
            self._tab.add(name)

        # Table tab — has a dedicated scrollable build
        self._table_host = ctk.CTkScrollableFrame(
            self._tab.tab("📋  Table"), fg_color="transparent"
        )
        self._table_host.pack(fill="both", expand=True, padx=8, pady=8)
        self._show_placeholder(self._table_host)

    # ── Table rendering ───────────────────────────────────────────────────
    def _show_placeholder(self, host):
        for w in host.winfo_children():
            w.destroy()
        ctk.CTkLabel(
            host,
            text="Run a comparison to see results.",
            font=ctk.CTkFont("Segoe UI", 14),
            text_color=C["muted"],
        ).pack(pady=60)

    def _render_table(self, data: dict, runs: int):
        host = self._table_host
        for w in host.winfo_children():
            w.destroy()

        headers = ["Algorithm", "Avg Time", "Min", "Max", "Success", "Complexity", "Type"]
        widths   = [200, 110, 100, 100, 90, 120, 160]

        # Header row
        hdr = ctk.CTkFrame(host, fg_color=C["bg_input"], corner_radius=8)
        hdr.pack(fill="x", pady=(0, 6))
        for h, w in zip(headers, widths):
            ctk.CTkLabel(
                hdr, text=h,
                font=ctk.CTkFont("Segoe UI", 11, "bold"),
                text_color=C["accent2"],
                width=w, anchor="w",
            ).pack(side="left", padx=8, pady=8)

        best_time = min(d["avg_time"] for d in data.values())

        for algo, d in data.items():
            is_best = abs(d["avg_time"] - best_time) < 1e-12
            row_bg  = "#1a2e1a" if is_best else C["bg_card"]
            row = ctk.CTkFrame(host, fg_color=row_bg, corner_radius=8)
            row.pack(fill="x", pady=2)

            suc = d["success"]
            suc_col = (C["success"] if suc == runs
                       else C["warning"] if suc > 0
                       else C["danger"])

            cells = [
                (algo,                  widths[0], C["text"]),
                (fmt_time(d["avg_time"]), widths[1],
                 C["accent"] if is_best else C["text"]),
                (fmt_time(d["min_time"]), widths[2], C["subtle"]),
                (fmt_time(d["max_time"]), widths[3], C["subtle"]),
                (f"{suc}/{runs}",         widths[4], suc_col),
                (ALGO_META[algo]["complexity"], widths[5], C["muted"]),
                (ALGO_META[algo]["type"],       widths[6], C["muted"]),
            ]
            for text, w, color in cells:
                ctk.CTkLabel(
                    row, text=text,
                    font=ctk.CTkFont("Segoe UI", 12),
                    text_color=color,
                    width=w, anchor="w",
                ).pack(side="left", padx=8, pady=10)

            if is_best:
                ctk.CTkLabel(
                    row, text="⭐ FASTEST",
                    font=ctk.CTkFont("Segoe UI", 11, "bold"),
                    text_color=C["success"],
                ).pack(side="left", padx=(0, 10), pady=10)

        # Summary bar
        best_algo = min(data, key=lambda a: data[a]["avg_time"])
        summary = ctk.CTkFrame(host, fg_color=C["bg_input"], corner_radius=10)
        summary.pack(fill="x", pady=(12, 4))
        ctk.CTkLabel(
            summary,
            text=(
                f"🏆  Best: {best_algo}  ·  "
                f"Avg {fmt_time(data[best_algo]['avg_time'])}  ·  "
                f"Success {data[best_algo]['success']}/{runs}"
            ),
            font=ctk.CTkFont("Segoe UI", 13, "bold"),
            text_color=C["success"],
        ).pack(padx=20, pady=12)

    # ── Chart rendering ───────────────────────────────────────────────────
    def _embed(self, tab_name: str, fig: Figure):
        tab = self._tab.tab(tab_name)
        for w in tab.winfo_children():
            w.destroy()
        canvas = FigureCanvasTkAgg(fig, master=tab)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)

    def _build_charts(self, data: dict, runs: int):
        algos      = list(data.keys())
        avg_times  = [data[a]["avg_time"] * 1000 for a in algos]   # ms
        successes  = [data[a]["success"]          for a in algos]
        efficiency = [1.0 / (data[a]["avg_time"] + 1e-9) for a in algos]
        colors     = [ALGO_COLORS[a]              for a in algos]

        bg_fig  = C["bg_card"]
        bg_axes = C["bg_input"]

        # ── Time bar chart ────────────────────────────────────────────────
        fig1 = Figure(figsize=(8, 4.5), facecolor=bg_fig)
        ax1  = fig1.add_subplot(111, facecolor=bg_axes)
        bars = ax1.bar(algos, avg_times, color=colors, width=0.5, zorder=3,
                       edgecolor=bg_fig, linewidth=1.5)
        ax1.set_title("Average Execution Time", color=C["text"],
                      fontsize=14, pad=12, fontweight="bold")
        ax1.set_ylabel("Time (ms)", color=C["muted"], fontsize=11)
        ax1.tick_params(colors=C["subtle"], labelsize=10)
        for spine in ax1.spines.values():
            spine.set_color(C["border"])
        ax1.yaxis.grid(True, color=C["border"], linestyle="--", alpha=0.5, zorder=0)
        ax1.set_axisbelow(True)
        for bar, val in zip(bars, avg_times):
            ax1.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + max(avg_times, default=1) * 0.02,
                f"{val:.2f} ms", ha="center", va="bottom",
                color=C["text"], fontsize=10, fontweight="bold",
            )
        fig1.tight_layout(pad=1.5)
        self._embed("⏱  Time", fig1)

        # ── Success bar chart ─────────────────────────────────────────────
        fig2 = Figure(figsize=(8, 4.5), facecolor=bg_fig)
        ax2  = fig2.add_subplot(111, facecolor=bg_axes)
        bars2 = ax2.bar(algos, successes, color=colors, width=0.5, zorder=3,
                        edgecolor=bg_fig, linewidth=1.5)
        ax2.set_title(f"Success Runs (out of {runs})", color=C["text"],
                      fontsize=14, pad=12, fontweight="bold")
        ax2.set_ylabel("Successful Runs", color=C["muted"], fontsize=11)
        ax2.set_ylim(0, runs + 0.8)
        ax2.yaxis.set_major_locator(mticker.MaxNLocator(integer=True))
        ax2.tick_params(colors=C["subtle"], labelsize=10)
        for spine in ax2.spines.values():
            spine.set_color(C["border"])
        ax2.yaxis.grid(True, color=C["border"], linestyle="--", alpha=0.5, zorder=0)
        ax2.set_axisbelow(True)
        for bar, val in zip(bars2, successes):
            ax2.text(
                bar.get_x() + bar.get_width() / 2, val + 0.06,
                str(val), ha="center", va="bottom",
                color=C["text"], fontsize=12, fontweight="bold",
            )
        fig2.tight_layout(pad=1.5)
        self._embed("✅  Success", fig2)

        # ── Efficiency pie chart ──────────────────────────────────────────
        fig3 = Figure(figsize=(7, 5), facecolor=bg_fig)
        ax3  = fig3.add_subplot(111, facecolor=bg_fig)
        wedges, texts, autotexts = ax3.pie(
            efficiency, labels=algos, autopct="%1.1f%%",
            colors=colors, startangle=140,
            wedgeprops=dict(edgecolor=bg_fig, linewidth=2.5),
            textprops=dict(color=C["text"]),
        )
        for at in autotexts:
            at.set_color(C["bg"])
            at.set_fontweight("bold")
            at.set_fontsize(10)
        ax3.set_title("Efficiency Distribution  (1 / avg_time)",
                      color=C["text"], fontsize=14, pad=12, fontweight="bold")
        fig3.tight_layout(pad=1.5)
        self._embed("🥧  Efficiency", fig3)

    # ── Event handlers ────────────────────────────────────────────────────
    def _on_compare(self):
        n, err = validate_n(self._n_entry.get())
        if err:
            self._status(err, "error")
            return
        if not _ALGO_OK:
            self._status(f"Import error: {_ALGO_ERR}", "error")
            return

        runs = int(self._runs_var.get())
        self._cmp_btn.configure(state="disabled", text="⏳  Running…")
        self._status(f"Comparing all algorithms for N = {n}…", "info")
        self._show_placeholder(self._table_host)

        def _worker():
            results = {}
            for algo in ALGO_NAMES:
                try:
                    results[algo] = measure_algorithm(algo, n, runs)
                except Exception:
                    results[algo] = {
                        "avg_time": 0.0, "min_time": 0.0, "max_time": 0.0,
                        "success": 0, "result": None,
                    }
            self.after(0, lambda: self._finish(results, n, runs))

        threading.Thread(target=_worker, daemon=True).start()

    def _finish(self, data: dict, n: int, runs: int):
        self._cmp_btn.configure(state="normal", text="⚡  Compare All")
        self._data = data
        self._render_table(data, runs)
        self._build_charts(data, runs)
        best = min(data, key=lambda a: data[a]["avg_time"])
        self._status(
            f"Done — N={n}  ·  🏆 Fastest: {best} ({fmt_time(data[best]['avg_time'])})",
            "success",
        )

    def _on_reset(self):
        self._data = {}
        self._show_placeholder(self._table_host)
        for tab_name in ("⏱  Time", "✅  Success", "🥧  Efficiency"):
            for w in self._tab.tab(tab_name).winfo_children():
                w.destroy()
        self._n_entry.delete(0, "end")
        self._n_entry.insert(0, "8")
        self._status("Reset.", "info")


# ══════════════════════════════════════════════════════════════════════════════
# Sidebar
# ══════════════════════════════════════════════════════════════════════════════
class Sidebar(ctk.CTkFrame):
    """
    Left navigation panel.
    Calls on_navigate("solve" | "compare") when a nav button is clicked.
    """

    _NAV = [
        ("solve",   "🧩", "Solve",   "Single algorithm run"),
        ("compare", "📊", "Compare", "All algorithms side-by-side"),
    ]

    def __init__(self, parent, on_navigate, **kwargs):
        super().__init__(
            parent,
            fg_color=C["bg_side"],
            corner_radius=0,
            width=230,
            **kwargs,
        )
        self.pack_propagate(False)
        self._on_navigate = on_navigate
        self._active      = "solve"
        self._nav_frames: dict[str, ctk.CTkFrame] = {}
        self._build()

    def _build(self):
        # ── Logo ──────────────────────────────────────────────────────────
        logo = ctk.CTkFrame(self, fg_color="transparent")
        logo.pack(fill="x", padx=20, pady=(28, 24))

        ctk.CTkLabel(
            logo, text="♛",
            font=ctk.CTkFont("Segoe UI", 36),
            text_color=C["accent"],
        ).pack(side="left", padx=(0, 12))

        titles = ctk.CTkFrame(logo, fg_color="transparent")
        titles.pack(side="left")
        ctk.CTkLabel(
            titles, text="N-Queens",
            font=ctk.CTkFont("Segoe UI", 18, "bold"),
            text_color=C["text"],
        ).pack(anchor="w")
        ctk.CTkLabel(
            titles, text="Solver & Analyzer",
            font=ctk.CTkFont("Segoe UI", 10),
            text_color=C["muted"],
        ).pack(anchor="w")

        # Divider
        ctk.CTkFrame(self, fg_color=C["border"], height=1).pack(fill="x", padx=16, pady=(0, 12))

        # ── Nav buttons ───────────────────────────────────────────────────
        ctk.CTkLabel(
            self, text="NAVIGATION",
            font=ctk.CTkFont("Segoe UI", 9, "bold"),
            text_color=C["muted"],
        ).pack(anchor="w", padx=20, pady=(4, 6))

        for key, icon, label, sub in self._NAV:
            self._make_nav_btn(key, icon, label, sub)

        # Divider
        ctk.CTkFrame(self, fg_color=C["border"], height=1).pack(fill="x", padx=16, pady=16)

        # ── Algorithm legend ──────────────────────────────────────────────
        ctk.CTkLabel(
            self, text="ALGORITHMS",
            font=ctk.CTkFont("Segoe UI", 9, "bold"),
            text_color=C["muted"],
        ).pack(anchor="w", padx=20, pady=(0, 6))

        for name, color in ALGO_COLORS.items():
            chip = ctk.CTkFrame(self, fg_color=C["bg_card"], corner_radius=8)
            chip.pack(fill="x", padx=12, pady=2)
            ctk.CTkLabel(chip, text="●",
                         font=ctk.CTkFont("Segoe UI", 10),
                         text_color=color).pack(side="left", padx=(12, 6), pady=8)
            ctk.CTkLabel(chip, text=name,
                         font=ctk.CTkFont("Segoe UI", 11),
                         text_color=C["subtle"]).pack(side="left", pady=8)

        # ── Footer ────────────────────────────────────────────────────────
        ctk.CTkLabel(
            self,
            text="Built with CustomTkinter",
            font=ctk.CTkFont("Segoe UI", 9),
            text_color=C["muted"],
        ).pack(side="bottom", pady=(0, 8))
        ctk.CTkLabel(
            self, text="N-Queens Solver  v1.0",
            font=ctk.CTkFont("Segoe UI", 9, "bold"),
            text_color=C["muted"],
        ).pack(side="bottom", pady=0)

        self._set_active("solve")

    def _make_nav_btn(self, key: str, icon: str, label: str, sub: str):
        frame = ctk.CTkFrame(self, fg_color="transparent", cursor="hand2", corner_radius=10)
        frame.pack(fill="x", padx=10, pady=2)

        inner = ctk.CTkFrame(frame, fg_color="transparent", cursor="hand2")
        inner.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(inner, text=icon,
                     font=ctk.CTkFont("Segoe UI", 20),
                     text_color=C["accent"]).pack(side="left", padx=(0, 12))

        text_col = ctk.CTkFrame(inner, fg_color="transparent")
        text_col.pack(side="left")

        main_lbl = ctk.CTkLabel(
            text_col, text=label,
            font=ctk.CTkFont("Segoe UI", 14, "bold"),
            text_color=C["text"],
        )
        main_lbl.pack(anchor="w")
        ctk.CTkLabel(
            text_col, text=sub,
            font=ctk.CTkFont("Segoe UI", 10),
            text_color=C["muted"],
        ).pack(anchor="w")

        # Bind click to every child widget
        for widget in (frame, inner, text_col, main_lbl):
            widget.bind("<Button-1>", lambda e, k=key: self._click(k))

        self._nav_frames[key] = frame

    def _click(self, key: str):
        self._set_active(key)
        self._on_navigate(key)

    def _set_active(self, key: str):
        self._active = key
        for k, frame in self._nav_frames.items():
            frame.configure(fg_color=C["bg_card"] if k == key else "transparent")


# ══════════════════════════════════════════════════════════════════════════════
# StatusBar
# ══════════════════════════════════════════════════════════════════════════════
class StatusBar(ctk.CTkFrame):
    """Bottom bar showing colour-coded status messages."""

    _COLORS = {
        "info":    C["subtle"],
        "success": C["success"],
        "warning": C["warning"],
        "error":   C["danger"],
    }

    def __init__(self, parent, **kwargs):
        super().__init__(parent, fg_color=C["bg_side"], height=36,
                         corner_radius=0, **kwargs)
        self.pack_propagate(False)

        self._dot = ctk.CTkLabel(self, text="●",
                                  font=ctk.CTkFont("Segoe UI", 10),
                                  text_color=C["muted"])
        self._dot.pack(side="left", padx=(16, 6), pady=0)

        self._lbl = ctk.CTkLabel(self, text="Ready.",
                                  font=ctk.CTkFont("Segoe UI", 12),
                                  text_color=C["muted"])
        self._lbl.pack(side="left")

    def set(self, message: str, level: str = "info"):
        color = self._COLORS.get(level, C["muted"])
        self._dot.configure(text_color=color)
        self._lbl.configure(text=message, text_color=color)


# ══════════════════════════════════════════════════════════════════════════════
# NQueensApp  —  Root Window
# ══════════════════════════════════════════════════════════════════════════════
class NQueensApp(ctk.CTk):
    """
    Root application window.
    Composes Sidebar + Header + page container (SolvePage / ComparePage) + StatusBar.
    """

    _TITLES = {
        "solve":   ("🧩  Solve N-Queens", "Choose an algorithm, set N, and click Solve."),
        "compare": ("📊  Compare Algorithms", "Benchmark all algorithms and analyse the results."),
    }

    def __init__(self):
        super().__init__()
        self.title("N-Queens Solver & Analyzer")
        self.geometry("1280x800")
        self.minsize(960, 640)
        self.configure(fg_color=C["bg"])
        self._build()

        if not _ALGO_OK:
            self._status.set(
                f"⚠  Algorithm files not found — {_ALGO_ERR}  "
                "(ensure backtracking.py, Bestfirst.py, genetic.py, HillClimbing.py are present)",
                "warning",
            )

    # ── Layout ─────────────────────────────────────────────────────────────
    def _build(self):
        # Sidebar (left strip)
        self._sidebar = Sidebar(self, on_navigate=self._navigate)
        self._sidebar.pack(side="left", fill="y")

        # Right panel
        right = ctk.CTkFrame(self, fg_color=C["bg"], corner_radius=0)
        right.pack(side="left", fill="both", expand=True)

        # Header
        self._header_frame = ctk.CTkFrame(right, fg_color=C["bg_card"],
                                           height=62, corner_radius=0)
        self._header_frame.pack(fill="x")
        self._header_frame.pack_propagate(False)

        self._header_title = ctk.CTkLabel(
            self._header_frame, text="🧩  Solve N-Queens",
            font=ctk.CTkFont("Segoe UI", 20, "bold"),
            text_color=C["text"],
        )
        self._header_title.pack(side="left", padx=24)

        self._header_sub = ctk.CTkLabel(
            self._header_frame,
            text="Choose an algorithm, set N, and click Solve.",
            font=ctk.CTkFont("Segoe UI", 12),
            text_color=C["muted"],
        )
        self._header_sub.pack(side="left")

        # Page container
        self._container = ctk.CTkFrame(right, fg_color="transparent")
        self._container.pack(fill="both", expand=True)

        # Status bar
        self._status = StatusBar(right)
        self._status.pack(fill="x", side="bottom")

        # Instantiate pages (hidden until navigated to)
        self._pages: dict[str, ctk.CTkFrame] = {
            "solve":   SolvePage(self._container,   self._status.set),
            "compare": ComparePage(self._container, self._status.set),
        }
        self._show("solve")

    # ── Navigation ──────────────────────────────────────────────────────────
    def _navigate(self, key: str):
        self._show(key)
        title, sub = self._TITLES.get(key, ("N-Queens", ""))
        self._header_title.configure(text=title)
        self._header_sub.configure(text=sub)

    def _show(self, key: str):
        for page in self._pages.values():
            page.pack_forget()
        self._pages[key].pack(fill="both", expand=True)


# ──────────────────────────────────────────────────────────────────────────────
# Entry point
# ──────────────────────────────────────────────────────────────────────────────
def main():
    app = NQueensApp()
    app.mainloop()


if __name__ == "__main__":
    main()