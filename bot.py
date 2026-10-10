import telebot
import logging
import os
from gigachat import GigaChat
from telebot.types import LabeledPrice, PreCheckoutQuery

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

# --- ОПЛАТА ---
@bot.message_handler(commands=['pro'])
def pro(message):
    user_id = message.from_user.id
    # Если уже PRO — сообщаем об этом
    if user_id in users and users[user_id].get("pro"):
        bot.reply_to(message, "У вас уже активирован тариф PRO. Спасибо за поддержку!")
        return

    # Отправляем счёт в Telegram Stars
    prices = [LabeledPrice(label="PRO-подписка", amount=100)]  # 100 Stars
    bot.send_invoice(
        chat_id=message.chat.id,
        title="Тариф PRO",
        description="Безлимитные запросы и длинные ответы.",
        invoice_payload="pro_purchase",
        provider_token="",  # Для цифровых товаров оставляем пустым
        currency="XTR",     # Обязательно для Telegram Stars
        prices=prices,
        start_parameter="pro"
    )

# Обязательное подтверждение перед оплатой
@bot.pre_checkout_query_handler(func=lambda query: True)
def process_pre_checkout(query: PreCheckoutQuery):
    # Всегда разрешаем оплату
    bot.answer_pre_checkout_query(query.id, ok=True)

# Успешная оплата — выдаём PRO
@bot.message_handler(content_types=['successful_payment'])
def got_payment(message):
    user_id = message.from_user.id
    if user_id not in users:
        users[user_id] = {"requests": 0, "pro": False}
    
    users[user_id]["pro"] = True
    bot.reply_to(message, "✅ Оплата прошла успешно! PRO-подписка активирована. Теперь у вас безлимитные запросы.")

@bot.message_handler(commands=['stats'])
def stats(message):
    if message.from_user.id == ADMIN_ID:
        text = f"👥 Всего пользователей: {len(users)}\n"
        for uid, data in users.items():
            status = "PRO" if data.get("pro") else "Free"
            text += f"ID {uid}: {data['requests']} запросов | {status}\n"
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
