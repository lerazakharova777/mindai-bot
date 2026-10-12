import telebot
import logging
import os
import sqlite3
from gigachat import GigaChat
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, LabeledPrice, PreCheckoutQuery

logging.basicConfig(level=logging.INFO)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GIGACHAT_API_KEY = os.environ.get("GIGACHAT_API_KEY")
ADMIN_ID = int(os.environ.get("ADMIN_ID", 0))

try:
    giga = GigaChat(credentials=GIGACHAT_API_KEY, verify_ssl_certs=False, model="GigaChat-3-Pro")
    AI_ENABLED = True
except Exception as e:
    print(f"Ошибка GigaChat: {e}")
    AI_ENABLED = False

conn = sqlite3.connect('users.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS users
                  (user_id INTEGER PRIMARY KEY, requests INTEGER, pro INTEGER, joined_at TEXT, username TEXT)''')
conn.commit()

def get_user(user_id):
    cursor.execute("SELECT requests, pro, joined_at, username FROM users WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    if row:
        return {"requests": row[0], "pro": bool(row[1]), "joined_at": row[2], "username": row[3]}
    return None

def register_user(user_id, username):
    cursor.execute("INSERT OR IGNORE INTO users (user_id, requests, pro, joined_at, username) VALUES (?, 0, 0, datetime('now'), ?)", (user_id, username))
    conn.commit()

def update_user(user_id, requests=None, pro=None):
    user = get_user(user_id)
    if user:
        if requests is not None:
            user["requests"] = requests
        if pro is not None:
            user["pro"] = pro
        cursor.execute("UPDATE users SET requests=?, pro=? WHERE user_id=?",
                       (user["requests"], int(user["pro"]), user_id))
        conn.commit()

bot = telebot.TeleBot(TELEGRAM_TOKEN)
history = {}

def main_keyboard():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("💬 Вопрос"), KeyboardButton("💎 PRO"))
    kb.add(KeyboardButton("📊 Статистика"))
    return kb

def pro_keyboard():
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("💎 PRO на месяц — 100 Stars", callback_data="buy_pro_1"))
    kb.add(InlineKeyboardButton("💎 PRO на полгода — 500 Stars", callback_data="buy_pro_6"))
    kb.add(InlineKeyboardButton("💎 PRO навсегда — 1000 Stars", callback_data="buy_pro_forever"))
    return kb

@bot.message_handler(commands=['start'])
def start(message):
    uid = message.from_user.id
    register_user(uid, message.from_user.username)
    name = message.from_user.first_name
    bot.reply_to(message, f"Привет, {name}! 👋\nЯ Bro AI. Отвечу на любые вопросы.\n\n💬 Лимит: 5 запросов.", reply_markup=main_keyboard())

@bot.message_handler(commands=['help'])
def help_cmd(message):
    bot.reply_to(message, "❓ Помощь:\n\n• Напиши вопрос — я отвечу.\n• 5 запросов бесплатно.\n• /pro — купить PRO.", reply_markup=main_keyboard())

@bot.message_handler(commands=['pro'])
def pro(message):
    bot.reply_to(message, "💎 Выбери тариф PRO:", reply_markup=pro_keyboard())

@bot.callback_query_handler(func=lambda call: call.data.startswith("buy_pro_"))
def buy_pro_callback(call):
    uid = call.from_user.id
    user = get_user(uid)
    if user and user["pro"]:
        bot.answer_callback_query(call.id, "У тебя уже есть PRO! ❤️")
        return

    if call.data == "buy_pro_1":
        amount = 100
        label = "PRO на месяц"
    elif call.data == "buy_pro_6":
        amount = 500
        label = "PRO на полгода"
    else:
        amount = 1000
        label = "PRO навсегда"

    prices = [LabeledPrice(label=label, amount=amount)]
    bot.send_invoice(
        chat_id=call.message.chat.id,
        title=label,
        description="Безлимитные запросы и длинные ответы.",
        invoice_payload=call.data,
        provider_token="",
        currency="XTR",
        prices=prices,
        start_parameter="pro"
    )
    bot.answer_callback_query(call.id)

@bot.pre_checkout_query_handler(func=lambda query: True)def pre_checkout(query: PreCheckoutQuery):
    bot.answer_pre_checkout_query(query.id, ok=True)

@bot.message_handler(content_types=['successful_payment'])
def payment_success(message):
    uid = message.from_user.id
    update_user(uid, pro=True)
    bot.reply_to(message, "🎉 Спасибо! PRO активирован. Теперь безлимит!", reply_markup=main_keyboard())

@bot.message_handler(commands=['stats'])
def stats(message):
    if message.from_user.id == ADMIN_ID:
        cursor.execute("SELECT COUNT(*) FROM users")
        total = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM users WHERE pro=1")
        pro_count = cursor.fetchone()[0]
        cursor.execute("SELECT SUM(requests) FROM users")
        total_req = cursor.fetchone()[0] or 0
        cursor.execute("SELECT COUNT(*) FROM users WHERE joined_at > datetime('now', '-1 day')")
        today = cursor.fetchone()[0]

        text = f"📊 **Статистика**\n\n"
        text += f"👥 Пользователей: {total}\n"
        text += f"💎 PRO: {pro_count}\n"
        text += f"🆓 Бесплатных: {total - pro_count}\n"
        text += f"📩 Всего запросов: {total_req}\n"
        text += f"📅 Пришло сегодня: {today}\n\n"
        text += "--- Топ-5 активных ---\n"
        cursor.execute("SELECT username, requests FROM users ORDER BY requests DESC LIMIT 5")
        for row in cursor.fetchall():
            text += f"• {row[0] or 'Аноним'}: {row[1]}\n"

        bot.reply_to(message, text)
    else:
        bot.reply_to(message, "Только для админа.")

@bot.message_handler(func=lambda m: m.text == "💬 Вопрос")
def btn_q(message):
    bot.reply_to(message, "Напиши вопрос!")

@bot.message_handler(func=lambda m: m.text == "💎 PRO")
def btn_pro(message):
    pro(message)

@bot.message_handler(func=lambda m: m.text == "📊 Статистика")
def btn_stats(message):
    stats(message)

@bot.message_handler(func=lambda message: True)
def ask_ai(message):
    uid = message.from_user.id
    user = get_user(uid)
    if not user:
        register_user(uid, message.from_user.username)
        user = get_user(uid)

    if not user["pro"] and user["requests"] >= 5:
        bot.reply_to(message, "Лимит исчерпан. Купи /pro!")
        return

    if not AI_ENABLED:
        bot.reply_to(message, "ИИ недоступен.")
        return

    bot.send_chat_action(message.chat.id, 'typing')

    if uid not in history:
        history[uid] = []

    history[uid].append({"role": "user", "content": message.text})
    if len(history[uid]) > 10:
        history[uid] = history[uid][-10:]

    try:
        system_prompt = (
            "Ты — дружелюбный и вежливый помощник по имени Bro AI. "
            "Отвечай на русском языке, тепло и по-дружески, как настоящий друг. "
            "Можно использовать лёгкий юмор и современный сленг, но без грубости. "
            "Сегодня 2026 год. Всегда используй актуальную дату — 2026 год, не путай с 2025. "
            "Если речь о деньгах, используй рубли (₽), а не доллары. "
            "Если пользователь задаёт математический вопрос, отвечай с формулами, но не используй знак $ (доллара), чтобы не путать."
        )
        messages = [{"role": "system", "content": system_prompt}] + history[uid]
        response = giga.chat({"messages": messages})
        answer = response.choices[0].message.content
        history[uid].append({"role": "assistant", "content": answer})
        new_req = user["requests"] + 1
        update_user(uid, requests=new_req)
        bot.reply_to(message, f"{answer}\n\n---\n💬 Запрос №{new_req}")
    except Exception as e:
        logging.error(f"Ошибка ИИ: {e}")
        bot.reply_to(message, "Ошибка. Попробуй ещё раз.")

if __name__ == "__main__":
    print("Бот запущен...")
    bot.polling(none_stop=True)
