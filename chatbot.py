import os
from dotenv import load_dotenv
import chatgpt

load_dotenv(".env")
chatbot = chatgpt.ChatBot(api_key = os.environ.get("OPENAI_API_KEY"))
system_setting = """
あなたは、多彩な特殊イベントが発生する「特殊オセロ」の少し強いAIプレイヤーです。
与えられた盤面状況、有効な特殊ルール、そして自分が置くことのできる座標（合法手）のリストから、一手を選択してください。

# 思考の指針
1. 勝利条件の確認: 通常ルール（得点・石を最大化）か、「判定逆転」ルール（得点・石を最小化）かを必ず確認して思考を切り替えてください。
2. マス目の価値の計算: 「総得点オセロ」が有効な場合、単に角（コーナー）を狙うだけでなく、各マスに配置されたスコアを重視してください。
3. 特殊イベントの先読み: 「寿命」「体力」「重力」「鏡」「無差別破壊」などのイベントやその予告がある場合、自分の着手が次のターン以降にどう変化するか（消滅や移動など）を予測してください。
4. ミッションの狙い目: 「反転個数指定」がある場合、ぴったりその数を反転させて連続手番（ボーナス）を狙える手を強力に評価してください。

# 出力フォーマット
出力は以下のセクションで構成してください。プログラムが自動処理するため、フォーマットは絶対に崩さないでください。

[MOVE]
row, col
[/MOVE]

※「row, col」の部分には、選択したマスの行番号と列番号（例: 3, 4）を半角数字とカンマだけで出力してください。余計な文字列（スペースや日本語）は一切含めないでください。
"""
chatbot.set_system_setting(system_setting)
def ai_move(self):
    if not self.game_started or self.game_over or self.is_human_turn():
        return
    
    player = self.current_player()
    moves = self.valid_moves(player)
    
    if not moves:
        return

    # 1. 盤面を文字列化する
    board_str = "\n".join([" ".join(map(str, row)) for row in self.board])
    
    # 2. 得点表を文字列化する（総得点ルール時）
    score_str = ""
    if self.settings.get("total_score"):
        score_str = "各マスの得点表:\n" + "\n".join([" ".join(map(str, row)) for row in self.cell_scores])

    # 3. LLMに渡すメッセージを作る
    prompt = f"""現在の盤面:{board_str}{score_str}
    あなたはプレイヤー {player} です。
    あなたの合法手（置ける座標 row, col）は以下の通りです:
    {moves}
    現在の特殊ルール:
    - 判定逆転: {self.settings.get("reverse_judgment")}
    - 次の重力予告: {self.next_gravity}
    - 破壊予告座標: {self.next_destroy_targets}
    合法手の中から最も有利な手を1つ選び、 [MOVE]row, col[/MOVE] の形式で出力してください。"""
    message = chatbot.chat(prompt)

    # --- ここでLLMのAPIを呼び出して prompt を渡す ---
    # response = chatbot.chat(prompt)
    
    # --- 返ってきた文字列から正規表現などで座標を抽出して置く ---
    # row, col = 抽出した座標
    # self.place_piece(row, col)