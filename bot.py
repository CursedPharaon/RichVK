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
            'пополнить_клан': self.cmd_donate_clan,
        }
        
        print("Бот Рич запущен!")
    
    # ============================ ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ ============================
    
    def get_user_name(self, user_id):
        if user_id in self.user_name_cache:
            return self.user_name_cache[user_id]
        try:
            user_info = self.vk.users.get(user_ids=user_id)[0]
            first_name = user_info.get('first_name', '')
            last_name = user_info.get('last_name', '')
            if first_name and last_name:
                name = f"{first_name} {last_name}"
            elif first_name:
                name = first_name
            else:
                name = f"id{user_id}"
            self.user_name_cache[user_id] = name
            return name
        except:
            return f"Пользователь {user_id}"
    
    def make_mention(self, user_id):
        name = self.get_user_name(user_id)
        return f"[id{user_id}|{name}]"
    
    def get_reply_user_id(self, event):
        try:
            if hasattr(event, 'reply_message') and event.reply_message:
                return event.reply_message['from_id']
            return None
        except:
            return None
    
    def get_user(self, user_id):
        try:
            # Пробуем получить пользователя
            result = supabase.table('users').select('*').eq('user_id', user_id).execute()
            
            if not result.data:
                # Создаём нового пользователя
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
                return new_user
            
            return result.data[0]
        except Exception as e:
            print(f"Ошибка get_user: {e}")
            # Возвращаем базового пользователя, чтобы бот не падал
            return {
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
                'richcoin': 0
            }
    
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
        user_rc = user.get('richcoin', 0)
        self.send_message(peer_id, f"🪙 РИЧКОИН\n\n💰 Цена: {price} {self.currency_symbol}\n💎 У вас: {user_rc} RC\n\n📈 Купить: !купить_ркоин [кол-во]\n📉 Продать: !продать_ркоин [кол-во]")
    
    def cmd_buy_richcoin(self, peer_id, user_id, args):
        if not args:
            self.send_message(peer_id, "❌ !купить_ркоин 10")
            return
        try:
            amount = int(args[0])
        except:
            self.send_message(peer_id, "❌ Число!")
            return
        if amount <= 0:
            self.send_message(peer_id, "❌ Положительное число!")
            return
        user = self.get_user(user_id)
        price = self.get_richcoin_price()
        total = price * amount
        if user['money'] < total:
            self.send_message(peer_id, f"❌ Нужно {total} {self.currency_symbol}")
            return
        self.update_user(user_id, {
            'money': user['money'] - total,
            'richcoin': user.get('richcoin', 0) + amount
        })
        new_price = int(price * 1.05)
        self.set_richcoin_price(new_price)
        self.send_message(peer_id, f"✅ Куплено {amount} RC за {total} {self.currency_symbol}!\n📈 Цена выросла до {new_price}")
    
    def cmd_sell_richcoin(self, peer_id, user_id, args):
        if not args:
            self.send_message(peer_id, "❌ !продать_ркоин 10")
            return
        try:
            amount = int(args[0])
        except:
            self.send_message(peer_id, "❌ Число!")
            return
        if amount <= 0:
            self.send_message(peer_id, "❌ Положительное число!")
            return
        user = self.get_user(user_id)
        user_rc = user.get('richcoin', 0)
        if user_rc < amount:
            self.send_message(peer_id, f"❌ У вас {user_rc} RC")
            return
        price = self.get_richcoin_price()
        total = int(price * amount * 0.95)
        self.update_user(user_id, {
            'money': user['money'] + total,
            'richcoin': user_rc - amount
        })
        new_price = int(price * 0.95)
        self.set_richcoin_price(new_price)
        self.send_message(peer_id, f"✅ Продано {amount} RC за {total} {self.currency_symbol}!\n📉 Цена упала до {new_price}")
    
    # ============================ ВЗЛОМ ============================
    def cmd_hack(self, peer_id, user_id, args):
        can, rem = self.check_cooldown(user_id, 'hack', 60)
        if not can:
            self.send_message(peer_id, f"⏰ Через {rem} мин")
            return
        item = random.choice(self.hack_items)
        roll = random.randint(1, 100)
        if roll <= item['chance']:
            reward = random.randint(item['reward'][0], item['reward'][1])
            user = self.get_user(user_id)
            self.update_user(user_id, {'money': user['money'] + reward, 'last_hack': datetime.now().isoformat()})
            self.send_message(peer_id, f"💻 Взломан {item['name']}!\n💰 +{reward} {self.currency_symbol}")
        else:
            self.update_user(user_id, {'last_hack': datetime.now().isoformat()})
            self.send_message(peer_id, f"💻 Провал! {item['name']} 🔒\n❌ 0 {self.currency_symbol}")
    
    # ============================ МАФИЯ ============================
    def cmd_mafia(self, peer_id, user_id, args):
        user = self.get_user(user_id)
        if not user['mafia']:
            text = "🔫 МАФИИ:\n\n"
            for m in self.valid_mafias:
                members = supabase.table('mafia_members').select('*').eq('mafia_name', m).execute()
                text += f"• {m} - {len(members.data)} чел\n"
            text += f"\n💡 !вступить_в_мафию [название]"
            self.send_message(peer_id, text)
            return
        mafia = supabase.table('mafia').select('*').eq('name', user['mafia']).execute()
        members = supabase.table('mafia_members').select('*').eq('mafia_name', user['mafia']).execute()
        self.send_message(peer_id, f"🔫 {user['mafia']}\n👥 {len(members.data)} чел\n💰 {mafia.data[0]['money'] if mafia.data else 0}\n\n💡 !покинуть_мафию")
    
    def cmd_join_mafia(self, peer_id, user_id, args):
        if not args:
            self.send_message(peer_id, f"❌ Доступны: {', '.join(self.valid_mafias)}")
            return
        name = ' '.join(args)
        if name not in self.valid_mafias:
            self.send_message(peer_id, f"❌ Нет мафии '{name}'\n✅ {', '.join(self.valid_mafias)}")
            return
        user = self.get_user(user_id)
        if user['mafia']:
            self.send_message(peer_id, f"❌ Вы в {user['mafia']}! Сначала !покинуть_мафию")
            return
        mafia = supabase.table('mafia').select('*').eq('name', name).execute()
        if not mafia.data:
            supabase.table('mafia').insert({'name': name, 'boss': user_id, 'money': 0}).execute()
        supabase.table('mafia_members').insert({'mafia_name': name, 'user_id': user_id}).execute()
        self.update_user(user_id, {'mafia': name})
        self.send_message(peer_id, f"✅ Вы в мафии '{name}'!")
    
    def cmd_leave_mafia(self, peer_id, user_id, args):
        user = self.get_user(user_id)
        if not user['mafia']:
            self.send_message(peer_id, "❌ Вы не в мафии")
            return
        name = user['mafia']
        supabase.table('mafia_members').delete().eq('mafia_name', name).eq('user_id', user_id).execute()
        remaining = supabase.table('mafia_members').select('*').eq('mafia_name', name).execute()
        if not remaining.data:
            supabase.table('mafia').delete().eq('name', name).execute()
            self.send_message(peer_id, f"✅ Мафия '{name}' распущена")
        else:
            self.send_message(peer_id, f"✅ Вы покинули '{name}'")
        self.update_user(user_id, {'mafia': None})
    
    # ============================ КЛАНЫ ============================
    def cmd_create_clan(self, peer_id, user_id, args):
        if not args:
            self.send_message(peer_id, "❌ !создать_клан [название]")
            return
        name = ' '.join(args)
        existing = supabase.table('clans').select('*').eq('name', name).execute()
        if existing.data:
            self.send_message(peer_id, "❌ Клан уже есть")
            return
        user = self.get_user(user_id)
        if user['clan']:
            self.send_message(peer_id, f"❌ Вы в клане '{user['clan']}'")
            return
        if user['money'] < 5000:
            self.send_message(peer_id, f"❌ Нужно 5000 {self.currency_symbol}")
            return
        supabase.table('clans').insert({'name': name, 'owner': user_id, 'money': 0, 'level': 1, 'attack': 10, 'defense': 10}).execute()
        supabase.table('clan_members').insert({'clan_name': name, 'user_id': user_id}).execute()
        self.update_user(user_id, {'money': user['money'] - 5000, 'clan': name})
        self.send_message(peer_id, f"✅ Клан '{name}' создан!")
    
    def cmd_join_clan(self, peer_id, user_id, args):
        if not args:
            self.send_message(peer_id, "❌ !вступить [название]")
            return
        name = ' '.join(args)
        clan = supabase.table('clans').select('*').eq('name', name).execute()
        if not clan.data:
            self.send_message(peer_id, f"❌ Клан '{name}' не найден")
            return
        user = self.get_user(user_id)
        if user['clan']:
            self.send_message(peer_id, f"❌ Вы в клане '{user['clan']}'")
            return
        supabase.table('clan_members').insert({'clan_name': name, 'user_id': user_id}).execute()
        self.update_user(user_id, {'clan': name})
        self.send_message(peer_id, f"✅ Вы в клане '{name}'!")
    
    def cmd_clan_info(self, peer_id, user_id, args):
        user = self.get_user(user_id)
        if not user['clan']:
            self.send_message(peer_id, "❌ Вы не в клане")
            return
        clan = supabase.table('clans').select('*').eq('name', user['clan']).execute()
        members = supabase.table('clan_members').select('*').eq('clan_name', user['clan']).execute()
        if not clan.data:
            self.send_message(peer_id, "❌ Клан не найден")
            return
        c = clan.data[0]
        self.send_message(peer_id, f"🏆 {user['clan']}\n👑 {self.make_mention(c['owner'])}\n👥 {len(members.data)} чел\n💰 {c['money']}\n📈 Ур.{c.get('level',1)} ⚔️{c.get('attack',10)} 🛡{c.get('defense',10)}")
    
    def cmd_leave_clan(self, peer_id, user_id, args):
        user = self.get_user(user_id)
        if not user['clan']:
            self.send_message(peer_id, "❌ Вы не в клане")
            return
        name = user['clan']
        clan = supabase.table('clans').select('*').eq('name', name).execute()
        if not clan.data:
            self.update_user(user_id, {'clan': None})
            self.send_message(peer_id, "✅ Клан удалён")
            return
        c = clan.data[0]
        if c['owner'] == user_id:
            supabase.table('clan_members').delete().eq('clan_name', name).eq('user_id', user_id).execute()
            remaining = supabase.table('clan_members').select('*').eq('clan_name', name).execute()
            if remaining.data:
                new_owner = remaining.data[0]['user_id']
                supabase.table('clans').update({'owner': new_owner}).eq('name', name).execute()
                self.send_message(peer_id, f"👑 Вы покинули '{name}'\n🏆 Новый владелец: {self.make_mention(new_owner)}")
            else:
                supabase.table('clans').delete().eq('name', name).execute()
                self.send_message(peer_id, f"✅ Клан '{name}' распущен")
        else:
            supabase.table('clan_members').delete().eq('clan_name', name).eq('user_id', user_id).execute()
            self.send_message(peer_id, f"✅ Вы покинули '{name}'")
        self.update_user(user_id, {'clan': None})
    
    def cmd_donate_clan(self, peer_id, user_id, args):
        if not args:
            self.send_message(peer_id, "❌ !пополнить_клан [сумма]")
            return
        try:
            amount = int(args[0])
        except:
            self.send_message(peer_id, "❌ Число!")
            return
        if amount <= 0:
            self.send_message(peer_id, "❌ Положительное число")
            return
        user = self.get_user(user_id)
        if not user['clan']:
            self.send_message(peer_id, "❌ Вы не в клане")
            return
        if user['money'] < amount:
            self.send_message(peer_id, f"❌ Нужно {amount} {self.currency_symbol}")
            return
        clan = supabase.table('clans').select('*').eq('name', user['clan']).execute()
        if not clan.data:
            self.send_message(peer_id, "❌ Клан не найден")
            return
        new_money = clan.data[0]['money'] + amount
        supabase.table('clans').update({'money': new_money}).eq('name', user['clan']).execute()
        self.update_user(user_id, {'money': user['money'] - amount})
        self.send_message(peer_id, f"✅ +{amount} в казну '{user['clan']}'\n💰 Теперь {new_money}")
    
    # ============================ БИТВЫ КЛАНОВ ============================
    def cmd_clan_war(self, peer_id, user_id, args):
        if len(args) < 2:
            self.send_message(peer_id, "❌ !битва_кланов [клан] [ставка]")
            return
        name = ' '.join(args[:-1])
        try:
            bet = int(args[-1])
        except:
            self.send_message(peer_id, "❌ Ставка - число!")
            return
        user = self.get_user(user_id)
        if not user['clan']:
            self.send_message(peer_id, "❌ Вы не в клане")
            return
        if user['clan'].lower() == name.lower():
            self.send_message(peer_id, "❌ Нельзя с самим собой")
            return
        target = supabase.table('clans').select('*').eq('name', name).execute()
        if not target.data:
            self.send_message(peer_id, "❌ Клан не найден")
            return
        clan = supabase.table('clans').select('*').eq('name', user['clan']).execute()
        if clan.data[0]['money'] < bet:
            self.send_message(peer_id, f"❌ В казне {clan.data[0]['money']}, нужно {bet}")
            return
        supabase.table('clan_wars').insert({'clan1': user['clan'], 'clan2': name, 'bet': bet, 'status': 'pending'}).execute()
        supabase.table('clans').update({'money': clan.data[0]['money'] - bet}).eq('name', user['clan']).execute()
        self.send_message(peer_id, f"⚔️ {user['clan']} vs {name}\n💰 {bet}\n⏳ !принять_битву {user['clan']} {bet}")
    
    def cmd_accept_war(self, peer_id, user_id, args):
        if len(args) < 2:
            self.send_message(peer_id, "❌ !принять_битву [клан] [ставка]")
            return
        name = ' '.join(args[:-1])
        try:
            bet = int(args[-1])
        except:
            self.send_message(peer_id, "❌ Ставка - число!")
            return
        user = self.get_user(user_id)
        if not user['clan']:
            self.send_message(peer_id, "❌ Вы не в клане")
            return
        war = supabase.table('clan_wars').select('*').eq('clan1', name).eq('clan2', user['clan']).eq('bet', bet).eq('status', 'pending').execute()
        if not war.data:
            self.send_message(peer_id, "❌ Нет вызова")
            return
        clan = supabase.table('clans').select('*').eq('name', user['clan']).execute()
        if clan.data[0]['money'] < bet:
            self.send_message(peer_id, f"❌ В казне {clan.data[0]['money']}, нужно {bet}")
            return
        supabase.table('clans').update({'money': clan.data[0]['money'] - bet}).eq('name', user['clan']).execute()
        supabase.table('clan_wars').update({'status': 'active'}).eq('id', war.data[0]['id']).execute()
        
        # Битва
        clan1 = supabase.table('clans').select('*').eq('name', name).execute().data[0]
        clan2 = supabase.table('clans').select('*').eq('name', user['clan']).execute().data[0]
        power1 = clan1.get('level', 1) * 100 + clan1.get('attack', 10) + clan1.get('defense', 10)
        power2 = clan2.get('level', 1) * 100 + clan2.get('attack', 10) + clan2.get('defense', 10)
        roll1 = random.randint(80, 120)
        roll2 = random.randint(80, 120)
        total = bet * 2
        if power1 * roll1 > power2 * roll2:
            winner = name
            new_money = supabase.table('clans').select('money').eq('name', name).execute().data[0]['money'] + total
            supabase.table('clans').update({'money': new_money}).eq('name', name).execute()
        else:
            winner = user['clan']
            new_money = supabase.table('clans').select('money').eq('name', user['clan']).execute().data[0]['money'] + total
            supabase.table('clans').update({'money': new_money}).eq('name', user['clan']).execute()
        supabase.table('clan_wars').update({'winner': winner, 'status': 'completed'}).eq('id', war.data[0]['id']).execute()
        self.send_message(peer_id, f"⚔️ ПОБЕДИТЕЛЬ: {winner}\n💰 +{total}")
    
    def cmd_upgrade_clan(self, peer_id, user_id, args):
        if not args:
            self.send_message(peer_id, "❌ !прокачать_клан [атака/защита]")
            return
        upgrade = args[0].lower()
        if upgrade not in ['атака', 'защита']:
            self.send_message(peer_id, "❌ Только 'атака' или 'защита'")
            return
        user = self.get_user(user_id)
        if not user['clan']:
            self.send_message(peer_id, "❌ Вы не в клане")
            return
        clan = supabase.table('clans').select('*').eq('name', user['clan']).execute()
        if not clan.data:
            self.send_message(peer_id, "❌ Клан не найден")
            return
        c = clan.data[0]
        if c['owner'] != user_id:
            self.send_message(peer_id, "❌ Только владелец")
            return
        current = c.get(upgrade, 10)
        cost = 5000 * current
        if c['money'] < cost:
            self.send_message(peer_id, f"❌ Нужно {cost} в казне")
            return
        new_val = current + 5
        supabase.table('clans').update({upgrade: new_val, 'money': c['money'] - cost}).eq('name', user['clan']).execute()
        self.send_message(peer_id, f"✅ {upgrade} {current} → {new_val}\n💰 -{cost}")
    
    # ============================ ПЕРЕДАЧА ДЕНЕГ ============================
    def cmd_transfer(self, peer_id, user_id, args, reply_user_id=None):
        target = reply_user_id
        if not target and args:
            for a in args:
                if a.isdigit():
                    if not target:
                        target = int(a)
                    else:
                        amount = int(a)
                        break
        if not target:
            self.send_message(peer_id, "❌ Укажите ID или ответьте на сообщение")
            return
        if target == user_id:
            self.send_message(peer_id, "❌ Себе нельзя")
            return
        if 'amount' not in dir():
            self.send_message(peer_id, "❌ Укажите сумму")
            return
        if amount <= 0:
            self.send_message(peer_id, "❌ Сумма > 0")
            return
        sender = self.get_user(user_id)
        receiver = self.get_user(target)
        if sender['money'] < amount:
            self.send_message(peer_id, f"❌ У вас {sender['money']}")
            return
        self.update_user(user_id, {'money': sender['money'] - amount})
        self.update_user(target, {'money': receiver['money'] + amount})
        self.send_message(peer_id, f"✅ Передано {amount} {self.currency_symbol}")
        self.send_message_to_user(target, f"💰 Вам перевели {amount} {self.currency_symbol}")
    
    # ============================ ДУЭЛЬ ============================
    def cmd_duel(self, peer_id, user_id, args, reply_user_id=None):
        target = reply_user_id
        if not target and args:
            for a in args:
                if a.isdigit():
                    if not target:
                        target = int(a)
                    else:
                        bet = int(a)
                        break
        if not target:
            self.send_message(peer_id, "❌ Укажите ID или ответьте")
            return
        if target == user_id:
            self.send_message(peer_id, "❌ С собой нельзя")
            return
        if 'bet' not in dir():
            self.send_message(peer_id, "❌ Укажите ставку")
            return
        user = self.get_user(user_id)
        opponent = self.get_user(target)
        if bet <= 0 or bet > user['money']:
            self.send_message(peer_id, f"❌ Ставка до {user['money']}")
            return
        supabase.table('duels').insert({'challenger': user_id, 'opponent': target, 'bet': bet, 'status': 'pending'}).execute()
        self.send_message(peer_id, f"⚔️ Вызов {self.make_mention(target)} на {bet}!\n!принять_дуэль {bet}")
    
    def cmd_accept_duel(self, peer_id, user_id, args):
        if not args:
            self.send_message(peer_id, "❌ !принять_дуэль [ставка]")
            return
        try:
            bet = int(args[0])
        except:
            self.send_message(peer_id, "❌ Число!")
            return
        duel = supabase.table('duels').select('*').eq('opponent', user_id).eq('bet', bet).eq('status', 'pending').execute()
        if not duel.data:
            self.send_message(peer_id, "❌ Нет вызова")
            return
        d = duel.data[0]
        challenger = self.get_user(d['challenger'])
        opponent = self.get_user(user_id)
        if opponent['money'] < bet:
            self.send_message(peer_id, f"❌ Нужно {bet}")
            return
        self.update_user(d['challenger'], {'money': challenger['money'] - bet})
        self.update_user(user_id, {'money': opponent['money'] - bet})
        power1 = random.randint(1, 100) + challenger['level'] * 5
        power2 = random.randint(1, 100) + opponent['level'] * 5
        winner = d['challenger'] if power1 > power2 else user_id
        self.update_user(winner, {'money': self.get_user(winner)['money'] + bet * 2})
        self.update_user(d['challenger'], {'duels_won' if winner == d['challenger'] else 'duels_lost': self.get_user(d['challenger']).get('duels_won', 0) + 1})
        self.update_user(user_id, {'duels_won' if winner == user_id else 'duels_lost': self.get_user(user_id).get('duels_won', 0) + 1})
        supabase.table('duels').update({'status': 'completed'}).eq('duel_id', d['duel_id']).execute()
        self.send_message(peer_id, f"⚔️ ПОБЕДИТЕЛЬ: {self.make_mention(winner)}\n💰 +{bet * 2}")
    
    def cmd_decline_duel(self, peer_id, user_id, args):
        if not args:
            self.send_message(peer_id, "❌ !отклонить_дуэль [ставка]")
            return
        try:
            bet = int(args[0])
        except:
            self.send_message(peer_id, "❌ Число!")
            return
        supabase.table('duels').update({'status': 'declined'}).eq('opponent', user_id).eq('bet', bet).eq('status', 'pending').execute()
        self.send_message(peer_id, f"❌ Дуэль отклонена")
    
    def cmd_rob(self, peer_id, user_id, args, reply_user_id=None):
        target = reply_user_id
        if not target and args:
            for a in args:
                if a.isdigit():
                    target = int(a)
                    break
        if not target:
            self.send_message(peer_id, "❌ Укажите ID или ответьте")
            return
        if target == user_id:
            self.send_message(peer_id, "❌ Себя нельзя")
            return
        can, rem = self.check_cooldown(user_id, 'rob', 30)
        if not can:
            self.send_message(peer_id, f"⏰ Через {rem} мин")
            return
        user = self.get_user(user_id)
        target_u = self.get_user(target)
        if random.random() < 0.6:
            amount = random.randint(50, min(300, target_u['money']))
            self.update_user(user_id, {'money': user['money'] + amount, 'last_rob': datetime.now().isoformat()})
            self.update_user(target, {'money': target_u['money'] - amount})
            self.send_message(peer_id, f"🔫 Ограблен {self.make_mention(target)} на {amount}!")
        else:
            penalty = random.randint(50, 150)
            self.update_user(user_id, {'money': max(0, user['money'] - penalty), 'last_rob': datetime.now().isoformat()})
            self.send_message(peer_id, f"❌ Провал! Штраф {penalty}")
    
    # ============================ ОСТАЛЬНЫЕ КОМАНДЫ ============================
    def cmd_help(self, peer_id, user_id, args):
        can, _ = self.check_cooldown(user_id, 'help', 0.17)
        if not can:
            return
        self.send_message(peer_id, "📜 КОМАНДЫ:\n\n💰 !баланс\n💼 !работы\n💪 !работа [название]\n🎰 !казино [орел_решка/кости] [ставка]\n👥 !создать_клан [название]\n🤝 !вступить [клан]\n🏆 !клан\n🚪 !покинуть_клан\n💰 !пополнить_клан [сумма]\n⚔️ !битва_кланов [клан] [ставка]\n📈 !прокачать_клан [атака/защита]\n🔫 !мафия\n🔫 !вступить_в_мафию [название]\n🔫 !покинуть_мафию\n⚔️ !дуэль [ставка] (ответом)\n💀 !ограбить (ответом)\n💻 !взлом\n🪙 !ркоин\n🪙 !купить_ркоин [кол-во]\n🪙 !продать_ркоин [кол-во]\n📊 !топ\n💸 !передать [сумма] (ответом)\n🏢 !бизнес\n🏢 !купитьбизнес [название]\n🏢 !собрать\n👔 !шкаф\n👔 !надеть [название]\n👔 !снять [название]")
        self.update_user(user_id, {'last_help': datetime.now().isoformat()})
    
    def cmd_start(self, peer_id, user_id, args):
        user = self.get_user(user_id)
        self.send_message(peer_id, f"🌟 Добро пожаловать!\n💰 {user['money']} {self.currency_symbol}\n⚡ {user['energy']}%\n🏆 Ур.{user['level']}\n📜 !помощь")
    
    def cmd_balance(self, peer_id, user_id, args):
        user = self.get_user(user_id)
        self.send_message(peer_id, f"💰 {user['money']} {self.currency_symbol}\n⚡ {user['energy']}%\n🏆 Ур.{user['level']}\n🪙 {user.get('richcoin',0)} RC")
    
    def cmd_jobs(self, peer_id, user_id, args):
        text = "📋 РАБОТЫ:\n\n"
        for name, data in self.jobs.items():
            text += f"📌 {name}\n   💰 {data['money'][0]}-{data['money'][1]}\n   ⚡ -{data['energy']}\n\n"
        self.send_message(peer_id, text)
    
    def cmd_work(self, peer_id, user_id, args):
        if not args:
            self.send_message(peer_id, "❌ !работа [название]")
            return
        name = args[0].lower()
        if name not in self.jobs:
            self.send_message(peer_id, "❌ Нет такой работы")
            return
        user = self.get_user(user_id)
        if user['job'] != name:
            self.update_user(user_id, {'job': name})
            self.send_message(peer_id, f"✅ Вы устроились на {name}!")
            return
        can, rem = self.check_cooldown(user_id, 'work', 10)
        if not can:
            self.send_message(peer_id, f"⏰ Через {rem} мин")
            return
        if user['energy'] < self.jobs[name]['energy']:
            self.send_message(peer_id, f"❌ Нужно {self.jobs[name]['energy']} энергии")
            return
        earned = random.randint(*self.jobs[name]['money'])
        new_energy = user['energy'] - self.jobs[name]['energy']
        new_exp = user['exp'] + 50
        new_level = user['level']
        if new_exp >= new_level * 100:
            new_level += 1
            new_energy = 100
            level_msg = f"\n🎉 УРОВЕНЬ {new_level}! Энергия восстановлена!"
        else:
            level_msg = ""
        self.update_user(user_id, {
            'money': user['money'] + earned,
            'energy': new_energy,
            'exp': new_exp,
            'level': new_level,
            'last_work': datetime.now().isoformat()
        })
        self.send_message(peer_id, f"✅ Работа на {name}\n💰 +{earned}\n⚡ {new_energy}%{level_msg}")
    
    def cmd_casino(self, peer_id, user_id, args):
        if len(args) < 2:
            self.send_message(peer_id, "❌ !казино [орёл_решка/кости] [ставка]")
            return
        game = args[0].lower()
        try:
            bet = int(args[1])
        except:
            self.send_message(peer_id, "❌ Ставка - число")
            return
        user = self.get_user(user_id)
        if bet <= 0 or bet > user['money']:
            self.send_message(peer_id, f"❌ Ставка до {user['money']}")
            return
        if game in ["орёл_решка", "орел_решка"]:
            if len(args) < 3:
                self.send_message(peer_id, "❌ орёл или решка?")
                return
            choice = args[2].lower()
            if choice not in ['орёл', 'орел', 'решка']:
                self.send_message(peer_id, "❌ орёл или решка")
                return
            coin = random.choice(['орёл', 'решка'])
            win = (choice == coin)
        elif game == "кости":
            user_roll = random.randint(1, 6)
            bot_roll = random.randint(1, 6)
            win = user_roll > bot_roll
            result = f"🎲 {user_roll} vs {bot_roll}"
        else:
            self.send_message(peer_id, "❌ орёл_решка или кости")
            return
        if win:
            self.update_user(user_id, {'money': user['money'] + bet})
            self.send_message(peer_id, f"✅ Выигрыш {bet}!\n💰 {user['money'] + bet}")
        else:
            self.update_user(user_id, {'money': user['money'] - bet})
            self.send_message(peer_id, f"❌ Проигрыш {bet}!\n💰 {user['money'] - bet}")
    
    def cmd_top(self, peer_id, user_id, args):
        users = supabase.table('users').select('user_id, money, level').order('money', desc=True).limit(10).execute()
        if not users.data:
            self.send_message(peer_id, "📊 Нет игроков")
            return
        text = "🏆 ТОП-10:\n\n"
        for i, u in enumerate(users.data, 1):
            text += f"{i}. {self.make_mention(u['user_id'])} - {u['money']} (Ур.{u['level']})\n"
        self.send_message(peer_id, text)
    
    # ============================ БИЗНЕС ============================
    def cmd_business(self, peer_id, user_id, args):
        try:
            biz = supabase.table('businesses').select('*').execute()
            my = supabase.table('user_businesses').select('*, businesses(*)').eq('user_id', user_id).execute()
            text = "🏢 БИЗНЕСЫ:\n\n"
            for b in biz.data:
                text += f"📌 {b['name']}\n   💰 {b['price']}\n   ⏱ {b['income_per_hour']}/час\n\n"
            if my.data:
                text += "📋 ВАШИ:\n"
                for m in my.data:
                    b = m['businesses']
                    last = datetime.fromisoformat(m['last_collected'].replace('Z', '+00:00'))
                    hours = (datetime.now() - last).total_seconds() / 3600
                    pending = int(b['income_per_hour'] * min(hours, 24))
                    text += f"• {b['name']} - +{pending}\n"
                text += f"\n💡 !собрать"
            else:
                text += "\n❌ Нет бизнесов. !купитьбизнес [название]"
            self.send_message(peer_id, text)
        except:
            self.send_message(peer_id, "❌ Ошибка")
    
    def cmd_buy_business(self, peer_id, user_id, args):
        if not args:
            self.send_message(peer_id, "❌ !купитьбизнес [название]")
            return
        name = ' '.join(args).lower()
        biz = supabase.table('businesses').select('*').ilike('name', f'%{name}%').execute()
        if not biz.data:
            self.send_message(peer_id, "❌ Бизнес не найден")
            return
        b = biz.data[0]
        user = self.get_user(user_id)
        existing = supabase.table('user_businesses').select('*').eq('user_id', user_id).eq('business_id', b['id']).execute()
        if existing.data:
            self.send_message(peer_id, f"❌ У вас уже есть {b['name']}")
            return
        if user['money'] < b['price']:
            self.send_message(peer_id, f"❌ Нужно {b['price']}")
            return
        self.update_user(user_id, {'money': user['money'] - b['price']})
        supabase.table('user_businesses').insert({'user_id': user_id, 'business_id': b['id'], 'last_collected': datetime.now().isoformat()}).execute()
        self.send_message(peer_id, f"✅ Куплен {b['name']} за {b['price']}!")
    
    def cmd_collect_business(self, peer_id, user_id, args):
        my = supabase.table('user_businesses').select('*, businesses(*)').eq('user_id', user_id).execute()
        if not my.data:
            self.send_message(peer_id, "❌ Нет бизнесов")
            return
        user = self.get_user(user_id)
        total = 0
        for m in my.data:
            b = m['businesses']
            last = datetime.fromisoformat(m['last_collected'].replace('Z', '+00:00'))
            hours = (datetime.now() - last).total_seconds() / 3600
            income = int(b['income_per_hour'] * min(hours, 24))
            total += income
            supabase.table('user_businesses').update({'last_collected': datetime.now().isoformat()}).eq('user_id', user_id).eq('business_id', b['id']).execute()
        if total > 0:
            self.update_user(user_id, {'money': user['money'] + total})
            self.send_message(peer_id, f"💰 +{total} {self.currency_symbol}")
        else:
            self.send_message(peer_id, "⏰ Накоплений нет")
    
    # ============================ ОДЕЖДА ============================
    def get_user_clothes(self, user_id):
        return supabase.table('user_clothes').select('*, clothes(*)').eq('user_id', user_id).execute().data
    
    def give_clothes_to_user(self, user_id, name):
        cloth = supabase.table('clothes').select('*').ilike('name', name).execute()
        if not cloth.data:
            cloth = supabase.table('clothes').select('*').ilike('name', f'%{name}%').execute()
        if not cloth.data:
            return False, "Одежда не найдена"
        c = cloth.data[0]
        existing = supabase.table('user_clothes').select('*').eq('user_id', user_id).eq('clothes_id', c['id']).execute()
        if existing.data:
            return False, f"Уже есть {c['name']}"
        supabase.table('user_clothes').insert({'user_id': user_id, 'clothes_id': c['id'], 'equipped': False}).execute()
        self.send_message_to_user(user_id, f"🎁 Выдана {c['name']}!")
        return True, c['name']
    
    def cmd_wardrobe(self, peer_id, user_id, args):
        clothes = self.get_user_clothes(user_id)
        if not clothes:
            self.send_message(peer_id, "❌ Нет одежды")
            return
        text = "👔 ГАРДЕРОБ:\n\n"
        eq = [c['clothes']['name'] for c in clothes if c.get('equipped')]
        not_eq = [c['clothes']['name'] for c in clothes if not c.get('equipped')]
        if eq:
            text += "✅ НАДЕТО:\n" + "\n".join(f"• {n}" for n in eq) + "\n\n"
        if not_eq:
            text += "📦 В ШКАФУ:\n" + "\n".join(f"• {n}" for n in not_eq) + "\n\n"
        text += "💡 !надеть [название]\n💡 !снять [название]"
        self.send_message(peer_id, text)
    
    def cmd_wear(self, peer_id, user_id, args):
        if not args:
            self.send_message(peer_id, "❌ !надеть [название]")
            return
        name = ' '.join(args).lower()
        clothes = self.get_user_clothes(user_id)
        found = None
        for c in clothes:
            if name in c['clothes']['name'].lower():
                found = c
                break
        if not found:
            self.send_message(peer_id, f"❌ Нет '{name}'")
            return
        supabase.table('user_clothes').update({'equipped': False}).eq('user_id', user_id).execute()
        supabase.table('user_clothes').update({'equipped': True}).eq('user_id', user_id).eq('clothes_id', found['clothes']['id']).execute()
        self.send_message(peer_id, f"✅ Надет {found['clothes']['name']}")
    
    def cmd_unwear(self, peer_id, user_id, args):
        if not args:
            self.send_message(peer_id, "❌ !снять [название]")
            return
        name = ' '.join(args).lower()
        clothes = self.get_user_clothes(user_id)
        found = None
        for c in clothes:
            if name in c['clothes']['name'].lower() and c.get('equipped'):
                found = c
                break
        if not found:
            self.send_message(peer_id, f"❌ Не надет '{name}'")
            return
        supabase.table('user_clothes').update({'equipped': False}).eq('user_id', user_id).eq('clothes_id', found['clothes']['id']).execute()
        self.send_message(peer_id, f"✅ Снят {found['clothes']['name']}")
    
    def cmd_give_clothes_to_all(self, peer_id, user_id, args):
        if user_id != ADMIN_ID:
            self.send_message(peer_id, "❌ Нет прав")
            return
        if not args:
            self.send_message(peer_id, "❌ !выдатьодежду [название]")
            return
        name = ' '.join(args)
        cloth = supabase.table('clothes').select('*').ilike('name', name).execute()
        if not cloth.data:
            cloth = supabase.table('clothes').select('*').ilike('name', f'%{name}%').execute()
        if not cloth.data:
            self.send_message(peer_id, "❌ Одежда не найдена")
            return
        c = cloth.data[0]
        users = supabase.table('users').select('user_id').execute()
        ok, already = 0, 0
        for u in users.data:
            ex = supabase.table('user_clothes').select('*').eq('user_id', u['user_id']).eq('clothes_id', c['id']).execute()
            if ex.data:
                already += 1
                continue
            supabase.table('user_clothes').insert({'user_id': u['user_id'], 'clothes_id': c['id'], 'equipped': False}).execute()
            self.send_message_to_user(u['user_id'], f"🎁 Выдана {c['name']}!")
            ok += 1
            time.sleep(0.05)
        self.send_message(peer_id, f"✅ Выдано {ok} игрокам\n📦 Уже было у {already}")
    
    def cmd_mass_mailing(self, peer_id, user_id, args):
        if user_id != ADMIN_ID:
            self.send_message(peer_id, "❌ Нет прав")
            return
        if not args:
            self.send_message(peer_id, "❌ !рассылка [текст]")
            return
        text = ' '.join(args)
        users = supabase.table('users').select('user_id').execute()
        sent = 0
        for u in users.data:
            try:
                self.send_message_to_user(u['user_id'], f"📢 {text}")
                sent += 1
                time.sleep(0.05)
            except:
                pass
        self.send_message(peer_id, f"✅ Отправлено {sent} пользователям")
    
    def cmd_admin(self, peer_id, user_id, args):
        if user_id != ADMIN_ID:
            self.send_message(peer_id, "❌ Нет прав")
            return
        if not args:
            self.send_message(peer_id, "👑 АДМИН:\n!админ дать [id] [сумма]\n!админ ркоин [цена]\n!админ одежда [id] [название]\n!админ бан [id]\n!админ разбан [id]\n!админ сброс [id]\n!админ стата")
            return
        action = args[0].lower()
        if action == 'дать' and len(args) >= 3:
            try:
                target = int(args[1])
                amount = int(args[2])
                u = self.get_user(target)
                self.update_user(target, {'money': u['money'] + amount})
                self.send_message(peer_id, f"✅ +{amount} {self.make_mention(target)}")
            except:
                self.send_message(peer_id, "❌ Ошибка")
        elif action == 'ркоин' and len(args) >= 2:
            try:
                price = int(args[1])
                self.set_richcoin_price(price)
                self.send_message(peer_id, f"✅ Цена Ричкоина: {price}")
            except:
                self.send_message(peer_id, "❌ Ошибка")
        elif action == 'одежда' and len(args) >= 3:
            try:
                target = int(args[1])
                name = ' '.join(args[2:])
                ok, msg = self.give_clothes_to_user(target, name)
                self.send_message(peer_id, f"✅ {msg}" if ok else f"❌ {msg}")
            except:
                self.send_message(peer_id, "❌ Ошибка")
        elif action == 'бан' and len(args) >= 2:
            try:
                target = int(args[1])
                supabase.table('blacklist').insert({'user_id': target}).execute()
                self.send_message(peer_id, f"✅ {self.make_mention(target)} в ЧС")
            except:
                self.send_message(peer_id, "❌ Ошибка")
        elif action == 'разбан' and len(args) >= 2:
            try:
                target = int(args[1])
                supabase.table('blacklist').delete().eq('user_id', target).execute()
                self.send_message(peer_id, f"✅ {self.make_mention(target)} из ЧС")
            except:
                self.send_message(peer_id, "❌ Ошибка")
        elif action == 'сброс' and len(args) >= 2:
            try:
                target = int(args[1])
                supabase.table('users').delete().eq('user_id', target).execute()
                supabase.table('clan_members').delete().eq('user_id', target).execute()
                supabase.table('mafia_members').delete().eq('user_id', target).execute()
                supabase.table('user_clothes').delete().eq('user_id', target).execute()
                supabase.table('user_businesses').delete().eq('user_id', target).execute()
                self.send_message(peer_id, f"✅ {self.make_mention(target)} сброшен")
            except:
                self.send_message(peer_id, "❌ Ошибка")
        elif action == 'стата':
            users = supabase.table('users').select('*', count='exact').execute()
            clans = supabase.table('clans').select('*', count='exact').execute()
            price = self.get_richcoin_price()
            self.send_message(peer_id, f"📊 СТАТИСТИКА:\n👥 {users.count} игроков\n🏆 {clans.count} кланов\n🪙 {price} Ричкоин")
    
    # ============================ ОСНОВНОЙ ЦИКЛ ============================
    def run(self):
        print("Бот слушает сообщения...")
        processed = set()
        while True:
            try:
                for event in self.longpoll.listen():
                    if event.type == VkEventType.MESSAGE_NEW:
                        if event.user_id == self.bot_id:
                            continue
                        key = f"{event.peer_id}_{event.message_id}"
                        if key in processed:
                            continue
                        processed.add(key)
                        if len(processed) > 500:
                            processed.clear()
                        msg = event.text.strip()
                        if not msg:
                            continue
                        process = False
                        clean = msg
                        if event.peer_id == event.user_id:
                            process = True
                        elif msg.startswith('!'):
                            clean = msg[1:].strip()
                            process = True
                        if not process:
                            continue
                        if self.check_blacklist(event.user_id):
                            continue
                        parts = clean.lower().split()
                        if not parts:
                            continue
                        cmd = parts[0]
                        args = parts[1:]
                        reply = self.get_reply_user_id(event)
                        try:
                            if cmd in self.commands:
                                print(f"Команда: {cmd} от {event.user_id}")
                                if cmd == 'передать':
                                    self.cmd_transfer(event.peer_id, event.user_id, args, reply)
                                elif cmd == 'дуэль':
                                    self.cmd_duel(event.peer_id, event.user_id, args, reply)
                                elif cmd == 'ограбить':
                                    self.cmd_rob(event.peer_id, event.user_id, args, reply)
                                else:
                                    self.commands[cmd](event.peer_id, event.user_id, args)
                        except Exception as e:
                            print(f"Ошибка: {e}")
                            traceback.print_exc()
                            self.send_message(event.peer_id, "❌ Ошибка! Попробуйте позже")
            except Exception as e:
                print(f"Ошибка longpoll: {e}")
                time.sleep(5)

def run_web():
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

if __name__ == "__main__":
    print("Запуск бота...")
    threading.Thread(target=run_web, daemon=True).start()
    bot = RichBot()
    bot.run()
