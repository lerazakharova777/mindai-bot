import telebot
import logging
import os
import sqlite3
from gigachat import GigaChat
from telebot.types import ReplyKeyboardMarkup, KeyboardButton

logging.basicConfig(level=logging.INFO)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GIGACHAT_API_KEY = os.environ.get("GIGACHAT_API_KEY")
ADMIN_ID = int(os.environ.get("ADMIN_ID", 0))

try:
    giga = GigaChat(credentials=GIGACHAT_API_KEY, verify_ssl_certs=False, model="GigaChat-3-Pro")
    AI_ENABLED = True
except Exception as e:
    print(f"Ошибка подключения GigaChat: {e}")
    AI_ENABLED = False

conn = sqlite3.connect('users.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS users
                  (user_id INTEGER PRIMARY KEY, requests INTEGER, pro INTEGER, mode TEXT)''')
conn.commit()

def get_user(user_id):
    cursor.execute("SELECT requests, pro, mode FROM users WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    if row:
        return {"requests": row[0], "pro": bool(row[1]), "mode": row[2] or "friend"}
    cursor.execute("INSERT INTO users VALUES (?, 0, 0, 'friend')", (user_id,))
    conn.commit()
    return {"requests": 0, "pro": False, "mode": "friend"}

def update_user(user_id, requests=None, pro=None, mode=None):
    user = get_user(user_id)
    if requests is not None:
        user["requests"] = requests
    if pro is not None:
        user["pro"] = pro
    if mode is not None:
        user["mode"] = mode
    cursor.execute("UPDATE users SET requests=?, pro=?, mode=? WHERE user_id=?",
                   (user["requests"], int(user["pro"]), user["mode"], user_id))
    conn.commit()

bot = telebot.TeleBot(TELEGRAM_TOKEN)
history = {}

SYSTEM_PROMPTS = {
    "friend": "Ты — дружелюбный помощник Mind AI. Общаешься тепло, с юмором, как настоящий друг. Отвечай на русском языке.",
    "official": "Ты — официальный ассистент. Отвечай чётко, по делу, без лишних эмоций. На русском языке.",
    "humor": "Ты — весёлый помощник. Отвечай с мемами, шутками и отсылками к интернет-культуре. На русском языке."
}

def main_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("💬 Задать вопрос"))
    keyboard.add(KeyboardButton("💎 Купить PRO"))
    keyboard.add(KeyboardButton("🎭 Режим общения"))
    keyboard.add(KeyboardButton("📊 Статистика"))
    return keyboard

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    get_user(user_id)
    name = message.from_user.first_name
    bot.reply_to(message, f"Привет, {name}! 👋\n\nЯ — Mind AI, твой умный помощник. Могу ответить на любые вопросы.\n\n💬 Бесплатный лимит: 5 запросов.\nВыбери действие в меню ниже или просто напиши вопрос.", reply_markup=main_keyboard())

@bot.message_handler(commands=['help'])
def help_cmd(message):
    bot.reply_to(message, "📖 Что я умею:\n\n• Отвечаю на любые вопросы\n• Помню историю диалога\n• Могу общаться в разных стилях\n\nКоманды:\n/start — начало\n/pro — купить PRO\n/mode — сменить режим\n/help — эта справка")

@bot.message_handler(commands=['pro'])
def pro(message):
    user_id = message.from_user.id
    user = get_user(user_id)
    if user["pro"]:
        bot.reply_to(message, "У тебя уже есть PRO! Спасибо за поддержку. ❤️")
        return
    bot.reply_to(message, "💎 Тариф PRO:\n\n• Безлимитные запросы\n• Длинные ответы\n• Приоритетная поддержка\n\nЦена: 100 Stars\n\n(Оплата будет подключена в следующем обновлении)")

@bot.message_handler(commands=['mode'])
def mode_cmd(message):
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("😊 Дружеский"))
    keyboard.add(KeyboardButton("📋 Официальный"))
    keyboard.add(KeyboardButton("😄 С юмором"))
    keyboard.add(KeyboardButton("◀️ Назад"))
    bot.reply_to(message, "Выбери режим общения:", reply_markup=keyboard)

@bot.message_handler(commands=['stats'])
def stats(message):
    if message.from_user.id == ADMIN_ID:cursor.execute("SELECT COUNT(*) FROM users")
        total = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM users WHERE pro=1")
        pro_count = cursor.fetchone()[0]
        cursor.execute("SELECT SUM(requests) FROM users")
        total_requests = cursor.fetchone()[0] or 0
        text = f"📊 Статистика бота\n\n👥 Пользователей: {total}\n💎 PRO: {pro_count}\n📩 Всего запросов: {total_requests}"
        bot.reply_to(message, text)
    else:
        bot.reply_to(message, "Извини, это команда только для администратора. 🙏")

@bot.message_handler(func=lambda m: m.text == "💬 Задать вопрос")
def ask_question(message):
    bot.reply_to(message, "Напиши свой вопрос, и я отвечу! 😊")

@bot.message_handler(func=lambda m: m.text == "💎 Купить PRO")
def buy_pro(message):
    pro(message)

@bot.message_handler(func=lambda m: m.text == "🎭 Режим общения")
def change_mode(message):
    mode_cmd(message)

@bot.message_handler(func=lambda m: m.text == "📊 Статистика")
def show_stats(message):
    stats(message)

@bot.message_handler(func=lambda m: m.text == "😊 Дружеский")
def set_friend(message):
    update_user(message.from_user.id, mode="friend")
    bot.reply_to(message, "Режим: Дружеский 😊", reply_markup=main_keyboard())

@bot.message_handler(func=lambda m: m.text == "📋 Официальный")
def set_official(message):
    update_user(message.from_user.id, mode="official")
    bot.reply_to(message, "Режим: Официальный 📋", reply_markup=main_keyboard())

@bot.message_handler(func=lambda m: m.text == "😄 С юмором")
def set_humor(message):
    update_user(message.from_user.id, mode="humor")
    bot.reply_to(message, "Режим: С юмором 😄", reply_markup=main_keyboard())

@bot.message_handler(func=lambda m: m.text == "◀️ Назад")
def back(message):
    bot.reply_to(message, "Главное меню:", reply_markup=main_keyboard())

@bot.message_handler(func=lambda message: True)
def ask_ai(message):
    user_id = message.from_user.id
    user = get_user(user_id)
    name = message.from_user.first_name

    if not user["pro"] and user["requests"] >= 5:
        bot.reply_to(message, f"Извини, {name}, бесплатные запросы закончились. 😔\nОформи PRO (/pro), и я снова буду отвечать!")
        return

    if not AI_ENABLED:
        bot.reply_to(message, "Извини, я сейчас недоступен. Попробуй чуть позже, пожалуйста.")
        return

    bot.send_chat_action(message.chat.id, 'typing')

    if user_id not in history:
        history[user_id] = []

    mode = user.get("mode", "friend")
    system_prompt = SYSTEM_PROMPTS.get(mode, SYSTEM_PROMPTS["friend"])

    history[user_id].append({"role": "user", "content": message.text})
    if len(history[user_id]) > 10:
        history[user_id] = history[user_id][-10:]

    messages = [{"role": "system", "content": system_prompt}] + history[user_id]

    try:
        response = giga.chat({"messages": messages})
        answer = response.choices[0].message.content
        history[user_id].append({"role": "assistant", "content": answer})
        new_requests = user["requests"] + 1
        update_user(user_id, requests=new_requests)
        bot.reply_to(message, f"{answer}\n\n---\n💬 Запрос №{new_requests}")
    except Exception as e:
        logging.error(f"Ошибка ИИ: {e}")
        bot.reply_to(message, "Извини, что-то пошло не так. Попробуй ещё раз, пожалуйста.")

if __name__ == "__main__":
    print("Бот запущен...")
    bot.polling(none_stop=True)
