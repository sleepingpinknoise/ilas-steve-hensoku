import tkinter as tk

EMPTY = 0
BLACK = 1
WHITE = 2

BOARD_SIZE = 8
CELL_SIZE = 70

DIRECTIONS = [
    (-1, -1), (-1, 0), (-1, 1),
    (0, -1),           (0, 1),
    (1, -1),  (1, 0),  (1, 1),
]


class OthelloApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Python Othello")

        self.board = [[EMPTY for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)]
        self.current_player = BLACK

        self.canvas = tk.Canvas(
            root,
            width=BOARD_SIZE * CELL_SIZE,
            height=BOARD_SIZE * CELL_SIZE,
            bg="green"
        )
        self.canvas.pack()

        self.status = tk.Label(root, font=("Arial", 14))
        self.status.pack(pady=8)

        self.canvas.bind("<Button-1>", self.on_click)

        self.setup_board()
        self.draw_board()

    def setup_board(self):
        self.board[3][3] = WHITE
        self.board[3][4] = BLACK
        self.board[4][3] = BLACK
        self.board[4][4] = WHITE

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
            return

        self.board[row][col] = self.current_player

        for r, c in flips:
            self.board[r][c] = self.current_player

        self.current_player = self.opponent(self.current_player)

        if not self.has_valid_move(self.current_player):
            self.current_player = self.opponent(self.current_player)

            if not self.has_valid_move(self.current_player):
                self.end_game()

        self.draw_board()

    def on_click(self, event):
        row = event.y // CELL_SIZE
        col = event.x // CELL_SIZE

        if self.in_bounds(row, col):
            self.place_piece(row, col)

    def draw_board(self):
        self.canvas.delete("all")

        for row in range(BOARD_SIZE):
            for col in range(BOARD_SIZE):
                x1 = col * CELL_SIZE
                y1 = row * CELL_SIZE
                x2 = x1 + CELL_SIZE
                y2 = y1 + CELL_SIZE

                self.canvas.create_rectangle(
                    x1, y1, x2, y2,
                    outline="black",
                    fill="#0b8f3a"
                )

                piece = self.board[row][col]

                if piece != EMPTY:
                    color = "black" if piece == BLACK else "white"
                    self.canvas.create_oval(
                        x1 + 8, y1 + 8,
                        x2 - 8, y2 - 8,
                        fill=color,
                        outline="black"
                    )

        player_text = "黒" if self.current_player == BLACK else "白"
        black_count, white_count = self.count_pieces()

        self.status.config(
            text=f"現在の手番: {player_text}   黒: {black_count}  白: {white_count}"
        )

    def count_pieces(self):
        black = sum(row.count(BLACK) for row in self.board)
        white = sum(row.count(WHITE) for row in self.board)
        return black, white

    def end_game(self):
        black, white = self.count_pieces()

        if black > white:
            result = "黒の勝ち"
        elif white > black:
            result = "白の勝ち"
        else:
            result = "引き分け"

        self.status.config(text=f"ゲーム終了: {result}  黒: {black}  白: {white}")


if __name__ == "__main__":
    root = tk.Tk()
    app = OthelloApp(root)
    root.mainloop()