import telebot
import logging
import os
import random
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

# --- ПРИВЕТСТВИЯ (просто «Привет!» + вежливость) ---
HELLO_PHRASES = [
    "Привет, {name}! Рад тебя видеть. Чем могу помочь?",
    "Привет, {name}! Я здесь, чтобы ответить на твои вопросы. Спрашивай, пожалуйста.",
    "Привет, {name}! Давай общаться. Что тебя интересует?",
    "Привет, {name}! Всегда рад помочь. О чём хочешь поговорить?",
]

# --- ЕСЛИ ЛИМИТ ЗАКОНЧИЛСЯ ---
LOW_LIMIT_PHRASES = [
    "{name}, к сожалению, бесплатные запросы закончились. Но есть /pro — и я снова буду отвечать без ограничений. Спасибо за понимание!",
    "Извини, {name}, лимит исчерпан. Если хочешь продолжить — оформи /pro, пожалуйста. Благодарю, что ты со мной!",
    "{name}, бесплатные запросы подошли к концу. Загляни в /pro, если хочешь продолжать общение. Спасибо!",
]

# --- ОШИБКИ ---
ERROR_PHRASES = [
    "Извини, что-то пошло не так. Давай попробуем ещё раз, пожалуйста.",
    "Прошу прощения, произошла небольшая ошибка. Попробуй снова, пожалуйста.",
    "Извини за заминку. Давай попробуем ещё раз.",
]

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    if user_id not in users:
        users[user_id] = {"requests": 0, "pro": False}
    
    name = message.from_user.first_name
    phrase = random.choice(HELLO_PHRASES).format(name=name)
    
    bot.reply_to(message, f"{phrase}\n\n💬 Бесплатный лимит: 5 запросов. Если захочешь больше — есть /pro.")

@bot.message_handler(commands=['pro'])
def pro(message):
    user_id = message.from_user.id
    if user_id in users and users[user_id].get("pro"):
        bot.reply_to(message, "У тебя уже есть PRO, {name}! Спасибо за поддержку. ❤️".format(name=message.from_user.first_name))
        return

    prices = [LabeledPrice(label="PRO-подписка", amount=100)]
    bot.send_invoice(
        chat_id=message.chat.id,
        title="PRO-подписка Mind AI",
        description="Безлимитные запросы, длинные ответы и поддержка проекта. 💎",
        invoice_payload="pro_purchase",
        provider_token="",
        currency="XTR",
        prices=prices,
        start_parameter="pro"
    )

@bot.pre_checkout_query_handler(func=lambda query: True)
def process_pre_checkout(query: PreCheckoutQuery):
    bot.answer_pre_checkout_query(query.id, ok=True)

@bot.message_handler(content_types=['successful_payment'])
def got_payment(message):
    user_id = message.from_user.id
    if user_id not in users:
        users[user_id] = {"requests": 0, "pro": False}
    
    users[user_id]["pro"] = True
    phrases = [
        "Спасибо огромное, {name}! PRO активирован. Теперь спрашивай сколько хочешь — я всегда рядом. 💎",
        "{name}, спасибо тебе! PRO включён. Теперь безлимит — пользуйся на здоровье!",
    ]
    bot.reply_to(message, random.choice(phrases).format(name=message.from_user.first_name))

@bot.message_handler(commands=['stats'])
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
            text += f"ID {uid}: {data['requests']} запросов | {status}\n"bot.reply_to(message, text)
    else:
        bot.reply_to(message, "Извини, это команда только для администратора. 🙏")

@bot.message_handler(func=lambda message: True)
def ask_ai(message):
    user_id = message.from_user.id
    name = message.from_user.first_name
    
    if user_id not in users:
        users[user_id] = {"requests": 0, "pro": False}

    if not users[user_id]["pro"] and users[user_id]["requests"] >= 5:
        bot.reply_to(message, random.choice(LOW_LIMIT_PHRASES).format(name=name))
        return

    if not AI_ENABLED:
        bot.reply_to(message, "Извини, {name}, я сейчас недоступен. Попробуй чуть позже, пожалуйста. 🙏".format(name=name))
        return

    bot.send_chat_action(message.chat.id, 'typing')

    try:
        response = giga.chat(message.text)
        answer = response.choices[0].message.content
        users[user_id]["requests"] += 1
        
        # Вежливая подпись
        answer = f"{answer}\n\n---\n💬 _Запрос №{users[user_id]['requests']}. Я всегда рядом, если что-то понадобится!_"
        bot.reply_to(message, answer)
    except Exception as e:
        logging.error(f"Ошибка ИИ: {e}")
        bot.reply_to(message, random.choice(ERROR_PHRASES))
