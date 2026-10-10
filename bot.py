import telebot
import logging
import os
import sqlite3
from gigachat import GigaChat
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, LabeledPrice, PreCheckoutQuery

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
                  (user_id INTEGER PRIMARY KEY, requests INTEGER, pro INTEGER)''')
conn.commit()

def get_user(user_id):
    cursor.execute("SELECT requests, pro FROM users WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    if row:
        return {"requests": row[0], "pro": bool(row[1])}
    cursor.execute("INSERT INTO users VALUES (?, 0, 0)", (user_id,))
    conn.commit()
    return {"requests": 0, "pro": False}

def update_user(user_id, requests=None, pro=None):
    user = get_user(user_id)
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

@bot.message_handler(commands=['start'])
def start(message):
    uid = message.from_user.id
    get_user(uid)
    name = message.from_user.first_name
    bot.reply_to(message, f"Привет, {name}! 👋\nЯ Mind AI. Отвечу на любые вопросы.\n\n💬 Лимит: 5 запросов.", reply_markup=main_keyboard())

@bot.message_handler(commands=['help'])
def help_cmd(message):
    bot.reply_to(message, "Команды:\n/start — начало\n/pro — купить PRO\n/help — справка")

@bot.message_handler(commands=['pro'])
def pro(message):
    uid = message.from_user.id
    user = get_user(uid)
    if user["pro"]:
        bot.reply_to(message, "У тебя уже есть PRO! ❤️")
        return
    prices = [LabeledPrice(label="PRO-подписка", amount=100)]
    bot.send_invoice(
        chat_id=message.chat.id,
        title="PRO-подписка Mind AI",
        description="Безлимитные запросы и длинные ответы.",
        invoice_payload="pro_purchase",
        provider_token="",
        currency="XTR",
        prices=prices,
        start_parameter="pro"
    )

@bot.pre_checkout_query_handler(func=lambda query: True)
def pre_checkout(query: PreCheckoutQuery):
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
        bot.reply_to(message, f"📊 Пользователей: {total}\n💎 PRO: {pro_count}")
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

@bot.message_handler(func=lambda message: True)def ask_ai(message):
    uid = message.from_user.id
    user = get_user(uid)
    name = message.from_user.first_name

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
        response = giga.chat({"messages": history[uid]})
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
