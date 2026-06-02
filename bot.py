import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType
import random
import os
import time
import re
from datetime import datetime, timedelta
from supabase import create_client, Client
from flask import Flask
import threading
import sys
import traceback

# Получаем переменные окружения
VK_TOKEN = os.environ.get('VK_TOKEN')
SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY')
ADMIN_ID = int(os.environ.get('ADMIN_ID', 0))

# Проверка наличия переменных
if not VK_TOKEN:
    print("ОШИБКА: VK_TOKEN не установлен!")
    sys.exit(1)
if not SUPABASE_URL or not SUPABASE_KEY:
    print("ОШИБКА: SUPABASE_URL или SUPABASE_KEY не установлены!")
    sys.exit(1)

print(f"Переменные окружения загружены")
print(f"ADMIN_ID: {ADMIN_ID}")

# Инициализация Supabase
try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    print("Supabase подключен")
except Exception as e:
    print(f"Ошибка подключения к Supabase: {e}")
    sys.exit(1)

# Flask приложение
app = Flask(__name__)

@app.route('/')
def health_check():
    return "Бот Рич работает!"

@app.route('/health')
def health():
    return "OK", 200

class RichBot:
    def __init__(self):
        print("Инициализация бота...")
        
        # Кеш для имен пользователей
        self.user_name_cache = {}
        
        self.valid_mafias = ['Братки', 'Мафиози', 'Гангстеры']
        
        self.hack_items = [
            {'name': 'Макдональдс', 'chance': 80, 'reward': (100, 300)},
            {'name': 'Магазин у дома', 'chance': 70, 'reward': (300, 600)},
            {'name': 'Банк', 'chance': 50, 'reward': (1000, 2500)},
            {'name': 'Пентагон', 'chance': 30, 'reward': (5000, 10000)},
            {'name': 'Центробанк', 'chance': 15, 'reward': (15000, 30000)},
            {'name': 'Криптобиржа', 'chance': 10, 'reward': (50000, 100000)},
        ]
        
        try:
            self.vk_session = vk_api.VkApi(token=VK_TOKEN)
            self.vk = self.vk_session.get_api()
            self.longpoll = VkLongPoll(self.vk_session)
        except Exception as e:
            print(f"Ошибка инициализации VK API: {e}")
            sys.exit(1)
        
        self.start_money = 1000
        self.currency_symbol = "Ричей"
        
        try:
            bot_info = self.vk.users.get()[0]
            self.bot_id = bot_info['id']
            self.bot_screen_name = bot_info.get('screen_name', 'rich_bot')
            print(f"Бот запущен: @{self.bot_screen_name} (ID: {self.bot_id})")
        except Exception as e:
            print(f"Ошибка: {e}")
            self.bot_id = 0
            self.bot_screen_name = 'rich_bot'
        
        self.jobs = {
            'программист': {'money': (500, 1000), 'energy': 20},
            'грузчик': {'money': (200, 500), 'energy': 15},
            'таксист': {'money': (300, 600), 'energy': 15},
            'официант': {'money': (200, 400), 'energy': 10},
            'шаурмист': {'money': (400, 700), 'energy': 20}
        }
        
        self.commands = {
            'начать': self.cmd_start,
            'баланс': self.cmd_balance,
            'работы': self.cmd_jobs,
            'работа': self.cmd_work,
            'казино': self.cmd_casino,
            'создать_клан': self.cmd_create_clan,
            'вступить': self.cmd_join_clan,
            'клан': self.cmd_clan_info,
            'пополнить_казну': self.cmd_donate_clan,
            'покинуть_клан': self.cmd_leave_clan,
            'выйти_из_клана': self.cmd_leave_clan,
            'битва_кланов': self.cmd_clan_war,
            'принять_битву': self.cmd_accept_war,
            'прокачать_клан': self.cmd_upgrade_clan,
            'мафия': self.cmd_mafia,
            'вступить_в_мафию': self.cmd_join_mafia,
            'покинуть_мафию': self.cmd_leave_mafia,
            'ограбить': self.cmd_rob,
            'дуэль': self.cmd_duel,
            'принять_дуэль': self.cmd_accept_duel,
            'отклонить_дуэль': self.cmd_decline_duel,
            'топ': self.cmd_top,
            'админ': self.cmd_admin,
            'помощь': self.cmd_help,
            'команды': self.cmd_help,
            'передать': self.cmd_transfer,
            'бизнес': self.cmd_business,
            'купитьбизнес': self.cmd_buy_business,
            'собрать': self.cmd_collect_business,
            'шкаф': self.cmd_wardrobe,
            'надеть': self.cmd_wear,
            'снять': self.cmd_unwear,
            'выдатьодежду': self.cmd_give_clothes_to_all,
            'рассылка': self.cmd_mass_mailing,
            'ркоин': self.cmd_richcoin,
            'купить_ркоин': self.cmd_buy_richcoin,
            'продать_ркоин': self.cmd_sell_richcoin,
            'взлом': self.cmd_hack,
        }
        
        print("Бот Рич запущен!")
    
    # ============================ ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ ============================
    
    def get_user_name(self, user_id):
        """Получить имя пользователя для кликабельного упоминания"""
        if user_id in self.user_name_cache:
            return self.user_name_cache[user_id]
        
        try:
            user_info = self.vk.users.get(user_ids=user_id, fields='screen_name')[0]
            screen_name = user_info.get('screen_name')
            if screen_name:
                name = screen_name
            else:
                first_name = user_info.get('first_name', f'id{user_id}')
                name = first_name
            
            self.user_name_cache[user_id] = name
            return name
        except Exception as e:
            print(f"Ошибка получения имени для {user_id}: {e}")
            return f'id{user_id}'
    
    def make_mention(self, user_id):
        """Создать кликабельное упоминание пользователя"""
        name = self.get_user_name(user_id)
        return f"[id{user_id}|@{name}]"
    
    def get_reply_user_id(self, event):
        """Получить ID пользователя, на чьё сообщение ответили"""
        try:
            if hasattr(event, 'reply_message') and event.reply_message:
                return event.reply_message['from_id']
            return None
        except:
            return None
    
    def get_user(self, user_id):
        try:
            result = supabase.table('users').select('*').eq('user_id', user_id).execute()
            
            if not result.data:
                new_user = {
                    'user_id': user_id,
                    'money': self.start_money,
                    'energy': 100,
                    'job': None,
                    'clan': None,
                    'mafia': None,
                    'level': 1,
                    'exp': 0,
                    'duels_won': 0,
                    'duels_lost': 0,
                    'last_business_collect': datetime.now().isoformat(),
                    'richcoin': 0,
                    'last_hack': None,
                    'last_help': None,
                    'last_rob': None,
                    'last_work': None
                }
                supabase.table('users').insert(new_user).execute()
                
                result = supabase.table('users').select('*').eq('user_id', user_id).execute()
                if result.data:
                    return result.data[0]
                else:
                    print(f"Не удалось создать пользователя {user_id}")
                    return None
            
            return result.data[0]
        except Exception as e:
            print(f"Ошибка get_user для {user_id}: {e}")
            traceback.print_exc()
            return None
    
    def update_user(self, user_id, data):
        try:
            supabase.table('users').update(data).eq('user_id', user_id).execute()
        except Exception as e:
            print(f"Ошибка update_user: {e}")
    
    def get_richcoin_price(self):
        try:
            result = supabase.table('richcoin').select('price').order('id', desc=True).limit(1).execute()
            if result.data:
                return result.data[0]['price']
            return 25000000
        except:
            return 25000000
    
    def set_richcoin_price(self, price):
        try:
            supabase.table('richcoin').insert({'price': price, 'last_updated': datetime.now().isoformat()}).execute()
            return True
        except:
            return False
    
    def send_message(self, peer_id, message):
        try:
            if not message:
                message = "⚠️ Произошла ошибка"
            if len(message) > 4000:
                message = message[:3997] + "..."
            
            self.vk.messages.send(
                peer_id=peer_id,
                message=message,
                random_id=random.randint(1, 9999999)
            )
        except Exception as e:
            print(f"Ошибка отправки: {e}")
    
    def send_message_to_user(self, user_id, message):
        try:
            if not message:
                message = "⚠️ Произошла ошибка"
            if len(message) > 4000:
                message = message[:3997] + "..."
            
            self.vk.messages.send(
                user_id=user_id,
                message=message,
                random_id=random.randint(1, 9999999)
            )
        except Exception as e:
            print(f"Ошибка отправки лички: {e}")
    
    def check_blacklist(self, user_id):
        try:
            result = supabase.table('blacklist').select('*').eq('user_id', user_id).execute()
            return len(result.data) > 0
        except:
            return False
    
    def check_cooldown(self, user_id, action, minutes):
        try:
            user = self.get_user(user_id)
            if not user:
                return True, 0
            last_time_str = user.get(f'last_{action}')
            if last_time_str:
                last_time = datetime.fromisoformat(last_time_str.replace('Z', '+00:00'))
                if datetime.now() - last_time < timedelta(minutes=minutes):
                    remaining = timedelta(minutes=minutes) - (datetime.now() - last_time)
                    return False, int(remaining.total_seconds() // 60)
            return True, 0
        except:
            return True, 0
    
    # ============================ РИЧКОИН ============================
    def cmd_richcoin(self, peer_id, user_id, args):
        price = self.get_richcoin_price()
        user = self.get_user(user_id)
        if not user:
            self.send_message(peer_id, "❌ Ошибка! Попробуйте позже")
            return
        user_rc = user.get('richcoin', 0)
        self.send_message(peer_id, f"🪙 РИЧКОИН\n\nТекущая цена: {price} {self.currency_symbol}\nУ вас: {user_rc} RC\n\nКупить: !купить_ркоин [количество]\nПродать: !продать_ркоин [количество]")
    
    def cmd_buy_richcoin(self, peer_id, user_id, args):
        if not args:
            self.send_message(peer_id, "Укажите количество: !купить_ркоин 10")
            return
        try:
            amount = int(args[0])
        except:
            self.send_message(peer_id, "Количество должно быть числом!")
            return
        if amount <= 0:
            self.send_message(peer_id, "Количество должно быть положительным!")
            return
        user = self.get_user(user_id)
        if not user:
            self.send_message(peer_id, "❌ Ошибка!")
            return
        price = self.get_richcoin_price()
        total_cost = price * amount
        if user['money'] < total_cost:
            self.send_message(peer_id, f"Не хватает денег! Нужно {total_cost} {self.currency_symbol}")
            return
        self.update_user(user_id, {
            'money': user['money'] - total_cost,
            'richcoin': user.get('richcoin', 0) + amount
        })
        new_price = int(price * 1.05)
        self.set_richcoin_price(new_price)
        self.send_message(peer_id, f"✅ {self.make_mention(user_id)} купил {amount} RC за {total_cost} {self.currency_symbol}!\n📈 Цена Ричкоина выросла до {new_price} {self.currency_symbol}")
    
    def cmd_sell_richcoin(self, peer_id, user_id, args):
        if not args:
            self.send_message(peer_id, "Укажите количество: !продать_ркоин 10")
            return
        try:
            amount = int(args[0])
        except:
            self.send_message(peer_id, "Количество должно быть числом!")
            return
        if amount <= 0:
            self.send_message(peer_id, "Количество должно быть положительным!")
            return
        user = self.get_user(user_id)
        if not user:
            self.send_message(peer_id, "❌ Ошибка!")
            return
        user_rc = user.get('richcoin', 0)
        if user_rc < amount:
            self.send_message(peer_id, f"У вас только {user_rc} RC!")
            return
        price = self.get_richcoin_price()
        total_income = int(price * amount * 0.95)
        self.update_user(user_id, {
            'money': user['money'] + total_income,
            'richcoin': user_rc - amount
        })
        new_price = int(price * 0.95)
        self.set_richcoin_price(new_price)
        self.send_message(peer_id, f"✅ {self.make_mention(user_id)} продал {amount} RC за {total_income} {self.currency_symbol}!\n📉 Цена Ричкоина упала до {new_price} {self.currency_symbol}")
    
    # ============================ ВЗЛОМ ============================
    def cmd_hack(self, peer_id, user_id, args):
        can_hack, remaining = self.check_cooldown(user_id, 'hack', 60)
        if not can_hack:
            self.send_message(peer_id, f"⏰ Взлом доступен через {remaining} мин!")
            return
        user = self.get_user(user_id)
        if not user:
            self.send_message(peer_id, "❌ Ошибка!")
            return
        item = random.choice(self.hack_items)
        roll = random.randint(1, 100)
        if roll <= item['chance']:
            reward = random.randint(item['reward'][0], item['reward'][1])
            self.update_user(user_id, {
                'money': user['money'] + reward,
                'last_hack': datetime.now().isoformat()
            })
            self.send_message(peer_id, f"💻 {self.make_mention(user_id)} взломал {item['name']}!\n💰 +{reward} {self.currency_symbol}")
        else:
            self.update_user(user_id, {'last_hack': datetime.now().isoformat()})
            self.send_message(peer_id, f"💻 {self.make_mention(user_id)} пытался взломать {item['name']}, но сработала сигнализация! 🚨\n❌ Ничего не получено")
    
    # ============================ МАФИЯ ============================
    def cmd_mafia(self, peer_id, user_id, args):
        user = self.get_user(user_id)
        if not user:
            self.send_message(peer_id, "❌ Ошибка!")
            return
        if not user['mafia']:
            text = "🔫 ДОСТУПНЫЕ МАФИИ:\n\n"
            for m in self.valid_mafias:
                members = supabase.table('mafia_members').select('*').eq('mafia_name', m).execute()
                text += f"• {m} - 👥 {len(members.data)} участников\n"
            text += f"\n💡 Вступить: !вступить_в_мафию [название]"
            self.send_message(peer_id, text)
            return
        mafia = supabase.table('mafia').select('*').eq('name', user['mafia']).execute()
        members = supabase.table('mafia_members').select('*').eq('mafia_name', user['mafia']).execute()
        self.send_message(peer_id, f"🔫 Мафия: {user['mafia']}\n👥 Участников: {len(members.data)}\n💰 Общак: {mafia.data[0]['money'] if mafia.data else 0}\n\n💡 Покинуть: !покинуть_мафию")
    
    def cmd_join_mafia(self, peer_id, user_id, args):
        if not args:
            self.send_message(peer_id, f"❌ Название мафии! Доступны: {', '.join(self.valid_mafias)}")
            return
        mafia_name = ' '.join(args)
        if mafia_name not in self.valid_mafias:
            self.send_message(peer_id, f"❌ Мафия '{mafia_name}' не существует!\n✅ Доступны: {', '.join(self.valid_mafias)}")
            return
        user = self.get_user(user_id)
        if not user:
            self.send_message(peer_id, "❌ Ошибка!")
            return
        if user['mafia']:
            self.send_message(peer_id, "❌ Ты уже в мафии! Сначала покинь: !покинуть_мафию")
            return
        mafia = supabase.table('mafia').select('*').eq('name', mafia_name).execute()
        if not mafia.data:
            supabase.table('mafia').insert({'name': mafia_name, 'boss': user_id, 'money': 0}).execute()
        supabase.table('mafia_members').insert({'mafia_name': mafia_name, 'user_id': user_id}).execute()
        self.update_user(user_id, {'mafia': mafia_name})
        self.send_message(peer_id, f"✅ {self.make_mention(user_id)} вступил в мафию '{mafia_name}'!")
    
    def cmd_leave_mafia(self, peer_id, user_id, args):
        user = self.get_user(user_id)
        if not user:
            self.send_message(peer_id, "❌ Ошибка!")
            return
        if not user['mafia']:
            self.send_message(peer_id, "❌ Вы не состоите в мафии!")
            return
        mafia_name = user['mafia']
        supabase.table('mafia_members').delete().eq('mafia_name', mafia_name).eq('user_id', user_id).execute()
        remaining = supabase.table('mafia_members').select('*').eq('mafia_name', mafia_name).execute()
        if not remaining.data:
            supabase.table('mafia').delete().eq('name', mafia_name).execute()
            self.send_message(peer_id, f"✅ Мафия '{mafia_name}' распущена!")
        else:
            self.send_message(peer_id, f"✅ {self.make_mention(user_id)} покинул мафию '{mafia_name}'!")
        self.update_user(user_id, {'mafia': None})
    
    # ============================ БИТВЫ КЛАНОВ ============================
    def cmd_clan_war(self, peer_id, user_id, args):
        if len(args) < 2:
            self.send_message(peer_id, "❌ Использование: !битва_кланов [название_клана] [ставка]")
            return
        clan_name = ' '.join(args[:-1])
        try:
            bet = int(args[-1])
        except:
            self.send_message(peer_id, "❌ Ставка должна быть числом!")
            return
        user = self.get_user(user_id)
        if not user:
            self.send_message(peer_id, "❌ Ошибка!")
            return
        if not user['clan']:
            self.send_message(peer_id, "❌ Вы не состоите в клане!")
            return
        attacker_clan = user['clan']
        if attacker_clan.lower() == clan_name.lower():
            self.send_message(peer_id, "❌ Нельзя вызвать свой же клан!")
            return
        target_clan = supabase.table('clans').select('*').eq('name', clan_name).execute()
        if not target_clan.data:
            self.send_message(peer_id, "❌ Такой клан не найден!")
            return
        if bet <= 0:
            self.send_message(peer_id, "❌ Ставка должна быть положительной!")
            return
        attacker_clan_data = supabase.table('clans').select('*').eq('name', attacker_clan).execute()
        if not attacker_clan_data.data or attacker_clan_data.data[0]['money'] < bet:
            self.send_message(peer_id, f"❌ В казне вашего клана недостаточно денег! Нужно {bet}")
            return
        supabase.table('clan_wars').insert({
            'clan1': attacker_clan,
            'clan2': clan_name,
            'bet': bet,
            'status': 'pending'
        }).execute()
        supabase.table('clans').update({'money': attacker_clan_data.data[0]['money'] - bet}).eq('name', attacker_clan).execute()
        self.send_message(peer_id, f"⚔️ Клан '{attacker_clan}' вызвал клан '{clan_name}' на битву!\n💰 Ставка: {bet}\n⏳ У клана '{clan_name}' есть время принять битву: !принять_битву {attacker_clan} {bet}")
    
    def cmd_accept_war(self, peer_id, user_id, args):
        if len(args) < 2:
            self.send_message(peer_id, "❌ Использование: !принять_битву [название_клана] [ставка]")
            return
        clan_name = ' '.join(args[:-1])
        try:
            bet = int(args[-1])
        except:
            self.send_message(peer_id, "❌ Ставка должна быть числом!")
            return
        user = self.get_user(user_id)
        if not user:
            self.send_message(peer_id, "❌ Ошибка!")
            return
        if not user['clan']:
            self.send_message(peer_id, "❌ Вы не состоите в клане!")
            return
        defender_clan = user['clan']
        war = supabase.table('clan_wars').select('*').eq('clan1', clan_name).eq('clan2', defender_clan).eq('bet', bet).eq('status', 'pending').execute()
        if not war.data:
            self.send_message(peer_id, "❌ Нет активных вызовов на битву!")
            return
        war_data = war.data[0]
        defender_clan_data = supabase.table('clans').select('*').eq('name', defender_clan).execute()
        if not defender_clan_data.data or defender_clan_data.data[0]['money'] < bet:
            self.send_message(peer_id, f"❌ В казне вашего клана недостаточно денег для ставки {bet}!")
            return
        supabase.table('clans').update({'money': defender_clan_data.data[0]['money'] - bet}).eq('name', defender_clan).execute()
        supabase.table('clan_wars').update({'status': 'active'}).eq('id', war_data['id']).execute()
        attacker_clan_data = supabase.table('clans').select('*').eq('name', clan_name).execute()
        attacker_power = (attacker_clan_data.data[0].get('level', 1) * 100 + attacker_clan_data.data[0].get('attack', 10) + attacker_clan_data.data[0].get('defense', 10))
        defender_power = (defender_clan_data.data[0].get('level', 1) * 100 + defender_clan_data.data[0].get('attack', 10) + defender_clan_data.data[0].get('defense', 10))
        attacker_roll = random.randint(80, 120)
        defender_roll = random.randint(80, 120)
        attacker_final = attacker_power * attacker_roll / 100
        defender_final = defender_power * defender_roll / 100
        total_bet = bet * 2
        if attacker_final > defender_final:
            winner = clan_name
            winner_money = supabase.table('clans').select('money').eq('name', clan_name).execute().data[0]['money'] + total_bet
            supabase.table('clans').update({'money': winner_money}).eq('name', clan_name).execute()
            self.send_message(peer_id, f"⚔️ БИТВА КЛАНОВ ЗАВЕРШЕНА!\n\n🏆 Победитель: {clan_name}\n💰 Выигрыш: {total_bet}")
        else:
            winner = defender_clan
            winner_money = supabase.table('clans').select('money').eq('name', defender_clan).execute().data[0]['money'] + total_bet
            supabase.table('clans').update({'money': winner_money}).eq('name', defender_clan).execute()
            self.send_message(peer_id, f"⚔️ БИТВА КЛАНОВ ЗАВЕРШЕНА!\n\n🏆 Победитель: {defender_clan}\n💰 Выигрыш: {total_bet}")
        supabase.table('clan_wars').update({'winner': winner, 'status': 'completed'}).eq('id', war_data['id']).execute()
        supabase.table('clans').update({'exp': supabase.table('clans').select('exp').eq('name', winner).execute().data[0].get('exp', 0) + 100}).eq('name', winner).execute()
    
    def cmd_upgrade_clan(self, peer_id, user_id, args):
        if not args:
            self.send_message(peer_id, "❌ Использование: !прокачать_клан [атака/защита]")
            return
        upgrade_type = args[0].lower()
        if upgrade_type not in ['атака', 'защита']:
            self.send_message(peer_id, "❌ Можно улучшить только 'атака' или 'защита'")
            return
        user = self.get_user(user_id)
        if not user:
            self.send_message(peer_id, "❌ Ошибка!")
            return
        if not user['clan']:
            self.send_message(peer_id, "❌ Вы не состоите в клане!")
            return
        clan_data = supabase.table('clans').select('*').eq('name', user['clan']).execute()
        if not clan_data.data:
            self.send_message(peer_id, "❌ Клан не найден!")
            return
        if clan_data.data[0]['owner'] != user_id:
            self.send_message(peer_id, "❌ Только владелец клана может улучшать его!")
            return
        current_value = clan_data.data[0].get(upgrade_type, 10)
        upgrade_cost = 5000 * current_value
        if clan_data.data[0]['money'] < upgrade_cost:
            self.send_message(peer_id, f"❌ В казне клана недостаточно денег! Нужно {upgrade_cost}")
            return
        new_value = current_value + 5
        supabase.table('clans').update({
            'money': clan_data.data[0]['money'] - upgrade_cost,
            upgrade_type: new_value
        }).eq('name', user['clan']).execute()
        self.send_message(peer_id, f"✅ Клан '{user['clan']}' улучшил {upgrade_type} с {current_value} до {new_value}!\n💰 Стоимость: {upgrade_cost}")
    
    # ============================ ПЕРЕДАЧА ДЕНЕГ ============================
    def cmd_transfer(self, peer_id, user_id, args, reply_user_id=None):
        target_id = reply_user_id
        
        if not target_id and len(args) >= 1:
            for arg in args:
                if arg.isdigit():
                    target_id = int(arg)
                    break
                mention = re.search(r'id(\d+)', arg)
                if mention:
                    target_id = int(mention.group(1))
                    break
        
        if not target_id:
            self.send_message(peer_id, "❌ Укажите ID получателя или ответьте на его сообщение!\nПример: !передать 123456 1000")
            return
        
        amount = None
        for arg in args:
            if arg.isdigit() and int(arg) != target_id:
                amount = int(arg)
                break
        
        if not amount:
            self.send_message(peer_id, "❌ Укажите сумму!\nПример: !передать 123456 1000")
            return
        
        if target_id == user_id:
            self.send_message(peer_id, "❌ Нельзя передать самому себе!")
            return
        if amount <= 0:
            self.send_message(peer_id, "❌ Сумма должна быть положительной!")
            return
        sender = self.get_user(user_id)
        receiver = self.get_user(target_id)
        if not sender or not receiver:
            self.send_message(peer_id, "❌ Ошибка при получении данных!")
            return
        if sender['money'] < amount:
            self.send_message(peer_id, f"❌ Не хватает денег! У вас {sender['money']} {self.currency_symbol}")
            return
        self.update_user(user_id, {'money': sender['money'] - amount})
        self.update_user(target_id, {'money': receiver['money'] + amount})
        self.send_message(peer_id, f"✅ {self.make_mention(user_id)} передал {self.make_mention(target_id)} {amount} {self.currency_symbol}!")
        self.send_message_to_user(target_id, f"💰 {self.make_mention(user_id)} передал вам {amount} {self.currency_symbol}!")
    
    # ============================ ДУЭЛЬ ============================
    def cmd_duel(self, peer_id, user_id, args, reply_user_id=None):
        opponent_id = reply_user_id
        
        if not opponent_id and len(args) >= 1:
            for arg in args:
                if arg.isdigit():
                    opponent_id = int(arg)
                    break
                mention = re.search(r'id(\d+)', arg)
                if mention:
                    opponent_id = int(mention.group(1))
                    break
        
        if not opponent_id:
            self.send_message(peer_id, "❌ Укажите ID соперника или ответьте на его сообщение!\nПример: !дуэль 123456 1000")
            return
        
        bet = None
        for arg in args:
            if arg.isdigit() and int(arg) != opponent_id:
                bet = int(arg)
                break
        
        if not bet:
            self.send_message(peer_id, "❌ Укажите ставку!\nПример: !дуэль 123456 1000")
            return
        
        if opponent_id == user_id:
            self.send_message(peer_id, "❌ Нельзя вызвать самого себя!")
            return
        user = self.get_user(user_id)
        opponent = self.get_user(opponent_id)
        if not user or not opponent:
            self.send_message(peer_id, "❌ Игрок не найден!")
            return
        if bet <= 0 or bet > user['money']:
            self.send_message(peer_id, f"❌ Неверная ставка! У тебя {user['money']}")
            return
        supabase.table('duels').insert({
            'challenger': user_id,
            'opponent': opponent_id,
            'bet': bet,
            'status': 'pending'
        }).execute()
        self.send_message(peer_id, f"⚔️ {self.make_mention(user_id)} вызвал {self.make_mention(opponent_id)} на дуэль! Ставка: {bet}\nДля принятия: !принять_дуэль {bet}")
    
    def cmd_accept_duel(self, peer_id, user_id, args):
        if not args:
            self.send_message(peer_id, "❌ Укажи ставку")
            return
        try:
            bet = int(args[0])
        except:
            self.send_message(peer_id, "❌ Ставка должна быть числом!")
            return
        duel = supabase.table('duels').select('*').eq('opponent', user_id).eq('bet', bet).eq('status', 'pending').execute()
        if not duel.data:
            self.send_message(peer_id, "❌ Нет активных приглашений!")
            return
        duel_data = duel.data[0]
        challenger_id = duel_data['challenger']
        challenger = self.get_user(challenger_id)
        opponent = self.get_user(user_id)
        if not challenger or not opponent:
            self.send_message(peer_id, "❌ Ошибка!")
            return
        if bet > opponent['money']:
            self.send_message(peer_id, f"❌ {self.make_mention(user_id)}, не хватает денег! Нужно {bet}")
            return
        self.update_user(challenger_id, {'money': challenger['money'] - bet})
        self.update_user(user_id, {'money': opponent['money'] - bet})
        challenger_power = random.randint(1, 100) + challenger['level'] * 5
        opponent_power = random.randint(1, 100) + opponent['level'] * 5
        winner_id = challenger_id if challenger_power > opponent_power else user_id
        winner_prize = bet * 2
        winner = self.get_user(winner_id)
        self.update_user(winner_id, {'money': winner['money'] + winner_prize})
        if winner_id == challenger_id:
            self.update_user(challenger_id, {'duels_won': challenger['duels_won'] + 1})
            self.update_user(user_id, {'duels_lost': opponent['duels_lost'] + 1})
        else:
            self.update_user(user_id, {'duels_won': opponent['duels_won'] + 1})
            self.update_user(challenger_id, {'duels_lost': challenger['duels_lost'] + 1})
        supabase.table('duels').update({'status': 'completed'}).eq('duel_id', duel_data['duel_id']).execute()
        self.send_message(peer_id, f"⚔️ ПОБЕДИТЕЛЬ ДУЭЛИ: {self.make_mention(winner_id)}\n💰 Выигрыш: {winner_prize}")
    
    def cmd_decline_duel(self, peer_id, user_id, args):
        if not args:
            self.send_message(peer_id, "❌ Укажи ставку")
            return
        try:
            bet = int(args[0])
        except:
            self.send_message(peer_id, "❌ Ставка должна быть числом!")
            return
        result = supabase.table('duels').update({'status': 'declined'}).eq('opponent', user_id).eq('bet', bet).eq('status', 'pending').execute()
        if result.data:
            challenger_id = result.data[0]['challenger']
            self.send_message(peer_id, f"❌ {self.make_mention(user_id)} отклонил дуэль с {self.make_mention(challenger_id)}!")
    
    def cmd_rob(self, peer_id, user_id, args, reply_user_id=None):
        target_id = reply_user_id
        
        if not target_id and len(args) >= 1:
            for arg in args:
                if arg.isdigit():
                    target_id = int(arg)
                    break
                mention = re.search(r'id(\d+)', arg)
                if mention:
                    target_id = int(mention.group(1))
                    break
        
        if not target_id:
            self.send_message(peer_id, "❌ Укажите ID жертвы или ответьте на его сообщение!\nПример: !ограбить 123456")
            return
        
        if target_id == user_id:
            self.send_message(peer_id, "❌ Нельзя грабить себя!")
            return
        user = self.get_user(user_id)
        target = self.get_user(target_id)
        if not user or not target:
            self.send_message(peer_id, "❌ Ошибка!")
            return
        can_rob, remaining = self.check_cooldown(user_id, 'rob', 30)
        if not can_rob:
            self.send_message(peer_id, f"⏰ {self.make_mention(user_id)}, следующий грабеж через {remaining} мин")
            return
        success = random.random() < 0.6
        if success:
            rob_amount = random.randint(50, min(300, target['money']))
            if rob_amount > target['money']:
                rob_amount = target['money']
            self.update_user(user_id, {'money': user['money'] + rob_amount, 'last_rob': datetime.now().isoformat()})
            self.update_user(target_id, {'money': target['money'] - rob_amount})
            self.send_message(peer_id, f"🔫 {self.make_mention(user_id)} ограбил {self.make_mention(target_id)} на {rob_amount}!")
        else:
            penalty = random.randint(50, 150)
            new_money = max(0, user['money'] - penalty)
            self.update_user(user_id, {'money': new_money, 'last_rob': datetime.now().isoformat()})
            self.send_message(peer_id, f"❌ {self.make_mention(user_id)} провалил грабеж! Штраф {penalty}!")
    
    # ============================ ОСТАЛЬНЫЕ КОМАНДЫ ============================
    def cmd_help(self, peer_id, user_id, args):
        can_help, remaining = self.check_cooldown(user_id, 'help', 0.17)
        if not can_help:
            return
        
        self.send_message(
            peer_id,
            f"📜 **КОМАНДЫ БОТА RICH:**\n\n"
            f"💰 !баланс - проверить баланс\n"
            f"💼 !работы - список работ\n"
            f"💪 !работа [название] - работать\n"
            f"🎰 !казино [орёл_решка/кости] [ставка]\n"
            f"👥 !создать_клан [название]\n"
            f"🤝 !вступить [клан]\n"
            f"🏆 !клан - инфо о клане\n"
            f"🚪 !покинуть_клан\n"
            f"⚔️ !битва_кланов [клан] [ставка]\n"
            f"📈 !прокачать_клан [атака/защита]\n"
            f"🔫 !мафия / !вступить_в_мафию / !покинуть_мафию\n"
            f"⚔️ !дуэль [ставка] (ответом на сообщение)\n"
            f"💀 !ограбить (ответом на сообщение)\n"
            f"💻 !взлом - раз в час\n"
            f"🪙 !ркоин / !купить_ркоин / !продать_ркоин\n"
            f"📊 !топ - топ игроков\n"
            f"💸 !передать [сумма] (ответом на сообщение)\n"
            f"🏢 !бизнес / !купитьбизнес / !собрать\n"
            f"👔 !шкаф / !надеть / !снять\n\n"
            f"💡 В беседах используй ! перед командой\n"
            f"💡 Для команд с пользователем - ответь на его сообщение!"
        )
        
        self.update_user(user_id, {'last_help': datetime.now().isoformat()})
    
    def cmd_start(self, peer_id, user_id, args):
        user = self.get_user(user_id)
        if not user:
            self.send_message(peer_id, "❌ Ошибка! Попробуйте позже")
            return
        self.send_message(peer_id, f"🌟 Добро пожаловать в Rich, {self.make_mention(user_id)}!\n\n💰 Баланс: {user['money']}\n⚡ Энергия: {user['energy']}%\n🏆 Уровень: {user['level']}\n\n📜 Команды: !помощь")
    
    def cmd_balance(self, peer_id, user_id, args):
        user = self.get_user(user_id)
        if not user:
            self.send_message(peer_id, "❌ Ошибка! Попробуйте позже")
            return
        self.send_message(peer_id, f"💰 Баланс {self.make_mention(user_id)}: {user['money']} {self.currency_symbol}\n⚡ Энергия: {user['energy']}%\n🏆 Уровень: {user['level']}\n🪙 Ричкоин: {user.get('richcoin', 0)} RC")
    
    def cmd_jobs(self, peer_id, user_id, args):
        text = "📋 Работы:\n\n"
        for name, data in self.jobs.items():
            text += f"📌 {name}\n   💰 {data['money'][0]}-{data['money'][1]} {self.currency_symbol}\n   ⚡ Тратит: {data['energy']} энергии\n\n"
        self.send_message(peer_id, text)
    
    def cmd_work(self, peer_id, user_id, args):
        if not args:
            self.send_message(peer_id, "❌ Укажи работу: !работа программист")
            return
        job_name = args[0].lower()
        if job_name not in self.jobs:
            self.send_message(peer_id, "❌ Нет такой работы")
            return
        user = self.get_user(user_id)
        if not user:
            self.send_message(peer_id, "❌ Ошибка!")
            return
        if user['job'] != job_name:
            self.update_user(user_id, {'job': job_name})
            self.send_message(peer_id, f"✅ {self.make_mention(user_id)}, ты устроился на {job_name}!")
            return
        can_work, remaining = self.check_cooldown(user_id, 'work', 10)
        if not can_work:
            self.send_message(peer_id, f"⏰ {self.make_mention(user_id)}, отдыхай! Следующая работа через {remaining} мин")
            return
        if user['energy'] < self.jobs[job_name]['energy']:
            self.send_message(peer_id, f"❌ {self.make_mention(user_id)}, мало энергии! Нужно {self.jobs[job_name]['energy']}")
            return
        earned = random.randint(*self.jobs[job_name]['money'])
        new_money = user['money'] + earned
        new_energy = user['energy'] - self.jobs[job_name]['energy']
        new_exp = user['exp'] + 50
        new_level = user['level']
        if new_exp >= new_level * 100:
            new_level += 1
            new_energy = 100
            level_msg = f"\n\n🎉 УРОВЕНЬ {new_level}! Энергия восстановлена!"
        else:
            level_msg = ""
        self.update_user(user_id, {
            'money': new_money,
            'energy': new_energy,
            'exp': new_exp,
            'level': new_level,
            'last_work': datetime.now().isoformat()
        })
        self.send_message(peer_id, f"✅ {self.make_mention(user_id)} поработал на {job_name}!\n💰 +{earned}\n⚡ Энергия: {new_energy}%{level_msg}")
    
    def cmd_casino(self, peer_id, user_id, args):
        if len(args) < 2:
            self.send_message(peer_id, "❌ Использование: !казино [орёл_решка/кости] [ставка]")
            return
        game = args[0].lower()
        try:
            bet = int(args[1])
        except:
            self.send_message(peer_id, "❌ Ставка - число!")
            return
        user = self.get_user(user_id)
        if not user:
            self.send_message(peer_id, "❌ Ошибка!")
            return
        if bet <= 0 or bet > user['money']:
            self.send_message(peer_id, f"❌ Неверная ставка! У тебя {user['money']}")
            return
        result = ""
        new_money = user['money']
        if game in ["орёл_решка", "орел_решка"]:
            if len(args) < 3:
                self.send_message(peer_id, "❌ Укажи орёл или решка!")
                return
            choice = args[2].lower()
            if choice not in ['орёл', 'орел', 'решка']:
                self.send_message(peer_id, "❌ Выбери орёл или решка!")
                return
            coin = random.choice(['орёл', 'решка'])
            win = (choice == coin)
            if win:
                new_money = user['money'] + bet
                result = f"🎲 Выпал {coin}! Ты выиграл {bet}!"
            else:
                new_money = user['money'] - bet
                result = f"🎲 Выпал {coin}! Ты проиграл {bet}!"
        elif game == "кости":
            user_roll = random.randint(1, 6)
            bot_roll = random.randint(1, 6)
            if user_roll > bot_roll:
                new_money = user['money'] + bet
                result = f"🎲 {user_roll} vs {bot_roll}\n✅ Выиграл {bet}!"
            elif user_roll < bot_roll:
                new_money = user['money'] - bet
                result = f"🎲 {user_roll} vs {bot_roll}\n❌ Проиграл {bet}!"
            else:
                result = f"🎲 {user_roll} vs {bot_roll}\n🤝 Ничья!"
        else:
            self.send_message(peer_id, "❌ Игры: орёл_решка, кости")
            return
        if new_money != user['money']:
            self.update_user(user_id, {'money': new_money})
        self.send_message(peer_id, f"🎰 {self.make_mention(user_id)}\n{result}\n💰 Новый баланс: {new_money}")
    
    def cmd_create_clan(self, peer_id, user_id, args):
        if not args:
            self.send_message(peer_id, "❌ Название клана!")
            return
        clan_name = ' '.join(args)
        existing = supabase.table('clans').select('*').eq('name', clan_name).execute()
        if existing.data:
            self.send_message(peer_id, "❌ Клан уже есть!")
            return
        user = self.get_user(user_id)
        if not user:
            self.send_message(peer_id, "❌ Ошибка!")
            return
        if user['clan']:
            self.send_message(peer_id, "❌ Ты уже в клане!")
            return
        if user['money'] < 5000:
            self.send_message(peer_id, f"❌ Нужно 5000! У тебя {user['money']}")
            return
        supabase.table('clans').insert({'name': clan_name, 'owner': user_id, 'money': 0, 'level': 1, 'exp': 0, 'attack': 10, 'defense': 10}).execute()
        supabase.table('clan_members').insert({'clan_name': clan_name, 'user_id': user_id}).execute()
        self.update_user(user_id, {'money': user['money'] - 5000, 'clan': clan_name})
        self.send_message(peer_id, f"✅ Клан '{clan_name}' создан! Владелец: {self.make_mention(user_id)}")

def cmd_donate_clan(self, peer_id, user_id, args):
    """!пополнить_клан [сумма] - пополнить казну клана"""
    if not args:
        self.send_message(peer_id, "❌ Укажите сумму: !пополнить_клан 1000")
        return
    
    try:
        amount = int(args[0])
    except:
        self.send_message(peer_id, "❌ Сумма должна быть числом!")
        return
    
    if amount <= 0:
        self.send_message(peer_id, "❌ Сумма должна быть положительной!")
        return
    
    user = self.get_user(user_id)
    if not user:
        self.send_message(peer_id, "❌ Ошибка!")
        return
    
    if not user['clan']:
        self.send_message(peer_id, "❌ Вы не состоите в клане!")
        return
    
    if user['money'] < amount:
        self.send_message(peer_id, f"❌ Не хватает денег! У вас {user['money']} {self.currency_symbol}")
        return
    
    # Пополняем казну клана
    clan = supabase.table('clans').select('*').eq('name', user['clan']).execute()
    if not clan.data:
        self.send_message(peer_id, "❌ Клан не найден!")
        return
    
    new_money = clan.data[0]['money'] + amount
    supabase.table('clans').update({'money': new_money}).eq('name', user['clan']).execute()
    
    # Списываем деньги у игрока
    self.update_user(user_id, {'money': user['money'] - amount})
    
    self.send_message(peer_id, f"✅ {self.make_mention(user_id)} пополнил казну клана '{user['clan']}' на {amount} {self.currency_symbol}!\n💰 Теперь в казне: {new_money} {self.currency_symbol}")
    
    def cmd_join_clan(self, peer_id, user_id, args):
        if not args:
            self.send_message(peer_id, "❌ Название клана!")
            return
        clan_name = ' '.join(args)
        clan = supabase.table('clans').select('*').eq('name', clan_name).execute()
        if not clan.data:
            self.send_message(peer_id, "❌ Клан не найден!")
            return
        user = self.get_user(user_id)
        if not user:
            self.send_message(peer_id, "❌ Ошибка!")
            return
        if user['clan']:
            self.send_message(peer_id, "❌ Ты уже в клане!")
            return
        supabase.table('clan_members').insert({'clan_name': clan_name, 'user_id': user_id}).execute()
        self.update_user(user_id, {'clan': clan_name})
        self.send_message(peer_id, f"✅ {self.make_mention(user_id)} вступил в клан '{clan_name}'!")
    
    def cmd_clan_info(self, peer_id, user_id, args):
        user = self.get_user(user_id)
        if not user:
            self.send_message(peer_id, "❌ Ошибка!")
            return
        if not user['clan']:
            self.send_message(peer_id, "❌ Ты не в клане!")
            return
        clan = supabase.table('clans').select('*').eq('name', user['clan']).execute()
        members = supabase.table('clan_members').select('*').eq('clan_name', user['clan']).execute()
        if not clan.data:
            self.send_message(peer_id, "❌ Клан не найден!")
            return
        clan_data = clan.data[0]
        self.send_message(peer_id, f"🏆 Клан: {user['clan']}\n👑 Владелец: {self.make_mention(clan_data['owner'])}\n👥 Участников: {len(members.data)}\n💰 Казна: {clan_data['money']}\n📈 Уровень: {clan_data.get('level', 1)}\n⚔️ Атака: {clan_data.get('attack', 10)} | 🛡 Защита: {clan_data.get('defense', 10)}")
    
    def cmd_leave_clan(self, peer_id, user_id, args):
        user = self.get_user(user_id)
        if not user:
            self.send_message(peer_id, "❌ Ошибка!")
            return
        if not user['clan']:
            self.send_message(peer_id, "❌ Вы не состоите в клане!")
            return
        clan_name = user['clan']
        clan = supabase.table('clans').select('*').eq('name', clan_name).execute()
        if not clan.data:
            self.update_user(user_id, {'clan': None})
            self.send_message(peer_id, "✅ Вы покинули несуществующий клан")
            return
        clan_data = clan.data[0]
        if clan_data['owner'] == user_id:
            members = supabase.table('clan_members').select('*').eq('clan_name', clan_name).execute()
            supabase.table('clan_members').delete().eq('clan_name', clan_name).eq('user_id', user_id).execute()
            remaining_members = supabase.table('clan_members').select('*').eq('clan_name', clan_name).execute()
            if remaining_members.data:
                new_owner_id = remaining_members.data[0]['user_id']
                supabase.table('clans').update({'owner': new_owner_id}).eq('name', clan_name).execute()
                self.send_message(peer_id, f"👑 Вы покинули клан '{clan_name}'!\n🏆 Новый владелец: {self.make_mention(new_owner_id)}")
            else:
                supabase.table('clans').delete().eq('name', clan_name).execute()
                self.send_message(peer_id, f"✅ Клан '{clan_name}' распущен")
        else:
            supabase.table('clan_members').delete().eq('clan_name', clan_name).eq('user_id', user_id).execute()
            self.send_message(peer_id, f"✅ {self.make_mention(user_id)} покинул клан '{clan_name}'!")
        self.update_user(user_id, {'clan': None})
    
    def cmd_top(self, peer_id, user_id, args):
        users = supabase.table('users').select('user_id, money, level').order('money', desc=True).limit(10).execute()
        if not users.data:
            self.send_message(peer_id, "📊 Пока нет игроков!")
            return
        text = "🏆 ТОП-10 БОГАЧЕЙ:\n\n"
        for i, user in enumerate(users.data, 1):
            text += f"{i}. {self.make_mention(user['user_id'])} - {user['money']} {self.currency_symbol} (Ур. {user['level']})\n"
        self.send_message(peer_id, text)
    
    # ============================ БИЗНЕС ============================
    def cmd_business(self, peer_id, user_id, args):
        try:
            businesses = supabase.table('businesses').select('*').execute()
            my_businesses = supabase.table('user_businesses').select('*, businesses(*)').eq('user_id', user_id).execute()
            text = "🏢 ДОСТУПНЫЕ БИЗНЕСЫ:\n\n"
            for biz in businesses.data:
                text += f"📌 {biz['name']}\n   💰 Цена: {biz['price']} {self.currency_symbol}\n   ⏱ Доход в час: {biz['income_per_hour']} {self.currency_symbol}\n\n"
            if my_businesses.data:
                text += "━━━━━━━━━━━━━━━━\n📋 ВАШИ БИЗНЕСЫ:\n"
                for mb in my_businesses.data:
                    biz = mb['businesses']
                    last_collected = datetime.fromisoformat(mb['last_collected'].replace('Z', '+00:00'))
                    hours_passed = (datetime.now() - last_collected).total_seconds() / 3600
                    pending = int(biz['income_per_hour'] * hours_passed)
                    text += f"   • {biz['name']} - +{pending} (готово)\n"
                text += f"\n💡 Собрать доход: !собрать"
            else:
                text += "\n❌ У вас нет бизнесов. Купить: !купитьбизнес [название]"
            self.send_message(peer_id, text)
        except Exception as e:
            print(f"Ошибка в бизнес: {e}")
            self.send_message(peer_id, "❌ Ошибка при загрузке бизнесов!")
    
    def cmd_buy_business(self, peer_id, user_id, args):
        if not args:
            self.send_message(peer_id, "❌ Укажите название бизнеса!")
            return
        biz_name = ' '.join(args).lower()
        business = supabase.table('businesses').select('*').ilike('name', f'%{biz_name}%').execute()
        if not business.data:
            self.send_message(peer_id, "❌ Бизнес не найден!")
            return
        biz = business.data[0]
        user = self.get_user(user_id)
        if not user:
            self.send_message(peer_id, "❌ Ошибка!")
            return
        existing = supabase.table('user_businesses').select('*').eq('user_id', user_id).eq('business_id', biz['id']).execute()
        if existing.data:
            self.send_message(peer_id, f"❌ У вас уже есть {biz['name']}!")
            return
        if user['money'] < biz['price']:
            self.send_message(peer_id, f"❌ Не хватает денег! Нужно {biz['price']}")
            return
        self.update_user(user_id, {'money': user['money'] - biz['price']})
        supabase.table('user_businesses').insert({'user_id': user_id, 'business_id': biz['id'], 'last_collected': datetime.now().isoformat()}).execute()
        self.send_message(peer_id, f"✅ {self.make_mention(user_id)} купил бизнес {biz['name']} за {biz['price']}!")
    
    def cmd_collect_business(self, peer_id, user_id, args):
        my_businesses = supabase.table('user_businesses').select('*, businesses(*)').eq('user_id', user_id).execute()
        if not my_businesses.data:
            self.send_message(peer_id, "❌ У вас нет бизнесов!")
            return
        user = self.get_user(user_id)
        if not user:
            self.send_message(peer_id, "❌ Ошибка!")
            return
        total_income = 0
        for mb in my_businesses.data:
            biz = mb['businesses']
            last_collected = datetime.fromisoformat(mb['last_collected'].replace('Z', '+00:00'))
            hours_passed = (datetime.now() - last_collected).total_seconds() / 3600
            hours_to_collect = min(hours_passed, 24)
            income = int(biz['income_per_hour'] * hours_to_collect)
            total_income += income
            supabase.table('user_businesses').update({'last_collected': datetime.now().isoformat()}).eq('user_id', user_id).eq('business_id', biz['id']).execute()
        if total_income > 0:
            self.update_user(user_id, {'money': user['money'] + total_income})
            self.send_message(peer_id, f"💰 {self.make_mention(user_id)} собрал {total_income} {self.currency_symbol} с бизнесов!")
        else:
            self.send_message(peer_id, "⏰ Накоплений пока нет.")
    
    # ============================ ОДЕЖДА ============================
    def get_user_clothes(self, user_id):
        result = supabase.table('user_clothes').select('*, clothes(*)').eq('user_id', user_id).execute()
        return result.data
    
    def give_clothes_to_user(self, user_id, clothes_name):
        clothes = supabase.table('clothes').select('*').ilike('name', clothes_name).execute()
        if not clothes.data:
            clothes = supabase.table('clothes').select('*').ilike('name', f'%{clothes_name}%').execute()
        if not clothes.data:
            return False, "Одежда не найдена"
        cloth = clothes.data[0]
        existing = supabase.table('user_clothes').select('*').eq('user_id', user_id).eq('clothes_id', cloth['id']).execute()
        if existing.data:
            return False, f"У пользователя уже есть {cloth['name']}"
        supabase.table('user_clothes').insert({'user_id': user_id, 'clothes_id': cloth['id'], 'equipped': False}).execute()
        self.send_message_to_user(user_id, f"🎁 Вам выдана одежда: {cloth['name']}!")
        return True, cloth['name']
    
    def cmd_wardrobe(self, peer_id, user_id, args):
        user_clothes = self.get_user_clothes(user_id)
        if not user_clothes:
            self.send_message(peer_id, "❌ У вас нет одежды! Администратор может выдать: !админ одежда [id] [название]")
            return
        text = "👔 ВАШ ГАРДЕРОБ:\n\n"
        equipped = []
        not_equipped = []
        for item in user_clothes:
            if item.get('equipped'):
                equipped.append(item['clothes']['name'])
            else:
                not_equipped.append(item['clothes']['name'])
        if equipped:
            text += "✅ НАДЕТО НА ВАС:\n"
            for name in equipped:
                text += f"   • {name}\n"
            text += "\n"
        if not_equipped:
            text += "📦 В ШКАФУ:\n"
            for name in not_equipped:
                text += f"   • {name}\n"
        text += "\n💡 Надеть: !надеть [название]\n💡 Снять: !снять [название]"
        self.send_message(peer_id, text)
    
    def cmd_wear(self, peer_id, user_id, args):
        if not args:
            self.send_message(peer_id, "❌ Укажите название одежды!")
            return
        clothes_name = ' '.join(args).lower()
        user_clothes = self.get_user_clothes(user_id)
        if not user_clothes:
            self.send_message(peer_id, "❌ У вас нет одежды!")
            return
        found_cloth = None
        for uc in user_clothes:
            if clothes_name in uc['clothes']['name'].lower():
                found_cloth = uc
                break
        if not found_cloth:
            my_clothes = [uc['clothes']['name'] for uc in user_clothes]
            self.send_message(peer_id, f"❌ У вас нет '{clothes_name}'!\n📦 Ваша одежда: {', '.join(my_clothes)}")
            return
        cloth = found_cloth['clothes']
        supabase.table('user_clothes').update({'equipped': False}).eq('user_id', user_id).execute()
        supabase.table('user_clothes').update({'equipped': True}).eq('user_id', user_id).eq('clothes_id', cloth['id']).execute()
        self.send_message(peer_id, f"✅ {self.make_mention(user_id)} надел {cloth['name']}!")
    
    def cmd_unwear(self, peer_id, user_id, args):
        if not args:
            self.send_message(peer_id, "❌ Укажите название одежды!")
            return
        clothes_name = ' '.join(args).lower()
        user_clothes = self.get_user_clothes(user_id)
        if not user_clothes:
            self.send_message(peer_id, "❌ У вас нет одежды!")
            return
        found_cloth = None
        for uc in user_clothes:
            if clothes_name in uc['clothes']['name'].lower():
                found_cloth = uc
                break
        if not found_cloth:
            self.send_message(peer_id, f"❌ У вас нет '{clothes_name}'!")
            return
        cloth = found_cloth['clothes']
        supabase.table('user_clothes').update({'equipped': False}).eq('user_id', user_id).eq('clothes_id', cloth['id']).execute()
        self.send_message(peer_id, f"✅ {self.make_mention(user_id)} снял {cloth['name']}!")
    
    def cmd_give_clothes_to_all(self, peer_id, user_id, args):
        if user_id != ADMIN_ID:
            self.send_message(peer_id, "❌ Нет прав!")
            return
        if not args:
            self.send_message(peer_id, "❌ Использование: !выдатьодежду [название]")
            return
        if args[0].lower() == 'всем':
            args = args[1:]
        if not args:
            self.send_message(peer_id, "❌ Укажите название одежды")
            return
        clothes_name = ' '.join(args)
        clothes_check = supabase.table('clothes').select('*').ilike('name', clothes_name).execute()
        if not clothes_check.data:
            clothes_check = supabase.table('clothes').select('*').ilike('name', f'%{clothes_name}%').execute()
        if not clothes_check.data:
            all_clothes = supabase.table('clothes').select('name').execute()
            names = ', '.join([c['name'] for c in all_clothes.data])
            self.send_message(peer_id, f"❌ Одежда '{clothes_name}' не найдена!\n📋 Доступно: {names}")
            return
        cloth = clothes_check.data[0]
        real_name = cloth['name']
        users = supabase.table('users').select('user_id').execute()
        if not users.data:
            self.send_message(peer_id, "❌ Нет пользователей!")
            return
        success_count = 0
        already_have_count = 0
        for user in users.data:
            existing = supabase.table('user_clothes').select('*').eq('user_id', user['user_id']).eq('clothes_id', cloth['id']).execute()
            if existing.data:
                already_have_count += 1
                continue
            supabase.table('user_clothes').insert({'user_id': user['user_id'], 'clothes_id': cloth['id'], 'equipped': False}).execute()
            self.send_message_to_user(user['user_id'], f"🎁 Вам выдана одежда: {real_name}!")
            success_count += 1
            time.sleep(0.05)
        self.send_message(peer_id, f"✅ Выдана одежда '{real_name}' {success_count} пользователям!\n📦 Уже была у {already_have_count}")
    
    def cmd_mass_mailing(self, peer_id, user_id, args):
        if user_id != ADMIN_ID:
            self.send_message(peer_id, "❌ Нет прав!")
            return
        if not args:
            self.send_message(peer_id, "❌ Использование: !рассылка [текст]")
            return
        text = ' '.join(args)
        users = supabase.table('users').select('user_id').execute()
        if not users.data:
            self.send_message(peer_id, "❌ Нет пользователей!")
            return
        sent_count = 0
        for user in users.data:
            try:
                self.send_message_to_user(user['user_id'], f"📢 РАССЫЛКА:\n\n{text}")
                sent_count += 1
                time.sleep(0.05)
            except:
                pass
        self.send_message(peer_id, f"📢 РАССЫЛКА ОТ АДМИНА:\n\n{text}")
        self.send_message(peer_id, f"✅ Рассылка отправлена {sent_count} пользователям!")
    
    def cmd_admin(self, peer_id, user_id, args):
        if user_id != ADMIN_ID:
            self.send_message(peer_id, "❌ Нет прав!")
            return
        if not args:
            self.send_message(peer_id, "👑 АДМИН КОМАНДЫ:\n\n!админ дать [id] [сумма]\n!админ ркоин [цена]\n!админ одежда [id] [название]\n!админ бан [id]\n!админ разбан [id]\n!админ сброс [id]\n!админ стата")
            return
        action = args[0].lower()
        if action == 'дать' and len(args) >= 3:
            try:
                target_id = int(args[1])
                amount = int(args[2])
                target = self.get_user(target_id)
                if target:
                    self.update_user(target_id, {'money': target['money'] + amount})
                    self.send_message(peer_id, f"✅ Выдано {amount} {self.make_mention(target_id)}")
            except:
                self.send_message(peer_id, "❌ Ошибка!")
        elif action == 'ркоин' and len(args) >= 2:
            try:
                new_price = int(args[1])
                if new_price <= 0:
                    self.send_message(peer_id, "❌ Цена должна быть положительной!")
                    return
                self.set_richcoin_price(new_price)
                self.send_message(peer_id, f"✅ Цена Ричкоина установлена на {new_price}")
            except:
                self.send_message(peer_id, "❌ Ошибка!")
        elif action == 'одежда' and len(args) >= 3:
            try:
                target_id = int(args[1])
                clothes_name = ' '.join(args[2:])
                success, result = self.give_clothes_to_user(target_id, clothes_name)
                if success:
                    self.send_message(peer_id, f"✅ Выдана одежда '{result}' {self.make_mention(target_id)}")
                else:
                    self.send_message(peer_id, f"❌ {result}")
            except:
                self.send_message(peer_id, "❌ Ошибка!")
        elif action == 'бан' and len(args) >= 2:
            try:
                target_id = int(args[1])
                supabase.table('blacklist').insert({'user_id': target_id}).execute()
                self.send_message(peer_id, f"✅ {self.make_mention(target_id)} в ЧС")
            except:
                self.send_message(peer_id, "❌ Ошибка!")
        elif action == 'разбан' and len(args) >= 2:
            try:
                target_id = int(args[1])
                supabase.table('blacklist').delete().eq('user_id', target_id).execute()
                self.send_message(peer_id, f"✅ {self.make_mention(target_id)} из ЧС")
            except:
                self.send_message(peer_id, "❌ Ошибка!")
        elif action == 'сброс' and len(args) >= 2:
            try:
                target_id = int(args[1])
                supabase.table('users').delete().eq('user_id', target_id).execute()
                supabase.table('clan_members').delete().eq('user_id', target_id).execute()
                supabase.table('mafia_members').delete().eq('user_id', target_id).execute()
                supabase.table('user_clothes').delete().eq('user_id', target_id).execute()
                supabase.table('user_businesses').delete().eq('user_id', target_id).execute()
                self.send_message(peer_id, f"✅ Прогресс {self.make_mention(target_id)} сброшен")
            except:
                self.send_message(peer_id, "❌ Ошибка!")
        elif action == 'стата':
            users_count = supabase.table('users').select('*', count='exact').execute()
            clans_count = supabase.table('clans').select('*', count='exact').execute()
            rc_price = self.get_richcoin_price()
            self.send_message(peer_id, f"📊 СТАТИСТИКА:\n\n👥 Игроков: {users_count.count}\n🏆 Кланов: {clans_count.count}\n🪙 Цена Ричкоина: {rc_price}")
    
    # ============================ ОСНОВНОЙ ЦИКЛ ============================
    def run(self):
        print("Бот слушает сообщения...")
        processed_messages = set()
        
        while True:
            try:
                for event in self.longpoll.listen():
                    if event.type == VkEventType.MESSAGE_NEW:
                        if event.user_id == self.bot_id:
                            continue
                        
                        user_id = event.user_id
                        peer_id = event.peer_id
                        message_text = event.text.strip()
                        message_id = event.message_id
                        
                        # Защита от дублирования
                        msg_key = f"{peer_id}_{message_id}"
                        if msg_key in processed_messages:
                            continue
                        processed_messages.add(msg_key)
                        
                        if len(processed_messages) > 500:
                            processed_messages.clear()
                        
                        if not message_text:
                            continue
                        
                        should_process = False
                        clean_message = message_text
                        
                        # В личке обрабатываем всё
                        if peer_id == user_id:
                            should_process = True
                        else:
                            if message_text.startswith('!'):
                                clean_message = message_text[1:].strip()
                                should_process = True
                            elif f"@{self.bot_screen_name}" in message_text.lower():
                                clean_message = message_text.lower().replace(f"@{self.bot_screen_name}", "").strip()
                                should_process = True
                        
                        if not should_process:
                            continue
                        
                        if self.check_blacklist(user_id):
                            continue
                        
                        parts = clean_message.lower().split()
                        if not parts:
                            continue
                        
                        command = parts[0]
                        cmd_args = parts[1:] if len(parts) > 1 else []
                        
                        # Получаем ID пользователя, на чьё сообщение ответили
                        reply_user_id = self.get_reply_user_id(event)
                        
                        if command in self.commands:
                            try:
                                print(f"Команда от @id{user_id}: {command}")
                                
                                # Для команд, которые поддерживают ответ на сообщение
                                if command == 'передать':
                                    self.cmd_transfer(peer_id, user_id, cmd_args, reply_user_id)
                                elif command == 'дуэль':
                                    self.cmd_duel(peer_id, user_id, cmd_args, reply_user_id)
                                elif command == 'ограбить':
                                    self.cmd_rob(peer_id, user_id, cmd_args, reply_user_id)
                                else:
                                    self.commands[command](peer_id, user_id, cmd_args)
                            except Exception as e:
                                print(f"Ошибка в команде {command}: {e}")
                                traceback.print_exc()
                                self.send_message(peer_id, "❌ Ошибка! Попробуйте позже")
            except Exception as e:
                print(f"Ошибка longpoll: {e}")
                traceback.print_exc()
                time.sleep(5)

def run_web_server():
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

if __name__ == "__main__":
    print("Запуск бота...")
    web_thread = threading.Thread(target=run_web_server)
    web_thread.daemon = True
    web_thread.start()
    bot = RichBot()
    bot.run()
