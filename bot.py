from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
import logging
import sqlite3
import os
from datetime import datetime
import time
import re

# Включим логирование
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Замените на ваш токен от @BotFather
BOT_TOKEN = "7683048854:AAFd22eUsTzqZeUzxGWdNsN8Wvopw6NVXTU"
# Замените на ID вашего канала (отрицательное число, например: -1001234567890)
CHANNEL_ID = -1003032674443

# ВАШ TELEGRAM ID - замените на свой реальный ID (узнайте у @userinfobot)
MY_TELEGRAM_ID = 5870642170  # ← ЗАМЕНИТЕ ЭТО ЧИСЛО НА СВОЙ ID!

# Стадии опроса
(AGE, NAME, GENDER, PARAMS, PARAMS_FEMALE, CITY, LOOKING_FOR, ABOUT, RULES) = range(9)

# Клавиатура для выбора пола
gender_keyboard = ReplyKeyboardMarkup([['М', 'Ж', 'Пара']], one_time_keyboard=True, resize_keyboard=True)

# Клавиатура для выбора кого ищет (только один вариант)
looking_for_keyboard = ReplyKeyboardMarkup([
    ['М', 'Ж', 'Пара']
], one_time_keyboard=True, resize_keyboard=True)

# Клавиатура для согласия с правилами
rules_keyboard = ReplyKeyboardMarkup([
    ['✅ Согласен', '❌ Не согласен']
], one_time_keyboard=True, resize_keyboard=True)

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
    await update.message.reply_text('Привет! Сколько вам лет? (ответьте цифрами)')
    return AGE

async def age_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатываем возраст"""
    try:
        age = int(update.message.text)
        if age <= 22:
            await update.message.reply_text('Спасибо за участие!')
            return ConversationHandler.END

        context.user_data['age'] = age
        await update.message.reply_text('Отлично! Нужно заполнить анкету.\n\nВаше имя?')
        return NAME
    except:
        await update.message.reply_text('Пожалуйста, введите возраст цифрами:')
        return AGE

async def name_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатываем имя"""
    if not update.message.text.replace(' ', '').isalpha():
        await update.message.reply_text('Пожалуйста, используйте только буквы:\nВаше имя?')
        return NAME

    context.user_data['name'] = update.message.text
    await update.message.reply_text('Вы?', reply_markup=gender_keyboard)
    return GENDER

async def gender_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатываем пол"""
    if update.message.text not in ['М', 'Ж', 'Пара']:
        await update.message.reply_text('Пожалуйста, выберите М, Ж или Пара:', reply_markup=gender_keyboard)
        return GENDER

    context.user_data['gender'] = update.message.text

    if update.message.text == 'Пара':
        await update.message.reply_text('Параметры для мужчины (вес-рост-возраст)\nПример: 85-185-30')
        return PARAMS
    else:
        await update.message.reply_text('Ваши параметры (вес-рост-возраст)\nПример: 65-175-25')
        return PARAMS

async def params_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатываем параметры"""
    try:
        params = update.message.text.split('-')
        if len(params) != 3:
            raise ValueError

        weight, height, age = map(int, params)

        if context.user_data['gender'] == 'Пара':
            context.user_data['male_params'] = f"{weight}кг/{height}см/{age}лет"
            await update.message.reply_text('Параметры для женщины (вес-рост-возраст)\nПример: 55-165-28')
            return PARAMS_FEMALE
        else:
            context.user_data['params'] = f"{weight}кг/{height}см/{age}лет"
            await update.message.reply_text('Ваш город?')
            return CITY

    except:
        if context.user_data['gender'] == 'Пара':
            await update.message.reply_text('Пожалуйста, введите в формате: вес-рост-возраст\nПример: 85-185-30')
        else:
            await update.message.reply_text('Пожалуйста, введите в формате: вес-рост-возраст\nПример: 65-175-25')
        return PARAMS

async def params_female_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатываем параметры женщины для пары"""
    try:
        params = update.message.text.split('-')
        if len(params) != 3:
            raise ValueError

        weight, height, age = map(int, params)
        context.user_data['female_params'] = f"{weight}кг/{height}см/{age}лет"

        # Объединяем параметры для пары
        context.user_data['params'] = f"М: {context.user_data['male_params']}, Ж: {context.user_data['female_params']}"

        await update.message.reply_text('Ваш город?')
        return CITY
    except:
        await update.message.reply_text('Пожалуйста, введите в формате: вес-рост-возраст\nПример: 55-165-28')
        return PARAMS_FEMALE

async def city_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатываем город"""
    context.user_data['city'] = update.message.text

    await update.message.reply_text(
        'Кого ищете?',
        reply_markup=looking_for_keyboard
    )
    return LOOKING_FOR

async def looking_for_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатываем кого ищет (один вариант)"""
    if update.message.text not in ['М', 'Ж', 'Пара']:
        await update.message.reply_text('Пожалуйста, выберите один из вариантов:', reply_markup=looking_for_keyboard)
        return LOOKING_FOR

    context.user_data['looking_for'] = update.message.text
    await update.message.reply_text('Расскажите о себе (не обязательно)', reply_markup=ReplyKeyboardMarkup([['Пропустить']], one_time_keyboard=True, resize_keyboard=True))
    return ABOUT

async def about_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатываем информацию о себе"""
    if update.message.text == 'Пропустить':
        context.user_data['about'] = '-'
    else:
        context.user_data['about'] = update.message.text

    # Автоматически определяем username пользователя
    username = update.effective_user.username
    if username:
        context.user_data['contact'] = f"@{username}"

        # Показываем правила
        rules_text = """
❌⭕️      ПРАВИЛА ОБЩЕНИЯ В ЧАТЕ!     ❌⭕️   ЧИТАЕМ ВНИМАТЕЛЬНО!     ❌⭕️

⚠️Возраст строго с 23 лет. (моложе 23 лет, попадают в БАН)

Общение в чате происходит только на Русском языке, на всех остальных в личных сообщениях!

Общение без анкеты = БАН ⛔️

⛔️ЗАПРЕЩЕНО:
Оскорблять участников.
Мат.
Затрагивать религиозные, национальные, политические,
Обсуждение СВО, использование в имени и сообщениях украинской символики, ущемляющие других темы.
Вывешивать фото с голыми интимными частями тела.
Реклама. Ссылки. Спам.
Пропаганда наркотиков, проституции, ЛГБТ.
Обсуждение нетрадиционной сексуальной ориентации.
Ущемление секс меньшинств.
Запрещается удалять ранее написанные сообщения!
Запрещено писать в ЛС без разрешения!

⛔️⛔️⛔️За нарушение правил БАН⛔️⛔️⛔️

♻️Повторный вход в чат после БАНа ПЛАТНЫЙ⚠️
        """

        await update.message.reply_text(rules_text, reply_markup=rules_keyboard)
        return RULES
    else:
        await update.message.reply_text('У вас не установлен username в Telegram. Пожалуйста, установите его в настройках Telegram и начните заново.')
        return ConversationHandler.END

async def rules_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатываем согласие с правилами"""
    if update.message.text == '✅ Согласен':
        # Завершаем анкету
        return await finish_profile(update, context)
    elif update.message.text == '❌ Не согласен':
        await update.message.reply_text('Вы не согласились с правилами. Анкета не будет создана.')
        return ConversationHandler.END
    else:
        await update.message.reply_text('Пожалуйста, выберите вариант:', reply_markup=rules_keyboard)
        return RULES

async def finish_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Завершаем анкету и отправляем приглашение"""
    user_id = update.effective_user.id

    try:
        # Создаем пригласительную ссылку
        invite_link = await context.bot.create_chat_invite_link(
            chat_id=CHANNEL_ID,
            member_limit=1,
            name=f"Для {context.user_data['name']}"
        )

        # Сохраняем анкету в базу данных
        save_profile_to_db(user_id, context.user_data, invite_link.invite_link)

        # Отправляем ссылку пользователю
        await update.message.reply_text(
            f"✅ Анкета заполнена!\n\n"
            f"Ваша персональная ссылка для входа в канал:\n"
            f"{invite_link.invite_link}\n\n"
            f"После входа по ссылке ваша анкета автоматически опубликуется в канале.\n"
            f"Ссылка действительна для одного использования."
        )

        # Добавляем команду для проверки вручную
        await update.message.reply_text(
            f"Если анкета не опубликовалась автоматически, используйте команду:\n"
            f"/publish_{user_id}"
        )

    except Exception as e:
        logger.error(f"Ошибка при создании ссылки: {e}")
        await update.message.reply_text(
            "Произошла ошибка. Свяжитесь с администратором."
        )

    return ConversationHandler.END

def save_profile_to_db(user_id, user_data, invite_link):
    """Сохраняем анкету в базу данных"""
    conn = sqlite3.connect('profiles.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO profiles
        (user_id, name, gender, params, city, looking_for, about, contact, invite_link)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        user_id,
        user_data['name'],
        user_data['gender'],
        user_data['params'],
        user_data['city'],
        user_data['looking_for'],
        user_data.get('about', '-'),
        user_data['contact'],
        invite_link
    ))
    conn.commit()
    conn.close()

def get_profile_from_db(user_id):
    """Получаем анкету из базы данных"""
    conn = sqlite3.connect('profiles.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM profiles WHERE user_id = ? AND joined = FALSE', (user_id,))
    row = cursor.fetchone()
    conn.close()

    if row:
        return {
            'user_id': row[0],
            'name': row[1],
            'gender': row[2],
            'params': row[3],
            'city': row[4],
            'looking_for': row[5],
            'about': row[6],
            'contact': row[7]
        }
    return None

def mark_profile_as_joined(user_id):
    """Помечаем анкету как опубликованную"""
    conn = sqlite3.connect('profiles.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE profiles SET joined = TRUE WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()

async def check_membership_and_publish(context: ContextTypes.DEFAULT_TYPE):
    """Периодически проверяем участников и публикуем анкеты"""
    try:
        conn = sqlite3.connect('profiles.db')
        cursor = conn.cursor()
        
        # Находим всех пользователей, которые еще не опубликованы
        cursor.execute('SELECT user_id FROM profiles WHERE joined = FALSE')
        users_to_check = cursor.fetchall()
        
        for (user_id,) in users_to_check:
            try:
                # Проверяем, является ли пользователь участником группы
                member = await context.bot.get_chat_member(CHANNEL_ID, user_id)
                
                if member.status in ['member', 'administrator', 'creator']:
                    # Пользователь в группе - публикуем анкету
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

                        # Помечаем как опубликованную
                        mark_profile_as_joined(user_id)
                        logger.info(f"Анкета пользователя {user_id} опубликована")
                        
            except Exception as e:
                # Если пользователь не найден в группе или другая ошибка
                continue
                
        conn.close()
        
    except Exception as e:
        logger.error(f"Ошибка в check_membership_and_publish: {e}")

async def manual_publish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ручная публикация анкеты по команде"""
    try:
        # Извлекаем user_id из команды
        command_text = update.message.text
        user_id_match = re.search(r'/publish_(\d+)', command_text)
        
        if not user_id_match:
            await update.message.reply_text("Неверный формат команды. Используйте: /publish_123456789")
            return
            
        user_id = int(user_id_match.group(1))
        
        # Проверяем права пользователя (только админы или сам пользователь)
        # ЗДЕСЬ ЗАМЕНИТЕ 123456789 НА ВАШ РЕАЛЬНЫЙ TELEGRAM ID!
        if update.effective_user.id != user_id and update.effective_user.id not in [MY_TELEGRAM_ID]:
            await update.message.reply_text("У вас нет прав для этой команды.")
            return
            
        # Получаем анкету
        profile = get_profile_from_db(user_id)
        if not profile:
            await update.message.reply_text("Анкета не найдена или уже опубликована.")
            return
            
        # Публикуем анкету
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

        # Помечаем как опубликованную
        mark_profile_as_joined(user_id)
        
        await update.message.reply_text("Анкета успешно опубликована!")
        
    except Exception as e:
        logger.error(f"Ошибка в manual_publish: {e}")
        await update.message.reply_text("Произошла ошибка при публикации.")

async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать статистику анкет"""
    try:
        conn = sqlite3.connect('profiles.db')
        cursor = conn.cursor()

        # Общее количество анкет
        cursor.execute('SELECT COUNT(*) FROM profiles')
        total = cursor.fetchone()[0]

        # Опубликованные анкеты
        cursor.execute('SELECT COUNT(*) FROM profiles WHERE joined = TRUE')
        published = cursor.fetchone()[0]

        # Анкеты ожидающие публикации
        waiting = total - published

        # Последние 5 анкет ожидающих публикации
        cursor.execute('''
            SELECT user_id, name, created_at
            FROM profiles
            WHERE joined = FALSE
            ORDER BY created_at DESC
            LIMIT 5
        ''')
        recent_waiting = cursor.fetchall()

        conn.close()

        # Формируем сообщение
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
                message += f"  Команда для ручной публикации: /publish_{user_id}\n"
        else:
            message += "Нет анкет ожидающих публикации"

        await update.message.reply_text(message)

    except Exception as e:
        logger.error(f"Ошибка при показе статистики: {e}")
        await update.message.reply_text("Ошибка при получении статистики")

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена опроса"""
    await update.message.reply_text('Опрос отменен.')
    return ConversationHandler.END

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ошибки"""
    logger.error(f"Ошибка: {context.error}")

def main():
    """Запуск бота"""
    import requests
    try:
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook")
        print("✅ Вебхук удален")
    except:
        pass
    # Инициализируем базу данных
    init_db()

    application = Application.builder().token(BOT_TOKEN).build()

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

    # Команда статистики
    application.add_handler(CommandHandler("stats", show_stats))
    
    # Команда для ручной публикации
    application.add_handler(MessageHandler(filters.Regex(r'^/publish_\d+'), manual_publish))

    application.add_error_handler(error_handler)
    
    # Добавляем периодическую проверку участников
    job_queue = application.job_queue
    job_queue.run_repeating(check_membership_and_publish, interval=300, first=10)  # Проверка каждые 5 минут

    logger.info("Бот запущен!")
    application.run_polling()

if __name__ == '__main__':
    main()
