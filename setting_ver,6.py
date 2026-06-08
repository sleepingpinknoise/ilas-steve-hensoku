import random
import tkinter as tk
from tkinter import messagebox


EMPTY = 0
HOLE = -1

PLAYER_COLORS = {
    1: ("黒", "black", "white"),
    2: ("白", "white", "black"),
    3: ("赤", "#d93535", "white"),
    4: ("青", "#1f66d1", "white"),
}

DIRECTIONS = [
    (-1, -1), (-1, 0), (-1, 1),
    (0, -1),           (0, 1),
    (1, -1),  (1, 0),  (1, 1),
]

GRAVITY_DIRECTIONS = {
    "上": (-1, 0),
    "下": (1, 0),
    "左": (0, -1),
    "右": (0, 1),
}

MIRROR_SIDES = ["上半分", "下半分", "左半分", "右半分"]


class OthelloApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Special Othello")
        self.root.geometry("1180x760")

        self.players = []
        self.board = []
        self.ages = []
        self.health = []
        self.holes = set()
        self.current_player_index = 0
        self.turn_count = 0
        self.game_started = False
        self.game_over = False
        self.next_gravity = None
        self.next_mirror = None
        self.next_destroy_targets = []

        self.settings = {}
        self.vars = {}

        self.build_layout()
        self.reset_settings()
        self.show_settings_screen()

    def build_layout(self):
        self.left = tk.Frame(self.root, width=390)
        self.left.pack(side=tk.LEFT, fill=tk.Y, padx=12, pady=12)
        self.left.pack_propagate(False)

        self.right = tk.Frame(self.root)
        self.right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(0, 12), pady=12)

        self.title_label = tk.Label(self.left, text="特殊オセロ設定", font=("Arial", 20, "bold"))
        self.title_label.pack(anchor="w", pady=(0, 8))

        self.canvas = tk.Canvas(self.right, bg="#0b8f3a", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.bind("<Button-1>", self.on_canvas_click)

        self.status = tk.Label(self.right, text="", font=("Arial", 13), anchor="w")
        self.status.pack(fill=tk.X, pady=(8, 0))

    def reset_settings(self):
        self.players = [{"kind": "人間"}, {"kind": "人間"}]
        self.holes = set()

        self.vars = {
            "rows": tk.IntVar(value=8),
            "cols": tk.IntVar(value=8),
            "wrap": tk.BooleanVar(value=False),
            "hole_count": tk.IntVar(value=0),
            "blackout": tk.BooleanVar(value=False),
            "blackout_duration": tk.IntVar(value=5),
            "blackout_interval": tk.IntVar(value=5),
            "gravity": tk.BooleanVar(value=False),
            "gravity_interval": tk.IntVar(value=5),
            "gravity_notice": tk.BooleanVar(value=False),
            "mirror": tk.BooleanVar(value=False),
            "mirror_interval": tk.IntVar(value=5),
            "mirror_notice": tk.BooleanVar(value=False),
            "destroy": tk.BooleanVar(value=False),
            "destroy_count": tk.IntVar(value=1),
            "destroy_interval": tk.IntVar(value=5),
            "destroy_notice": tk.BooleanVar(value=False),
            "expand": tk.BooleanVar(value=False),
            "expand_count": tk.IntVar(value=3),
            "life": tk.BooleanVar(value=False),
            "life_length": tk.IntVar(value=5),
            "life_show": tk.BooleanVar(value=False),
            "health": tk.BooleanVar(value=False),
            "health_count": tk.IntVar(value=3),
            "health_show": tk.BooleanVar(value=False),
            "flip_limit_event": tk.BooleanVar(value=False),
            "flip_limit_interval": tk.IntVar(value=5),
            "flip_limit": tk.BooleanVar(value=False),
            "flip_limit_count": tk.IntVar(value=3),
        }

    def clear_left(self):
        for widget in self.left.winfo_children():
            if widget is not self.title_label:
                widget.destroy()

    def show_settings_screen(self):
        self.clear_left()
        self.title_label.config(text="特殊オセロ設定")
        self.game_started = False
        self.game_over = False

        self.add_player_section()
        self.add_board_section()
        self.add_event_section()

        button_row = tk.Frame(self.left)
        button_row.pack(fill=tk.X, pady=10)
        tk.Button(button_row, text="試合開始", command=self.start_game, font=("Arial", 13, "bold")).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5)
        )
        tk.Button(button_row, text="設定リセット", command=self.reset_all_settings).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0)
        )

        self.draw_preview_board()

    def add_player_section(self):
        frame = tk.LabelFrame(self.left, text="人数変更", padx=8, pady=6)
        frame.pack(fill=tk.X, pady=5)
        self.player_label = tk.Label(frame, text="")
        self.player_label.pack(anchor="w")
        row = tk.Frame(frame)
        row.pack(fill=tk.X, pady=(5, 0))
        tk.Button(row, text="CPU追加", command=lambda: self.add_player("CPU")).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)
        tk.Button(row, text="人数追加", command=lambda: self.add_player("人間")).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)
        tk.Button(row, text="1人削除", command=self.remove_player).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)
        self.update_player_label()

    def add_board_section(self):
        frame = tk.LabelFrame(self.left, text="盤面変更", padx=8, pady=6)
        frame.pack(fill=tk.X, pady=5)

        self.dimension_control(frame, "縦", "rows", 4, 24)
        self.dimension_control(frame, "横", "cols", 4, 24)

        tk.Checkbutton(frame, text="循環", variable=self.vars["wrap"]).pack(anchor="w")

        hole_row = tk.Frame(frame)
        hole_row.pack(fill=tk.X, pady=(6, 0))
        tk.Label(hole_row, text="穴の数").pack(side=tk.LEFT)
        tk.Spinbox(
            hole_row,
            from_=0,
            to=288,
            width=5,
            textvariable=self.vars["hole_count"],
            command=self.clamp_hole_count,
        ).pack(side=tk.LEFT, padx=5)
        tk.Button(hole_row, text="実行", command=self.generate_random_holes).pack(side=tk.LEFT, padx=4)
        tk.Label(frame, text="右の盤面クリックでも穴を指定できます", fg="#444").pack(anchor="w", pady=(3, 0))

    def dimension_control(self, parent, label, key, start, end):
        row = tk.Frame(parent)
        row.pack(fill=tk.X, pady=3)
        tk.Label(row, text=f"{label}マス", width=7, anchor="w").pack(side=tk.LEFT)
        scale = tk.Scale(
            row,
            from_=start,
            to=end,
            orient=tk.HORIZONTAL,
            resolution=2,
            showvalue=False,
            variable=self.vars[key],
            command=lambda _value: self.on_dimension_change(),
        )
        scale.pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.Spinbox(
            row,
            from_=start,
            to=end,
            increment=2,
            width=5,
            textvariable=self.vars[key],
            command=self.on_dimension_change,
        ).pack(side=tk.LEFT, padx=(6, 0))

    def add_event_section(self):
        frame = tk.LabelFrame(self.left, text="イベント選択", padx=8, pady=6)
        frame.pack(fill=tk.BOTH, expand=True, pady=5)

        self.event_row(frame, "暗転", "blackout", [("適応", "blackout_duration", 1, 99), ("間隔", "blackout_interval", 0, 99)])
        self.event_row(frame, "重力", "gravity", [("間隔", "gravity_interval", 0, 99)], "gravity_notice")
        self.event_row(frame, "鏡", "mirror", [("間隔", "mirror_interval", 0, 99)], "mirror_notice")
        self.event_row(
            frame,
            "無差別破壊",
            "destroy",
            [("破壊", "destroy_count", 1, 98), ("間隔", "destroy_interval", 1, 99)],
            "destroy_notice",
        )
        self.event_row(frame, "盤面拡大", "expand", [("回数", "expand_count", 1, 10)])
        self.event_row(frame, "寿命", "life", [("長さ", "life_length", 1, 99)], "life_show", "表示")
        self.event_row(frame, "体力", "health", [("回数", "health_count", 1, 99)], "health_show", "表示")
        self.event_row(frame, "反転個数指定", "flip_limit_event", [("間隔", "flip_limit_interval", 0, 99)])
        self.event_row(frame, "反転力低下", "flip_limit", [("上限", "flip_limit_count", 1, 99)])

    def event_row(self, parent, title, enabled_key, number_specs, option_key=None, option_text="予告"):
        row = tk.Frame(parent)
        row.pack(fill=tk.X, pady=2)
        tk.Checkbutton(row, text=title, variable=self.vars[enabled_key], width=12, anchor="w").pack(side=tk.LEFT)
        for label, key, start, end in number_specs:
            tk.Label(row, text=label).pack(side=tk.LEFT)
            tk.Spinbox(row, from_=start, to=end, width=4, textvariable=self.vars[key]).pack(side=tk.LEFT, padx=(2, 5))
        if option_key:
            tk.Checkbutton(row, text=option_text, variable=self.vars[option_key]).pack(side=tk.LEFT)

    def add_player(self, kind):
        if len(self.players) >= 4:
            messagebox.showinfo("人数変更", "人数は最大4人です。")
            return
        self.players.append({"kind": kind})
        self.update_player_label()
        self.draw_preview_board()

    def remove_player(self):
        if len(self.players) <= 1:
            messagebox.showinfo("人数変更", "一人は残してください。")
            return
        self.players.pop()
        self.update_player_label()
        self.draw_preview_board()

    def update_player_label(self):
        counts = []
        for i, player in enumerate(self.players, start=1):
            counts.append(f"{PLAYER_COLORS[i][0]}:{player['kind']}")
        self.player_label.config(text=f"{len(self.players)}人対戦  " + " / ".join(counts))
        if hasattr(self, "remove_btn"):
            state = tk.DISABLED if len(self.players) <= 1 else tk.NORMAL  # <= 2 → <= 1
            self.remove_btn.config(state=state)

    def reset_all_settings(self):
        self.reset_settings()
        self.show_settings_screen()

    def on_dimension_change(self):
        self.force_even_dimensions()
        self.remove_invalid_holes()
        self.clamp_hole_count()
        self.draw_preview_board()

    def force_even_dimensions(self):
        for key in ("rows", "cols"):
            value = self.vars[key].get()
            value = max(4, min(24, value))
            if value % 2:
                value += 1
            self.vars[key].set(max(4, min(24, value)))

    def max_holes(self):
        return (self.vars["rows"].get() * self.vars["cols"].get()) // 2

    def clamp_hole_count(self):
        value = max(0, min(self.max_holes(), self.vars["hole_count"].get()))
        self.vars["hole_count"].set(value)

    def initial_cells(self, rows=None, cols=None, player_count=None):
        rows = rows or self.vars["rows"].get()
        cols = cols or self.vars["cols"].get()
        player_count = player_count or len(self.players)
        top = rows // 2 - 2
        left = cols // 2 - 2
        if player_count < 2:
            return {}
        pattern = {
            2: ["0000", "0210", "0120", "0000"],
            3: ["0200", "1310", "0232", "0010"],
            4: ["0430", "4123", "2341", "0210"],
        }[player_count]
        cells = {}
        for r, line in enumerate(pattern):
            for c, char in enumerate(line):
                value = int(char)
                if value:
                    cells[(top + r, left + c)] = value
        return cells

    def remove_invalid_holes(self):
        rows = self.vars["rows"].get()
        cols = self.vars["cols"].get()
        initial = set(self.initial_cells(rows, cols).keys())
        self.holes = {
            cell for cell in self.holes
            if 0 <= cell[0] < rows and 0 <= cell[1] < cols and cell not in initial
        }

    def generate_random_holes(self):
        self.force_even_dimensions()
        self.clamp_hole_count()
        rows = self.vars["rows"].get()
        cols = self.vars["cols"].get()
        initial = set(self.initial_cells(rows, cols).keys())
        candidates = [
            (r, c)
            for r in range(rows)
            for c in range(cols)
            if (r, c) not in initial
        ]
        count = min(self.vars["hole_count"].get(), len(candidates))
        self.holes = set(random.sample(candidates, count))
        self.draw_preview_board()

    def collect_settings(self):
        self.force_even_dimensions()
        self.clamp_hole_count()
        destroy_interval = max(1, self.vars["destroy_interval"].get())
        self.vars["destroy_count"].set(min(self.vars["destroy_count"].get(), destroy_interval - 1 or 1))
        return {key: var.get() for key, var in self.vars.items()}

    def start_game(self):
        if len(self.players) < 2:
            messagebox.showinfo("人数変更", "人数は最低2人です。")
            return
        self.settings = self.collect_settings()
        self.board = self.create_initial_board()
        self.ages = [[None for _ in row] for row in self.board]
        self.health = [[None for _ in row] for row in self.board]
        self.current_player_index = 0
        self.turn_count = 0
        self.game_started = True
        self.game_over = False
        self.prepare_predictions()
        self.show_game_controls()
        self.draw_board()
        self.schedule_cpu_if_needed()

    def show_game_controls(self):
        self.clear_left()
        self.title_label.config(text="特殊オセロ")
        info = tk.LabelFrame(self.left, text="対局情報", padx=8, pady=8)
        info.pack(fill=tk.X, pady=5)
        self.game_info = tk.Label(info, text="", justify=tk.LEFT, anchor="w")
        self.game_info.pack(fill=tk.X)
        tk.Button(self.left, text="設定画面に戻る", command=self.confirm_return_to_settings).pack(fill=tk.X, pady=10)

    def confirm_return_to_settings(self):
        if messagebox.askyesno("設定画面", "対局を終了して設定画面に戻りますか？"):
            self.show_settings_screen()

    def create_initial_board(self):
        rows = self.settings["rows"]
        cols = self.settings["cols"]
        board = [[EMPTY for _ in range(cols)] for _ in range(rows)]
        for r, c in self.holes:
            if 0 <= r < rows and 0 <= c < cols:
                board[r][c] = HOLE
        for (r, c), value in self.initial_cells(rows, cols, len(self.players)).items():
            board[r][c] = value
        return board

    def current_player(self):
        return self.current_player_index + 1

    def player_name(self, player):
        return PLAYER_COLORS[player][0]

    def is_human_turn(self):
        return self.players[self.current_player_index]["kind"] == "人間"

    def in_bounds(self, row, col):
        return 0 <= row < len(self.board) and 0 <= col < len(self.board[0])

    def next_pos(self, row, col, dr, dc):
        row += dr
        col += dc
        if self.settings.get("wrap"):
            return row % len(self.board), col % len(self.board[0])
        if self.in_bounds(row, col):
            return row, col
        return None

    def get_flips(self, row, col, player):
        if not self.in_bounds(row, col) or self.board[row][col] != EMPTY:
            return []

        flips = []
        max_steps = len(self.board) * len(self.board[0])
        line_limit = self.settings.get("flip_limit_count", 99) if self.settings.get("flip_limit") else 99

        for dr, dc in DIRECTIONS:
            pos = self.next_pos(row, col, dr, dc)
            line = []
            seen = set()
            while pos is not None and pos not in seen and len(seen) < max_steps:
                seen.add(pos)
                r, c = pos
                value = self.board[r][c]
                if value in (EMPTY, HOLE):
                    break
                if value == player:
                    if line:
                        flips.extend(line[:line_limit])
                    break
                line.append((r, c))
                pos = self.next_pos(r, c, dr, dc)
        return flips

    def valid_moves(self, player):
        moves = []
        for row in range(len(self.board)):
            for col in range(len(self.board[0])):
                if self.get_flips(row, col, player):
                    moves.append((row, col))
        return moves

    def next_player_with_move(self):
        for step in range(1, len(self.players) + 1):
            next_index = (self.current_player_index + step) % len(self.players)
            if self.valid_moves(next_index + 1):
                return next_index
        return None

    def place_piece(self, row, col):
        if self.game_over:
            return
        player = self.current_player()
        flips = self.get_flips(row, col, player)
        if not flips:
            self.status.config(text="そこには置けません")
            return

        self.board[row][col] = player
        self.ages[row][col] = 0 if self.settings.get("life") else None
        self.health[row][col] = self.settings.get("health_count") if self.settings.get("health") else None

        for r, c in flips:
            if self.settings.get("health") and self.health[r][c] is not None:
                self.health[r][c] -= 1
                if self.health[r][c] <= 0:
                    self.board[r][c] = EMPTY
                    self.ages[r][c] = None
                    self.health[r][c] = None
                    continue
            self.board[r][c] = player

        if self.settings.get("expand") and self.settings["expand_count"] > 0 and self.is_outer_cell(row, col):
            self.expand_board()
            self.settings["expand_count"] -= 1

        self.turn_count += 1
        self.after_turn_events()

        next_index = self.next_player_with_move()
        if next_index is None:
            self.end_game()
            return
        self.current_player_index = next_index
        self.prepare_predictions()
        self.draw_board()
        self.schedule_cpu_if_needed()

    def is_outer_cell(self, row, col):
        return row == 0 or col == 0 or row == len(self.board) - 1 or col == len(self.board[0]) - 1

    def after_turn_events(self):
        self.apply_life()
        if self.should_fire("gravity", "gravity_interval"):
            self.apply_gravity(self.next_gravity or random.choice(list(GRAVITY_DIRECTIONS)))
        if self.should_fire("mirror", "mirror_interval"):
            self.apply_mirror(self.next_mirror or random.choice(MIRROR_SIDES))
        if self.should_fire("destroy", "destroy_interval"):
            self.apply_destroy(self.next_destroy_targets)

    def should_fire(self, enabled_key, interval_key):
        if not self.settings.get(enabled_key):
            return False
        interval = self.settings.get(interval_key, 0)
        return interval == 0 or (self.turn_count > 0 and self.turn_count % interval == 0)

    def apply_life(self):
        if not self.settings.get("life"):
            return
        limit = self.settings["life_length"]
        for r in range(len(self.board)):
            for c in range(len(self.board[0])):
                if self.board[r][c] > 0 and self.ages[r][c] is not None:
                    self.ages[r][c] += 1
                    if self.ages[r][c] >= limit:
                        self.board[r][c] = EMPTY
                        self.ages[r][c] = None
                        self.health[r][c] = None

    def apply_gravity(self, direction_name):
        dr, dc = GRAVITY_DIRECTIONS[direction_name]
        pieces = []
        holes = {(r, c) for r, row in enumerate(self.board) for c, value in enumerate(row) if value == HOLE}
        for r in range(len(self.board)):
            for c in range(len(self.board[0])):
                if self.board[r][c] > 0:
                    pieces.append((r, c, self.board[r][c], self.ages[r][c], self.health[r][c]))
                    self.board[r][c] = EMPTY
                    self.ages[r][c] = None
                    self.health[r][c] = None
        pieces.sort(key=lambda item: item[0] * dr + item[1] * dc, reverse=True)
        occupied = set(holes)
        for r, c, value, age, hp in pieces:
            nr, nc = r, c
            while True:
                test = (nr + dr, nc + dc)
                if not self.in_bounds(*test) or test in occupied:
                    break
                nr, nc = test
            self.board[nr][nc] = value
            self.ages[nr][nc] = age
            self.health[nr][nc] = hp
            occupied.add((nr, nc))
        self.next_gravity = None
    def apply_mirror(self, side):
        rows = len(self.board)
        cols = len(self.board[0])
        if side in ("上半分", "下半分"):
            source_rows = range(0, rows // 2) if side == "上半分" else range(rows // 2, rows)
            for r in source_rows:
                target_r = rows - 1 - r
                for c in range(cols):
                    self.copy_cell(r, c, target_r, c)
        else:
            source_cols = range(0, cols // 2) if side == "左半分" else range(cols // 2, cols)
            for c in source_cols:
                target_c = cols - 1 - c
                for r in range(rows):
                    self.copy_cell(r, c, r, target_c)

    def copy_cell(self, sr, sc, tr, tc):
        self.board[tr][tc] = self.board[sr][sc]
        self.ages[tr][tc] = self.ages[sr][sc]
        self.health[tr][tc] = self.health[sr][sc]

    def apply_destroy(self, targets):
        if not targets:
            targets = self.random_piece_targets(self.settings["destroy_count"])
        for r, c in targets:
            if self.in_bounds(r, c) and self.board[r][c] > 0:
                self.board[r][c] = EMPTY
                self.ages[r][c] = None
                self.health[r][c] = None
        self.next_destroy_targets = []

    def random_piece_targets(self, count):
        pieces = [
            (r, c)
            for r in range(len(self.board))
            for c in range(len(self.board[0]))
            if self.board[r][c] > 0
        ]
        return random.sample(pieces, min(count, len(pieces))) if pieces else []

    def expand_board(self):
        old_rows = len(self.board)
        old_cols = len(self.board[0])
        if old_rows >= 24 or old_cols >= 24:
            return
        old_board = [row[:] for row in self.board]
        old_ages = [row[:] for row in self.ages]
        old_health = [row[:] for row in self.health]
        new_rows = min(24, old_rows + 2)
        new_cols = min(24, old_cols + 2)
        self.board = [[EMPTY for _ in range(new_cols)] for _ in range(new_rows)]
        self.ages = [[None for _ in range(new_cols)] for _ in range(new_rows)]
        self.health = [[None for _ in range(new_cols)] for _ in range(new_rows)]
        row_shift = 1 if new_rows > old_rows else 0
        col_shift = 1 if new_cols > old_cols else 0
        for r in range(old_rows):
            for c in range(old_cols):
                nr = r + row_shift
                nc = c + col_shift
                self.board[nr][nc] = old_board[r][c]
                self.ages[nr][nc] = old_ages[r][c]
                self.health[nr][nc] = old_health[r][c]
        messagebox.showinfo("盤面拡大", "盤面が拡大しました。")

    def prepare_predictions(self):
        if self.settings.get("gravity") and self.settings.get("gravity_notice"):
            if self.next_gravity ==None:
                self.next_gravity = random.choice(list(GRAVITY_DIRECTIONS))
        else:
            self.next_gravity = None
        if self.settings.get("mirror") and self.settings.get("mirror_notice"):
            self.next_mirror = random.choice(MIRROR_SIDES)
        else:
            self.next_mirror = None
        if self.settings.get("destroy") and self.settings.get("destroy_notice"):
            if self.next_destroy_targets==[]:
                self.next_destroy_targets = self.random_piece_targets(self.settings["destroy_count"])
        else:
            self.next_destroy_targets = []

    def schedule_cpu_if_needed(self):
        if self.game_started and not self.game_over and not self.is_human_turn():
            self.root.after(500, self.cpu_move)

    def cpu_move(self):
        if not self.game_started or self.game_over or self.is_human_turn():
            return
        moves = self.valid_moves(self.current_player())
        if moves:
            self.place_piece(*random.choice(moves))

    def on_canvas_click(self, event):
        cell = self.cell_from_event(event)
        if cell is None:
            return
        row, col = cell
        if not self.game_started:
            self.toggle_hole(row, col)
            return
        if self.is_human_turn():
            self.place_piece(row, col)

    def toggle_hole(self, row, col):
        self.force_even_dimensions()
        initial = set(self.initial_cells().keys())
        if (row, col) in initial:
            messagebox.showinfo("穴指定", "初期配置の場所には穴を作れません。")
            return
        if (row, col) in self.holes:
            self.holes.remove((row, col))
        else:
            if len(self.holes) >= self.max_holes():
                messagebox.showinfo("穴指定", "穴の数が上限に達しています。")
                return
            self.holes.add((row, col))
        self.vars["hole_count"].set(len(self.holes))
        self.draw_preview_board()

    def cell_from_event(self, event):
        if self.game_started and self.board:
            rows = len(self.board)
            cols = len(self.board[0])
        else:
            rows = self.vars["rows"].get()
            cols = self.vars["cols"].get()
        size, offset_x, offset_y = self.board_geometry(rows, cols)
        col = int((event.x - offset_x) // size)
        row = int((event.y - offset_y) // size)
        if 0 <= row < rows and 0 <= col < cols:
            return row, col
        return None

    def board_geometry(self, rows, cols):
        width = max(1, self.canvas.winfo_width())
        height = max(1, self.canvas.winfo_height())
        size = max(16, min((width - 20) // cols, (height - 20) // rows))
        offset_x = (width - size * cols) // 2
        offset_y = (height - size * rows) // 2
        return size, offset_x, offset_y

    def draw_preview_board(self):
        self.force_even_dimensions()
        rows = self.vars["rows"].get()
        cols = self.vars["cols"].get()
        preview = [[EMPTY for _ in range(cols)] for _ in range(rows)]
        for r, c in self.holes:
            if 0 <= r < rows and 0 <= c < cols:
                preview[r][c] = HOLE
        for (r, c), value in self.initial_cells(rows, cols, len(self.players)).items():
            preview[r][c] = value
        self.draw_grid(preview, title="初期配置プレビュー")
        self.status.config(text="設定を調整してから試合開始を押してください。")

    def draw_board(self):
        self.draw_grid(self.board, title=None)
        counts = self.count_pieces()
        player = self.current_player()
        text = [f"{self.turn_count}ターン目", f"手番: {self.player_name(player)} ({self.players[player - 1]['kind']})"]
        text.extend(f"{self.player_name(p)}:{counts.get(p, 0)}" for p in range(1, len(self.players) + 1))
        if self.next_gravity:
            text.append(f"重力予告:{self.next_gravity}")
        if self.next_mirror:
            text.append(f"鏡予告:{self.next_mirror}")
        if self.next_destroy_targets:
            text.append(f"破壊予告:{len(self.next_destroy_targets)}個")
        self.status.config(text="   ".join(text))
        if hasattr(self, "game_info"):
            self.game_info.config(text="\n".join(text))

    def draw_grid(self, board, title=None):
        self.canvas.delete("all")
        rows = len(board)
        cols = len(board[0])
        size, offset_x, offset_y = self.board_geometry(rows, cols)
        blackout = self.is_blackout_active() if self.game_started else False
        valid = set(self.valid_moves(self.current_player())) if self.game_started and blackout else set()

        if title:
            self.canvas.create_text(
                self.canvas.winfo_width() // 2,
                18,
                text=title,
                fill="white",
                font=("Arial", 16, "bold"),
            )

        for r in range(rows):
            for c in range(cols):
                x1 = offset_x + c * size
                y1 = offset_y + r * size
                x2 = x1 + size
                y2 = y1 + size
                value = board[r][c]
                if value == HOLE:
                    fill = "#FFFFFF"
                elif blackout and (r, c) not in valid:
                    fill = "#111111"
                else:
                    fill = "#0b8f3a"
                self.canvas.create_rectangle(x1, y1, x2, y2, outline="black", fill=fill)

                if value > 0 and not (blackout and (r, c) not in valid):
                    name, color, text_color = PLAYER_COLORS[value]
                    pad = max(3, size // 9)
                    self.canvas.create_oval(x1 + pad, y1 + pad, x2 - pad, y2 - pad, fill=color, outline="black")
                    if size >= 28:
                        if self.settings.get("life_show") and self.ages and self.ages[r][c] is not None:
                            left = max(0, self.settings["life_length"] - self.ages[r][c])
                            self.canvas.create_text((x1 + x2) // 2, y1 + size * 0.28, text=str(left), fill=text_color, font=("Arial", 8))
                        if self.settings.get("health_show") and self.health and self.health[r][c] is not None:
                            self.canvas.create_text((x1 + x2) // 2, y2 - size * 0.28, text=str(self.health[r][c]), fill=text_color, font=("Arial", 8))

                if self.game_started and (r, c) in self.valid_moves(self.current_player()):
                    self.canvas.create_oval(
                        x1 + size * 0.38,
                        y1 + size * 0.38,
                        x2 - size * 0.38,
                        y2 - size * 0.38,
                        fill="#f2d04f",
                        outline="",
                    )

                if self.game_started and (r, c) in self.next_destroy_targets:
                    self.canvas.create_rectangle(
                        x1 + 3,
                        y1 + 3,
                        x2 - 3,
                        y2 - 3,
                        outline="#ff4d4d",
                        width=3,
                    )

        if self.game_over:
            self.canvas.create_rectangle(offset_x + 30, offset_y + 90, offset_x + size * cols - 30, offset_y + 210, fill="white", outline="black", width=2)
            self.canvas.create_text(offset_x + size * cols // 2, offset_y + 135, text="ゲーム終了", font=("Arial", 28, "bold"))
            self.canvas.create_text(offset_x + size * cols // 2, offset_y + 180, text=self.result_text(), font=("Arial", 16))

    def is_blackout_active(self):
        if not self.settings.get("blackout"):
            return False
        interval = self.settings.get("blackout_interval", 5)
        duration = self.settings.get("blackout_duration", 5)
        if interval == 0:
            return True
        cycle = duration + interval
        return self.turn_count % cycle < duration

    def count_pieces(self):
        counts = {player: 0 for player in range(1, len(self.players) + 1)}
        for row in self.board:
            for value in row:
                if value > 0:
                    counts[value] = counts.get(value, 0) + 1
        return counts

    def result_text(self):
        counts = self.count_pieces()
        best = max(counts.values()) if counts else 0
        winners = [self.player_name(player) for player, count in counts.items() if count == best]
        if len(winners) == 1:
            return f"{winners[0]}の勝ち  " + "  ".join(f"{self.player_name(p)}:{c}" for p, c in counts.items())
        return "引き分け  " + "  ".join(f"{self.player_name(p)}:{c}" for p, c in counts.items())

    def end_game(self):
        self.game_over = True
        self.draw_board()
        messagebox.showinfo("ゲーム終了", self.result_text())


if __name__ == "__main__":
    root = tk.Tk()
    app = OthelloApp(root)
    root.mainloop()
