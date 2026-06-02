import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType
import os
import random
from flask import Flask
import threading
import sys

VK_TOKEN = os.environ.get('VK_TOKEN')

if not VK_TOKEN:
    print("НЕТ ТОКЕНА!")
    sys.exit(1)

app = Flask(__name__)

@app.route('/')
def health():
    return "OK"


class SimpleBot:
    def __init__(self):
        print("Инициализация VK...")
        self.session = vk_api.VkApi(token=VK_TOKEN)
        self.vk = self.session.get_api()
        self.longpoll = VkLongPoll(self.session)
        self.bot_id = self.vk.users.get()[0]['id']
        print(f"Бот запущен! ID: {self.bot_id}")

    def send(self, peer_id, msg):
        try:
            self.vk.messages.send(peer_id=peer_id, message=msg, random_id=random.randint(1, 9999999))
        except Exception as e:
            print(f"Ошибка: {e}")

    def run(self):
        print("Слушаю сообщения...")
        for event in self.longpoll.listen():
            if event.type == VkEventType.MESSAGE_NEW and event.user_id != self.bot_id:
                text = event.text.strip().lower()
                if text == "!тест":
                    self.send(event.peer_id, "✅ Бот работает!")


def run_web():
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)


if __name__ == "__main__":
    print("Запуск...")
    threading.Thread(target=run_web, daemon=True).start()
    bot = SimpleBot()
    bot.run()
