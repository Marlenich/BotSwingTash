from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
import logging
import sqlite3
import os
from datetime import datetime
import re

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
    'http://', 'https://', 't.me/', '@', '.com', '.org', '.net', '.io',
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
    
    # Проверяем на запрещенные слова
    for word in BLACKLIST_WORDS:
        if word in text:
            logger.warning(f"Обнаружено запрещенное слово: {word} от пользователя {update.effective_user.id}")
            return False
    
    # Проверяем команды (только разрешенные)
    if text.startswith('/'):
        command = text.split(' ')[0].split('@')[0]
        if not any(command.startswith(allowed) for allowed in ALLOWED_COMMANDS):
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

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начинаем опрос"""
    # 🔒 Проверка безопасности
    if not security_check(update, context):
        await update.message.reply_text("Команда отклонена системой безопасности.")
        return ConversationHandler.END
        
    await update.message.reply_text('Привет! Сколько вам лет? (ответьте цифрами)')
    return AGE

# 🔒 ОБНОВЛЕННЫЕ ОБРАБОТЧИКИ С ПРОВЕРКОЙ БЕЗОПАСНОСТИ
async def age_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not security_check(update, context):
        return ConversationHandler.END
    # ... остальной код age_handler

async def name_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not security_check(update, context):
        return ConversationHandler.END
    # ... остальной код name_handler

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
