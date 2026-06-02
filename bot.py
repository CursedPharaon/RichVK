import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType
import random
import os
import time
from datetime import datetime
from supabase import create_client, Client
from flask import Flask
import threading
import sys

print("1. Начало загрузки...")

VK_TOKEN = os.environ.get('VK_TOKEN')
SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY')
ADMIN_ID = os.environ.get('ADMIN_ID', '0')

print("2. Переменные получены")

if not VK_TOKEN:
    print("ОШИБКА: VK_TOKEN не найден")
    sys.exit(1)

if not SUPABASE_URL or not SUPABASE_KEY:
    print("ОШИБКА: SUPABASE_URL или SUPABASE_KEY не найдены")
    sys.exit(1)

print("3. Подключаюсь к Supabase...")
try:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    print("4. Supabase подключён")
except Exception as e:
    print(f"ОШИБКА Supabase: {e}")
    sys.exit(1)

app = Flask(__name__)

@app.route('/')
def health():
    return "OK"

print("5. Создаю класс бота...")


class RichBot:
    def __init__(self):
        print("6. Инициализация бота...")
        try:
            self.vk_session = vk_api.VkApi(token=VK_TOKEN)
            self.vk = self.vk_session.get_api()
            self.longpoll = VkLongPoll(self.vk_session)
            self.bot_id = self.vk.users.get()[0]['id']
            print(f"7. Бот подключён, ID: {self.bot_id}")
        except Exception as e:
            print(f"ОШИБКА VK: {e}")
            sys.exit(1)

    def send_message(self, peer_id, text):
        try:
            self.vk.messages.send(peer_id=peer_id, message=text[:4000], random_id=random.randint(1, 999999))
        except Exception as e:
            print(f"Send error: {e}")

    def run(self):
        print("8. Бот запущен и слушает сообщения!")
        for event in self.longpoll.listen():
            if event.type == VkEventType.MESSAGE_NEW and event.user_id != self.bot_id:
                text = event.text.strip()
                if text == "!тест":
                    self.send_message(event.peer_id, "✅ Бот работает!")


def run_web():
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)


print("9. Запуск потоков...")
threading.Thread(target=run_web, daemon=True).start()
print("10. Создание бота...")
bot = RichBot()
print("11. Запуск бота...")
bot.run()
