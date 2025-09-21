from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
import logging
import sqlite3
import os
from datetime import datetime
import re
import asyncio

# Включим логирование
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# 🔒 ЗАЩИТА: список разрешенных команд
ALLOWED_COMMANDS = ['start', 'stats', 'publish_', 'check_members', 'cancel']

# 🔒 ЗАЩИТА: ID администраторов (только вы)
ADMIN_IDS = [5870642170]  # ← ЗАМЕНИТЕ НА ВАШ REAL TELEGRAM ID!

# 🔒 ЗАЩИТА: Запрещенные слова в сообщениях (крипто, ссылки и т.д.)
BLACKLIST_WORDS = [
    'crypto', 'bitcoin', 'ether', 'usdt', 'bnb', 'solana', 'xrp', 'cardano',
    'dogecoin', 'shiba', 'matic', 'dot', 'avax', 'link', 'ltc', 'ada',
    'http://', 'https://', 't.me/', '.com', '.org', '.net', '.io',
    'airdrop', 'free', 'money', 'investment', 'profit'
]

# Замените на ваш НОВЫЙ токен от @BotFather
BOT_TOKEN = "8406149502:AAG71sNihxvmbw-5JlIZ0Dq_hj1cIt9ZwwE"  # ← ЗАМЕНИТЕ НА НОВЫЙ ТОКЕН!

# Замените на ID вашего канала
CHANNEL_ID = -1003032674443

# Стадии опроса
(AGE, NAME, GENDER, PARAMS, PARAMS_FEMALE, CITY, LOOKING_FOR, ABOUT, RULES) = range(9)

# Клавиатуры
gender_keyboard = ReplyKeyboardMarkup([['М', 'Ж', 'Пара']], one_time_keyboard=True, resize_keyboard=True)
looking_for_keyboard = ReplyKeyboardMarkup([['М', 'Ж', 'Пара']], one_time_keyboard=True, resize_keyboard=True)
rules_keyboard = ReplyKeyboardMarkup([['✅ Согласен', '❌ Не согласен']], one_time_keyboard=True, resize_keyboard=True)

# 🔒 Функция проверки безопасности
def security_check(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Проверяем сообщение на безопасность"""
    if not update.message or not update.message.text:
        return True
    
    text = update.message.text.lower()
    
    # Проверяем на запрещенные слова (только в тексте, не в командах)
    for word in BLACKLIST_WORDS:
        if word in text and not text.startswith('/'):
            logger.warning(f"Обнаружено запрещенное слово: {word} от пользователя {update.effective_user.id}")
            return False
    
    # Проверяем команды (только разрешенные)
    if text.startswith('/'):
        # Извлекаем чистую команду без @botname
        command = text.split(' ')[0].split('@')[0]
        allowed_commands = [f'/{cmd}' for cmd in ALLOWED_COMMANDS]
        
        if command not in allowed_commands:
            logger.warning(f"Запрещенная команда: {command} от пользователя {update.effective_user.id}")
            return False
    
    return True

# 🔒 Функция проверки администратора
def is_admin(user_id: int) -> bool:
    """Проверяет, является ли пользователь администратором"""
    return user_id in ADMIN_IDS

# Инициализация базы данных
def init_db():
    conn = sqlite3.connect('profiles.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS profiles (
            user_id INTEGER PRIMARY KEY,
            name TEXT,
            gender TEXT,
            params TEXT,
            city TEXT,
            looking_for TEXT,
            about TEXT,
            contact TEXT,
            invite_link TEXT,
            joined BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def get_profile_from_db(user_id):
    """Получить анкету из базы данных"""
    try:
        conn = sqlite3.connect('profiles.db')
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM profiles WHERE user_id = ?', (user_id,))
        profile = cursor.fetchone()
        conn.close()
        
        if profile:
            return {
                'user_id': profile[0],
                'name': profile[1],
                'gender': profile[2],
                'params': profile[3],
                'city': profile[4],
                'looking_for': profile[5],
                'about': profile[6],
                'contact': profile[7],
                'invite_link': profile[8]
            }
        return None
    except Exception as e:
        logger.error(f"Ошибка при получении анкеты: {e}")
        return None

def mark_profile_as_joined(user_id):
    """Пометить анкету как опубликованную"""
    try:
        conn = sqlite3.connect('profiles.db')
        cursor = conn.cursor()
        cursor.execute('UPDATE profiles SET joined = TRUE WHERE user_id = ?', (user_id,))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Ошибка при обновлении анкеты: {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начинаем опрос"""
    # 🔒 Проверка безопасности
    if not security_check(update, context):
        await update.message.reply_text("Команда отклонена системой безопасности.")
        return ConversationHandler.END
        
    await update.message.reply_text('Привет! Сколько вам лет? (ответьте цифрами)')
    return AGE

async def age_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик возраста"""
    if not security_check(update, context):
        return ConversationHandler.END
        
    try:
        age = int(update.message.text)
        if age < 18 or age > 100:
            await update.message.reply_text('Пожалуйста, введите реальный возраст (от 18 лет).')
            return AGE
        context.user_data['age'] = age
        await update.message.reply_text('Отлично! Теперь введите ваше имя:')
        return NAME
    except ValueError:
        await update.message.reply_text('Пожалуйста, введите возраст цифрами:')
        return AGE

async def name_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик имени"""
    if not security_check(update, context):
        return ConversationHandler.END
        
    name = update.message.text.strip()
    if len(name) < 2 or len(name) > 50:
        await update.message.reply_text('Пожалуйста, введите реальное имя (2-50 символов):')
        return NAME
        
    context.user_data['name'] = name
    await update.message.reply_text('Выберите ваш пол:', reply_markup=gender_keyboard)
    return GENDER

async def gender_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик пола"""
    if not security_check(update, context):
        return ConversationHandler.END
        
    gender = update.message.text
    if gender not in ['М', 'Ж', 'Пара']:
        await update.message.reply_text('Пожалуйста, выберите пол из предложенных вариантов:', reply_markup=gender_keyboard)
        return GENDER
        
    context.user_data['gender'] = gender
    
    if gender == 'М':
        await update.message.reply_text('Введите ваши параметры (рост, вес, телосложение):')
        return PARAMS
    elif gender == 'Ж':
        await update.message.reply_text('Введите ваши параметры (рост, вес, параметры фигуры):')
        return PARAMS_FEMALE
    else:
        await update.message.reply_text('Введите параметры пары (возрасты, внешность):')
        return PARAMS

async def params_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик параметров"""
    if not security_check(update, context):
        return ConversationHandler.END
        
    params = update.message.text.strip()
    if len(params) < 5:
        await update.message.reply_text('Пожалуйста, введите более подробные параметры:')
        return PARAMS
        
    context.user_data['params'] = params
    await update.message.reply_text('Введите ваш город:')
    return CITY

async def params_female_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик параметров для женщин"""
    if not security_check(update, context):
        return ConversationHandler.END
        
    params = update.message.text.strip()
    if len(params) < 5:
        await update.message.reply_text('Пожалуйста, введите более подробные параметры:')
        return PARAMS_FEMALE
        
    context.user_data['params'] = params
    await update.message.reply_text('Введите ваш город:')
    return CITY

async def city_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик города"""
    if not security_check(update, context):
        return ConversationHandler.END
        
    city = update.message.text.strip()
    if len(city) < 2:
        await update.message.reply_text('Пожалуйста, введите реальный город:')
        return CITY
        
    context.user_data['city'] = city
    await update.message.reply_text('Кого вы ищете?', reply_markup=looking_for_keyboard)
    return LOOKING_FOR

async def looking_for_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик поиска"""
    if not security_check(update, context):
        return ConversationHandler.END
        
    looking_for = update.message.text
    if looking_for not in ['М', 'Ж', 'Пара']:
        await update.message.reply_text('Пожалуйста, выберите из предложенных вариантов:', reply_markup=looking_for_keyboard)
        return LOOKING_FOR
        
    context.user_data['looking_for'] = looking_for
    await update.message.reply_text('Расскажите о себе (интересы, увлечения, что ищете):')
    return ABOUT

async def about_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик информации о себе"""
    if not security_check(update, context):
        return ConversationHandler.END
        
    about = update.message.text.strip()
    if len(about) < 10:
        await update.message.reply_text('Пожалуйста, напишите более подробно о себе (минимум 10 символов):')
        return ABOUT
        
    context.user_data['about'] = about
    await update.message.reply_text('''📝 Правила канала:
❌⭕️   ЧИТАЕМ ВНИМАТЕЛЬНО!     ❌⭕️

⚠️Возраст строго с 23 лет. (моложе 23 лет, попадают в БАН)

Общение в чате происходит только на Русском языке, на всех остальных в личных сообщениях!

Общение в чате начинается с вывешивания анкеты!

Общение без анкеты = БАН ⛔️

⛔️ЗАПРЕЩЕНО:
Оскорблять участников. 
Мат. 
Затрагивать религиозные, национальные, политические, 
Обсуждение СВО, использование в имени и сообщениях украинской символики, ущемляющие других темы. 
Вывешивать фото с голыми интимными частями тела. 
Фото имитации секса даже если не видно важных мест.
Любой порно и эро контент, включая секс товары.
Реклама. Ссылки. Спам. 
Пропаганда наркотиков, проституции, ЛГБТ.
Обсуждение нетрадиционной сексуальной ориентации.
Ущемление секс меньшинств. 
Запрещается удалять ранее написанные сообщения!
Запрещено писать в ЛС без разрешения!

⛔️⛔️⛔️За нарушение правил БАН⛔️⛔️⛔️

♻️Повторный вход в чат после БАНа ПЛАТНЫЙ⚠️
✅ Нажимая "Согласен", вы подтверждаете, что ознакомились с правилами и согласны на публикацию вашей анкеты.''', reply_markup=rules_keyboard)
    return RULES

async def rules_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик согласия с правилами"""
    if not security_check(update, context):
        return ConversationHandler.END
        
    choice = update.message.text
    if choice == '✅ Согласен':
        # Сохраняем анкету в базу данных
        user_id = update.effective_user.id
        user_data = context.user_data
        
        conn = sqlite3.connect('profiles.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO profiles 
            (user_id, name, gender, params, city, looking_for, about, contact, invite_link)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            user_id,
            user_data.get('name'),
            user_data.get('gender'),
            user_data.get('params'),
            user_data.get('city'),
            user_data.get('looking_for'),
            user_data.get('about'),
            f"@{update.effective_user.username}" if update.effective_user.username else f"ID: {user_id}",
            f"https://t.me/{update.effective_user.username}" if update.effective_user.username else ""
        ))
        
        conn.commit()
        conn.close()
        
        await update.message.reply_text('''✅ Ваша анкета сохранена!

📋 Для публикации анкеты вам нужно:
1. Подписаться на наш канал
2. Отправить команду /publish

Ваша анкета будет проверена и опубликована после проверки подписки.''')
        
        return ConversationHandler.END
    else:
        await update.message.reply_text('❌ Вы не согласились с правилами. Анкета не сохранена.')
        return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена создания анкеты"""
    await update.message.reply_text('Создание анкеты отменено.')
    return ConversationHandler.END

# 🔒 ЗАЩИЩЕННАЯ КОМАНДА СТАТИСТИКИ
async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать статистику анкет (только для админов)"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("У вас нет прав для этой команды.")
        return
    
    if not security_check(update, context):
        return
        
    try:
        conn = sqlite3.connect('profiles.db')
        cursor = conn.cursor()

        cursor.execute('SELECT COUNT(*) FROM profiles')
        total = cursor.fetchone()[0]

        cursor.execute('SELECT COUNT(*) FROM profiles WHERE joined = TRUE')
        published = cursor.fetchone()[0]

        waiting = total - published

        cursor.execute('''
            SELECT user_id, name, created_at
            FROM profiles
            WHERE joined = FALSE
            ORDER BY created_at DESC
            LIMIT 5
        ''')
        recent_waiting = cursor.fetchall()

        conn.close()

        message = f"""
📊 Статистика анкет:
• Всего анкет: {total}
• Опубликовано: {published}
• Ожидают публикации: {waiting}

📋 Последние 5 ожидающих:
"""
        if recent_waiting:
            for profile in recent_waiting:
                user_id, name, created_at = profile
                message += f"• {name} (ID: {user_id}) - {created_at}\n"
        else:
            message += "Нет анкет ожидающих публикации"

        await update.message.reply_text(message)

    except Exception as e:
        logger.error(f"Ошибка при показе статистики: {e}")
        await update.message.reply_text("Ошибка при получении статистики")

# 🔒 ЗАЩИЩЕННАЯ КОМАНДА ПРОВЕРКИ
async def check_all_memberships(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда для ручной проверки всех участников (только для админов)"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("У вас нет прав для этой команды.")
        return
    
    if not security_check(update, context):
        return
        
    try:
        await update.message.reply_text("Начинаю проверку...")
        
        conn = sqlite3.connect('profiles.db')
        cursor = conn.cursor()
        cursor.execute('SELECT user_id FROM profiles WHERE joined = FALSE')
        users_to_check = cursor.fetchall()
        
        published_count = 0
        
        for (user_id,) in users_to_check:
            try:
                member = await context.bot.get_chat_member(CHANNEL_ID, user_id)
                
                if member.status in ['member', 'administrator', 'creator']:
                    profile = get_profile_from_db(user_id)
                    if profile:
                        profile_text = f"""
👤 Имя: {profile['name']}
⚡ {profile['gender']}
📏 Параметры: {profile['params']}
🏙 Город: {profile['city']}
❤ Ищу: {profile['looking_for']}
📞 Контакт: {profile['contact']}
ℹ О себе: {profile['about']}
                        """

                        await context.bot.send_message(
                            chat_id=CHANNEL_ID,
                            text=profile_text
                        )

                        mark_profile_as_joined(user_id)
                        published_count += 1
                        await asyncio.sleep(1)  # Задержка между сообщениями
                        
            except Exception as e:
                continue
                
        conn.close()
        
        await update.message.reply_text(f"✅ Проверка завершена! Опубликовано анкет: {published_count}")
        
    except Exception as e:
        logger.error(f"Ошибка в check_all_memberships: {e}")
        await update.message.reply_text("❌ Ошибка при проверке")

# 🔒 ЗАЩИЩЕННАЯ КОМАНДА ПУБЛИКАЦИИ
async def manual_publish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ручная публикация анкеты по команде"""
    if not security_check(update, context):
        return
        
    try:
        command_text = update.message.text
        user_id_match = re.search(r'/publish_(\d+)', command_text)
        
        if not user_id_match:
            await update.message.reply_text("Неверный формат команды.")
            return
            
        user_id = int(user_id_match.group(1))
        
        # Только админ или владелец анкеты
        if not is_admin(update.effective_user.id) and update.effective_user.id != user_id:
            await update.message.reply_text("У вас нет прав для этой команды.")
            return
            
        profile = get_profile_from_db(user_id)
        if not profile:
            await update.message.reply_text("Анкета не найдена или уже опубликована.")
            return
            
        profile_text = f"""
👤 Имя: {profile['name']}
⚡ {profile['gender']}
📏 Параметры: {profile['params']}
🏙 Город: {profile['city']}
❤ Ищу: {profile['looking_for']}
📞 Контакт: {profile['contact']}
ℹ О себе: {profile['about']}
        """

        await context.bot.send_message(
            chat_id=CHANNEL_ID,
            text=profile_text
        )

        mark_profile_as_joined(user_id)
        await update.message.reply_text("✅ Анкета успешно опубликована!")
        
    except Exception as e:
        logger.error(f"Ошибка в manual_publish: {e}")
        await update.message.reply_text("❌ Ошибка при публикации")

# 🔒 ГЛОБАЛЬНЫЙ ФИЛЬТР БЕЗОПАСНОСТИ
async def security_filter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Глобальный фильтр безопасности"""
    if not security_check(update, context):
        # Логируем попытку взлома
        logger.warning(f"ПОПЫТКА ВЗЛОМА: {update.effective_user.id} - {update.message.text if update.message else 'No text'}")
        return
    
    # Пропускаем сообщение дальше в обработчики
    return True

def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ошибок"""
    logger.error(f"Ошибка: {context.error}")
    if update and update.message:
        update.message.reply_text('Произошла ошибка. Попробуйте позже.')

def main():
    """Запуск бота с защитой"""
    try:
        # Инициализируем базу данных
        init_db()

        # Создаем приложение с обработчиком ошибок
        application = Application.builder().token(BOT_TOKEN).build()

        # 🔒 Добавляем глобальный фильтр безопасности
        application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, security_filter), group=-1)

        # Создаем обработчик диалога
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler('start', start)],
            states={
                AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, age_handler)],
                NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, name_handler)],
                GENDER: [MessageHandler(filters.TEXT & ~filters.COMMAND, gender_handler)],
                PARAMS: [MessageHandler(filters.TEXT & ~filters.COMMAND, params_handler)],
                PARAMS_FEMALE: [MessageHandler(filters.TEXT & ~filters.COMMAND, params_female_handler)],
                CITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, city_handler)],
                LOOKING_FOR: [MessageHandler(filters.TEXT & ~filters.COMMAND, looking_for_handler)],
                ABOUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, about_handler)],
                RULES: [MessageHandler(filters.TEXT & ~filters.COMMAND, rules_handler)],
            },
            fallbacks=[CommandHandler('cancel', cancel)]
        )

        application.add_handler(conv_handler)

        # 🔒 Защищенные команды
        application.add_handler(CommandHandler("stats", show_stats))
        application.add_handler(CommandHandler("check_members", check_all_memberships))
        application.add_handler(MessageHandler(filters.Regex(r'^/publish_\d+'), manual_publish))

        # Обработчик ошибок
        application.add_error_handler(error_handler)

        logger.info("🛡️ Защищенный бот запущен!")
        application.run_polling()

    except Exception as e:
        logger.error(f"Критическая ошибка при запуске: {e}")

if __name__ == '__main__':
    main()
