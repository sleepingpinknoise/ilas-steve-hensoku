def show_board(board):
    for row in board:
        print(" ".join(row))

def get_flips(board, x, y, player):
    opponent = 'W' if player == 'B' else 'B'
    flips = []
    for dx in range(-1, 2):
        for dy in range(-1, 2):
            if dx == 0 and dy == 0:
                continue
            nx = x + dx
            ny = y + dy
            line = []
            while 0 <= nx < 8 and 0 <= ny < 8:
                if board[ny][nx] == opponent:
                    line.append((nx, ny))
                elif board[ny][nx] == player:
                    flips = flips + line
                    break
                else:
                    break
                nx = nx + dx
                ny = ny + dy
    return flips

board = [['.' for _ in range(8)] for _ in range(8)]
board[3][3] = 'W'
board[3][4] = 'B'
board[4][3] = 'B'
board[4][4] = 'W'

current_player = 'B'

while True:
    show_board(board)
    print("Current player:", current_player)

    text = input("Enter your move (x y): ")
    parts = text.split()
    x = int(parts[0])
    y = int(parts[1])

    if x < 0 or x >= 8 or y < 0 or y >= 8 or board[y][x] != '.':
        print("Invalid move. Try again.")
        continue

    flips = get_flips(board, x, y, current_player)
    if len(flips) == 0:
        print("Invalid move. Try again.")
        continue

    board[y][x] = current_player
    for fx, fy in flips:
        board[fy][fx] = current_player

    if current_player == 'B':
        current_player = 'W'
    else:
        current_player = 'B'