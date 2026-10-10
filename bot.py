import telebot
import logging
import os
from gigachat import GigaChat

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

bot = telebot.TeleBot(TELEGRAM_TOKEN)
users = {}

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    if user_id not in users:
        users[user_id] = {"requests": 0, "pro": False}
    name = message.from_user.first_name
    bot.reply_to(message, f"Привет, {name}! Рад тебя видеть. Чем могу помочь?\n\n💬 Бесплатный лимит: 5 запросов.")

@bot.message_handler(commands=['pro'])
def pro(message):
    bot.reply_to(message, "💎 Тариф PRO:\n• Безлимитные запросы\n• Длинные ответы\nЦена: 100 Stars.")

@bot.message_handler(commands=['stars'])
def stats(message):
    if message.from_user.id == ADMIN_ID:
        total = len(users)
        pro_count = sum(1 for d in users.values() if d.get("pro"))
        text = f"📊 **Статистика бота**\n\n"
        text += f"👥 Всего пользователей: {total}\n"
        text += f"💎 PRO: {pro_count}\n"
        text += f"🆓 Бесплатных: {total - pro_count}\n\n"
        for uid, data in users.items():
            status = "💎 PRO" if data.get("pro") else "🆓 Free"
            text += f"ID {uid}: {data['requests']} запросов | {status}\n"
        bot.reply_to(message, text)
    else:
        bot.reply_to(message, "Извини, это команда только для администратора. 🙏")

@bot.message_handler(func=lambda message: True)
def ask_ai(message):
    user_id = message.from_user.id
    if user_id not in users:
        users[user_id] = {"requests": 0, "pro": False}

    if not users[user_id]["pro"] and users[user_id]["requests"] >= 5:
        bot.reply_to(message, "Извини, бесплатные запросы закончились. Оформи /pro, пожалуйста. 🙏")
        return

    if not AI_ENABLED:
        bot.reply_to(message, "Извини, я сейчас недоступен. Попробуй чуть позже, пожалуйста.")
        return

    bot.send_chat_action(message.chat.id, 'typing')

    try:
        response = giga.chat(message.text)
        answer = response.choices[0].message.content
        users[user_id]["requests"] += 1
        bot.reply_to(message, answer)
    except Exception as e:
        logging.error(f"Ошибка ИИ: {e}")
        bot.reply_to(message, "Извини, что-то пошло не так. Попробуй ещё раз, пожалуйста.")

if __name__ == "__main__":
    print("Бот запущен...")
    bot.polling(none_stop=True)
