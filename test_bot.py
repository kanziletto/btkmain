import asyncio
from telebot.async_telebot import AsyncTeleBot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

BOT_TOKEN = "8280880523:AAHa1jdL_JKZa1YqLr063Qp6VGOLFU2W7QQ"  # BotFather'dan aldığın token

bot = AsyncTeleBot(BOT_TOKEN)


def build_menu():
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("👤 Hesabım", callback_data="menu_hesap"),
        InlineKeyboardButton("📄 Domainlerim", callback_data="menu_domainler"),
    )
    return kb


@bot.message_handler(commands=['start'])
async def send_welcome(message):
    await bot.send_message(
        message.chat.id,
        "Test botu: /start altında inline buton var.\n\nButonlara tıkla, cevap gelmeli.",
        reply_markup=build_menu()
    )


@bot.callback_query_handler(func=lambda call: True)
async def test_callback(call):
    # Konsolda da görelim:
    print("CALLBACK GELDI:", call, "DATA:", call.data)

    # Kullanıcıya basit bir mesaj dönelim:
    await bot.answer_callback_query(call.id)  # spinner dursun
    await bot.send_message(call.message.chat.id, f"Callback aldım: {call.data}")


async def main():
    await bot.polling(non_stop=True, skip_pending=True)


if __name__ == "__main__":
    asyncio.run(main())

