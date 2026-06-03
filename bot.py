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

# Переменные окружения
VK_TOKEN = os.environ.get('VK_TOKEN')
SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY')
ADMIN_ID = int(os.environ.get('ADMIN_ID', 0))

if not VK_TOKEN or not SUPABASE_URL or not SUPABASE_KEY:
    print("Ошибка: переменные окружения не установлены")
    sys.exit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
app = Flask(__name__)

@app.route('/')
def health():
    return "OK"

class RichBot:
    def __init__(self):
        print("Запуск бота...")
        self.vk_session = vk_api.VkApi(token=VK_TOKEN)
        self.vk = self.vk_session.get_api()
        self.longpoll = VkLongPoll(self.vk_session)
        self.bot_id = self.vk.users.get()[0]['id']
        self.start_money = 1000
        self.valid_mafias = ['Братки', 'Мафиози', 'Гангстеры']
        
        self.jobs = {
            'программист': {'money': (500, 1000), 'energy': 20},
            'грузчик': {'money': (200, 500), 'energy': 15},
            'таксист': {'money': (300, 600), 'energy': 15},
            'официант': {'money': (200, 400), 'energy': 10},
            'шаурмист': {'money': (400, 700), 'energy': 20}
        }
        
        self.hack_items = [
            {'name': 'Макдональдс', 'chance': 80, 'reward': (100, 300)},
            {'name': 'Магазин', 'chance': 70, 'reward': (300, 600)},
            {'name': 'Банк', 'chance': 50, 'reward': (1000, 2500)},
            {'name': 'Пентагон', 'chance': 30, 'reward': (5000, 10000)},
            {'name': 'Центробанк', 'chance': 15, 'reward': (15000, 30000)},
        ]
        
        self.commands = {
            'начать': self.cmd_start, 'баланс': self.cmd_balance, 'помощь': self.cmd_help,
            'работы': self.cmd_jobs, 'работа': self.cmd_work, 'казино': self.cmd_casino,
            'создать_клан': self.cmd_create_clan, 'вступить': self.cmd_join_clan, 'клан': self.cmd_clan_info,
            'покинуть_клан': self.cmd_leave_clan, 'пополнить_клан': self.cmd_donate_clan,
            'битва_кланов': self.cmd_clan_war, 'принять_битву': self.cmd_accept_war, 'прокачать_клан': self.cmd_upgrade_clan,
            'мафия': self.cmd_mafia, 'вступить_в_мафию': self.cmd_join_mafia, 'покинуть_мафию': self.cmd_leave_mafia,
            'ограбить': self.cmd_rob, 'дуэль': self.cmd_duel, 'принять_дуэль': self.cmd_accept_duel,
            'отклонить_дуэль': self.cmd_decline_duel, 'топ': self.cmd_top, 'админ': self.cmd_admin,
            'передать': self.cmd_transfer, 'бизнес': self.cmd_business, 'купитьбизнес': self.cmd_buy_business,
            'собрать': self.cmd_collect_business, 'шкаф': self.cmd_wardrobe, 'надеть': self.cmd_wear,
            'снять': self.cmd_unwear, 'выдатьодежду': self.cmd_give_clothes_to_all, 'рассылка': self.cmd_mass_mailing,
            'ркоин': self.cmd_richcoin, 'купить_ркоин': self.cmd_buy_richcoin, 'продать_ркоин': self.cmd_sell_richcoin,
            'взлом': self.cmd_hack,
        }
        print(f"Бот запущен! ID: {self.bot_id}")
    
    def get_user(self, user_id):
        try:
            res = supabase.table('users').select('*').eq('user_id', user_id).execute()
            if res.data:
                return res.data[0]
            new = {'user_id': user_id, 'money': self.start_money, 'energy': 100, 'job': None, 'clan': None,
                   'mafia': None, 'level': 1, 'exp': 0, 'duels_won': 0, 'duels_lost': 0, 'richcoin': 0}
            supabase.table('users').insert(new).execute()
            return new
        except:
            return {'user_id': user_id, 'money': self.start_money, 'energy': 100, 'level': 1, 'richcoin': 0}
    
    def update_user(self, user_id, data):
        try:
            supabase.table('users').update(data).eq('user_id', user_id).execute()
        except:
            pass
    
    def get_richcoin_price(self):
        try:
            res = supabase.table('richcoin').select('price').order('id', desc=True).limit(1).execute()
            return res.data[0]['price'] if res.data else 25000000
        except:
            return 25000000
    
    def set_richcoin_price(self, price):
        try:
            supabase.table('richcoin').insert({'price': price}).execute()
        except:
            pass
    
    def check_cooldown(self, user_id, action, minutes):
        try:
            user = self.get_user(user_id)
            last = user.get(f'last_{action}')
            if last:
                last_time = datetime.fromisoformat(last.replace('Z', '+00:00'))
                if datetime.now() - last_time < timedelta(minutes=minutes):
                    rem = int((timedelta(minutes=minutes) - (datetime.now() - last_time)).total_seconds() // 60)
                    return False, rem
            return True, 0
        except:
            return True, 0
    
    def send_message(self, peer_id, text):
        try:
            self.vk.messages.send(peer_id=peer_id, message=text[:4000], random_id=random.randint(1, 9999999))
        except:
            pass
    
    def get_reply_id(self, event):
        try:
            if event.reply_message:
                return event.reply_message['from_id']
        except:
            pass
        return None
    
    # ==================== ОСНОВНЫЕ КОМАНДЫ ====================
    
    def cmd_start(self, peer_id, user_id, args):
        u = self.get_user(user_id)
        self.send_message(peer_id, f"🌟 Добро пожаловать!\n💰 Баланс: {u['money']}\n⚡ Энергия: {u['energy']}%\n🏆 Уровень: {u['level']}\n\n!помощь - список команд")
    
    def cmd_balance(self, peer_id, user_id, args):
        u = self.get_user(user_id)
        self.send_message(peer_id, f"💰 Баланс: {u['money']}\n⚡ Энергия: {u['energy']}%\n🏆 Уровень: {u['level']}\n🪙 Ричкоин: {u.get('richcoin', 0)}")
    
    def cmd_help(self, peer_id, user_id, args):
        self.send_message(peer_id, "📜 КОМАНДЫ:\n\n!баланс\n!работы\n!работа [название]\n!казино [орел/кости] [ставка]\n!создать_клан [название]\n!вступить [клан]\n!клан\n!покинуть_клан\n!пополнить_клан [сумма]\n!битва_кланов [клан] [ставка]\n!прокачать_клан [атака/защита]\n!мафия\n!вступить_в_мафию [название]\n!покинуть_мафию\n!дуэль [ставка] (ответом)\n!ограбить (ответом)\n!взлом\n!ркоин\n!купить_ркоин [кол-во]\n!продать_ркоин [кол-во]\n!топ\n!передать [сумма] (ответом)\n!бизнес\n!купитьбизнес [название]\n!собрать\n!шкаф\n!надеть [название]\n!снять [название]")
    
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
        u = self.get_user(user_id)
        if u['job'] != name:
            self.update_user(user_id, {'job': name})
            self.send_message(peer_id, f"✅ Вы устроились на {name}!")
            return
        can, rem = self.check_cooldown(user_id, 'work', 10)
        if not can:
            self.send_message(peer_id, f"⏰ Через {rem} мин")
            return
        if u['energy'] < self.jobs[name]['energy']:
            self.send_message(peer_id, f"❌ Нужно {self.jobs[name]['energy']} энергии")
            return
        earned = random.randint(*self.jobs[name]['money'])
        new_energy = u['energy'] - self.jobs[name]['energy']
        new_exp = u['exp'] + 50
        new_level = u['level']
        if new_exp >= new_level * 100:
            new_level += 1
            new_energy = 100
            self.send_message(peer_id, f"🎉 УРОВЕНЬ {new_level}!")
        self.update_user(user_id, {'money': u['money'] + earned, 'energy': new_energy, 'exp': new_exp, 'level': new_level, 'last_work': datetime.now().isoformat()})
        self.send_message(peer_id, f"✅ +{earned} 💰\n⚡ Энергия: {new_energy}%")
    
    def cmd_casino(self, peer_id, user_id, args):
        if len(args) < 2:
            self.send_message(peer_id, "❌ !казино [орел/кости] [ставка]")
            return
        game = args[0].lower()
        try:
            bet = int(args[1])
        except:
            self.send_message(peer_id, "❌ Ставка - число")
            return
        u = self.get_user(user_id)
        if bet <= 0 or bet > u['money']:
            self.send_message(peer_id, f"❌ Ставка до {u['money']}")
            return
        win = False
        if game in ['орел', 'орел_решка']:
            if len(args) < 3:
                self.send_message(peer_id, "❌ орёл или решка?")
                return
            choice = args[2].lower()
            coin = random.choice(['орёл', 'решка'])
            win = (choice == coin)
            self.send_message(peer_id, f"🎲 Выпал {coin}!")
        elif game == 'кости':
            u_roll = random.randint(1, 6)
            b_roll = random.randint(1, 6)
            win = u_roll > b_roll
            self.send_message(peer_id, f"🎲 {u_roll} vs {b_roll}")
        else:
            self.send_message(peer_id, "❌ орёл или кости")
            return
        if win:
            self.update_user(user_id, {'money': u['money'] + bet})
            self.send_message(peer_id, f"✅ Выиграли {bet}!\n💰 {u['money'] + bet}")
        else:
            self.update_user(user_id, {'money': u['money'] - bet})
            self.send_message(peer_id, f"❌ Проиграли {bet}!\n💰 {u['money'] - bet}")
    
    # ==================== КЛАНЫ ====================
    
    def cmd_create_clan(self, peer_id, user_id, args):
        if not args:
            self.send_message(peer_id, "❌ !создать_клан [название]")
            return
        name = ' '.join(args)
        if supabase.table('clans').select('*').eq('name', name).execute().data:
            self.send_message(peer_id, "❌ Клан уже есть")
            return
        u = self.get_user(user_id)
        if u['clan']:
            self.send_message(peer_id, f"❌ Вы уже в клане {u['clan']}")
            return
        if u['money'] < 5000:
            self.send_message(peer_id, f"❌ Нужно 5000, у вас {u['money']}")
            return
        supabase.table('clans').insert({'name': name, 'owner': user_id, 'money': 0}).execute()
        supabase.table('clan_members').insert({'clan_name': name, 'user_id': user_id}).execute()
        self.update_user(user_id, {'money': u['money'] - 5000, 'clan': name})
        self.send_message(peer_id, f"✅ Клан '{name}' создан!")
    
    def cmd_join_clan(self, peer_id, user_id, args):
        if not args:
            self.send_message(peer_id, "❌ !вступить [название]")
            return
        name = ' '.join(args)
        if not supabase.table('clans').select('*').eq('name', name).execute().data:
            self.send_message(peer_id, f"❌ Клан '{name}' не найден")
            return
        u = self.get_user(user_id)
        if u['clan']:
            self.send_message(peer_id, f"❌ Вы уже в клане {u['clan']}")
            return
        supabase.table('clan_members').insert({'clan_name': name, 'user_id': user_id}).execute()
        self.update_user(user_id, {'clan': name})
        self.send_message(peer_id, f"✅ Вы вступили в '{name}'!")
    
    def cmd_clan_info(self, peer_id, user_id, args):
        u = self.get_user(user_id)
        if not u['clan']:
            self.send_message(peer_id, "❌ Вы не в клане")
            return
        clan = supabase.table('clans').select('*').eq('name', u['clan']).execute().data[0]
        members = supabase.table('clan_members').select('*').eq('clan_name', u['clan']).execute().data
        self.send_message(peer_id, f"🏆 {u['clan']}\n👑 Владелец: {clan['owner']}\n👥 Участников: {len(members)}\n💰 Казна: {clan['money']}")
    
    def cmd_leave_clan(self, peer_id, user_id, args):
        u = self.get_user(user_id)
        if not u['clan']:
            self.send_message(peer_id, "❌ Вы не в клане")
            return
        name = u['clan']
        supabase.table('clan_members').delete().eq('clan_name', name).eq('user_id', user_id).execute()
        self.update_user(user_id, {'clan': None})
        self.send_message(peer_id, f"✅ Вы покинули '{name}'")
    
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
        u = self.get_user(user_id)
        if not u['clan']:
            self.send_message(peer_id, "❌ Вы не в клане")
            return
        if u['money'] < amount:
            self.send_message(peer_id, f"❌ Нужно {amount}, у вас {u['money']}")
            return
        clan = supabase.table('clans').select('*').eq('name', u['clan']).execute().data[0]
        supabase.table('clans').update({'money': clan['money'] + amount}).eq('name', u['clan']).execute()
        self.update_user(user_id, {'money': u['money'] - amount})
        self.send_message(peer_id, f"✅ +{amount} в казну!")
    
    def cmd_clan_war(self, peer_id, user_id, args):
        if len(args) < 2:
            self.send_message(peer_id, "❌ !битва_кланов [клан] [ставка]")
            return
        name = ' '.join(args[:-1])
        try:
            bet = int(args[-1])
        except:
            self.send_message(peer_id, "❌ Ставка - число")
            return
        u = self.get_user(user_id)
        if not u['clan']:
            self.send_message(peer_id, "❌ Вы не в клане")
            return
        if not supabase.table('clans').select('*').eq('name', name).execute().data:
            self.send_message(peer_id, "❌ Клан не найден")
            return
        my_clan = supabase.table('clans').select('*').eq('name', u['clan']).execute().data[0]
        if my_clan['money'] < bet:
            self.send_message(peer_id, f"❌ В казне {my_clan['money']}")
            return
        supabase.table('clan_wars').insert({'clan1': u['clan'], 'clan2': name, 'bet': bet}).execute()
        supabase.table('clans').update({'money': my_clan['money'] - bet}).eq('name', u['clan']).execute()
        self.send_message(peer_id, f"⚔️ {u['clan']} vs {name}\n💰 Ставка: {bet}\n!принять_битву {bet}")
    
    def cmd_accept_war(self, peer_id, user_id, args):
        if not args:
            self.send_message(peer_id, "❌ !принять_битву [ставка]")
            return
        try:
            bet = int(args[0])
        except:
            self.send_message(peer_id, "❌ Число")
            return
        u = self.get_user(user_id)
        if not u['clan']:
            self.send_message(peer_id, "❌ Вы не в клане")
            return
        war = supabase.table('clan_wars').select('*').eq('clan2', u['clan']).eq('bet', bet).eq('status', 'pending').execute().data
        if not war:
            self.send_message(peer_id, "❌ Нет вызова")
            return
        my_clan = supabase.table('clans').select('*').eq('name', u['clan']).execute().data[0]
        if my_clan['money'] < bet:
            self.send_message(peer_id, f"❌ В казне {my_clan['money']}")
            return
        supabase.table('clans').update({'money': my_clan['money'] - bet}).eq('name', u['clan']).execute()
        winner = random.choice([war[0]['clan1'], u['clan']])
        total = bet * 2
        winner_clan = supabase.table('clans').select('money').eq('name', winner).execute().data[0]
        supabase.table('clans').update({'money': winner_clan['money'] + total}).eq('name', winner).execute()
        supabase.table('clan_wars').update({'winner': winner, 'status': 'completed'}).eq('id', war[0]['id']).execute()
        self.send_message(peer_id, f"⚔️ ПОБЕДИТЕЛЬ: {winner}\n💰 +{total}")
    
    def cmd_upgrade_clan(self, peer_id, user_id, args):
        self.send_message(peer_id, "⏳ В разработке")
    
    # ==================== МАФИЯ ====================
    
    def cmd_mafia(self, peer_id, user_id, args):
        u = self.get_user(user_id)
        if not u['mafia']:
            text = "🔫 МАФИИ:\n\n"
            for m in self.valid_mafias:
                members = supabase.table('mafia_members').select('*').eq('mafia_name', m).execute().data
                text += f"• {m} - {len(members)} чел\n"
            self.send_message(peer_id, text + "\n!вступить_в_мафию [название]")
            return
        members = supabase.table('mafia_members').select('*').eq('mafia_name', u['mafia']).execute().data
        self.send_message(peer_id, f"🔫 {u['mafia']}\n👥 {len(members)} чел")
    
    def cmd_join_mafia(self, peer_id, user_id, args):
        if not args:
            self.send_message(peer_id, f"❌ Доступны: {', '.join(self.valid_mafias)}")
            return
        name = ' '.join(args)
        if name not in self.valid_mafias:
            self.send_message(peer_id, f"❌ Мафия '{name}' не существует")
            return
        u = self.get_user(user_id)
        if u['mafia']:
            self.send_message(peer_id, f"❌ Вы уже в {u['mafia']}")
            return
        supabase.table('mafia_members').insert({'mafia_name': name, 'user_id': user_id}).execute()
        self.update_user(user_id, {'mafia': name})
        self.send_message(peer_id, f"✅ Вы в мафии '{name}'!")
    
    def cmd_leave_mafia(self, peer_id, user_id, args):
        u = self.get_user(user_id)
        if not u['mafia']:
            self.send_message(peer_id, "❌ Вы не в мафии")
            return
        name = u['mafia']
        supabase.table('mafia_members').delete().eq('mafia_name', name).eq('user_id', user_id).execute()
        self.update_user(user_id, {'mafia': None})
        self.send_message(peer_id, f"✅ Вы покинули '{name}'")
    
    # ==================== ВЗАИМОДЕЙСТВИЕ ====================
    
    def cmd_transfer(self, peer_id, user_id, args, reply_id=None):
        target = reply_id
        amount = None
        for a in args:
            if a.isdigit():
                if target is None:
                    target = int(a)
                else:
                    amount = int(a)
                    break
        if target is None:
            self.send_message(peer_id, "❌ Укажите ID или ответьте на сообщение")
            return
        if amount is None:
            self.send_message(peer_id, "❌ Укажите сумму")
            return
        if target == user_id:
            self.send_message(peer_id, "❌ Себе нельзя")
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
        self.send_message(peer_id, f"✅ Передано {amount}")
    
    def cmd_duel(self, peer_id, user_id, args, reply_id=None):
        target = reply_id
        bet = None
        for a in args:
            if a.isdigit():
                if target is None:
                    target = int(a)
                else:
                    bet = int(a)
                    break
        if target is None:
            self.send_message(peer_id, "❌ Укажите ID или ответьте")
            return
        if bet is None:
            self.send_message(peer_id, "❌ Укажите ставку")
            return
        if target == user_id:
            self.send_message(peer_id, "❌ С собой нельзя")
            return
        u = self.get_user(user_id)
        if bet <= 0 or bet > u['money']:
            self.send_message(peer_id, f"❌ Ставка до {u['money']}")
            return
        supabase.table('duels').insert({'challenger': user_id, 'opponent': target, 'bet': bet}).execute()
        self.send_message(peer_id, f"⚔️ Вызов!\n💰 Ставка: {bet}\n!принять_дуэль {bet}")
    
    def cmd_accept_duel(self, peer_id, user_id, args):
        if not args:
            self.send_message(peer_id, "❌ !принять_дуэль [ставка]")
            return
        try:
            bet = int(args[0])
        except:
            self.send_message(peer_id, "❌ Число")
            return
        duel = supabase.table('duels').select('*').eq('opponent', user_id).eq('bet', bet).eq('status', 'pending').execute().data
        if not duel:
            self.send_message(peer_id, "❌ Нет вызова")
            return
        d = duel[0]
        challenger = self.get_user(d['challenger'])
        opponent = self.get_user(user_id)
        if opponent['money'] < bet:
            self.send_message(peer_id, f"❌ Нужно {bet}")
            return
        self.update_user(d['challenger'], {'money': challenger['money'] - bet})
        self.update_user(user_id, {'money': opponent['money'] - bet})
        winner = random.choice([d['challenger'], user_id])
        self.update_user(winner, {'money': self.get_user(winner)['money'] + bet*2})
        supabase.table('duels').update({'status': 'completed'}).eq('duel_id', d['duel_id']).execute()
        self.send_message(peer_id, f"⚔️ ПОБЕДИТЕЛЬ: {winner}\n💰 +{bet*2}")
    
    def cmd_decline_duel(self, peer_id, user_id, args):
        if not args:
            self.send_message(peer_id, "❌ !отклонить_дуэль [ставка]")
            return
        try:
            bet = int(args[0])
        except:
            self.send_message(peer_id, "❌ Число")
            return
        supabase.table('duels').update({'status': 'declined'}).eq('opponent', user_id).eq('bet', bet).eq('status', 'pending').execute()
        self.send_message(peer_id, "❌ Дуэль отклонена")
    
    def cmd_rob(self, peer_id, user_id, args, reply_id=None):
        target = reply_id
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
        u = self.get_user(user_id)
        t = self.get_user(target)
        if random.random() < 0.6:
            amount = random.randint(50, min(300, t['money']))
            self.update_user(user_id, {'money': u['money'] + amount, 'last_rob': datetime.now().isoformat()})
            self.update_user(target, {'money': t['money'] - amount})
            self.send_message(peer_id, f"🔫 Ограблено {amount}!")
        else:
            penalty = random.randint(50, 150)
            self.update_user(user_id, {'money': max(0, u['money'] - penalty), 'last_rob': datetime.now().isoformat()})
            self.send_message(peer_id, f"❌ Штраф {penalty}")
    
    def cmd_hack(self, peer_id, user_id, args):
        can, rem = self.check_cooldown(user_id, 'hack', 60)
        if not can:
            self.send_message(peer_id, f"⏰ Через {rem} мин")
            return
        item = random.choice(self.hack_items)
        if random.randint(1,100) <= item['chance']:
            reward = random.randint(item['reward'][0], item['reward'][1])
            u = self.get_user(user_id)
            self.update_user(user_id, {'money': u['money'] + reward, 'last_hack': datetime.now().isoformat()})
            self.send_message(peer_id, f"💻 Взломан {item['name']}!\n💰 +{reward}")
        else:
            self.update_user(user_id, {'last_hack': datetime.now().isoformat()})
            self.send_message(peer_id, f"💻 Провал! {item['name']}")
    
    # ==================== РИЧКОИН ====================
    
    def cmd_richcoin(self, peer_id, user_id, args):
        price = self.get_richcoin_price()
        u = self.get_user(user_id)
        self.send_message(peer_id, f"🪙 Цена: {price}\n💎 У вас: {u.get('richcoin',0)}\n\n!купить_ркоин [кол-во]\n!продать_ркоин [кол-во]")
    
    def cmd_buy_richcoin(self, peer_id, user_id, args):
        if not args:
            self.send_message(peer_id, "❌ !купить_ркоин [кол-во]")
            return
        try:
            amount = int(args[0])
        except:
            self.send_message(peer_id, "❌ Число")
            return
        if amount <= 0:
            self.send_message(peer_id, "❌ >0")
            return
        u = self.get_user(user_id)
        price = self.get_richcoin_price()
        cost = price * amount
        if u['money'] < cost:
            self.send_message(peer_id, f"❌ Нужно {cost}")
            return
        self.update_user(user_id, {'money': u['money'] - cost, 'richcoin': u.get('richcoin',0) + amount})
        self.set_richcoin_price(int(price * 1.05))
        self.send_message(peer_id, f"✅ Куплено {amount} RC за {cost}")
    
    def cmd_sell_richcoin(self, peer_id, user_id, args):
        if not args:
            self.send_message(peer_id, "❌ !продать_ркоин [кол-во]")
            return
        try:
            amount = int(args[0])
        except:
            self.send_message(peer_id, "❌ Число")
            return
        if amount <= 0:
            self.send_message(peer_id, "❌ >0")
            return
        u = self.get_user(user_id)
        if u.get('richcoin',0) < amount:
            self.send_message(peer_id, f"❌ У вас {u.get('richcoin',0)} RC")
            return
        price = self.get_richcoin_price()
        income = int(price * amount * 0.95)
        self.update_user(user_id, {'money': u['money'] + income, 'richcoin': u.get('richcoin',0) - amount})
        self.set_richcoin_price(int(price * 0.95))
        self.send_message(peer_id, f"✅ Продано {amount} RC за {income}")
    
    # ==================== БИЗНЕСЫ ====================
    
    def cmd_business(self, peer_id, user_id, args):
        businesses = supabase.table('businesses').select('*').execute().data
        my = supabase.table('user_businesses').select('*, businesses(*)').eq('user_id', user_id).execute().data
        text = "🏢 БИЗНЕСЫ:\n\n"
        for b in businesses:
            text += f"📌 {b['name']}\n   💰 {b['price']}\n   ⏱ +{b['income_per_hour']}/час\n\n"
        if my:
            text += "📋 ВАШИ БИЗНЕСЫ:\n"
            for m in my:
                b = m['businesses']
                last = datetime.fromisoformat(m['last_collected'].replace('Z', '+00:00'))
                hours = (datetime.now() - last).total_seconds() / 3600
                pending = int(b['income_per_hour'] * min(hours, 24))
                text += f"• {b['name']} - готово +{pending}\n"
            text += "\n!собрать - собрать доход"
        else:
            text += "\n❌ Нет бизнесов\n!купитьбизнес [название]"
        self.send_message(peer_id, text)
    
    def cmd_buy_business(self, peer_id, user_id, args):
        if not args:
            self.send_message(peer_id, "❌ !купитьбизнес [название]")
            return
        name = ' '.join(args).lower()
        biz = supabase.table('businesses').select('*').ilike('name', f'%{name}%').execute().data
        if not biz:
            self.send_message(peer_id, "❌ Бизнес не найден")
            return
        b = biz[0]
        u = self.get_user(user_id)
        exist = supabase.table('user_businesses').select('*').eq('user_id', user_id).eq('business_id', b['id']).execute().data
        if exist:
            self.send_message(peer_id, f"❌ У вас уже есть {b['name']}")
            return
        if u['money'] < b['price']:
            self.send_message(peer_id, f"❌ Нужно {b['price']}")
            return
        self.update_user(user_id, {'money': u['money'] - b['price']})
        supabase.table('user_businesses').insert({'user_id': user_id, 'business_id': b['id'], 'last_collected': datetime.now().isoformat()}).execute()
        self.send_message(peer_id, f"✅ Куплен {b['name']} за {b['price']}!")
    
    def cmd_collect_business(self, peer_id, user_id, args):
        my = supabase.table('user_businesses').select('*, businesses(*)').eq('user_id', user_id).execute().data
        if not my:
            self.send_message(peer_id, "❌ Нет бизнесов")
            return
        u = self.get_user(user_id)
        total = 0
        for m in my:
            b = m['businesses']
            last = datetime.fromisoformat(m['last_collected'].replace('Z', '+00:00'))
            hours = (datetime.now() - last).total_seconds() / 3600
            income = int(b['income_per_hour'] * min(hours, 24))
            total += income
            supabase.table('user_businesses').update({'last_collected': datetime.now().isoformat()}).eq('user_id', user_id).eq('business_id', b['id']).execute()
        if total > 0:
            self.update_user(user_id, {'money': u['money'] + total})
            self.send_message(peer_id, f"💰 +{total} с бизнесов!")
        else:
            self.send_message(peer_id, "⏰ Накоплений нет")
    
    # ==================== ОДЕЖДА ====================
    
    def cmd_wardrobe(self, peer_id, user_id, args):
        clothes = supabase.table('user_clothes').select('*, clothes(*)').eq('user_id', user_id).execute().data
        if not clothes:
            self.send_message(peer_id, "❌ Нет одежды\n!админ одежда [id] [название] - выдать")
            return
        text = "👔 ГАРДЕРОБ:\n\n"
        eq = [c['clothes']['name'] for c in clothes if c.get('equipped')]
        not_eq = [c['clothes']['name'] for c in clothes if not c.get('equipped')]
        if eq:
            text += "✅ НАДЕТО:\n" + "\n".join(f"• {n}" for n in eq) + "\n\n"
        if not_eq:
            text += "📦 В ШКАФУ:\n" + "\n".join(f"• {n}" for n in not_eq) + "\n\n"
        text += "!надеть [название]\n!снять [название]"
        self.send_message(peer_id, text)
    
    def cmd_wear(self, peer_id, user_id, args):
        if not args:
            self.send_message(peer_id, "❌ !надеть [название]")
            return
        name = ' '.join(args).lower()
        clothes = supabase.table('user_clothes').select('*, clothes(*)').eq('user_id', user_id).execute().data
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
        clothes = supabase.table('user_clothes').select('*, clothes(*)').eq('user_id', user_id).execute().data
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
        cloth = supabase.table('clothes').select('*').ilike('name', name).execute().data
        if not cloth:
            cloth = supabase.table('clothes').select('*').ilike('name', f'%{name}%').execute().data
        if not cloth:
            self.send_message(peer_id, "❌ Одежда не найдена")
            return
        c = cloth[0]
        users = supabase.table('users').select('user_id').execute().data
        ok = 0
        already = 0
        for u in users:
            ex = supabase.table('user_clothes').select('*').eq('user_id', u['user_id']).eq('clothes_id', c['id']).execute().data
            if ex:
                already += 1
                continue
            supabase.table('user_clothes').insert({'user_id': u['user_id'], 'clothes_id': c['id'], 'equipped': False}).execute()
            try:
                self.vk.messages.send(user_id=u['user_id'], message=f"🎁 Вам выдали {c['name']}!", random_id=random.randint(1,9999999))
            except:
                pass
            ok += 1
            time.sleep(0.05)
        self.send_message(peer_id, f"✅ Выдано {ok} игрокам\n📦 У {already} уже было")
    
    def cmd_mass_mailing(self, peer_id, user_id, args):
        if user_id != ADMIN_ID:
            self.send_message(peer_id, "❌ Нет прав")
            return
        if not args:
            self.send_message(peer_id, "❌ !рассылка [текст]")
            return
        text = ' '.join(args)
        users = supabase.table('users').select('user_id').execute().data
        sent = 0
        for u in users:
            try:
                self.vk.messages.send(user_id=u['user_id'], message=f"📢 {text}", random_id=random.randint(1,9999999))
                sent += 1
                time.sleep(0.05)
            except:
                pass
        self.send_message(peer_id, f"✅ Отправлено {sent}")
    
    def cmd_top(self, peer_id, user_id, args):
        users = supabase.table('users').select('user_id, money, level').order('money', desc=True).limit(10).execute().data
        if not users:
            self.send_message(peer_id, "📊 Нет игроков")
            return
        text = "🏆 ТОП-10 БОГАЧЕЙ:\n\n"
        for i, u in enumerate(users, 1):
            text += f"{i}. {u['user_id']} - {u['money']} (Ур.{u['level']})\n"
        self.send_message(peer_id, text)
    
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
                self.send_message(peer_id, f"✅ +{amount} пользователю {target}")
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
                cloth = supabase.table('clothes').select('*').ilike('name', name).execute().data
                if not cloth:
                    cloth = supabase.table('clothes').select('*').ilike('name', f'%{name}%').execute().data
                if not cloth:
                    self.send_message(peer_id, "❌ Одежда не найдена")
                    return
                c = cloth[0]
                ex = supabase.table('user_clothes').select('*').eq('user_id', target).eq('clothes_id', c['id']).execute().data
                if ex:
                    self.send_message(peer_id, "❌ У пользователя уже есть эта одежда")
                    return
                supabase.table('user_clothes').insert({'user_id': target, 'clothes_id': c['id'], 'equipped': False}).execute()
                self.send_message(peer_id, f"✅ Выдана {c['name']} пользователю {target}")
                try:
                    self.vk.messages.send(user_id=target, message=f"🎁 Вам выдали {c['name']}!", random_id=random.randint(1,9999999))
                except:
                    pass
            except:
                self.send_message(peer_id, "❌ Ошибка")
        elif action == 'бан' and len(args) >= 2:
            try:
                target = int(args[1])
                supabase.table('blacklist').insert({'user_id': target}).execute()
                self.send_message(peer_id, f"✅ Забанен {target}")
            except:
                self.send_message(peer_id, "❌ Ошибка")
        elif action == 'разбан' and len(args) >= 2:
            try:
                target = int(args[1])
                supabase.table('blacklist').delete().eq('user_id', target).execute()
                self.send_message(peer_id, f"✅ Разбанен {target}")
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
                self.send_message(peer_id, f"✅ Прогресс пользователя {target} сброшен")
            except:
                self.send_message(peer_id, "❌ Ошибка")
        elif action == 'стата':
            users = supabase.table('users').select('*', count='exact').execute()
            clans = supabase.table('clans').select('*', count='exact').execute()
            price = self.get_richcoin_price()
            self.send_message(peer_id, f"📊 СТАТИСТИКА:\n👥 Игроков: {users.count}\n🏆 Кланов: {clans.count}\n🪙 Цена Ричкоина: {price}")
    
    # ==================== ОСНОВНОЙ ЦИКЛ ====================
    
    def run(self):
        print("Бот слушает...")
        processed = set()
        while True:
            try:
                for event in self.longpoll.listen():
                    if event.type == VkEventType.MESSAGE_NEW and event.user_id != self.bot_id:
                        key = f"{event.peer_id}_{event.message_id}"
                        if key in processed:
                            continue
                        processed.add(key)
                        if len(processed) > 500:
                            processed.clear()
                        text = event.text.strip()
                        if not text:
                            continue
                        if event.peer_id == event.user_id or text.startswith('!'):
                            if text.startswith('!'):
                                text = text[1:]
                            parts = text.lower().split()
                            if not parts:
                                continue
                            cmd = parts[0]
                            args = parts[1:]
                            reply = self.get_reply_id(event)
                            try:
                                if cmd == 'передать':
                                    self.cmd_transfer(event.peer_id, event.user_id, args, reply)
                                elif cmd == 'дуэль':
                                    self.cmd_duel(event.peer_id, event.user_id, args, reply)
                                elif cmd == 'ограбить':
                                    self.cmd_rob(event.peer_id, event.user_id, args, reply)
                                elif cmd in self.commands:
                                    self.commands[cmd](event.peer_id, event.user_id, args)
                            except Exception as e:
                                print(f"Ошибка: {e}")
                                self.send_message(event.peer_id, "❌ Ошибка")
            except Exception as e:
                print(f"Longpoll error: {e}")
                time.sleep(5)

def run_web():
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

if __name__ == "__main__":
    print("Запуск...")
    threading.Thread(target=run_web, daemon=True).start()
    bot = RichBot()
    bot.run()
