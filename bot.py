import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
import aiohttp
import uuid
import time

# Токен твоего бота
BOT_TOKEN = "8948122875:AAE5PmFoT58posjBymvMfaa9g2XQx2nEC9w"

# Ключ авторизации GigaChat
GIGACHAT_AUTH_KEY = "MDFhMTIwMGUtMDAwMC03MDhkLTgwNTEtN2VhZTM1ZTU4N2VlOmQ1OTQ0M2QyLTVkNDMtNGQwZi05YzY3LTkyYjFmMzQ2YzZlYg=="

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

gigachat_token = None
token_expires_at = 0

# Хранилище имен пользователей
user_names = {}

async def get_gigachat_token():
    global gigachat_token, token_expires_at
    if gigachat_token and time.time() < token_expires_at:
        return gigachat_token
    
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json",
        "RqUID": str(uuid.uuid4()),
        "Authorization": f"Basic {GIGACHAT_AUTH_KEY}"
    }
    data = {"scope": "GIGACHAT_API_PERS"}
    
    async with aiohttp.ClientSession() as session:
        async with session.post("https://ngw.devices.sberbank.ru:9443/api/v2/oauth", headers=headers, data=data, ssl=False) as resp:
            if resp.status == 200:
                result = await resp.json()
                gigachat_token = result['access_token']
                token_expires_at = time.time() + 1700
                return gigachat_token
            return None

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    if user_id not in user_names:
        user_names[user_id] = None
        await message.answer(
            f"Привет! 👋 Я — Mind AI.\n\n"
            "Давай познакомимся. Как тебя зовут?"
        )
    else:
        name = user_names[user_id]
        await message.answer(f"С возвращением, {name}! 😊 Чем могу помочь?")

@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    await message.answer(
        "🤖 **Что я умею:**\n\n"
        "• Отвечаю на любые вопросы\n"
        "• Помогаю с учёбой и идеями\n"
        "• Пишу тексты и объясняю сложное\n"
        "• Просто болтаю, если грустно\n\n"
        "💎 **Команды:**\n"
        "/start — начать общение\n"
        "/pro — купить подписку PRO\n"
        "/help — эта справка"
    )

@dp.message(Command("pro"))
async def cmd_pro(message: types.Message):
    await message.answer(
        "💎 **Тариф PRO**\n\n"
        "• Безлимитные запросы\n"
        "• Длинные ответы\n\n"
        "Цена: 100 Stars",
        reply_markup=types.InlineKeyboardMarkup(
            inline_keyboard=[
                [types.InlineKeyboardButton(text="💎 Купить PRO", callback_data="buy_pro")]
            ]
        )
    )

@dp.callback_query(F.data == "buy_pro")
async def process_buy_pro(callback: types.CallbackQuery):
    await callback.message.answer("✅ Спасибо за покупку! (Это тест).")
    await callback.answer()

@dp.message(F.text)
async def handle_message(message: types.Message):
    user_id = message.from_user.id
    text = message.text

    # Если имя еще не сохранено — сохраняем его
    if user_id not in user_names or user_names[user_id] is None:
        user_names[user_id] = text
        await message.answer(f"Очень приятно, {text}! 😊 Теперь я запомнил твоё имя. Спрашивай что угодно!")
        return

    name = user_names[user_id]
    await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")

    token = await get_gigachat_token()
    if not token:
        await message.answer("Ошибка авторизации. Проверь ключ GigaChat.")
        return

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": f"Bearer {token}"
    }

    # Системный промпт: бот общается как близкий друг
    system_prompt = (
        f"Ты — близкий друг пользователя по имени {name}. "
        "Общайся тепло, искренне и с заботой. Обращайся по имени, используй эмодзи, "
        "поддерживай в трудную минуту, радуйся успехам. Отвечай кратко, но по-дружески."
    )

    data = {
        "model": "GigaChat","messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text}
        ]
    }

    async with aiohttp.ClientSession() as session:
        async with session.post("https://gigachat.devices.sberbank.ru/api/v1/chat/completions", headers=headers, json=data, ssl=False) as resp:
            if resp.status == 200:
                result = await resp.json()
                answer = result['choices'][0]['message']['content']
                await message.answer(answer)
            else:
                await message.answer(f"Ошибка GigaChat: {resp.status}")

async def main():
    print("Бот запущен и готов к работе...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
