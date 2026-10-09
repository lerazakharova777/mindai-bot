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
    
    data = {
        "scope": "GIGACHAT_API_PERS"
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post("https://ngw.devices.sberbank.ru:9443/api/v2/oauth", headers=headers, data=data, ssl=False) as resp:
            if resp.status == 200:
                result = await resp.json()
                gigachat_token = result['access_token']
                token_expires_at = time.time() + 1700
                return gigachat_token
            else:
                print(f"Ошибка получения токена: {resp.status}")
                return None

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    await message.answer(
        f"Привет, {message.from_user.first_name}! 👋\n\n"
        "Я — Mind AI. Задай мне любой вопрос, и я отвечу!"
    )

@dp.message(Command("pro"))
async def cmd_pro(message: types.Message):
    await message.answer(
        "💎 Тариф PRO\n\n"
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
    
    data = {
        "model": "GigaChat",
        "messages": [
            {"role": "user", "content": message.text}
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
