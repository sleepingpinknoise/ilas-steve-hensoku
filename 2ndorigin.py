import tkinter as tk
from tkinter import messagebox
import json
import threading
import websocket  

SERVER_URL = "wss://ilas-steve-hensoku.onrender.com/ws"

EMPTY = 0
BLACK = 1
WHITE = 2

BOARD_SIZE = 8
CELL_SIZE = 70

DIRECTIONS = [
    (-1, -1), (-1, 0), (-1, 1),
    (0, -1),           (0, 1),
    (1, -1),  (1, 0),  (1, 1),
]


class OthelloApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Python Othello (オンライン対戦版)")

        self.board = []
        self.current_player = BLACK
        self.game_started = False
        self.game_over = False
        self.ws = None
        self.my_color = EMPTY  

        self.title_label = tk.Label(
            root,
            text="Python Othello",
            font=("Arial", 22, "bold"),
        )
        self.title_label.pack(pady=(12, 4))

        self.canvas = tk.Canvas(
            root,
            width=BOARD_SIZE * CELL_SIZE,
            height=BOARD_SIZE * CELL_SIZE,
            bg="#0b8f3a",
        )
        self.canvas.pack()

        self.status = tk.Label(root, font=("Arial", 14))
        self.status.pack(pady=8)

        self.button_frame = tk.Frame(root)
        self.button_frame.pack(pady=(0, 12))

        self.start_button = tk.Button(
            self.button_frame,
            text="サーバーに接続",  
            font=("Arial", 13),
            command=self.connect_server, 
        )
        self.start_button.pack(side=tk.LEFT, padx=5)

        self.reset_button = tk.Button(
            self.button_frame,
            text="リセット",
            font=("Arial", 13),
            command=self.reset_to_start,
        )
        self.reset_button.pack(side=tk.LEFT, padx=5)

        self.canvas.bind("<Button-1>", self.on_click)
        self.draw_start_screen()

    def connect_server(self):
        self.status.config(text="サーバーに接続中...")
        self.start_button.config(state=tk.DISABLED)
        
        def run():
            try:
                self.ws = websocket.create_connection(SERVER_URL)
                print("Renderサーバーに繋がったよ！")
                threading.Thread(target=self.listen_server, daemon=True).start()
            except Exception as e:
                print("接続エラー:", e)
                self.root.after(0, lambda: self.status.config(text="サーバー接続失敗。URLを確認してね"))
                self.root.after(0, lambda: self.start_button.config(state=tk.NORMAL))

        threading.Thread(target=run, daemon=True).start()

   
    def listen_server(self):
        while True:
            try:
                response = self.ws.recv()
                data = json.loads(response)
                print("サーバーからデータ受信:", data)

             
                if "action" in data and data["action"] == "start":
                    self.root.after(0, self.start_game)
                    
                
                elif "row" in data and "col" in data:
                    row = data["row"]
                    col = data["col"]
                    
                    self.root.after(0, lambda r=row, c=col: self.remote_place_piece(r, c))

            except Exception as e:
                print("通信切断またはエラー:", e)
                break

        self.root.after(0, lambda: self.status.config(text="通信が切断されました"))

    def create_initial_board(self):
        board = [[EMPTY for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)]
        board[3][3] = WHITE
        board[3][4] = BLACK
        board[4][3] = BLACK
        board[4][4] = WHITE
        return board

    def start_game(self):
        self.board = self.create_initial_board()
        self.current_player = BLACK
        self.game_started = True
        self.game_over = False
        self.start_button.config(text="対局中", state=tk.DISABLED)
        self.draw_board()

    def reset_to_start(self):
        if self.ws:
            try:
                self.ws.close()
            except:
                pass
        self.board = []
        self.current_player = BLACK
        self.game_started = False
        self.game_over = False
        self.start_button.config(text="サーバーに接続", state=tk.NORMAL)
        self.draw_start_screen()

    def opponent(self, player):
        return WHITE if player == BLACK else BLACK

    def in_bounds(self, row, col):
        return 0 <= row < BOARD_SIZE and 0 <= col < BOARD_SIZE

    def get_flips(self, row, col, player):
        if self.board[row][col] != EMPTY:
            return []

        flips = []
        opponent = self.opponent(player)

        for dr, dc in DIRECTIONS:
            r, c = row + dr, col + dc
            line = []

            while self.in_bounds(r, c) and self.board[r][c] == opponent:
                line.append((r, c))
                r += dr
                c += dc

            if self.in_bounds(r, c) and self.board[r][c] == player and line:
                flips.extend(line)

        return flips

    def has_valid_move(self, player):
        for row in range(BOARD_SIZE):
            for col in range(BOARD_SIZE):
                if self.get_flips(row, col, player):
                    return True
        return False


    def place_piece(self, row, col):
        flips = self.get_flips(row, col, self.current_player)

        if not flips:
            self.status.config(text="そこには置けません")
            return False  

        self.board[row][col] = self.current_player

        for r, c in flips:
            self.board[r][c] = self.current_player

        self.current_player = self.opponent(self.current_player)

        if not self.has_valid_move(self.current_player):
            passed_player = "黒" if self.current_player == BLACK else "白"
            self.current_player = self.opponent(self.current_player)

            if not self.has_valid_move(self.current_player):
                self.end_game()
                return True

            self.draw_board()
            self.status.config(text=f"{passed_player}は置ける場所がないためパス")
            return True

        self.draw_board()
        return True  # 正常に置けたらTrueを返す

    def remote_place_piece(self, row, col):
        self.place_piece(row, col)

    def on_click(self, event):
        if not self.game_started:
            messagebox.showinfo("ゲーム開始前", "「サーバーに接続」ボタンを押してください。")
            return

        if self.game_over:
            messagebox.showinfo("ゲーム終了", "ゲームは終了しました。リセットで新しく始められます。")
            return

     
        row = event.y // CELL_SIZE
        col = event.x // CELL_SIZE

        if self.in_bounds(row, col):
          
            success = self.place_piece(row, col)
            if success and self.ws:
             
                data = {"row": row, "col": col}
                try:
                    self.ws.send(json.dumps(data))
                except Exception as e:
                    print("データ送信失敗:", e)

    def draw_start_screen(self):
        self.canvas.delete("all")
        self.canvas.create_rectangle(
            0, 0, BOARD_SIZE * CELL_SIZE, BOARD_SIZE * CELL_SIZE,
            fill="#0b8f3a", outline="",
        )

        for i in range(BOARD_SIZE + 1):
            pos = i * CELL_SIZE
            self.canvas.create_line(pos, 0, pos, BOARD_SIZE * CELL_SIZE, fill="black")
            self.canvas.create_line(0, pos, BOARD_SIZE * CELL_SIZE, pos, fill="black")

        self.canvas.create_text(
            BOARD_SIZE * CELL_SIZE // 2, BOARD_SIZE * CELL_SIZE // 2 - 20,
            text="オンラインオセロ", fill="white", font=("Arial", 28, "bold"),
        )
        self.canvas.create_text(
            BOARD_SIZE * CELL_SIZE // 2, BOARD_SIZE * CELL_SIZE // 2 + 28,
            text="下の「サーバーに接続」を押してください", fill="white", font=("Arial", 16),
        )
        self.status.config(text="待機中")

    def draw_board(self):
        self.canvas.delete("all")

        for row in range(BOARD_SIZE):
            for col in range(BOARD_SIZE):
                x1 = col * CELL_SIZE
                y1 = row * CELL_SIZE
                x2 = x1 + CELL_SIZE
                y2 = y1 + CELL_SIZE

                self.canvas.create_rectangle(
                    x1, y1, x2, y2, outline="black", fill="#0b8f3a",
                )

                piece = self.board[row][col]

                if piece != EMPTY:
                    color = "black" if piece == BLACK else "white"
                    self.canvas.create_oval(
                        x1 + 8, y1 + 8, x2 - 8, y2 - 8,
                        fill=color, outline="black",
                    )

        if self.game_over:
            return

        player_text = "黒" if self.current_player == BLACK else "white"
        black_count, white_count = self.count_pieces()
        self.status.config(
            text=f"ゲーム中  手番: {player_text}   黒: {black_count}  白: {white_count}"
        )

    def count_pieces(self):
        black = sum(row.count(BLACK) for row in self.board)
        white = sum(row.count(WHITE) for row in self.board)
        return black, white

    def end_game(self):
        self.game_over = True
        self.start_button.config(text="ゲーム終了", state=tk.DISABLED)
        self.draw_board()

        black, white = self.count_pieces()

        if black > white:
            result = "黒の勝ち"
        elif white > black:
            result = "白の勝ち"
        else:
            result = "引き分け"

        result_text = f"ゲーム終了\n{result}\n黒: {black}  白: {white}"
        self.status.config(text=result_text.replace("\n", "   "))

        self.canvas.create_rectangle(
            80, 205, BOARD_SIZE * CELL_SIZE - 80, 355,
            fill="white", outline="black", width=2,
        )
        self.canvas.create_text(
            BOARD_SIZE * CELL_SIZE // 2, 250,
            text="ゲーム終了", fill="black", font=("Arial", 28, "bold"),
        )
        self.canvas.create_text(
            BOARD_SIZE * CELL_SIZE // 2, 305,
            text=f"{result}   黒: {black}  白: {white}", fill="black", font=("Arial", 16),
        )
        messagebox.showinfo("ゲーム終了", result_text)


if __name__ == "__main__":
    root = tk.Tk()
    app = OthelloApp(root)
    root.mainloop()これ動かない
