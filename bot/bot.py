import os
import json
import asyncio
from datetime import datetime, timedelta, time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import nest_asyncio

nest_asyncio.apply()  # позволяет работать в окружениях с уже запущенным loop

TOKEN = os.getenv("BOT_TOKEN")
DATA_FILE = "users.json"

# Загрузка пользователей
if os.path.exists(DATA_FILE):
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        users = json.load(f)
else:
    users = {}

# Юбилейные дни
ANNIVERSARY_DAYS = {
    10: "💖 10 дней вместе — это только начало!",
    20: "🔥 20 дней в отношениях! Продолжаем?",
    50: "🔥 50 дней вместе! Уже серьёзно!",
    100: "🎉 100 дней вместе! Вау!",
    150: "🎉 150 дней вместе! Может пора остановиться?"
}
ANNIVERSARY_IMAGE = "https://i.imgur.com/0Z8FQkM.png"

# Сохранение пользователей
def save_users():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("❤️ Я нахожусь в отношениях", callback_data="start_relation")]
    ])
    await update.message.reply_text(
        "Привет! 👋\nЯ бот, который считает дни ваших отношений 💖\n\n"
        "Нажми кнопку ниже, если ты сейчас в отношениях:",
        reply_markup=keyboard
    )

# Начало отношений
async def start_relation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chat_id = str(query.message.chat.id)

    if chat_id in users and users[chat_id]["active"]:
        await query.answer("Счётчик уже запущен!")
        return

    users[chat_id] = {"day": 1, "active": True}
    save_users()

    await query.answer()
    await send_day_message(context, chat_id)

# Отправка сообщения о дне
async def send_day_message(context, chat_id):
    if chat_id not in users or not users[chat_id]["active"]:
        return

    day = users[chat_id]["day"]
    text = f"День {day}: Ещё не расстались"

    if day in ANNIVERSARY_DAYS:
        text += f"\n\n{ANNIVERSARY_DAYS[day]}"
        await context.bot.send_photo(chat_id, ANNIVERSARY_IMAGE)

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("💔 Расстались", callback_data="breakup")]
    ])

    await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=keyboard)

# Подтверждение расставания
async def breakup_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Да", callback_data="breakup_yes"),
            InlineKeyboardButton("❌ Нет", callback_data="breakup_no")
        ]
    ])
    await query.answer()
    await query.edit_message_text("Вы точно расстались?", reply_markup=keyboard)

# Да — остановка
async def breakup_yes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chat_id = str(query.message.chat.id)

    users[chat_id]["active"] = False
    save_users()

    await query.answer()
    await query.edit_message_text("💔 Счётчик остановлен.\nСпасибо, что пользовались ботом.")

# Нет — продолжаем
async def breakup_no(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("💖 Хорошо, продолжаем считать дни!")

# Асинхронный цикл для ежедневных сообщений
async def daily_loop(app):
    while True:
        now = datetime.utcnow() + timedelta(hours=3)  # МСК
        target_time = datetime.combine(now.date(), time(hour=12, minute=0, second=0))
        if now > target_time:
            target_time += timedelta(days=1)
        wait_seconds = (target_time - now).total_seconds()
        await asyncio.sleep(wait_seconds)

        # Отправляем сообщение всем активным пользователям
        for chat_id in users:
            if users[chat_id]["active"]:
                users[chat_id]["day"] += 1
                await send_day_message(app, chat_id)
        save_users()

# Основная функция запуска
def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(start_relation, pattern="start_relation"))
    app.add_handler(CallbackQueryHandler(breakup_confirm, pattern="breakup"))
    app.add_handler(CallbackQueryHandler(breakup_yes, pattern="breakup_yes"))
    app.add_handler(CallbackQueryHandler(breakup_no, pattern="breakup_no"))

    # Запускаем ежедневный цикл через asyncio
    asyncio.create_task(daily_loop(app))

    # PTB сам запускает свой loop
    app.run_polling()

if __name__ == "__main__":
    main()
