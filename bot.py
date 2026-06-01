import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType
import random
import os
import time
from datetime import datetime, timedelta
from supabase import create_client, Client
from flask import Flask
import threading
import sys

# Получаем переменные окружения
VK_TOKEN = os.environ.get('VK_TOKEN')
SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY')
ADMIN_ID = int(os.environ.get('ADMIN_ID', 0))

# Проверка наличия переменных
if not VK_TOKEN:
    print("❌ ОШИБКА: VK_TOKEN не установлен!")
    sys.exit(1)
if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ ОШИБКА: SUPABASE_URL или SUPABASE_KEY не установлены!")
    sys.exit(1)

print(f"✅ Переменные окружения загружены")
print(f"👑 ADMIN_ID: {ADMIN_ID}")

# Инициализация Supabase
try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    print("✅ Supabase подключен")
except Exception as e:
    print(f"❌ Ошибка подключения к Supabase: {e}")
    sys.exit(1)

# Flask приложение для Render
app = Flask(__name__)

@app.route('/')
def health_check():
    return "🤖 Бот Рич работает!"

@app.route('/health')
def health():
    return "OK", 200

class RichBot:
    def __init__(self):
        print("🔄 Инициализация бота...")
        
        try:
            self.vk_session = vk_api.VkApi(token=VK_TOKEN)
            self.vk = self.vk_session.get_api()
            self.longpoll = VkLongPoll(self.vk_session)
        except Exception as e:
            print(f"❌ Ошибка инициализации VK API: {e}")
            sys.exit(1)
        
        self.start_money = 1000
        self.currency_symbol = "💰 Ричей"
        
        # Получаем информацию о боте
        try:
            bot_info = self.vk.users.get()[0]
            self.bot_id = bot_info['id']
            self.bot_screen_name = bot_info.get('screen_name', 'rich_bot')
            print(f"🤖 Бот запущен: @{self.bot_screen_name} (ID: {self.bot_id})")
        except Exception as e:
            print(f"❌ Ошибка получения информации о боте: {e}")
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
            'мафия': self.cmd_mafia,
            'вступить_в_мафию': self.cmd_join_mafia,
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
        }
        
        print("✅ Бот Рич (Supabase) запущен и готов к работе!")
        print(f"💬 В беседах используй ! перед командой")
    
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
                    'last_business_collect': datetime.now().isoformat()
                }
                supabase.table('users').insert(new_user).execute()
                return new_user
            
            return result.data[0]
        except Exception as e:
            print(f"Ошибка get_user: {e}")
            return None
    
    def update_user(self, user_id, data):
        try:
            supabase.table('users').update(data).eq('user_id', user_id).execute()
        except Exception as e:
            print(f"Ошибка update_user: {e}")
    
    def send_message(self, peer_id, message):
        try:
            self.vk.messages.send(
                peer_id=peer_id,
                message=message[:4000],
                random_id=random.randint(1, 999999)
            )
        except Exception as e:
            print(f"Ошибка отправки: {e}")
    
    def send_message_to_user(self, user_id, message):
        try:
            self.vk.messages.send(
                user_id=user_id,
                message=message[:4000],
                random_id=random.randint(1, 999999)
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
    
    # ============================ КОМАНДА ПЕРЕДАЧИ ДЕНЕГ ============================
    def cmd_transfer(self, peer_id, user_id, args):
        if len(args) < 2:
            self.send_message(peer_id, "❌ Использование: передать [id] [сумма]")
            return
        
        try:
            target_id = int(args[0])
            amount = int(args[1])
        except:
            self.send_message(peer_id, "❌ ID и сумма должны быть числами!")
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
        
        self.send_message(peer_id, f"✅ @id{user_id} передал @id{target_id} {amount} {self.currency_symbol}!")
        self.send_message_to_user(target_id, f"💰 @id{user_id} передал вам {amount} {self.currency_symbol}!")
    
    # ============================ БИЗНЕСЫ ============================
    def cmd_business(self, peer_id, user_id, args):
        try:
            businesses = supabase.table('businesses').select('*').execute()
            my_businesses = supabase.table('user_businesses').select('*, businesses(*)').eq('user_id', user_id).execute()
            
            text = "🏢 ДОСТУПНЫЕ БИЗНЕСЫ:\n\n"
            for biz in businesses.data:
                text += f"📌 {biz['name']}\n"
                text += f"   💰 Цена: {biz['price']} {self.currency_symbol}\n"
                text += f"   ⏱ Доход в час: {biz['income_per_hour']} {self.currency_symbol}\n\n"
            
            if my_businesses.data:
                text += "━━━━━━━━━━━━━━━━\n📋 ВАШИ БИЗНЕСЫ:\n"
                total_income = 0
                for mb in my_businesses.data:
                    biz = mb['businesses']
                    last_collected = datetime.fromisoformat(mb['last_collected'].replace('Z', '+00:00'))
                    hours_passed = (datetime.now() - last_collected).total_seconds() / 3600
                    pending = int(biz['income_per_hour'] * hours_passed)
                    text += f"   • {biz['name']} - +{pending} (готово к сбору)\n"
                    total_income += biz['income_per_hour']
                text += f"\n💰 Общий доход в час: {total_income} {self.currency_symbol}"
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
            self.send_message(peer_id, "❌ Бизнес не найден! Список: !бизнес")
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
            self.send_message(peer_id, f"❌ Не хватает денег! Нужно {biz['price']} {self.currency_symbol}")
            return
        
        self.update_user(user_id, {'money': user['money'] - biz['price']})
        supabase.table('user_businesses').insert({
            'user_id': user_id,
            'business_id': biz['id'],
            'last_collected': datetime.now().isoformat()
        }).execute()
        
        self.send_message(peer_id, f"✅ @id{user_id} купил бизнес {biz['name']} за {biz['price']} {self.currency_symbol}!")
    
    def cmd_collect_business(self, peer_id, user_id, args):
        my_businesses = supabase.table('user_businesses').select('*, businesses(*)').eq('user_id', user_id).execute()
        
        if not my_businesses.data:
            self.send_message(peer_id, "❌ У вас нет бизнесов! Купите: !купитьбизнес")
            return
        
        user = self.get_user(user_id)
        total_income = 0
        
        for mb in my_businesses.data:
            biz = mb['businesses']
            last_collected = datetime.fromisoformat(mb['last_collected'].replace('Z', '+00:00'))
            hours_passed = (datetime.now() - last_collected).total_seconds() / 3600
            hours_to_collect = min(hours_passed, 24)
            income = int(biz['income_per_hour'] * hours_to_collect)
            total_income += income
            
            supabase.table('user_businesses').update({
                'last_collected': datetime.now().isoformat()
            }).eq('user_id', user_id).eq('business_id', biz['id']).execute()
        
        if total_income > 0:
            self.update_user(user_id, {'money': user['money'] + total_income})
            self.send_message(peer_id, f"💰 @id{user_id} собрал {total_income} {self.currency_symbol} со своих бизнесов!")
        else:
            self.send_message(peer_id, "⏰ Накоплений пока нет. Зайдите позже!")
    
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
        
        supabase.table('user_clothes').insert({
            'user_id': user_id,
            'clothes_id': cloth['id'],
            'equipped': False
        }).execute()
        
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
            text += "\n"
        
        text += "💡 Команды:\n"
        text += "   • надеть [название]\n"
        text += "   • снять [название]"
        
        self.send_message(peer_id, text)
    
    def cmd_wear(self, peer_id, user_id, args):
        if not args:
            self.send_message(peer_id, "❌ Укажите название одежды!")
            return
        
        clothes_name = ' '.join(args).lower()
        
        user_clothes = self.get_user_clothes(user_id)
        
        if not user_clothes:
            self.send_message(peer_id, "❌ У вас нет одежды в гардеробе!")
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
        
        self.send_message(peer_id, f"✅ @id{user_id} надел {cloth['name']}!")
    
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
        
        self.send_message(peer_id, f"✅ @id{user_id} снял {cloth['name']}!")
    
    def cmd_give_clothes_to_all(self, peer_id, user_id, args):
        if user_id != ADMIN_ID:
            self.send_message(peer_id, "❌ Нет прав! Это админ-команда.")
            return
        
        if not args:
            self.send_message(peer_id, "❌ Использование: выдатьодежду [название одежды]")
            return
        
        if args[0].lower() == 'всем':
            args = args[1:]
        
        if not args:
            self.send_message(peer_id, "❌ Укажите название одежды после 'всем'")
            return
        
        clothes_name = ' '.join(args)
        
        clothes_check = supabase.table('clothes').select('*').ilike('name', clothes_name).execute()
        
        if not clothes_check.data:
            clothes_check = supabase.table('clothes').select('*').ilike('name', f'%{clothes_name}%').execute()
        
        if not clothes_check.data:
            all_clothes = supabase.table('clothes').select('name').execute()
            names = ', '.join([c['name'] for c in all_clothes.data])
            self.send_message(peer_id, f"❌ Одежда '{clothes_name}' не найдена!\n📋 Доступная одежда: {names}")
            return
        
        cloth = clothes_check.data[0]
        real_name = cloth['name']
        
        users = supabase.table('users').select('user_id').execute()
        
        if not users.data:
            self.send_message(peer_id, "❌ Нет пользователей в базе!")
            return
        
        success_count = 0
        already_have_count = 0
        
        for user in users.data:
            existing = supabase.table('user_clothes').select('*').eq('user_id', user['user_id']).eq('clothes_id', cloth['id']).execute()
            
            if existing.data:
                already_have_count += 1
                continue
            
            supabase.table('user_clothes').insert({
                'user_id': user['user_id'],
                'clothes_id': cloth['id'],
                'equipped': False
            }).execute()
            
            self.send_message_to_user(user['user_id'], f"🎁 Вам выдана одежда: {real_name}!")
            success_count += 1
            time.sleep(0.05)
        
        self.send_message(peer_id, f"✅ Выдана одежда '{real_name}' {success_count} пользователям!\n📦 Уже была у {already_have_count} пользователей.")
    
    # ============================ РАССЫЛКА ============================
    def cmd_mass_mailing(self, peer_id, user_id, args):
        if user_id != ADMIN_ID:
            self.send_message(peer_id, "❌ Нет прав! Это админ-команда.")
            return
        
        if not args:
            self.send_message(peer_id, "❌ Использование: рассылка [текст сообщения]")
            return
        
        text = ' '.join(args)
        
        users = supabase.table('users').select('user_id').execute()
        
        if not users.data:
            self.send_message(peer_id, "❌ Нет пользователей в базе!")
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
        self.send_message(peer_id, f"✅ Рассылка отправлена в личку {sent_count} пользователям и в этот чат!")
    
    # ============================ КОМАНДЫ КЛАНА ============================
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
            return
        
        if user['clan']:
            self.send_message(peer_id, "❌ Ты уже в клане!")
            return
        
        if user['money'] < 5000:
            self.send_message(peer_id, f"❌ Нужно 5000! У тебя {user['money']}")
            return
        
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
        
        self.send_message(peer_id, f"✅ Клан '{clan_name}' создан! Владелец: @id{user_id}")
    
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
            return
        
        if user['clan']:
            self.send_message(peer_id, "❌ Ты уже в клане!")
            return
        
        supabase.table('clan_members').insert({
            'clan_name': clan_name,
            'user_id': user_id
        }).execute()
        
        self.update_user(user_id, {'clan': clan_name})
        self.send_message(peer_id, f"✅ @id{user_id} вступил в клан '{clan_name}'!")
    
    def cmd_clan_info(self, peer_id, user_id, args):
        user = self.get_user(user_id)
        if not user:
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
        
        self.send_message(
            peer_id,
            f"🏆 Клан: {user['clan']}\n"
            f"👑 Владелец: @id{clan_data['owner']}\n"
            f"👥 Участников: {len(members.data)}\n"
            f"💰 Казна: {clan_data['money']}\n"
            f"📅 Создан: {clan_data['created_at'][:10]}"
        )
    
    def cmd_leave_clan(self, peer_id, user_id, args):
        """!покинуть_клан - выйти из текущего клана"""
        user = self.get_user(user_id)
        
        if not user:
            self.send_message(peer_id, "❌ Ошибка! Попробуй позже")
            return
        
        if not user['clan']:
            self.send_message(peer_id, "❌ Вы не состоите в клане!")
            return
        
        clan_name = user['clan']
        
        # Проверяем, существует ли клан
        clan = supabase.table('clans').select('*').eq('name', clan_name).execute()
        
        if not clan.data:
            # Клана нет в базе, но у пользователя есть запись - просто очищаем
            self.update_user(user_id, {'clan': None})
            self.send_message(peer_id, "✅ Вы покинули несуществующий клан (данные очищены)")
            return
        
        clan_data = clan.data[0]
        
        # Проверяем, является ли пользователь владельцем
        if clan_data['owner'] == user_id:
            # Владелец покидает клан - находим нового владельца
            members = supabase.table('clan_members').select('*').eq('clan_name', clan_name).execute()
            
            # Удаляем владельца из участников
            supabase.table('clan_members').delete().eq('clan_name', clan_name).eq('user_id', user_id).execute()
            
            # Получаем обновленный список участников
            remaining_members = supabase.table('clan_members').select('*').eq('clan_name', clan_name).execute()
            
            if remaining_members.data:
                # Есть другие участники - передаем владение первому
                new_owner_id = remaining_members.data[0]['user_id']
                supabase.table('clans').update({'owner': new_owner_id}).eq('name', clan_name).execute()
                self.send_message(peer_id, f"👑 Вы покинули клан '{clan_name}'!\n🏆 Новый владелец: @id{new_owner_id}")
            else:
                # Участников не осталось - удаляем клан
                supabase.table('clans').delete().eq('name', clan_name).execute()
                self.send_message(peer_id, f"✅ Клан '{clan_name}' распущен (вы были последним участником)")
        else:
            # Обычный участник - просто удаляем из клана
            supabase.table('clan_members').delete().eq('clan_name', clan_name).eq('user_id', user_id).execute()
            self.send_message(peer_id, f"✅ @id{user_id} покинул клан '{clan_name}'!")
        
        # Обновляем данные пользователя
        self.update_user(user_id, {'clan': None})
    
    # ============================ МАФИЯ ============================
    def cmd_mafia(self, peer_id, user_id, args):
        user = self.get_user(user_id)
        if not user:
            return
        
        if not user['mafia']:
            self.send_message(peer_id, "❌ Ты не в мафии! Используй 'вступить_в_мафию' [название]")
            return
        
        mafia = supabase.table('mafia').select('*').eq('name', user['mafia']).execute()
        members = supabase.table('mafia_members').select('*').eq('mafia_name', user['mafia']).execute()
        
        self.send_message(
            peer_id,
            f"🔫 Мафия: {user['mafia']}\n"
            f"👥 Участников: {len(members.data)}\n"
            f"💰 Общак: {mafia.data[0]['money'] if mafia.data else 0}"
        )
    
    def cmd_join_mafia(self, peer_id, user_id, args):
        if not args:
            self.send_message(peer_id, "❌ Название мафии! Доступны: Братки, Мафиози, Гангстеры")
            return
        
        mafia_name = ' '.join(args)
        
        user = self.get_user(user_id)
        if not user:
            return
        
        if user['mafia']:
            self.send_message(peer_id, "❌ Ты уже в мафии!")
            return
        
        mafia = supabase.table('mafia').select('*').eq('name', mafia_name).execute()
        
        if not mafia.data:
            supabase.table('mafia').insert({
                'name': mafia_name,
                'boss': user_id,
                'money': 0
            }).execute()
        
        supabase.table('mafia_members').insert({
            'mafia_name': mafia_name,
            'user_id': user_id
        }).execute()
        
        self.update_user(user_id, {'mafia': mafia_name})
        self.send_message(peer_id, f"✅ @id{user_id} в мафии '{mafia_name}'!")
    
    # ============================ ОСТАЛЬНЫЕ КОМАНДЫ ============================
    def cmd_help(self, peer_id, user_id, args):
        self.send_message(
            peer_id,
            f"📜 КОМАНДЫ БОТА RICH:\n\n"
            f"💰 баланс - проверить баланс\n"
            f"💼 работы - список работ\n"
            f"💪 работа [название] - работать\n"
            f"🎰 казино [орёл_решка/кости] [ставка] - играть\n"
            f"👥 создать_клан [название]\n"
            f"🤝 вступить [клан]\n"
            f"🏆 клан - инфо о клане\n"
            f"🚪 покинуть_клан - выйти из клана\n"
            f"🔫 мафия - инфо о мафии\n"
            f"🔫 вступить_в_мафию [название]\n"
            f"⚔️ дуэль [id] [ставка]\n"
            f"💀 ограбить [id]\n"
            f"📊 топ - топ игроков\n"
            f"💸 передать [id] [сумма] - перевести деньги\n"
            f"🏢 бизнес - список бизнесов\n"
            f"💰 купитьбизнес [название]\n"
            f"🧾 собрать - собрать доход с бизнесов\n"
            f"👔 шкаф - гардероб\n"
            f"👕 надеть [название]\n"
            f"👕 снять [название]\n\n"
            f"💡 В беседах используй ! перед командой"
        )
    
    def cmd_start(self, peer_id, user_id, args):
        user = self.get_user(user_id)
        if not user:
            self.send_message(peer_id, "❌ Ошибка! Попробуй позже")
            return
        
        self.send_message(
            peer_id,
            f"🌟 Добро пожаловать в Rich, @id{user_id}!\n\n"
            f"💰 Баланс: {user['money']}\n"
            f"⚡ Энергия: {user['energy']}%\n"
            f"🏆 Уровень: {user['level']}\n\n"
            f"📜 Команды: помощь"
        )
    
    def cmd_balance(self, peer_id, user_id, args):
        user = self.get_user(user_id)
        if not user:
            self.send_message(peer_id, "❌ Ошибка!")
            return
            
        self.send_message(
            peer_id,
            f"💰 Баланс @id{user_id}: {user['money']} {self.currency_symbol}\n"
            f"⚡ Энергия: {user['energy']}%\n"
            f"🏆 Уровень: {user['level']}\n"
            f"🎯 Побед в дуэлях: {user['duels_won']}\n"
            f"💀 Поражений: {user['duels_lost']}"
        )
    
    def cmd_jobs(self, peer_id, user_id, args):
        text = "📋 Работы:\n\n"
        for name, data in self.jobs.items():
            text += f"📌 {name}\n"
            text += f"   💰 {data['money'][0]}-{data['money'][1]}\n"
            text += f"   ⚡ Тратит: {data['energy']} энергии\n\n"
        self.send_message(peer_id, text)
    
    def cmd_work(self, peer_id, user_id, args):
        if not args:
            self.send_message(peer_id, "❌ Укажи работу: работа программист")
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
            self.send_message(peer_id, f"✅ @id{user_id}, ты устроился на {job_name}!")
            return
        
        can_work, remaining = self.check_cooldown(user_id, 'work', 10)
        if not can_work:
            self.send_message(peer_id, f"⏰ @id{user_id}, отдыхай! Следующая работа через {remaining} мин")
            return
        
        if user['energy'] < self.jobs[job_name]['energy']:
            self.send_message(peer_id, f"❌ @id{user_id}, мало энергии! Нужно {self.jobs[job_name]['energy']}")
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
        
        self.send_message(
            peer_id,
            f"✅ @id{user_id} поработал на {job_name}!\n"
            f"💰 +{earned}\n"
            f"⚡ Энергия: {new_energy}%{level_msg}"
        )
    
    def cmd_casino(self, peer_id, user_id, args):
        if len(args) < 2:
            self.send_message(peer_id, "❌ Использование: казино [орёл_решка/кости] [ставка]")
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
        
        self.send_message(peer_id, f"🎰 @id{user_id}\n{result}\n💰 Новый баланс: {new_money}")
    
    def cmd_rob(self, peer_id, user_id, args):
        if not args:
            self.send_message(peer_id, "❌ Кого грабить? ID пользователя")
            return
        
        try:
            target_id = int(args[0])
        except:
            self.send_message(peer_id, "❌ ID должен быть числом!")
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
            self.send_message(peer_id, f"⏰ @id{user_id}, следующий грабеж через {remaining} мин")
            return
        
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
            
            self.send_message(peer_id, f"🔫 @id{user_id} ограбил @id{target_id} на {rob_amount}!")
        else:
            penalty = random.randint(50, 150)
            new_money = max(0, user['money'] - penalty)
            
            self.update_user(user_id, {
                'money': new_money,
                'last_rob': datetime.now().isoformat()
            })
            self.send_message(peer_id, f"❌ @id{user_id} провалил грабеж! Штраф {penalty}!")
    
    def cmd_duel(self, peer_id, user_id, args):
        if len(args) < 2:
            self.send_message(peer_id, "❌ Использование: дуэль [id] [ставка]")
            return
        
        try:
            opponent_id = int(args[0])
            bet = int(args[1])
        except:
            self.send_message(peer_id, "❌ ID и ставка должны быть числами!")
            return
        
        if opponent_id == user_id:
            self.send_message(peer_id, "❌ С собой нельзя!")
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
        
        self.send_message(peer_id, f"⚔️ @id{user_id} вызвал @id{opponent_id} на дуэль! Ставка: {bet}\n"
                                   f"Для принятия: принять_дуэль {bet}")
    
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
            self.send_message(peer_id, f"❌ @id{user_id}, не хватает денег! Нужно {bet}")
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
        
        self.send_message(peer_id, f"⚔️ ПОБЕДИТЕЛЬ ДУЭЛИ: @id{winner_id}\n💰 Выигрыш: {winner_prize}")
    
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
            self.send_message(peer_id, f"❌ @id{user_id} отклонил дуэль с @id{challenger_id}!")
    
    def cmd_top(self, peer_id, user_id, args):
        users = supabase.table('users').select('user_id, money, level').order('money', desc=True).limit(10).execute()
        
        if not users.data:
            self.send_message(peer_id, "📊 Пока нет игроков!")
            return
        
        text = "🏆 ТОП-10 БОГАЧЕЙ:\n\n"
        for i, user in enumerate(users.data, 1):
            text += f"{i}. @id{user['user_id']} - {user['money']} {self.currency_symbol} (Ур. {user['level']})\n"
        
        self.send_message(peer_id, text)
    
    # ============================ АДМИН КОМАНДЫ ============================
    def cmd_admin(self, peer_id, user_id, args):
        if user_id != ADMIN_ID:
            self.send_message(peer_id, "❌ Нет прав! Команды только для администратора.")
            return
        
        if not args:
            self.send_message(peer_id, "👑 АДМИН КОМАНДЫ:\n\n"
                                      "• админ дать [id] [сумма] - выдать деньги\n"
                                      "• админ одежда [id] [название] - выдать одежду по id\n"
                                      "• админ бан [id] - заблокировать\n"
                                      "• админ разбан [id] - разблокировать\n"
                                      "• админ сброс [id] - сбросить прогресс\n"
                                      "• админ стата - статистика бота")
            return
        
        action = args[0].lower()
        
        if action == 'дать' and len(args) >= 3:
            try:
                target_id = int(args[1])
                amount = int(args[2])
            except:
                self.send_message(peer_id, "❌ ID и сумма - числа!")
                return
            
            target = self.get_user(target_id)
            if target:
                self.update_user(target_id, {'money': target['money'] + amount})
                self.send_message(peer_id, f"✅ Выдано {amount} {self.currency_symbol} @id{target_id}")
                self.send_message_to_user(target_id, f"👑 Администратор выдал вам {amount} {self.currency_symbol}!")
        
        elif action == 'одежда' and len(args) >= 3:
            try:
                target_id = int(args[1])
                clothes_name = ' '.join(args[2:])
            except:
                self.send_message(peer_id, "❌ Неверный формат! Использование: админ одежда [id] [название]")
                return
            
            success, result = self.give_clothes_to_user(target_id, clothes_name)
            if success:
                self.send_message(peer_id, f"✅ Выдана одежда '{result}' @id{target_id}")
            else:
                self.send_message(peer_id, f"❌ {result}")
        
        elif action == 'бан' and len(args) >= 2:
            try:
                target_id = int(args[1])
                supabase.table('blacklist').insert({'user_id': target_id}).execute()
                self.send_message(peer_id, f"✅ @id{target_id} в ЧС")
            except:
                self.send_message(peer_id, "❌ Ошибка!")
        
        elif action == 'разбан' and len(args) >= 2:
            try:
                target_id = int(args[1])
                supabase.table('blacklist').delete().eq('user_id', target_id).execute()
                self.send_message(peer_id, f"✅ @id{target_id} из ЧС")
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
                self.send_message(peer_id, f"✅ Прогресс @id{target_id} сброшен")
            except:
                self.send_message(peer_id, "❌ Ошибка!")
        
        elif action == 'стата':
            users_count = supabase.table('users').select('*', count='exact').execute()
            clans_count = supabase.table('clans').select('*', count='exact').execute()
            businesses_count = supabase.table('user_businesses').select('*', count='exact').execute()
            clothes_count = supabase.table('user_clothes').select('*', count='exact').execute()
            
            self.send_message(
                peer_id,
                f"📊 СТАТИСТИКА БОТА:\n\n"
                f"👥 Игроков: {users_count.count}\n"
                f"🏆 Кланов: {clans_count.count}\n"
                f"🏢 Куплено бизнесов: {businesses_count.count}\n"
                f"👔 Выдано одежды: {clothes_count.count}\n"
                f"💰 Стартовый капитал: {self.start_money}\n"
                f"💼 Работ: {len(self.jobs)}"
            )
    
    def run(self):
        print("🔄 Бот слушает сообщения...")
        print("💡 В беседах используй ! перед командой")
        
        while True:
            try:
                for event in self.longpoll.listen():
                    if event.type == VkEventType.MESSAGE_NEW:
                        if event.user_id == self.bot_id:
                            continue
                        
                        user_id = event.user_id
                        peer_id = event.peer_id
                        message_text = event.text.strip()
                        
                        if not message_text:
                            continue
                        
                        should_process = False
                        clean_message = message_text
                        
                        if peer_id == user_id:
                            should_process = True
                        else:
                            if message_text.startswith('!'):
                                clean_message = message_text[1:].strip()
                                should_process = True
                            elif f"@{self.bot_screen_name}" in message_text.lower():
                                clean_message = message_text.lower().replace(f"@{self.bot_screen_name}", "").strip()
                                should_process = True
                            elif message_text.lower().split()[0] in ['баланс', 'топ', 'помощь', 'команды', 'начать', 'бизнес', 'шкаф', 'передать']:
                                should_process = True
                                clean_message = message_text
                        
                        if not should_process:
                            continue
                        
                        if self.check_blacklist(user_id):
                            continue
                        
                        parts = clean_message.lower().split()
                        if not parts:
                            continue
                        
                        command = parts[0]
                        args = parts[1:] if len(parts) > 1 else []
                        
                        if command in self.commands:
                            try:
                                print(f"📩 Команда от @id{user_id} в чат {peer_id}: {command}")
                                self.commands[command](peer_id, user_id, args)
                            except Exception as e:
                                print(f"❌ Ошибка в {command}: {e}")
                                self.send_message(peer_id, f"❌ Ошибка! Попробуй позже")
            except Exception as e:
                print(f"❌ Ошибка в longpoll: {e}")
                time.sleep(5)

def run_web_server():
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

if __name__ == "__main__":
    print("🚀 Запуск бота...")
    
    web_thread = threading.Thread(target=run_web_server)
    web_thread.daemon = True
    web_thread.start()
    
    bot = RichBot()
    bot.run()
