from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
import logging
import sqlite3
import re

# Включим логирование
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Токен бота
BOT_TOKEN = "8406149502:AAG71sNihxvmbw-5JlIZ0Dq_hj1cIt9ZwwE"  # ← ЗАМЕНИТЕ НА НОВЫЙ ТОКЕН!

# ID вашего канала/чата
CHANNEL_ID = -1003032674443  # ← ЗАМЕНИТЕ НА ID ВАШЕГО ЧАТА
CHAT_INVITE_LINK = "https://t.me/+UArqelqms7AzODJi"  # ← ЗАМЕНИТЕ НА ССЫЛКУ ВАШЕГО ЧАТА

# Стадии опроса
(AGE, NAME, GENDER, PARAMS, LOOKING_FOR, ABOUT, RULES) = range(7)

# Клавиатуры
gender_keyboard = ReplyKeyboardMarkup([['Мужчина', 'Женщина', 'Пара']], one_time_keyboard=True, resize_keyboard=True)
looking_for_keyboard = ReplyKeyboardMarkup([['Мужчину', 'Женщину', 'Пару']], one_time_keyboard=True, resize_keyboard=True)
skip_keyboard = ReplyKeyboardMarkup([['Пропустить']], one_time_keyboard=True, resize_keyboard=True)
rules_keyboard = ReplyKeyboardMarkup([['✅ Согласен', '❌ Не согласен']], one_time_keyboard=True, resize_keyboard=True)

# Инициализация базы данных
def init_db():
    conn = sqlite3.connect('profiles.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS profiles (
            user_id INTEGER PRIMARY KEY,
            age INTEGER,
            name TEXT,
            gender TEXT,
            params TEXT,
            looking_for TEXT,
            about TEXT,
            contact TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            published BOOLEAN DEFAULT FALSE
        )
    ''')
    conn.commit()
    conn.close()

def save_profile(user_id, user_data, contact):
    """Сохранить анкету в базу данных"""
    try:
        conn = sqlite3.connect('profiles.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO profiles 
            (user_id, age, name, gender, params, looking_for, about, contact)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            user_id,
            user_data.get('age'),
            user_data.get('name'),
            user_data.get('gender'),
            user_data.get('params'),
            user_data.get('looking_for'),
            user_data.get('about', 'Не указано'),
            contact
        ))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Ошибка при сохранении анкеты: {e}")
        return False

def mark_as_published(user_id):
    """Пометить анкету как опубликованную"""
    try:
        conn = sqlite3.connect('profiles.db')
        cursor = conn.cursor()
        cursor.execute('UPDATE profiles SET published = TRUE WHERE user_id = ?', (user_id,))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Ошибка при обновлении анкеты: {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начинаем опрос"""
    # Проверяем, есть ли аргументы (для инвайт-ссылок)
    if context.args and len(context.args) > 0:
        # Это инвайт-ссылка, но мы просто начинаем анкету заново
        await update.message.reply_text('Для входа в чат нужно сначала заполнить анкету.')
    
    await update.message.reply_text('Привет! Сколько вам лет? (ответьте цифрами)')
    return AGE

async def age_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик возраста"""
    try:
        age = int(update.message.text)
        if age < 23:
            await update.message.reply_text('❌ К сожалению, вход в чат разрешен только с 23 лет.')
            return ConversationHandler.END
        if age > 100:
            await update.message.reply_text('Пожалуйста, введите реальный возраст.')
            return AGE
            
        context.user_data['age'] = age
        await update.message.reply_text('Отлично! Теперь введите ваше имя:')
        return NAME
    except ValueError:
        await update.message.reply_text('Пожалуйста, введите возраст цифрами:')
        return AGE

async def name_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик имени"""
    name = update.message.text.strip()
    if len(name) < 2:
        await update.message.reply_text('Пожалуйста, введите имя (минимум 2 символа):')
        return NAME
    if len(name) > 50:
        await update.message.reply_text('Пожалуйста, введите более короткое имя (максимум 50 символов):')
        return NAME
        
    # Проверяем, что имя состоит из букв
    if not re.match(r'^[a-zA-Zа-яА-ЯёЁ\s]+$', name):
        await update.message.reply_text('Пожалуйста, используйте только буквы в имени:')
        return NAME
        
    context.user_data['name'] = name
    await update.message.reply_text('Выберите ваш пол:', reply_markup=gender_keyboard)
    return GENDER

async def gender_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик пола"""
    gender = update.message.text
    if gender not in ['Мужчина', 'Женщина', 'Пара']:
        await update.message.reply_text('Пожалуйста, выберите пол из предложенных вариантов:', reply_markup=gender_keyboard)
        return GENDER
        
    context.user_data['gender'] = gender
    
    if gender == 'Пара':
        await update.message.reply_text('Введите параметры пары (формат: М рост-вес-возраст, Ж рост-вес-возраст):\nПример: М 180-75-25, Ж 165-55-23')
    else:
        await update.message.reply_text('Введите ваши параметры (формат: рост-вес-возраст):\nПример: 180-75-25')
    
    return PARAMS

async def params_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик параметров"""
    params = update.message.text.strip()
    
    # Проверяем формат параметров
    if context.user_data['gender'] == 'Пара':
        if not re.match(r'^М \d+-\d+-\d+,\s*Ж \d+-\d+-\d+$', params):
            await update.message.reply_text('Неверный формат! Используйте: М рост-вес-возраст, Ж рост-вес-возраст\nПример: М 180-75-25, Ж 165-55-23')
            return PARAMS
    else:
        if not re.match(r'^\d+-\d+-\d+$', params):
            await update.message.reply_text('Неверный формат! Используйте: рост-вес-возраст\nПример: 180-75-25')
            return PARAMS
        
    context.user_data['params'] = params
    await update.message.reply_text('Кого вы ищете?', reply_markup=looking_for_keyboard)
    return LOOKING_FOR

async def looking_for_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик поиска"""
    looking_for = update.message.text
    if looking_for not in ['Мужчину', 'Женщину', 'Пару']:
        await update.message.reply_text('Пожалуйста, выберите из предложенных вариантов:', reply_markup=looking_for_keyboard)
        return LOOKING_FOR
        
    context.user_data['looking_for'] = looking_for
    await update.message.reply_text('Расскажите о себе (интересы, увлечения, что ищете):', reply_markup=skip_keyboard)
    return ABOUT

async def about_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик информации о себе"""
    if update.message.text == 'Пропустить':
        context.user_data['about'] = 'Не указано'
    else:
        about = update.message.text.strip()
        if len(about) > 500:
            await update.message.reply_text('Слишком длинное описание (максимум 500 символов). Сократите:')
            return ABOUT
        context.user_data['about'] = about
    
    # Показываем правила
    rules_text = """❌⭕️      ПРАВИЛА ОБЩЕНИЯ В ЧАТЕ!     ❌⭕️   ЧИТАЕМ ВНИМАТЕЛЬНО!     ❌⭕️

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

♻️Повторный вход в чат после БАНа ПЛАТНЫЙ⚠️"""

    await update.message.reply_text(rules_text, reply_markup=rules_keyboard)
    return RULES

async def rules_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик согласия с правилами"""
    choice = update.message.text
    
    if choice == '✅ Согласен':
        user_id = update.effective_user.id
        username = update.effective_user.username
        contact = f"@{username}" if username else f"ID: {user_id}"
        
        # Сохраняем анкету
        if save_profile(user_id, context.user_data, contact):
            # Публикуем анкету в чат
            profile_text = format_profile(context.user_data, contact)
            
            try:
                await context.bot.send_message(
                    chat_id=CHANNEL_ID,
                    text=profile_text
                )
                mark_as_published(user_id)
                
                # Отправляем ссылку на чат
                await update.message.reply_text(
                    f"✅ Ваша анкета опубликована!\n\n"
                    f"🔗 Ссылка для входа в чат: {CHAT_INVITE_LINK}\n\n"
                    f"Добро пожаловать!"
                )
                
            except Exception as e:
                logger.error(f"Ошибка при публикации анкеты: {e}")
                await update.message.reply_text("❌ Ошибка при публикации анкеты. Попробуйте позже.")
        else:
            await update.message.reply_text("❌ Ошибка при сохранении анкеты. Попробуйте позже.")
    else:
        await update.message.reply_text('❌ Вы не согласились с правилами. Анкета не будет опубликована.')
    
    return ConversationHandler.END

def format_profile(user_data, contact):
    """Форматирование анкеты для публикации"""
    if user_data['gender'] == 'Пара':
        profile_text = f"""
Новый участник

Имя: {user_data['name']}
Возраст: {user_data['age']}
Пол: {user_data['gender']}
Параметры: {user_data['params']}
Ищет: {user_data['looking_for']}
О себе: {user_data['about']}
Контакт: {contact}

#анкета #новыйучастник
"""
    else:
        profile_text = f"""
Новый участник

Имя: {user_data['name']}
Возраст: {user_data['age']}
Пол: {user_data['gender']}
Параметры: {user_data['params']}
Ищет: {user_data['looking_for']}
О себе: {user_data['about']}
Контакт: {contact}

#анкета #новыйучастник
"""
    return profile_text

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена создания анкеты"""
    await update.message.reply_text('Создание анкеты отменено.')
    return ConversationHandler.END

def main():
    """Запуск бота"""
    # Инициализируем базу данных
    init_db()

    # Создаем приложение
    application = Application.builder().token(BOT_TOKEN).build()

    # Создаем обработчик диалога
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, age_handler)],
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, name_handler)],
            GENDER: [MessageHandler(filters.TEXT & ~filters.COMMAND, gender_handler)],
            PARAMS: [MessageHandler(filters.TEXT & ~filters.COMMAND, params_handler)],
            LOOKING_FOR: [MessageHandler(filters.TEXT & ~filters.COMMAND, looking_for_handler)],
            ABOUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, about_handler)],
            RULES: [MessageHandler(filters.TEXT & ~filters.COMMAND, rules_handler)],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    application.add_handler(conv_handler)

    logger.info("Бот запущен!")
    application.run_polling()

if __name__ == '__main__':
    main()

