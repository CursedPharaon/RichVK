import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType
import random
import os
import re
from datetime import datetime, timedelta
from supabase import create_client, Client
from flask import Flask
import threading

# Получаем переменные окружения
VK_TOKEN = os.environ.get('VK_TOKEN')
SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY')
ADMIN_ID = int(os.environ.get('ADMIN_ID', 0))

# Инициализация Supabase
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Flask приложение для Render
app = Flask(__name__)

@app.route('/')
def health_check():
    return "Бот Рич работает!"

class RichBot:
    def __init__(self):
        self.vk_session = vk_api.VkApi(token=VK_TOKEN)
        self.vk = self.vk_session.get_api()
        self.longpoll = VkLongPoll(self.vk_session)
        
        self.start_money = 1000
        self.currency_symbol = "💰 Ричей"
        
        # Конфиг работ
        self.jobs = {
            'программист': {'money': (500, 1000), 'energy': 20},
            'грузчик': {'money': (200, 500), 'energy': 15},
            'таксист': {'money': (300, 600), 'energy': 15},
            'официант': {'money': (200, 400), 'energy': 10},
            'шаурмист': {'money': (400, 700), 'energy': 20}
        }
        
        # Команды
        self.commands = {
            'начать': self.cmd_start,
            'баланс': self.cmd_balance,
            'работы': self.cmd_jobs,
            'работа': self.cmd_work,
            'казино': self.cmd_casino,
            'создать_клан': self.cmd_create_clan,
            'вступить': self.cmd_join_clan,
            'клан': self.cmd_clan_info,
            'мафия': self.cmd_mafia,
            'вступить_в_мафию': self.cmd_join_mafia,
            'ограбить': self.cmd_rob,
            'дуэль': self.cmd_duel,
            'принять_дуэль': self.cmd_accept_duel,
            'отклонить_дуэль': self.cmd_decline_duel,
            'топ': self.cmd_top,
            'реф': self.cmd_ref,
            'админ': self.cmd_admin
        }
        
        print("✅ Бот Рич (Supabase) запущен!")
    
    def extract_ref_from_message(self, text):
        """Извлечь ref из текста сообщения"""
        # Ищем ref=123 или ?ref=123 или &ref=123
        patterns = [
            r'ref[=:]\s*(\d+)',
            r'\?ref=(\d+)',
            r'&ref=(\d+)',
            r'начать\s+ref[=:]\s*(\d+)',
            r'https?://vk\.com/[^\s]+\?ref=(\d+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return int(match.group(1))
        return None
    
    def get_user(self, user_id):
        """Получить или создать пользователя"""
        try:
            result = supabase.table('users').select('*').eq('user_id', user_id).execute()
            
            if not result.data:
                # Создаем нового пользователя
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
                    'referrer': None,
                    'referrals_count': 0
                }
                supabase.table('users').insert(new_user).execute()
                return new_user
            
            return result.data[0]
        except Exception as e:
            print(f"Ошибка get_user: {e}")
            return None
    
    def update_user(self, user_id, data):
        """Обновить данные пользователя"""
        try:
            supabase.table('users').update(data).eq('user_id', user_id).execute()
        except Exception as e:
            print(f"Ошибка update_user: {e}")
    
    def send_message(self, user_id, message):
        """Отправить сообщение"""
        try:
            self.vk.messages.send(
                user_id=user_id,
                message=message[:4000],
                random_id=random.randint(1, 999999)
            )
        except Exception as e:
            print(f"Ошибка отправки: {e}")
    
    def check_blacklist(self, user_id):
        """Проверка в черном списке"""
        try:
            result = supabase.table('blacklist').select('*').eq('user_id', user_id).execute()
            return len(result.data) > 0
        except:
            return False
    
    def check_cooldown(self, user_id, action, minutes):
        """Проверка кулдауна"""
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
    
    def generate_referral_link(self, user_id):
        """Сгенерировать реферальную ссылку с параметром ref"""
        try:
            user_info = self.vk.users.get(user_ids=user_id)[0]
            screen_name = user_info['screen_name']
            return f"https://vk.com/{screen_name}?ref={user_id}"
        except:
            return f"https://vk.com/id{user_id}?ref={user_id}"
    
    def process_referral(self, new_user_id, referrer_id):
        """Обработка реферальной привязки"""
        if new_user_id == referrer_id:
            return False
        
        # Проверяем, не привязан ли уже
        new_user = self.get_user(new_user_id)
        if not new_user:
            return False
        
        if new_user.get('referrer'):
            return False
        
        # Проверяем, существует ли реферер
        referrer = self.get_user(referrer_id)
        if not referrer:
            return False
        
        # Привязываем реферала
        self.update_user(new_user_id, {'referrer': referrer_id})
        
        # Начисляем бонусы
        bonus = 500
        
        # Бонус новому игроку
        self.update_user(new_user_id, {'money': new_user['money'] + bonus})
        
        # Бонус рефереру
        self.update_user(referrer_id, {
            'money': referrer['money'] + bonus,
            'referrals_count': referrer['referrals_count'] + 1
        })
        
        # Записываем награду
        supabase.table('referral_rewards').insert({
            'referrer_id': referrer_id,
            'referred_id': new_user_id,
            'reward_amount': bonus,
            'claimed': False
        }).execute()
        
        # Проверяем достижения (каждые 5 рефералов)
        new_count = referrer['referrals_count'] + 1
        if new_count % 5 == 0:
            achievement_bonus = 1000
            self.update_user(referrer_id, {'money': referrer['money'] + achievement_bonus})
            supabase.table('referral_rewards').insert({
                'referrer_id': referrer_id,
                'referred_id': None,
                'reward_amount': achievement_bonus,
                'claimed': False
            }).execute()
            self.send_message(referrer_id, f"🎉 ДОСТИЖЕНИЕ! Ты пригласил {new_count} друзей и получил +{achievement_bonus} {self.currency_symbol}!")
        
        self.send_message(referrer_id, f"🎉 По твоей ссылке зарегистрировался новый игрок! Ты получил +{bonus} {self.currency_symbol}!")
        self.send_message(new_user_id, f"🎁 Ты получил +{bonus} {self.currency_symbol} за регистрацию по реферальной ссылке!")
        
        return True
    
    def get_available_bonus(self, user_id):
        """Получить сумму доступных бонусов за рефералов"""
        try:
            rewards = supabase.table('referral_rewards').select('reward_amount').eq('referrer_id', user_id).eq('claimed', False).execute()
            if not rewards.data:
                return 0
            return sum(r.get('reward_amount', 0) for r in rewards.data)
        except:
            return 0
    
    def cmd_start(self, user_id, args):
        # Проверяем наличие реферального параметра в сообщении
        full_message = ' '.join(args) if args else ''
        ref_id = self.extract_ref_from_message(full_message)
        
        # Если есть реферал и пользователь новый - обрабатываем
        if ref_id:
            # Проверяем, существует ли пользователь
            existing = supabase.table('users').select('*').eq('user_id', user_id).execute()
            if not existing.data:
                # Новый пользователь - обрабатываем реферала
                self.process_referral(user_id, ref_id)
        
        user = self.get_user(user_id)
        if not user:
            self.send_message(user_id, "❌ Ошибка! Попробуй позже")
            return
        
        # Показываем реферальную ссылку в приветствии
        ref_link = self.generate_referral_link(user_id)
        
        self.send_message(
            user_id,
            f"🌟 Добро пожаловать в Rich!\n\n"
            f"💰 Баланс: {user['money']}\n"
            f"⚡ Энергия: {user['energy']}%\n"
            f"🏆 Уровень: {user['level']}\n\n"
            f"🔗 Твоя реферальная ссылка:\n{ref_link}\n"
            f"📌 Отправь её другу, и вы оба получите +500 монет!\n\n"
            f"📜 Команды:\n"
            f"• баланс - проверка денег\n"
            f"• работы - список работ\n"
            f"• работа [название] - работать\n"
            f"• казино [игра] [ставка] - играть\n"
            f"• создать_клан [название]\n"
            f"• вступить [клан]\n"
            f"• дуэль [id] [ставка]\n"
            f"• ограбить [id]\n"
            f"• реф - реферальная система\n"
            f"• топ - таблица лидеров"
        )
    
    def cmd_balance(self, user_id, args):
        user = self.get_user(user_id)
        if not user:
            self.send_message(user_id, "❌ Ошибка!")
            return
            
        self.send_message(
            user_id,
            f"💰 Баланс: {user['money']} {self.currency_symbol}\n"
            f"⚡ Энергия: {user['energy']}%\n"
            f"🏆 Уровень: {user['level']}\n"
            f"🎯 Побед в дуэлях: {user['duels_won']}\n"
            f"💀 Поражений: {user['duels_lost']}"
        )
    
    def cmd_jobs(self, user_id, args):
        text = "📋 Работы:\n\n"
        for name, data in self.jobs.items():
            text += f"📌 {name}\n"
            text += f"   💰 {data['money'][0]}-{data['money'][1]}\n"
            text += f"   ⚡ Тратит: {data['energy']} энергии\n\n"
        self.send_message(user_id, text)
    
    def cmd_work(self, user_id, args):
        if not args:
            self.send_message(user_id, "❌ Укажи работу: работа программист")
            return
        
        job_name = args[0].lower()
        if job_name not in self.jobs:
            self.send_message(user_id, "❌ Нет такой работы")
            return
        
        user = self.get_user(user_id)
        if not user:
            self.send_message(user_id, "❌ Ошибка!")
            return
        
        if user['job'] != job_name:
            self.update_user(user_id, {'job': job_name})
            self.send_message(user_id, f"✅ Ты устроился на {job_name}!")
            return
        
        # Проверка кулдауна
        can_work, remaining = self.check_cooldown(user_id, 'work', 10)
        if not can_work:
            self.send_message(user_id, f"⏰ Отдыхай! Следующая работа через {remaining} мин")
            return
        
        if user['energy'] < self.jobs[job_name]['energy']:
            self.send_message(user_id, f"❌ Мало энергии! Нужно {self.jobs[job_name]['energy']}")
            return
        
        # Работаем
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
        
        self.send_message(
            user_id,
            f"✅ Ты поработал на {job_name}!\n"
            f"💰 +{earned}\n"
            f"⚡ Энергия: {new_energy}%{level_msg}"
        )
    
    def cmd_casino(self, user_id, args):
        if len(args) < 2:
            self.send_message(user_id, "❌ Использование: казино [орёл_решка/кости] [ставка]")
            return
        
        game = args[0].lower()
        try:
            bet = int(args[1])
        except:
            self.send_message(user_id, "❌ Ставка - число!")
            return
        
        user = self.get_user(user_id)
        if not user:
            self.send_message(user_id, "❌ Ошибка!")
            return
        
        if bet <= 0 or bet > user['money']:
            self.send_message(user_id, f"❌ Неверная ставка! У тебя {user['money']}")
            return
        
        result = ""
        new_money = user['money']
        
        if game == "орёл_решка":
            if len(args) < 3:
                self.send_message(user_id, "❌ Укажи орёл или решка!")
                return
            
            choice = args[2].lower()
            if choice not in ['орёл', 'орел', 'решка']:
                self.send_message(user_id, "❌ Выбери орёл или решка!")
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
            self.send_message(user_id, "❌ Игры: орёл_решка, кости")
            return
        
        if new_money != user['money']:
            self.update_user(user_id, {'money': new_money})
        
        self.send_message(user_id, f"{result}\n💰 Новый баланс: {new_money}")
    
    def cmd_create_clan(self, user_id, args):
        if not args:
            self.send_message(user_id, "❌ Название клана!")
            return
        
        clan_name = ' '.join(args)
        
        # Проверка существования клана
        existing = supabase.table('clans').select('*').eq('name', clan_name).execute()
        if existing.data:
            self.send_message(user_id, "❌ Клан уже есть!")
            return
        
        user = self.get_user(user_id)
        if not user:
            return
        
        if user['clan']:
            self.send_message(user_id, "❌ Ты уже в клане!")
            return
        
        if user['money'] < 5000:
            self.send_message(user_id, f"❌ Нужно 5000! У тебя {user['money']}")
            return
        
        # Создаем клан
        supabase.table('clans').insert({
            'name': clan_name,
            'owner': user_id,
            'money': 0
        }).execute()
        
        supabase.table('clan_members').insert({
            'clan_name': clan_name,
            'user_id': user_id
        }).execute()
        
        self.update_user(user_id, {
            'money': user['money'] - 5000,
            'clan': clan_name
        })
        
        self.send_message(user_id, f"✅ Клан '{clan_name}' создан!")
    
    def cmd_join_clan(self, user_id, args):
        if not args:
            self.send_message(user_id, "❌ Название клана!")
            return
        
        clan_name = ' '.join(args)
        
        # Проверка существования
        clan = supabase.table('clans').select('*').eq('name', clan_name).execute()
        if not clan.data:
            self.send_message(user_id, "❌ Клан не найден!")
            return
        
        user = self.get_user(user_id)
        if not user:
            return
        
        if user['clan']:
            self.send_message(user_id, "❌ Ты уже в клане!")
            return
        
        # Вступаем
        supabase.table('clan_members').insert({
            'clan_name': clan_name,
            'user_id': user_id
        }).execute()
        
        self.update_user(user_id, {'clan': clan_name})
        self.send_message(user_id, f"✅ Ты в клане '{clan_name}'!")
    
    def cmd_clan_info(self, user_id, args):
        user = self.get_user(user_id)
        if not user:
            return
        
        if not user['clan']:
            self.send_message(user_id, "❌ Ты не в клане!")
            return
        
        clan = supabase.table('clans').select('*').eq('name', user['clan']).execute()
        members = supabase.table('clan_members').select('*').eq('clan_name', user['clan']).execute()
        
        if not clan.data:
            self.send_message(user_id, "❌ Клан не найден!")
            return
        
        clan_data = clan.data[0]
        
        self.send_message(
            user_id,
            f"🏆 Клан: {user['clan']}\n"
            f"👑 Владелец: @id{clan_data['owner']}\n"
            f"👥 Участников: {len(members.data)}\n"
            f"💰 Казна: {clan_data['money']}\n"
            f"📅 Создан: {clan_data['created_at'][:10]}"
        )
    
    def cmd_mafia(self, user_id, args):
        user = self.get_user(user_id)
        if not user:
            return
        
        if not user['mafia']:
            self.send_message(user_id, "❌ Ты не в мафии! Используй 'вступить_в_мафию' [название]")
            return
        
        mafia = supabase.table('mafia').select('*').eq('name', user['mafia']).execute()
        members = supabase.table('mafia_members').select('*').eq('mafia_name', user['mafia']).execute()
        
        self.send_message(
            user_id,
            f"🔫 Мафия: {user['mafia']}\n"
            f"👥 Участников: {len(members.data)}\n"
            f"💰 Общак: {mafia.data[0]['money'] if mafia.data else 0}"
        )
    
    def cmd_join_mafia(self, user_id, args):
        if not args:
            self.send_message(user_id, "❌ Название мафии!")
            return
        
        mafia_name = ' '.join(args)
        
        user = self.get_user(user_id)
        if not user:
            return
        
        if user['mafia']:
            self.send_message(user_id, "❌ Ты уже в мафии!")
            return
        
        # Проверяем или создаем мафию
        mafia = supabase.table('mafia').select('*').eq('name', mafia_name).execute()
        
        if not mafia.data:
            # Создаем новую мафию
            supabase.table('mafia').insert({
                'name': mafia_name,
                'boss': user_id,
                'money': 0
            }).execute()
        
        # Добавляем участника
        supabase.table('mafia_members').insert({
            'mafia_name': mafia_name,
            'user_id': user_id
        }).execute()
        
        self.update_user(user_id, {'mafia': mafia_name})
        self.send_message(user_id, f"✅ Ты в мафии '{mafia_name}'!")
    
    def cmd_rob(self, user_id, args):
        if not args:
            self.send_message(user_id, "❌ Кого грабить? ID пользователя")
            return
        
        try:
            target_id = int(args[0])
        except:
            self.send_message(user_id, "❌ ID должен быть числом!")
            return
        
        if target_id == user_id:
            self.send_message(user_id, "❌ Нельзя грабить себя!")
            return
        
        user = self.get_user(user_id)
        target = self.get_user(target_id)
        
        if not user or not target:
            self.send_message(user_id, "❌ Ошибка!")
            return
        
        # Проверка кулдауна
        can_rob, remaining = self.check_cooldown(user_id, 'rob', 30)
        if not can_rob:
            self.send_message(user_id, f"⏰ Следующий грабеж через {remaining} мин")
            return
        
        # Шанс успеха
        success = random.random() < 0.6
        
        if success:
            rob_amount = random.randint(50, min(300, target['money']))
            if rob_amount > target['money']:
                rob_amount = target['money']
            
            self.update_user(user_id, {
                'money': user['money'] + rob_amount,
                'last_rob': datetime.now().isoformat()
            })
            self.update_user(target_id, {'money': target['money'] - rob_amount})
            
            self.send_message(user_id, f"🔫 Успешно! Ты ограбил @id{target_id} на {rob_amount}!")
            self.send_message(target_id, f"⚠️ Тебя ограбил @id{user_id} на {rob_amount}!")
        else:
            # Штраф за провал
            penalty = random.randint(50, 150)
            new_money = max(0, user['money'] - penalty)
            
            self.update_user(user_id, {
                'money': new_money,
                'last_rob': datetime.now().isoformat()
            })
            self.send_message(user_id, f"❌ Провал! Тебя поймали, штраф {penalty}!")
    
    def cmd_duel(self, user_id, args):
        if len(args) < 2:
            self.send_message(user_id, "❌ Использование: дуэль [id] [ставка]")
            return
        
        try:
            opponent_id = int(args[0])
            bet = int(args[1])
        except:
            self.send_message(user_id, "❌ ID и ставка должны быть числами!")
            return
        
        if opponent_id == user_id:
            self.send_message(user_id, "❌ С собой нельзя!")
            return
        
        user = self.get_user(user_id)
        opponent = self.get_user(opponent_id)
        
        if not user or not opponent:
            self.send_message(user_id, "❌ Игрок не найден!")
            return
        
        if bet <= 0 or bet > user['money']:
            self.send_message(user_id, f"❌ Неверная ставка! У тебя {user['money']}")
            return
        
        # Создаем дуэль
        supabase.table('duels').insert({
            'challenger': user_id,
            'opponent': opponent_id,
            'bet': bet,
            'status': 'pending'
        }).execute()
        
        self.send_message(user_id, f"⚔️ Ты вызвал @id{opponent_id} на дуэль! Ставка: {bet}\n"
                                   f"Для принятия: принять_дуэль {bet}")
        
        self.send_message(opponent_id, f"⚔️ @id{user_id} вызывает тебя на дуэль!\n"
                                       f"💰 Ставка: {bet}\n"
                                       f"✅ принять_дуэль {bet}")
    
    def cmd_accept_duel(self, user_id, args):
        if not args:
            self.send_message(user_id, "❌ Укажи ставку")
            return
        
        try:
            bet = int(args[0])
        except:
            self.send_message(user_id, "❌ Ставка должна быть числом!")
            return
        
        # Ищем дуэль
        duel = supabase.table('duels').select('*').eq('opponent', user_id).eq('bet', bet).eq('status', 'pending').execute()
        
        if not duel.data:
            self.send_message(user_id, "❌ Нет активных приглашений!")
            return
        
        duel_data = duel.data[0]
        challenger_id = duel_data['challenger']
        
        challenger = self.get_user(challenger_id)
        opponent = self.get_user(user_id)
        
        if not challenger or not opponent:
            self.send_message(user_id, "❌ Ошибка!")
            return
        
        if bet > opponent['money']:
            self.send_message(user_id, f"❌ Не хватает денег! Нужно {bet}")
            return
        
        # Забираем ставки
        self.update_user(challenger_id, {'money': challenger['money'] - bet})
        self.update_user(user_id, {'money': opponent['money'] - bet})
        
        # Дуэль
        challenger_power = random.randint(1, 100) + challenger['level'] * 5
        opponent_power = random.randint(1, 100) + opponent['level'] * 5
        
        winner_id = challenger_id if challenger_power > opponent_power else user_id
        winner_prize = bet * 2
        
        # Обновляем победителя
        winner = self.get_user(winner_id)
        self.update_user(winner_id, {'money': winner['money'] + winner_prize})
        
        # Обновляем статистику
        if winner_id == challenger_id:
            self.update_user(challenger_id, {'duels_won': challenger['duels_won'] + 1})
            self.update_user(user_id, {'duels_lost': opponent['duels_lost'] + 1})
        else:
            self.update_user(user_id, {'duels_won': opponent['duels_won'] + 1})
            self.update_user(challenger_id, {'duels_lost': challenger['duels_lost'] + 1})
        
        # Закрываем дуэль
        supabase.table('duels').update({'status': 'completed'}).eq('duel_id', duel_data['duel_id']).execute()
        
        self.send_message(user_id, f"⚔️ ПОБЕДИТЕЛЬ: @id{winner_id}\n💰 Выигрыш: {winner_prize}")
        self.send_message(challenger_id, f"⚔️ ПОБЕДИТЕЛЬ: @id{winner_id}\n💰 Выигрыш: {winner_prize}")
    
    def cmd_decline_duel(self, user_id, args):
        if not args:
            self.send_message(user_id, "❌ Укажи ставку")
            return
        
        try:
            bet = int(args[0])
        except:
            self.send_message(user_id, "❌ Ставка должна быть числом!")
            return
        
        # Закрываем дуэль
        result = supabase.table('duels').update({'status': 'declined'}).eq('opponent', user_id).eq('bet', bet).eq('status', 'pending').execute()
        
        if result.data:
            self.send_message(user_id, "❌ Ты отклонил дуэль!")
            challenger_id = result.data[0]['challenger']
            self.send_message(challenger_id, f"❌ @id{user_id} отклонил дуэль!")
    
    def cmd_top(self, user_id, args):
        users = supabase.table('users').select('user_id, money, level').order('money', desc=True).limit(10).execute()
        
        if not users.data:
            self.send_message(user_id, "📊 Пока нет игроков!")
            return
        
        text = "🏆 ТОП-10 БОГАЧЕЙ:\n\n"
        for i, user in enumerate(users.data, 1):
            text += f"{i}. @id{user['user_id']} - {user['money']} {self.currency_symbol} (Ур. {user['level']})\n"
        
        self.send_message(user_id, text)
    
    def cmd_ref(self, user_id, args):
        """Реферальная система"""
        user = self.get_user(user_id)
        if not user:
            return
        
        if not args:
            referrers = supabase.table('users').select('user_id').eq('referrer', user_id).execute()
            rewards = supabase.table('referral_rewards').select('reward_amount').eq('referrer_id', user_id).eq('claimed', False).execute()
            total_bonus = sum(r.get('reward_amount', 0) for r in rewards.data) if rewards.data else 0
            
            referrer_info = ""
            if user.get('referrer'):
                referrer_info = f"\n👤 Пригласил: @id{user['referrer']}"
            
            ref_link = self.generate_referral_link(user_id)
            
            self.send_message(
                user_id,
                f"🌟 РЕФЕРАЛЬНАЯ СИСТЕМА\n\n"
                f"🔗 Твоя ссылка:\n{ref_link}\n\n"
                f"📊 Статистика:\n"
                f"• Приглашено: {user['referrals_count']}\n"
                f"• Накоплено бонусов: {total_bonus} {self.currency_symbol}{referrer_info}\n\n"
                f"💡 Как это работает:\n"
                f"1. Отправь ссылку другу\n"
                f"2. Друг переходит по ссылке и пишет 'начать'\n"
                f"3. Вы оба получаете +500 {self.currency_symbol}\n"
                f"4. За каждые 5 приглашений +1000 бонусом!\n\n"
                f"🎁 Команды:\n"
                f"• реф бонус - забрать накопленный бонус\n"
                f"• реф топ - топ приглашающих"
            )
            return
        
        subcmd = args[0].lower()
        
        if subcmd == "бонус":
            available = self.get_available_bonus(user_id)
            
            if available <= 0:
                self.send_message(user_id, "❌ Нет доступных бонусов!")
                return
            
            self.update_user(user_id, {'money': user['money'] + available})
            supabase.table('referral_rewards').update({'claimed': True}).eq('referrer_id', user_id).eq('claimed', False).execute()
            self.send_message(user_id, f"✅ Ты получил {available} {self.currency_symbol}!")
        
        elif subcmd == "топ":
            referrers_stats = supabase.table('users').select('user_id, referrals_count').gte('referrals_count', 1).order('referrals_count', desc=True).limit(10).execute()
            
            if not referrers_stats.data:
                self.send_message(user_id, "📊 Пока нет приглашений!")
                return
            
            text = "🏆 ТОП ПРИГЛАШАЮЩИХ:\n\n"
            for i, stat in enumerate(referrers_stats.data, 1):
                text += f"{i}. @id{stat['user_id']} - {stat['referrals_count']} приглашений\n"
            
            self.send_message(user_id, text)
        
        else:
            self.send_message(user_id, "❌ Использование: реф [бонус/топ]")
    
    def cmd_admin(self, user_id, args):
        if user_id != ADMIN_ID:
            self.send_message(user_id, "❌ Нет прав!")
            return
        
        if not args:
            self.send_message(user_id, "👑 Админ команды:\n\n"
                                      "• админ дать [id] [сумма] - выдать валюту\n"
                                      "• админ бан [id] - забанить\n"
                                      "• админ разбан [id] - разбанить\n"
                                      "• админ сброс [id] - сбросить прогресс\n"
                                      "• админ стата - статистика бота")
            return
        
        action = args[0].lower()
        
        if action == 'дать' and len(args) >= 3:
            try:
                target_id = int(args[1])
                amount = int(args[2])
            except:
                self.send_message(user_id, "❌ ID и сумма - числа!")
                return
            
            target = self.get_user(target_id)
            if target:
                self.update_user(target_id, {'money': target['money'] + amount})
                self.send_message(user_id, f"✅ Выдано {amount} @id{target_id}")
        
        elif action == 'бан' and len(args) >= 2:
            try:
                target_id = int(args[1])
                supabase.table('blacklist').insert({'user_id': target_id}).execute()
                self.send_message(user_id, f"✅ @id{target_id} в ЧС")
            except:
                self.send_message(user_id, "❌ Ошибка!")
        
        elif action == 'разбан' and len(args) >= 2:
            try:
                target_id = int(args[1])
                supabase.table('blacklist').delete().eq('user_id', target_id).execute()
                self.send_message(user_id, f"✅ @id{target_id} из ЧС")
            except:
                self.send_message(user_id, "❌ Ошибка!")
        
        elif action == 'сброс' and len(args) >= 2:
            try:
                target_id = int(args[1])
                supabase.table('users').delete().eq('user_id', target_id).execute()
                supabase.table('clan_members').delete().eq('user_id', target_id).execute()
                supabase.table('mafia_members').delete().eq('user_id', target_id).execute()
                self.send_message(user_id, f"✅ Прогресс @id{target_id} сброшен")
            except:
                self.send_message(user_id, "❌ Ошибка!")
        
        elif action == 'стата':
            users_count = supabase.table('users').select('*', count='exact').execute()
            clans_count = supabase.table('clans').select('*', count='exact').execute()
            
            self.send_message(
                user_id,
                f"📊 СТАТИСТИКА БОТА:\n\n"
                f"👥 Игроков: {users_count.count}\n"
                f"🏆 Кланов: {clans_count.count}\n"
                f"💰 Стартовый капитал: {self.start_money}\n"
                f"💼 Работ: {len(self.jobs)}"
            )
    
    def run(self):
        print("🔄 Бот слушает сообщения...")
        for event in self.longpoll.listen():
            if event.type == VkEventType.MESSAGE_NEW and event.to_me:
                user_id = event.user_id
                message_text = event.text.strip()
                
                if not message_text:
                    continue
                
                # Проверка ЧС
                if self.check_blacklist(user_id):
                    self.send_message(user_id, "🚫 Ты в черном списке!")
                    continue
                
                message_lower = message_text.lower()
                parts = message_lower.split()
                command = parts[0]
                args = parts[1:] if len(parts) > 1 else []
                
                if command in self.commands:
                    try:
                        self.commands[command](user_id, args)
                    except Exception as e:
                        print(f"Ошибка в {command}: {e}")
                        self.send_message(user_id, "❌ Ошибка! Попробуй позже")

def run_web_server():
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

if __name__ == "__main__":
    # Запускаем веб-сервер в отдельном потоке
    web_thread = threading.Thread(target=run_web_server)
    web_thread.daemon = True
    web_thread.start()
    
    # Запускаем бота
    bot = RichBot()
    bot.run()
