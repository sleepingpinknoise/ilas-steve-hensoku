import asyncio
import json
import random
import threading
import tkinter as tk
from tkinter import messagebox
import websockets

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

SERVER_URL = "wss://ilas-steve-hensoku.onrender.com/ws"

class OthelloApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Special Othello (Online)")
        self.root.geometry("1180x760")

        self.players = []
        self.board = []
        self.cell_scores = []
        self.ages = []
        self.health = []
        self.flip_mission_counters = []
        self.flip_mission_targets = []
        self.current_player_index = 0
        self.turn_count = 0
        self.game_started = False
        self.game_over = False
        self.next_gravity = None
        self.next_mirror = None
        self.next_destroy_targets = []
        self.is_bonus_turn = False

        # --- オンライン通信用の変数 ---
        self.websocket = None
        self.my_player_number = None  # 自分が何Pか (1=黒, 2=白)
        self.loop = None

        self.settings = {}
        self.vars = {}

        self.build_layout()
        self.reset_settings()
        self.show_settings_screen()

        # 起動と同時にバックグラウンドで通信用スレッドを開始
        self.start_network_thread()

    # ==========================================
    # 📡 オンライン通信コアロジック
    # ==========================================
    def start_network_thread(self):
        self.loop = asyncio.new_event_loop()
        threading.Thread(target=self.run_async_loop, daemon=True).start()

    def run_async_loop(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self.connect_to_server())

    async def connect_to_server(self):
        self.status.config(text="Renderサーバーに接続中...")
        try:
            async with websockets.connect(SERVER_URL) as websocket:
                self.websocket = websocket
                self.status.config(text="【オンライン】 接続成功！設定を決めて『試合開始』を押してね。")
                
                while True:
                    message = await websocket.recv()
                    data = json.loads(message)
                    
                    # 1P(ホスト)から初期化データを受信した場合
                    if data["type"] == "START_GAME":
                        if self.my_player_number is None:
                            self.my_player_number = 2  # 後から入ってきた人は自動的に2P(白)
                        
                        self.settings = data["settings"]
                        self.board = data["board"]
                        self.cell_scores = data["cell_scores"]
                        self.ages = data["ages"]
                        self.health = data["health"]
                        self.flip_mission_counters = data["flip_mission_counters"]
                        self.flip_mission_targets = data["flip_mission_targets"]
                        self.current_player_index = data["current_player_index"]
                        self.turn_count = data["turn_count"]
                        self.next_gravity = data["next_gravity"]
                        self.next_mirror = data["next_mirror"]
                        self.next_destroy_targets = data["next_destroy_targets"]
                        
                        self.game_started = True
                        self.game_over = False
                        self.root.after(0, self.show_game_controls)
                        self.root.after(0, self.draw_board)

                    # 相手が石を置いて、計算済みの最新盤面が送られてきた場合
                    elif data["type"] == "UPDATE_BOARD":
                        self.board = data["board"]
                        self.ages = data["ages"]
                        self.health = data["health"]
                        self.current_player_index = data["current_player_index"]
                        self.turn_count = data["turn_count"]
                        self.next_gravity = data["next_gravity"]
                        self.next_mirror = data["next_mirror"]
                        self.next_destroy_targets = data["next_destroy_targets"]
                        self.flip_mission_counters = data["flip_mission_counters"]
                        self.flip_mission_targets = data["flip_mission_targets"]
                        self.is_bonus_turn = data["is_bonus_turn"]
                        self.game_over = data["game_over"]
                        
                        self.root.after(0, self.draw_board)
                        if self.game_over:
                            self.root.after(0, self.end_game_popup)
                            
        except Exception as e:
            self.status.config(text=f"【切断またはエラー】: {e}")

    def send_to_server(self, payload):
        if self.websocket:
            asyncio.run_coroutine_threadsafe(
                self.websocket.send(json.dumps(payload)), 
                self.loop
            )

    # ==========================================
    # 🛠️ UIレイアウト・設定画面
    # ==========================================
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
            "rows": tk.IntVar(value=8), "cols": tk.IntVar(value=8), "wrap": tk.BooleanVar(value=False),
            "hole_count": tk.IntVar(value=0), "blackout": tk.BooleanVar(value=False),
            "blackout_duration": tk.IntVar(value=5), "blackout_interval": tk.IntVar(value=5),
            "gravity": tk.BooleanVar(value=False), "gravity_interval": tk.IntVar(value=5), "gravity_notice": tk.BooleanVar(value=False),
            "mirror": tk.BooleanVar(value=False), "mirror_interval": tk.IntVar(value=5), "mirror_notice": tk.BooleanVar(value=False),
            "destroy": tk.BooleanVar(value=False), "destroy_count": tk.IntVar(value=1), "destroy_interval": tk.IntVar(value=5), "destroy_notice": tk.BooleanVar(value=False),
            "expand": tk.BooleanVar(value=False), "expand_count": tk.IntVar(value=3),
            "life": tk.BooleanVar(value=False), "life_length": tk.IntVar(value=5), "life_show": tk.BooleanVar(value=False),
            "health": tk.BooleanVar(value=False), "health_count": tk.IntVar(value=3), "health_show": tk.BooleanVar(value=False),
            "flip_limit_event": tk.BooleanVar(value=False), "flip_limit_interval": tk.IntVar(value=5), "flip_limit_notice": tk.BooleanVar(value=False),
            "flip_limit": tk.BooleanVar(value=False), "flip_limit_count": tk.IntVar(value=3),
            "reverse_judgment": tk.BooleanVar(value=False),
            "total_score": tk.BooleanVar(value=False), "total_score_count": tk.IntVar(value=5), "total_score_show": tk.BooleanVar(value=False),
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

        self.add_board_section()
        self.add_event_section()

        button_row = tk.Frame(self.left)
        button_row.pack(fill=tk.X, pady=10)
        tk.Button(button_row, text="試合開始 (自分が1Pホスト)", command=self.start_game, font=("Arial", 13, "bold"), bg="#1f66d1", fg="white").pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.draw_preview_board()

    def add_board_section(self):
        frame = tk.LabelFrame(self.left, text="盤面変更", padx=8, pady=6)
        frame.pack(fill=tk.X, pady=5)
        self.dimension_control(frame, "縦", "rows", 4, 24)
        self.dimension_control(frame, "横", "cols", 4, 24)
        tk.Checkbutton(frame, text="循環（端と端が繋がる）", variable=self.vars["wrap"]).pack(anchor="w")
        
        hole_row = tk.Frame(frame)
        hole_row.pack(fill=tk.X, pady=(6, 0))
        tk.Label(hole_row, text="穴の数").pack(side=tk.LEFT)
        tk.Spinbox(hole_row, from_=0, to=288, width=5, textvariable=self.vars["hole_count"], command=self.clamp_hole_count).pack(side=tk.LEFT, padx=5)
        tk.Button(hole_row, text="ランダム穴生成", command=self.generate_random_holes).pack(side=tk.LEFT, padx=4)

    def dimension_control(self, parent, label, key, start, end):
        row = tk.Frame(parent)
        row.pack(fill=tk.X, pady=3)
        tk.Label(row, text=f"{label}マス", width=7, anchor="w").pack(side=tk.LEFT)
        scale = tk.Scale(row, from_=start, to=end, orient=tk.HORIZONTAL, showvalue=False, variable=self.vars[key], command=lambda _: self.on_dimension_change())
        scale.pack(side=tk.LEFT, fill=tk.X, expand=True)

    def add_event_section(self):
        frame = tk.LabelFrame(self.left, text="イベント選択", padx=8, pady=6)
        frame.pack(fill=tk.BOTH, expand=True, pady=5)
        canvas = tk.Canvas(frame, highlightthickness=0)
        scrollbar = tk.Scrollbar(frame, orient=tk.VERTICAL, command=canvas.yview)
        inner_frame = tk.Frame(canvas)
        inner_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=inner_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.event_row(inner_frame, "暗転", "blackout", [("適応", "blackout_duration", 1, 99), ("間隔", "blackout_interval", 0, 99)])
        self.event_row(inner_frame, "重力", "gravity", [("間隔", "gravity_interval", 0, 99)], "gravity_notice")
        self.event_row(inner_frame, "鏡", "mirror", [("間隔", "mirror_interval", 0, 99)], "mirror_notice")
        self.event_row(inner_frame, "無差別破壊", "destroy", [("破壊", "destroy_count", 1, 98), ("間隔", "destroy_interval", 1, 99)], "destroy_notice")
        self.event_row(inner_frame, "寿命", "life", [("長さ", "life_length", 1, 99)], "life_show", "表示")
        self.event_row(inner_frame, "体力", "health", [("回数", "health_count", 1, 99)], "health_show", "表示")
        self.event_row(inner_frame, "反転個数指定", "flip_limit_event", [("間隔", "flip_limit_interval", 1, 99)])
        self.event_row(inner_frame, "反転力低下", "flip_limit", [("上限", "flip_limit_count", 1, 99)])
        self.event_row(inner_frame, "判定逆転", "reverse_judgment", [])
        self.event_row(inner_frame, "総得点オセロ", "total_score", [("上限", "total_score_count", 1, 99)], "total_score_show", "表示")

    def event_row(self, parent, title, enabled_key, number_specs, option_key=None, option_text="予告"):
        row = tk.Frame(parent)
        row.pack(fill=tk.X, pady=2)
        tk.Checkbutton(row, text=title, variable=self.vars[enabled_key], width=12, anchor="w").pack(side=tk.LEFT)
        for label, key, start, end in number_specs:
            tk.Label(row, text=label).pack(side=tk.LEFT)
            tk.Spinbox(row, from_=start, to=end, width=4, textvariable=self.vars[key]).pack(side=tk.LEFT, padx=(2, 5))
        if option_key:
            tk.Checkbutton(row, text=option_text, variable=self.vars[option_key]).pack(side=tk.LEFT)

    def on_dimension_change(self):
        self.force_even_dimensions()
        self.remove_invalid_holes()
        self.clamp_hole_count()
        self.draw_preview_board()

    def force_even_dimensions(self):
        for key in ("rows", "cols"):
            v = self.vars[key].get()
            if v % 2: self.vars[key].set(v + 1)

    def max_holes(self): return (self.vars["rows"].get() * self.vars["cols"].get()) // 2
    def clamp_hole_count(self): self.vars["hole_count"].set(max(0, min(self.max_holes(), self.vars["hole_count"].get())))

    def initial_cells(self, rows=None, cols=None):
        rows = rows or self.vars["rows"].get()
        cols = cols or self.vars["cols"].get()
        top, left = rows // 2 - 1, cols // 2 - 1
        return {(top, left): 2, (top, left+1): 1, (top+1, left): 1, (top+1, left+1): 2}

    def remove_invalid_holes(self):
        initial = set(self.initial_cells().keys())
        self.holes = {c for c in self.holes if 0 <= c[0] < self.vars["rows"].get() and 0 <= c[1] < self.vars["cols"].get() and c not in initial}

    def generate_random_holes(self):
        self.force_even_dimensions()
        initial = set(self.initial_cells().keys())
        candidates = [(r, c) for r in range(self.vars["rows"].get()) for c in range(self.vars["cols"].get()) if (r, c) not in initial]
        self.holes = set(random.sample(candidates, min(self.vars["hole_count"].get(), len(candidates))))
        self.draw_preview_board()

    # ==========================================
    # 🎮 ゲームプレイ・同期ロジック
    # ==========================================
    def start_game(self):
        """【ホスト処理】自分が1Pとして部屋を設定し、相手に送りつけて同期する"""
        self.my_player_number = 1
        self.settings = {k: v.get() for k, v in self.vars.items()}
        
        rows, cols = self.settings["rows"], self.settings["cols"]
        self.board = [[EMPTY for _ in range(cols)] for _ in range(rows)]
        for r, c in self.holes: self.board[r][c] = HOLE
        for (r, c), val in self.initial_cells(rows, cols).items(): self.board[r][c] = val
        
        self.cell_scores = [[random.randint(1, self.settings.get("total_score_count", 5)) if self.settings.get("total_score") else 1 for _ in range(cols)] for _ in range(rows)]
        self.ages = [[None for _ in range(cols)] for _ in range(rows)]
        self.health = [[None for _ in range(cols)] for _ in range(rows)]
        self.flip_mission_counters = [self.settings.get("flip_limit_interval", 5), self.settings.get("flip_limit_interval", 5)]
        self.flip_mission_targets = [random.randint(1, 4), random.randint(1, 4)]
        
        self.turn_count = 0
        self.current_player_index = 0
        self.game_started = True
        self.game_over = False
        self.prepare_predictions()
        
        # 2P(対戦相手)に初期データをまるごと同期
        payload = {
            "type": "START_GAME", "settings": self.settings, "board": self.board, "cell_scores": self.cell_scores,
            "ages": self.ages, "health": self.health, "flip_mission_counters": self.flip_mission_counters,
            "flip_mission_targets": self.flip_mission_targets, "current_player_index": self.current_player_index,
            "turn_count": self.turn_count, "next_gravity": self.next_gravity, "next_mirror": self.next_mirror, "next_destroy_targets": self.next_destroy_targets
        }
        self.send_to_server(payload)
        
        self.show_game_controls()
        self.draw_board()

    def show_game_controls(self):
        self.clear_left()
        self.title_label.config(text="特殊オセロ 対局中")
        info = tk.LabelFrame(self.left, text="対局情報", padx=8, pady=8)
        info.pack(fill=tk.X, pady=5)
        self.game_info = tk.Label(info, text="", justify=tk.LEFT, anchor="w")
        self.game_info.pack(fill=tk.X)

    def current_player(self): return self.current_player_index + 1
    def player_name(self, p): return PLAYER_COLORS[p][0]
    def in_bounds(self, r, c): return 0 <= r < len(self.board) and 0 <= c < len(self.board[0])

    def next_pos(self, r, c, dr, dc):
        r, c = r + dr, c + dc
        if self.settings.get("wrap"): return r % len(self.board), c % len(self.board[0])
        return (r, c) if self.in_bounds(r, c) else None

    def get_flips(self, row, col, player):
        if not self.in_bounds(row, col) or self.board[row][col] != EMPTY: return []
        flips = []
        line_limit = self.settings.get("flip_limit_count", 99) if self.settings.get("flip_limit") else 99
        for dr, dc in DIRECTIONS:
            pos = self.next_pos(row, col, dr, dc)
            line = []
            while pos and self.board[pos[0]][pos[1]] not in (EMPTY, HOLE):
                if self.board[pos[0]][pos[1]] == player:
                    if line: flips.extend(line[:line_limit])
                    break
                line.append(pos)
                pos = self.next_pos(pos[0], pos[1], dr, dc)
        return flips

    def valid_moves(self, player):
        return [(r, c) for r in range(len(self.board)) for c in range(len(self.board[0])) if self.get_flips(r, c, player)]

    def place_piece(self, row, col):
        """【手番関所】自分の手番の時だけ石を置き、計算結果を通信で相手に上書きさせる"""
        if self.game_over or self.current_player() != self.my_player_number: return
        
        player = self.current_player()
        flips = self.get_flips(row, col, player)
        if not flips: return

        self.board[row][col] = player
        if self.settings.get("life"): self.ages[row][col] = 0
        if self.settings.get("health"): self.health[row][col] = self.settings["health_count"]

        for r, c in flips:
            if self.settings.get("health") and self.health[r][c] is not None:
                self.health[r][c] -= 1
                if self.health[r][c] <= 0:
                    self.board[r][c] = EMPTY
                    self.ages[r][c] = self.health[r][c] = None
                    continue
            self.board[r][c] = player

        self.turn_count += 1
        self.after_turn_events()

        # 限定ミッション処理
        is_bonus = False
        pi = self.current_player_index
        if self.settings.get("flip_limit_event"):
            if self.flip_mission_counters[pi] == 0:
                if len(flips) == self.flip_mission_targets[pi]:
                    is_bonus = True
                self.flip_mission_counters[pi] = self.settings.get("flip_limit_interval", 5)
                self.flip_mission_targets[pi] = random.randint(1, 4)
            else:
                self.flip_mission_counters[pi] -= 1

        if is_bonus and self.valid_moves(player):
            self.is_bonus_turn = True
        else:
            self.is_bonus_turn = False
            # オンライン用に2人手番で交代
            self.current_player_index = (self.current_player_index + 1) % 2

        # 双方パスなら終了
        if not self.valid_moves(1) and not self.valid_moves(2):
            self.game_over = True

        self.prepare_predictions()
        self.draw_board()

        # 変更された最新データを丸ごとサーバー経由で送信
        payload = {
            "type": "UPDATE_BOARD", "board": self.board, "ages": self.ages, "health": self.health,
            "current_player_index": self.current_player_index, "turn_count": self.turn_count,
            "next_gravity": self.next_gravity, "next_mirror": self.next_mirror, "next_destroy_targets": self.next_destroy_targets,
            "flip_mission_counters": self.flip_mission_counters, "flip_mission_targets": self.flip_mission_targets,
            "is_bonus_turn": self.is_bonus_turn, "game_over": self.game_over
        }
        self.send_to_server(payload)
        
        if self.game_over:
            self.end_game_popup()

    def after_turn_events(self):
        # 寿命
        if self.settings.get("life"):
            for r in range(len(self.board)):
                for c in range(len(self.board[0])):
                    if self.board[r][c] > 0 and self.ages[r][c] is not None:
                        self.ages[r][c] += 1
                        if self.ages[r][c] >= self.settings["life_length"]:
                            self.board[r][c] = EMPTY
                            self.ages[r][c] = self.health[r][c] = None
        # 重力
        if self.settings.get("gravity") and (self.turn_count % self.settings.get("gravity_interval", 5) == 0):
            g_dir = self.next_gravity or random.choice(list(GRAVITY_DIRECTIONS.keys()))
            self.apply_gravity(g_dir)
        # 鏡
        if self.settings.get("mirror") and (self.turn_count % self.settings.get("mirror_interval", 5) == 0):
            m_side = self.next_mirror or random.choice(MIRROR_SIDES)
            self.apply_mirror(m_side)
        # 無差別破壊
        if self.settings.get("destroy") and (self.turn_count % self.settings.get("destroy_interval", 5) == 0):
            for r, c in self.next_destroy_targets:
                if self.in_bounds(r, c) and self.board[r][c] != HOLE:
                    self.board[r][c] = EMPTY
                    self.ages[r][c] = self.health[r][c] = None

    def apply_gravity(self, d_name):
        dr, dc = GRAVITY_DIRECTIONS[d_name]
        pieces = []
        for r in range(len(self.board)):
            for c in range(len(self.board[0])):
                if self.board[r][c] > 0:
                    pieces.append((r, c, self.board[r][c], self.ages[r][c], self.health[r][c]))
                    self.board[r][c] = EMPTY
                    self.ages[r][c] = self.health[r][c] = None
        pieces.sort(key=lambda x: x[0]*dr + x[1]*dc, reverse=True)
        for r, c, val, age, hp in pieces:
            cr, cc = r, c
            while True:
                nr, nc = cr + dr, cc + dc
                if not self.in_bounds(nr, nc) or self.board[nr][nc] != EMPTY: break
                cr, cc = nr, nc
            self.board[cr][cc] = val
            self.ages[cr][cc], self.health[cr][cc] = age, hp

    def apply_mirror(self, side):
        rows, cols = len(self.board), len(self.board[0])
        if side == "上半分":
            for r in range(rows // 2): self.board[rows-1-r] = self.board[r][:]
        elif side == "下半分":
            for r in range(rows // 2): self.board[r] = self.board[rows-1-r][:]
        elif side == "左半分":
            for r in range(rows):
                for c in range(cols // 2): self.board[r][cols-1-c] = self.board[r][c]
        elif side == "右半分":
            for r in range(rows):
                for c in range(cols // 2): self.board[r][c] = self.board[r][cols-1-c]

    def prepare_predictions(self):
        self.next_gravity = random.choice(list(GRAVITY_DIRECTIONS.keys())) if self.settings.get("gravity") else None
        self.next_mirror = random.choice(MIRROR_SIDES) if self.settings.get("mirror") else None
        if self.settings.get("destroy"):
            cand = [(r, c) for r in range(len(self.board)) for c in range(len(self.board[0])) if self.board[r][c] != HOLE]
            self.next_destroy_targets = random.sample(cand, min(self.settings.get("destroy_count", 1), len(cand))) if cand else []

    def is_blackout_active(self):
        if not self.settings.get("blackout"): return False
        cycle = self.turn_count % (self.settings["blackout_interval"] + self.settings["blackout_duration"])
        return cycle >= self.settings["blackout_interval"]

    def count_pieces(self):
        scores = {1: 0, 2: 0}
        for r in range(len(self.board)):
            for c in range(len(self.board[0])):
                p = self.board[r][c]
                if p > 0: scores[p] += self.cell_scores[r][c] if self.settings.get("total_score") else 1
        return scores

    def end_game_popup(self):
        scores = self.count_pieces()
        rev = self.settings.get("reverse_judgment", False)
        win_val = min(scores.values()) if rev else max(scores.values())
        winners = [p for p, s in scores.items() if s == win_val]
        msg = f"【ゲーム終了】\n黒: {scores[1]}点\n白: {scores[2]}点\n勝者: " + "&".join([self.player_name(w) for w in winners]) + " ってわけ！"
        messagebox.showinfo("終了", msg)

    # ==========================================
    # 🎨 画面描画とクリックイベント
    # ==========================================
    def on_canvas_click(self, event):
        if not self.game_started:
            self.handle_preview_click(event)
            return
        cw, ch = self.canvas.winfo_width(), self.canvas.winfo_height()
        rows, cols = len(self.board), len(self.board[0])
        size = min(cw // cols, ch // rows)
        col = (event.x - (cw - size * cols) // 2) // size
        row = (event.y - (ch - size * rows) // 2) // size
        if 0 <= row < rows and 0 <= col < cols: self.place_piece(row, col)

    def handle_preview_click(self, event):
        cw, ch = self.canvas.winfo_width() or 740, self.canvas.winfo_height() or 680
        rows, cols = self.vars["rows"].get(), self.vars["cols"].get()
        size = min(cw // cols, ch // rows)
        col = (event.x - (cw - size * cols) // 2) // size
        row = (event.y - (ch - size * rows) // 2) // size
        if 0 <= row < rows and 0 <= col < cols:
            if (row, col) in self.initial_cells(): return
            if (row, col) in self.holes: self.holes.remove((row, col))
            else: self.holes.add((row, col))
            self.vars["hole_count"].set(len(self.holes))
            self.draw_preview_board()

    def draw_preview_board(self):
        self.canvas.delete("all")
        cw, ch = self.canvas.winfo_width() or 740, self.canvas.winfo_height() or 680
        rows, cols = self.vars["rows"].get(), self.vars["cols"].get()
        size = min(cw // cols, ch // rows)
        ox, oy = (cw - size * cols) // 2, (ch - size * rows) // 2
        initial = self.initial_cells()
        for r in range(rows):
            for c in range(cols):
                x1, y1 = ox + c * size, oy + r * size
                bg = "#3a3a3a" if (r, c) in self.holes else ("#11732e" if (r, c) in initial else "#0b8f3a")
                self.canvas.create_rectangle(x1, y1, x1+size, y1+size, fill=bg, outline="#05401a")
                if (r, c) in initial:
                    self.canvas.create_oval(x1+4, y1+4, x1+size-4, y1+size-4, fill=PLAYER_COLORS[initial[(r, c)]][1], outline="")
        self.status.config(text="【設定中】 マスクリックで穴を配置/消去できるってわけ")

    def draw_board(self):
        self.canvas.delete("all")
        cw, ch = self.canvas.winfo_width(), self.canvas.winfo_height()
        rows, cols = len(self.board), len(self.board[0])
        size = min(cw // cols, ch // rows)
        ox, oy = (cw - size * cols) // 2, (ch - size * rows) // 2
        blackout = self.is_blackout_active()
        valid_moves = self.valid_moves(self.current_player()) if not self.game_over else []

        for r in range(rows):
            for c in range(cols):
                x1, y1 = ox + c * size, oy + r * size
                bg = "black" if blackout else ("#222" if self.board[r][c] == HOLE else "#0b8f3a")
                self.canvas.create_rectangle(x1, y1, x1+size, y1+size, fill=bg, outline="#05401a" if not blackout else "black")
                if blackout: continue
                
                # 石の描画
                if self.board[r][c] > 0:
                    p = self.board[r][c]
                    self.canvas.create_oval(x1+4, y1+4, x1+size-4, y1+size-4, fill=PLAYER_COLORS[p][1], outline="")
                    txt = ""
                    if self.settings.get("life") and self.settings.get("life_show") and self.ages[r][c] is not None:
                        txt += f"L{self.settings['life_length'] - self.ages[r][c]}"
                    if self.settings.get("health") and self.settings.get("health_show") and self.health[r][c] is not None:
                        txt += f"\nH{self.health[r][c]}"
                    if txt and size >= 28:
                        self.canvas.create_text(x1+size//2, y1+size//2, text=txt, fill=PLAYER_COLORS[p][2], font=("Arial", max(7, size//5)))
                
                # 置ける場所ヒント (自分の手番のときだけ表示する)
                elif (r, c) in valid_moves and self.current_player() == self.my_player_number:
                    self.canvas.create_oval(x1+size//2-4, y1+size//2-4, x1+size//2+4, y1+size//2+4, fill="#ffffff", outline="")
                
                # 総得点スコア表示
                if self.settings.get("total_score") and self.settings.get("total_score_show") and self.board[r][c] != HOLE and size >= 20:
                    self.canvas.create_text(x1+10, y1+10, text=str(self.cell_scores[r][c]), fill="#90e6a7", font=("Arial", max(6, size//6)))
        self.update_info_panel()

    def update_info_panel(self):
        scores = self.count_pieces()
        p = self.current_player()
        role = "あなた" if p == self.my_player_number else "あいて"
        
        info_str = f"ターン数: {self.turn_count}\n現在の手番: {self.player_name(p)} ({role})\nあなたの色: {self.player_name(self.my_player_number) if self.my_player_number else '未定'}\n\n【現在の得点】\n黒: {scores[1]}点\n白: {scores[2]}点\n"
        
        info_str += "\n【次回のイベント予告】\n"
        info_str += f"重力: {self.next_gravity or 'なし'}\n"
        info_str += f"鏡: {self.next_mirror or 'なし'}\n"
        info_str += f"破壊マス数: {len(self.next_destroy_targets) if self.next_destroy_targets else 'なし'}\n"

        if self.settings.get("flip_limit_event"):
            info_str += f"\n【ミッション】\n黒: あと{self.flip_mission_counters[0]}T内に {self.flip_mission_targets[0]}個反転\n白: あと{self.flip_mission_counters[1]}T内に {self.flip_mission_targets[1]}個反転\n"
        
        self.game_info.config(text=info_str)
        self.status.config(text=f"【対局中】 {self.player_name(p)}の番（{role}）ってわけ" if not self.game_over else "ゲーム終了！")


if __name__ == "__main__":
    root = tk.Tk()
    app = OthelloApp(root)
    root.mainloop()
