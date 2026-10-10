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

# --- ПОДКЛЮЧЕНИЕ К GIGACHAT ---
try:
    giga = GigaChat(credentials=GIGACHAT_API_KEY, verify_ssl_certs=False, model="GigaChat-3-Pro")
    AI_ENABLED = True
except Exception as e:
    print(f"Ошибка подключения GigaChat: {e}")
    AI_ENABLED = False

# --- БАЗА ДАННЫХ (SQLite) ---
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

# --- БОТ ---
bot = telebot.TeleBot(TELEGRAM_TOKEN)

# История диалогов (в памяти)
history = {}  # {user_id: [{"role": "...", "content": "..."}]}

# Системные промпты для режимов
SYSTEM_PROMPTS = {
    "friend": "Ты — дружелюбный помощник Mind AI. Общаешься тепло, с юмором, как настоящий друг. Отвечай на русском языке.",
    "official": "Ты — официальный ассистент. Отвечай чётко, по делу, без лишних эмоций. На русском языке.",
    "humor": "Ты — весёлый помощник. Отвечай с мемами, шутками и отсылками к интернет-культуре. На русском языке."
}

# --- КЛАВИАТУРА ---
def main_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("💬 Задать вопрос"))
    keyboard.add(KeyboardButton("💎 Купить PRO"))
    keyboard.add(KeyboardButton("🎭 Режим общения"))
    keyboard.add(KeyboardButton("📊 Статистика"))
    return keyboard

# --- /start ---
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    get_user(user_id)
    name = message.from_user.first_name
    bot.reply_to(message, 
        f"Привет, {name}! 👋\n\n"
        f"Я — Mind AI, твой умный помощник. Могу ответить на любые вопросы.\n\n"
        f"💬 Бесплатный лимит: 5 запросов.\n"
        f"Выбери действие в меню ниже или просто напиши вопрос.",
        reply_markup=main_keyboard()
    )

# --- /help ---
@bot.message_handler(commands=['help'])
def help_cmd(message):
    bot.reply_to(message,
        "📖 **Что я умею:**\n\n"
        "• Отвечаю на любые вопросы\n"
        "• Помню историю диалога\n"
        "• Могу общаться в разных стилях\n\n"
        "**Команды:**\n"
        "/start — начало\n"
        "/pro — купить PRO\n"
        "/mode — сменить режим общения\n"
        "/help — эта справка"
    )

# --- /pro ---
@bot.message_handler(commands=['pro'])
def pro(message):
    user_id = message.from_user.id
    user = get_user(user_id)
    if user["pro"]:
        bot.reply_to(message, "У тебя уже есть PRO! Спасибо за поддержку. ❤️")
        return
    bot.reply_to(message,
        "💎 **Тариф PRO:**\n\n"
        "• Безлимитные запросы\n"
        "• Длинные ответы\n"
        "• Приоритетная поддержка\n\n"
        "Цена: 100 Stars\n\n"
        "(Оплата будет подключена в следующем обновлении)"
    answer = response.choices[0].message.content

        history[user_id].append({"role": "assistant", "content": answer})

        # Обновляем счётчик запросов
        new_requests = user["requests"] + 1
        update_user(user_id, requests=new_requests)

        # Подпись
        answer = f"{answer}\n\n---\n💬 _Запрос №{new_requests}_"
        bot.reply_to(message, answer)
    except Exception as e:
        logging.error(f"Ошибка ИИ: {e}")
        bot.reply_to(message, "Извини, что-то пошло не так. Попробуй ещё раз, пожалуйста.")

if __name__ == "__main__":
    print("Бот запущен...")
    bot.polling(none_stop=True)

# --- /mode ---
