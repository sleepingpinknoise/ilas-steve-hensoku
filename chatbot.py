import os
from dotenv import load_dotenv
import chatgpt

load_dotenv(".env")
chatbot = chatgpt.ChatBot(api_key = os.environ.get("OPENAI_API_KEY"))
system_setting = input("Please set system: ").strip()
chatbot.set_system_setting(system_setting)
print("Please input something after '>'")
while True:
    prompt = input("> ").strip()
    if prompt == "reset":
        chatbot.reset_message()
    elif prompt == "quit":
        break
    else:
        message = chatbot.chat(prompt)
        print(message)
