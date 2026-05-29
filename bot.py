import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType
import random
import os
from datetime import datetime, timedelta
from supabase import create_client, Client

# Получаем переменные окружения
VK_TOKEN = os.environ.get('VK_TOKEN')
SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY')
ADMIN_ID = int(os.environ.get('ADMIN_ID', 0))

# Инициализация Supabase
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

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
            'админ': self.cmd_admin
        }
        
        print("✅ Бот Рич (Supabase) запущен!")
    
    def get_user(self, user_id):
        """Получить или создать пользователя"""
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
                'duels_lost': 0
            }
            supabase.table('users').insert(new_user).execute()
            return new_user
        
        return result.data[0]
    
    def update_user(self, user_id, data):
        """Обновить данные пользователя"""
        supabase.table('users').update(data).eq('user_id', user_id).execute()
    
    def send_message(self, user_id, message):
        """Отправить сообщение"""
        try:
            self.vk.messages.send(
                user_id=user_id,
                message=message,
                random_id=random.randint(1, 999999)
            )
        except Exception as e:
            print(f"Ошибка отправки: {e}")
    
    def check_blacklist(self, user_id):
        """Проверка в черном списке"""
        result = supabase.table('blacklist').select('*').eq('user_id', user_id).execute()
        return len(result.data) > 0
    
    def check_cooldown(self, user_id, action, minutes):
        """Проверка кулдауна"""
        user = self.get_user(user_id)
        last_time_str = user.get(f'last_{action}')
        
        if last_time_str:
            last_time = datetime.fromisoformat(last_time_str.replace('Z', '+00:00'))
            if datetime.now() - last_time < timedelta(minutes=minutes):
                remaining = timedelta(minutes=minutes) - (datetime.now() - last_time)
                return False, int(remaining.total_seconds() // 60)
        return True, 0
    
    def cmd_start(self, user_id, args):
        user = self.get_user(user_id)
        self.send_message(
            user_id,
            f"🌟 Добро пожаловать в Rich!\n\n"
            f"💰 Баланс: {user['money']}\n"
            f"⚡ Энергия: {user['energy']}%\n"
            f"🏆 Уровень: {user['level']}\n\n"
            f"📜 Команды:\n"
            f"• баланс - проверка денег\n"
            f"• работы - список работ\n"
            f"• работа [название] - работать\n"
            f"• казино [игра] [ставка] - играть\n"
            f"• создать_клан [название]\n"
            f"• вступить [клан]\n"
            f"• дуэль [id] [ставка]\n"
            f"• ограбить [id]\n"
            f"• топ - таблица лидеров"
        )
    
    def cmd_balance(self, user_id, args):
        user = self.get_user(user_id)
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
        
        if bet <= 0 or bet > user['money']:
            self.send_message(user_id, f"❌ Неверная ставка! У тебя {user['money']}")
            return
        
        result = ""
        
        if game == "орёл_решка":
            choice = args[2].lower() if len(args) > 2 else None
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
                new_money = user['money']
                result = f"🎲 {user_roll} vs {bot_roll}\n🤝 Ничья!"
        
        else:
            self.send_message(user_id, "❌ Игры: орёл_решка, кости")
            return
        
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
        
        if not user['mafia']:
            self.send_message(user_id, "❌ Ты не в мафии! Используй 'вступить_в_мафию'")
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
            self.send_message(user_id, "❌ Название мафии! Доступны: Братки, Мафиози, Гангстеры")
            return
        
        mafia_name = ' '.join(args)
        
        user = self.get_user(user_id)
        
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
        
        # Проверка кулдауна
        can_rob, remaining = self.check_cooldown(user_id, 'rob', 30)
        if not can_rob:
            self.send_message(user_id, f"⏰ Следующий грабеж через {remaining} мин")
            return
        
        # Шанс успеха
        success_chance = 0.6
        success = random.random() < success_chance
        
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
            self.update_user(user_id, {
                'money': user['money'] - penalty,
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
                                   f"Для принятия: принять_дуэль {bet}\n"
                                   f"Для отказа: отклонить_дуэль {bet}")
        
        self.send_message(opponent_id, f"⚔️ @id{user_id} вызывает тебя на дуэль!\n"
                                       f"💰 Ставка: {bet}\n"
                                       f"✅ принять_дуэль {bet}\n"
                                       f"❌ отклонить_дуэль {bet}")
    
    def cmd_accept_duel(self, user_id, args):
        if not args:
            self.send_message(user_id, "❌ Укажи ставку из приглашения")
            return
        
        try:
            bet = int(args[0])
        except:
            self.send_message(user_id, "❌ Ставка должна быть числом!")
            return
        
        # Ищем дуэль
        duel = supabase.table('duels').select('*').eq('opponent', user_id).eq('bet', bet).eq('status', 'pending').execute()
        
        if not duel.data:
            self.send_message(user_id, "❌ Нет активных приглашений с такой ставкой!")
            return
        
        duel_data = duel.data[0]
        challenger_id = duel_data['challenger']
        
        challenger = self.get_user(challenger_id)
        opponent = self.get_user(user_id)
        
        if bet > opponent['money']:
            self.send_message(user_id, f"❌ Не хватает денег на ставку! Нужно {bet}")
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
        
        self.send_message(user_id, f"⚔️ Результат дуэли:\n"
                                   f"@{challenger_id} vs @{user_id}\n"
                                   f"💰 Победитель получает {winner_prize}!\n"
                                   f"🏆 Победил @id{winner_id}")
        
        self.send_message(challenger_id, f"⚔️ Результат дуэли:\n"
                                         f"Ты vs @{user_id}\n"
                                         f"💰 Победитель получает {winner_prize}!\n"
                                         f"🏆 Победил @id{winner_id}")
    
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
        else:
            self.send_message(user_id, "❌ Нет активной дуэли с такой ставкой")
    
    def cmd_top(self, user_id, args):
        users = supabase.table('users').select('user_id, money, level').order('money', desc=True).limit(10).execute()
        
        text = "🏆 ТОП-10 БОГАЧЕЙ:\n\n"
        for i, user in enumerate(users.data, 1):
            text += f"{i}. @id{user['user_id']} - {user['money']} {self.currency_symbol} (Ур. {user['level']})\n"
        
        self.send_message(user_id, text)
    
    def cmd_admin(self, user_id, args):
        if user_id != ADMIN_ID:
            self.send_message(user_id, "❌ Нет прав!")
            return
        
        if not args:
            self.send_message(user_id, "Админ команды:\n"
                                      "админ дать [id] [сумма] - выдать валюту\n"
                                      "админ бан [id] - забанить\n"
                                      "админ разбан [id] - разбанить")
            return
        
        action = args[0].lower()
        
        if action == 'дать' and len(args) >= 3:
            try:
                target_id = int(args[1])
                amount = int(args[2])
            except:
                self.send_message(user_id, "❌ ID и сумма должны быть числами!")
                return
            
            target = self.get_user(target_id)
            self.update_user(target_id, {'money': target['money'] + amount})
            self.send_message(user_id, f"✅ Выдано {amount} пользователю @id{target_id}")
            self.send_message(target_id, f"💰 Админ выдал тебе {amount} {self.currency_symbol}!")
        
        elif action == 'бан' and len(args) >= 2:
            try:
                target_id = int(args[1])
            except:
                self.send_message(user_id, "❌ ID должен быть числом!")
                return
            
            supabase.table('blacklist').insert({'user_id': target_id}).execute()
            self.send_message(user_id, f"✅ @id{target_id} добавлен в ЧС")
        
        elif action == 'разбан' and len(args) >= 2:
            try:
                target_id = int(args[1])
            except:
                self.send_message(user_id, "❌ ID должен быть числом!")
                return
            
            supabase.table('blacklist').delete().eq('user_id', target_id).execute()
            self.send_message(user_id, f"✅ @id{target_id} удален из ЧС")
    
    def run(self):
        print("🔄 Бот слушает сообщения...")
        for event in self.longpoll.listen():
            if event.type == VkEventType.MESSAGE_NEW and event.to_me:
                user_id = event.user_id
                message = event.text.lower().strip()
                
                # Проверка ЧС
                if self.check_blacklist(user_id):
                    self.send_message(user_id, "🚫 Ты в черном списке бота!")
                    continue
                
                if not message:
                    continue
                
                parts = message.split()
                command = parts[0]
                args = parts[1:] if len(parts) > 1 else []
                
                if command in self.commands:
                    try:
                        self.commands[command](user_id, args)
                    except Exception as e:
                        print(f"Ошибка в команде {command}: {e}")
                        self.send_message(user_id, "❌ Ошибка! Попробуй позже")

if __name__ == "__main__":
    bot = RichBot()
    bot.run()
