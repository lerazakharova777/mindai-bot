import telebot
import logging
import os
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
    print(f"Ошибка GigaChat: {e}")
    AI_ENABLED = False

bot = telebot.TeleBot(TELEGRAM_TOKEN)
users = {}

def main_keyboard():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("💬 Вопрос"))
    kb.add(KeyboardButton("💎 PRO"))
    kb.add(KeyboardButton("📊 Стата"))
    return kb

@bot.message_handler(commands=['start'])
def start(message):
    uid = message.from_user.id
    if uid not in users:
        users[uid] = {"req": 0, "pro": False}
    name = message.from_user.first_name
    bot.reply_to(message, f"Привет, {name}! Я Mind AI. Задай вопрос!", reply_markup=main_keyboard())

@bot.message_handler(commands=['help'])
def help_cmd(message):
    bot.reply_to(message, "Команды:\n/start - начало\n/pro - купить PRO\n/stats - статистика")

@bot.message_handler(commands=['pro'])
def pro(message):
    bot.reply_to(message, "💎 PRO: безлимит за 100 Stars.")

@bot.message_handler(commands=['stats'])
def stats(message):
    if message.from_user.id == ADMIN_ID:
        bot.reply_to(message, f"👥 Пользователей: {len(users)}")
    else:
        bot.reply_to(message, "Только для админа.")

@bot.message_handler(func=lambda m: m.text == "💬 Вопрос")
def btn_q(message):
    bot.reply_to(message, "Напиши вопрос!")

@bot.message_handler(func=lambda m: m.text == "💎 PRO")
def btn_pro(message):
    pro(message)

@bot.message_handler(func=lambda m: m.text == "📊 Стата")
def btn_stats(message):
    stats(message)

@bot.message_handler(func=lambda message: True)
def ask_ai(message):
    uid = message.from_user.id
    if uid not in users:
        users[uid] = {"req": 0, "pro": False}

    if not users[uid]["pro"] and users[uid]["req"] >= 5:
        bot.reply_to(message, "Лимит исчерпан. Купи /pro!")
        return

    if not AI_ENABLED:
        bot.reply_to(message, "ИИ недоступен.")
        return

    bot.send_chat_action(message.chat.id, 'typing')

    try:
        response = giga.chat(message.text)
        answer = response.choices[0].message.content
        users[uid]["req"] += 1
        bot.reply_to(message, answer)
    except Exception as e:
        logging.error(f"Ошибка: {e}")
        bot.reply_to(message, "Ошибка. Попробуй ещё раз.")

if __name__ == "__main__":
    print("Бот запущен...")
    bot.polling(none_stop=True)
