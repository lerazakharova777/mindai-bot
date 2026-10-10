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
    bot.reply_to(message, "Привет! Я Mind AI. Напиши мне любой вопрос, и я отвечу.\nБесплатный лимит: 5 запросов.")

@bot.message_handler(commands=['pro'])
def pro(message):
    bot.reply_to(message, "💎 Тариф PRO:\n• Безлимитные запросы\n• Длинные ответы\nЦена: 100 Stars.")

@bot.message_handler(commands=['stats'])
def stats(message):
    if message.from_user.id == ADMIN_ID:
        text = f"👥 Всего пользователей: {len(users)}\n"
        for uid, data in users.items():
            text += f"ID {uid}: {data['requests']} запросов\n"
        bot.reply_to(message, text)
    else:
        bot.reply_to(message, "У вас нет доступа.")

@bot.message_handler(func=lambda message: True)
def ask_ai(message):
    user_id = message.from_user.id
    if user_id not in users:
        users[user_id] = {"requests": 0, "pro": False}

    if not users[user_id]["pro"] and users[user_id]["requests"] >= 5:
        bot.reply_to(message, "❌ Лимит исчерпан. Купите PRO (/pro).")
        return

    if not AI_ENABLED:
        bot.reply_to(message, "⚠️ ИИ временно недоступен.")
        return

    bot.send_chat_action(message.chat.id, 'typing')

    try:
        response = giga.chat(message.text)
        answer = response.choices[0].message.content
        users[user_id]["requests"] += 1
        bot.reply_to(message, answer)
    except Exception as e:
        logging.error(f"Ошибка ИИ: {e}")
        bot.reply_to(message, "⚠️ Ошибка при запросе к ИИ.")

if __name__ == "__main__":
    print("Бот запущен...")
    bot.polling(none_stop=True)
